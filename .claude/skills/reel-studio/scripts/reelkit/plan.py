"""Build an editable timeline (timeline.json) + captions (SRT and styled ASS)
from a style profile, a list of media and a script / voice-over."""
from __future__ import annotations

import re
from pathlib import Path

from . import transcribe as tr
from .style import derive_rules
from .util import (IMAGE_EXTS, VERSION, ReelkitError, expand_media, ffprobe_json, load_defaults, log,
                   media_duration, now_iso, read_json, write_json, write_srt)

RHYTHM = [1.0, 0.8, 1.2, 0.9, 1.1, 0.85, 1.15]  # deterministic variation around the median


def load_rules(style_path) -> tuple:
    if style_path:
        style = read_json(style_path)
        return style.get("editing_rules") or derive_rules(style), style.get("name", Path(style_path).stem)
    return derive_rules({"metrics": {}, "traits": {}}), "defaults"


def shot_lengths(total: float, rules: dict) -> list:
    med, lo, hi = rules["shot_median_s"], rules["shot_min_s"], rules["shot_max_s"]
    first = min(rules["first_shot_max_s"] or med, med)
    first = max(first, lo)
    lengths, t, i = [], 0.0, 0
    while total - t > 1e-6:
        want = first if i == 0 else min(max(med * RHYTHM[i % len(RHYTHM)], lo), hi)
        rem = total - t
        if rem - want < lo:  # never leave a sliver shorter than the minimum
            want = rem if (rem <= hi * 1.25 or rem < 2 * lo) else rem / 2
        lengths.append(round(want, 3))
        t += want
        i += 1
    return lengths


def _media_info(path: Path) -> dict:
    if path.suffix.lower() in IMAGE_EXTS:
        return {"kind": "image", "duration": None, "has_audio": False}
    info = ffprobe_json(path)
    return {"kind": "video", "duration": media_duration(path),
            "has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", []))}


def assign_media(media: list, lengths: list, rules: dict, timeline_dir: Path, keep_audio: bool) -> list:
    infos = {m: _media_info(m) for m in media}
    offsets = {m: 0.0 for m in media}
    segs, start = [], 0.0
    for i, dur in enumerate(lengths):
        m = media[i % len(media)]
        info = infos[m]
        seg = {"index": i + 1, "media": _rel(m, timeline_dir), "kind": info["kind"],
               "start": round(start, 3), "duration": dur, "fit": "cover"}
        if info["kind"] == "image":
            seg.update({"in": 0.0, "motion": rules.get("image_motion")})
        else:
            src_dur = info["duration"] or dur
            if src_dur < dur:
                seg.update({"in": 0.0, "note": f"source plus courte ({src_dur:.2f}s) que le plan : image figée en fin"})
            else:
                if offsets[m] + dur > src_dur:
                    offsets[m] = 0.0
                seg["in"] = round(offsets[m], 3)
                offsets[m] += dur
            seg["keep_audio"] = keep_audio and info["has_audio"]
        segs.append(seg)
        start += dur
    return segs


def _rel(path: Path, base: Path) -> str:
    try:
        return Path(path).resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


# ----------------------------------------------------------------- captions

def chunk_words(words: list, per: int) -> list:
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        ends_sentence = re.search(r"[.!?…:;]$", w["word"])
        if len(cur) >= per or ends_sentence:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [{"start": c[0]["start"], "end": c[-1]["end"], "text": " ".join(w["word"] for w in c)} for c in chunks]


def words_from_script(text: str, total: float, lead_in: float = 0.15) -> list:
    tokens = text.split()
    if not tokens:
        return []
    weights = [len(t) + 2 for t in tokens]
    span = total - lead_in - 0.2
    scale, t, out = span / sum(weights), lead_in, []
    for tok, wgt in zip(tokens, weights):
        out.append({"start": t, "end": t + wgt * scale, "word": tok})
        t += wgt * scale
    return out


def _ass_color(hexcolor: str, alpha: str = "00") -> str:
    h = hexcolor.strip("#")
    return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _ass_time(sec: float) -> str:
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def write_ass(cues: list, cap: dict, width: int, height: int, path: Path) -> Path:
    align = {"top": 8, "center": 5}.get(cap["position"], 2)
    margin_v = 0 if align == 5 else (int(height * 0.12) if align == 8 else cap["margin_v"])
    hl, primary = _ass_color(cap["highlight_color"]), _ass_color(cap["primary_color"])
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Reel,{cap['font']},{cap['size']},{primary},{hl},"
        f"{_ass_color(cap['outline_color'])},&H64000000,{-1 if cap['bold'] else 0},0,0,0,100,100,0,0,1,"
        f"{cap['outline']},2,{align},80,80,{margin_v},1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for c in cues:
        text = c["text"].upper() if cap["uppercase"] else c["text"]
        toks = [_ass_escape(t) for t in text.split()]
        if len(toks) > 1:  # emphasise the longest word, a common Reels caption device
            k = max(range(len(toks)), key=lambda j: len(re.sub(r"\W", "", toks[j])))
            toks[k] = "{\\c" + hl + "}" + toks[k] + "{\\c" + primary + "}"
        lines.append(f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Reel,,0,0,0,,{' '.join(toks)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ----------------------------------------------------------------- main

def plan(out_dir, media, style=None, script=None, voiceover=None, music=None, duration=None,
         keep_original_audio=False, transcribe_voiceover=False, language=None) -> Path:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rules, style_name = load_rules(style)
    d = load_defaults()
    out = d["output"]
    media = expand_media(media)
    text = None
    if script:
        sp = Path(script).expanduser()
        text = sp.read_text(encoding="utf-8").strip() if sp.is_file() else str(script).strip()

    vo = Path(voiceover).resolve() if voiceover else None
    if vo and not vo.is_file():
        raise ReelkitError(f"Voix off introuvable: {voiceover}")
    if duration:
        total = float(duration)
    elif vo:
        total = media_duration(vo) + 0.3
    elif text:
        total = max(len(text.split()) / rules["words_per_minute"] * 60 + 0.6, 3.0)
    else:
        total = float(rules["target_duration_s"])
    total = round(total, 3)

    lengths = shot_lengths(total, rules)
    segments = assign_media(media, lengths, rules, out_dir, keep_original_audio and not vo)

    cap = rules["captions"]
    caption_source, words = None, []
    if vo and transcribe_voiceover:
        data = tr.transcribe(vo, language=language)
        write_json(out_dir / "voiceover.transcript.json", data)
        words = tr.words_from_segments(data["segments"])
        caption_source = "transcription de la voix off (timing mot à mot)"
    elif text:
        words = words_from_script(text, total)
        caption_source = "script réparti proportionnellement (timing approximatif)"
    cues = chunk_words(words, int(rules["words_per_caption"])) if words else []
    files = {}
    if cues and cap.get("enabled", True):
        write_srt(cues, out_dir / "captions.srt")
        write_ass(cues, cap, out["width"], out["height"], out_dir / "captions.ass")
        files = {"srt": "captions.srt", "ass": "captions.ass"}

    mix = d["audio_mix"]
    timeline = {
        "schema": "reelkit.timeline/1",
        "tool_version": VERSION,
        "generated_at": now_iso(),
        "style": style_name,
        "rules_used": rules,
        "output": {**out, "duration_s": total, "file": "render.mp4"},
        "segments": segments,
        "audio": {
            "voiceover": _rel(vo, out_dir) if vo else None,
            "music": _rel(Path(music).resolve(), out_dir) if music else None,
            "original_audio": any(s.get("keep_audio") for s in segments),
            **mix,
        },
        "captions": {**files, "source": caption_source, "count": len(cues), "style": cap},
        "manual_steps": _manual_steps(vo, music, cues),
    }
    path = write_json(out_dir / "timeline.json", timeline)
    log(f"timeline: {path} — {len(segments)} plans, {total}s, {len(cues)} sous-titres")
    return path


def _manual_steps(vo, music, cues) -> list:
    steps = []
    if not vo:
        steps.append("Aucune voix off : enregistrez-la (ou utilisez un TTS de votre choix) puis relancez `plan --voiceover`.")
    if cues and not vo:
        steps.append("Sous-titres calés sur une estimation : relancez avec --voiceover … --transcribe-voiceover pour un calage mot à mot.")
    if music:
        steps.append("Vérifiez que vous détenez les droits de la musique pour une diffusion publique.")
    steps.append("Relisez timeline.json : chaque plan (média, point d'entrée, durée) est modifiable à la main avant `render`.")
    return steps
