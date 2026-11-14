#!/usr/bin/env python3
"""Repo-wide data denylist gate. Scans every tracked file, no path filter.

Exit 1 on any hit. Prints the scan size so an empty list is visible, not silent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DENYLIST = HERE / "denylist.txt"
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip"}


def load_patterns(path: Path = DENYLIST) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def tracked_files(repo: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, check=True, capture_output=True
    ).stdout
    return [repo / p for p in out.decode().split("\0") if p]


def scan(paths: list[Path], patterns: list[str], repo: Path) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if path.resolve() == DENYLIST.resolve() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if not path.is_file():
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            hits.extend(f"{path.relative_to(repo)}:{lineno}: {p}" for p in patterns if p in line)
    return hits


def main(argv: list[str] | None = None) -> int:
    repo = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    patterns = load_patterns()
    paths = tracked_files(repo)
    hits = scan(paths, patterns, repo)
    print(f"leak-gate: scanned {len(paths)} files against {len(patterns)} patterns")
    for hit in hits:
        print(hit)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
