# Claude Reels Toolkit

Cinq skills Claude Code + un moteur local (Python + FFmpeg) pour **décoder des Reels qui marchent, en extraire un style de montage mesuré, et produire une nouvelle vidéo 9:16 dans ce style**.

```
URL / fichier ──► reel-analyze ──► reel-style ──► reel-adapt ──► reel-render ──► render.mp4 (vérifié)
                  mesures + frames   profil         script +        FFmpeg : coupes, 9:16,
                  + décodage Claude  récurrent vs   timeline +      sous-titres, mix, −14 LUFS
                                     ponctuel       sous-titres
                         ▲───────────── reel-studio : orchestration, diagnostic, auto-test ─────────────▲
```

## Ce qui le distingue

| | Méthode « reel → storyboard → script » (reel-engine & co.) | Ce toolkit |
|---|---|---|
| Analyse | lecture des frames à 1 i/s | **coupes mesurées** (ffmpeg scene score), durée de chaque plan, coupes/min, 1re coupe, loudness, silences, débit de parole |
| Style | une vidéo à la fois | **profil multi-vidéos** : traits récurrents / occasionnels / uniques, coefficient de variation |
| Production | script + storyboard à tourner | **timeline éditable + rendu FFmpeg** 1080x1920 + **contrôle automatique** du fichier final |
| Transcription | openai-whisper (~2 Go PyTorch) | faster-whisper (CPU, sans PyTorch) — ou SRT fourni |
| Installation | copie dans `~/.claude/skills` + modification de `~/.bashrc` | **locale au projet** par défaut, aucun fichier global touché |
| Clés API | aucune | aucune |

## Skills

| Skill | Rôle |
|---|---|
| `reel-studio` | Conventions, orchestration, `doctor`, `selftest`, `status`, dépannage |
| `reel-analyze` | Acquisition (yt-dlp ou fichier local) + mesures + décodage visuel par Claude (`decode.json`) |
| `reel-style` | Profil de style multi-vidéos (`style.json` / `style.md`) |
| `reel-adapt` | Script adapté + `timeline.json` + sous-titres SRT/ASS |
| `reel-render` | Rendu FFmpeg + vérification objective |

## Prérequis

- **Requis** : Python ≥ 3.9, FFmpeg complet (libass, loudnorm, zoompan). Rien d'autre pour analyser des fichiers locaux et monter.
- **Optionnel** : `yt-dlp` (télécharger depuis une URL), `faster-whisper` (transcrire localement). `pip install -r requirements.txt`.
- **Aucune clé API, aucun service payant.** Les frames et transcriptions lues par Claude passent par votre session Claude Code habituelle (Anthropic), comme tout fichier que Claude lit.

## Démarrage en 3 commandes

```bash
python install.py --project /chemin/de/votre/projet --venv     # skills + dépendances optionnelles
cd /chemin/de/votre/projet && .venv-reelkit/bin/python .claude/skills/reel-studio/scripts/reelkit.py selftest
claude    # puis : /reel-studio
```

Détails : [INSTALL.md](INSTALL.md) · Utilisation : [USAGE.md](USAGE.md) · Fidélité à la méthode d'origine : [FIDELITY.md](FIDELITY.md) · Tests : [TESTS.md](TESTS.md) · Maintenance : [MAINTENANCE.md](MAINTENANCE.md) · Licences : [LICENSES.md](LICENSES.md)

## Commandes du moteur

```
reelkit.py doctor                         prérequis
reelkit.py ingest <url|fichier>...        grab + analyze
reelkit.py grab <url|fichier>             acquisition seule
reelkit.py analyze <id|dossier>           mesures, frames, planche contact, transcription
reelkit.py style <id>... --name X         profil de style
reelkit.py plan --media ... [--style --script --voiceover --music]
reelkit.py render timeline.json [--draft] rendu + vérification
reelkit.py verify fichier.mp4 [...]       contrôle d'un MP4
reelkit.py status                         état du workspace
reelkit.py selftest [--full]              test de bout en bout sur médias synthétiques
```

## Limites connues

- Pas d'OCR : le texte à l'écran est lu visuellement par Claude sur les frames (fiable sur texte lisible, pas exhaustif).
- Seules les **coupes franches** sont détectées ; fondus/transitions sont à décrire par Claude s'ils sont visibles.
- La police des sous-titres d'un créateur est **estimée**, jamais identifiée avec certitude.
- Pas d'identification de musique, pas de génération de voix, pas de publication.
- Instagram limite l'accès anonyme : contenus privés ou limitation de débit → fichier local ou vos propres cookies.
- Transitions avancées, étalonnage, animations mot à mot type « karaoké » : à finir dans un logiciel de montage.
