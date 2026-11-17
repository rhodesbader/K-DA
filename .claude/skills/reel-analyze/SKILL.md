---
name: reel-analyze
description: Acquire and analyze a short vertical video (Instagram Reel URL, TikTok/Shorts URL with --any-site, or a local video file) - downloads with yt-dlp when allowed, measures cuts, shot lengths, pacing, loudness, silences, extracts keyframes and a contact sheet, transcribes speech locally, then has Claude decode hook, sections, on-screen text, caption style, framing and persuasion mechanics into decode.json with frame evidence. Use whenever the user pastes a reel link or video file and asks to analyze, decode, break down, transcribe or understand why it works, or compare several reels.
---

# Reel Analyze — acquisition + analyse vérifiable

Conventions (chemin du moteur `RK`, interpréteur, workspace) : voir le skill `reel-studio`.

## 1. Acquérir et mesurer

Une ou plusieurs sources (URL ou fichiers) :

```bash
<python> <RK> ingest "<url ou fichier>" ["<url2>" ...] [--lang fr]
```

- URL Instagram (`/reel/`, `/reels/`, `/p/`, `/tv/`) acceptée directement. Autres plateformes : ajouter `--any-site`.
- Fichier local : copié dans le workspace, jamais modifié.
- Contenu privé ou bloqué : **ne contourne pas**. Propose (a) réessayer plus tard, (b) `--cookies-from-browser <navigateur>` avec la propre session de l'utilisateur, s'il a le droit d'accéder au contenu, (c) qu'il fournisse le fichier.
- Rappelle une fois que la réutilisation de contenus tiers est soumise au droit d'auteur : l'analyse sert à comprendre une méthode, pas à republier la vidéo.

Options utiles : `--threshold 0.2–0.5` (sensibilité des coupes), `--max-frames 32` (montages très rapides), `--transcribe off|on`, `--model small|medium|large-v3`, `--srt transcript.srt` (transcription fournie).

Le moteur écrit dans `reels-workspace/reels/<id>/` : `analysis.json` (mesures), `report.md` (lisible), `frames/`, `contact_sheet.jpg`, `transcript.srt` si disponible, et un `decode.json` vierge.

## 2. Regarder (toi, Claude)

1. Lis `report.md`.
2. Lis `contact_sheet.jpg` (vue d'ensemble, tuiles numérotées avec timecode).
3. Lis les frames individuelles :
   - montage coupé ou texte à l'écran → **toutes** les frames (le texte change souvent à chaque plan) ;
   - plan unique sans texte → 2–3 frames suffisent.
4. Texte trop petit : extrais une image pleine résolution :
   `ffmpeg -loglevel error -ss <secondes> -i <reel>/source.mp4 -frames:v 1 <reel>/fullres_<secondes>.png`
5. Aligne transcription et timecodes des frames.

## 3. Décoder dans `decode.json`

Remplis le fichier existant (même schéma, ne supprime aucune clé) puis mets `"filled": true`.

- `hook` : type (ex. cognitive-dissonance, before/after, output-as-proof, question, claim contre-intuitif), visuel, phrase/texte, émotion, preuves.
- `sections` : arc réel de la vidéo (Hook / Problème / Solution / Démo / CTA… selon ce qui est vu), avec start/end, visuel, parole, texte à l'écran, style de sous-titre, mécanique nommée.
- `on_screen_text` : chaque texte lu, avec frame source.
- `captions` : position (`lower-third`, `center`, `top`), casse (`uppercase`/`sentence`), police **estimée** (`font_family_guess`), graisse, couleurs hex, couleur d'accent, mots par sous-titre, animation (`word-by-word`, `pop`, `static`…).
- `framing`, `transitions` (seulement si visibles entre deux frames ; le moteur ne détecte que les coupes franches), `effects`, `color_grade`, `music`, `cta`.
- `why_it_works` : 5–8 mécaniques précises, chacune liée à une preuve.
- `open_questions` : ce que tu n'as pas pu établir.

Valeurs normalisées en minuscules, mêmes mots d'une vidéo à l'autre (sinon le profil de style ne pourra pas les regrouper).

## 4. Restituer

Réponds avec : en-tête (source, durée, plans, coupes/min, mode spoken/text_overlay, statut transcription), storyboard par section (Visuel / Parole ou Texte / Style de sous-titre / Mécanique), « Pourquoi ça marche », limites (ce qui n'est pas mesuré). Sépare **Mesuré** / **Observé sur frames** / **Déduit**.

## Comparer plusieurs vidéos

Après ingestion de toutes les sources, présente un tableau comparatif (durée, plans, médiane des plans, coupes/min, 1re coupe, mots/min, LUFS, type de hook, style de sous-titre) puis propose `reel-style` pour en tirer un profil.
