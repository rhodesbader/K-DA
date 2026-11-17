"""Prerequisite checks. Read-only: never installs anything."""
from __future__ import annotations

import importlib.util
import shutil
import sys

from .util import VERSION, run


def _ffmpeg_filters() -> set:
    ff = shutil.which("ffmpeg")
    if not ff:
        return set()
    out = run([ff, "-hide_banner", "-filters"], check=False).stdout
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and len(parts[0]) == 3:
            names.add(parts[1])
    return names


def _ytdlp_version() -> str | None:
    if importlib.util.find_spec("yt_dlp"):
        proc = run([sys.executable, "-m", "yt_dlp", "--version"], check=False)
        if proc.returncode == 0:
            return proc.stdout.strip() + " (module Python)"
    exe = shutil.which("yt-dlp")
    if exe:
        proc = run([exe, "--version"], check=False)
        if proc.returncode == 0:
            return proc.stdout.strip() + " (binaire)"
    return None


def _module_version(name: str) -> str | None:
    if not importlib.util.find_spec(name):
        return None
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "installé")
    except Exception as exc:  # import exists but is broken
        return f"ERREUR import: {exc}"


def check() -> dict:
    checks = []

    def add(name, ok, detail, required, fix=""):
        checks.append({"name": name, "ok": bool(ok), "required": required, "detail": detail, "fix": fix})

    py_ok = sys.version_info >= (3, 9)
    add("python>=3.9", py_ok, sys.version.split()[0], True, "Installez Python 3.10+ (python.org).")

    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        detail = run([path, "-version"], check=False).stdout.splitlines()[0] if path else "absent"
        add(tool, path, detail, True,
            "macOS: brew install ffmpeg | Ubuntu: sudo apt install ffmpeg | Windows: winget install Gyan.FFmpeg")

    filters = _ffmpeg_filters()
    for flt, why in (("subtitles", "sous-titres incrustés (libass)"), ("loudnorm", "normalisation audio"),
                     ("zoompan", "mouvement sur images"), ("silencedetect", "analyse audio"),
                     ("tile", "planche contact"), ("drawtext", "étiquettes de la planche (optionnel)")):
        add(f"ffmpeg filtre {flt}", flt in filters, why, flt != "drawtext",
            "Utilisez un build FFmpeg complet (libass, freetype).")

    ytv = _ytdlp_version()
    add("yt-dlp", ytv, ytv or "absent (requis seulement pour télécharger depuis une URL)", False,
        "pip install -r requirements.txt")
    fw = _module_version("faster_whisper")
    add("faster-whisper", fw and not str(fw).startswith("ERREUR"), fw or "absent (transcription locale désactivée)",
        False, "pip install -r requirements.txt (le modèle se télécharge depuis Hugging Face au 1er usage)")

    core_ok = all(c["ok"] for c in checks if c["required"])
    return {"reelkit_version": VERSION, "core_ok": core_ok, "checks": checks}


def render(result: dict) -> str:
    lines = [f"reelkit {result['reelkit_version']} — diagnostic", ""]
    for c in result["checks"]:
        mark = "OK " if c["ok"] else ("KO " if c["required"] else "-- ")
        req = "requis " if c["required"] else "option."
        lines.append(f"[{mark}] {req} {c['name']}: {c['detail']}")
        if not c["ok"] and c["fix"]:
            lines.append(f"         -> {c['fix']}")
    lines += ["", "Socle fonctionnel: " + ("OUI" if result["core_ok"] else "NON — corrigez les lignes KO")]
    return "\n".join(lines)
