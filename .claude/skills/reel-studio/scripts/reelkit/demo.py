"""Synthetic, copyright-free demo media generated with FFmpeg (for self-tests)."""
from __future__ import annotations

from pathlib import Path

from .util import ffmpeg

SOURCES = [
    "testsrc2=size={w}x{h}:rate=30",
    "smptebars=size={w}x{h}:rate=30",
    "mandelbrot=size={w}x{h}:rate=30",
    "rgbtestsrc=size={w}x{h}:rate=30",
    "color=c=0x1E3A8A:size={w}x{h}:rate=30",
]


def make_reel(path: Path, shot_lengths: list, w=720, h=1280, tone=440) -> Path:
    """A vertical 'reel' with hard cuts at known times and a tone + gaps as audio."""
    inputs, fc = [], []
    for i, d in enumerate(shot_lengths):
        inputs += ["-f", "lavfi", "-t", f"{d}", "-i", SOURCES[i % len(SOURCES)].format(w=w, h=h)]
        fc.append(f"[{i}:v]format=yuv420p,setsar=1[v{i}]")
    total = sum(shot_lengths)
    n = len(shot_lengths)
    inputs += ["-f", "lavfi", "-t", f"{total}", "-i", f"sine=frequency={tone}:sample_rate=48000"]
    fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]")
    fc.append(f"[{n}:a]volume='if(lt(mod(t,2),1.5),0.3,0)':eval=frame[a]")
    ffmpeg(*inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-shortest", "-y", str(path))
    return path


def make_media(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, src in enumerate(SOURCES[:3]):
        p = out_dir / f"clip_{i + 1}.mp4"
        ffmpeg("-f", "lavfi", "-t", "6", "-i", src.format(w=1280, h=720), "-f", "lavfi", "-t", "6",
               "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000", "-shortest",
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(p))
        clips.append(p)
    img = out_dir / "still.png"
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=size=1080x1350", "-frames:v", "1", "-y", str(img))
    vo = out_dir / "voiceover.wav"
    ffmpeg("-f", "lavfi", "-t", "9", "-i", "sine=frequency=220:sample_rate=48000",
           "-af", "volume='if(lt(mod(t,1),0.7),0.5,0)':eval=frame", "-y", str(vo))
    music = out_dir / "music.wav"
    ffmpeg("-f", "lavfi", "-t", "4", "-i", "sine=frequency=660:sample_rate=48000", "-y", str(music))
    return {"clips": clips, "image": img, "voiceover": vo, "music": music}
