import os

import io
import re
from datetime import date
from pathlib import Path

import librosa
import torch
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from transformers import AutoModelForSpeechSeq2Seq, WhisperProcessor

from backend.config import (
    MODEL_CACHE_DIR,
    TRANSCRIPTION_LANGUAGE,
    TRANSCRIPTION_MODEL,
    STRUCTURING_MODEL,
    STRUCTURE_LANGUAGE,
)
from backend.prompt_render import (
    render_dialogue_labeling_system_prompt,
    render_dialogue_labeling_user_prompt,
    render_system_prompt,
    render_user_prompt,
)
from backend.utils import (
    DialogueTurns,
    MedicalCard,
    MedicalCardLLM,
    SpeakerSegmentLabels,
    get_logger,
)
from backend.document_generator import generate_pdf, generate_docx

load_dotenv()
os.environ.setdefault("HF_HOME", MODEL_CACHE_DIR)

logger = get_logger("backend.pipeline")


class MainPipeline:

    def __init__(self):
        logger.info("Initializing MainPipeline")

        self.transcription_model, self.transcription_processor, self.transcription_device = (
            self._build_transcription_pipeline()
        )
        logger.info("Whisper transcription model initialized")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

        self.structuring_llm = ChatOpenAI(
            api_key=api_key,
            model=STRUCTURING_MODEL,
            temperature=0.2,
        ).with_structured_output(MedicalCardLLM)

        self.dialogue_labeling_llm = ChatOpenAI(
            api_key=api_key,
            model=STRUCTURING_MODEL,
            temperature=0,
        ).with_structured_output(SpeakerSegmentLabels)

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
            llm_result = self.structuring_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            result = MedicalCard(
                document_date=date.today(),
                patient=llm_result.patient,
                complaints=llm_result.complaints,
                current_medications=llm_result.current_medications,
                diagnosis=llm_result.diagnosis,
                prescriptions=llm_result.prescriptions,
                patient_summary=llm_result.patient_summary,
                doctor_summary=llm_result.doctor_summary,
            )

            logger.info("MedicalCard successfully generated by LLM")
            return result

        except Exception:
            logger.exception("Error during MedicalCard structuring")
            raise

    def _generate_document_bytes(
        self,
        medical_card: MedicalCard,
        source_transcript: str,
        output_format: str,
    ) -> bytes:
        fmt = output_format.lower()

        if fmt == "docx":
            logger.info("Generating DOCX document")
            return generate_docx(medical_card, source_transcript)

        if fmt == "pdf":
            logger.info("Generating PDF document")
            return generate_pdf(medical_card, source_transcript)

        logger.error("Unsupported output format: %s", output_format)
        raise ValueError(f"Unsupported output format: {output_format}")

    def transcribe_audio(self, audio_file: bytes, audio_filename: str | None = None) -> str:
        logger.info("Transcription step started")
        transcribed_text = self._call_model_to_transcribe(audio_file, audio_filename=audio_filename)
        logger.info("Transcription: %s", transcribed_text)
        return transcribed_text

    def split_transcript_into_sentences(self, transcript: str) -> list[str]:
        cleaned_transcript = " ".join(transcript.split()).strip()
        if not cleaned_transcript:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", cleaned_transcript)
        normalized_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        if normalized_sentences:
            return normalized_sentences

        return [cleaned_transcript]

    def number_transcript_sentences(self, transcript: str) -> str:
        sentences = self.split_transcript_into_sentences(transcript)
        return "\n".join(
            f"[{index}] {sentence} [{index}]"
            for index, sentence in enumerate(sentences, start=1)
        )

    def label_transcript_speakers(self, numbered_transcript: str) -> SpeakerSegmentLabels:
        cleaned_numbered_transcript = numbered_transcript.strip()
        if not cleaned_numbered_transcript:
            raise ValueError("Numbered transcript must not be empty.")

        system_prompt = render_dialogue_labeling_system_prompt()
        user_prompt = render_dialogue_labeling_user_prompt(
            numbered_transcript=cleaned_numbered_transcript,
        )

        try:
            result = self.dialogue_labeling_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        except Exception:
            logger.exception("Error during dialogue speaker labeling")
            raise

        expected_ids = self._extract_numbered_transcript_ids(cleaned_numbered_transcript)
        returned_ids = [segment.id for segment in result.segments]

        if returned_ids != expected_ids:
            raise ValueError(
                "Speaker labeling response must contain every transcript id exactly once and in order."
            )

        return result

    def _extract_numbered_transcript_ids(self, numbered_transcript: str) -> list[int]:
        ids = [int(match) for match in re.findall(r"\[(\d+)\]", numbered_transcript)]
        unique_ids: list[int] = []
        for segment_id in ids:
            if not unique_ids or unique_ids[-1] != segment_id:
                unique_ids.append(segment_id)
        return unique_ids

    def build_dialogue_turns(
        self,
        numbered_transcript: str,
        speaker_labels: SpeakerSegmentLabels,
    ) -> DialogueTurns:
        segment_text_by_id = self._extract_segment_texts(numbered_transcript)
        turns: list[dict[str, str]] = []

        for segment in speaker_labels.segments:
            segment_text = segment_text_by_id.get(segment.id, "").strip()
            if not segment_text:
                continue

            if turns and turns[-1]["speaker"] == segment.speaker:
                turns[-1]["text"] = f'{turns[-1]["text"]} {segment_text}'.strip()
                continue

            turns.append({
                "speaker": segment.speaker,
                "text": segment_text,
            })

        return DialogueTurns.model_validate({"turns": turns})

    def format_dialogue_turns(self, dialogue_turns: DialogueTurns) -> str:
        speaker_names = {
            "doctor": "Лікар",
            "patient": "Пацієнт",
        }
        return "\n\n".join(
            f'{speaker_names[turn.speaker]}: {turn.text}'
            for turn in dialogue_turns.turns
        )

    def _extract_segment_texts(self, numbered_transcript: str) -> dict[int, str]:
        matches = re.findall(r"\[(\d+)\]\s*(.*?)\s*\[\1\]", numbered_transcript, flags=re.DOTALL)
        return {
            int(segment_id): text.strip()
            for segment_id, text in matches
            if text.strip()
        }

    def generate_document_from_transcript(self, dialogue_text: str, output_format: str) -> bytes:
        logger.info("Document generation from approved dialogue started | format=%s", output_format)
        cleaned_dialogue_text = dialogue_text.strip()
        if not cleaned_dialogue_text:
            raise ValueError("Dialogue text must not be empty.")

        medical_card = self._call_model_to_structure(cleaned_dialogue_text)
        return self._generate_document_bytes(medical_card, cleaned_dialogue_text, output_format)
