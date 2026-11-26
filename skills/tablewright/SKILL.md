---
name: tablewright
description: "Use for tabletop RPG table work in Pathfinder 2e, Starfinder 2e or D&D 5e (2024): check or build an encounter against the XP budget, run initiative and HP at the table, turn a character into a one-page sheet, and route characters, battle maps and printable minis to the right tool; tt.py runs the math. Use on 'is this fight too hard', 'build a moderate encounter for 4 level 3s', 'track initiative', 'make a character sheet', 'make a Starfinder character', 'print a mini of my character', 'battle map for this fight'. Not for video game design (ludowright) or card games (cardwright)."
---

# tablewright

Run as `python "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" <command>`. Private data (characters, which often carry players' and children's names, campaign notes, tracker files, portraits, minis) lives in `TABLEWRIGHT_HOME` (default `~/.tablewright`), never in this plugin.

## Encounters

1. Get the system, party size and party level. Foes are creature levels (pf2e, sf2e) or challenge ratings (5e).
2. `tt.py encounter --system pf2e --party 4 --level 3 --foe 5 --foe 2 --foe 2` gives total XP, threat band and what the next band needs. It exits 1 when a foe is more than 4 levels above the party.
3. `tt.py budget --system 5e --party 4 --level 5 --threat moderate` gives the XP to spend and sample foe counts. Pick real creatures from the system's own books or the person's notes; tablewright ships numbers only.
4. Say what the band means at the table (PF2e: moderate is a fair fight, severe can kill a careless party; 5e 2024: high can drop a character) and suggest one change to move the band (add or remove a foe, swap a foe for one a level lower). Terrain, action economy and solo bosses matter more than the number: name them.

Tables and sources: [references/encounters.md](references/encounters.md).

## At the table

`tt.py tracker init "Hero:17:20" "Goblin:12:6"` (name:initiative:hp), then `tracker next`, `tracker hit Goblin 5`, `tracker heal Hero 4`, `tracker cond Hero "frightened 1"` (`--remove` to clear), `tracker add "Reinforcement:9:12"`, `tracker show`. Downed combatants are skipped. The file is `TABLEWRIGHT_HOME/tracker.json` unless `--file` is given; one file per running fight.

## Session prep

Before a session, write a card in markdown with `## Opening`, `## Leads` (three bullets), `## NPCs` (`Name: what they want now`) and optional `## Fights` (each with `out: ...`, a way the fight can end before anyone dies or flees), then `tt.py prep card.md`. It exits 1 on a missing opening, the wrong number of leads (`--leads N` to change) or an NPC without a goal, and warns on a fight with no way out. Keep the card short: prep what the table will actually touch.

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
