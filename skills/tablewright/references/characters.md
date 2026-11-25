# Characters

Load when writing, checking or rendering a character.

## Common schema (`tt.py check`)

Required: `name`, `system` (pf2e, sf2e, 5e, or any label), `level` (1 to 20), `ancestry`, `class`, `abilities` (`str dex con int wis cha` as scores, or as modifiers with `"modifiers": true` at the top), `hp`.
Optional: `ac`, `speed`, `saves` and `skills` (name to bonus), `attacks` (list of objects, printed in order), `feats`, `gear` (lists), `notes`.

A system's own engine or export (Pathbuilder JSON, Foundry actor, D&D Beyond) maps onto this schema in a small adapter script kept in the person's project, not here.

## Document set

The pattern from the Starfinder pipeline that works for any system: one `character.json` holds the mechanics, one `narrative.json` the story the model wrote, and everything else is rendered from those two: sheet, ability cards, a one-page summary for a young player, GM notes, portraits. Rerolls change the seed, edits lock every other choice. Each character gets its own folder in `TABLEWRIGHT_HOME`.

## config.json in TABLEWRIGHT_HOME

```
{"systems": {"sf2e": {"character_skill": "<path>/sf2e-character/SKILL.md", "mini_skill": "<path>/sf2e-miniature/SKILL.md"}}}
```
