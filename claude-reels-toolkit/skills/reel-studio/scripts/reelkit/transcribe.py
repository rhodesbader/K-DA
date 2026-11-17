"""Local speech-to-text with faster-whisper (optional dependency).

Audio never leaves the machine. The model is downloaded once from Hugging Face
(or loaded from REELKIT_WHISPER_MODEL_DIR / a local path given as model name).
"""
from __future__ import annotations

import importlib.util
import os

from .util import ReelkitError, load_defaults, log


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def transcribe(audio_path, model: str | None = None, language: str | None = None) -> dict:
    if not available():
        raise ReelkitError("faster-whisper n'est pas installé (`pip install -r requirements.txt`).")
    from faster_whisper import WhisperModel  # imported lazily: heavy

    cfg = load_defaults()["transcription"]
    model = model or os.environ.get("REELKIT_WHISPER_MODEL") or cfg["model"]
    root = os.environ.get("REELKIT_WHISPER_MODEL_DIR")
    log(f"transcription locale (faster-whisper, modèle '{model}')… 1er usage = téléchargement du modèle")
    try:
        wm = WhisperModel(model, device="cpu", compute_type=cfg["compute_type"],
                          download_root=root or None)
    except Exception as exc:
        raise ReelkitError(
            f"Impossible de charger le modèle Whisper '{model}': {exc}\n"
            "Vérifiez l'accès réseau à huggingface.co, ou téléchargez le modèle et passez son dossier "
            "via REELKIT_WHISPER_MODEL=/chemin/vers/modele.") from exc
    segments, info = wm.transcribe(str(audio_path), language=language or None,
                                   vad_filter=cfg["vad_filter"], word_timestamps=True)
    out = []
    for seg in segments:
        out.append({
            "start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip(),
            "words": [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip()}
                      for w in (seg.words or [])],
        })
    return {"engine": "faster-whisper", "model": model, "language": info.language,
            "language_probability": round(info.language_probability, 3), "segments": out}


def words_from_segments(segments) -> list:
    words = []
    for seg in segments:
        if seg.get("words"):
            words += [w for w in seg["words"] if w.get("word")]
        else:  # SRT without word timing: spread words evenly inside the cue
            toks = seg["text"].split()
            if not toks:
                continue
            step = (seg["end"] - seg["start"]) / len(toks)
            words += [{"start": seg["start"] + i * step, "end": seg["start"] + (i + 1) * step, "word": t}
                      for i, t in enumerate(toks)]
    return words
