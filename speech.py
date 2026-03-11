import subprocess
import tempfile
from pathlib import Path

import whisper

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def ogg_to_wav(ogg_path: str) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
        capture_output=True,
        check=True,
    )
    return wav_path


def transcribe(audio_path: str) -> str:
    model = _get_model()
    result = model.transcribe(audio_path, language="ru")
    return result["text"].strip()
