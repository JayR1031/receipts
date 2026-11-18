"""Run the verifier measurement scripts and compare every count with expected.txt.

Usage: run_baseline.py [--kinds k1,k2,...]   (default: every group)

Exit 0 when no fail-open count (wrong prices verified) and no fail-closed count (true quotes
rejected) is above its "at most" value in expected.txt, 1 when one is or one is missing, 2 for an
unknown kind. A count that fell prints FELL and does not fail.

To add a group: write a function returning a GroupResult (summary lines, observations) and
register it in GROUPS under its kind; add its lines to expected.txt under that kind.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EXPECTED = HERE / "expected.txt"

Obs = tuple[str, int, int]  # name, observed count, denominator
GroupResult = tuple[list[str], list[Obs]]  # summary lines as printed, observations
NOISE = ("RULES", "OPEN", "CLOSED", "EX", "VERIFIED-WITH-WRONG-SLOT")


@dataclass(frozen=True)
class Metric:
    name: str
    pattern: str  # regex; group 1 is the count, group 2 the denominator
    swap: bool = False  # True when the denominator is printed before the count


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    metrics: tuple[Metric, ...]


@dataclass(frozen=True)
class Limit:
    group: str
    direction: str
    at_most: int
    denominator: int


def run_script(argv: tuple[str, ...]) -> str:
    cmd = [sys.executable, str(HERE / argv[0]), *argv[1:]]
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def summary_lines(output: str) -> list[str]:
    return [ln for ln in output.splitlines() if not ln.startswith(NOISE)]


def parse(output: str, metrics: tuple[Metric, ...]) -> list[Obs]:
    found = []
    for m in metrics:
        hit = re.search(m.pattern, output)
        if hit is None:
            raise RuntimeError(f"no line matching {m.pattern!r} for {m.name}")
        count, den = int(hit.group(1)), int(hit.group(2))
        found.append((m.name, den, count) if m.swap else (m.name, count, den))
    return found


def run_commands(commands: list[Command]) -> GroupResult:
    lines: list[str] = []
    obs: list[Obs] = []
    for cmd in commands:
        out = run_script(cmd.argv)
        lines.append("$ " + " ".join(cmd.argv))
        lines.extend(summary_lines(out))
        obs.extend(parse(out, cmd.metrics))
    return lines, obs


def total(name: str, parts: tuple[str, ...], obs: list[Obs]) -> Obs:
    rows = [o for o in obs if o[0] in parts]
    return name, sum(o[1] for o in rows), sum(o[2] for o in rows)


def add_commands() -> list[Command]:
    cmds = []
    for seed, extra in (("51", ()), ("52", ()), ("53", ("all", "1"))):
        mis = rf"seed={seed} MIS tried=\d+ scored>=90=(\d+) verified=(\d+)"
        true = rf"seed={seed} TRUE tried=(\d+) verified=\d+ rejected-for-numbers=(\d+)"
        cmds.append(
            Command(
                ("fuzz_add.py", seed, "6000", *extra),
                (
                    Metric(f"add.s{seed}.open", mis, swap=True),
                    Metric(f"add.s{seed}.closed", true, swap=True),
                ),
            )
        )
    return cmds


def quote_commands() -> list[Command]:
    place_all = (
        Metric("place_all.open", r"misquotes tried=(\d+) .*verified=(\d+)", swap=True),
        Metric("place_all.closed", r"legit tried=(\d+) .*rejected-for-numbers=(\d+)", swap=True),
    )
    dense = (Metric("dense.closed", r"true quotes tried=(\d+) .*rejected-for-numbers=(\d+)", True),)
    cmds = [Command(("fuzz_place_all.py", "2", "6000"), place_all)]
    cmds.append(Command(("fuzz_dense.py", "9", "8000"), dense))
    cmds.extend(add_commands())
    for seed in ("7", "11", "12", "13"):
        pat = rf"seed={seed} tried=(\d+) verified_fuzzy=\d+ verified_with_a_wrong_slot=(\d+)"
        cmds.append(
            Command(("fuzz_place2.py", seed, "40000"), (Metric(f"place2.s{seed}", pat, True),))
        )
    for seed in ("5", "6"):
        pat = rf"seed={seed} misquotes tried=(\d+) verified=(\d+)"
        cmds.append(Command(("fuzz_skip.py", seed, "6000"), (Metric(f"skip.s{seed}", pat, True),)))
    spread = r"spread misquotes tried=(\d+) verified=(\d+)"
    cmds.append(Command(("fuzz_spread.py", "1", "6000"), (Metric("spread.open", spread, True),)))
    return cmds


def quote_group() -> GroupResult:
    lines, obs = run_commands(quote_commands())
    obs.append(total("add.open.total", ("add.s51.open", "add.s52.open", "add.s53.open"), obs))
    obs.append(
        total("add.closed.total", ("add.s51.closed", "add.s52.closed", "add.s53.closed"), obs)
    )
    obs.append(total("place2.total", tuple(f"place2.s{s}" for s in (7, 11, 12, 13)), obs))
    obs.append(total("skip.total", ("skip.s5", "skip.s6"), obs))
    return lines, obs


GROUPS: dict[str, Callable[[], GroupResult]] = {"quote": quote_group}


def read_expected(path: Path) -> dict[str, Limit]:
    limits = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        group, name, direction, at_most, den = (f.strip() for f in raw.split("|")[:5])
        limits[name] = Limit(group, direction, int(at_most), int(den))
    return limits


def status(count: int, limit: Limit) -> str:
    if count > limit.at_most:
        return "ROSE"
    return "FELL" if count < limit.at_most else "ok"


def compare(obs: list[Obs], limits: dict[str, Limit]) -> tuple[list[str], bool]:
    lines: list[str] = []
    failed = False
    for name, count, den in obs:
        limit = limits.get(name)
        if limit is None:
            lines.append(f"{name}: {count} of {den}, not in expected.txt — MISSING")
            failed = True
            continue
        word = status(count, limit)
        note = "" if den == limit.denominator else f" (denominator was {limit.denominator})"
        lines.append(f"{name}: {count} of {den}, expected at most {limit.at_most} — {word}{note}")
        failed = failed or word == "ROSE"
    return lines, failed


def unobserved(kinds: list[str], obs: list[Obs], limits: dict[str, Limit]) -> list[str]:
    seen = {o[0] for o in obs}
    return [n for n, lim in limits.items() if lim.group in kinds and n not in seen]


def main(argv: list[str]) -> int:
    kinds = list(GROUPS)
    if argv[:1] == ["--kinds"] and len(argv) == 2:
        kinds = [k for k in argv[1].split(",") if k]
    elif argv:
        print("usage: run_baseline.py [--kinds k1,k2,...]", file=sys.stderr)
        return 2
    unknown = [k for k in kinds if k not in GROUPS]
    if unknown:
        print(f"unknown kind(s) {unknown}; known: {sorted(GROUPS)}", file=sys.stderr)
        return 2
    limits = read_expected(EXPECTED)
    lines: list[str] = []
    obs: list[Obs] = []
    for kind in kinds:
        group_lines, group_obs = GROUPS[kind]()
        lines.extend(group_lines)
        obs.extend(group_obs)
    report, failed = compare(obs, limits)
    missing = unobserved(kinds, obs, limits)
    print("\n".join(lines + report + [f"{n}: not observed — MISSING" for n in missing]))
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
