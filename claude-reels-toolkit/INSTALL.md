# Installation

Durée : 2 min (sans transcription) à 5 min (avec yt-dlp + faster-whisper). Aucun droit administrateur requis si Python et FFmpeg sont déjà présents.

## 1. Prérequis système

| Outil | Vérifier | Installer si absent |
|---|---|---|
| Python ≥ 3.9 | `python3 --version` (Windows : `py --version`) | python.org, `brew install python`, `sudo apt install python3 python3-venv` |
| FFmpeg complet | `ffmpeg -version` | macOS `brew install ffmpeg` · Ubuntu/Debian `sudo apt install ffmpeg` · Windows `winget install Gyan.FFmpeg` (puis rouvrir le terminal) |
| Claude Code | `claude --version` | https://claude.ai/code |

`sudo` / `winget` modifient le système : à lancer vous-même.

## 2. Installation automatique (recommandée)

Décompressez le ZIP, puis depuis le dossier `claude-reels-toolkit/` :

```bash
# macOS / Linux
python3 install.py --project /chemin/de/votre/projet --venv

# Windows (PowerShell)
py install.py --project C:\chemin\de\votre\projet --venv
```

Ce que fait le script (lisible dans `install.py`) :

1. valide le frontmatter des 5 skills ;
2. copie `skills/*` vers `<projet>/.claude/skills/` et marque chaque dossier (`.reelkit-installed`) ;
3. refuse d'écraser un dossier de skill qu'il n'a pas créé (sauf `--force`) ;
4. avec `--venv` : crée `<projet>/.venv-reelkit/` et y installe `requirements.txt` (yt-dlp, faster-whisper) — rien n'est installé dans votre Python système ;
5. lance le diagnostic `doctor`.

Il ne modifie **ni** `~/.claude/`, **ni** `settings.json`, **ni** `CLAUDE.md`, **ni** vos fichiers shell.

Options : `--dry-run` (simulation), `--check` (validation seule), `--user` (installation globale dans `~/.claude/skills`, à n'utiliser que si vous voulez les skills dans tous vos projets).

Ajoutez au `.gitignore` de votre projet : `reels-workspace/` et `.venv-reelkit/`.

## 3. Installation manuelle (secours)

```bash
mkdir -p /chemin/projet/.claude/skills
cp -R claude-reels-toolkit/skills/* /chemin/projet/.claude/skills/
# optionnel
python3 -m venv /chemin/projet/.venv-reelkit
/chemin/projet/.venv-reelkit/bin/pip install -r claude-reels-toolkit/requirements.txt
```

Windows : copiez le contenu de `skills\` dans `projet\.claude\skills\` ; le venv est `projet\.venv-reelkit\Scripts\python.exe`.

## 4. Vérifier

```bash
cd /chemin/projet
.venv-reelkit/bin/python .claude/skills/reel-studio/scripts/reelkit.py doctor     # sans venv : python3 …
.venv-reelkit/bin/python .claude/skills/reel-studio/scripts/reelkit.py selftest   # ~30 s, doit finir par RÉUSSI
```

Dans Claude Code (session ouverte **après** l'installation — les skills sont chargés au démarrage) :

- tapez `/` : `reel-studio`, `reel-analyze`, `reel-style`, `reel-adapt`, `reel-render` doivent apparaître ;
- ou demandez : « Quels skills reel-* sont disponibles ? Lance le diagnostic reel-studio. »

Si rien n'apparaît : vérifiez que Claude Code est lancé depuis la racine du projet et que `.claude/skills/<nom>/SKILL.md` existe ; relancez la session.

## 5. Transcription : premier usage

Le premier `analyze` avec transcription télécharge le modèle Whisper choisi depuis huggingface.co (`small` ≈ 480 Mo, `base` ≈ 140 Mo, `tiny` ≈ 75 Mo). Machine sans accès : téléchargez un modèle CTranslate2 (ex. `Systran/faster-whisper-small`) ailleurs, copiez le dossier, puis `export REELKIT_WHISPER_MODEL=/chemin/du/modele`. Alternative sans modèle : `--srt votre_transcription.srt`.

## 6. Désinstaller

```bash
python3 claude-reels-toolkit/uninstall.py --project /chemin/projet            # skills uniquement
python3 claude-reels-toolkit/uninstall.py --project /chemin/projet --venv     # + environnement virtuel
python3 claude-reels-toolkit/uninstall.py --project /chemin/projet --purge-workspace   # + analyses et rendus
```

Seuls les dossiers marqués `.reelkit-installed` sont supprimés. Installation globale : ajoutez `--user`.
