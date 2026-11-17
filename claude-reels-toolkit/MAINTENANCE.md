# Maintenance

## Mettre à jour les skills dans un projet

```bash
cd claude-reels-toolkit            # nouvelle version décompressée
python3 install.py --project /chemin/projet          # remplace uniquement les dossiers marqués .reelkit-installed
python3 -m unittest discover -s tests                # facultatif : tests du paquet
```

Relancez la session Claude Code pour recharger les skills. Le workspace (`reels-workspace/`) n'est jamais touché.

Personnalisations : ne modifiez pas les fichiers installés (ils seraient écrasés). Changez plutôt `editing_rules` dans vos `style.json`, ou `timeline.json` par projet. Pour changer les défauts globaux, modifiez `skills/reel-studio/config/defaults.json` dans **votre copie source** du toolkit puis réinstallez.

## Mettre à jour les dépendances

| Dépendance | Fréquence conseillée | Commande |
|---|---|---|
| yt-dlp | dès qu'un téléchargement Instagram échoue (les plateformes changent souvent) | `.venv-reelkit/bin/pip install -U yt-dlp` |
| faster-whisper | trimestrielle | `.venv-reelkit/bin/pip install -U faster-whisper` |
| FFmpeg | annuelle | gestionnaire de paquets du système |

Après une mise à jour : `reelkit.py doctor` puis `reelkit.py selftest`. Si tout passe, reportez les versions dans `requirements.txt` (épinglage `==`).

## Surveiller les dépôts sources d'inspiration

Aucun code tiers n'est embarqué, il n'y a donc rien à fusionner. Pour suivre les évolutions de méthode :

```bash
git clone --depth 20 https://github.com/aipauloshimas/reel-engine.git /tmp/reel-engine
git -C /tmp/reel-engine log --oneline --since="3 months ago"
```

Points à regarder : nouvelles sections de `reel-decode/SKILL.md` (champs de storyboard), changements de seuils dans `scripts/transcribe_reel.sh`, ajout d'un fichier LICENSE.

## Évolution du format

- `analysis.json` (`reelkit.analysis/1`), `decode.json` (`reelkit.decode/1`), `style.json` (`reelkit.style/1`), `timeline.json` (`reelkit.timeline/1`) portent un champ `schema`. Toute modification incompatible incrémente le numéro.
- Ajouter un trait qualitatif au profil : l'ajouter dans `templates/decode.template.json`, dans `DECODE_SCALARS` ou `DECODE_LISTS` de `reelkit/style.py`, documenter dans `reel-analyze/SKILL.md`, ajouter un test dans `tests/test_units.py`.

## Construire le ZIP

```bash
python3 build_zip.py        # -> dist/claude-reels-toolkit-<version>.zip, vérifié (ouverture + contenu)
```

## Conventions Claude Code à revérifier lors des mises à jour de Claude Code

- Emplacement des skills projet : `.claude/skills/<nom>/SKILL.md` ; utilisateur : `~/.claude/skills/<nom>/SKILL.md`.
- Frontmatter : `name` (minuscules, chiffres, tirets, ≤ 64 car., identique au dossier) et `description` (≤ 1024 car.). `python3 install.py --check` le contrôle.
