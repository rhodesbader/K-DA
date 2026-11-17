"""Acquisition: download a reel with yt-dlp, or import a local file."""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import sys
from pathlib import Path

from .util import VIDEO_EXTS, ReelkitError, log, now_iso, read_json, run, slugify, write_json

INSTAGRAM_RE = re.compile(
    r"^https://(?:www\.)?(?:instagram\.com|instagr\.am)/(?:[A-Za-z0-9_.]+/)?(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)/?(?:\?.*)?$"
)
KEEP_FIELDS = ("id", "title", "uploader", "uploader_id", "channel", "description", "upload_date",
               "timestamp", "duration", "view_count", "like_count", "comment_count", "webpage_url",
               "extractor_key", "width", "height", "fps")
NETWORK_HINTS = ("proxy", "urlopen error", "name resolution", "getaddrinfo", "timed out",
                 "connection refused", "network is unreachable")
LOGIN_HINTS = ("login", "log in", "cookies", "rate-limit", "rate limit", "private", "401", "403",
               "not available", "unavailable")


def ytdlp_cmd() -> list:
    if importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    raise ReelkitError("yt-dlp absent. `pip install -r requirements.txt`, ou fournissez un fichier vidéo local.")


def reel_id_for(source: str, any_site: bool) -> str:
    m = INSTAGRAM_RE.match(source)
    if m:
        return m.group(1)
    if not source.startswith("https://"):
        raise ReelkitError(f"Source invalide (ni fichier existant, ni URL https): {source}")
    if not any_site:
        raise ReelkitError(
            "URL non Instagram. Ajoutez --any-site pour les autres plateformes prises en charge par yt-dlp "
            "(TikTok, YouTube Shorts...), dans le respect de leurs conditions d'utilisation.")
    return "web-" + hashlib.sha1(source.encode()).hexdigest()[:10]


def _existing_source(reel_dir: Path):
    return next((p for p in sorted(reel_dir.glob("source.*")) if p.suffix.lower() in VIDEO_EXTS), None)


def grab(source: str, workspace: Path, any_site=False, cookies_from_browser=None, cookies=None,
         force=False) -> Path:
    local = Path(source).expanduser()
    if local.is_file():
        return _import_local(local, workspace, force)

    rid = reel_id_for(source, any_site)
    reel_dir = workspace / "reels" / rid
    existing = _existing_source(reel_dir) if reel_dir.exists() else None
    if existing and not force:
        log(f"déjà téléchargé: {existing} (utilisez --force pour retélécharger)")
        return reel_dir
    reel_dir.mkdir(parents=True, exist_ok=True)
    for old in reel_dir.glob("source.*"):
        old.unlink()

    cmd = ytdlp_cmd() + [
        "--no-playlist", "--no-progress", "--restrict-filenames",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "--write-info-json",
        "-o", str(reel_dir / "source.%(ext)s"),
    ]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    if cookies:
        cmd += ["--cookies", str(Path(cookies).expanduser())]
    cmd.append(source)
    log("téléchargement via yt-dlp…")
    proc = run(cmd, check=False)
    video = _existing_source(reel_dir)
    if proc.returncode != 0 or not video:
        err = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
        if not any(reel_dir.iterdir()):
            reel_dir.rmdir()  # leave no empty folder behind
        low, hint = " ".join(err).lower(), ""
        if any(h in low for h in NETWORK_HINTS):
            hint = ("\nIndice: problème réseau (proxy, DNS, pare-feu). Vérifiez l'accès à la plateforme depuis cette "
                    "machine, ou téléchargez la vidéo vous-même et donnez le chemin du fichier.")
        elif any(h in low for h in LOGIN_HINTS):
            hint = ("\nIndice: contenu privé, connexion requise ou limitation de débit. Réessayez plus tard, "
                    "ou passez --cookies-from-browser firefox (votre propre session), ou téléchargez la vidéo "
                    "vous-même et donnez le chemin du fichier.")
        raise ReelkitError("échec du téléchargement:\n" + "\n".join(err) + hint)

    info_path = reel_dir / "source.info.json"
    info = read_json(info_path) if info_path.exists() else {}
    if info_path.exists():
        info_path.unlink()  # contains signed media URLs; we only keep a minimal subset
    meta = {k: info.get(k) for k in KEEP_FIELDS if info.get(k) is not None}
    meta.update({"reel_id": rid, "source_type": "url", "source_url": source, "fetched_at": now_iso(),
                 "file": video.name})
    write_json(reel_dir / "meta.json", meta)
    log(f"OK: {video}")
    return reel_dir


def _import_local(path: Path, workspace: Path, force: bool) -> Path:
    if path.suffix.lower() not in VIDEO_EXTS:
        raise ReelkitError(f"Extension non prise en charge: {path.suffix}")
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        h.update(fh.read(4 * 1024 * 1024))
    h.update(str(path.stat().st_size).encode())
    rid = f"local-{slugify(path.stem, 30)}-{h.hexdigest()[:8]}"
    reel_dir = workspace / "reels" / rid
    dest = reel_dir / f"source{path.suffix.lower()}"
    if dest.exists() and not force:
        log(f"déjà importé: {dest}")
        return reel_dir
    reel_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    write_json(reel_dir / "meta.json", {"reel_id": rid, "source_type": "local", "original_name": path.name,
                                        "fetched_at": now_iso(), "file": dest.name})
    log(f"importé: {dest}")
    return reel_dir
