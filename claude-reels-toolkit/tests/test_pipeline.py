"""End-to-end integration test (needs ffmpeg). Runs the same self-test users run after install."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _common import ENGINE


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg absent")
class Pipeline(unittest.TestCase):
    def test_selftest_end_to_end(self):
        with tempfile.TemporaryDirectory() as t:
            proc = subprocess.run([sys.executable, str(ENGINE / "reelkit.py"), "selftest", "--dir", t],
                                  capture_output=True, text=True, timeout=600)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr[-3000:])
            rep = json.loads((Path(t) / "selftest_report.json").read_text(encoding="utf-8"))
            self.assertTrue(rep["ok"])
            ws = Path(t) / "workspace"
            reel = next((ws / "reels").iterdir())
            for f in ("analysis.json", "report.md", "contact_sheet.jpg", "decode.json", "frames/frame_001.jpg"):
                self.assertTrue((reel / f).exists(), f)
            proj = ws / "projects" / "selftest"
            for f in ("timeline.json", "captions.srt", "captions.ass", "render.mp4", "render.verify.json"):
                self.assertTrue((proj / f).exists(), f)

    def test_verify_detects_wrong_resolution(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "x.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25",
                            "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True)
            proc = subprocess.run([sys.executable, str(ENGINE / "reelkit.py"), "--workspace", t, "verify", str(out),
                                   "--width", "1080", "--height", "1920", "--fps", "30"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)
            self.assertIn("NON CONFORME", proc.stdout)


if __name__ == "__main__":
    unittest.main()
