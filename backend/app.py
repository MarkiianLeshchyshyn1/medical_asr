from functools import lru_cache

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.pipeline import MainPipeline


app = FastAPI(title="Medical Document Backend")


@lru_cache(maxsize=1)
def get_pipeline() -> MainPipeline:
    return MainPipeline()


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
        document_bytes, _ = get_pipeline().process_audio(
            audio_file=audio_bytes,
            output_format=output_format,
            audio_filename=audio_file.filename,
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
