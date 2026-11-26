# Changelog

## 0.3.0 (2026-11-26)
- `tt.py world`: setting card check (6 to 8 traits, each anchored to a place, NPC or faction). Idea from Shea, The Lazy Dungeon Master (ch. XIV).
- `tracker --public`: players' board with damage taken and no HP; `+` marks who is on deck. Ideas from The Lazy Dungeon Master and Johnn Four, How to Run Fast and Exciting Combats (3.04).
- `tt.py combat-log`: turn times of a real fight from a CSV, flags players over 90 s a turn. Idea from How to Run Fast and Exciting Combats (1.01).
- `tt.py threads`: open story promises, latest first, `--finale` check. Idea from Walmsley, Play Unsafe (p. 43-47).
- `tt.py npcs`: three-line NPC card check. Idea from Johnn Four, 3 Line NPCs.
- 7 new tests; wording and thresholds are ours.

## 0.2.0 (2026-11-26)
- `tt.py prep`: checks a session prep card (opening, three leads, NPCs with current goals, a way out of each fight) with 2 tests. Idea from Shea, The Lazy Dungeon Master (session prep and combat chapters); the checks and wording are ours.
- `tt.py fiveroom`: checks an adventure plan against the five-role arc (entrance, puzzle, setback, climax, reward) with 2 tests. Idea from Johnn Four, 5 Room Dungeons (method section); thresholds are one GM's advice, unverified.

## 0.1.1 (2026-11-25)
- Licence fixes: encounter budgets credited to Pathfinder and Starfinder GM Core, ORC notice added, SRD 5.2.1 with the exact CC-BY-4.0 attribution.
- Full eval suite results in TESTS.md.

## 0.1.0 (2026-11-25)
- First version: hub skill (encounters, table tracker, characters, minis and maps routing), references for encounter math, the character schema and minis, `tt.py` (encounter, budget, tracker, sheet, check, licence) with 12 tests. An eval found `--foe 0.25` refused; decimal CRs are accepted. Starfinder character and mini pipelines stay in their project; tablewright routes to them as the first system adapter.
