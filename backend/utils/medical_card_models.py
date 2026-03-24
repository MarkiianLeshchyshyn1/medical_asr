from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import field_validator


class PatientInfo(BaseModel):
    full_name: Optional[str] = Field(
        None,
        description="Повне офіційне ім'я пацієнта, яке використовується для ідентифікації в медичній документації.",
    )
    age: Optional[int] = Field(
        None,
        description="Вік пацієнта у повних роках на момент медичного звернення.",
    )
    gender: Optional[str] = Field(
        None,
        description="Стать або гендер пацієнта, які мають значення для клінічної оцінки.",
    )


class MedicalComplaint(BaseModel):
    description: str = Field(
        ...,
        description="Основна скарга або симптом, описані пацієнтом своїми словами.",
    )
    duration: Optional[str] = Field(
        None,
        description="Зазначена тривалість симптомів та їх часовий перебіг.",
    )


class Diagnosis(BaseModel):
    preliminary: Optional[str] = Field(
        None,
        description="Попередній клінічний діагноз на основі первинної оцінки та наявної інформації.",
    )
    icd10: Optional[str] = Field(
        None,
        description="Код діагнозу за МКХ-10, що відповідає попередньому діагнозу, якщо він відомий.",
    )


class Prescription(BaseModel):
    name: str = Field(
        ...,
        description="Назва призначеного препарату, лікування або клінічної рекомендації.",
    )
    dosage: Optional[str] = Field(
        None,
        description="Дозування або інструкції щодо застосування призначеного лікування.",
    )
    duration: Optional[str] = Field(
        None,
        description="Очікувана тривалість призначеного лікування або втручання.",
    )


class MedicalCard(BaseModel):
    document_date: date = Field(
        default_factory=date.today,
        description="Дата створення медичного запису.",
    )

    patient: PatientInfo

    complaints: List[MedicalComplaint] = Field(
        default_factory=list,
        description="Список скарг пацієнта, озвучених під час медичного звернення.",
    )

    diagnosis: Optional[Diagnosis] = None

    prescriptions: List[Prescription] = Field(
        default_factory=list,
        description="Список препаратів або методів лікування, призначених лікарем.",
    )

    doctor_notes: Optional[str] = Field(
        None,
        description="Додаткові нотатки або спостереження лікаря, що стосуються звернення.",
    )

    @field_validator("document_date", mode="before")
    @classmethod
    def normalize_document_date(cls, value):
        if value in (None, "", "null", "None"):
            return date.today()
        return value
