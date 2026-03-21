import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

TRANSCRIPTION_MODEL = "openai/whisper-large-v3"
TRANSCRIPTION_LANGUAGE = "uk"
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", str(BASE_DIR / "model"))
STRUCTURING_MODEL = os.getenv("STRUCTURING_MODEL", "gpt-oss-20b")
STRUCTURE_LANGUAGE = "Ukranian"

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
API_URL = f"{BACKEND_BASE_URL}/generate-document"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/medical_documents",
)
