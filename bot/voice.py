"""Voice message processing using OpenAI Whisper."""

import os
import tempfile
import whisper

_model = None


def get_model():
    global _model
    if _model is None:
        model_name = os.getenv("WHISPER_MODEL", "base")
        _model = whisper.load_model(model_name)
    return _model


async def transcribe_voice(file_path: str) -> str:
    """Transcribe an audio file to text using Whisper."""
    model = get_model()
    result = model.transcribe(file_path, language="ru")
    return result["text"]
