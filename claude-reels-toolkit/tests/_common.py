import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "skills" / "reel-studio" / "scripts"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT))
