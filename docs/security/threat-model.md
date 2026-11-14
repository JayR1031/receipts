# Threat model (STRIDE-light)

| Asset | Threat | Control | Test that proves the control |
| --- | --- | --- | --- |
| Secrets in the repo (API keys, tokens, credentials) | A secret is committed and reaches a fork, a log, or a public remote | Gitleaks (`.gitleaks.toml`, `.pre-commit-config.yaml`) scanning staged files and CI | `bin/red-test` plants a known-format secret and confirms gitleaks exits non-zero on it |
| Client data in the repo (names, invoice numbers, account identifiers) | Real client data lands in a tracked file via a commit, a doc, or a fixture | The leak-gate denylist (`scripts/leak_gate/`), repo-wide, no path filter | `bin/red-test` plants a denylisted pattern in a tracked file and confirms `check_tracked.py` exits 1 and names the hit |
| Third-party dependencies | A dependency ships a known vulnerability | Dependency audit job blocking merge (Dependabot alerts + `pip-audit` / `npm audit` in CI) | CI run against a pinned vulnerable version confirms the audit job fails the build |

Add rows here as new assets or controls are introduced. Every row needs a test that proves the
control fails when it should — a control without a red case is not verified.
