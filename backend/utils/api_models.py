from pydantic import BaseModel


class ApprovedTranscriptRequest(BaseModel):
    dialogue_text: str
    output_format: str


class TranscriptionResponse(BaseModel):
    dialogue_text: str
