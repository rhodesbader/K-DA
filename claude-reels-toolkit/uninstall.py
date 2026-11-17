#!/usr/bin/env python3
"""Remove the toolkit's skills. Only deletes folders carrying the toolkit marker.

  python uninstall.py [--project PATH] [--user] [--venv] [--purge-workspace]

The analysis workspace (reels-workspace/) is kept unless --purge-workspace is given.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

MARKER = ".reelkit-installed"
SKILLS = ["reel-studio", "reel-analyze", "reel-style", "reel-adapt", "reel-render"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--user", action="store_true", help="désinstaller de ~/.claude/skills")
    ap.add_argument("--venv", action="store_true", help="supprimer aussi .venv-reelkit")
    ap.add_argument("--purge-workspace", action="store_true", help="supprimer reels-workspace/ (analyses, rendus)")
    args = ap.parse_args()
    project = Path(args.project).expanduser().resolve()
    target = (Path.home() / ".claude" / "skills") if args.user else (project / ".claude" / "skills")
    for name in SKILLS:
        d = target / name
        if not d.exists():
            continue
        if not (d / MARKER).exists():
            print(f"ignoré (pas installé par le toolkit): {d}")
            continue
        shutil.rmtree(d)
        print(f"supprimé: {d}")
    if args.venv and (project / ".venv-reelkit").exists():
        shutil.rmtree(project / ".venv-reelkit")
        print("supprimé: .venv-reelkit")
    if args.purge_workspace and (project / "reels-workspace").exists():
        shutil.rmtree(project / "reels-workspace")
        print("supprimé: reels-workspace/")
    print("Désinstallation terminée. Relancez la session Claude Code pour que la liste des skills se mette à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
