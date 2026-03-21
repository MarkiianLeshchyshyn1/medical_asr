import os

import io
import logging
from pathlib import Path

import librosa
import torch
from langchain_openai import ChatOpenAI
from os import getenv
from dotenv import load_dotenv
from transformers import AutoModelForSpeechSeq2Seq, WhisperProcessor

from backend.config import (
    MODEL_CACHE_DIR,
    TRANSCRIPTION_LANGUAGE,
    TRANSCRIPTION_MODEL,
    STRUCTURING_MODEL,
    STRUCTURE_LANGUAGE,
)
from backend.utils import MedicalCard
from backend.prompt_render import render_system_prompt, render_user_prompt
from backend.document_generator import generate_pdf, generate_docx

load_dotenv()
os.environ.setdefault("HF_HOME", MODEL_CACHE_DIR)

logger = logging.getLogger("MainPipeline")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class MainPipeline:

    def __init__(self):
        logger.info("Initializing MainPipeline")

        self.transcription_model, self.transcription_processor, self.transcription_device = (
            self._build_transcription_pipeline()
        )
        logger.info("Whisper transcription model initialized")

        api_key = getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

        self.structuring_llm = ChatOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=STRUCTURING_MODEL,
            temperature=0.5,
            extra_body={"reasoning_effort": "low"}
        ).with_structured_output(MedicalCard)

        logger.info("LLM client initialized")

    def _build_transcription_pipeline(self):
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("Loading Whisper model: %s", TRANSCRIPTION_MODEL)

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            TRANSCRIPTION_MODEL,
            cache_dir=MODEL_CACHE_DIR,
            local_files_only=True,
            dtype=torch_dtype,
            low_cpu_mem_usage=True,
        )
        processor = WhisperProcessor.from_pretrained(
            TRANSCRIPTION_MODEL,
            cache_dir=MODEL_CACHE_DIR,
            local_files_only=True,
        )

        model = model.to(device)
        model.eval()

        return model, processor, device

    def _call_model_to_transcribe(self, audio_bytes: bytes, audio_filename: str | None = None) -> str:
        suffix = Path(audio_filename or "upload.wav").suffix or ".wav"
        audio_format = suffix.lstrip(".").lower()

        if audio_format != "wav":
            raise RuntimeError(
                f"Unsupported audio format: '{audio_format}'. "
                "Supported format: wav."
            )

        logger.info("Transcribing audio with Whisper model: %s", TRANSCRIPTION_MODEL)
        audio_array, sampling_rate = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

        duration_seconds = len(audio_array) / sampling_rate
        chunk_seconds = 15

        def transcribe_chunk(chunk_audio):
            inputs = self.transcription_processor(
                chunk_audio,
                sampling_rate=sampling_rate,
                return_tensors="pt",
            )
            input_features = inputs.input_features.to(self.transcription_device)
            with torch.no_grad():
                predicted_ids = self.transcription_model.generate(
                    input_features,
                    language=TRANSCRIPTION_LANGUAGE,
                    task="transcribe",
                )
            return self.transcription_processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True,
            )[0].strip()

        if duration_seconds <= chunk_seconds:
            transcription = transcribe_chunk(audio_array)
        else:
            logger.info("Audio duration %.2fs > %ss, transcribing in chunks", duration_seconds, chunk_seconds)
            chunk_size = sampling_rate * chunk_seconds
            parts = []
            for start in range(0, len(audio_array), chunk_size):
                end = start + chunk_size
                chunk_audio = audio_array[start:end]
                if len(chunk_audio) == 0:
                    continue
                chunk_text = transcribe_chunk(chunk_audio)
                if chunk_text:
                    parts.append(chunk_text)
            transcription = " ".join(parts).strip()

        logger.info("Total transcription length: %d characters", len(transcription))
        return transcription


    def _call_model_to_structure(self, transcribed_text: str) -> MedicalCard:
        logger.info("Structuring transcription into MedicalCard")

        system_prompt = render_system_prompt(language=STRUCTURE_LANGUAGE)
        user_prompt = render_user_prompt(transcript=transcribed_text)

        try:
            result = self.structuring_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])

            logger.info("MedicalCard successfully generated by LLM")
            return result

        except Exception as e:
            logger.exception("Error during MedicalCard structuring")
            raise

    def _generate_document_bytes(self, medical_card: MedicalCard, output_format: str) -> bytes:
        fmt = output_format.lower()

        if fmt == "docx":
            logger.info("Generating DOCX document")
            return generate_docx(medical_card)

        if fmt == "pdf":
            logger.info("Generating PDF document")
            return generate_pdf(medical_card)

        logger.error("Unsupported output format: %s", output_format)
        raise ValueError(f"Unsupported output format: {output_format}")

    def process_audio(self, audio_file: bytes, output_format: str, audio_filename: str | None = None) -> tuple[bytes, str]:
        logger.info("Pipeline started | format=%s", output_format)

        transcribed_text = self._call_model_to_transcribe(audio_file, audio_filename=audio_filename)
        logger.info("Transcription: %s", transcribed_text)
        medical_card = self._call_model_to_structure(transcribed_text)
        document_bytes = self._generate_document_bytes(medical_card, output_format)
        return document_bytes, transcribed_text

    def invoke_pipeline(self, audio_file: bytes, output_format: str, audio_filename: str | None = None):
        try:
            document_bytes, _ = self.process_audio(
                audio_file=audio_file,
                output_format=output_format,
                audio_filename=audio_filename,
            )
            return document_bytes

        except ValueError as e:
            logger.error(f"Pipeline input error: {e}")
            raise RuntimeError(f"Pipeline input error: {e}")

        except Exception as e:
            logger.exception("Pipeline execution failed")
            raise RuntimeError(f"Pipeline execution failed: {e}")
