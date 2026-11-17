#!/usr/bin/env python3
"""Entry point: python reelkit.py <command> ...  (see `python reelkit.py --help`)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reelkit.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
