import json
import tempfile
import unittest
from pathlib import Path

from _common import ENGINE  # noqa: F401

from reelkit import grab, plan, style, transcribe, util


class Util(unittest.TestCase):
    def test_srt_roundtrip(self):
        cues = [{"start": 0.0, "end": 1.25, "text": "Bonjour à tous"}, {"start": 61.5, "end": 3725.042, "text": "fin"}]
        with tempfile.TemporaryDirectory() as t:
            p = util.write_srt(cues, Path(t) / "a.srt")
            back = util.parse_srt(p.read_text(encoding="utf-8"))
        self.assertEqual([c["text"] for c in back], ["Bonjour à tous", "fin"])
        self.assertAlmostEqual(back[1]["end"], 3725.042, places=3)

    def test_count_words_strips_tags(self):
        self.assertEqual(util.count_words("[Music] l'été arrive (applause) 2026"), 2)

    def test_slugify(self):
        self.assertEqual(util.slugify("Été / Reel #1 ?"), "Ete-Reel-1")
        self.assertEqual(util.slugify("???"), "untitled")

    def test_describe(self):
        d = util.describe([1, 2, 3, None])
        self.assertEqual((d["n"], d["median"], d["min"], d["max"]), (3, 2.0, 1.0, 3.0))
        self.assertIsNone(util.describe([None]))


class Grab(unittest.TestCase):
    def test_instagram_urls(self):
        ok = ["https://www.instagram.com/reel/DeYjzhEkpJg/?vrfl=MXZl",
              "https://instagram.com/p/AbC_-1/", "https://www.instagram.com/someone/reel/XYZ123/"]
        for u in ok:
            self.assertTrue(grab.INSTAGRAM_RE.match(u), u)
        self.assertEqual(grab.reel_id_for(ok[0], False), "DeYjzhEkpJg")

    def test_rejects_lookalikes_and_other_sites(self):
        for u in ["https://instagram.com.evil.com/reel/X/", "http://instagram.com/reel/X/",
                  "https://www.instagram.com/accounts/login/"]:
            self.assertIsNone(grab.INSTAGRAM_RE.match(u), u)
        with self.assertRaises(util.ReelkitError):
            grab.reel_id_for("https://www.tiktok.com/@a/video/1", any_site=False)
        self.assertTrue(grab.reel_id_for("https://www.tiktok.com/@a/video/1", any_site=True).startswith("web-"))


class Plan(unittest.TestCase):
    RULES = {"shot_median_s": 2.0, "shot_min_s": 0.8, "shot_max_s": 3.0, "first_shot_max_s": 1.2}

    def test_shot_lengths_cover_total_and_respect_min(self):
        for total in (3.0, 7.3, 15.0, 29.97, 60.0):
            ls = plan.shot_lengths(total, self.RULES)
            self.assertAlmostEqual(sum(ls), total, delta=0.01)
            self.assertTrue(all(x >= 0.8 - 1e-6 for x in ls), ls)
            self.assertLessEqual(ls[0], 1.2)

    def test_chunk_words_breaks_on_punctuation(self):
        words = [{"start": i, "end": i + 1, "word": w} for i, w in enumerate("Un deux. Trois quatre cinq six".split())]
        chunks = plan.chunk_words(words, 3)
        self.assertEqual([c["text"] for c in chunks], ["Un deux.", "Trois quatre cinq", "six"])

    def test_words_from_script_fit_duration(self):
        ws = plan.words_from_script("un deux trois quatre", 10.0)
        self.assertEqual(len(ws), 4)
        self.assertLess(ws[-1]["end"], 10.0)

    def test_ass_color_is_bgr(self):
        self.assertEqual(plan._ass_color("#FFE600"), "&H0000E6FF")


class Transcribe(unittest.TestCase):
    def test_words_from_segments_without_word_timing(self):
        ws = transcribe.words_from_segments([{"start": 0, "end": 2, "text": "a b"}])
        self.assertEqual([(w["word"], w["start"], w["end"]) for w in ws], [("a", 0, 1), ("b", 1, 2)])


def _fake_analysis(d: Path, rid, shot_median, cpm, uploader="creator"):
    d.mkdir(parents=True)
    util.write_json(d / "analysis.json", {
        "reel_id": rid, "source": {"uploader": uploader}, "content_mode": "spoken",
        "technical": {"duration_s": 30, "fps": 30, "orientation": "vertical", "aspect_ratio": "9:16"},
        "pacing": {"shots": 12, "cuts_per_minute": cpm, "first_cut_at_s": 1.0, "shots_in_first_3s": 2,
                   "shot_length_s": {"median": shot_median, "mean": shot_median, "min": 0.6, "max": 4.0}},
        "transcript": {"words_per_minute_speech": 170}, "audio": {"integrated_lufs": -14.5, "silence_ratio": 0.1}})


class Style(unittest.TestCase):
    def test_recurring_vs_one_off(self):
        with tempfile.TemporaryDirectory() as t:
            dirs = []
            for i, pos in enumerate(["lower-third", "lower-third", "center"]):
                d = Path(t) / f"r{i}"
                _fake_analysis(d, f"r{i}", 2.0 + i * 0.1, 22)
                dec = json.loads((util.TEMPLATES_DIR / "decode.template.json").read_text(encoding="utf-8"))
                dec.update(filled=True, reel_id=f"r{i}", transitions=["hard cut"] + (["zoom"] if i == 2 else []))
                dec["captions"].update(position=pos, case="UPPERCASE", highlight_color="#ffe600")
                util.write_json(d / "decode.json", dec)
                dirs.append(d)
            s = style.build_style(dirs, "c")
        pos = {v["value"]: v["class"] for v in s["traits"]["captions.position"]}
        self.assertEqual(pos, {"lower-third": "recurring", "center": "one-off"})
        tr = {v["value"]: v["class"] for v in s["traits"]["transitions"]}
        self.assertEqual(tr, {"hard cut": "recurring", "zoom": "one-off"})
        r = s["editing_rules"]
        self.assertEqual(r["captions"]["position"], "lower-third")
        self.assertTrue(r["captions"]["uppercase"])
        self.assertEqual(r["captions"]["highlight_color"], "#FFE600")
        self.assertAlmostEqual(r["shot_median_s"], 2.1)
        self.assertEqual(s["metrics"]["cuts_per_minute"]["consistency"], "constant")

    def test_warns_on_mixed_creators(self):
        with tempfile.TemporaryDirectory() as t:
            _fake_analysis(Path(t) / "a", "a", 2, 20, "alice")
            _fake_analysis(Path(t) / "b", "b", 2, 20, "bob")
            s = style.build_style([Path(t) / "a", Path(t) / "b"], "x")
        self.assertTrue(any("Plusieurs comptes" in w for w in s["warnings"]))


if __name__ == "__main__":
    unittest.main()
