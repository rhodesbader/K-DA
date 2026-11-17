"""reelkit command line. Every command appends a line to <workspace>/reports/runs.jsonl."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from . import analyze as an
from . import demo, doctor, grab, plan, render, style, verify
from .util import VERSION, ReelkitError, log, now_iso, read_json, workspace_root, write_json


def _ws(args) -> Path:
    return Path(args.workspace).expanduser().resolve() if args.workspace else workspace_root()


def _reel_dir(ws: Path, ref: str) -> Path:
    p = Path(ref).expanduser()
    if p.is_dir():
        return p.resolve()
    q = ws / "reels" / ref
    if q.is_dir():
        return q
    raise ReelkitError(f"Dossier de reel introuvable: {ref} (cherché aussi dans {ws / 'reels'})")


def cmd_doctor(args):
    res = doctor.check()
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else doctor.render(res))
    return {"core_ok": res["core_ok"]}, (0 if res["core_ok"] else 1)


def cmd_grab(args):
    d = grab.grab(args.source, _ws(args), args.any_site, args.cookies_from_browser, args.cookies, args.force)
    print(d)
    return {"reel_dir": str(d)}, 0


def _analyze(args, d: Path):
    a = an.analyze(d, args.threshold, args.max_frames, args.transcribe, args.model, args.lang, args.srt)
    print(f"{d}\n  plans={a['pacing']['shots']} coupes/min={a['pacing']['cuts_per_minute']} "
          f"transcription={a['transcript']['status']} mode={a['content_mode']}\n  -> {d / 'report.md'}")
    return a


def cmd_analyze(args):
    d = _reel_dir(_ws(args), args.reel)
    _analyze(args, d)
    return {"reel_dir": str(d)}, 0


def cmd_ingest(args):
    ws = _ws(args)
    done, failed = [], []
    for src in args.sources:
        try:
            d = grab.grab(src, ws, args.any_site, args.cookies_from_browser, args.cookies, args.force)
            _analyze(args, d)
            done.append(str(d))
        except ReelkitError as exc:
            log(f"ÉCHEC {src}: {exc}")
            failed.append({"source": src, "error": str(exc).splitlines()[0]})
    print(json.dumps({"ok": done, "failed": failed}, ensure_ascii=False, indent=2))
    return {"ok": done, "failed": failed}, (0 if not failed else 2)


def cmd_style(args):
    ws = _ws(args)
    dirs = [_reel_dir(ws, r) for r in args.reels]
    s = style.build_style(dirs, args.name, args.threshold)
    out = Path(args.out) if args.out else ws / "styles" / f"{args.name}.json"
    style.save(s, out)
    for w in s["warnings"]:
        print("AVERTISSEMENT:", w)
    print(out)
    return {"style": str(out), "warnings": s["warnings"]}, 0


def cmd_plan(args):
    out = Path(args.out) if args.out else _ws(args) / "projects" / args.project
    p = plan.plan(out, args.media, args.style, args.script, args.voiceover, args.music, args.duration,
                  args.keep_original_audio, args.transcribe_voiceover, args.lang)
    print(p)
    return {"timeline": str(p)}, 0


def cmd_render(args):
    rep = render.render(args.timeline, args.out, args.keep_temp, args.draft)
    print(verify.render_text(rep))
    return {"file": rep["file"], "ok": rep["ok"]}, (0 if rep["ok"] else 3)


def cmd_verify(args):
    exp = {k: v for k, v in {"width": args.width, "height": args.height, "fps": args.fps,
                              "duration_s": args.duration, "loudness_target_lufs": args.lufs}.items() if v is not None}
    rep = verify.verify(args.video, exp)
    print(verify.render_text(rep))
    return {"ok": rep["ok"]}, (0 if rep["ok"] else 3)


def cmd_status(args):
    ws = _ws(args)
    rows = []
    for d in sorted((ws / "reels").glob("*")) if (ws / "reels").exists() else []:
        dec = d / "decode.json"
        rows.append({"reel": d.name, "analysed": (d / "analysis.json").exists(),
                     "decoded": dec.exists() and bool(read_json(dec).get("filled"))})
    styles = [p.name for p in (ws / "styles").glob("*.json")] if (ws / "styles").exists() else []
    projects = [p.parent.name for p in (ws / "projects").glob("*/timeline.json")] if (ws / "projects").exists() else []
    res = {"workspace": str(ws), "reels": rows, "styles": styles, "projects": projects}
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return {"reels": len(rows)}, 0


def cmd_selftest(args):
    """End-to-end run on synthetic media: grab(local) -> analyze -> style -> plan -> render -> verify."""
    base = Path(args.dir).resolve() if args.dir else Path(tempfile.mkdtemp(prefix="reelkit-selftest-"))
    base.mkdir(parents=True, exist_ok=True)
    ws = base / "workspace"
    results = []

    def step(name, ok, detail=""):
        results.append({"step": name, "ok": bool(ok), "detail": detail})
        print(f"[{'OK' if ok else 'KO'}] {name} {detail}")

    expected_cuts = [[1.2, 1.8, 2.0, 2.5], [1.0, 2.2, 1.6, 2.4, 1.8]]
    dirs = []
    for i, lengths in enumerate(expected_cuts):
        src = demo.make_reel(base / f"demo_reel_{i + 1}.mp4", lengths, tone=330 + 110 * i)
        d = grab.grab(str(src), ws)
        a = an.analyze(d, transcribe="off")
        got = [c["time"] for c in a["cuts"]]
        want, t = [], 0.0
        for x in lengths[:-1]:
            t += x
            want.append(round(t, 2))
        ok = len(got) == len(want) and all(abs(g - w) < 0.1 for g, w in zip(got, want))
        step(f"détection des coupes reel {i + 1}", ok, f"attendu {want} / détecté {got}")
        step(f"planche contact reel {i + 1}", (d / "contact_sheet.jpg").exists())
        dirs.append(d)
    s = style.build_style(dirs, "selftest")
    style.save(s, ws / "styles" / "selftest.json")
    step("profil de style", s["metrics"].get("shot_median_s") is not None,
         f"plan médian={s['metrics']['shot_median_s']['median']}s")
    m = demo.make_media(base / "media")
    script = "Voici un test complet du pipeline. Trois plans, une image fixe, et des sous-titres incrustés!"
    tl = plan.plan(ws / "projects" / "selftest", [*m["clips"], m["image"]], ws / "styles" / "selftest.json",
                   script, m["voiceover"], m["music"])
    t = read_json(tl)
    step("timeline", len(t["segments"]) >= 3 and t["captions"]["count"] > 0,
         f"{len(t['segments'])} plans, {t['captions']['count']} sous-titres")
    rep = render.render(tl, draft=not args.full)
    step("rendu + vérification", rep["ok"], "; ".join(f"{c['name']}={c['actual']}" for c in rep["checks"]))
    ok = all(r["ok"] for r in results)
    write_json(base / "selftest_report.json", {"ok": ok, "results": results, "at": now_iso(), "dir": str(base)})
    print(f"\nAUTO-TEST: {'RÉUSSI' if ok else 'ÉCHEC'} — fichiers dans {base}")
    return {"ok": ok, "dir": str(base)}, (0 if ok else 4)


def build_parser():
    p = argparse.ArgumentParser(prog="reelkit", description="Analyse, profil de style et montage de Reels (FFmpeg).")
    p.add_argument("--version", action="version", version=f"reelkit {VERSION}")
    p.add_argument("--workspace", help="dossier de travail (défaut: $REELKIT_WORKSPACE ou ./reels-workspace)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor", help="vérifier les prérequis")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_doctor)

    def acq(s):
        s.add_argument("--any-site", action="store_true", help="autoriser d'autres sites pris en charge par yt-dlp")
        s.add_argument("--cookies-from-browser", help="ex: firefox, chrome (votre propre session)")
        s.add_argument("--cookies", help="fichier cookies.txt (format Netscape)")
        s.add_argument("--force", action="store_true", help="retélécharger / réimporter")

    def ana(s):
        s.add_argument("--threshold", type=float, help="seuil de détection de coupe (0.1–0.6, défaut 0.3)")
        s.add_argument("--max-frames", type=int)
        s.add_argument("--transcribe", choices=["auto", "on", "off"], default="auto")
        s.add_argument("--model", help="modèle faster-whisper (tiny, base, small, medium, large-v3)")
        s.add_argument("--lang", help="langue forcée (fr, en, …)")
        s.add_argument("--srt", help="transcription SRT existante à utiliser")

    s = sub.add_parser("grab", help="télécharger une URL ou importer un fichier local")
    s.add_argument("source")
    acq(s)
    s.set_defaults(fn=cmd_grab)

    s = sub.add_parser("analyze", help="analyser un reel déjà acquis")
    s.add_argument("reel", help="id du reel ou chemin du dossier")
    ana(s)
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("ingest", help="grab + analyze pour une ou plusieurs sources")
    s.add_argument("sources", nargs="+")
    acq(s)
    ana(s)
    s.set_defaults(fn=cmd_ingest)

    s = sub.add_parser("style", help="construire un profil de style depuis plusieurs reels")
    s.add_argument("reels", nargs="+")
    s.add_argument("--name", required=True)
    s.add_argument("--threshold", type=float, default=0.6, help="part minimale pour qu'un trait soit 'récurrent'")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_style)

    s = sub.add_parser("plan", help="générer timeline.json + sous-titres")
    s.add_argument("--project", default="nouveau-reel")
    s.add_argument("--media", nargs="+", required=True, help="fichiers ou dossiers (vidéos/images), dans l'ordre")
    s.add_argument("--style", help="profil style.json (sinon valeurs par défaut)")
    s.add_argument("--script", help="texte ou fichier .txt du script")
    s.add_argument("--voiceover", help="fichier audio de voix off")
    s.add_argument("--music", help="fichier musique (droits à votre charge)")
    s.add_argument("--duration", type=float)
    s.add_argument("--keep-original-audio", action="store_true")
    s.add_argument("--transcribe-voiceover", action="store_true", help="caler les sous-titres mot à mot (faster-whisper)")
    s.add_argument("--lang")
    s.add_argument("--out", help="dossier projet (défaut: workspace/projects/<project>)")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("render", help="rendre une timeline en MP4 puis vérifier")
    s.add_argument("timeline")
    s.add_argument("--out")
    s.add_argument("--draft", action="store_true", help="aperçu rapide demi-résolution")
    s.add_argument("--keep-temp", action="store_true")
    s.set_defaults(fn=cmd_render)

    s = sub.add_parser("verify", help="contrôler un MP4")
    s.add_argument("video")
    s.add_argument("--width", type=int)
    s.add_argument("--height", type=int)
    s.add_argument("--fps", type=float)
    s.add_argument("--duration", type=float)
    s.add_argument("--lufs", type=float)
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("status", help="état du workspace")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("selftest", help="test de bout en bout sur médias synthétiques")
    s.add_argument("--dir")
    s.add_argument("--full", action="store_true", help="rendu pleine résolution")
    s.set_defaults(fn=cmd_selftest)
    return p


def _safe_args(args) -> dict:
    hidden = {"fn", "cookies", "cookies_from_browser"}
    return {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k not in hidden}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    t0 = time.time()
    status, outputs, code = "ok", {}, 0
    try:
        outputs, code = args.fn(args)
        if code:
            status = "failed"
    except ReelkitError as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        status, outputs, code = "error", {"error": str(exc).splitlines()[0]}, 1
    except KeyboardInterrupt:
        status, code = "interrupted", 130
    if args.cmd not in ("doctor", "status", "selftest"):
        try:
            rep = _ws(args) / "reports" / "runs.jsonl"
            rep.parent.mkdir(parents=True, exist_ok=True)
            with open(rep, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": now_iso(), "cmd": args.cmd, "args": _safe_args(args), "status": status,
                                     "seconds": round(time.time() - t0, 1), "outputs": outputs},
                                    ensure_ascii=False) + "\n")
        except OSError:
            pass
    return code
