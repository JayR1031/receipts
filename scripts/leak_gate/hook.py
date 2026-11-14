#!/usr/bin/env python3
"""pre-commit entry: scan the staged files pre-commit passes as arguments."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_tracked import load_patterns, scan  # noqa: E402


def main(argv: list[str]) -> int:
    repo = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    patterns = load_patterns()
    hits = scan([repo / a for a in argv], patterns, repo)
    print(f"leak-gate (staged): {len(argv)} files against {len(patterns)} patterns")
    for hit in hits:
        print(hit)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
