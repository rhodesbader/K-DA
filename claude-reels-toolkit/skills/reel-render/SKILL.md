---
name: reel-render
description: Render a reelkit timeline.json into a vertical 1080x1920 H.264/AAC MP4 with FFmpeg - cuts, 9:16 crop, image zoom, burned-in styled captions, voice-over, music with ducking, -14 LUFS loudness normalization - then verify resolution, fps, duration, codecs, loudness and black frames. Use when the user wants to export, render, preview or check a Reel video file.
---

# Reel Render — montage FFmpeg + contrôle

Conventions (moteur `RK`, interpréteur, workspace) : voir `reel-studio`.

## Aperçu rapide (recommandé d'abord)

```bash
<python> <RK> render reels-workspace/projects/<projet>/timeline.json --draft
```

Demi-résolution, encodage rapide. Extrais une planche pour vérifier visuellement :

```bash
ffmpeg -loglevel error -y -i reels-workspace/projects/<projet>/render.mp4 -vf "fps=1,scale=180:-2,tile=6x5" -frames:v 1 reels-workspace/projects/<projet>/render_sheet.jpg
```

Lis `render_sheet.jpg` : recadrage, lisibilité et position des sous-titres (hors zone d'interface Instagram en bas), enchaînement des plans.

## Export final

```bash
<python> <RK> render reels-workspace/projects/<projet>/timeline.json [--out final.mp4]
```

Paramètres (dans `timeline.json` → `output`) : 1080x1920, 30 i/s, libx264 CRF 18 preset medium, yuv420p, AAC 192 kb/s 48 kHz, `+faststart`, loudness −14 LUFS / true peak −1,5 dBTP.

Le rendu est **automatiquement vérifié** ; le rapport est écrit à côté (`*.verify.json`). Code de sortie 3 = non conforme : lis la ligne KO, corrige, relance.

Contrôle d'un fichier quelconque :

```bash
<python> <RK> verify fichier.mp4 --width 1080 --height 1920 --fps 30 --duration 28 --lufs -14
```

## Ce qui reste manuel (à signaler)

- Enregistrement de la voix off (ou TTS au choix de l'utilisateur).
- Transitions autres que la coupe franche, effets, étalonnage, animations de sous-titres mot à mot avancées : à faire dans un logiciel de montage (CapCut, Premiere, DaVinci Resolve) à partir du `render.mp4`, des `captions.srt` ou de la timeline.
- Droits sur la musique et les médias tiers.
- Publication : le toolkit ne publie rien.
