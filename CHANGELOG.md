# Changelog

## 0.5.0 (2026-11-26)
- `tt.py villain`: villain cards (want, public face, reach, indirect harms, offers with more than one option). Idea from Johnn Four, 7 Ways to Improve Your GMing (p. 13-14, 20).
- `tt.py twist`: planned twists need a workaround when they remove an ability, spread over axes and include a positive one. Idea from McDonald, Plot Twists (p. 4-8).
- `tt.py campaign`: PC plotlines, adventure phase and reason, written-out NPCs stay out, opposition, aftermath after major adventures, payback payoffs. Idea from Johnn Four, Campaign Creation Guide (p. 59, 93, 122-133).
- `prep`: optional `## Clock` with a consequence per step and a `shown:` line. Idea from Wick, Play Dirty.
- 4 new tests; wording and thresholds are ours and unverified.

## 0.4.0 (2026-11-26)
- `tt.py table`: random encounter table check (roll gaps and overlaps, fight share, unavoidable easy fights). Idea from Nerzugal's Dungeon Master Toolkit (travel tables).
- `tt.py item`: magic items pair each boon with an equal or stronger drawback. Idea from Nerzugal's Dungeon Master Toolkit.
- `encounter --mission --clock --healers`: warnings for kill-only fights, missing or long clocks, and healing foes. Idea from How to Run Fast and Exciting Combats (2.02, 2.10).
- `fiveroom`: puzzle `fail_cost`, `lock_in`/`reset`, `min_players`; climax `immune` without `weakness`; setback plus climax XP over `fight_budget`. Ideas from Nerzugal's Toolkit, Bill Webb's Book of Dirty Tricks and 5 Room Dungeons.
- `prep`: `## Hazards` need a warning; lethal threats need a tell and may not be hidden; false leads fewer than real ones, each with an ending. Ideas from Nerzugal's Toolkit and Bill Webb's Book of Dirty Tricks.
- `world`: optional nation (internal and external conflict), society (leader, goal, rule) and city (theme, food, shelter, shop, twist) cards. Idea from the Kobold Guide to Worldbuilding.
- 7 new tests; wording and thresholds are ours and unverified.

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
