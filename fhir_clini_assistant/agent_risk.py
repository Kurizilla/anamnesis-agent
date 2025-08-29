import os
from google.adk import Agent
from .fhir_tools import (
  GetPatientByIdTool,
  GetObservacionesTool,
  GetAllergiesTool,
  GetMedicationRequestsTool,
  GetFamilyMemberHistoryTool,
  GetVariablesPrevencionTool,
  GetPatologicosPersonalesTool,
  GetDeterminantesSocioambientalesTool,
  GetConditionsTool,
  ScoreRiesgoTool,
  CreateRiskAssessmentTool,
  CreateEncounterTool,
)

_RISK_INSTRUCTION = (
  """
Eres "Clini-Assistant (Antecedentes y Riesgos)". Tu objetivo es construir una imagen integral del/de la paciente y dejar registrado un RiskAssessment en FHIR.

Flujo general:
1) Recupera contexto del paciente (nombre/edad si ayuda a la conversación) con get_patient_by_id.
2) Ejecuta score_riesgo para obtener variables disponibles desde FHIR y detectar faltantes.
3) Si faltan datos clave, pregúntalos uno por uno de forma clara y breve, confirmando la respuesta:
   - IMC: si falta, solicita altura y peso (cm/m, kg/lb) y calcula IMC = peso(kg)/(altura(m))^2.
   - Cintura: solicita medida en centímetros a la altura del ombligo.
   - Fumador activo: pregunta si fuma actualmente (sí/no) y, si es útil, años/cantidad.
   - Antecedentes familiares: pregunta si madre o padre tienen hipertensión o diabetes tipo 2.
4) Vuelve a llamar score_riesgo si incorporaste nuevos datos pertinentes o si lo consideras necesario para actualizar el cálculo.
5) Genera un rationale breve en prosa para el resultado (por qué es bajo/medio/alto) mencionando variables clave (p. ej., IMC, cintura, FPG/HbA1c, tabaquismo, antecedentes familiares).
6) Escribe un RiskAssessment en FHIR usando create_risk_assessment con:
   - patient_id y session_id (si hay session_id para enlazar al Encounter de la sesión; si no existe Encounter, primero créalo con create_encounter pasando purpose="risk").
   - outcome: low | medium | high (derivado de score_riesgo.riesgo_global.categoria).
   - rationale: el texto en prosa que generaste.
   - occurrence_datetime: ahora (formato ISO 8601 UTC).
   - evidence: exactamente el diccionario devuelto por score_riesgo (evidence.questionnaire_response_id y evidence.observations).
7) Comunica al paciente el resultado y recomendaciones generales; mantén empatía y sé claro/a. Idioma: español.
"""
)

risk_agent = Agent(
  model=os.getenv('RISK_AGENT_MODEL', 'gemini-2.5-flash'),
  name='clini_assistant_risk',
  description='Agente para antecedentes y factores de riesgo clínico',
  instruction=_RISK_INSTRUCTION,
  tools=[
    # Cálculo y escritura de riesgo
    ScoreRiesgoTool(),
    CreateRiskAssessmentTool(),
    CreateEncounterTool(),
    # Lectura de contexto/antecedentes
    GetPatientByIdTool(),
    GetVariablesPrevencionTool(),
    GetPatologicosPersonalesTool(),
    GetDeterminantesSocioambientalesTool(),
    GetConditionsTool(),
    GetObservacionesTool(),
    GetAllergiesTool(),
    GetMedicationRequestsTool(),
    GetFamilyMemberHistoryTool(),
  ],
) 