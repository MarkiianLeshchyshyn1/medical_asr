from typing import List

from pydantic import BaseModel

from backend.utils.speaker_label_models import DialogueTurn, SpeakerSegmentLabel


class ApprovedTranscriptRequest(BaseModel):
    transcript: str
    output_format: str


class TranscriptionResponse(BaseModel):
    transcript: str
    numbered_transcript: str
    segments: List[SpeakerSegmentLabel]
    dialogue_turns: List[DialogueTurn]
    dialogue_text: str
