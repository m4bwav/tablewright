---
name: tablewright
description: "Use for tabletop RPG table work in Pathfinder 2e, Starfinder 2e or D&D 5e (2024): check or build an encounter against the XP budget, run initiative and HP at the table, turn a character into a one-page sheet, and route characters, battle maps and printable minis to the right tool; tt.py runs the math. Use on 'is this fight too hard', 'build a moderate encounter for 4 level 3s', 'track initiative', 'make a character sheet', 'make a Starfinder character', 'print a mini of my character', 'battle map for this fight'. Not for video game design (ludowright) or card games (cardwright)."
---

# tablewright

Run as `python "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" <command>`. Private data (characters, which often carry players' and children's names, campaign notes, tracker files, portraits, minis) lives in `TABLEWRIGHT_HOME` (default `~/.tablewright`), never in this plugin.

## Encounters

1. Get the system, party size and party level. Foes are creature levels (pf2e, sf2e) or challenge ratings (5e).
2. `tt.py encounter --system pf2e --party 4 --level 3 --foe 5 --foe 2 --foe 2` gives total XP, threat band and what the next band needs. It exits 1 when a foe is more than 4 levels above the party. Add `--mission rescue --clock 4 --healers 1` to get warnings for a kill-only goal, a goal with no round limit, a clock outside 1 to 5 rounds, and foes that heal.
3. `tt.py budget --system 5e --party 4 --level 5 --threat moderate` gives the XP to spend and sample foe counts. Pick real creatures from the system's own books or the person's notes; tablewright ships numbers only.
4. Say what the band means at the table (PF2e: moderate is a fair fight, severe can kill a careless party; 5e 2024: high can drop a character) and suggest one change to move the band (add or remove a foe, swap a foe for one a level lower). Terrain, action economy and solo bosses matter more than the number: name them.

Tables and sources: [references/encounters.md](references/encounters.md).

## At the table

`tt.py tracker init "Hero:17:20" "Goblin:12:6"` (name:initiative:hp), then `tracker next`, `tracker hit Goblin 5`, `tracker heal Hero 4`, `tracker cond Hero "frightened 1"` (`--remove` to clear), `tracker add "Reinforcement:9:12"`, `tracker show`. Downed combatants are skipped; `+` marks who is on deck so the next player can get ready. `--public` prints the players' board for a shared screen: order, conditions and damage taken, never HP or HP max. The file is `TABLEWRIGHT_HOME/tracker.json` unless `--file` is given; one file per running fight.

To find what slows fights, log a few real ones as CSV `actor,start,end` (seconds) and run `tt.py combat-log fight.csv`: total time, GM share, median and longest turn per actor, and who runs over 90 s a turn (`--budget`, `--gm NAME`). Measure before blaming anyone.

## Session prep

Before a session, write a card in markdown with `## Opening`, `## Leads` (three bullets), `## NPCs` (`Name: what they want now`) and optional `## Fights` (each with `out: ...`, a way the fight can end before anyone dies or flees), then `tt.py prep card.md`. It exits 1 on a missing opening, the wrong number of leads (`--leads N` to change) or an NPC without a goal, and warns on a fight with no way out. Optional `## Hazards` bullets need `warned: where players learn of it`. A fight or hazard marked `lethal` needs a `tell:` (warns) and fails when also `hidden: yes`. Leads tagged `(false)` should be fewer than real ones and carry `ends: how players learn it is a dead end`. Keep the card short: prep what the table will actually touch.

For a setting, write `## Traits` with 6 to 8 bullets, each `trait: the place, NPC or faction where players meet it`, then `tt.py world card.md`; it exits 1 on too few or too many traits or a trait with no anchor. Optional sections are checked too: `## Nations` bullets need `internal:` and `external:` conflicts, `## Societies` need `leader:`, `goal:` and `rule:` (reward or punishment), `## Cities` need `theme:`, `food:`, `shelter:`, `shop:` and `twist:`.

For random tables, `tt.py table travel.csv` (columns `roll,kind,difficulty,avoidable`, rolls like `1-4`) exits 1 on rolls with no row or overlaps and warns when fights fill over 35% of the die (`--max-fight`) or an easy fight cannot be avoided. `tt.py item items.json` checks each magic item has a `drawback_tier` at least its `benefit_tier` (minor, moderate, major, legendary, campaign) and warns on campaign-changing drawbacks.

Keep a `## Threads` list of promises and planted objects (`- thing: open` or `- thing: paid`); `tt.py threads card.md` lists the open ones latest first, the usual payoff order, and `--finale` exits 1 while any is open. For NPCs, `tt.py npcs card.md` checks three-line cards under `## NPCs`: `- Name: look; doing now; hook because why`.

## Adventure structure

For a one-session site adventure, plan it as JSON areas with roles in order: entrance, puzzle, setback, climax, reward (a role is a step, not one map room). `tt.py fiveroom plan.json` exits 1 on roles out of order, not exactly one climax near the end, a puzzle with under two solutions, a setback that costs nothing, or a climax with no non-damage lever; it warns on a missing earlier clue, missing climax terrain, no twist or hook in the reward, areas 1 and 2 in the same mode, and planned minutes outside 120 to 240. Fields: `role`, `mode`, `solutions`, `clue_in` (area number), `fail_cost`, `lock_in` and `reset`, `min_players`, `cost`, `lever`, `terrain`, `immune` and `weakness`, `twist` or `hook`, `minutes`, `xp`; plan-level `party` and `fight_budget`. Puzzles warn without a `fail_cost` and fail when they lock in with no reset or need more players than the party; a climax foe `immune` with no `weakness` warns; setback plus climax `xp` over `fight_budget` warns. Hand the map to mapwright with the roles marked on its rooms; keep loops around the critical path.

## Characters

- Any system: keep a character as JSON in the common schema ([references/characters.md](references/characters.md)), `tt.py check char.json`, then `tt.py sheet char.json --out sheet.md` for a one-page sheet.
- Starfinder 2e: a full level-1 build with sheet, cards, kid summary, GM notes and pictures comes from the sf2e-character skill and its rules engine. Read its SKILL.md (path in `TABLEWRIGHT_HOME/config.json` under `systems.sf2e.character_skill`) and follow it. Mechanics come from an engine or the books, never invented.
- Writing for a child: short sentences, read-aloud friendly, keep their own words from any interview.

## Minis and maps

- Printable mini of a character: for Starfinder characters with reference pictures, the sf2e-miniature skill (`systems.sf2e.mini_skill` in config) makes the mesh, a 32 mm pawn on a 25 mm base and a print file. For anything else, polywright (generate, then polywright-print) or printable-3d-model. Details: [references/minis.md](references/minis.md).
- Battle map for an encounter: hand mapwright the setting, size in 5 ft squares (PF2e and 5e use 1 inch = 5 ft), the features that matter to the fight (cover, difficult terrain, elevation) and where each side starts.

Never post characters, names or campaign notes anywhere public; this repository is public.

## Maintenance

Evergreen unit: research in [RESEARCH.md](../../RESEARCH.md), changes in [CHANGELOG.md](../../CHANGELOG.md), lessons in [LEARNINGS.md](../../LEARNINGS.md), state in [evergreen.json](../../evergreen.json), evals in [TESTS.md](../../TESTS.md). On 'refresh tablewright', run evergreen-refresh on this unit.
