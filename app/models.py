from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ChatRequestModel(BaseModel):
  user_id: str
  message: str
  patient_id: Optional[str] = None
  session_id: Optional[str] = None
  agent_kind: Optional[str] = Field(default=None, description='"anamnesis" | "risk"')


class BootstrapRequestModel(BaseModel):
  user_id: str
  patient_id: str
  agent_kind: Optional[str] = Field(default=None, description='"anamnesis" | "risk"')


class CIProblem(BaseModel):
  text: str


class CIFinding(BaseModel):
  item: str
  basis: str


class CIPlanModel(BaseModel):
  status: str
  subject_ref: str
  encounter_ref: str
  summary: str
  description_md: Optional[str] = None
  problems: Optional[List[CIProblem]] = None
  findings: Optional[List[CIFinding]] = None
  prognosis: Optional[str] = None
  protocols: List[str]
  recommendations: Optional[List[str]] = None

  @validator('subject_ref')
  def validate_subject(cls, v: str) -> str:
    if not (isinstance(v, str) and v.startswith('Patient/')):
      raise ValueError('subject_ref must be "Patient/<id>"')
    return v

  @validator('encounter_ref')
  def validate_encounter(cls, v: str) -> str:
    if not (isinstance(v, str) and v.startswith('Encounter/')):
      raise ValueError('encounter_ref must be "Encounter/<id>"')
    return v


class CIEnvelope(BaseModel):
  clinical_impression: CIPlanModel 