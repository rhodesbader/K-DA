---
name: reel-adapt
description: Prepare a new Reel from a style profile - writes the adapted script (hook structure, sections, CTA) for the user's own topic or product, then generates an editable timeline.json (shot order, in-points, durations matched to the creator's pacing), SRT and styled ASS captions for a 1080x1920 export. Use when the user wants to adapt a decoded reel or a creator style to their own content, write a reel script, or prepare an edit from their own clips, images, voice-over and music.
---

# Reel Adapt — script + timeline

Conventions (moteur `RK`, interpréteur, workspace) : voir `reel-studio`.

## Entrées à réunir

1. **Profil de style** `reels-workspace/styles/<nom>.json` (sinon : défauts, à signaler) et/ou le `decode.json` d'une vidéo de référence.
2. **Sujet** : produit/thème, public visé, émotion recherchée, CTA. Demande uniquement ce qui manque, une question à la fois.
3. **Médias de l'utilisateur** : vidéos et images (fichiers ou dossier), dans l'ordre voulu. Uniquement des médias qu'il a le droit d'utiliser.
4. **Voix off** (optionnelle) : fichier audio. **Musique** (optionnelle) : fichier dont il détient les droits.

## 1. Écrire le script (toi, Claude)

À partir du `hook` et des `sections` décodés :

- conserve la **mécanique** du hook (structure de phrase, dispositif visuel, émotion), change le contenu ;
- respecte la durée cible (`editing_rules.target_duration_s`) et le débit (`words_per_minute`) : nb de mots ≈ durée × débit / 60 ;
- respecte le vocabulaire exact du domaine de l'utilisateur ;
- n'invente ni chiffres, ni témoignages, ni promesses invérifiables.

Livre : script parlé, puis un tableau plan par plan (temps, visuel conseillé, texte à l'écran, mécanique). Enregistre le script dans `reels-workspace/projects/<projet>/script.txt`.

## 2. Générer la timeline

```bash
<python> <RK> plan --project <projet> --style reels-workspace/styles/<nom>.json \
  --media <dossier_ou_fichiers...> --script reels-workspace/projects/<projet>/script.txt \
  [--voiceover voix.wav --transcribe-voiceover] [--music musique.mp3] [--duration 28] [--keep-original-audio]
```

- Sans voix off : durée déduite du script et du débit ; sous-titres répartis proportionnellement (approximatifs).
- Avec voix off + `--transcribe-voiceover` (faster-whisper) : sous-titres calés mot à mot.
- Plans : 1er plan court (≤ 1re coupe médiane du créateur), puis variation déterministe autour de la médiane, bornée par min/max mesurés. Images : léger zoom avant.

Sorties : `timeline.json`, `captions.srt`, `captions.ass`.

## 3. Relire avec l'utilisateur

Résume la timeline (plans, durées, médias, nombre de sous-titres) et les `manual_steps`. `timeline.json` se modifie à la main : `media`, `in` (point d'entrée), `duration`, `fit` (`cover` recadre en 9:16, `contain` ajoute des bandes), `motion` (`zoom_in` ou `null`), `keep_audio`. Le style des sous-titres est dans `captions.style` (régénéré à chaque `plan`).

Quand c'est validé → skill `reel-render`.
