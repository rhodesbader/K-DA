# Rapport de fidélité

Recherche menée le 2026-10-13. Ce document sépare ce qui est **confirmé**, ce qui est **déduit** et ce qui a été **ajouté**.

## 1. La vidéo de référence n'a pas pu être examinée

Référence : `https://www.instagram.com/reel/DeYjzhEkpJg/`

| Tentative | Résultat |
|---|---|
| Accès direct (curl, outil de lecture web, yt-dlp) depuis l'environnement de construction | **Échec** : instagram.com bloqué par le proxy réseau de l'environnement (403 / DNS) |
| Recherche web sur l'identifiant `DeYjzhEkpJg` | **Aucun résultat** associant cet identifiant à un auteur, une légende ou un dépôt |
| Copie locale de la vidéo dans le dépôt | **Absente** (seul fichier présent : `KoDA – Amélioration complète.zip`, un handoff de design d'application sans rapport, d'après la liste de ses fichiers) |

**Conséquence : ni l'auteur, ni la légende, ni la transcription, ni les commandes montrées dans la vidéo ne sont connus.** Rien dans ce toolkit ne prétend reproduire *exactement* cette vidéo.

Pour lever ce point : déposez le fichier vidéo (ou une capture de la légende) dans le projet et lancez
`/reel-analyze Analyse [fichier] et liste chaque outil, dépôt et commande visible.` — le toolkit est précisément conçu pour ça.

## 2. Projets examinés (code lu, rien exécuté de tiers)

Clonés depuis GitHub et lus (README, SKILL.md, scripts, dépendances, licences).

| Dépôt | Ce qu'il fait (confirmé par le code) | Licence | Dernier commit lu | Pertinence |
|---|---|---|---|---|
| [aipauloshimas/reel-engine](https://github.com/aipauloshimas/reel-engine) | 7 skills : `reel-grab` (yt-dlp + openai-whisper + frames 1 i/s), `reel-decode` (storyboard + mécaniques de persuasion + 3 questions), `reel-adapt` (script adapté), `reel-scout` (gallery-dl + cookies), `voice-setup`, `reel-doctor`, `reel-start` | « MIT » annoncé dans le README, **aucun fichier LICENSE** | 903c44f (2026-04-27) | **La plus proche** du besoin « analyser un reel → l'adapter ». Ne fait ni profil multi-vidéos, ni montage. |
| [joaocalixto/reels-to-md](https://github.com/joaocalixto/reels-to-md) | Reel → tutoriel Markdown + scripts extraits | MIT | 359a26b (2026-06-11) | Faible (but : documenter un tutoriel, pas monter) |
| [Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) | 13 skills de gestion de compte (hooks notés, légendes, carrousels, humanizer) | MIT | d03c56b (2026-09-13) | Faible (écriture, pas vidéo) |
| [farzaliyevramil/watch-instagram](https://github.com/farzaliyevramil/watch-instagram) (trouvé en recherche) | Frames par plan + planche contact + whisper.cpp | MIT | — | Moyenne (idée de planche contact par plan) |
| [Murtadha-Najem/claude-reel](https://github.com/Murtadha-Najem/claude-reel) (trouvé en recherche) | OCR, classification audio, Shazam, transcription Gemini | MIT | — | Faible (dépend d'une clé Gemini, orienté arabe) |

**Points de vigilance relevés dans reel-engine** (raison de ne pas l'installer tel quel) : son `install.sh` invite à un `curl … | bash`, utilise `sudo apt/dnf/pacman`, ajoute des lignes à `~/.bashrc`/`~/.zshrc`, installe dans `~/.claude/skills` (global) et ses instructions demandent à l'agent d'agir « sans demander la permission entre les étapes ». Rien de malveillant n'a été trouvé, mais c'est contraire à la consigne « installation locale, pas de modification globale sans accord ». Son absence de fichier LICENSE rend aussi la redistribution de son code juridiquement fragile.

**Je ne sais pas** lequel de ces projets (s'il y en a un) est celui de la vidéo.

## 3. Ce qui est repris (méthode, pas code)

Aucun fichier tiers n'est copié dans le paquet. Le code est original. Les idées de méthode reprises, avec leur source :

| Élément | Source | Statut |
|---|---|---|
| Pipeline acquisition → décodage → adaptation | reel-engine (grab/decode/adapt) | repris, restructuré |
| Détection « parlé » vs « texte à l'écran » (< 15 mots transcrits) | reel-engine `transcribe_reel.sh` | repris (seuil identique, configurable) |
| Storyboard par section : Visuel / Parole / Style de sous-titre / Mécanique | reel-engine `reel-decode` | repris dans `decode.json` |
| Hook : conserver la mécanique, changer le contenu | reel-engine `reel-adapt` | repris dans `reel-adapt` |
| Une frame par plan + planche contact horodatée | watch-instagram | repris (implémentation FFmpeg propre) |
| Validation stricte des URL Instagram (anti-sosie de domaine) | reel-engine | repris et testé |

## 4. Ce qui est ajouté / amélioré

| Ajout | Pourquoi |
|---|---|
| Coupes mesurées (score de scène FFmpeg) au lieu de frames à 1 i/s | durée réelle de chaque plan, coupes/min, 1re coupe : le rythme devient un chiffre |
| Loudness EBU R128, silences, débit de parole | mesurables, réutilisables au montage |
| Profil multi-vidéos récurrent / occasionnel / unique + CV | demandé (Skill C) ; absent de tous les projets examinés |
| Timeline JSON éditable + sous-titres ASS stylés | demandé (Skill D) |
| Rendu FFmpeg 9:16 + mix voix/musique avec ducking + −14 LUFS | demandé (Skill E) ; absent de tous les projets examinés |
| Vérification automatique du rendu | « vérifier le résultat final » |
| faster-whisper au lieu d'openai-whisper | même famille de modèles, sans PyTorch (~2 Go économisés) |
| Installation locale au projet, marquée, réversible | consigne explicite |
| Journal d'exécution `runs.jsonl` (cookies masqués) | « rapports d'exécution » |
| Auto-test sur médias synthétiques | vérifiable sans contenu tiers |

## 5. Volontairement non repris

- `reel-scout` (scraping de profils via cookies de navigateur + monkey-patch de gallery-dl) : zone grise vis-à-vis des conditions d'Instagram, fragile, et non nécessaire au workflow.
- `voice-setup` : utile pour le copywriting, hors du périmètre analyse/montage. Le skill `reel-adapt` demande le ton directement.
- Identification musicale (Shazam) et OCR (RapidOCR) : dépendances lourdes ; Claude lit le texte sur les frames.

## 6. Hypothèses

- **H1** (non vérifiée) : la vidéo présente une méthode de type « Claude Code analyse un reel viral et l'adapte » — cohérent avec les dépôts suggérés, mais non confirmé.
- **H2** : le livrable attendu inclut le montage automatisé (déduit de la demande, pas de la vidéo).
