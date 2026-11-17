"""Aggregate several analysed reels into a reusable style profile.

Separates what is recurring (present in >= threshold of reels) from one-offs.
Numeric metrics come from analysis.json (measured); qualitative traits come
from decode.json files that Claude filled (only those with "filled": true).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .util import VERSION, ReelkitError, describe, load_defaults, log, now_iso, read_json, write_json

NUMERIC = {
    "duration_s": lambda a: a["technical"]["duration_s"],
    "shots": lambda a: a["pacing"]["shots"],
    "shot_median_s": lambda a: (a["pacing"].get("shot_length_s") or {}).get("median"),
    "shot_mean_s": lambda a: (a["pacing"].get("shot_length_s") or {}).get("mean"),
    "shot_min_s": lambda a: (a["pacing"].get("shot_length_s") or {}).get("min"),
    "shot_max_s": lambda a: (a["pacing"].get("shot_length_s") or {}).get("max"),
    "cuts_per_minute": lambda a: a["pacing"].get("cuts_per_minute"),
    "first_cut_at_s": lambda a: a["pacing"].get("first_cut_at_s"),
    "shots_in_first_3s": lambda a: a["pacing"].get("shots_in_first_3s"),
    "words_per_minute": lambda a: a["transcript"].get("words_per_minute_speech"),
    "integrated_lufs": lambda a: a["audio"].get("integrated_lufs"),
    "silence_ratio": lambda a: a["audio"].get("silence_ratio"),
    "fps": lambda a: a["technical"]["fps"],
}
CATEGORICAL_ANALYSIS = {
    "orientation": lambda a: a["technical"]["orientation"],
    "aspect_ratio": lambda a: a["technical"]["aspect_ratio"],
    "content_mode": lambda a: a["content_mode"],
}
DECODE_SCALARS = ["hook.type", "hook.emotion", "captions.present", "captions.position", "captions.case",
                  "captions.font_family_guess", "captions.weight", "captions.highlight_color",
                  "captions.words_per_caption", "captions.animation", "framing.dominant_shot",
                  "framing.subject_position", "framing.camera_motion", "color_grade", "music.present",
                  "music.style", "cta.present", "cta.type"]
DECODE_LISTS = ["transitions", "effects", "captions.colors"]


def _get(d: dict, dotted: str):
    for part in dotted.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(part)
    return d


def _norm(v):
    if isinstance(v, str):
        v = v.strip().lower()
        return v or None
    return v


def _classify(count: int, n: int, threshold: float) -> str:
    if n >= 2 and count / n >= threshold:
        return "recurring"
    return "occasional" if count >= 2 else "one-off"


def _traits(values_per_reel: list, n: int, threshold: float) -> list:
    counter = Counter()
    for vals in values_per_reel:
        for v in set(vals):
            counter[v] += 1
    return [{"value": v, "count": c, "share": round(c / n, 2), "class": _classify(c, n, threshold)}
            for v, c in counter.most_common()]


def build_style(reel_dirs, name: str, threshold: float = 0.6) -> dict:
    analyses, decodes = [], []
    for d in reel_dirs:
        d = Path(d)
        if not (d / "analysis.json").exists():
            raise ReelkitError(f"{d} n'a pas d'analysis.json. Lancez `analyze` d'abord.")
        analyses.append(read_json(d / "analysis.json"))
        dec = d / "decode.json"
        if dec.exists():
            data = read_json(dec)
            if data.get("filled"):
                decodes.append(data)
    n = len(analyses)
    warnings = []
    if n < 3:
        warnings.append(f"Seulement {n} vidéo(s) : distinguer constantes et exceptions exige idéalement ≥ 3 vidéos du même créateur.")
    if len(decodes) < n:
        warnings.append(f"{n - len(decodes)} vidéo(s) sans decode.json rempli : traits qualitatifs calculés sur {len(decodes)} vidéo(s).")
    uploaders = {a["source"].get("uploader") for a in analyses if a["source"].get("uploader")}
    if len(uploaders) > 1:
        warnings.append(f"Plusieurs comptes mélangés ({', '.join(sorted(uploaders))}) : le profil n'est pas celui d'un seul créateur.")

    metrics = {}
    for key, fn in NUMERIC.items():
        stats = describe([_safe(fn, a) for a in analyses])
        if stats:
            stats["consistency"] = "constant" if (stats["cv"] is not None and stats["cv"] < 0.25) else "variable"
            metrics[key] = stats

    traits = {k: _traits([[_safe(fn, a)] for a in analyses if _safe(fn, a) is not None], n, threshold)
              for k, fn in CATEGORICAL_ANALYSIS.items()}
    nd = len(decodes)
    if nd:
        for key in DECODE_SCALARS:
            vals = [[_norm(_get(dc, key))] for dc in decodes if _norm(_get(dc, key)) is not None]
            if vals:
                traits[key] = _traits(vals, nd, threshold)
        for key in DECODE_LISTS:
            vals = [[_norm(x) for x in (_get(dc, key) or []) if _norm(x)] for dc in decodes]
            if any(vals):
                traits[key] = _traits(vals, nd, threshold)

    style = {
        "schema": "reelkit.style/1",
        "tool_version": VERSION,
        "name": name,
        "generated_at": now_iso(),
        "n_reels": n,
        "n_decoded": nd,
        "reels": [a["reel_id"] for a in analyses],
        "uploaders": sorted(uploaders),
        "recurring_threshold": threshold,
        "warnings": warnings,
        "metrics": metrics,
        "traits": traits,
    }
    style["editing_rules"] = derive_rules(style)
    return style


def _safe(fn, a):
    try:
        return fn(a)
    except (KeyError, TypeError):
        return None


def _top(traits: dict, key: str, recurring_only=True):
    for t in traits.get(key, []):
        if not recurring_only or t["class"] == "recurring":
            return t["value"]
    return None


def derive_rules(style: dict) -> dict:
    """Turn the profile into concrete parameters for `plan`. Each rule records its origin."""
    d = load_defaults()
    ed, cap = d["editing"], d["captions"]
    m, tr = style["metrics"], style["traits"]
    rules, origin = {}, {}

    def pick(name, value, default, src):
        if value is None:
            rules[name], origin[name] = default, "défaut"
        else:
            rules[name], origin[name] = value, src

    def med(k):
        return (m.get(k) or {}).get("median")

    pick("target_duration_s", med("duration_s"), ed["target_duration_s"], "médiane des vidéos")
    pick("shot_median_s", med("shot_median_s"), ed["shot_median_s"], "médiane des plans")
    pick("shot_min_s", max(med("shot_min_s"), 0.5) if med("shot_min_s") else None, ed["shot_min_s"],
         "médiane des plans les plus courts")
    pick("shot_max_s", med("shot_max_s"), ed["shot_max_s"], "médiane des plans les plus longs")
    pick("first_shot_max_s", med("first_cut_at_s"), ed["first_shot_max_s"], "médiane de la 1re coupe")
    pick("words_per_minute", med("words_per_minute"), ed["words_per_minute"], "débit de parole mesuré")
    wpc = _top(tr, "captions.words_per_caption")
    pick("words_per_caption", int(wpc) if isinstance(wpc, (int, float)) and not isinstance(wpc, bool) else None,
         ed["words_per_caption"], "trait récurrent")
    rules["image_motion"], origin["image_motion"] = ed["image_motion"], "défaut"

    pos = _top(tr, "captions.position")
    case = _top(tr, "captions.case")
    rules["captions"] = {
        **cap,
        "position": _position(pos) or cap["position"],
        "uppercase": (case in ("uppercase", "majuscules", "caps")) if case else cap["uppercase"],
        "highlight_color": _hex(_top(tr, "captions.highlight_color")) or cap["highlight_color"],
        "enabled": _top(tr, "captions.present") is not False,
    }
    origin["captions"] = "traits récurrents si présents, sinon défauts"
    rules["origin"] = origin
    if rules["shot_min_s"] > rules["shot_median_s"]:
        rules["shot_min_s"] = round(rules["shot_median_s"] * 0.6, 2)
    if rules["shot_max_s"] < rules["shot_median_s"]:
        rules["shot_max_s"] = round(rules["shot_median_s"] * 1.6, 2)
    return rules


def _position(value):
    if not value:
        return None
    v = str(value)
    if any(k in v for k in ("center", "centre", "middle", "milieu")) and "lower" not in v and "bas" not in v:
        return "center"
    if any(k in v for k in ("top", "haut")):
        return "top"
    return "lower-third"


def _hex(value):
    if isinstance(value, str) and len(value.strip("#")) == 6:
        try:
            int(value.strip("#"), 16)
            return "#" + value.strip("#").upper()
        except ValueError:
            return None
    return None


def render_md(style: dict) -> str:
    lines = [f"# Profil de style — {style['name']}", "",
             f"_Généré le {style['generated_at']} à partir de {style['n_reels']} vidéo(s) "
             f"({style['n_decoded']} décodée(s)). Seuil « récurrent » : {int(style['recurring_threshold'] * 100)} %._", ""]
    if style["warnings"]:
        lines += ["## Avertissements"] + [f"- ⚠️ {w}" for w in style["warnings"]] + [""]
    lines += ["## Métriques mesurées", "", "| Métrique | Médiane | Min | Max | CV | Constance |",
              "|---|---|---|---|---|---|"]
    for k, s in style["metrics"].items():
        lines.append(f"| {k} | {s['median']} | {s['min']} | {s['max']} | {s['cv']} | {s['consistency']} |")
    lines += ["", "## Traits (récurrents vs ponctuels)", ""]
    for k, vals in style["traits"].items():
        desc = ", ".join(f"{v['value']} ({v['count']}/{v['class']})" for v in vals)
        lines.append(f"- **{k}** : {desc}")
    lines += ["", "## Règles de montage dérivées", "", "```json",
              json.dumps(style["editing_rules"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def save(style: dict, out: Path) -> Path:
    out = Path(out)
    write_json(out, style)
    out.with_suffix(".md").write_text(render_md(style), encoding="utf-8")
    log(f"profil écrit: {out} (+ {out.with_suffix('.md').name})")
    return out
