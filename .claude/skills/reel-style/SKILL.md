---
name: reel-style
description: Build a reusable editing style profile (style.json + style.md) from several analyzed reels of the same creator - measured pacing, shot lengths, speech rate, loudness, plus caption, hook, framing and transition traits classified as recurring, occasional or one-off. Use when the user wants to extract, clone, compare or document a creator's editing style, or wants a style to apply to a new video.
---

# Reel Style — profil de style réutilisable

Conventions (moteur `RK`, interpréteur, workspace) : voir `reel-studio`.

## Prérequis

- Chaque vidéo a été passée par `reel-analyze` (présence de `analysis.json`).
- Pour les traits qualitatifs, chaque `decode.json` doit être rempli (`"filled": true`) avec un vocabulaire homogène. Si ce n'est pas le cas, termine d'abord les décodages.
- Minimum technique : 2 vidéos. Recommandé : 3 à 10 vidéos **du même créateur**, de formats comparables.

## Construire

```bash
<python> <RK> style <id_ou_dossier_1> <id_2> <id_3> --name <createur> [--threshold 0.6]
```

Sorties : `reels-workspace/styles/<createur>.json` et `.md`.

- `metrics` : statistiques mesurées (médiane, min, max, coefficient de variation). `consistency: constant` si CV < 0,25.
- `traits` : chaque valeur avec son nombre d'occurrences et sa classe — `recurring` (≥ seuil des vidéos décodées), `occasional` (≥ 2 vidéos), `one-off` (1 seule vidéo).
- `editing_rules` : paramètres concrets pour `plan`, chacun avec son origine (`origin`) : mesure ou défaut.
- `warnings` : peu de vidéos, décodages manquants, comptes mélangés.

## Restituer

1. Présente d'abord les avertissements.
2. « Signature du créateur » : uniquement les traits `recurring` et les métriques `constant`.
3. « Variations » : traits `occasional`, métriques `variable`.
4. « Propre à une seule vidéo » : `one-off` — à ne pas reproduire par défaut.
5. Ce que le profil **ne dit pas** (police exacte, effets non visibles, musique non identifiée).

Ne décris jamais une caractéristique absente des données. Une police est une estimation visuelle, pas une identification.

## Ajuster

Les règles sont modifiables à la main dans `editing_rules` (ex. `captions.font`, `captions.size`, `shot_median_s`) : `plan` les lit telles quelles. Documente toute modification manuelle dans la réponse.
