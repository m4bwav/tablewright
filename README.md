# tablewright

![tablewright banner](.github/images/banner.jpg)

Tabletop RPG table work, as a Claude Code plugin, for Pathfinder 2e, Starfinder 2e and D&D 5e (2024). It checks a planned fight against the encounter budget, runs initiative and hit points at the table, turns a character into a one-page sheet, and routes character builds, battle maps and printable miniatures to the tools that make them.

## What it does

- **Encounters**: `tt.py encounter --system pf2e --party 4 --level 3 --foe 5 --foe 2` gives total XP, the threat band and what the next band needs. `tt.py budget --system 5e --party 4 --level 5 --threat high` gives the XP to spend and sample foe counts.
- **Tracker**: `tt.py tracker init "Hero:17:20" "Goblin:12:6"`, then `next`, `hit`, `heal`, `cond`, `add`, `show`. Downed combatants are skipped.
- **Sheets**: `tt.py check char.json` and `tt.py sheet char.json --out sheet.md` from a simple common character schema.
- **Prep checks**: `tt.py prep`, `world`, `npcs`, `threads`, `fiveroom`, `villain`, `twist`, `campaign`, `hooks`, `tavern`, `venues`, `party`, `item`, `table` (and `table combine A.csv B.csv --seed N --count K`), `mystery` (clues per conclusion, suspects) and `safety` (cut and brake calls, debrief, confirmations), plus `calendar`, `hirelings`, `district`, `chase`, `attendance`, `trap` and `downtime` (0.11.0). Each exits 1 on a problem and prints `warn:` lines for softer ones.
- **Licences**: `tt.py licence`. tablewright ships numbers only: PF2e and SF2e encounter tables from Pathfinder GM Core and Starfinder GM Core under the [ORC License](https://paizo.com/orclicense), D&D 2024 tables from [SRD 5.2.1](https://www.dndbeyond.com/srd) under CC-BY-4.0, with the required attribution in `tt.py licence` (checked 2026-11-25).

Your characters and campaign notes live in `TABLEWRIGHT_HOME` (default `~/.tablewright`), outside the plugin. Needs only Python 3.9+.

## Install

```
/plugin marketplace add m4bwav/tablewright
/plugin install tablewright
```

## Develop

`python -m pytest -q`. Rules: [AGENTS.md](AGENTS.md).

## Licence

MIT for the code. Rules tables: see `tt.py licence`.
