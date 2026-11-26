# Changelog

## 0.8.0 (2026-11-26)
- `encounter`: `--wave ROUND:COUNTxFOE[:removed_by]` reinforcements with their own XP and band, a finite `--pool`, `--prep` steps that remove waves (warns when one removes nothing), `--morale`, and `--smart` foes warn with no `--escape`. Ideas from A Goblin's Tale (DM guide) and the Book of Challenges.
- `encounter --hazard`: identical hazards count barely more than one (each repeat adds a tenth); `prep` warns on repeated hazard names. Idea from the Book of Challenges.
- `table --die N`: warns when rolls do not run 1 to the die's faces; tables without a `kind` column (step tables) now check too. Idea from the Campaign Planner.
- `threads`: `(opened: session N)` tags; open threads older than `--stale` sessions (default 3) warn. Idea from the Campaign Planner.
- `campaign`: optional `events` (trigger and level each) and a `climax` with trigger, level, session and foreshadowing `signs` scheduled before it (`--signs`, default 3). Idea from the Campaign Planner.
- `fiveroom`: optional puzzle `hints` (with a `baseline:` one) and `reward`. Idea from the Book of Challenges.
- `tt.py session-log`: a session log template whose threads feed `threads`. Idea from the Adventurers League DM Guide 4.0 and the Campaign Planner.
- 9 new tests; wording and thresholds are ours and unverified.
- Skipped: AL party-strength overlay and loot split (more than a small item), a separate set-piece command (folded into `encounter --wave`).

## 0.7.0 (2026-11-26)
- `tt.py mystery`: each conclusion needs 2 clues (3 is safe) a typical party can find, 3+ suspects, and an opening scene that does not point only at the culprit. Idea from the Kobold Guide to Game Design (p. 158-162).
- `tt.py safety`: a cut call, a brake call, a debrief of 10+ minutes, content warnings for lines and veils, and every player confirmed (`--party`). Idea from Beyond Role and Play (the Hamlet safety report, Wieslander).
- `item`: optional `cost_axis`, `uses`, `unpredictable`, `bypasses` and `friction`; old files still pass. Idea from the Kobold Guide to Magic (p. 29-36, 59-60, 83-88).
- `tt.py table combine`: roll 2 to 4 checked tables of 6+ rows together, seeded, no repeats while the tables allow. Idea from the AEG Ultimate Toolbox (p. 353).
- 5 new tests; wording and thresholds are ours and unverified.

## 0.6.0 (2026-11-26)
- `tt.py hooks`: city hook decks (shape, district and stakes tags; two choices per plot hook; followups for framed, accused, mistaken and ambush hooks; rumours keep a separate truth; shape and colour mix). Ideas from Johnn Four, 650 City Encounters (p. 2-45) and Goodman Games, GM Gems (p. 8-9).
- `tt.py tavern`: tavern and inn cards by role (map dot, plot point, encounter, adventure), a house special, a map that fits the expected play, two-sided conflicts, hooks that say where to go, stock encounter variety and a hook per PC. Idea from the RoleplayingTips Inns, Taverns, Restaurants Design Guide (p. 13-52, 139-140).
- `tt.py venues`: taverns, restaurants and inns for a population, with `--anomaly` for a story reason. Same guide (p. 40).
- `tt.py party`: PCs tied to two others and to the main plot; every planned reveal has a fallback. Idea from Panshin, The Game Master (p. 21-24, 153-154).
- 4 new tests; wording and thresholds are ours and unverified.

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
