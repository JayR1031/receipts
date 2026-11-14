# leak_gate

The leak gate is a repo-wide data denylist: `check_tracked.py` reads `denylist.txt` next to
it — one literal, case-sensitive substring per line — and scans every file `git ls-files`
reports for this repository, printing `scanned N files against M patterns` before it says
anything else, so an empty denylist is visible rather than a silent pass. Any hit is printed
as `path:line: pattern` and the script exits 1; `hook.py` runs the same scan restricted to the
filenames pre-commit passes it, so a match is caught at commit time as well as in CI.

The scan has no path filter and never will. A gate scoped to one folder — `apps/api/`, a
`docs/` tree, anything narrower than the whole repository — reports green about every file
outside that folder, and a green check that never looked is a worse failure mode than a check
that is visibly absent: nobody double-checks a passing gate. Client names, real invoice or
account numbers, and other data are just as likely to land in a top-level README, a script
under `scripts/`, or a stray note as in the paths a narrower scope would have picked.

An empty `denylist.txt` is not proof the gate works, only proof it has nothing to look for.
`bin/red-test` plants a known pattern in a tracked file and confirms `check_tracked.py` exits
1 and names it, then removes the plant — the same discipline this repo's tests use everywhere
else: watch the guard turn red before trusting it stays green. Run `bin/red-test` after any
change to `check_tracked.py`, `hook.py`, or the denylist format itself.
