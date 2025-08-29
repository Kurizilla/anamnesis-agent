import os
from google.adk import Agent
from .fhir_tools import (
  GetMotivoConsultaTool,
  GetAreasAfectadasTool,
  GetPatientByIdTool,
  GetObservacionesTool,
  GetConditionsTool,
  GetAllergiesTool,
  GetMedicationRequestsTool,
  GetFamilyMemberHistoryTool,
  GetVariablesPrevencionTool,
  GetPatologicosPersonalesTool,
  GetDeterminantesSocioambientalesTool,
  GetDisponibilidadRecursosTool,
  GetPresentacionPacienteTool,
  GetResumenHistorialMedicoTool,
  ScanDatosEspecificosTool,
  CreateEncounterTool,
  CreateRiskAssessmentTool,
  CreateClinicalImpressionTool,
  UpdateEncounterStatusTool,
)

_ANAMNESIS_INSTRUCTION = (
  """
Eres "Clini-Assistant (Anamnesis)", un asistente de IA que conduce la entrevista clínica basada en los motivos de consulta actuales. Tu objetivo es caracterizar el problema principal y construir una anamnesis clara y completa.

Inicio:
- Si tienes patient/patient_id, recupera motivos (get_motivo_consulta) y saluda mencionándolos. Si no, pide amablemente el ID del paciente para continuar.

Flujo sugerido (ajústalo al caso):
- Motivo de consulta; cronología (inicio, duración, evolución), factores agravantes/atenuantes, síntomas acompañantes, red de apoyo, hallazgos objetivos disponibles.
- Antecedentes pertinentes al problema (toma decisiones de qué profundizar según el motivo), medicación y alergias relevantes.
- Resume y confirma con el/la paciente.

Cierre automático de la consulta:
1) Genera un resumen de la anamnesis en prosa y registra ClinicalImpression (create_clinical_impression) con patient_id y session_id.
2) Actualiza el Encounter a completed (update_encounter_status).
- Responde siempre en español, con empatía y claridad.
"""
)

anamnesis_agent = Agent(
  model=os.getenv('ANAMNESIS_AGENT_MODEL', 'gemini-2.5-flash'),
  name='clini_assistant_anamnesis',
  description='Agente de entrevista clínica (anamnesis) centrado en motivos de consulta',
  instruction=_ANAMNESIS_INSTRUCTION,
  tools=[
    # Cierre/escritura
    CreateClinicalImpressionTool(),
    UpdateEncounterStatusTool(),
    CreateRiskAssessmentTool(),
    CreateEncounterTool(),
    # Consulta enfocada en motivos/antecedentes pertinentes
    GetMotivoConsultaTool(),
    GetAreasAfectadasTool(),
    GetPatientByIdTool(),
    GetObservacionesTool(),
    GetConditionsTool(),
    GetAllergiesTool(),
    GetMedicationRequestsTool(),
    GetFamilyMemberHistoryTool(),
    GetVariablesPrevencionTool(),
    GetPatologicosPersonalesTool(),
    GetDeterminantesSocioambientalesTool(),
    GetDisponibilidadRecursosTool(),
    GetPresentacionPacienteTool(),
    GetResumenHistorialMedicoTool(),
    ScanDatosEspecificosTool(),
  ],
) 