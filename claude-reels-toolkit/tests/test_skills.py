import re
import unittest

from _common import ROOT

import install


class SkillStructure(unittest.TestCase):
    def test_every_skill_valid(self):
        dirs = install.skill_dirs()
        self.assertEqual({d.name for d in dirs},
                         {"reel-studio", "reel-analyze", "reel-style", "reel-adapt", "reel-render"})
        for d in dirs:
            with self.subTest(skill=d.name):
                self.assertEqual(install.validate_skill(d), [])

    def test_frontmatter_parses_as_yaml_when_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML non installé (validation stricte ignorée)")
        for d in install.skill_dirs():
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            data = yaml.safe_load(text.split("---")[1])
            self.assertEqual(data["name"], d.name)
            self.assertIsInstance(data["description"], str)

    def test_engine_files_referenced_exist(self):
        studio = ROOT / "skills" / "reel-studio"
        for rel in ("scripts/reelkit.py", "config/defaults.json", "templates/decode.template.json"):
            self.assertTrue((studio / rel).is_file(), rel)

    def test_skills_reference_only_existing_commands(self):
        from reelkit.cli import build_parser
        cmds = set(build_parser()._subparsers._group_actions[0].choices)
        for d in install.skill_dirs():
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            for cmd in re.findall(r"<RK> ([a-z]+)", text):
                self.assertIn(cmd, cmds, f"{d.name} cite une commande inconnue: {cmd}")


if __name__ == "__main__":
    unittest.main()
