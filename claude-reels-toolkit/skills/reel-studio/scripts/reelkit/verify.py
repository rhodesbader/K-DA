"""Objective checks on a rendered file (resolution, fps, duration, codecs, loudness, black frames)."""
from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

from .util import ffmpeg, ffprobe_json, load_defaults, now_iso


def verify(video, expected: dict | None = None) -> dict:
    video = Path(video)
    expected = expected or {}
    tol = load_defaults()["verify"]
    checks = []

    def add(name, ok, exp, act):
        checks.append({"name": name, "ok": bool(ok), "expected": exp, "actual": act})

    if not video.is_file() or video.stat().st_size == 0:
        add("fichier présent", False, "fichier non vide", "absent")
        return {"file": str(video), "ok": False, "checks": checks, "checked_at": now_iso()}
    info = ffprobe_json(video)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float(info.get("format", {}).get("duration", 0))
    fps = float(Fraction(v.get("avg_frame_rate", "0/1"))) if v.get("avg_frame_rate", "0/0") != "0/0" else 0

    add("codec vidéo h264", v.get("codec_name") == "h264", "h264", v.get("codec_name"))
    add("pixel format yuv420p", v.get("pix_fmt") == "yuv420p", "yuv420p", v.get("pix_fmt"))
    add("piste audio aac", a is not None and a.get("codec_name") == "aac", "aac", a.get("codec_name") if a else None)
    if expected.get("width"):
        add("résolution", (v.get("width"), v.get("height")) == (expected["width"], expected["height"]),
            f"{expected['width']}x{expected['height']}", f"{v.get('width')}x{v.get('height')}")
    if expected.get("fps"):
        add("cadence", abs(fps - expected["fps"]) < 0.1, expected["fps"], round(fps, 3))
    if expected.get("duration_s"):
        add("durée", abs(dur - expected["duration_s"]) <= tol["duration_tolerance_s"],
            expected["duration_s"], round(dur, 3))

    target = expected.get("loudness_target_lufs")
    if a is not None and target is not None:
        proc = ffmpeg("-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-", check=False)
        summary = proc.stderr[proc.stderr.rfind("Summary:"):]
        m_i = re.search(r"I:\s+(-?[0-9.]+) LUFS", summary)
        m_p = re.search(r"Peak:\s+(-?[0-9.]+|-inf) dBFS", summary)
        lufs = float(m_i.group(1)) if m_i else None
        add("loudness intégrée", lufs is not None and abs(lufs - target) <= tol["loudness_tolerance_lu"],
            f"{target} ±{tol['loudness_tolerance_lu']} LUFS", lufs)
        peak = None if not m_p or m_p.group(1) == "-inf" else float(m_p.group(1))
        add("true peak <= -1 dBTP", peak is None or peak <= -0.9, "<= -1.0 dBTP", peak)

    proc = ffmpeg("-i", str(video), "-an", "-vf", "blackdetect=d=0.5:pix_th=0.10", "-f", "null", "-", check=False)
    black = sum(float(x) for x in re.findall(r"black_duration:([0-9.]+)", proc.stderr))
    add("pas de longue séquence noire", black < max(dur * 0.2, 0.5), "< 20 % de noir", round(black, 2))

    return {"file": str(video), "ok": all(c["ok"] for c in checks), "duration_s": round(dur, 3),
            "checks": checks, "checked_at": now_iso()}


def render_text(report: dict) -> str:
    lines = [f"Vérification: {report['file']}"]
    for c in report["checks"]:
        lines.append(f"  [{'OK' if c['ok'] else 'KO'}] {c['name']}: attendu {c['expected']} / mesuré {c['actual']}")
    lines.append("RÉSULTAT: " + ("CONFORME" if report["ok"] else "NON CONFORME"))
    return "\n".join(lines)
