"""Run the verifier measurement scripts and compare every count with expected.txt.

Usage: run_baseline.py [--kinds k1,k2,...]   (default: every group)

Groups: `quote` runs the eleven PR #35 commands (the quote-to-page rule); `count`, `unsigned`,
`suffix`, `trailing`, `leading_decimal`, `free` and `control` each run fuzz_claim_values.py for
that kind (the claim-against-quote rule, issue #45).

Before running anything it checks two things, and a failure of either exits 1:
- pins: the SHA-256 of each of the six PR #35 scripts (PINNED_SCRIPTS) against pinned.sha256. A
  changed digest, a missing script, one of the six with no line, or a missing pin file fails.
- argv: every command (script, seed, n, extra arguments) must be the one that each of its counts'
  expected.txt lines names before the colon of its set column, so lowering a sample size fails.
A denominator that no rule can move (FIXED) also fails when it changes; the other denominators
only print a note.

Exit 0 when no fail-open count (wrong prices or claims verified) and no fail-closed count (true
quotes or claims rejected) is above its "at most" value in expected.txt, 1 when one is or one is
missing, 2 for an unknown kind. A count that fell prints FELL and does not fail.

To add a group: register a Group (its commands, and any totals over their counts) in GROUPS under
its kind; add its lines to expected.txt under that kind, each set column starting with its
command.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EXPECTED = HERE / "expected.txt"
PINNED = HERE / "pinned.sha256"
PINNED_SCRIPTS = (
    "fuzz_place_all.py",
    "fuzz_dense.py",
    "fuzz_skip.py",
    "fuzz_add.py",
    "fuzz_place2.py",
    "fuzz_spread.py",
)
CLAIM_ARGV = ("fuzz_claim_values.py", "45", "300")  # seed, then n cases per kind
CLAIM_KINDS = ("count", "unsigned", "suffix", "trailing", "leading_decimal", "free", "control")
# Denominators fixed before any receipts.verify call: fuzz_place2.py's step() counts one try per
# iteration (tally.tried, line 127), fuzz_spread.py's main() counts one per iteration (line 47),
# and fuzz_claim_values.py verifies one WRONG and one TRUE claim in each of its n cases per kind,
# with no skip (record(), called once per case by run_kind()).
FIXED = frozenset(
    {"place2.s7", "place2.s11", "place2.s12", "place2.s13", "place2.total"}
    | {"spread.open"}
    | {f"claims.{kind}.{side}" for kind in CLAIM_KINDS for side in ("open", "closed")}
)

Obs = tuple[str, int, int]  # name, observed count, denominator
GroupResult = tuple[list[str], list[Obs]]  # summary lines as printed, observations
NOISE = ("RULES", "OPEN", "CLOSED", "EX", "VERIFIED-WITH-WRONG-SLOT", "SHAPE")


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
class Group:
    commands: tuple[Command, ...]
    totals: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (name, the counts it sums)


@dataclass(frozen=True)
class Limit:
    group: str
    direction: str
    at_most: int
    denominator: int
    over: str  # the set column: "<command>: <what is counted, of what>"


def read_pins(path: Path) -> tuple[dict[str, str], list[str]]:
    """`{script name: digest}` from `path`, and one message per line that is not `digest name`."""
    pins: dict[str, str] = {}
    bad: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 2:
            pins[fields[1]] = fields[0]
        elif fields:
            bad.append(f"{path.name}: unreadable pin line {line!r}")
    return pins, bad


def check_pins(path: Path) -> list[str]:
    """One message per PR #35 script that is unpinned, missing or changed, or per unreadable pin."""
    if not path.is_file():
        return [f"{path.name}: pin file is missing"]
    pins, bad = read_pins(path)
    bad += [f"{n}: no line in {path.name} (unpinned)" for n in PINNED_SCRIPTS if n not in pins]
    for name, digest in pins.items():
        script = HERE / name
        if not script.is_file():
            bad.append(f"{name}: pinned script is missing")
        elif hashlib.sha256(script.read_bytes()).hexdigest() != digest:
            bad.append(f"{name}: SHA-256 differs from pinned.sha256 (the generation changed)")
    return bad


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


QUOTE_TOTALS = (
    ("add.open.total", ("add.s51.open", "add.s52.open", "add.s53.open")),
    ("add.closed.total", ("add.s51.closed", "add.s52.closed", "add.s53.closed")),
    ("place2.total", tuple(f"place2.s{s}" for s in (7, 11, 12, 13))),
    ("skip.total", ("skip.s5", "skip.s6")),
)


def claim_command(kind: str) -> Command:
    wrong = rf"kind={kind} WRONG claims verified (\d+) of (\d+)"
    true = rf"kind={kind} TRUE claims rejected (\d+) of (\d+)"
    metrics = (Metric(f"claims.{kind}.open", wrong), Metric(f"claims.{kind}.closed", true))
    return Command((*CLAIM_ARGV, kind), metrics)


GROUPS: dict[str, Group] = {"quote": Group(tuple(quote_commands()), QUOTE_TOTALS)}
GROUPS |= {kind: Group((claim_command(kind),)) for kind in CLAIM_KINDS}


def run_group(group: Group) -> GroupResult:
    lines, obs = run_commands(list(group.commands))
    return lines, obs + [total(name, parts, obs) for name, parts in group.totals]


def read_expected(path: Path) -> dict[str, Limit]:
    limits = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        group, name, direction, at_most, den, over = (f.strip() for f in raw.split("|", 5))
        limits[name] = Limit(group, direction, int(at_most), int(den), over)
    return limits


def argv_mismatches(groups: Iterable[Group], limits: dict[str, Limit]) -> list[str]:
    """One message per count whose command is not the one its expected.txt line names."""
    runs = {m.name: " ".join(c.argv) for g in groups for c in g.commands for m in c.metrics}
    bad = []
    for name, argv in runs.items():
        limit = limits.get(name)
        named = argv if limit is None else limit.over.partition(":")[0].strip()
        if named != argv:
            bad.append(f"{name}: run_baseline.py runs '{argv}', expected.txt names '{named}'")
    return bad


def preflight(limits: dict[str, Limit]) -> list[str]:
    """Why no count can be trusted, checked before anything runs: the pins, then every argv."""
    pins = [f"PIN MISMATCH {e}" for e in check_pins(PINNED)]
    return pins + [f"ARGV MISMATCH {e}" for e in argv_mismatches(GROUPS.values(), limits)]


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
        moved = den != limit.denominator
        note = f" (denominator was {limit.denominator})" if moved else ""
        fixed = moved and name in FIXED
        note += " — FIXED DENOMINATOR CHANGED" if fixed else ""
        lines.append(f"{name}: {count} of {den}, expected at most {limit.at_most} — {word}{note}")
        failed = failed or word == "ROSE" or fixed
    return lines, failed


def unobserved(kinds: list[str], obs: list[Obs], limits: dict[str, Limit]) -> list[str]:
    seen = {o[0] for o in obs}
    return [n for n, lim in limits.items() if lim.group in kinds and n not in seen]


def parse_kinds(argv: list[str]) -> list[str] | None:
    """The kinds to run, or None after printing why the arguments are unusable (exit 2)."""
    kinds = list(GROUPS)
    if argv[:1] == ["--kinds"] and len(argv) == 2:
        kinds = [k for k in argv[1].split(",") if k]
    elif argv:
        print("usage: run_baseline.py [--kinds k1,k2,...]", file=sys.stderr)
        return None
    unknown = [k for k in kinds if k not in GROUPS]
    if unknown or not kinds:
        print(f"unknown or empty kinds {unknown}; known: {sorted(GROUPS)}", file=sys.stderr)
        return None
    return kinds


def main(argv: list[str]) -> int:
    kinds = parse_kinds(argv)
    if kinds is None:
        return 2
    limits = read_expected(EXPECTED)
    errors = preflight(limits)
    if errors:
        print("\n".join(errors))
        return 1
    lines: list[str] = []
    obs: list[Obs] = []
    for kind in kinds:
        group_lines, group_obs = run_group(GROUPS[kind])
        lines.extend(group_lines)
        obs.extend(group_obs)
    report, failed = compare(obs, limits)
    missing = unobserved(kinds, obs, limits)
    print("\n".join(lines + report + [f"{n}: not observed — MISSING" for n in missing]))
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
