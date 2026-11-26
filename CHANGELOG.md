# Changelog

## 0.11.0 (2026-11-26)
- `tt.py calendar FILE [--drift 3]`: a world-day ledger per group; prints each group's timeline and warns when split groups drift 3 or more days apart. Idea from the 1979 AD&D Dungeon Masters Guide (time keeping, pp. 37-50).
- `tt.py hirelings FILE [--roll NAME --event E --seed N]`: hireling loyalty from pay against the going rate, treatment and the leader's charisma modifier; lists the events that call for a check (unpaid, abused, sent ahead, bribe, leader down) and rolls one. Idea from the 1979 AD&D Dungeon Masters Guide (pp. 169-170).
- `tt.py district FILE`: city district cards with watch strength, bribe cost, gate and curfew rules and the block's owner; warns on missing fields and prints a one-line card each. Idea from the Lankhmar GM guide (AD&D 2e).
- `tt.py chase [--lead --escape --rounds --table --seed]`: a seeded city pursuit, opposed d6 per round plus a complication from a built-in list or the user's table, ending when caught or escaped. Idea from the Lankhmar GM guide.
- `encounter --foe 3:brute` (or `"3 role:brute"`): foe roles, a role count, and a warning when 4 or more foes all share one role. Idea from the D&D 4e Dungeon Master's Guide.
- `tt.py prep`: fights and hazards may carry `treat:` (an edge the party can find); a fight with `threat:` or `diff:` but no `timer:`/`clock:` and no treat warns. Idea from ICRPG Master Edition (Runehammer), pp. 92-93.
- `tt.py prep`: a fight rated harder than the one before, or a climax, warns when it turns fewer than two of damage, disruption (`hazard:`, `terrain:`) and duration (`timer:`, `clock:`); `levers:` names them outright. Idea from ICRPG Master Edition, pp. 94-95.
- `session-log` gains an `ending:` line (countdown, hook, choice, ran-long); `tt.py review` counts endings by kind and warns when most ran long. Idea from ICRPG Master Edition, p. 82.
- `tt.py houserules`: entries may name a `situation` (or `trigger`) and `distinguishes`; two rules for the same situation that differ with no `distinguishes` warn. Idea from Arbiter of Worlds (Alexander Macris), ch. 13, pp. 81-82.
- `tt.py prep`: fights may carry `stakes: position|assets|character|party`; all rated fights at one level warn, a climax below character warns. Idea from Arbiter of Worlds, ch. 15, pp. 90-91.
- `session-log` gains `ended_mid_fight:` and `recap:` lines; `review` warns on a mid-fight stop and on a log with no recap. Idea from Arbiter of Worlds, ch. 10, pp. 61-62.
- `tt.py attendance ROSTER --present N [--dynamic collective|competitive|individualist]`: warns at half or fewer present and says how to handle absent PCs for the group's dynamic. Idea from Arbiter of Worlds, ch. 12, p. 77.
- `tt.py trap FILE`: each trap needs a trigger, detection, disable method, effect and a severity band (setback, dangerous, deadly); mostly deadly warns. Idea from the D&D 5e Dungeon Master's Guide (2014), ch. 5, pp. 120-122. No DCs or damage numbers included.
- `tt.py downtime FILE`: each activity needs a time cost and a money cost or sink; repeatable ones need an outcomes table; warns on no hook or one that replaces adventuring. Idea from the 5e DMG, ch. 6, pp. 127-132.
- `tt.py npcs`: a card tagged `major: true` also needs `ideal:`, `bond:` and `flaw:` (or `secret:`). Idea from the 5e DMG, ch. 4, pp. 89-91.
- `tt.py item`: an entry with `reward:` (a blessing, title or favour, not an item) needs a `condition` or `expectation`. Idea from the 5e DMG, ch. 7, p. 227.
- 15 new tests; all wording, steps and numbers are ours and unverified.

## 0.10.0 (2026-11-26)
- `tt.py safety`: optional `comfort` per player and topic (none, offscreen, limited, full) and `planned` levels; each topic takes the lowest player's level and a planned level above it fails. Idea from the D&D 3.5 Advanced GM guide (Dungeon Master's Guide II era, "Sensitive Subjects"). Empty `takebacks` or `info_flow` warn; idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py battle plan.json [--results]`: a mass battle played as three representative fights, each with a shape and a carry-over for a win, and a five-step result. Idea from the D&D 3.5 Advanced GM guide.
- `tt.py tracker init --timer N` and `tracker late`: a per-turn timer that delays a player who runs out. Idea from the D&D 3.5 Advanced GM guide.
- `session-log` gains `## Highlights` and `## Weak points`; `tt.py review logs` tallies them per player. Idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py prep`: `## Players` with `for:` tags (every player gets a moment) and `likely:` triage tags, from the D&D 3.5 Dungeon Master's Guide; `diff:` tags warn on a session with no easy or no hard fight, from the D&D 4e Dungeon Master's Guide.
- `tt.py houserules rules.json`: every rule needs a why; removals want an offset. Idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py fiveroom`: a climax may carry `tiers` (minimum, middle, full); warns on fewer than three or a minimum that needs a kill. Idea from the D&D 3.5 Advanced GM guide.
- `tt.py challenge card.json`: a skill challenge (goal, successes before failures, mixed skill kinds, a failure route, a shown score) from the D&D 4e Dungeon Master's Guide, with an optional progress pool, milestones and time limit from the Fallout 2d20 GM toolkit.
- `tt.py travel`: days and fatigue for an overland trip from pace, terrain, hours and route knowledge. Idea from the Fallout 2d20 GM toolkit; multipliers are ours.
- `tt.py table`: optional `when` column (moving, camped, any); all one state warns. Idea from the Fallout 2d20 GM toolkit.
- 10 new tests; all wording, steps and multipliers are ours and unverified.
- Skipped: faction reputation ladder (`heat standing` already covers it), scavenging-site builder (low checkable value), monster-role count per fight (needs a role field on every foe; later), single-path gate check (`mystery` covers most of it), cut scenes with consent, session-log recap line, 2d10 variance note (ludowright's).

## 0.9.0 (2026-11-26)
- `tt.py strength LEVELS --target-level N [--target-size 5]`: average party level (.5 rounds up) and a five-step strength label from headcount and level against the target; fails under 3 or over 7 players. Idea from the Adventurers League DM Guide 2.0.
- `tt.py loot file.json [--seed]`: gold split evenly with the remainder named; permanent items go to the agreed PC, else the interested PC with the fewest permanent items, ties by a seeded roll; consumables do not count. Idea from the Adventurers League DM Guide 2.0.
- `tt.py reaction`: an improvised NPC's first reaction, 2d6 plus `--mod` and `--approach`, in five bands of our own. Ideas from the Lankhmar GM guide (AD&D 2e) and the 1979 AD&D Dungeon Masters Guide.
- `tt.py heat show|crime|standing|cool`: a faction ledger with standing (-3 to +3, each change needs a reason) and heat that rises by 1 plus witnesses per crime, through five escalation steps (quiet, noticed, collector, enforcers, open hunt). Idea from the Lankhmar GM guide.
- `tt.py premise card.json`: core and twist, a hook layer that is not the same premise with the same root, a finish line for pursuit, an agenda per faction for a race, a losable witness or clue for investigation; warns on defend with no faulty intel or choice and an object found incomplete. Idea from the Game Ideas collection (the Big List of RPG Plots).
- `tt.py wander`: a random-encounter clock (`--every` minutes, 1 in `--chance`, `--hours`, `--budget`), `--placed` areas, and `--run` to roll distance, surprise for each side, reaction and whether the party can evade. All numbers are ours and configurable. Idea from the 1979 AD&D Dungeon Masters Guide.
- 7 new tests; wording, bands and thresholds are ours and unverified.
- Skipped: campaign premise-rut check, premise and twist tables for `table combine`, two-plot physical/personal pairing, district cards, henchman hiring, forced march (outside the six asked for).

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
