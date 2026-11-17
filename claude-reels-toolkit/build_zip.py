#!/usr/bin/env python3
"""Build dist/claude-reels-toolkit-<version>.zip from the toolkit files, then re-open and check it."""
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "skills" / "reel-studio" / "scripts"))
from reelkit.util import VERSION  # noqa: E402

EXCLUDE_DIRS = {"__pycache__", "dist", ".venv-reelkit", ".venv", "reels-workspace", ".git"}
REQUIRED = ["README.md", "INSTALL.md", "USAGE.md", "FIDELITY.md", "TESTS.md", "MAINTENANCE.md", "LICENSES.md",
            "LICENSE", "requirements.txt", ".env.example", ".gitignore", "install.py", "uninstall.py",
            "skills/reel-studio/SKILL.md", "skills/reel-studio/scripts/reelkit.py",
            "skills/reel-studio/config/defaults.json", "skills/reel-studio/templates/decode.template.json",
            "skills/reel-analyze/SKILL.md", "skills/reel-style/SKILL.md", "skills/reel-adapt/SKILL.md",
            "skills/reel-render/SKILL.md", "tests/test_pipeline.py", "examples/script-exemple.txt"]


def files():
    for p in sorted(HERE.rglob("*")):
        rel = p.relative_to(HERE)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.suffix != ".pyc" and p.name != ".env":
            yield p, rel


def main():
    out = HERE / "dist" / f"claude-reels-toolkit-{VERSION}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p, rel in files():
            info = zipfile.ZipInfo(f"claude-reels-toolkit/{rel.as_posix()}", date_time=(2026, 10, 13, 0, 0, 0))
            info.external_attr = (0o755 if p.suffix == ".py" else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        names = set(z.namelist())
    missing = [r for r in REQUIRED if f"claude-reels-toolkit/{r}" not in names]
    leaks = [n for n in names if n.endswith("/.env") or any(k in n for k in ("cookies", "reels-workspace", ".venv"))]
    print(f"{out} — {len(names)} fichiers, {out.stat().st_size // 1024} Ko")
    if bad or missing or leaks:
        print("ÉCHEC", {"corrompu": bad, "manquants": missing, "fuites": leaks})
        return 1
    print("ZIP vérifié : intègre, complet, sans données de travail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
