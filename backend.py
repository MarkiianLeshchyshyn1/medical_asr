from functools import lru_cache

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from db import DocumentRecord, SessionLocal, init_db
from pipeline import MainPipeline


app = FastAPI(title="Medical Document Backend")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@lru_cache(maxsize=1)
def get_pipeline() -> MainPipeline:
    return MainPipeline()


def get_record_or_404(record_id: int) -> DocumentRecord:
    with SessionLocal() as session:
        record = session.get(DocumentRecord, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found.")
        session.expunge(record)
        return record


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate-document")
async def generate_document(
    audio_file: UploadFile = File(...),
    output_format: str = Form(...),
):
    output_format = output_format.lower()
    if output_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported output format. Use pdf or docx.")

    try:
        audio_bytes = await audio_file.read()
        document_bytes, transcript = get_pipeline().process_audio(
            audio_file=audio_bytes,
            output_format=output_format,
            audio_filename=audio_file.filename,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    record = DocumentRecord(
        transcript=transcript,
        audio_filename=audio_file.filename or "audio.wav",
        audio_content=audio_bytes,
        document_filename=f"medical_document.{output_format}",
        document_content=document_bytes,
        output_format=output_format,
    )

    with SessionLocal() as session:
        session.add(record)
        session.commit()
        session.refresh(record)

    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "transcript": transcript,
        "audio_filename": record.audio_filename,
        "document_filename": record.document_filename,
        "output_format": record.output_format,
    }


@app.get("/history")
def get_history():
    with SessionLocal() as session:
        records = (
            session.query(DocumentRecord)
            .order_by(DocumentRecord.created_at.desc())
            .all()
        )

    return [
        {
            "id": record.id,
            "created_at": record.created_at.isoformat(),
            "transcript_preview": record.transcript[:80],
            "audio_filename": record.audio_filename,
            "document_filename": record.document_filename,
        }
        for record in records
    ]


@app.get("/history/{record_id}")
def get_history_item(record_id: int):
    record = get_record_or_404(record_id)
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "transcript": record.transcript,
        "audio_filename": record.audio_filename,
        "document_filename": record.document_filename,
        "output_format": record.output_format,
    }


@app.get("/history/{record_id}/audio")
def download_audio(record_id: int):
    record = get_record_or_404(record_id)
    return Response(
        content=record.audio_content,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{record.audio_filename}"'},
    )


@app.get("/history/{record_id}/document")
def download_document(record_id: int):
    record = get_record_or_404(record_id)
    media_type = (
        "application/pdf"
        if record.output_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(
        content=record.document_content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{record.document_filename}"'},
    )
