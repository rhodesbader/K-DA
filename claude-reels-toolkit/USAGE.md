# Guide d'utilisation

Prompts à copier dans Claude Code (session ouverte à la racine du projet où les skills sont installés). Entre crochets : à remplacer.

## Analyser un Reel

```
/reel-analyze Analyse ce Reel et explique pourquoi il fonctionne : [https://www.instagram.com/reel/XXXX/]
```

Fichier local (vidéo téléchargée par vous, enregistrement d'écran…) :

```
/reel-analyze Analyse la vidéo [~/Downloads/reference.mp4]. Langue : français.
```

Contenu inaccessible anonymement et que vous avez le droit de voir :

```
/reel-analyze Analyse [URL] en utilisant les cookies de mon navigateur firefox.
```

Résultat : `reels-workspace/reels/<id>/report.md` (mesures), `decode.json` (décodage Claude avec preuves), storyboard dans la réponse.

## Comparer plusieurs vidéos

```
/reel-analyze Analyse ces 4 Reels puis fais un tableau comparatif (rythme, hook, sous-titres, CTA) :
[URL1] [URL2] [fichier3.mp4] [fichier4.mp4]
```

## Créer un profil de style

```
/reel-style Construis le profil de style de [@createur] à partir de toutes les vidéos analysées de ce compte. Sépare sa signature de ce qui est propre à une seule vidéo.
```

Ligne de commande équivalente :

```bash
python .claude/skills/reel-studio/scripts/reelkit.py style [id1] [id2] [id3] --name [createur]
```

## Préparer un nouveau montage

```
/reel-adapt Avec le style [createur], prépare un Reel de ~30 s sur [mon produit / mon sujet] pour [public].
Émotion visée : [soulagement / curiosité / FOMO]. CTA : [enregistrer / commenter "GUIDE"].
Mes médias sont dans [~/Videos/rush-produit/], ma voix off est [~/Audio/vo.wav].
```

Claude écrit le script, puis génère `reels-workspace/projects/<projet>/timeline.json`, `captions.srt`, `captions.ass`. Sans voix off, la durée et les sous-titres sont estimés à partir du script et du débit du créateur.

## Générer et exporter la vidéo

```
/reel-render Fais d'abord un aperçu rapide du projet [nom], montre-moi une planche des images, puis exporte en version finale.
```

```bash
python .claude/skills/reel-studio/scripts/reelkit.py render reels-workspace/projects/[nom]/timeline.json --draft
python .claude/skills/reel-studio/scripts/reelkit.py render reels-workspace/projects/[nom]/timeline.json
```

Le fichier final est contrôlé automatiquement (1080x1920, 30 i/s, H.264/AAC, durée, −14 LUFS, true peak, séquences noires) → `render.verify.json`.

## Tout le pipeline en une demande

```
/reel-studio Voici 3 Reels de [@createur] : [URL1] [URL2] [URL3]. Analyse-les, construis son profil de style,
puis prépare et exporte un Reel dans ce style sur [sujet] avec les médias de [dossier] et la voix off [fichier].
Donne-moi un rapport d'exécution à la fin.
```

## Diagnostiquer un problème

```
/reel-studio Lance le diagnostic et l'auto-test, puis explique-moi ce qui bloque.
```

```bash
python .claude/skills/reel-studio/scripts/reelkit.py doctor
python .claude/skills/reel-studio/scripts/reelkit.py selftest
python .claude/skills/reel-studio/scripts/reelkit.py status
tail -n 5 reels-workspace/reports/runs.jsonl
```

## Retouches manuelles fréquentes

| Besoin | Où |
|---|---|
| Changer un plan, son point d'entrée, sa durée | `timeline.json` → `segments[]` (`media`, `in`, `duration`) |
| Bandes noires au lieu de recadrer | `segments[].fit = "contain"` |
| Supprimer le zoom sur une image | `segments[].motion = null` |
| Police / taille / couleur / position des sous-titres | `editing_rules.captions` du `style.json`, puis relancer `plan` |
| Volume musique | `timeline.json` → `audio.music_gain_db` (ex. −20) |
| Désactiver le ducking | `audio.duck_music_under_voice = false` |
| Sensibilité de détection des coupes | `analyze --threshold 0.2` (plus de coupes) / `0.45` (moins) |
