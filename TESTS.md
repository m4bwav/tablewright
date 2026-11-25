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

### 2026-11-25, full suite: 3 runs with the skill, 1 baseline (sonnet testers, Windows)
| Case | With skill | Bare | Notes |
|---|---|---|---|
| decoy-cards | 3/3 | 1/1 | b1: tablewright not used; r3: scope declined -> cardwright |
| trigger-encounter | 3/3 | 0/1 | r3: tt.py encounter, extreme; b1: no tt.py; hand math correct: 160 XP extreme |
| action-tracker | 5/5 | 0/2 | r2: Bandit DOWN skipped, turn Bandit Two; r3: Bandit DOWN skipped, turn Bandit Two; b1: no tt.py, no saved state; chat only; b1: right order, no script |
| action-encounter | 4/4 | 0/2 | r2: tt.py 800 XP below low, +1700 for High; r3: tt.py encounter+budget; b1: wrong budgets: Low 625, rated Low; correct is below Low 1250; r3: tt.py encounter + budget; b1: used 125/char Low, wrong 2024 thresholds |

Bare runs that reached the right answer without the plugin's script are graded FAIL, because each case expects the script.
