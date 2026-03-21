from transformers import AutoModelForSpeechSeq2Seq, WhisperProcessor

from config import MODEL_CACHE_DIR, TRANSCRIPTION_MODEL


def main() -> None:
    print(f"Downloading model '{TRANSCRIPTION_MODEL}' to {MODEL_CACHE_DIR}...")
    AutoModelForSpeechSeq2Seq.from_pretrained(
        TRANSCRIPTION_MODEL,
        cache_dir=MODEL_CACHE_DIR,
    )
    WhisperProcessor.from_pretrained(
        TRANSCRIPTION_MODEL,
        cache_dir=MODEL_CACHE_DIR,
    )
    print("Done.")


if __name__ == "__main__":
    main()
