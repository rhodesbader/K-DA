#!/usr/bin/env python3
"""Install the Claude Reels Toolkit skills into a Claude Code project (default) or user scope.

  python install.py                      # into the current directory's .claude/skills/
  python install.py --project ~/mon-projet
  python install.py --project . --venv   # + local virtualenv .venv-reelkit with optional deps
  python install.py --user               # ~/.claude/skills (global: only if you really want it)
  python install.py --check              # validate the skills without installing

Safe by design: never overwrites a skill folder it did not create (unless --force),
never touches settings.json or CLAUDE.md, never needs admin rights.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_SRC = HERE / "skills"
MARKER = ".reelkit-installed"
VERSION = "1.0.0"


def skill_dirs() -> list:
    return sorted(p for p in SKILLS_SRC.iterdir() if (p / "SKILL.md").is_file())


def validate_skill(path: Path) -> list:
    """Return a list of problems (empty = valid)."""
    problems = []
    text = (path / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return ["frontmatter YAML absent (doit commencer et finir par ---)"]
    fields = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if ":" not in line or line.startswith((" ", "\t")):
            problems.append(f"ligne de frontmatter inattendue: {line!r}")
            continue
        k, v = line.split(":", 1)
        fields[k.strip()] = v.strip()
    name, desc = fields.get("name", ""), fields.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        problems.append(f"name invalide: {name!r}")
    if name != path.name:
        problems.append(f"name ({name}) différent du dossier ({path.name})")
    if not desc or len(desc) > 1024:
        problems.append(f"description vide ou > 1024 caractères ({len(desc)})")
    if desc[:1] in "\"'[{>|&*!%@`":
        problems.append("description commençant par un caractère YAML spécial")
    if ": " in desc and not desc.startswith(("'", '"')):
        problems.append("description contenant ': ' non citée (YAML ambigu)")
    if len(text[m.end():].strip()) < 50:
        problems.append("corps du skill vide")
    return problems


def check() -> bool:
    ok = True
    for d in skill_dirs():
        probs = validate_skill(d)
        print(f"[{'OK' if not probs else 'KO'}] {d.name}" + "".join(f"\n      - {p}" for p in probs))
        ok &= not probs
    engine = SKILLS_SRC / "reel-studio" / "scripts" / "reelkit.py"
    print(f"[{'OK' if engine.is_file() else 'KO'}] moteur {engine.relative_to(HERE)}")
    return ok and engine.is_file()


def install(target: Path, force: bool, dry: bool) -> list:
    if not dry:
        target.mkdir(parents=True, exist_ok=True)
    done = []
    for src in skill_dirs():
        dst = target / src.name
        if dst.exists() and not (dst / MARKER).exists() and not force:
            raise SystemExit(f"STOP: {dst} existe et n'a pas été créé par ce toolkit. "
                             "Renommez-le ou relancez avec --force si vous voulez le remplacer.")
        print(f"{'(simulation) ' if dry else ''}installe {src.name} -> {dst}")
        if not dry:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (dst / MARKER).write_text(f"claude-reels-toolkit {VERSION}\n", encoding="utf-8")
        done.append(dst)
    return done


def make_venv(project: Path) -> Path:
    venv = project / ".venv-reelkit"
    if not venv.exists():
        print(f"création de l'environnement virtuel {venv}")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    print("installation des dépendances optionnelles (yt-dlp, faster-whisper)…")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip", "-q"])
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(HERE / "requirements.txt"), "-q"])
    return py


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="racine du projet Claude Code (défaut: dossier courant)")
    ap.add_argument("--user", action="store_true", help="installer dans ~/.claude/skills (portée globale)")
    ap.add_argument("--venv", action="store_true", help="créer .venv-reelkit et installer requirements.txt")
    ap.add_argument("--force", action="store_true", help="remplacer des dossiers de skills existants")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="valider les skills sans installer")
    args = ap.parse_args()

    if sys.version_info < (3, 9):
        print("Python 3.9+ requis.")
        return 1
    if not check():
        print("Skills invalides : installation annulée.")
        return 1
    if args.check:
        return 0

    project = Path(args.project).expanduser().resolve()
    target = (Path.home() / ".claude" / "skills") if args.user else (project / ".claude" / "skills")
    if args.user:
        print("ATTENTION: installation utilisateur (globale) dans", target)
    install(target, args.force, args.dry_run)
    if args.dry_run:
        return 0

    py = Path(sys.executable)
    if args.venv:
        py = make_venv(project)
    engine = target / "reel-studio" / "scripts" / "reelkit.py"
    print("\n--- diagnostic ---")
    subprocess.call([str(py), str(engine), "doctor"])
    print(f"""
Installé. Prochaines étapes :
  1. Ajoutez au .gitignore du projet (si vous versionnez) :  reels-workspace/  .venv-reelkit/
  2. Ouvrez Claude Code dans {project} (ou relancez la session) puis tapez /reel-studio
  3. Auto-test : {py} {engine} selftest
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
