import os
from google.adk import Agent
from fhir_clini_assistant.agent import _openapi_toolset
from fhir_clini_assistant.fhir_tools import (
	GetConditionsTool,
	GetPatientByIdTool,
	GetObservacionesTool,
	GetAllergiesTool,
	GetMedicationRequestsTool,
	GetFamilyMemberHistoryTool,
	GetVariablesPrevencionTool,
	GetPatologicosPersonalesTool,
	GetDeterminantesSocioambientalesTool,
	GetDisponibilidadRecursosTool,
	GetMotivoConsultaTool,
	GetAreasAfectadasTool,
	GetPresentacionPacienteTool,
	GetResumenHistorialMedicoTool,
	ScanDatosEspecificosTool,
	ScoreRiesgoTool,
	CreateEncounterTool,
	CreateRiskAssessmentTool,
	CreateClinicalImpressionTool,
	UpdateEncounterStatusTool,
)

_INSTRUCTION = (
	"""
Eres "Clini-Assistant (Voz)", un asistente de IA que interactúa por voz con la/el paciente para realizar anamnesis. Mantén frases cortas, claras y empáticas y confirma entendidos cuando sea necesario.

Objetivo: conducir una entrevista clínica efectiva por voz y, al finalizar, registrar anamnesis y cerrar el encuentro en FHIR.

Inicio (primer turno por voz):
- Si tienes patient/patient_id, obtén motivos de consulta (get_motivo_consulta) y saluda mencionándolos brevemente.
- Si no tienes patient_id, solicita amablemente el ID del paciente y explica por qué.

Cierre de la consulta (por voz):
1) Llama score_riesgo y luego create_risk_assessment con outcome y evidence devueltos por score_riesgo; incluye session_id para vincular el Encounter.
2) Genera resumen breve y claro de la anamnesis y llama create_clinical_impression con patient_id, session_id y summary.
3) Llama update_encounter_status con session_id y status="completed".

Siempre responde en español.
"""
)

root_agent = Agent(
	model='gemini-live-2.5-flash-preview-native-audio',
	name='clini_assistant_live',
	description='Agente de consulta clínica por voz con acceso a FHIR.',
	instruction=_INSTRUCTION,
	tools=[
		# Priorizar cierre/escritura
		CreateClinicalImpressionTool(),
		UpdateEncounterStatusTool(),
		CreateRiskAssessmentTool(),
		CreateEncounterTool(),
		# Consulta
		ScoreRiesgoTool(),
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
		# OpenAPI toolset al final
		_openapi_toolset,
	],
) 