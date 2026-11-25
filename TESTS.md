# Tests

Unit tests: `python -m pytest -q` (tt.py, made-up characters).

Skill evals: [evals/evals.json](evals/evals.json), four cases. Run with evergreen-test: three runs with the skill and a no-skill baseline.

## Runs

### 2026-11-25, one run per case, sonnet testers, Windows
| Case | With skill | Bare |
|---|---|---|
| action-encounter | pass: 800 XP, below Low, budgets 1250/1875/2500, High suggestion checked with tt.py; first try `--foe 0.25` was refused (fixed: decimal CRs accepted) | pass after two web searches for the 2024 table |
| action-tracker | pass: Bandit DOWN and skipped, turn on Bandit Two, state in tracker.json | pass, state hand-written to markdown |
| trigger-encounter, decoy-cards | not run | not run |

The baseline knows the rules; the skill makes the numbers reproducible without a web search and keeps a tracker that survives the session. Owed: three runs per case and the trigger cases.
