# Rapport de tests

Environnement : Linux (conteneur cloud), Python 3.13, FFmpeg 6.1.1, Claude Code 2.1.326.
Dépendances optionnelles testées dans un venv : yt-dlp 2026.8.19, faster-whisper 1.2.1.
Les tests ont été exécutés deux fois (octobre puis novembre 2026, après reconstruction dans un nouveau conteneur) avec les mêmes résultats.

## Réussis

| # | Contrôle | Résultat |
|---|---|---|
| 1 | Structure du projet et fichiers requis (`build_zip.py` → liste `REQUIRED`) | OK |
| 2 | Frontmatter YAML des 5 SKILL.md : `install.py --check` + parsing PyYAML strict (`tests/test_skills.py`) | OK |
| 3 | Les skills ne citent que des commandes existantes du moteur ; fichiers référencés présents | OK |
| 4 | Syntaxe : `python -m compileall` sur tout le code | OK |
| 5 | Lint `ruff` (E, F, W, B) | OK (B905 `zip(strict=)` ignoré : indisponible en Python 3.9 ; E501 lignes longues ignoré) |
| 6 | Tests unitaires : SRT aller-retour, comptage de mots, slug, stats, regex URL Instagram (dont domaine sosie, http, page login), découpage des plans (somme = durée, minimum respecté), sous-titres (ponctuation), couleurs ASS, profil récurrent/unique, alerte comptes mélangés | 19/19 OK (`python -m unittest discover -s tests`) |
| 7 | Détection des coupes sur 2 vidéos synthétiques à coupes connues | coupes attendues `[1.2, 3.0, 5.0]` et `[1.0, 3.2, 4.8, 7.2]` → détectées **exactement** |
| 8 | Images clés + planche contact horodatée | OK (vérifiée visuellement) |
| 9 | Loudness / silences mesurés | OK (valeurs cohérentes avec les signaux générés) |
| 10 | Profil de style à partir de 2 analyses | OK (avertissement « < 3 vidéos » émis comme prévu) |
| 11 | Timeline : 3 clips paysage + 1 image + voix off + musique + script | OK : 5 plans, 5 sous-titres |
| 12 | Rendu aperçu (540x960) et **final (1080x1920)** + vérification auto | CONFORME : h264/yuv420p/aac, 30 i/s, durée 9,3 s exacte, −14,0 LUFS, pas de noir |
| 13 | Contrôle visuel du rendu (planche 1 i/s) | recadrage 9:16 OK, zoom sur image OK, sous-titres lisibles avec mot accentué |
| 14 | Variante : sans style, sans script, audio d'origine conservé | CONFORME |
| 15 | `verify` détecte un fichier non conforme (mauvaise résolution) | code 3, « NON CONFORME » |
| 16 | Transcription depuis un SRT fourni (`--srt`) : débit, mode `spoken`, texte du hook 0–3 s | OK |
| 17 | Erreurs propres : téléchargement Instagram impossible (réseau) → message + indice réseau, aucun dossier vide laissé | OK |
| 18 | Erreurs propres : modèle Whisper inaccessible → `auto` continue (statut `failed`), `on` s'arrête avec la marche à suivre | OK |
| 19 | Installeur : refus d'écraser un skill étranger ; installation + venv ; réinstallation idempotente ; `selftest` depuis l'emplacement installé | OK |
| 20 | Désinstalleur : supprime seulement les 5 skills marqués + venv ; skill étranger conservé | OK |
| 21 | **Claude Code reconnaît les skills** : `claude -p` dans le projet liste `reel-adapt, reel-analyze, reel-render, reel-studio, reel-style` | OK |
| 22 | **Invocation réelle** `/reel-analyze` en mode headless sur une vidéo de démo : le moteur tourne, Claude lit les frames, remplit `decode.json` (`filled: true`, inconnues à `null`, preuves citées), sépare Mesuré / Observé / Déduit | OK |
| 23 | ZIP : création, test d'intégrité, présence des fichiers requis, absence de données de travail ; tests rejoués depuis le ZIP décompressé | OK (`build_zip.py`) |

## Échoués

Aucun parmi les tests exécutés.

## Non exécutés (et pourquoi)

| Test | Raison |
|---|---|
| Téléchargement réel d'un Reel Instagram (dont la vidéo de référence) | instagram.com bloqué par le proxy de l'environnement de construction (403). Chemin d'erreur testé ; chemin nominal non testé ici. |
| Transcription réelle avec faster-whisper | huggingface.co bloqué → modèle non téléchargeable. Chargement de la bibliothèque OK, transcription testée via SRT fourni. |
| Analyse d'une vraie vidéo parlée avec sous-titres incrustés | aucune vidéo réelle autorisée disponible dans l'environnement ; tests sur mires synthétiques uniquement. |
| macOS et Windows | seul Linux disponible. Le code n'utilise que `pathlib`/`subprocess` ; le chemin des sous-titres est passé en relatif pour éviter l'échappement `C:` de FFmpeg sous Windows — **non vérifié sur Windows**. |
| Police « Inter » sur la machine cible | présente ici ; ailleurs libass prend une police de repli (documenté). |

## Rejouer les tests

```bash
cd claude-reels-toolkit
python3 install.py --check
python3 -m unittest discover -s tests -v
python3 skills/reel-studio/scripts/reelkit.py selftest --full
python3 build_zip.py
```
