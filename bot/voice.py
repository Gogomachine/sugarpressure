"""Voice message processing using faster-whisper."""

import os
from faster_whisper import WhisperModel

_model = None


def get_model():
    global _model
    if _model is None:
        model_name = os.getenv("WHISPER_MODEL", "base")
        _model = WhisperModel(model_name, compute_type="int8", device="cpu")
    return _model


async def transcribe_voice(file_path: str) -> str:
    """Transcribe an audio file to text using faster-whisper."""
    model = get_model()
    segments, _ = model.transcribe(file_path, language="ru")
    text = " ".join(segment.text.strip() for segment in segments)
    return text
