from functools import lru_cache

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.config import TEST_TRANSCRIPT_STUB, USE_TEST_TRANSCRIPT_STUB
from backend.pipeline import MainPipeline
from backend.utils import (
    ApprovedTranscriptRequest,
    TranscriptionResponse,
    get_logger,
)


app = FastAPI(title="Medical Document Backend")
logger = get_logger("backend.app")


@lru_cache(maxsize=1)
def get_pipeline() -> MainPipeline:
    return MainPipeline()


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe-audio")
async def transcribe_audio(audio_file: UploadFile = File(...)) -> TranscriptionResponse:
    if USE_TEST_TRANSCRIPT_STUB:
        logger.info("Returning test transcript stub for /transcribe-audio")
        return TranscriptionResponse(dialogue_text=TEST_TRANSCRIPT_STUB)

    try:
        audio_bytes = await audio_file.read()
        pipeline = get_pipeline()
        transcript = pipeline.transcribe_audio(
            audio_file=audio_bytes,
            audio_filename=audio_file.filename,
        )
        numbered_transcript = pipeline.number_transcript_sentences(transcript)
        logger.info("Numbered transcript:\n%s", numbered_transcript)
        speaker_labels = pipeline.label_transcript_speakers(numbered_transcript)
        logger.info("Speaker labels: %s", speaker_labels.model_dump())
        dialogue_turns = pipeline.build_dialogue_turns(numbered_transcript, speaker_labels)
        logger.info("Dialogue turns: %s", dialogue_turns.model_dump())
        dialogue_text = pipeline.format_dialogue_turns(dialogue_turns)
        logger.info("Dialogue text:\n%s", dialogue_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return TranscriptionResponse(
        dialogue_text=dialogue_text,
    )


@app.post("/generate-document-from-transcript")
def generate_document_from_transcript(request: ApprovedTranscriptRequest):
    output_format = request.output_format.lower()
    if output_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported output format. Use pdf or docx.")

    try:
        document_bytes = get_pipeline().generate_document_from_transcript(
            dialogue_text=request.dialogue_text,
            output_format=output_format,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    media_type = (
        "application/pdf"
        if output_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    filename = f"medical_document.{output_format}"

    return Response(
        content=document_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
