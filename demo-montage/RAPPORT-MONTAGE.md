# Rapport — montages réalisés par le Claude Reels Toolkit

## Ce qu'il faut savoir d'abord

**Aucun montage n'a été fait à partir d'un vrai Reel.** L'environnement de travail n'avait accès ni à Instagram ni à des vidéos réelles. Tous les montages ont été produits à partir de **médias de test générés par FFmpeg** (mires de couleur, fractale, sons purs). Ils servent à prouver que la chaîne de montage fonctionne, pas à produire un contenu publiable.

## Fichiers de ce dossier

| Fichier | Contenu |
|---|---|
| `montage-demo-1080x1920.mp4` | Le montage final de démonstration (9,3 s, format Reel vertical) |
| `planche_montage.jpg` | Une image par seconde du montage, pour le voir d'un coup d'œil |
| `timeline.json` | Le plan de montage : quel média, à quel moment, combien de temps |
| `captions.srt` | Les sous-titres générés |
| `render.verify.json` | Le contrôle automatique du fichier final |

## Comment le montage a été fabriqué

**1. Deux « Reels de référence » analysés.** Deux vidéos verticales de test, avec des coupes placées à des instants connus :

| Vidéo | Coupes placées | Coupes détectées par l'outil |
|---|---|---|
| Référence 1 | 1,2 s · 3,0 s · 5,0 s | 1,2 s · 3,0 s · 5,0 s |
| Référence 2 | 1,0 s · 3,2 s · 4,8 s · 7,2 s | 1,0 s · 3,2 s · 4,8 s · 7,2 s |

Détection exacte, au dixième de seconde près.

**2. Profil de style extrait de ces deux vidéos** : durée médiane d'un plan 1,85 s, première coupe rapide (≈ 1,1 s), plans entre 1,1 s et 2,45 s.

**3. Montage d'une nouvelle vidéo dans ce style**, avec :
- 3 clips **horizontaux** (1280x720), recadrés automatiquement en vertical 9:16 ;
- 1 **image fixe**, animée par un léger zoom avant ;
- une **voix off** et une **musique** (sons de test), la musique baissant automatiquement sous la voix ;
- un **script** transformé en sous-titres incrustés, 3 mots maximum, mot le plus long surligné en jaune.

Résultat : 5 plans (1,1 s · 1,48 s · 2,22 s · 1,67 s · 2,84 s), 5 sous-titres.

**4. Contrôle automatique du fichier final** — tout conforme :

| Contrôle | Attendu | Mesuré |
|---|---|---|
| Résolution | 1080x1920 | 1080x1920 |
| Cadence | 30 i/s | 30 i/s |
| Durée | 9,3 s | 9,3 s |
| Codecs | H.264 / AAC | H.264 / AAC |
| Volume (loudness) | −14 LUFS (standard réseaux sociaux) | −14,0 LUFS |
| Crête audio | ≤ −1 dBTP | −12 dBTP |
| Images noires | aucune longue séquence | 0 s |

## Autres montages testés

- **Aperçu rapide** (540x960, encodage accéléré) : conforme.
- **Montage sans style, sans script, en gardant le son d'origine des clips** (7 s) : conforme.
- **Détection d'un fichier non conforme** (mauvaise résolution) : l'outil le signale bien « NON CONFORME ».

## Ce qui n'a pas été testé

- Un montage à partir de **vrais rushs** et d'une **vraie voix** : à faire sur ta machine.
- Le calage des sous-titres **mot à mot** sur une vraie voix off (nécessite le modèle Whisper, inaccessible ici). Dans la démo, les sous-titres sont répartis selon la longueur des mots, donc approximatifs.
- Transitions autres que la coupe franche, étalonnage, effets : hors du périmètre automatique, à faire dans un logiciel de montage.

## Pour faire un vrai montage

Dans Claude Code, ouvert sur ce dépôt :

```
/reel-adapt Prépare un Reel de 30 s sur [ton sujet] avec les vidéos de [dossier] et la voix off [fichier].
/reel-render Fais un aperçu, montre-moi la planche, puis exporte la version finale.
```

Documentation complète : `claude-reels-toolkit/USAGE.md` (exemples), `claude-reels-toolkit/TESTS.md` (tous les tests).
