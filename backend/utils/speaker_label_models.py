from typing import List, Literal

from pydantic import BaseModel, Field


class SpeakerSegmentLabel(BaseModel):
    id: int = Field(
        ...,
        description="Ідентифікатор пронумерованого сегмента транскрипту.",
    )
    speaker: Literal["doctor", "patient"] = Field(
        ...,
        description="Визначена роль мовця для цього сегмента.",
    )


class SpeakerSegmentLabels(BaseModel):
    segments: List[SpeakerSegmentLabel] = Field(
        default_factory=list,
        description="Мітки мовців для всіх пронумерованих сегментів транскрипту.",
    )


class DialogueTurn(BaseModel):
    speaker: Literal["doctor", "patient"] = Field(
        ...,
        description="Роль мовця для репліки діалогу.",
    )
    text: str = Field(
        ...,
        description="Текст репліки після об'єднання сусідніх сегментів одного мовця.",
    )


class DialogueTurns(BaseModel):
    turns: List[DialogueTurn] = Field(
        default_factory=list,
        description="Готовий діалог, поділений на репліки лікаря та пацієнта.",
    )
