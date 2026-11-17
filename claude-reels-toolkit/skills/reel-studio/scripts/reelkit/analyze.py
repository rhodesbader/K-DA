"""Measured (not guessed) analysis of a reel: technical specs, cuts, pacing,
keyframes + contact sheet, loudness, silences, transcript.

Everything written to analysis.json is either measured by ffmpeg/ffprobe or
comes from a transcript. Qualitative judgement (hook, caption style, persuasion)
is left to Claude in decode.json, with frame evidence.
"""
from __future__ import annotations

import json
import re
import shutil
from fractions import Fraction
from pathlib import Path

from . import transcribe as tr
from .util import (TEMPLATES_DIR, VERSION, ReelkitError, count_words, describe, ffmpeg, ffprobe_json,
                   find_source_video, fmt_ts, load_defaults, log, now_iso, parse_srt, read_json, write_json,
                   write_srt)


# ----------------------------------------------------------------- technical

def probe(video: Path) -> dict:
    info = ffprobe_json(video)
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v:
        raise ReelkitError(f"Pas de flux vidéo dans {video}")
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rotation = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    rotation = rotation or int((v.get("tags") or {}).get("rotate", 0) or 0)
    if abs(rotation) % 180 == 90:
        w, h = h, w
    try:
        fps = float(Fraction(v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"))
    except (ZeroDivisionError, ValueError):
        fps = 0.0
    duration = float(info.get("format", {}).get("duration") or v.get("duration") or 0)
    ratio = Fraction(w, h).limit_denominator(20) if w and h else None
    return {
        "duration_s": round(duration, 3),
        "width": w, "height": h, "rotation": rotation,
        "aspect_ratio": f"{ratio.numerator}:{ratio.denominator}" if ratio else None,
        "orientation": "vertical" if h > w else ("horizontal" if w > h else "square"),
        "fps": round(fps, 3),
        "video_codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "bitrate_kbps": round(int(info["format"]["bit_rate"]) / 1000) if info.get("format", {}).get("bit_rate") else None,
        "has_audio": a is not None,
        "audio_codec": a.get("codec_name") if a else None,
        "audio_sample_rate": int(a["sample_rate"]) if a and a.get("sample_rate") else None,
        "audio_channels": a.get("channels") if a else None,
    }


# ----------------------------------------------------------------- cuts

def detect_cuts(video: Path, threshold: float, min_gap: float, duration: float) -> list:
    proc = ffmpeg("-i", str(video), "-an", "-sn",
                  "-vf", f"scale=320:-2,select='gt(scene,{threshold})',metadata=print:file=-",
                  "-f", "null", "-")
    cuts, t = [], None
    for line in proc.stdout.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"lavfi\.scene_score=([0-9.]+)", line)
        if m and t is not None:
            if 0.05 < t < duration - 0.05 and (not cuts or t - cuts[-1]["time"] >= min_gap):
                cuts.append({"time": round(t, 3), "score": round(float(m.group(1)), 3)})
            t = None
    return cuts


def shots_from_cuts(cuts: list, duration: float) -> list:
    bounds = [0.0] + [c["time"] for c in cuts] + [duration]
    return [{"index": i + 1, "start": round(a, 3), "end": round(b, 3), "duration": round(b - a, 3)}
            for i, (a, b) in enumerate(zip(bounds, bounds[1:])) if b - a > 0.01]


def pacing(shots: list, duration: float) -> dict:
    lengths = [s["duration"] for s in shots]
    stats = describe(lengths) or {}
    return {
        "shots": len(shots),
        "cuts": max(len(shots) - 1, 0),
        "cuts_per_minute": round((len(shots) - 1) / duration * 60, 2) if duration else None,
        "shot_length_s": stats,
        "first_cut_at_s": shots[1]["start"] if len(shots) > 1 else None,
        "shots_in_first_3s": sum(1 for s in shots if s["start"] < 3.0),
    }


# ----------------------------------------------------------------- frames

def keyframe_times(shots: list, duration: float, max_frames: int) -> list:
    mids = [(s["start"] + s["end"]) / 2 for s in shots]
    if len(mids) > max_frames - 2:
        step = len(mids) / (max_frames - 2)
        mids = [mids[int(i * step)] for i in range(max_frames - 2)]
    times = sorted({0.0, *[round(m, 2) for m in mids], round(max(duration - 0.15, 0.0), 2)})
    kept = []
    for t in times:
        if not kept or t - kept[-1] >= 0.3:
            kept.append(t)
    return kept


def shot_at(shots: list, t: float) -> int | None:
    for s in shots:
        if s["start"] <= t < s["end"] or (s is shots[-1] and t <= s["end"]):
            return s["index"]
    return None


def extract_keyframes(video: Path, times: list, frames_dir: Path, long_side: int) -> list:
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    scale = f"scale='if(gt(iw,ih),{long_side},-2)':'if(gt(iw,ih),-2,{long_side})'"
    out = []
    for i, t in enumerate(times, 1):
        name = f"frame_{i:03d}.jpg"
        ffmpeg("-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", scale, "-q:v", "3", "-y",
               str(frames_dir / name))
        if (frames_dir / name).exists():
            out.append({"file": f"frames/{name}", "time": t, "timecode": fmt_ts(t)})
    return out


def contact_sheet(reel_dir: Path, frames: list, columns: int) -> str | None:
    if not frames:
        return None
    tmp = reel_dir / ".thumbs"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        for i, f in enumerate(frames, 1):
            label = f"#{i} {f['timecode']}".replace(":", r"\:")
            src, dst = str(reel_dir / f["file"]), str(tmp / f"t_{i:03d}.jpg")
            base = "scale=320:-2"
            proc = ffmpeg("-i", src, "-vf",
                          f"{base},drawtext=text='{label}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=5",
                          "-y", dst, check=False)
            if proc.returncode != 0:  # drawtext missing (no freetype/fontconfig): unlabeled tile
                ffmpeg("-i", src, "-vf", base, "-y", dst)
        rows = -(-len(frames) // columns)
        ffmpeg("-framerate", "1", "-i", str(tmp / "t_%03d.jpg"), "-vf",
               f"tile={columns}x{rows}:padding=6:margin=6:color=0x202020", "-frames:v", "1", "-q:v", "3",
               "-y", str(reel_dir / "contact_sheet.jpg"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "contact_sheet.jpg" if (reel_dir / "contact_sheet.jpg").exists() else None


# ----------------------------------------------------------------- audio

def audio_analysis(video: Path, reel_dir: Path, duration: float, cfg: dict) -> dict:
    wav = reel_dir / "audio.wav"
    ffmpeg("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-y", str(wav))
    res = {"has_audio": True, "file": "audio.wav"}
    res.update(measure_loudness(video))
    proc = ffmpeg("-i", str(video), "-vn", "-af",
                  f"silencedetect=noise={cfg['silence_noise_db']}dB:d={cfg['silence_min_s']}",
                  "-f", "null", "-")
    silences, start = [], None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start: (-?[0-9.]+)", line)
        if m:
            start = max(float(m.group(1)), 0.0)
        m = re.search(r"silence_end: ([0-9.]+)", line)
        if m and start is not None:
            silences.append({"start": round(start, 2), "end": round(float(m.group(1)), 2)})
            start = None
    if start is not None:
        silences.append({"start": round(start, 2), "end": round(duration, 2)})
    total = sum(s["end"] - s["start"] for s in silences)
    res.update({"silences": silences, "silence_ratio": round(total / duration, 3) if duration else None})
    return res


def measure_loudness(path: Path) -> dict:
    proc = ffmpeg("-i", str(path), "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-", check=False)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not m:
        return {"integrated_lufs": None, "true_peak_dbtp": None, "loudness_range_lu": None}
    data = json.loads(m.group(0))

    def num(key):
        try:
            v = float(data[key])
            return None if v in (float("inf"), float("-inf")) else round(v, 2)
        except (KeyError, ValueError):
            return None
    return {"integrated_lufs": num("input_i"), "true_peak_dbtp": num("input_tp"),
            "loudness_range_lu": num("input_lra")}


# ----------------------------------------------------------------- transcript

def get_transcript(reel_dir: Path, has_audio: bool, mode: str, model, language, srt_path) -> dict:
    tjson, tsrt = reel_dir / "transcript.json", reel_dir / "transcript.srt"
    if srt_path:
        cues = parse_srt(Path(srt_path).expanduser().read_text(encoding="utf-8", errors="replace"))
        write_srt(cues, tsrt)
        data = {"engine": "srt-fourni", "model": None, "language": language, "segments": cues}
        write_json(tjson, data)
        return {"status": "ok", "source": "srt fourni par l'utilisateur", **_tmeta(data)}
    if tjson.exists() and mode != "on":
        data = read_json(tjson)
        return {"status": "ok", "source": f"cache ({data.get('engine')})", **_tmeta(data)}
    if tsrt.exists() and mode != "on":
        data = {"engine": "srt-existant", "model": None, "language": language,
                "segments": parse_srt(tsrt.read_text(encoding="utf-8", errors="replace"))}
        write_json(tjson, data)
        return {"status": "ok", "source": "transcript.srt existant", **_tmeta(data)}
    if not has_audio:
        return {"status": "no_audio"}
    if mode == "off":
        return {"status": "skipped", "reason": "--transcribe off"}
    if not tr.available():
        if mode == "on":
            raise ReelkitError("--transcribe on demandé mais faster-whisper n'est pas installé.")
        return {"status": "unavailable", "reason": "faster-whisper absent ; fournissez --srt ou installez-le"}
    try:
        data = tr.transcribe(reel_dir / "audio.wav", model=model, language=language)
    except ReelkitError as exc:
        if mode == "on":
            raise
        log(f"transcription impossible: {exc}")
        return {"status": "failed", "reason": str(exc).splitlines()[0]}
    write_json(tjson, data)
    write_srt(data["segments"], tsrt)
    return {"status": "ok", "source": f"faster-whisper ({data['model']})", **_tmeta(data)}


def _tmeta(data: dict) -> dict:
    segs = data.get("segments", [])
    words = sum(count_words(s["text"]) for s in segs)
    speech = sum(max(s["end"] - s["start"], 0) for s in segs)
    return {"file": "transcript.srt", "language": data.get("language"), "segments": len(segs), "words": words,
            "speech_seconds": round(speech, 2),
            "words_per_minute_speech": round(words / speech * 60, 1) if speech > 1 else None,
            "text": " ".join(s["text"] for s in segs)}


# ----------------------------------------------------------------- main

def analyze(reel_dir: Path, threshold=None, max_frames=None, transcribe="auto", model=None, language=None,
            srt=None) -> dict:
    reel_dir = Path(reel_dir).resolve()
    cfg = load_defaults()["analysis"]
    threshold = threshold if threshold is not None else cfg["scene_threshold"]
    max_frames = max_frames or cfg["max_keyframes"]
    video = find_source_video(reel_dir)
    meta = read_json(reel_dir / "meta.json") if (reel_dir / "meta.json").exists() else {}

    log("lecture des caractéristiques techniques…")
    tech = probe(video)
    dur = tech["duration_s"]
    log("détection des coupes…")
    cuts = detect_cuts(video, threshold, cfg["min_shot_gap_s"], dur)
    shots = shots_from_cuts(cuts, dur)
    log(f"{len(shots)} plans détectés ; extraction des images clés…")
    frames = extract_keyframes(video, keyframe_times(shots, dur, max_frames), reel_dir / "frames",
                               cfg["keyframe_long_side_px"])
    for f in frames:
        f["shot"] = shot_at(shots, f["time"])
    sheet = contact_sheet(reel_dir, frames, cfg["contact_sheet_columns"])
    audio = {"has_audio": False}
    if tech["has_audio"]:
        log("analyse audio (loudness, silences)…")
        audio = audio_analysis(video, reel_dir, dur, cfg)
    transcript = get_transcript(reel_dir, tech["has_audio"], transcribe, model, language, srt)

    words = transcript.get("words")
    if transcript.get("status") == "ok":
        content_mode = "text_overlay" if words < cfg["text_overlay_word_threshold"] else "spoken"
    else:
        content_mode = "unknown"
    hook_text = None
    if transcript.get("status") == "ok":
        segs = read_json(reel_dir / "transcript.json")["segments"]
        hook_text = " ".join(s["text"] for s in segs if s["start"] < 3.0) or None

    analysis = {
        "schema": "reelkit.analysis/1",
        "tool_version": VERSION,
        "generated_at": now_iso(),
        "reel_id": meta.get("reel_id", reel_dir.name),
        "source": {k: meta.get(k) for k in ("source_type", "source_url", "uploader", "uploader_id",
                                             "upload_date", "view_count", "like_count", "comment_count",
                                             "description", "original_name") if meta.get(k) is not None},
        "video_file": video.name,
        "technical": tech,
        "pacing": pacing(shots, dur),
        "scene_threshold": threshold,
        "cuts": cuts,
        "shots": shots,
        "keyframes": frames,
        "contact_sheet": sheet,
        "audio": audio,
        "transcript": {k: v for k, v in transcript.items() if k != "text"},
        "content_mode": content_mode,
        "hook_window_0_3s": {"shots": sum(1 for s in shots if s["start"] < 3.0), "spoken_text": hook_text},
        "not_measured": [
            "texte à l'écran (pas d'OCR automatique : lecture visuelle des frames par Claude)",
            "type de transition (cut franc vs fondu) : seules les coupes nettes sont détectées",
            "identification de la musique",
            "étalonnage / effets visuels",
        ],
    }
    write_json(reel_dir / "analysis.json", analysis)
    (reel_dir / "report.md").write_text(render_report(analysis, transcript.get("text")), encoding="utf-8")
    if not (reel_dir / "decode.json").exists():
        tpl = read_json(TEMPLATES_DIR / "decode.template.json")
        tpl["reel_id"] = analysis["reel_id"]
        write_json(reel_dir / "decode.json", tpl)
    log(f"analyse écrite: {reel_dir / 'analysis.json'}")
    return analysis


def render_report(a: dict, transcript_text: str | None) -> str:
    t, p, au = a["technical"], a["pacing"], a["audio"]
    sl = p.get("shot_length_s") or {}
    src = a.get("source", {})
    lines = [
        f"# Rapport d'analyse — {a['reel_id']}",
        "",
        f"_Généré le {a['generated_at']} par reelkit {a['tool_version']}. Données mesurées (ffprobe/ffmpeg)._",
        "",
        "## Source",
        f"- Type : {src.get('source_type', '?')}" + (f" — {src['source_url']}" if src.get("source_url") else ""),
    ]
    if src.get("uploader"):
        lines.append(f"- Compte : {src['uploader']}")
    if src.get("description"):
        lines.append(f"- Légende : {src['description'][:600]}")
    lines += [
        "",
        "## Technique",
        f"- Durée : {t['duration_s']} s — {t['width']}x{t['height']} ({t['aspect_ratio']}, {t['orientation']}) — {t['fps']} i/s",
        f"- Codecs : {t['video_codec']} / {t['audio_codec'] or 'pas d’audio'} — {t['bitrate_kbps']} kb/s",
        "",
        "## Rythme de montage",
        f"- Plans : {p['shots']} — coupes/min : {p['cuts_per_minute']} — 1re coupe à : {p['first_cut_at_s']} s",
        f"- Durée des plans : médiane {sl.get('median')} s, moyenne {sl.get('mean')} s, min {sl.get('min')} s, max {sl.get('max')} s",
        f"- Plans dans les 3 premières secondes : {p['shots_in_first_3s']}",
        f"- Seuil de détection : {a['scene_threshold']} (augmentez si trop de fausses coupes, baissez si coupes manquées)",
        "",
        "| Plan | Début | Fin | Durée |",
        "|---|---|---|---|",
    ]
    lines += [f"| {s['index']} | {fmt_ts(s['start'])} | {fmt_ts(s['end'])} | {s['duration']} s |" for s in a["shots"]]
    lines += ["", "## Audio"]
    if au.get("has_audio"):
        lines += [f"- Loudness intégrée : {au.get('integrated_lufs')} LUFS — true peak {au.get('true_peak_dbtp')} dBTP — LRA {au.get('loudness_range_lu')} LU",
                  f"- Part de silence : {au.get('silence_ratio')}"]
    else:
        lines.append("- Pas de piste audio.")
    tsc = a["transcript"]
    lines += ["", "## Transcription", f"- Statut : {tsc.get('status')} ({tsc.get('source') or tsc.get('reason', '')})"]
    if tsc.get("status") == "ok":
        lines += [f"- Langue : {tsc.get('language')} — mots : {tsc.get('words')} — débit : {tsc.get('words_per_minute_speech')} mots/min",
                  f"- Mode de contenu : **{a['content_mode']}** (seuil : <15 mots = text_overlay)",
                  "", "> " + (transcript_text or "")[:3000]]
    lines += ["", "## Images clés", f"- Planche contact : `{a['contact_sheet']}`", ""]
    lines += [f"- `{f['file']}` — {f['timecode']} (plan {f['shot']})" for f in a["keyframes"]]
    lines += ["", "## Non mesuré automatiquement"] + [f"- {x}" for x in a["not_measured"]]
    lines += ["", "## Étape suivante (Claude)",
              "Lire `contact_sheet.jpg`, puis les frames pertinentes, et remplir `decode.json` "
              "(chaque affirmation cite une frame ou un passage de transcription ; inconnu = null)."]
    return "\n".join(lines) + "\n"
