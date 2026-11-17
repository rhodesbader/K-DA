"""Render a timeline.json to a vertical MP4 with FFmpeg.

Pipeline: each segment -> normalised intermediate (same size/fps/codec, with
an audio track) -> lossless concat -> final pass (captions burn-in, voice-over,
music with ducking, EBU R128 loudness normalisation).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .util import ReelkitError, ffmpeg, has_stream, log, media_duration, read_json, write_json
from .verify import verify


def _resolve(base: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    q = q if q.is_absolute() else (base / q)
    if not q.is_file():
        raise ReelkitError(f"Fichier référencé introuvable: {q}")
    return q.resolve()


def _segment_cmd(seg: dict, src: Path, out: Path, W: int, H: int, fps: int, enc: list) -> list:
    dur = float(seg["duration"])
    nframes = max(int(round(dur * fps)), 1)
    fit = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if seg.get("fit", "cover") == "cover"
           else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black")
    if seg["kind"] == "image":
        if seg.get("motion") == "zoom_in":
            vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                  f"zoompan=z='min(zoom+{0.10 / nframes:.6f},1.10)':d={nframes}:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={fps}")
            inputs = ["-i", str(src)]
        else:
            vf = fit + f",fps={fps}"
            inputs = ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(src)]
        audio_in, amap = ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"], "1:a:0"
    else:
        src_dur = media_duration(src)
        tpad = max(dur - max(src_dur - float(seg.get("in", 0)), 0), 0)
        vf = fit + f",fps={fps}" + (f",tpad=stop_mode=clone:stop_duration={tpad + 0.1:.3f}" if tpad > 0.01 else "")
        inputs = ["-ss", f"{float(seg.get('in', 0)):.3f}", "-t", f"{dur:.3f}", "-i", str(src)]
        if seg.get("keep_audio") and has_stream(src, "audio"):
            audio_in, amap = [], "0:a:0"
        else:
            audio_in, amap = ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"], "1:a:0"
    vf += ",setsar=1,format=yuv420p"
    return [*inputs, *audio_in, "-map", "0:v:0", "-map", amap, "-vf", vf,
            "-af", "aresample=48000,apad", "-frames:v", str(nframes), "-t", f"{dur:.3f}",
            *enc, "-y", str(out)]


def render(timeline_path, out_path=None, keep_temp=False, draft=False) -> dict:
    tl_path = Path(timeline_path).resolve()
    base = tl_path.parent
    tl = read_json(tl_path)
    o = tl["output"]
    W, H, fps = int(o["width"]), int(o["height"]), int(o["fps"])
    if draft:  # fast preview: half resolution, quick preset
        W, H = W // 2 // 2 * 2, H // 2 // 2 * 2
    crf = str(o.get("crf", 18) if not draft else 28)
    preset = "veryfast" if draft else o.get("preset", "medium")
    out = Path(out_path).resolve() if out_path else base / o.get("file", "render.mp4")
    tmp = base / ".render_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    enc = ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p", "-r", str(fps),
           "-c:a", "aac", "-b:a", o.get("audio_bitrate", "192k"), "-ar", "48000", "-ac", "2"]
    try:
        parts = []
        for seg in tl["segments"]:
            src = _resolve(base, seg["media"])
            part = tmp / f"seg_{seg['index']:03d}.mp4"
            log(f"plan {seg['index']}/{len(tl['segments'])} ({seg['kind']}, {seg['duration']}s)")
            ffmpeg(*_segment_cmd(seg, src, part, W, H, fps, enc))
            parts.append(part.name)
        (tmp / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        ffmpeg("-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-y", "concat.mp4", cwd=tmp)

        a = tl["audio"]
        vo, music = _resolve(base, a.get("voiceover")), _resolve(base, a.get("music"))
        total = float(o["duration_s"])
        inputs, fc, mix = ["-i", str(tmp / "concat.mp4")], [], []
        ass = tl.get("captions", {}).get("ass")
        if ass:
            shutil.copy2(_resolve(base, ass), tmp / "captions.ass")  # relative name: avoids path escaping (Windows)
            fc.append("[0:v]subtitles=filename=captions.ass[v]")  # libass scales PlayRes to frame size
        else:
            fc.append("[0:v]null[v]")
        if a.get("original_audio"):
            fc.append(f"[0:a]volume={a.get('original_audio_gain_db', 0)}dB[orig]")
            mix.append("[orig]")
        idx = 1
        if vo:
            inputs += ["-i", str(vo)]
            fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                      f"volume={a.get('voiceover_gain_db', 0)}dB,asplit=2[vo][vokey]")
            mix.append("[vo]")
            idx += 1
        if music:
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
                      f"afade=t=out:st={max(total - 1.0, 0):.3f}:d=1,volume={a.get('music_gain_db', -16)}dB[mus0]")
            if vo and a.get("duck_music_under_voice", True):
                fc.append("[mus0][vokey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mus]")
            else:
                fc.append("[mus0]anull[mus]")
                if vo:
                    fc.append("[vokey]anullsink")
            mix.append("[mus]")
        elif vo:
            fc.append("[vokey]anullsink")
        loud = (f"loudnorm=I={o.get('loudness_target_lufs', -14)}:TP={o.get('true_peak_dbtp', -1.5)}:LRA=11,"
                "aresample=48000,apad")
        if not mix:
            fc.append("[0:a]anull[a]")  # silent track kept so players and platforms get a valid audio stream
        elif len(mix) == 1:
            fc.append(f"{mix[0]}{loud}[a]")
        else:
            fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=longest:normalize=0,{loud}[a]")
        ffmpeg(*inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
               "-t", f"{total:.3f}", *enc, "-movflags", "+faststart", "-y", str(out), cwd=tmp)
    finally:
        if not keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)
    log(f"rendu: {out}")
    has_sound = bool(tl["audio"].get("voiceover") or tl["audio"].get("music") or tl["audio"].get("original_audio"))
    expected = {"width": W, "height": H, "fps": fps, "duration_s": float(o["duration_s"]),
                "loudness_target_lufs": o.get("loudness_target_lufs", -14) if has_sound else None}
    report = verify(out, expected)
    report["timeline"] = tl_path.name
    report["draft"] = draft
    write_json(out.with_suffix(".verify.json"), report)
    return report
