# Log

Append-only. One line per operation: `## [YYYY-MM-DD] op | title` where op is one of add, update, supersede, verify, verify-failed, prune, handoff, index. Newest at the bottom. Never edited, only appended; this is the history the entries themselves do not carry.

## [2026-11-25] init | scaffolded
- 2026-11-25: tablewright 0.1.0 built: tt.py, 11 tests, hub skill, references, evergreen unit.
- 2026-11-25: v0.1.0 tagged and released; installed from mark-local.
- 2026-11-25: licence check. PF2e/SF2e budgets credited to GM Core (was Player Core) with an ORC attribution notice; D&D tables moved to SRD 5.2.1 with WotC's exact CC-BY-4.0 statement in tt.py licence; source URLs checked 2026-11-25.
- 2026-11-26: 0.7.0 adds mystery, safety, item cost/uses/friction fields, table combine. Note: main() party check now only applies to int --party (safety takes a file path).
- 2026-11-26: 0.8.0 adds encounter waves/pool/prep/morale/escape and --hazard (identical repeats add 10% each), table --die, threads --stale with (opened: session N), campaign events/climax signs, fiveroom hints/reward, session-log. Tests in tests/test_v080.py import helpers from test_tt. Skipped AL loot split and party-strength overlay.
- 2026-11-26: 0.9.0 adds strength, loot, reaction, heat, premise, wander (tests/test_v090.py). Sources: AL DMG 2.0, Lankhmar GM guide, Game Ideas collection, 1e DMG harvest notes. Skipped premise-rut, premise tables, district cards, henchmen, forced march.
