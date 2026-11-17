---
name: reel-studio
description: Orchestrator and diagnostics for the Claude Reels Toolkit (reelkit engine, FFmpeg). Use when the user wants the full Reels workflow end to end (analyze reference reels, build a creator style profile, plan and render a new vertical video), asks what the toolkit can do, wants to check prerequisites, troubleshoot a failing step, see the workspace status, or run the self-test. Also the place where the engine path and shared conventions are defined for the other reel-* skills.
---

# Reel Studio — orchestration et diagnostic

Tu coordonnes le pipeline Reels. Les étapes spécialisées vivent dans d'autres skills ; ici tu fixes les conventions, vérifies les prérequis et enchaînes les étapes sans travail inutile.

## Conventions partagées (valables pour tous les skills reel-*)

**Moteur** — un seul script Python, sans dépendance hors FFmpeg pour le cœur :

- Installation projet : `.claude/skills/reel-studio/scripts/reelkit.py`
- Installation utilisateur : `~/.claude/skills/reel-studio/scripts/reelkit.py`

Prends le premier qui existe. Appelle-le `RK` dans ta tête.

**Interpréteur** — si `.venv-reelkit/` existe à la racine du projet, utilise `.venv-reelkit/bin/python` (Windows : `.venv-reelkit\Scripts\python.exe`), sinon `python3` (Windows : `py` ou `python`).

**Workspace** — `./reels-workspace/` (ou `$REELKIT_WORKSPACE`) :

```
reels-workspace/
  reels/<id>/        source.mp4, meta.json, analysis.json, report.md, frames/, contact_sheet.jpg,
                     audio.wav, transcript.srt|json, decode.json (rempli par Claude)
  styles/<nom>.json  profil de style (+ .md lisible)
  projects/<nom>/    timeline.json, captions.srt/.ass, render.mp4, render.verify.json
  reports/runs.jsonl journal d'exécution de chaque commande
```

**Règles de vérité** — ce que le moteur écrit dans `analysis.json` est mesuré. Ce que tu écris dans `decode.json` doit citer une frame ou un timecode. Invisible / inaudible / incertain = `null`. Ne présente jamais une hypothèse comme un constat.

## Diagnostic

```bash
<python> <RK> doctor
```

Socle requis : Python ≥ 3.9, `ffmpeg`/`ffprobe` avec les filtres subtitles (libass), loudnorm, zoompan, silencedetect, tile. Optionnels : `yt-dlp` (téléchargement d'URL), `faster-whisper` (transcription locale). Si une ligne requise est KO : donne la commande de correction affichée, ne l'exécute pas sans accord si elle demande des droits administrateur.

Auto-test complet (médias synthétiques générés localement, ~30 s) :

```bash
<python> <RK> selftest
```

État du workspace : `<python> <RK> status`

## Enchaînement complet

1. **Analyse** de chaque vidéo de référence → skill `reel-analyze` (`ingest` puis remplissage de `decode.json`).
2. **Profil de style** dès 2 vidéos (idéalement ≥ 3 du même créateur) → skill `reel-style`.
3. **Adaptation** : script + timeline + sous-titres → skill `reel-adapt`.
4. **Rendu et contrôle** → skill `reel-render`.

Évite les opérations redondantes : `grab` réutilise un téléchargement existant, `analyze` réutilise une transcription en cache. Utilise `--force` / `--transcribe on` seulement si l'utilisateur le demande ou si l'entrée a changé.

## Rapport d'exécution

À la fin d'un enchaînement, résume en tableau : étape, statut (réussi / échoué / non exécuté), fichiers produits, actions manuelles restantes (voix off à enregistrer, droits musicaux, relecture). Les détails bruts sont dans `reels-workspace/reports/runs.jsonl`.

## Dépannage rapide

| Symptôme | Cause probable | Action |
|---|---|---|
| `yt-dlp absent` | dépendance optionnelle non installée | `pip install -r requirements.txt` ou fournir un fichier local |
| échec téléchargement + « login/private/rate-limit » | contenu privé, limitation Instagram | réessayer plus tard ; `--cookies-from-browser firefox` (session de l'utilisateur) ; ou fichier local |
| échec téléchargement + « proxy/réseau » | pas d'accès réseau à la plateforme | vérifier la connexion ; ou fichier local |
| `transcription=unavailable` | faster-whisper absent | installer, ou `--srt fichier.srt` |
| `Impossible de charger le modèle Whisper` | pas d'accès à huggingface.co | télécharger le modèle ailleurs, `REELKIT_WHISPER_MODEL=/chemin/modele` |
| trop / pas assez de coupes | seuil inadapté | `analyze --threshold 0.4` (moins) ou `0.2` (plus) |
| police des sous-titres différente | police absente du système | installer la police ou changer `captions.font` dans timeline.json |
| `render` NON CONFORME | voir `render.verify.json` | corriger la ligne KO puis relancer |
