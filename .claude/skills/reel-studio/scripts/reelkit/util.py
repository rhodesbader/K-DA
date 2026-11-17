"""Shared helpers: subprocess, ffprobe, JSON, SRT, paths."""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0.0"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}

ENGINE_DIR = Path(__file__).resolve().parent
SKILL_DIR = ENGINE_DIR.parent.parent  # .../reel-studio
CONFIG_DIR = SKILL_DIR / "config"
TEMPLATES_DIR = SKILL_DIR / "templates"


class ReelkitError(RuntimeError):
    """Expected, user-facing failure (bad input, missing tool...)."""


def log(msg: str) -> None:
    print(f"[reelkit] {msg}", file=sys.stderr, flush=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise ReelkitError(f"'{tool}' est introuvable dans le PATH. Lancez `reelkit.py doctor`.")
    return path


def run(cmd, cwd=None, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-20:])
        raise ReelkitError(f"{Path(cmd[0]).name} a échoué (code {proc.returncode}):\n{tail}")
    return proc


def ffmpeg(*args, cwd=None, check: bool = True) -> subprocess.CompletedProcess:
    return run([need("ffmpeg"), "-hide_banner", "-nostdin", *args], cwd=cwd, check=check)


def ffprobe_json(path) -> dict:
    proc = run([need("ffprobe"), "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", str(path)])
    return json.loads(proc.stdout or "{}")


def media_duration(path) -> float:
    info = ffprobe_json(path)
    dur = info.get("format", {}).get("duration")
    if dur in (None, "N/A"):
        for s in info.get("streams", []):
            if s.get("duration") not in (None, "N/A"):
                return float(s["duration"])
        return 0.0
    return float(dur)


def has_stream(path, kind: str) -> bool:
    return any(s.get("codec_type") == kind for s in ffprobe_json(path).get("streams", []))


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def slugify(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9_-]+", "-", text).strip("-_")
    return (text[:maxlen].strip("-_") or "untitled")


def fmt_ts(sec: float) -> str:
    sec = max(float(sec), 0.0)
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:04.1f}"


def srt_ts(sec: float) -> str:
    ms = int(round(max(float(sec), 0.0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


_SRT_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def _parse_srt_time(value: str) -> float:
    m = _SRT_TIME.search(value)
    if not m:
        raise ValueError(f"horodatage SRT invalide: {value!r}")
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_srt(text: str) -> list:
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text.strip().lstrip("﻿")):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        start_s, end_s = lines[idx].split("-->", 1)
        body = " ".join(lines[idx + 1:]).strip()
        if body:
            cues.append({"start": _parse_srt_time(start_s), "end": _parse_srt_time(end_s), "text": body})
    return cues


def write_srt(cues, path) -> Path:
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{srt_ts(c['start'])} --> {srt_ts(c['end'])}\n{c['text']}\n")
    Path(path).write_text("\n".join(out), encoding="utf-8")
    return Path(path)


def count_words(text: str) -> int:
    text = re.sub(r"[\[\(][^\]\)]*[\]\)]", " ", text or "")  # strip [Music], (applause)
    return len(re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", text))


def workspace_root() -> Path:
    env = os.environ.get("REELKIT_WORKSPACE")
    return Path(env).expanduser().resolve() if env else (Path.cwd() / "reels-workspace").resolve()


def load_defaults() -> dict:
    return read_json(CONFIG_DIR / "defaults.json")


def describe(values) -> dict | None:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    mean = statistics.fmean(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return {
        "n": len(vals),
        "mean": round(mean, 3),
        "median": round(statistics.median(vals), 3),
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "stdev": round(stdev, 3),
        "cv": round(stdev / abs(mean), 3) if mean else None,
    }


def find_source_video(reel_dir: Path) -> Path:
    for p in sorted(Path(reel_dir).glob("source.*")):
        if p.suffix.lower() in VIDEO_EXTS:
            return p
    raise ReelkitError(f"Aucune vidéo source.* dans {reel_dir}. Lancez d'abord `grab`.")


def expand_media(items) -> list:
    out = []
    for item in items:
        p = Path(item).expanduser()
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in VIDEO_EXTS | IMAGE_EXTS)
        elif p.is_file():
            out.append(p)
        else:
            raise ReelkitError(f"Média introuvable: {item}")
    if not out:
        raise ReelkitError("Aucun média exploitable (vidéo ou image) fourni.")
    return [q.resolve() for q in out]
