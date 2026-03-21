import os

from transformers import AutoModelForSpeechSeq2Seq, WhisperProcessor

MODEL_NAME = "openai/whisper-large-v3"
CACHE_DIR = "C:/Users/markiian_leshchyshyn/Documents/NULP/Diploma/code/train/model"
os.environ.setdefault("HF_HOME", CACHE_DIR)

AutoModelForSpeechSeq2Seq.from_pretrained(
    MODEL_NAME,
    cache_dir=CACHE_DIR,
)
WhisperProcessor.from_pretrained(
    MODEL_NAME,
    cache_dir=CACHE_DIR,
)

print(f"Base model '{MODEL_NAME}' downloaded and cached.")
