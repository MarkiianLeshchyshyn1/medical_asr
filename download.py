# download_model.py
from transformers import WhisperForConditionalGeneration, WhisperProcessor

WhisperForConditionalGeneration.from_pretrained(
    "openai/whisper-large-v3",
    cache_dir="C:/Users/markiian_leshchyshyn/Documents/NULP/Diploma/code/train/model"
)
WhisperProcessor.from_pretrained(
    "openai/whisper-large-v3",
    cache_dir="C:/Users/markiian_leshchyshyn/Documents/NULP/Diploma/code/train/model"
)

print("Model downloaded and cached.")
