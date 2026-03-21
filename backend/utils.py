from pydantic import BaseModel, Field
from pydantic import field_validator
from typing import List, Optional
from datetime import date


class PatientInfo(BaseModel):
    full_name: Optional[str] = Field(
        None,
        description="Patient’s full legal name used for identification in medical records."
    )
    age: Optional[int] = Field(
        None,
        description="Patient’s age in completed years at the time of the medical encounter."
    )
    gender: Optional[str] = Field(
        None,
        description="Patient’s self-reported gender or biological sex relevant to clinical assessment."
    )


class MedicalComplaint(BaseModel):
    description: str = Field(
        ...,
        description="Patient-reported primary complaint or symptom described in their own words."
    )
    duration: Optional[str] = Field(
        None,
        description="Reported duration and temporal pattern of the symptom(s)."
    )


class Diagnosis(BaseModel):
    preliminary: Optional[str] = Field(
        None,
        description="Preliminary clinical diagnosis based on initial assessment and available information."
    )
    icd10: Optional[str] = Field(
        None,
        description="ICD-10 diagnostic code corresponding to the preliminary diagnosis, if available."
    )


class Prescription(BaseModel):
    name: str = Field(
        ...,
        description="Name of the prescribed medication, treatment, or clinical recommendation."
    )
    dosage: Optional[str] = Field(
        None,
        description="Dosage or instructions describing how the prescribed treatment should be used."
    )
    duration: Optional[str] = Field(
        None,
        description="Intended duration of the prescribed treatment or intervention."
    )


class MedicalCard(BaseModel):
    document_date: date = Field(
        default_factory=date.today,
        description="Date on which the medical record was created."
    )

    patient: PatientInfo

    complaints: List[MedicalComplaint] = Field(
        default_factory=list,
        description="List of patient-reported complaints presented during the medical encounter."
    )

    diagnosis: Optional[Diagnosis] = None

    prescriptions: List[Prescription] = Field(
        default_factory=list,
        description="List of medications or treatments prescribed by the clinician."
    )

    doctor_notes: Optional[str] = Field(
        None,
        description="Additional clinician notes or observations relevant to the encounter."
    )

    source_transcript: Optional[str] = Field(
        None,
        description="Original unstructured transcript of the patient encounter for reference or audit."
    )

    @field_validator("document_date", mode="before")
    @classmethod
    def normalize_document_date(cls, value):
        if value in (None, "", "null", "None"):
            return date.today()
        return value
