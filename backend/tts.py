"""Offline text-to-speech using Piper (https://github.com/rhasspy/piper)."""
import wave
from functools import lru_cache
from pathlib import Path

from .config import VOICES_DIR


def find_voice_model() -> Path | None:
    models = sorted(VOICES_DIR.glob("*.onnx"))
    return models[0] if models else None


def voice_available() -> bool:
    if find_voice_model() is None:
        return False
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def _load_voice(model_path: str):
    from piper import PiperVoice
    return PiperVoice.load(model_path)


def synthesize(text: str, out_path: Path) -> float:
    """Speak `text` into a WAV file and return its length in seconds."""
    model = find_voice_model()
    if model is None:
        raise RuntimeError("No voice model found in the voices/ folder. Run setup.bat or see README.md.")
    voice = _load_voice(str(model))
    with wave.open(str(out_path), "wb") as wav_file:
        if hasattr(voice, "synthesize_wav"):  # piper-tts 1.3+
            voice.synthesize_wav(text, wav_file)
        else:                                 # older piper-tts
            voice.synthesize(text, wav_file)
    with wave.open(str(out_path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def concat_wavs(paths: list[Path], gap: float, out_path: Path) -> None:
    """Join WAV files into one, with `gap` seconds of silence after each."""
    params = None
    chunks = []
    for path in paths:
        with wave.open(str(path), "rb") as wav_file:
            params = params or wav_file.getparams()
            chunks.append(wav_file.readframes(wav_file.getnframes()))
    silence = b"\x00" * (int(params.framerate * gap) * params.sampwidth * params.nchannels)
    with wave.open(str(out_path), "wb") as out:
        out.setparams(params)
        for chunk in chunks:
            out.writeframes(chunk)
            out.writeframes(silence)
