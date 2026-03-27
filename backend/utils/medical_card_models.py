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
        description="Скарга, симптом - описані пацієнтом під час розмови із лікарем",
    )
    duration: Optional[str] = Field(
        "Тривалість не зазначена",
        description="Зазначена тривалість симптомів та їх часовий перебіг.",
    )

class CurrentMedication(BaseModel):
    name: Optional[str] = Field(
        "Не приймає ніяких препаратів",
        description="Назва препарату, який пацієнт зараз приймає або приймав раніше.",
    )
    duration: Optional[str] = Field(
        "Тривалість не зазначена",
        description="Тривалість прийому препарату.",
    )


class Diagnosis(BaseModel):
    preliminary: Optional[str] = Field(
        None,
        description="Попередній клінічний діагноз на основі первинної оцінки та наявної інформації.",
    )


class Prescription(BaseModel):
    name: str = Field(
        ...,
        description="Назва призначеного препарату, лікування або клінічної рекомендації.",
    )
    dosage: Optional[str] = Field(
        "Дозування не зазначено",
        description="Дозування або інструкції щодо застосування призначеного лікування.",
    )
    duration: Optional[str] = Field(
        "Тривалість не зазначена",
        description="Очікувана тривалість призначеного лікування або втручання.",
    )


class MedicalCardBase(BaseModel):
    patient: PatientInfo

    complaints: List[MedicalComplaint] = Field(
        default_factory=list,
        description="Список скарг пацієнта, озвучених під час медичного звернення.",
    )

    current_medications: List[CurrentMedication] = Field(
        default_factory=list,
        description="Список препаратів, які пацієнт зараз приймає або приймав раніше.",
    )

    diagnosis: Optional[Diagnosis] = Field(
        None,
        description="Попередній клінічний діагноз, поставлений лікарем.",
    )

    prescriptions: List[Prescription] = Field(
        default_factory=list,
        description="Список препаратів або методів лікування, призначених лікарем.",
    )

    patient_summary: Optional[str] = Field(
        None,
        description="Короткий результат скарг та стану пацієнта на 3-4 речення.",
    )

    doctor_summary: Optional[str] = Field(
        None,
        description="Короткий висновок, пояснень і рекомендацій від лікаря на 3-4 речення.",
    )


class MedicalCard(MedicalCardBase):
    document_date: date = Field(
        default_factory=date.today,
    )

    @field_validator("document_date", mode="before")
    @classmethod
    def normalize_document_date(cls, value):
        if value in (None, "", "null", "None"):
            return date.today()
        return value


class MedicalCardLLM(MedicalCardBase):
    """Схема для відповіді LLM без системних полів (наприклад, дати документа)."""
