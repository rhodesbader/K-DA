# Licences

## Ce paquet

Code, skills et documentation : **MIT** (voir `LICENSE`). Écrits pour ce toolkit ; aucun fichier de projet tiers n'est inclus.

## Dépendances (non incluses dans le ZIP, installées par l'utilisateur)

| Composant | Licence | Rôle | Remarque |
|---|---|---|---|
| FFmpeg | LGPL 2.1+ (GPL selon les options de compilation, ex. libx264) | analyse et rendu | appelé en ligne de commande, non redistribué |
| yt-dlp | Unlicense | téléchargement (optionnel) | |
| faster-whisper | MIT | transcription (optionnel) | |
| CTranslate2 | MIT | moteur d'inférence de faster-whisper | |
| Modèles Whisper (OpenAI, convertis par Systran) | MIT | poids du modèle | téléchargés depuis Hugging Face au 1er usage |

## Projets ayant inspiré la méthode (aucun code copié)

| Projet | Licence constatée |
|---|---|
| aipauloshimas/reel-engine | « MIT » dans le README, pas de fichier LICENSE au commit 903c44f |
| farzaliyevramil/watch-instagram | MIT |
| joaocalixto/reels-to-md | MIT |
| Jakeschincariol/instagram-agent-skill | MIT |
| Murtadha-Najem/claude-reel | MIT |

## Contenus traités

Les vidéos, musiques et transcriptions que vous analysez ou montez restent soumises aux droits de leurs auteurs et aux conditions des plateformes. Le toolkit n'inclut aucun média tiers ; l'auto-test utilise uniquement des mires générées par FFmpeg.
