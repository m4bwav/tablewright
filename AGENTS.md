# AGENTS.md

Rules for any AI agent working in this repository. `CLAUDE.md` imports this file; `.github/copilot-instructions.md` points here.

## What this is

tablewright: one hub skill, `skills/tablewright/`. `scripts/tt.py` is the CLI (standard library only), `skills/tablewright/references/` holds encounter math, the character schema and mini notes (load one when a step needs it), `evals/` the eval suite, `ai-docs/` the notes and handoff (start with `ai-docs/HANDOFF.md`).

## Rules

- Public repository: no personal data. Characters, players' and children's names, campaign notes and minis live in `TABLEWRIGHT_HOME`. Fixtures use made-up characters. Run a leak check before every push.
- Bundle rules numbers only, with their licence notice (`tt.py licence`): no rules text, creatures or art from any book or site.
- Python 3.9+, standard library only. UTF-8, LF. Exit 2 is a usage or validation error.
- Every change gets a test: `python -m pytest -q`.
- Evergreen unit at the root: read `evergreen.json` before editing; changes go in CHANGELOG with the reason, lessons in LEARNINGS.
- A release bumps `.claude-plugin/plugin.json` and CHANGELOG together.
- Plain short sentences, no em dashes, relative links. No AI attribution anywhere.

## Commands

- Tests: `python -m pytest -q`
- Encounters: `python scripts/tt.py encounter|budget --system pf2e|sf2e|5e ...`
- Table: `tt.py tracker init|add|hit|heal|next|cond|show`
- Characters: `tt.py check|sheet char.json`

## everlast (session knowledge, load on demand)

- `ai-docs/INDEX.md` lists what past sessions learned here (solutions with verified commands, decisions with reasons, plans). At the start of a task, scan it and open only the entries whose title or tags match; no line matches: `everlast.py search "<key terms>"` before concluding nothing was recorded. Read `ai-docs/HANDOFF.md` when continuing unfinished work (everlast-resume skill).
- Before acting on an entry marked `(recheck due)`, run `everlast.py recheck <entry>`, re-run its Verified-by command only when that is read-only or safe (a build, a test, a version query), then record `everlast.py verify <entry>` or `verify <entry> --failed "what broke"`; a fix that changed is superseded, never reused blindly. When an entry, or this file, disagrees with the code, follow the code, name each mismatch in your reply, and record `verify --failed` on the entry.
- Before finishing a task that hit a dead end, verified a non-obvious command, made a design choice, or taught you something about the user, record it (everlast-capture skill, or `everlast.py note` / `handoff`); rewrite `HANDOFF.md` when work is left unfinished. Say "nothing to record" when that is true.
- Anything naming a person, an internal host or name, a credential, or an opinion about people goes to the private sidecar (`--private`), never here. Lessons about the user or this machine go to the user tier (`--user`).
- Rules go in this file, system layout in CODEMAP.md; the doc set holds only what could not be re-derived from the code in a minute.
- Link documents together with relative markdown links: every markdown folder is reachable from an index whose lines say when to read each file (`ai-docs/INDEX.md` is generated from frontmatter; give entries a one-line `summary`), and an entry links the entries it relates to on a typed `Related:` line (`supersedes`, `contradicts`, `builds on`, `see also`). The set then reads as a graph for people in Obsidian and for agents alike. No wikilinks in the repo.
