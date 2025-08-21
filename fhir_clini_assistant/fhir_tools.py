import os
from datetime import datetime
import logging
from typing import Any, Optional

from google.auth import default
from google.auth.transport.requests import AuthorizedSession
from google.genai import types

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
import yaml
from pathlib import Path
import json
import unicodedata

logger = logging.getLogger(__name__)


def _build_fhir_store_base_url() -> str:
  project = os.getenv("FHIR_PROJECT")
  location = os.getenv("FHIR_LOCATION")
  dataset = os.getenv("FHIR_DATASET")
  store = os.getenv("FHIR_STORE")
  if not all([project, location, dataset, store]):
    missing = [
        name
        for name, val in (
            ("FHIR_PROJECT", project),
            ("FHIR_LOCATION", location),
            ("FHIR_DATASET", dataset),
            ("FHIR_STORE", store),
        )
        if not val
    ]
    raise ValueError(
        "Faltan variables de entorno para FHIR: " + ", ".join(missing)
    )
  return (
      "https://healthcare.googleapis.com/v1/projects/"
      f"{project}/locations/{location}/datasets/{dataset}/fhirStores/{store}/fhir"
  )


def _new_authorized_session() -> AuthorizedSession:
  credentials, _ = default()
  return AuthorizedSession(credentials)


def _normalize_patient_query_value(patient: str) -> list[str]:
  if not patient:
    return []
  patient = patient.strip()
  if patient.lower().startswith("patient/"):
    return [patient, patient.replace("Patient/", "")]  # try both
  return [patient, f"Patient/{patient}"]


class GetConditionsTool(BaseTool):
  """Obtiene condiciones clínicas (FHIR Condition) de un paciente.

  Argumentos:
    patient: string con id del paciente, con o sin prefijo "Patient/".
  Retorno:
    lista[dict]: {condicion, codigo, fecha_inicio, fecha_registro, estado_verificacion, estado_clinico}
  """

  def __init__(self):
    super().__init__(
        name="get_conditions",
        description=(
            "Obtiene las condiciones clínicas activas o registradas del paciente"
            " desde FHIR (Condition). Acepta patient con o sin prefijo 'Patient/'."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    # Probar ambas variantes del parámetro de búsqueda
    candidates = _normalize_patient_query_value(patient)
    for candidate in candidates:
      resp = self._session.get(
          f"{self._base_url}/Condition",
          params={"patient": candidate},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      # 200 esperado; continuar con siguiente candidato si no
      if resp.status_code != 200:
        continue

      bundle = resp.json()
      entries = bundle.get("entry", [])
      results = []
      for entry in entries:
        resource = entry.get("resource", {})

        code_obj = resource.get("code", {})
        condicion = "Desconocida"
        codigo = ""
        if "text" in code_obj and code_obj["text"]:
          condicion = code_obj["text"]
        elif code_obj.get("coding"):
          condicion = code_obj["coding"][0].get("display", "Desconocida")
          codigo = code_obj["coding"][0].get("code", "")

        verification_obj = resource.get("verificationStatus", {})
        estado_verificacion = (
            verification_obj.get("coding", [{}])[0].get("code", "Desconocido")
        )

        clinical_obj = resource.get("clinicalStatus", {})
        estado_clinico = (
            clinical_obj.get("coding", [{}])[0].get("code", "Desconocido")
        )

        fecha_inicio = resource.get(
            "onsetDateTime", resource.get("recordedDate", "Fecha no disponible")
        )
        fecha_registro = resource.get("recordedDate", "Fecha no disponible")

        results.append(
            {
                "condicion": condicion,
                "codigo": codigo,
                "fecha_inicio": fecha_inicio,
                "fecha_registro": fecha_registro,
                "estado_verificacion": estado_verificacion,
                "estado_clinico": estado_clinico,
            }
        )

      if results:
        return results

    # Si ninguna variante devolvió 200 con resultados
    raise types.FunctionCallError(
        code="NOT_FOUND",
        message=(
            "No se encontraron condiciones clínicas registradas para el paciente"
        ),
    ) 


class GetPatientByIdTool(BaseTool):
  """Obtiene información de un paciente (FHIR Patient/{id})."""

  def __init__(self):
    super().__init__(
        name="get_patient_by_id",
        description=(
            "Obtiene información del paciente por ID directo en FHIR (Patient/{id})."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get("patient_id", "")
    if not patient_id:
      raise ValueError("Parámetro requerido: patient_id")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    resp = self._session.get(
        f"{self._base_url}/Patient/{patient_id}",
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if resp.status_code != 200:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="Paciente no encontrado"
      )
    resource = resp.json()

    # Extraer datos clave
    nombre = resource.get("name", [{}])[0].get("text", "Desconocido")
    contacto = [
        {"value": t.get("value", ""), "system": t.get("system", "")}
        for t in resource.get("telecom", [])
        if t.get("value")
    ]
    documentos = [
        {
            "value": i.get("value", ""),
            "display": i.get("type", {})
            .get("coding", [{}])[0]
            .get("display", "Desconocido"),
        }
        for i in resource.get("identifier", [])
        if i.get("value")
    ]
    direccion = resource.get("address", [{}])[0] if resource.get("address") else {}

    return {
        "nombre": nombre,
        "contacto": contacto,
        "documentos": documentos,
        "genero": resource.get("gender", "Desconocido"),
        "fecha_de_nacimiento": resource.get("birthDate", "Desconocida"),
        "direccion": direccion,
        "activo": resource.get("active", False),
    }


class GetObservacionesTool(BaseTool):
  """Obtiene observaciones clínicas (FHIR Observation) por paciente."""

  def __init__(self):
    super().__init__(
        name="get_observaciones",
        description=(
            "Obtiene observaciones (Observation) del paciente. Usa subject=Patient/{id}."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    # Intentar con subject y con patient
    candidates = _normalize_patient_query_value(patient)
    # subject requiere prefijo Patient/
    subject_vals = [c if c.lower().startswith("patient/") else f"Patient/{c}" for c in candidates]

    # 1) subject
    resp = self._session.get(
        f"{self._base_url}/Observation",
        params={"subject": subject_vals[0]},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    # 2) fallback patient
    if resp.status_code != 200:
      resp = self._session.get(
          f"{self._base_url}/Observation",
          params={"patient": candidates[0]},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )

    if resp.status_code != 200:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se encontraron observaciones registradas"
      )

    entries = resp.json().get("entry", [])
    if not entries:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se encontraron observaciones registradas"
      )

    results = []
    for entry in entries:
      resource = entry.get("resource", {})
      code = resource.get("code", {}).get("text", "Observación sin nombre")
      val_q = resource.get("valueQuantity", {})
      referencia = resource.get("referenceRange", [{}])[0]
      results.append(
          {
              "observacion": code,
              "valor": val_q.get("value"),
              "unidad": val_q.get("unit"),
              "rango_referencia": {
                  "min": referencia.get("low", {}).get("value"),
                  "max": referencia.get("high", {}).get("value"),
              },
              "fecha": resource.get("effectiveDateTime", "Fecha no disponible"),
              "paciente_id": resource.get("subject", {})
              .get("reference", "")
              .replace("Patient/", ""),
          }
      )
    return results


class GetAllergiesTool(BaseTool):
  """Obtiene alergias (AllergyIntolerance) por paciente."""

  def __init__(self):
    super().__init__(
        name="get_allergies",
        description=(
            "Obtiene alergias confirmadas y activas del paciente (AllergyIntolerance)."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    patient_id = patient.replace("Patient/", "")
    resp = self._session.get(
        f"{self._base_url}/AllergyIntolerance",
        params={"patient": patient_id},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if resp.status_code != 200:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se pudo obtener alergias"
      )
    entries = resp.json().get("entry", [])
    results = []
    for entry in entries:
      resource = entry.get("resource", {})
      status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get(
          "code", ""
      )
      verification = resource.get("verificationStatus", {}).get("coding", [{}])[0].get(
          "code", ""
      )
      code = resource.get("code", {}).get("coding", [{}])[0]
      reaction = resource.get("reaction", [{}])[0]
      results.append(
          {
              "alergia_a": code.get("display", "Desconocido"),
              "codigo": code.get("code", ""),
              "categoria": resource.get("category", []),
              "descripcion_reaccion": reaction.get("description", ""),
              "manifestacion": reaction.get("manifestation", [{}])[0]
              .get("coding", [{}])[0]
              .get("display", ""),
              "severidad": reaction.get("severity", ""),
              "criticalidad": resource.get("criticality", ""),
              "fecha_registro": resource.get(
                  "recordedDate", "Fecha no disponible"
              ),
              "estado_clinico": status,
              "estado_verificacion": verification,
              "paciente_id": resource.get("patient", {})
              .get("reference", "")
              .replace("Patient/", ""),
          }
      )
    if not results:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se encontraron alergias registradas"
      )
    return results


class GetMedicationRequestsTool(BaseTool):
  """Obtiene prescripciones (MedicationRequest) del paciente."""

  def __init__(self):
    super().__init__(
        name="get_medication_requests",
        description=(
          "Obtiene recetas de medicamentos (MedicationRequest) por paciente."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    # intentar ambos parámetros
    resp = self._session.get(
        f"{self._base_url}/MedicationRequest",
        params={"patient": patient},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if resp.status_code != 200:
      resp = self._session.get(
          f"{self._base_url}/MedicationRequest",
          params={"subject": f"Patient/{patient}"},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
    if resp.status_code != 200:
      raise types.FunctionCallError(
          code="NOT_FOUND",
          message="No se pudo obtener la información de medicamentos",
      )

    entries = resp.json().get("entry", [])
    results = []
    for entry in entries:
      resource = entry.get("resource", {})
      med_cc = resource.get("medicationCodeableConcept", {})
      medicamento = med_cc.get("coding", [{}])[0].get("display", "Desconocido")
      status = resource.get("status", "Desconocido")
      intent = resource.get("intent", "Desconocido")
      instrucciones = [di.get("text", "") for di in resource.get("dosageInstruction", [])]
      razones = [r.get("display", "") for r in resource.get("reasonReference", [])]
      patient_ref = (
          resource.get("subject", {})
          .get("reference", resource.get("patient", {}).get("reference", ""))
          .replace("Patient/", "")
      )
      results.append(
          {
              "medicamento": medicamento,
              "estado": status,
              "intencion": intent,
              "instrucciones": instrucciones,
              "razones": razones,
              "paciente_id": patient_ref,
          }
      )
    if not results:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se encontraron recetas de medicamentos"
      )
    return results


class GetFamilyMemberHistoryTool(BaseTool):
  """Obtiene antecedentes familiares completados (FamilyMemberHistory)."""

  def __init__(self):
    super().__init__(
        name="get_family_member_history",
        description=(
            "Obtiene antecedentes familiares completados del paciente (FamilyMemberHistory)."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    patient_id = patient.replace("Patient/", "")
    resp = self._session.get(
        f"{self._base_url}/FamilyMemberHistory",
        params={"patient": patient_id},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if resp.status_code != 200:
      raise types.FunctionCallError(
          code="NOT_FOUND",
          message="No se pudo obtener antecedentes familiares",
      )

    entries = resp.json().get("entry", [])
    results = []
    for entry in entries:
      resource = entry.get("resource", {})
      if resource.get("status") != "completed":
        continue

      relationship_obj = resource.get("relationship", {})
      relationship = "Relación desconocida"
      if relationship_obj.get("coding"):
        relationship = relationship_obj["coding"][0].get("display", relationship)
      elif "text" in relationship_obj:
        relationship = relationship_obj["text"]

      patient_ref = resource.get("patient", {}).get("reference", "").replace(
          "Patient/", ""
      )

      for condition in resource.get("condition", []):
        cond_info = condition.get("code", {})
        condicion = "Condición desconocida"
        codigo = ""
        if cond_info.get("coding"):
          condicion = cond_info["coding"][0].get("display", condicion)
          codigo = cond_info["coding"][0].get("code", "")
        elif "text" in cond_info:
          condicion = cond_info["text"]

        results.append(
            {
                "paciente_id": patient_ref,
                "relacion": relationship.strip(),
                "condicion": condicion.strip(),
                "codigo": codigo.strip(),
                "contribuyo_a_la_muerte": condition.get("contributedToDeath", False),
            }
        )

    if not results:
      raise types.FunctionCallError(
          code="NOT_FOUND",
          message="No se encontraron antecedentes familiares válidos",
      )
    return results


# Helpers para QuestionnaireResponse
async def _fetch_questionnaire_entries(session: AuthorizedSession, base_url: str, patient: str) -> list[dict]:
  # Intentar con patient y subject
  candidates = _normalize_patient_query_value(patient)
  # 1) patient
  resp = session.get(
      f"{base_url}/QuestionnaireResponse",
      params={"patient": candidates[0]},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
  )
  if resp.status_code != 200:
    # 2) subject
    resp = session.get(
        f"{base_url}/QuestionnaireResponse",
        params={"subject": f"Patient/{candidates[0]}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
  if resp.status_code != 200:
    return []
  return resp.json().get("entry", [])


def _extract_items_structure(item_list, prefix=""):
  results = []
  for item in item_list:
    text = item.get("text", "Pregunta desconocida")
    full_text = f"{prefix}{text}" if prefix else text
    answers = [str(answer.get(list(answer.keys())[0])) for answer in item.get("answer", [])]
    if answers:
      results.append({"pregunta": full_text, "respuestas": answers})
    if "item" in item:
      results.extend(_extract_items_structure(item["item"], prefix=full_text + " -> "))
  return results


class GetQuestionnaireSectionTool(BaseTool):
  """Obtiene secciones procesadas desde QuestionnaireResponse por nombre de sección."""

  def __init__(self):
    super().__init__(
        name="get_questionnaire_section",
        description=(
            "Obtiene preguntas/respuestas de una sección de QuestionnaireResponse"
            " para un paciente, dado el nombre de sección."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "")
    section_name: str = args.get("section_name", "")
    if not patient or not section_name:
      raise ValueError("Parámetros requeridos: patient, section_name")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    entries = await _fetch_questionnaire_entries(self._session, self._base_url, patient)
    results = []
    for entry in entries:
      resource = entry.get("resource", {})
      section_items = [
          item
          for item in resource.get("item", [])
          if item.get("text", "").lower() == section_name.lower()
      ]
      if not section_items:
        continue
      for item in section_items:
        preguntas = _extract_items_structure(item.get("item", []))
        results.append(
            {
                "fecha": resource.get("authored", "Fecha desconocida"),
                "estado": resource.get("status", "Desconocido"),
                "doctor_id": resource.get("author", {})
                .get("reference", "")
                .replace("Practitioner/", ""),
                "paciente_id": resource.get("patient", {})
                .get("reference", "")
                .replace("Patient/", ""),
                "preguntas": preguntas,
            }
        )
    if not results:
      raise types.FunctionCallError(
          code="NOT_FOUND",
          message=f"No se encontraron respuestas en QuestionnaireResponse para: {section_name}",
      )
    return results


# Wrappers convenientes por sección
class GetVariablesPrevencionTool(BaseTool):
  def __init__(self):
    super().__init__(
        name="get_variables_prevencion",
        description=(
            "Obtiene variables de prevención (sección de QuestionnaireResponse)."
        ),
    )
    self._delegate = GetQuestionnaireSectionTool()

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    args = {**args, "section_name": "Variables de Prevención"}
    return await self._delegate.run_async(args=args, tool_context=tool_context)


class GetPatologicosPersonalesTool(BaseTool):
  def __init__(self):
    super().__init__(
        name="get_patologicos_personales",
        description=(
            "Obtiene Antecedentes Patológicos Personales (QuestionnaireResponse)."
        ),
    )
    self._delegate = GetQuestionnaireSectionTool()

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    args = {**args, "section_name": "Antecedentes Patológicos Personales"}
    return await self._delegate.run_async(args=args, tool_context=tool_context)


class GetDeterminantesSocioambientalesTool(BaseTool):
  def __init__(self):
    super().__init__(
        name="get_determinantes_socioambientales",
        description=(
            "Obtiene Determinantes Socioambientales (QuestionnaireResponse)."
        ),
    )
    self._delegate = GetQuestionnaireSectionTool()

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    args = {**args, "section_name": "Determinantes Socioambientales"}
    return await self._delegate.run_async(args=args, tool_context=tool_context)


class GetDisponibilidadRecursosTool(BaseTool):
  """Resumen simple de recursos disponibles para un paciente.

  Devuelve un objeto con datos básicos de Patient y listas con nombres de
  recursos presentes (hasta un máximo pequeño por tipo para eficiencia).
  """

  def __init__(self):
    super().__init__(
        name="get_disponibilidad_recursos",
        description=(
            "Obtiene un resumen de recursos clínicos disponibles para un paciente."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get("patient_id", "")
    if not patient_id:
      raise ValueError("Parámetro requerido: patient_id")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    # Patient
    p = self._session.get(
        f"{self._base_url}/Patient/{patient_id}",
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if p.status_code != 200:
      raise types.FunctionCallError(code="NOT_FOUND", message="Paciente no encontrado")
    patient = p.json()
    nombre = patient.get("name", [{}])[0].get("text", "Desconocido")
    genero = patient.get("gender", "Desconocido")
    fecha_nac = patient.get("birthDate", "Desconocida")

    # Helper: gather up to N names per resource type
    def _gather(resource_type: str, params: dict[str, str], name_fn):
      r = self._session.get(
          f"{self._base_url}/{resource_type}",
          params=params,
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if r.status_code != 200:
        return []
      items = []
      for entry in r.json().get("entry", [])[:5]:
        items.append(name_fn(entry.get("resource", {})))
      return [i for i in items if i]

    params_patient = {"patient": patient_id}
    params_subject = {"subject": f"Patient/{patient_id}"}

    condiciones = _gather(
        "Condition",
        params_patient,
        lambda res: (res.get("code", {}).get("coding", [{}])[0].get("display") or res.get("code", {}).get("text")),
    )
    observaciones = _gather(
        "Observation",
        params_subject,
        lambda res: res.get("code", {}).get("text"),
    )
    alergias = _gather(
        "AllergyIntolerance",
        params_patient,
        lambda res: res.get("code", {}).get("coding", [{}])[0].get("display"),
    )
    antecedentes_familiares = _gather(
        "FamilyMemberHistory",
        params_patient,
        lambda res: res.get("relationship", {}).get("text")
        or (res.get("relationship", {}).get("coding", [{}])[0].get("display")),
    )
    medicamentos = _gather(
        "MedicationRequest",
        params_patient,
        lambda res: res.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
    )

    return {
        "patient_id": patient_id,
        "nombre": nombre,
        "genero": genero,
        "fecha_de_nacimiento": fecha_nac,
        "recursos_disponibles": {
            "condiciones": condiciones,
            "observaciones": observaciones,
            "alergias": [
                {"alergia_a": a, "estado": "", "verificacion": ""} for a in alergias
            ],
            "antecedentes_familiares": antecedentes_familiares,
            "medicamentos": medicamentos,
        },
    } 
 
 
class GetMotivoConsultaTool(BaseTool):
  """Obtiene motivos de consulta y cuestionarios asociados al encounter de triage más reciente.

  Busca el Encounter del paciente que tenga la extensión
  http://goes.gob.sv/fhir/extensions/triage/created-datetime y luego obtiene
  los QuestionnaireResponse vinculados a ese encounter para devolver:
  - motivos (questionnaire "symptom-list"): "<motivo>", orden <n>
  - detalles (questionnaire "symptom-qualification"): pares pregunta/respuesta
  - priorizacion (questionnaire "prioritization-questions"): pares pregunta/respuesta
  """

  def __init__(self):
    super().__init__(
        name="get_motivo_consulta",
        description=(
            "Obtiene los motivos de consulta y sus detalles/priorización a partir del "
            "encounter de triage más reciente del paciente (resuelto desde el patient)."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "") or args.get("patient_id", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    logger.debug("get_motivo_consulta: args patient=%r base_url=%s", patient, self._base_url)

    def _parse_dt(v: str) -> Optional[datetime]:
      try:
        if not v:
          return None
        # Soporta 'Z' y offsets
        if v.endswith("Z"):
          v = v.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
      except Exception:
        return None

    TRIAGE_CREATED_URL = "http://goes.gob.sv/fhir/extensions/triage/created-datetime"

    # 1) Resolver encounter si no fue provisto
    candidates = _normalize_patient_query_value(patient)
    # Intentar con patient y luego subject, limitar a los últimos 5
    resp = self._session.get(
        f"{self._base_url}/Encounter",
        params={"patient": candidates[0], "_sort": "-date", "_count": "5"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    logger.debug("Encounter search by patient: status=%s", getattr(resp, "status_code", None))
    if resp.status_code != 200:
      resp = self._session.get(
          f"{self._base_url}/Encounter",
          params={"subject": f"Patient/{candidates[0]}", "_sort": "-date", "_count": "5"},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
    logger.debug("Encounter search by subject: status=%s", getattr(resp, "status_code", None))
    entries = resp.json().get("entry", [])[:5] if resp.status_code == 200 else []
    logger.debug("Encounter entries found: %d", len(entries))

    latest_tuple: tuple[Optional[datetime], str] = (None, "")
    for entry in entries:
      res = entry.get("resource", {})
      # Filtrar solo encounters que tengan la extensión de triage created-datetime
      created_dt_val = None
      for ext in res.get("extension", []) or []:
        if ext.get("url") == TRIAGE_CREATED_URL:
          created_dt_val = ext.get("valueDateTime")
          break
      if not created_dt_val:
        logger.debug("Encounter %s skipped: missing triage created-datetime extension", res.get("id"))
        continue
      created_dt = _parse_dt(created_dt_val) or _parse_dt(res.get("meta", {}).get("lastUpdated", "")) or _parse_dt(res.get("period", {}).get("start", ""))
      if created_dt is None:
        logger.debug("Encounter %s skipped: could not parse created_dt", res.get("id"))
        continue
      if latest_tuple[0] is None or created_dt > latest_tuple[0]:
        latest_tuple = (created_dt, res.get("id", ""))
        logger.debug("Encounter candidate updated: id=%s created_dt=%s", latest_tuple[1], latest_tuple[0])

    enc_id = latest_tuple[1]

    if not enc_id:
      logger.warning("No triage encounter found for patient=%r", patient)
      # Devolver mensaje para que el agente pida motivos en la conversación
      return {
        "encounter_id": "",
        "motivos": [],
        "detalles": [],
        "priorizacion": [],
        "mensaje": "Este paciente no tiene motivos de consulta registrados. Pregunta por el motivo principal de consulta.",
      }

    # 2) Obtener QuestionnaireResponse por encounter
    qr_resp = self._session.get(
        f"{self._base_url}/QuestionnaireResponse",
        params={"encounter": f"Encounter/{enc_id}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    logger.debug("QuestionnaireResponse search by encounter ref: status=%s", getattr(qr_resp, "status_code", None))
    if qr_resp.status_code != 200:
      qr_resp = self._session.get(
          f"{self._base_url}/QuestionnaireResponse",
          params={"encounter": enc_id},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
    logger.debug("QuestionnaireResponse search by encounter id: status=%s", getattr(qr_resp, "status_code", None))
    qr_entries = qr_resp.json().get("entry", []) if qr_resp.status_code == 200 else []
    logger.debug("QuestionnaireResponse entries found: %d", len(qr_entries))

    MOTIVOS_Q = "http://goes.gob.sv/fhir/questionnaire/symptom-list"
    DETALLES_Q = "http://goes.gob.sv/fhir/questionnaire/symptom-qualification"
    PRIORI_Q = "http://goes.gob.sv/fhir/questionnaire/prioritization-questions"
    SYMPTOM_ORDER_URL = "http://goes.gob.sv/fhir/extensions/symptom/order"

    motivos: list[dict[str, Any]] = []
    detalles: list[dict[str, Any]] = []
    priorizacion: list[dict[str, Any]] = []
    motivos_checked = 0
    motivos_aceptados = 0

    def _first_answer_value(ans_list: list[dict]) -> Optional[str]:
      for ans in ans_list or []:
        for k, v in ans.items():
          if k.startswith("value"):
            return str(v)
      return None

    for entry in qr_entries:
      qr = entry.get("resource", {})
      if qr.get("status") and qr.get("status") != "completed":
        continue
      questionnaire = qr.get("questionnaire", "")
      items = qr.get("item", []) or []

      if questionnaire == MOTIVOS_Q:
        logger.debug("Parsing symptom-list items: %d", len(items))
        for it in items:
          # Considerar solo marcados como verdaderos si vienen con valueBoolean True
          answers = it.get("answer", [])
          answer_val = _first_answer_value(answers)
          motivos_checked += 1
          if str(answer_val).lower() not in ("true", "1", "yes", "si"):
            # Si no hay respuesta booleana afirmativa, aún podemos listar si se requiere. Se omite por defecto.
            continue
          orden = None
          for ext in it.get("extension", []) or []:
            if ext.get("url") == SYMPTOM_ORDER_URL:
              orden = ext.get("valueInteger")
              break
          motivos.append({
            "motivo": it.get("linkId", ""),
            "orden": orden if isinstance(orden, int) else None,
          })
          motivos_aceptados += 1

      elif questionnaire == DETALLES_Q:
        logger.debug("Parsing symptom-qualification items: %d", len(items))
        for it in items:
          pregunta_full = it.get("linkId", "")
          pregunta = pregunta_full.split("|", 1)[1] if "|" in pregunta_full else pregunta_full
          resp_val = _first_answer_value(it.get("answer", []))
          if resp_val is not None:
            detalles.append({"pregunta": pregunta, "respuesta": resp_val})

      elif questionnaire == PRIORI_Q:
        logger.debug("Parsing prioritization-questions items: %d", len(items))
        for it in items:
          pregunta_full = it.get("linkId", "")
          pregunta = pregunta_full.split("|", 1)[1] if "|" in pregunta_full else pregunta_full
          resp_val = _first_answer_value(it.get("answer", []))
          if resp_val is not None:
            priorizacion.append({"pregunta": pregunta, "respuesta": resp_val})

    # Ordenar motivos por 'orden' si está disponible
    motivos.sort(key=lambda m: (m.get("orden") is None, m.get("orden", 0)))

    # Formatear como "<motivo>, orden <n>" si hay orden
    motivos_fmt = [
      f"{m.get('motivo','')}, orden {m['orden']}" if m.get("orden") is not None else m.get("motivo","")
      for m in motivos
    ]

    logger.debug(
      "get_motivo_consulta result: encounter_id=%s motivos_checked=%d motivos_aceptados=%d motivos=%d detalles=%d priorizacion=%d",
      enc_id, motivos_checked, motivos_aceptados, len(motivos_fmt), len(detalles), len(priorizacion)
    )

    result = {
      "encounter_id": enc_id,
      "motivos": motivos_fmt,
      "detalles": detalles,
      "priorizacion": priorizacion,
    }
    if not motivos_fmt:
      # Señal amistosa para el agente cuando no hay motivos cargados
      result["mensaje"] = "Este paciente no tiene motivos de consulta registrados. Pregunta por el motivo principal de consulta."
    return result


class GetAreasAfectadasTool(BaseTool):
  """Obtiene las áreas afectadas del triage desde ClinicalImpression más reciente.

  Lógica:
  - Con patient/patient_id, busca los últimos 5 ClinicalImpression del paciente
    (ordenados por fecha descendente).
  - Selecciona el más reciente que tenga protocol que incluya
    "http://goes.gob.sv/fhir/protocols/triage/affected-areas".
  - Devuelve la lista de áreas desde finding[].itemCodeableConcept.text.
  """

  def __init__(self):
    super().__init__(
        name="get_areas_afectadas",
        description=(
            "Obtiene las áreas afectadas del triage (ClinicalImpression con protocolo"
            " affected-areas) para el paciente."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "") or args.get("patient_id", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    logger.debug("get_areas_afectadas: patient=%r base_url=%s", patient, self._base_url)

    candidates = _normalize_patient_query_value(patient)
    # Buscar últimos 5 ClinicalImpression por patient o subject
    resp = self._session.get(
        f"{self._base_url}/ClinicalImpression",
        params={"patient": candidates[0], "_sort": "-date", "_count": "5"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if resp.status_code != 200:
      resp = self._session.get(
          f"{self._base_url}/ClinicalImpression",
          params={"subject": f"Patient/{candidates[0]}", "_sort": "-date", "_count": "5"},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
    entries = resp.json().get("entry", [])[:5] if resp.status_code == 200 else []
    logger.debug("ClinicalImpression entries found: %d", len(entries))

    PROTOCOL_URL = "http://goes.gob.sv/fhir/protocols/triage/affected-areas"

    def _parse_dt(v: str) -> Optional[datetime]:
      try:
        if not v:
          return None
        if v.endswith("Z"):
          v = v.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
      except Exception:
        return None

    # Elegir el más reciente que cumpla protocolo
    selected = None
    selected_dt: Optional[datetime] = None
    for entry in entries:
      res = entry.get("resource", {})
      protocols = res.get("protocol", []) or []
      logger.debug(
        "ClinicalImpression candidate id=%s protocols=%s date=%s",
        res.get("id"), protocols, res.get("date") or res.get("meta", {}).get("lastUpdated")
      )
      if PROTOCOL_URL not in protocols:
        continue
      dt = _parse_dt(res.get("date", "")) or _parse_dt(res.get("meta", {}).get("lastUpdated", ""))
      if selected is None or (dt and selected_dt and dt > selected_dt) or (dt and not selected_dt):
        selected = res
        selected_dt = dt
        logger.debug("Selected ClinicalImpression id=%s at=%s", res.get("id"), selected_dt)

    if not selected:
      raise types.FunctionCallError(
          code="NOT_FOUND",
          message="No se encontró ClinicalImpression de áreas afectadas reciente",
      )

    # Extraer encounter_id y áreas
    enc_ref = (selected.get("encounter", {}) or {}).get("reference", "")
    enc_id = enc_ref.replace("Encounter/", "")
    areas = []
    for fnd in selected.get("finding", []) or []:
      cc = fnd.get("itemCodeableConcept", {}) or {}
      txt = cc.get("text")
      if txt:
        areas.append(txt)
    # Fallback: intentar parsear summary separando por comas
    if not areas and selected.get("summary"):
      logger.debug("No areas in findings; falling back to summary parse")
      areas = [s.strip() for s in str(selected.get("summary")).split(",") if s.strip()]

    logger.debug("get_areas_afectadas result: encounter_id=%s areas=%s", enc_id, areas)

    if not areas:
      raise types.FunctionCallError(
          code="NOT_FOUND", message="No se encontraron áreas afectadas en ClinicalImpression"
      )

    return {
      "encounter_id": enc_id,
      "areas": areas,
      "fecha": selected.get("date") or selected.get("meta", {}).get("lastUpdated"),
    }


class GetPresentacionPacienteTool(BaseTool):
  """Resumen breve de la presentación actual del paciente (placeholder).

  En producción consolidará histórico relevante de FHIR (condiciones crónicas,
  últimos laboratorios, signos vitales recientes, alergias y medicamentos).
  """

  def __init__(self):
    super().__init__(
        name="get_presentacion_paciente",
        description=(
            "Construye una presentación sintética del paciente a partir del "
            "historial (FHIR). Por ahora retorna datos dummy."
        ),
    )

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get("patient_id", "")
    return {
      "patient_id": patient_id,
      "condiciones_cronicas": ["Hipertensión esencial", "Migraña sin aura"],
      "medicamentos_activos": [
        {"medicamento": "Losartán 50 mg", "frecuencia": "cada 24 h"},
        {"medicamento": "Paracetamol 500 mg", "a demanda": "dolor leve"}
      ],
      "alergias": [
        {"alergeno": "Penicilina", "reaccion": "exantema", "severidad": "moderada"}
      ],
      "laboratorios_recientes": [
        {"prueba": "HbA1c", "valor": 5.4, "unidad": "%", "fecha": "2024-11-10"},
        {"prueba": "Colesterol total", "valor": 180, "unidad": "mg/dL", "fecha": "2024-11-10"}
      ],
      "signos_vitales_recientes": {
        "PA": "124/78 mmHg",
        "FC": "72 lpm",
        "FR": "16 rpm",
        "Temp": "36.7 C",
        "IMC": 24.1
      }
    }


class GetResumenHistorialMedicoTool(BaseTool):
  """Genera un resumen clínico del historial del paciente (placeholder).

  En producción agregará recursos FHIR; por ahora devuelve un resumen textual
  con secciones clave.
  """

  def __init__(self):
    super().__init__(
        name="get_resumen_historial_medico",
        description=(
            "Resumen de antecedentes personales, familiares, alergias, "
            "medicamentos y eventos relevantes. (Dummy)"
        ),
    )

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get("patient_id", "")
    resumen = (
      "Paciente con HTA bien controlada y migraña episódica. Sin DM. "
      "Alergia conocida a penicilina. Últimos controles dentro de parámetros."
    )
    return {
      "patient_id": patient_id,
      "resumen": resumen,
      "secciones": {
        "antecedentes_personales": ["Hipertensión esencial (2019)", "Migraña (2018)"],
        "antecedentes_familiares": ["Madre con DM2", "Padre con ECV a los 65"],
        "alergias": ["Penicilina (exantema)"],
        "medicamentos": ["Losartán 50 mg/día", "Paracetamol 500 mg si dolor"],
        "eventos_relevantes": ["Cefalea recurrente en el último mes"],
      }
    }


class ScanDatosEspecificosTool(BaseTool):
  """Barre/consulta datos clínicos específicos por concepto (placeholder).

  Permite solicitar conceptos clínicos concretos (p.ej., "tabaquismo", "embarazo",
  "último LDL"). En producción mapeará conceptos a recursos FHIR.
  """

  def __init__(self):
    super().__init__(
        name="scan_datos_especificos",
        description=(
            "Busca uno o más conceptos clínicos puntuales en el historial del paciente. "
            "Argumentos: patient (id) y conceptos (lista de strings). (Dummy)"
        ),
    )

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    conceptos = args.get("conceptos", []) or []
    results = []
    for c in conceptos[:10]:
      results.append({
        "concepto": c,
        "resultado": "No concluyente en placeholder",
        "fuente": "dummy",
        "confianza": 0.5,
      })
    if not results:
      results = [{
        "concepto": "(ninguno)",
        "resultado": "Sin conceptos solicitados",
        "fuente": "dummy",
        "confianza": 0.0,
      }]
    return results 


class ScoreRiesgoTool(BaseTool):
  """Calcula score de riesgo determinístico a partir de parámetros clínicos.

  Implementaciones iniciales:
  - IMC: busca Observation por code=IMC y toma el último por meta.lastUpdated;
    extrae valueQuantity.value o component.valueString y calcula el score desde YAML.
  """

  def __init__(self):
    super().__init__(
        name="score_riesgo",
        description=(
            "Calcula un score de riesgo a partir de parámetros FHIR (p.ej., IMC). "
            "Retorna valores individuales y sus puntajes según tabla configurable."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None
    # Carga configuración YAML
    self._cfg = None
    try:
      cfg_path = Path(__file__).with_name('score_config.yaml')
      if cfg_path.exists():
        self._cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
    except Exception:
      self._cfg = {}

  def _ensure(self):
    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

  def _score_by_ranges(self, value: float, ranges: list[dict]) -> Optional[int]:
    for r in ranges:
      min_v = r.get('min')
      max_v = r.get('max')
      if min_v is not None and max_v is not None:
        if value >= float(min_v) and value <= float(max_v):
          return int(r.get('score', 0))
      elif min_v is not None and max_v is None:
        if value >= float(min_v):
          return int(r.get('score', 0))
      elif min_v is None and max_v is not None:
        if value <= float(max_v):
          return int(r.get('score', 0))
    return None

  def _parse_imc_value(self, obs: dict) -> Optional[float]:
    # Prefer valueQuantity.value
    vq = obs.get('valueQuantity') or {}
    if 'value' in vq:
      try:
        return float(vq.get('value'))
      except Exception:
        pass
    # Fallback: component[0].valueString like "25.170000 kg/m2"
    comps = obs.get('component') or []
    for c in comps:
      vs = c.get('valueString')
      if isinstance(vs, str) and vs.strip():
        try:
          num = vs.strip().split()[0]
          return float(num)
        except Exception:
          continue
    return None

  async def _fetch_latest_observation_by_code(self, patient_id: str, code: str) -> Optional[dict]:
    self._ensure()
    logger.debug("score_riesgo.fetch_obs: patient=%s code=%s base_url=%s", patient_id, code, self._base_url)
    params = {"patient": patient_id, "code": code}
    resp = self._session.get(
        f"{self._base_url}/Observation",
        params=params,
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    logger.debug("score_riesgo.fetch_obs: status=%s", getattr(resp, 'status_code', None))
    if resp.status_code != 200:
      return None
    entries = resp.json().get('entry', [])
    logger.debug("score_riesgo.fetch_obs: entries=%d", len(entries))
    if not entries:
      return None
    # Elegir el de meta.lastUpdated más reciente
    def _parse_dt_str(d: str) -> float:
      try:
        if d.endswith('Z'):
          d = d.replace('Z', '+00:00')
        return datetime.fromisoformat(d).timestamp()
      except Exception:
        return 0.0
    def _last_updated(entry: dict) -> float:
      res = entry.get('resource', {}) or {}
      meta = res.get('meta', {}) or {}
      return _parse_dt_str(meta.get('lastUpdated', ''))
    entries.sort(key=_last_updated, reverse=True)
    top = entries[0].get('resource', {})
    logger.debug("score_riesgo.fetch_obs: selected id=%s lastUpdated=%s", top.get('id'), (top.get('meta', {}) or {}).get('lastUpdated'))
    return entries[0].get('resource')

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient: str = args.get("patient", "") or args.get("patient_id", "")
    if not patient:
      raise ValueError("Parámetro requerido: patient")
    logger.debug("score_riesgo.run: patient=%s", patient)

    # IMC
    imc_obs = await self._fetch_latest_observation_by_code(patient, "IMC")
    imc_value = self._parse_imc_value(imc_obs) if imc_obs else None
    imc_score = None
    cfg_imc = (self._cfg or {}).get('imc') or {}
    ranges = cfg_imc.get('ranges') or []
    logger.debug("score_riesgo.imc: value=%s ranges=%s", imc_value, ranges)
    if imc_value is not None and ranges:
      imc_score = self._score_by_ranges(imc_value, ranges)
    logger.debug("score_riesgo.imc: score=%s", imc_score)
    imc_obs_id = (imc_obs or {}).get('id') if isinstance(imc_obs, dict) else None

    # Smoking and waist circumference from QuestionnaireResponse (latest by lastUpdated)
    self._ensure()
    # 1) Fetch latest QuestionnaireResponse for subject
    q_resp = self._session.get(
        f"{self._base_url}/QuestionnaireResponse",
        params={"subject": f"Patient/{patient}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    smoking = None
    years_smoking = None
    cigs_per_year = None
    cintura_cm = None
    qr_selected_id = None
    if q_resp.status_code == 200:
      entries = q_resp.json().get('entry', [])
      # pick latest by meta.lastUpdated
      def _parse_dt_str(d: str) -> float:
        try:
          if d.endswith('Z'): d = d.replace('Z', '+00:00')
          return datetime.fromisoformat(d).timestamp()
        except Exception:
          return 0.0
      def _last_updated_qr(e: dict) -> float:
        res = e.get('resource', {}) or {}
        meta = res.get('meta', {}) or {}
        return _parse_dt_str(meta.get('lastUpdated', ''))
      entries.sort(key=_last_updated_qr, reverse=True)
      # Filter by identifier.system == https://www.tca.com if present
      TCA_SYSTEM = "https://www.tca.com"
      resources = [e.get('resource', {}) for e in entries]
      def _has_tca_system(r: dict) -> bool:
        ident = r.get('identifier')
        if isinstance(ident, dict):
          return ident.get('system') == TCA_SYSTEM
        if isinstance(ident, list):
          return any((it or {}).get('system') == TCA_SYSTEM for it in ident)
        return False
      filtered = [r for r in resources if _has_tca_system(r)]
      logger.debug("score_riesgo.qr: total=%d filtered_by_system=%d", len(resources), len(filtered))
      # Order candidates: filtered first (newest first), then the rest (newest first)
      filtered.sort(key=lambda r: _parse_dt_str(((r.get('meta', {}) or {}).get('lastUpdated', ''))), reverse=True)
      rest = [r for r in resources if r not in filtered]
      rest.sort(key=lambda r: _parse_dt_str(((r.get('meta', {}) or {}).get('lastUpdated', ''))), reverse=True)
      candidates = filtered + rest
      for qr in candidates:
        ident = qr.get('identifier')
        systems = []
        if isinstance(ident, dict):
          systems = [ident.get('system')]
        elif isinstance(ident, list):
          systems = [(i or {}).get('system') for i in ident]
        logger.debug(
          "score_riesgo.qr.try: id=%s status=%s lastUpdated=%s systems=%s",
          qr.get('id'), qr.get('status'), (qr.get('meta', {}) or {}).get('lastUpdated'), systems
        )
        found_any = False
        sections = qr.get('item', []) or []
        for section in sections:
          if section.get('linkId') == '10001':
            for question in section.get('item', []) or []:
              if question.get('linkId') == '10012':
                ans = question.get('answer', []) or []
                logger.debug("score_riesgo.qr.10012 raw=%s", json.dumps(ans, ensure_ascii=False))
                if ans and 'valueBoolean' in ans[0]:
                  smoking = bool(ans[0]['valueBoolean'])
                  found_any = True
                else:
                  subitems = question.get('item', []) or []
                  present = {si.get('linkId') for si in subitems}
                  if '10013' in present and '10104' in present:
                    smoking = True
                    found_any = True
                  for subq in subitems:
                    if subq.get('linkId') == '10013':
                      for a in subq.get('answer', []) or []:
                        if 'valueString' in a:
                          cigs_per_year = a['valueString']
                          found_any = True
                        if 'valueInteger' in a:
                          cigs_per_year = a['valueInteger']
                          found_any = True
                    if subq.get('linkId') == '10104':
                      for a in subq.get('answer', []) or []:
                        if 'valueInteger' in a:
                          years_smoking = a['valueInteger']
                          found_any = True
              if question.get('linkId') == '10009':
                ans = question.get('answer', []) or []
                logger.debug("score_riesgo.qr.10009 raw=%s", json.dumps(ans, ensure_ascii=False))
                if ans and 'valueInteger' in ans[0]:
                  cintura_cm = int(ans[0]['valueInteger'])
                  logger.debug("score_riesgo.cintura: %s cm (from QR id=%s)", cintura_cm, qr.get('id'))
                  found_any = True
        if found_any:
          logger.debug("score_riesgo.qr.selected_by_content: id=%s dump=%s", qr.get('id'), json.dumps(qr, ensure_ascii=False))
          qr_selected_id = qr.get('id')
          break
      else:
        logger.debug("score_riesgo.qr: no relevant values (cintura/fumar) found across %d QRs", len(candidates))

    # Score cintura por género
    cintura_score = None
    cintura_cfg = (self._cfg or {}).get('cintura_cm') or {}
    # Get gender from GetPatientByIdTool
    genero = None
    try:
      ptool = GetPatientByIdTool()
      pres = await ptool.run_async(args={"patient_id": patient}, tool_context=None)
      genero = (pres or {}).get('genero')
    except Exception:
      pass
    gender_key = 'male' if str(genero).lower().startswith('m') else 'female' if str(genero).lower().startswith('f') else None
    if cintura_cm is not None and gender_key and cintura_cfg.get(gender_key):
      cintura_score = self._score_by_ranges(float(cintura_cm), cintura_cfg[gender_key].get('ranges') or [])
    logger.debug("score_riesgo.cintura: gender=%s value=%s score=%s", gender_key, cintura_cm, cintura_score)

    # Score fumar
    fumar_score = None
    fumar_cfg = (self._cfg or {}).get('fumar') or {}
    if smoking is True:
      fumar_score = int(fumar_cfg.get('current', 3))
    elif smoking is False:
      fumar_score = int(fumar_cfg.get('none', 0))
    logger.debug("score_riesgo.fumar: smoking=%s years=%s cigs_per_year=%s score=%s", smoking, years_smoking, cigs_per_year, fumar_score)

    # Sexo (mujer=0, hombre=1) basado en Patient.gender
    sexo_score = None
    sexo_genero = None
    try:
      g = (genero or '').strip().lower()
      if g.startswith('f'):
        sexo_score = 0
        sexo_genero = 'mujer'
      elif g.startswith('m'):
        sexo_score = 1
        sexo_genero = 'hombre'
      else:
        sexo_genero = genero
    except Exception:
      pass
    logger.debug("score_riesgo.sexo: genero=%s score=%s", genero, sexo_score)

    # Edad y score por edad desde Patient.birthDate
    edad_val = None
    edad_score = None
    try:
      ptool = GetPatientByIdTool()
      pres = await ptool.run_async(args={"patient_id": patient}, tool_context=None)
      birth = (pres or {}).get('fecha_de_nacimiento')
      if birth:
        try:
          # birth en formato YYYY-MM-DD
          by, bm, bd = [int(x) for x in str(birth).split('-')[:3]]
          today = datetime.utcnow().date()
          years = today.year - by - ((today.month, today.day) < (bm, bd))
          edad_val = float(years)
        except Exception:
          pass
    except Exception:
      pass
    edad_cfg = (self._cfg or {}).get('edad') or {}
    edad_ranges = edad_cfg.get('ranges') or []
    if edad_val is not None and edad_ranges:
      edad_score = self._score_by_ranges(edad_val, edad_ranges)
    logger.debug("score_riesgo.edad: value=%s score=%s", edad_val, edad_score)
 
    # Analitos: FPG (glucosa) y HbA1c desde Observation
    analytes_score = None
    fpg_val = None
    fpg_unit = None
    fpg_cat = None
    a1c_val = None
    a1c_unit = None
    a1c_cat = None
    try:
      self._ensure()
      # Buscar observaciones por subject (preferido) y fallback a patient
      def _parse_dt_str(d: str) -> float:
        try:
          if d.endswith('Z'):
            d = d.replace('Z', '+00:00')
          return datetime.fromisoformat(d).timestamp()
        except Exception:
          return 0.0
      def _last_updated_obs(e: dict) -> float:
        res = e.get('resource', {}) or {}
        meta = res.get('meta', {}) or {}
        return _parse_dt_str(meta.get('lastUpdated', '')) or _parse_dt_str(res.get('effectiveDateTime', ''))
      def _norm(s: str) -> str:
        if not isinstance(s, str):
          s = str(s or '')
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.lower().strip()
      # 1) subject
      resp = self._session.get(
        f"{self._base_url}/Observation",
        params={"subject": f"Patient/{patient}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if resp.status_code != 200:
        resp = self._session.get(
          f"{self._base_url}/Observation",
          params={"patient": str(patient).replace('Patient/', '')},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
        )
      entries = resp.json().get('entry', []) if getattr(resp, 'status_code', None) == 200 else []
      logger.debug("score_riesgo.analitos: obs_entries=%d", len(entries))
      # Filtrar por texto en code
      fpg_candidates = []
      a1c_candidates = []
      for e in entries:
        res = e.get('resource', {}) or {}
        code = res.get('code', {}) or {}
        texts = []
        if 'text' in code and code.get('text'):
          texts.append(code.get('text'))
        for c in code.get('coding', []) or []:
          if c.get('display'):
            texts.append(c.get('display'))
          if c.get('code'):
            texts.append(c.get('code'))
        joined = ' '.join(texts)
        nj = _norm(joined)
        if 'glucosa' in nj:
          fpg_candidates.append(e)
        if 'hemoglobina glicosilada' in nj or 'hb a1c' in nj or 'hba1c' in nj:
          a1c_candidates.append(e)
      fpg_candidates.sort(key=_last_updated_obs, reverse=True)
      a1c_candidates.sort(key=_last_updated_obs, reverse=True)
      def _extract_val_unit(res: dict) -> tuple[Optional[float], Optional[str]]:
        vq = res.get('valueQuantity') or {}
        if 'value' in vq:
          try:
            return float(vq.get('value')), vq.get('unit') or vq.get('code')
          except Exception:
            pass
        for comp in (res.get('component') or []):
          vqc = comp.get('valueQuantity') or {}
          if 'value' in vqc:
            try:
              return float(vqc.get('value')), vqc.get('unit') or vqc.get('code')
            except Exception:
              continue
        return None, None
      if fpg_candidates:
        fpg_res = fpg_candidates[0].get('resource', {}) or {}
        fpg_val, fpg_unit = _extract_val_unit(fpg_res)
        logger.debug("score_riesgo.analitos.fpg: id=%s lastUpdated=%s val=%s unit=%s",
          fpg_res.get('id'), (fpg_res.get('meta', {}) or {}).get('lastUpdated'), fpg_val, fpg_unit)
        fpg_obs_id = fpg_res.get('id')
      else:
        fpg_obs_id = None
      if a1c_candidates:
        a1c_res = a1c_candidates[0].get('resource', {}) or {}
        a1c_val, a1c_unit = _extract_val_unit(a1c_res)
        logger.debug("score_riesgo.analitos.hba1c: id=%s lastUpdated=%s val=%s unit=%s",
          a1c_res.get('id'), (a1c_res.get('meta', {}) or {}).get('lastUpdated'), a1c_val, a1c_unit)
        a1c_obs_id = a1c_res.get('id')
      else:
        a1c_obs_id = None
      # Categorizar según config
      a_cfg = (self._cfg or {}).get('analitos') or {}
      g_cfg = a_cfg.get('fpg_mg_dl') or {}
      h_cfg = a_cfg.get('hba1c_pct') or {}
      def _cat_fpg(v: Optional[float]) -> Optional[str]:
        if v is None:
          return None
        if g_cfg and v >= float(g_cfg.get('diabetes_min', 126.0)):
          return 'diabetes'
        if g_cfg and v >= float(g_cfg.get('prediabetes_min', 100.0)) and v <= float(g_cfg.get('prediabetes_max', 125.0)):
          return 'prediabetes'
        if g_cfg and v <= float(g_cfg.get('normal_max', 99.9)):
          return 'normal'
        return None
      def _cat_a1c(v: Optional[float]) -> Optional[str]:
        if v is None:
          return None
        if h_cfg and v >= float(h_cfg.get('diabetes_min', 6.5)):
          return 'diabetes'
        if h_cfg and v >= float(h_cfg.get('prediabetes_min', 5.7)) and v <= float(h_cfg.get('prediabetes_max', 6.4)):
          return 'prediabetes'
        if h_cfg and v <= float(h_cfg.get('normal_max', 5.69)):
          return 'normal'
        return None
      fpg_cat = _cat_fpg(fpg_val)
      a1c_cat = _cat_a1c(a1c_val)
      # Score combinado: max de riesgo disponible
      if 'diabetes' in (fpg_cat, a1c_cat):
        analytes_score = 5
      elif 'prediabetes' in (fpg_cat, a1c_cat):
        analytes_score = 3
      elif (fpg_cat == 'normal' and (a1c_cat in ('normal', None))) or (a1c_cat == 'normal' and (fpg_cat in ('normal', None))):
        analytes_score = 0
      logger.debug("score_riesgo.analitos: fpg=%s(%s) a1c=%s(%s) score=%s", fpg_val, fpg_cat, a1c_val, a1c_cat, analytes_score)
    except Exception as e:
      logger.warning("score_riesgo.analitos: error %s", e)
      fpg_obs_id = fpg_obs_id if 'fpg_obs_id' in locals() else None
      a1c_obs_id = a1c_obs_id if 'a1c_obs_id' in locals() else None

    # Triglicéridos (mg/dL): Observation más reciente con 'triglic' en code/display
    trig_val = None
    trig_unit = None
    trig_score = None
    try:
      self._ensure()
      def _parse_dt_str2(d: str) -> float:
        try:
          if d.endswith('Z'):
            d = d.replace('Z', '+00:00')
          return datetime.fromisoformat(d).timestamp()
        except Exception:
          return 0.0
      def _last_updated_obs2(e: dict) -> float:
        res = e.get('resource', {}) or {}
        meta = res.get('meta', {}) or {}
        return _parse_dt_str2(meta.get('lastUpdated', '')) or _parse_dt_str2(res.get('effectiveDateTime', ''))
      def _norm2(s: str) -> str:
        if not isinstance(s, str):
          s = str(s or '')
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.lower().strip()
      resp = self._session.get(
        f"{self._base_url}/Observation",
        params={"subject": f"Patient/{patient}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if resp.status_code != 200:
        resp = self._session.get(
          f"{self._base_url}/Observation",
          params={"patient": str(patient).replace('Patient/', '')},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
        )
      entries = resp.json().get('entry', []) if getattr(resp, 'status_code', None) == 200 else []
      cands = []
      for e in entries:
        res = e.get('resource', {}) or {}
        code = res.get('code', {}) or {}
        texts = []
        if code.get('text'): texts.append(code.get('text'))
        for c in code.get('coding', []) or []:
          if c.get('display'): texts.append(c.get('display'))
          if c.get('code'): texts.append(c.get('code'))
        nj = _norm2(' '.join(texts))
        if 'triglic' in nj:
          cands.append(e)
      cands.sort(key=_last_updated_obs2, reverse=True)
      def _extract_val_unit2(res: dict) -> tuple[Optional[float], Optional[str]]:
        vq = res.get('valueQuantity') or {}
        if 'value' in vq:
          try:
            return float(vq.get('value')), vq.get('unit') or vq.get('code')
          except Exception:
            pass
        for comp in (res.get('component') or []):
          vqc = comp.get('valueQuantity') or {}
          if 'value' in vqc:
            try:
              return float(vqc.get('value')), vqc.get('unit') or vqc.get('code')
            except Exception:
              continue
        return None, None
      if cands:
        res0 = cands[0].get('resource', {}) or {}
        trig_val, trig_unit = _extract_val_unit2(res0)
        logger.debug("score_riesgo.trigliceridos: id=%s lastUpdated=%s val=%s unit=%s",
          res0.get('id'), (res0.get('meta', {}) or {}).get('lastUpdated'), trig_val, trig_unit)
        trig_obs_id = res0.get('id')
      else:
        trig_obs_id = None
      cfg_trig = (self._cfg or {}).get('trigliceridos_mg_dl') or {}
      if trig_val is not None and cfg_trig:
        trig_score = self._score_by_ranges(float(trig_val), cfg_trig.get('ranges') or [])
      logger.debug("score_riesgo.trigliceridos: value=%s score=%s", trig_val, trig_score)
    except Exception as e:
      logger.warning("score_riesgo.trigliceridos: error %s", e)
      trig_obs_id = trig_obs_id if 'trig_obs_id' in locals() else None

    # HDL (mg/dL): Observation más reciente con 'hdl' o 'alta densidad' en code/display
    hdl_val = None
    hdl_unit = None
    hdl_score = None
    try:
      self._ensure()
      def _parse_dt_str3(d: str) -> float:
        try:
          if d.endswith('Z'):
            d = d.replace('Z', '+00:00')
          return datetime.fromisoformat(d).timestamp()
        except Exception:
          return 0.0
      def _last_updated_obs3(e: dict) -> float:
        res = e.get('resource', {}) or {}
        meta = res.get('meta', {}) or {}
        return _parse_dt_str3(meta.get('lastUpdated', '')) or _parse_dt_str3(res.get('effectiveDateTime', ''))
      def _norm3(s: str) -> str:
        if not isinstance(s, str):
          s = str(s or '')
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.lower().strip()
      resp = self._session.get(
        f"{self._base_url}/Observation",
        params={"subject": f"Patient/{patient}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if resp.status_code != 200:
        resp = self._session.get(
          f"{self._base_url}/Observation",
          params={"patient": str(patient).replace('Patient/', '')},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
        )
      entries = resp.json().get('entry', []) if getattr(resp, 'status_code', None) == 200 else []
      cands = []
      for e in entries:
        res = e.get('resource', {}) or {}
        code = res.get('code', {}) or {}
        texts = []
        if code.get('text'): texts.append(code.get('text'))
        for c in code.get('coding', []) or []:
          if c.get('display'): texts.append(c.get('display'))
          if c.get('code'): texts.append(c.get('code'))
        nj = _norm3(' '.join(texts))
        if 'hdl' in nj or 'alta densidad' in nj:
          cands.append(e)
      cands.sort(key=_last_updated_obs3, reverse=True)
      def _extract_val_unit3(res: dict) -> tuple[Optional[float], Optional[str]]:
        vq = res.get('valueQuantity') or {}
        if 'value' in vq:
          try:
            return float(vq.get('value')), vq.get('unit') or vq.get('code')
          except Exception:
            pass
        for comp in (res.get('component') or []):
          vqc = comp.get('valueQuantity') or {}
          if 'value' in vqc:
            try:
              return float(vqc.get('value')), vqc.get('unit') or vqc.get('code')
            except Exception:
              continue
        return None, None
      if cands:
        res0 = cands[0].get('resource', {}) or {}
        hdl_val, hdl_unit = _extract_val_unit3(res0)
        logger.debug("score_riesgo.hdl: id=%s lastUpdated=%s val=%s unit=%s",
          res0.get('id'), (res0.get('meta', {}) or {}).get('lastUpdated'), hdl_val, hdl_unit)
        hdl_obs_id = res0.get('id')
      else:
        hdl_obs_id = None
      cfg_hdl = (self._cfg or {}).get('hdl_mg_dl') or {}
      if hdl_val is not None and cfg_hdl and gender_key and cfg_hdl.get(gender_key):
        hdl_score = self._score_by_ranges(float(hdl_val), cfg_hdl[gender_key].get('ranges') or [])
      logger.debug("score_riesgo.hdl: value=%s gender_key=%s score=%s", hdl_val, gender_key, hdl_score)
    except Exception as e:
      logger.warning("score_riesgo.hdl: error %s", e)
      hdl_obs_id = hdl_obs_id if 'hdl_obs_id' in locals() else None

    # Antecedentes familiares (FamilyMemberHistory): DM2 o HTA esencial en Madre/Padre
    fam_cfg = (self._cfg or {}).get('antecedentes_familiares') or {}
    risk_terms = fam_cfg.get('risk_conditions') or [
      'diabetes mellitus tipo 2',
      'hipertensión esencial',
    ]
    first_degree_labels = {s.lower(): True for s in (fam_cfg.get('relationships') or ['madre', 'padre'])}
    score_if_any = int(fam_cfg.get('score_if_any', 2))
    score_if_none = int(fam_cfg.get('score_if_none', 0))
    fam_score = None
    fam_matches: list[dict[str, str]] = []
    try:
      self._ensure()
      fmh_resp = self._session.get(
        f"{self._base_url}/FamilyMemberHistory",
        params={"patient": str(patient).replace('Patient/', '')},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if fmh_resp.status_code == 200:
        entries = fmh_resp.json().get('entry', [])
        logger.debug("score_riesgo.famhist: entries=%d", len(entries))
        def _norm(s: str) -> str:
          return ' '.join((s or '').strip().split()).lower()
        for entry in entries:
          res = (entry or {}).get('resource', {})
          if res.get('status') != 'completed':
            continue
          rel_obj = res.get('relationship', {}) or {}
          rel_txt = rel_obj.get('text')
          if not rel_txt and rel_obj.get('coding'):
            rel_txt = (rel_obj['coding'][0] or {}).get('display')
          rel_n = _norm(rel_txt or '')
          if rel_n not in first_degree_labels:
            continue
          for cond in res.get('condition', []) or []:
            code = (cond.get('code', {}) or {})
            disp = None
            if code.get('coding'):
              disp = (code['coding'][0] or {}).get('display') or (code['coding'][0] or {}).get('code')
            if not disp:
              disp = code.get('text')
            disp_n = _norm(disp or '')
            for term in risk_terms:
              if term and _norm(term) in disp_n:
                fam_matches.append({"relacion": rel_txt or '', "condicion": disp or ''})
                break
        fam_score = score_if_any if fam_matches else score_if_none
        logger.debug("score_riesgo.famhist: matches=%d score=%s", len(fam_matches), fam_score)
      else:
        logger.debug("score_riesgo.famhist: request failed status=%s", getattr(fmh_resp, 'status_code', None))
    except Exception as e:
      logger.warning("score_riesgo.famhist: error %s", e)

    # Agregación global de riesgo (porcentaje y categoría)
    def _max_from_ranges(ranges: list[dict]) -> int:
      try:
        return max(int(r.get('score', 0)) for r in (ranges or [])) if ranges else 0
      except Exception:
        return 0
    total_obt = 0
    total_pos = 0
    # IMC
    if imc_score is not None:
      total_obt += int(imc_score or 0)
      total_pos += _max_from_ranges(((self._cfg or {}).get('imc') or {}).get('ranges') or [])
    # Edad
    if edad_score is not None:
      total_obt += int(edad_score or 0)
      total_pos += _max_from_ranges(((self._cfg or {}).get('edad') or {}).get('ranges') or [])
    # Cintura (usar genero)
    if cintura_score is not None and gender_key and ((self._cfg or {}).get('cintura_cm') or {}).get(gender_key):
      total_obt += int(cintura_score or 0)
      total_pos += _max_from_ranges(((self._cfg or {}).get('cintura_cm') or {}).get(gender_key, {}).get('ranges') or [])
    # Fumar
    if fumar_score is not None:
      total_obt += int(fumar_score or 0)
      fumar_vals = [int(v) for v in ((self._cfg or {}).get('fumar') or {}).values() if isinstance(v, (int, float))]
      total_pos += (max(fumar_vals) if fumar_vals else 0)
    # Antecedentes familiares
    if fam_score is not None:
      total_obt += int(fam_score or 0)
      total_pos += int((fam_cfg.get('score_if_any', 2)))
    # Analitos (FPG/HbA1c): máximo 5 por definición
    if analytes_score is not None:
      total_obt += int(analytes_score or 0)
      total_pos += 5
    # Triglicéridos
    if trig_score is not None:
      total_obt += int(trig_score or 0)
      total_pos += _max_from_ranges(((self._cfg or {}).get('trigliceridos_mg_dl') or {}).get('ranges') or [])
    # HDL (por género)
    if hdl_score is not None and gender_key and ((self._cfg or {}).get('hdl_mg_dl') or {}).get(gender_key):
      total_obt += int(hdl_score or 0)
      total_pos += _max_from_ranges(((self._cfg or {}).get('hdl_mg_dl') or {}).get(gender_key, {}).get('ranges') or [])
    # Sexo
    if sexo_score is not None:
      total_obt += int(sexo_score or 0)
      total_pos += 1
    riesgo_pct = None
    riesgo_cat = None
    if total_pos > 0:
      riesgo_pct = round((total_obt / float(total_pos)) * 100.0, 2)
      if riesgo_pct < 20.0:
        riesgo_cat = 'bajo'
      elif riesgo_pct < 30.0:
        riesgo_cat = 'medio'
      else:
        riesgo_cat = 'alto'
    logger.debug("score_riesgo.global: obt=%s pos=%s pct=%s cat=%s", total_obt, total_pos, riesgo_pct, riesgo_cat)

    result = {
      "patient_id": patient,
      "imc": {
        "valor": imc_value,
        "unidad": "kg/m2" if imc_value is not None else None,
        "score": imc_score,
      },
      "edad": {
        "valor": (int(edad_val) if isinstance(edad_val, float) else edad_val),
        "score": edad_score,
      },
      "sexo": {
        "genero": sexo_genero if sexo_genero is not None else genero,
        "score": sexo_score,
      },
      "analitos": {
        "fpg": {"valor": fpg_val, "unidad": fpg_unit, "categoria": fpg_cat},
        "hba1c": {"valor": a1c_val, "unidad": a1c_unit, "categoria": a1c_cat},
        "score": analytes_score,
      },
      "trigliceridos": {"valor": trig_val, "unidad": trig_unit, "score": trig_score},
      "hdl": {"valor": hdl_val, "unidad": hdl_unit, "score": hdl_score},
      "cintura_cm": {
        "valor": cintura_cm,
        "score": cintura_score,
        "genero": genero,
      },
      "fumar": {
        "estado": ("actual" if smoking else ("no" if smoking is False else None)),
        "anios_fumando": years_smoking,
        "cigarros_por_anio": cigs_per_year,
        "score": fumar_score,
      },
      "antecedentes_familiares": {
        "primer_grado_riesgo": fam_score,
        "coincidencias": fam_matches,
      },
      "riesgo_global": {
        "puntos": {"obtenidos": total_obt, "maximos": total_pos, "porcentaje": riesgo_pct},
        "categoria": riesgo_cat,
      },
      "evidence": {
        "questionnaire_response_id": qr_selected_id,
        "observations": {
          "imc": imc_obs_id,
          "fpg": fpg_obs_id,
          "hba1c": a1c_obs_id,
          "trigliceridos": trig_obs_id,
          "hdl": hdl_obs_id,
        },
      },
    }
    return result 


class CreateEncounterTool(BaseTool):
  """Crea un Encounter básico en FHIR para un paciente dado.

  Cuerpo creado (mínimo):
    - resourceType: Encounter
    - status: in-progress
    - class: Coding VR (virtual)
    - subject: reference Patient/{id}
    - extension: anamnesis-agent/created-datetime con fecha actual UTC
    - identifier: system propio con session_id

  Args:
    patient_id (str): ID del paciente (con o sin prefijo "Patient/").
    session_id (str, opcional): ID de sesión a correlacionar en identifier.
    created_datetime (str, opcional): ISO8601 para valueDateTime. Si no se provee, se usa ahora en UTC.
  Retorna:
    dict: { "encounter_id": str, "status": str }
  """

  def __init__(self):
    super().__init__(
        name="create_encounter",
        description=(
            "Crea un Encounter 'in-progress' con class=VR (virtual) y subject=Patient/{id}."
        ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get("patient_id") or args.get("patient") or ""
    if not patient_id:
      raise ValueError("Parámetro requerido: patient_id")

    # Normalizar a ID sin prefijo
    pid = str(patient_id).strip().replace("Patient/", "")

    # Fecha de creación (UTC)
    created_dt: str = args.get("created_datetime") or (datetime.utcnow().isoformat() + "Z")
    session_id: Optional[str] = args.get("session_id")

    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

    identifier = []
    if session_id:
      identifier = [
        {
          "system": "http://goes.gob.sv/fhir/identifiers/session",
          "value": session_id,
        }
      ]

    body = {
      "resourceType": "Encounter",
      "status": "in-progress",
      "class": {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": "VR",
        "display": "virtual",
      },
      "subject": {
        "reference": f"Patient/{pid}",
      },
      "extension": [
        {
          "url": "http://goes.gob.sv/fhir/extensions/anamnesis-agent/created-datetime",
          "valueDateTime": created_dt,
        }
      ],
    }
    if identifier:
      body["identifier"] = identifier

    headers = {"Content-Type": "application/fhir+json;charset=utf-8"}
    if session_id:
      headers["If-None-Exist"] = "identifier=http://goes.gob.sv/fhir/identifiers/session|" + session_id

    resp = self._session.post(f"{self._base_url}/Encounter", headers=headers, json=body)

    if resp.status_code not in (200, 201):
      raise types.FunctionCallError(
          code="FAILED_PRECONDITION",
          message=f"No se pudo crear Encounter (status {resp.status_code}): {resp.text}",
      )

    resource = resp.json() if resp.content else {}
    enc_id = resource.get("id") or (resource.get("entry", [{}])[0].get("resource", {}) if isinstance(resource.get("entry"), list) else {}).get("id")

    return {
      "encounter_id": enc_id,
      "status": resource.get("status", "in-progress"),
    }


class CreateRiskAssessmentTool(BaseTool):
  """Crea un RiskAssessment referenciando recursos base y el Encounter de la sesión.

  Args:
    patient_id (str): ID del paciente
    encounter_id (str, opcional): Encounter existente. Si no se pasa, se puede resolver por session_id.
    session_id (str, opcional): Si no se pasa encounter_id, intenta resolver Encounter por identifier=session_id.
    outcome (str): "low" | "medium" | "high"
    rationale (str): explicación en prosa
    occurrence_datetime (str, opcional): ISO8601; por defecto ahora en UTC

  Comportamiento:
    - Recolecta IDs de evidencia (QuestionnaireResponse y Observations relevantes) para basis
    - Construye y POSTea un RiskAssessment
  """

  def __init__(self):
    super().__init__(
      name="create_risk_assessment",
      description=(
        "Crea un RiskAssessment enlazado al Encounter y con basis a Observations/QuestionnaireResponse."
      ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  def _ensure(self):
    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

  def _pick_latest_qr_id(self, patient_id: str) -> Optional[str]:
    r = self._session.get(
      f"{self._base_url}/QuestionnaireResponse",
      params={"subject": f"Patient/{patient_id}"},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if r.status_code != 200:
      return None
    entries = r.json().get("entry", [])
    best_id = None
    best_ts = 0.0
    for e in entries:
      res = (e or {}).get("resource", {}) or {}
      rid = res.get("id")
      ts = 0.0
      try:
        dt = (res.get("meta", {}) or {}).get("lastUpdated") or res.get("authored")
        if dt:
          if str(dt).endswith("Z"): dt = str(dt).replace("Z", "+00:00")
          ts = datetime.fromisoformat(str(dt)).timestamp()
      except Exception:
        ts = 0.0
      if rid and ts >= best_ts:
        best_ts = ts
        best_id = rid
    return best_id

  def _pick_latest_obs_ids(self, patient_id: str) -> dict:
    # Busca Observations por subject y filtra por textos comunes
    def _get_entries():
      r = self._session.get(
        f"{self._base_url}/Observation",
        params={"subject": f"Patient/{patient_id}"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if r.status_code != 200:
        r = self._session.get(
          f"{self._base_url}/Observation",
          params={"patient": patient_id},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
        )
      return r.json().get("entry", []) if getattr(r, "status_code", None) == 200 else []

    entries = _get_entries()

    def _norm(s: str) -> str:
      try:
        s = unicodedata.normalize('NFD', s or '')
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.lower().strip()
      except Exception:
        return str(s or '').lower()

    def _last_updated(e: dict) -> float:
      res = (e or {}).get('resource', {}) or {}
      dt = (res.get('meta', {}) or {}).get('lastUpdated') or res.get('effectiveDateTime')
      try:
        if not dt: return 0.0
        if str(dt).endswith('Z'): dt = str(dt).replace('Z', '+00:00')
        return datetime.fromisoformat(str(dt)).timestamp()
      except Exception:
        return 0.0

    buckets = {
      'imc': [],
      'fpg': [],
      'a1c': [],
      'trig': [],
      'hdl': [],
    }
    for e in entries:
      res = (e or {}).get('resource', {}) or {}
      code = (res.get('code', {}) or {})
      texts = []
      if code.get('text'): texts.append(code.get('text'))
      for c in (code.get('coding') or []):
        if c.get('display'): texts.append(c.get('display'))
        if c.get('code'): texts.append(c.get('code'))
      nj = _norm(' '.join(texts))
      rid = res.get('id')
      if not rid: continue
      if 'imc' in nj:
        buckets['imc'].append((e, _last_updated(e)))
      if 'glucosa' in nj or 'fpg' in nj:
        buckets['fpg'].append((e, _last_updated(e)))
      if 'hb a1c' in nj or 'hba1c' in nj or 'hemoglobina glicosilada' in nj:
        buckets['a1c'].append((e, _last_updated(e)))
      if 'triglic' in nj:
        buckets['trig'].append((e, _last_updated(e)))
      if 'hdl' in nj or 'alta densidad' in nj:
        buckets['hdl'].append((e, _last_updated(e)))

    result: dict[str, Optional[str]] = {k: None for k in buckets.keys()}
    for k, arr in buckets.items():
      if arr:
        arr.sort(key=lambda t: t[1], reverse=True)
        result[k] = ((arr[0][0] or {}).get('resource', {}) or {}).get('id')

    # Intento adicional: IMC por code=IMC
    if not result.get('imc'):
      r = self._session.get(
        f"{self._base_url}/Observation",
        params={"patient": patient_id, "code": "IMC"},
        headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      )
      if r.status_code == 200:
        es = r.json().get('entry', [])
        es.sort(key=_last_updated, reverse=True)
        if es:
          result['imc'] = ((es[0] or {}).get('resource', {}) or {}).get('id')

    return result

  def _resolve_encounter_id_by_session(self, session_id: str) -> Optional[str]:
    r = self._session.get(
      f"{self._base_url}/Encounter",
      params={"identifier": "http://goes.gob.sv/fhir/identifiers/session|" + session_id},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if r.status_code != 200:
      return None
    entries = r.json().get('entry', [])
    if not entries:
      return None
    return ((entries[0] or {}).get('resource', {}) or {}).get('id')

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get('patient_id') or ''
    if not patient_id:
      raise ValueError('Parámetro requerido: patient_id')
    encounter_id: Optional[str] = args.get('encounter_id')
    session_id: Optional[str] = args.get('session_id')
    outcome: str = args.get('outcome') or ''
    rationale: str = args.get('rationale') or ''
    occurrence_dt: str = args.get('occurrence_datetime') or (datetime.utcnow().isoformat() + 'Z')
    evidence: Optional[dict] = args.get('evidence')

    if not outcome:
      raise ValueError('Parámetro requerido: outcome')

    self._ensure()

    # Resolver Encounter si es necesario
    if not encounter_id and session_id:
      encounter_id = self._resolve_encounter_id_by_session(session_id)

    basis_refs = []
    # Evidence: preferir evidencia explícita si se pasa; si no, resolver automáticamente
    if isinstance(evidence, dict):
      qr_id = evidence.get('questionnaire_response_id')
      if qr_id:
        basis_refs.append({"reference": f"QuestionnaireResponse/{qr_id}"})
      obs_map = (evidence.get('observations') or {}) if isinstance(evidence.get('observations'), dict) else {}
      for oid in [obs_map.get('imc'), obs_map.get('fpg'), obs_map.get('hba1c'), obs_map.get('trigliceridos'), obs_map.get('hdl')]:
        if oid:
          basis_refs.append({"reference": f"Observation/{oid}"})
    else:
      # Fallback automático
      qr_id = self._pick_latest_qr_id(patient_id)
      if qr_id:
        basis_refs.append({"reference": f"QuestionnaireResponse/{qr_id}"})
      obs_ids = self._pick_latest_obs_ids(patient_id)
      for key in ["imc", "fpg", "a1c", "trig", "hdl"]:
        oid = obs_ids.get(key)
        if oid:
          basis_refs.append({"reference": f"Observation/{oid}"})

    # Construir RiskAssessment
    body = {
      "resourceType": "RiskAssessment",
      "status": "final",
      "subject": {"reference": f"Patient/{patient_id}"},
      "occurrenceDateTime": occurrence_dt,
      "method": {
        "coding": [
          {"system": "http://goes.gob.sv/fhir/codeable-concept/risk-assessment-method", "code": "early-warning"}
        ]
      },
      "prediction": [
        {
          "outcome": {
            "coding": [
              {"system": "http://goes.gob.sv/fhir/codeable-concept/risk-assessment-outcome", "code": outcome}
            ]
          },
          "rationale": rationale,
        }
      ],
    }
    if encounter_id:
      body["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    if basis_refs:
      body["basis"] = basis_refs

    headers = {"Content-Type": "application/fhir+json;charset=utf-8"}
    resp = self._session.post(f"{self._base_url}/RiskAssessment", headers=headers, json=body)
    if resp.status_code not in (200, 201):
      raise types.FunctionCallError(
        code="FAILED_PRECONDITION",
        message=f"No se pudo crear RiskAssessment (status {resp.status_code}): {resp.text}",
      )

    res = resp.json() if resp.content else {}
    return {
      "risk_assessment_id": res.get('id'),
      "outcome": outcome,
    }


class CreateClinicalImpressionTool(BaseTool):
  """Crea un ClinicalImpression de anamnesis enlazado a Encounter y Patient.

  Args:
    patient_id (str): ID del paciente
    encounter_id (str, opcional): Encounter a relacionar. Si falta y hay session_id, se resuelve por identifier.
    session_id (str, opcional): Para resolver encounter por identifier de sesión.
    summary (str): Resumen clínicamente relevante de la anamnesis
    date (str, opcional): ISO8601; por defecto ahora en UTC

  Retorna:
    dict: { clinical_impression_id: str }
  """

  def __init__(self):
    super().__init__(
      name="create_clinical_impression",
      description=(
        "Crea ClinicalImpression (anamnesis) con protocolo del agente, status completed, subject y encounter."
      ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  def _ensure(self):
    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

  def _resolve_encounter_id_by_session(self, session_id: str) -> Optional[str]:
    r = self._session.get(
      f"{self._base_url}/Encounter",
      params={"identifier": "http://goes.gob.sv/fhir/identifiers/session|" + session_id},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if r.status_code != 200:
      return None
    entries = r.json().get('entry', [])
    if not entries:
      return None
    return ((entries[0] or {}).get('resource', {}) or {}).get('id')

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    patient_id: str = args.get('patient_id') or ''
    if not patient_id:
      raise ValueError('Parámetro requerido: patient_id')
    encounter_id: Optional[str] = args.get('encounter_id')
    session_id: Optional[str] = args.get('session_id')
    summary: str = args.get('summary') or ''
    date_str: str = args.get('date') or (datetime.utcnow().isoformat() + 'Z')

    if not summary:
      raise ValueError('Parámetro requerido: summary')

    self._ensure()
    logger.info("CI_CREATE start patient_id=%s encounter_in=%s session_id=%s", patient_id, encounter_id, session_id)

    if not encounter_id and session_id:
      encounter_id = self._resolve_encounter_id_by_session(session_id)
    logger.info("CI_CREATE resolved encounter_id=%s via session", encounter_id)

    body = {
      "resourceType": "ClinicalImpression",
      "status": "completed",
      "subject": {"reference": f"Patient/{patient_id}"},
      "protocol": [
        "http://goes.gob.sv/fhir/protocols/anamnesis-agent/anamnesis",
      ],
      "summary": summary,
      "date": date_str,
    }
    if encounter_id:
      body["encounter"] = {"reference": f"Encounter/{encounter_id}"}

    headers = {"Content-Type": "application/fhir+json;charset=utf-8"}
    try:
      logger.debug("CI_CREATE body=%s", json.dumps({**body, "summary": (summary[:200] + ('…' if len(summary) > 200 else ''))}, ensure_ascii=False))
    except Exception:
      pass
    resp = self._session.post(f"{self._base_url}/ClinicalImpression", headers=headers, json=body)
    if resp.status_code not in (200, 201):
      raise types.FunctionCallError(
        code="FAILED_PRECONDITION",
        message=f"No se pudo crear ClinicalImpression (status {resp.status_code}): {resp.text}",
      )
    data = resp.json() if resp.content else {}
    logger.info("CI_CREATE ok id=%s status=%s", data.get('id'), resp.status_code)
    return {"clinical_impression_id": data.get('id')}


class UpdateEncounterStatusTool(BaseTool):
  """Actualiza el status de un Encounter (p.ej., completed).

  Args:
    encounter_id (str, opcional): ID directo del encounter
    session_id (str, opcional): Alternativa para resolver encounter por identifier de sesión
    status (str): nuevo estado, p.ej. "completed"
  """

  def __init__(self):
    super().__init__(
      name="update_encounter_status",
      description=(
        "Actualiza el campo status de un Encounter existente usando PUT."
      ),
    )
    self._session: Optional[AuthorizedSession] = None
    self._base_url: Optional[str] = None

  def _ensure(self):
    if not self._session:
      self._session = _new_authorized_session()
    if not self._base_url:
      self._base_url = _build_fhir_store_base_url()

  def _resolve_encounter_id_by_session(self, session_id: str) -> Optional[str]:
    r = self._session.get(
      f"{self._base_url}/Encounter",
      params={"identifier": "http://goes.gob.sv/fhir/identifiers/session|" + session_id},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if r.status_code != 200:
      return None
    entries = r.json().get('entry', [])
    if not entries:
      return None
    return ((entries[0] or {}).get('resource', {}) or {}).get('id')

  async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
    encounter_id: Optional[str] = args.get('encounter_id')
    session_id: Optional[str] = args.get('session_id')
    status: str = args.get('status') or ''

    if not status:
      raise ValueError('Parámetro requerido: status')

    self._ensure()
    logger.info("ENCOUNTER_UPDATE start encounter_in=%s session_id=%s status=%s", encounter_id, session_id, status)

    if not encounter_id and session_id:
      encounter_id = self._resolve_encounter_id_by_session(session_id)
    logger.info("ENCOUNTER_UPDATE resolved encounter_id=%s", encounter_id)
    if not encounter_id:
      raise ValueError('No se pudo resolver encounter_id')

    # Obtener recurso existente
    get_r = self._session.get(
      f"{self._base_url}/Encounter/{encounter_id}",
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    if get_r.status_code != 200:
      raise types.FunctionCallError(code="NOT_FOUND", message="Encounter no encontrado para actualizar")
    res = get_r.json() or {}
    res['status'] = status

    put_r = self._session.put(
      f"{self._base_url}/Encounter/{encounter_id}",
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
      json=res,
    )
    if put_r.status_code not in (200, 201):
      raise types.FunctionCallError(code="FAILED_PRECONDITION", message=f"No se pudo actualizar Encounter: {put_r.text}")

    logger.info("ENCOUNTER_UPDATE ok id=%s status=%s", encounter_id, status)
    return {"encounter_id": encounter_id, "status": status}