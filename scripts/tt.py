#!/usr/bin/env python3
"""tablewright CLI: tabletop RPG table work, standard library only.

Commands:
  encounter   XP total and threat band of a planned fight (pf2e, sf2e, 5e)
  budget      XP to spend for a threat, with example foe mixes
  tracker     initiative and HP tracker kept in a JSON file
  sheet       character JSON (common schema) to a one-page markdown sheet
  check       check a character JSON against the common schema
  prep        check a session prep card (opening, leads, NPC goals, fight exits)
  combat-log  turn times of a real fight, flags players over 90 s a turn
  threads     story promises still open, latest first; --finale fails on any open
  npcs        check three-line NPC cards (look; doing now; hook because why)
  world       check a setting card (6 to 8 traits, each anchored)
  fiveroom    check an adventure plan against the five-role arc
  licence     notices for the bundled rules tables

Exit 2 is a usage or validation error.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Pathfinder 2e and Starfinder 2e (ORC): creature XP by level minus party level, budgets for 4 players.
PF_XP = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120, 4: 160}
PF_BUDGET = {"trivial": 40, "low": 60, "moderate": 80, "severe": 120, "extreme": 160}
PF_ADJUST = {"trivial": 10, "low": 20, "moderate": 20, "severe": 30, "extreme": 40}

# D&D 5e 2024 (SRD 5.2.1, CC-BY-4.0): XP budget per character by level, and XP by challenge rating.
DND_BUDGET = {
    1: (50, 75, 100), 2: (100, 150, 200), 3: (150, 225, 400), 4: (250, 375, 500), 5: (500, 750, 1100),
    6: (600, 1000, 1400), 7: (750, 1300, 1700), 8: (1000, 1700, 2100), 9: (1300, 2000, 2600),
    10: (1600, 2300, 3100), 11: (1900, 2900, 4100), 12: (2200, 3700, 4700), 13: (2600, 4200, 5400),
    14: (2900, 4900, 6200), 15: (3300, 5400, 7800), 16: (3800, 6100, 9800), 17: (4500, 7200, 11700),
    18: (5000, 8700, 14200), 19: (5500, 10700, 17200), 20: (6400, 13200, 22000),
}
DND_BANDS = ("low", "moderate", "high")
CR_XP = {"0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
         "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400, "13": 10000,
         "14": 11500, "15": 13000, "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
         "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000, "26": 90000, "27": 105000,
         "28": 120000, "29": 135000, "30": 155000}

LICENCE = """Pathfinder 2e and Starfinder 2e encounter tables (XP budget, character adjustment, creature XP):
game mechanics under the ORC License (https://paizo.com/orclicense, text by Azora Law).
ORC Notice / attribution: this product is based on the following Licensed Material:
Pathfinder GM Core, (c) 2023 Paizo Inc.; Starfinder GM Core, (c) Paizo Inc.
(encounter building rules; https://2e.aonprd.com/Rules.aspx?ID=2716, https://2e.aonsrd.com/rules/793-xp-budget).
D&D 2024 encounter tables: This work includes material taken from the System Reference Document 5.2.1
("SRD 5.2.1") by Wizards of the Coast LLC and available at https://www.dndbeyond.com/srd.
The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License (CC-BY-4.0)
available at https://creativecommons.org/licenses/by/4.0/legalcode.
tablewright bundles numbers only, no rules text, creatures or art. Sources checked 2026-11-25."""

SCHEMA_REQUIRED = ["name", "system", "level", "ancestry", "class", "abilities", "hp"]
ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(2)


def pf_budgets(party):
    return {k: v + (party - 4) * PF_ADJUST[k] for k, v in PF_BUDGET.items()}


def dnd_budgets(party, level):
    if level not in DND_BUDGET:
        die("5e level must be 1 to 20")
    return {b: x * party for b, x in zip(DND_BANDS, DND_BUDGET[level])}


def foe_xp(system, foe, level):
    if system in ("pf2e", "sf2e"):
        try:
            d = int(foe) - level
        except ValueError:
            die(f"foe level must be a number: {foe}")
        if d < -4:
            return 0, "too weak to count"
        if d > 4:
            return None, "more than 4 levels above the party: do not use"
        return PF_XP[d], ""
    foe = {"0.125": "1/8", "0.25": "1/4", "0.5": "1/2", ".125": "1/8", ".25": "1/4", ".5": "1/2"}.get(foe, foe)
    if foe not in CR_XP:
        die(f"unknown challenge rating: {foe} (use 0, 1/8, 1/4, 1/2, 1..30)")
    return CR_XP[foe], ""


def band_for(total, budgets):
    name = None
    for k, v in sorted(budgets.items(), key=lambda kv: kv[1]):
        if total >= v:
            name = k
    return name or "below " + min(budgets, key=budgets.get)


def cmd_encounter(a):
    budgets = pf_budgets(a.party) if a.system != "5e" else dnd_budgets(a.party, a.level)
    total, notes = 0, []
    for f in a.foe:
        xp, note = foe_xp(a.system, f, a.level)
        if xp is None:
            notes.append(f"foe {f}: {note}")
            continue
        total += xp
        if note:
            notes.append(f"foe {f}: {note}")
    band = band_for(total, budgets)
    nxt = [(k, v) for k, v in sorted(budgets.items(), key=lambda kv: kv[1]) if v > total]
    res = {"system": a.system, "party": a.party, "level": a.level, "xp": total, "threat": band,
           "budgets": budgets, "next": {"threat": nxt[0][0], "xp_needed": nxt[0][1] - total} if nxt else None, "notes": notes}
    if a.system == "5e" and total > budgets["high"]:
        res["notes"].append("above the High budget (2024 has no higher band): expect a character to drop")
    if a.system != "5e" and total > budgets["extreme"]:
        res["notes"].append("over the Extreme budget")
    res["warnings"] = mission_warnings(a)
    bad = any("do not use" in n for n in notes)
    if a.json:
        print(json.dumps(res, indent=2))
        sys.exit(1 if bad else 0)
    print(f"{a.system} party of {a.party} at level {a.level}: {total} XP, threat {band}")
    print("budgets: " + ", ".join(f"{k} {v}" for k, v in budgets.items()))
    if res["next"]:
        print(f"next band: {res['next']['threat']} needs {res['next']['xp_needed']} XP more")
    for n in res["notes"]:
        print("note: " + n)
    for w in res["warnings"]:
        print("warn: " + w)
    sys.exit(1 if bad else 0)


def mission_warnings(a):
    """Warnings for a fight that is only a damage race (no goal, no clock, foes that undo damage)."""
    w = []
    if a.mission is None:
        return w
    if a.mission == "kill":
        w.append("kill-only mission: add a goal besides killing (rescue, hold, escape, steal, stop a ritual)")
    elif a.clock is None:
        w.append(f"{a.mission} mission has no clock: give it a round limit (--clock N)")
    if a.clock is not None and not 1 <= a.clock <= 5:
        w.append(f"clock of {a.clock} rounds; 1 to 5 keeps pressure on")
    if a.healers:
        w.append(f"{a.healers} foe(s) heal or grant temp HP: fights drag; cap it or make the healer a target")
    return w


def cmd_budget(a):
    if a.system == "5e":
        budgets = dnd_budgets(a.party, a.level)
        if a.threat not in budgets:
            die("5e threats: low, moderate, high")
        xp = budgets[a.threat]
        mixes = []
        for cr, v in sorted(CR_XP.items(), key=lambda kv: kv[1]):
            n = xp // v
            if 1 <= n <= 8:
                mixes.append(f"{n} x CR {cr} ({n * v} XP)")
        mixes = mixes[-4:]
    else:
        budgets = pf_budgets(a.party)
        if a.threat not in budgets:
            die("pf2e/sf2e threats: trivial, low, moderate, severe, extreme")
        xp = budgets[a.threat]
        mixes = []
        for d in range(4, -5, -1):
            v = PF_XP[d]
            n = xp // v
            if 1 <= n <= 8:
                mixes.append(f"{n} x level {a.level + d} ({n * v} XP)")
        mixes = mixes[:4]
    if a.json:
        print(json.dumps({"xp": xp, "mixes": mixes}, indent=2))
        return
    print(f"{a.threat} for {a.party} at level {a.level}: {xp} XP")
    for m in mixes:
        print("  " + m)


# ---------- tracker ----------

def tload(p):
    if not p.exists():
        die(f"no tracker at {p}; start one with: tracker init")
    return json.loads(p.read_text(encoding="utf-8"))


def tsave(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def find(d, name):
    for c in d["order"]:
        if c["name"].lower() == name.lower():
            return c
    die(f"no combatant named {name}")


def show(d, public=False):
    """Print the order. public: the players' board, damage taken but never HP or HP max."""
    print(f"round {d['round']}")
    up = [i for i, c in enumerate(d["order"]) if c["hp"] > 0 and i != d["turn"]]
    deck = next((i for i in up if i > d["turn"]), up[0] if up else None)
    for i, c in enumerate(d["order"]):
        mark = ">" if i == d["turn"] else ("+" if i == deck else " ")
        conds = (" [" + ", ".join(c["conditions"]) + "]") if c["conditions"] else ""
        state = " DOWN" if c["hp"] <= 0 else ""
        hp = f"took {c['max_hp'] - c['hp']}" if public else f"{c['hp']}/{c['max_hp']}"
        print(f"{mark} {c['init']:>3} {c['name']:<16} {hp}{state}{conds}")


def cmd_tracker(a):
    p = Path(a.file)
    if a.action == "init":
        order = []
        for spec in a.args:
            parts = spec.split(":")
            if len(parts) != 3:
                die(f"combatant as name:initiative:hp, got {spec}")
            try:
                order.append({"name": parts[0], "init": int(parts[1]), "hp": int(parts[2]), "max_hp": int(parts[2]), "conditions": []})
            except ValueError:
                die(f"initiative and hp must be numbers: {spec}")
        if len({c["name"].lower() for c in order}) != len(order):
            die("combatant names must be unique")
        order.sort(key=lambda c: -c["init"])
        d = {"round": 1, "turn": 0, "order": order, "log": []}
    else:
        d = tload(p)
        if a.action in ("hit", "heal"):
            if len(a.args) != 2:
                die(f"{a.action} NAME AMOUNT")
            c = find(d, a.args[0])
            n = int(a.args[1])
            c["hp"] = max(0, c["hp"] - n) if a.action == "hit" else min(c["max_hp"], c["hp"] + n)
            d["log"].append(f"r{d['round']} {c['name']} {a.action} {n} -> {c['hp']}")
        elif a.action == "next":
            alive = [i for i, c in enumerate(d["order"]) if c["hp"] > 0]
            if not alive:
                die("everyone is down")
            i = d["turn"]
            while True:
                i += 1
                if i >= len(d["order"]):
                    i, d["round"] = 0, d["round"] + 1
                if d["order"][i]["hp"] > 0:
                    break
            d["turn"] = i
        elif a.action == "cond":
            if len(a.args) < 2:
                die("cond NAME CONDITION [--remove]")
            c = find(d, a.args[0])
            cond = " ".join(a.args[1:])
            if a.remove:
                c["conditions"] = [x for x in c["conditions"] if x != cond]
            elif cond not in c["conditions"]:
                c["conditions"].append(cond)
        elif a.action == "add":
            if len(a.args) != 1 or len(a.args[0].split(":")) != 3:
                die("add name:initiative:hp")
            n, i, h = a.args[0].split(":")
            cur = d["order"][d["turn"]]
            d["order"].append({"name": n, "init": int(i), "hp": int(h), "max_hp": int(h), "conditions": []})
            d["order"].sort(key=lambda c: -c["init"])
            d["turn"] = d["order"].index(cur)
    if a.action != "show":
        tsave(p, d)
    show(d, a.public)


def cmd_combatlog(a):
    """Time a real fight: CSV rows actor,start,end in seconds (round,actor,start,end also works)."""
    import csv, statistics
    turns = {}
    rows = list(csv.reader(Path(a.log).read_text(encoding="utf-8").splitlines()))
    rows = [r for r in rows if r and not r[0].strip().lower() in ("actor", "round")]
    if not rows:
        die("no turns in log")
    for r in rows:
        try:
            actor, start, end = r[-3].strip(), float(r[-2]), float(r[-1])
        except (ValueError, IndexError):
            die(f"row as actor,start,end: {','.join(r)}")
        turns.setdefault(actor, []).append(end - start)
    total = max(float(r[-1]) for r in rows) - min(float(r[-2]) for r in rows)
    gm = sum(turns.get(a.gm, []))
    print(f"fight {total / 60:.1f} min, {sum(map(len, turns.values()))} turns, GM share {gm / total:.0%}" if total else "fight 0 min")
    slow = []
    for actor, ts in sorted(turns.items(), key=lambda kv: -statistics.median(kv[1])):
        med = statistics.median(ts)
        flag = " SLOW" if med > a.budget and actor != a.gm else ""
        if flag:
            slow.append(actor)
        print(f"  {actor:<16} median {med:>5.0f}s  longest {max(ts):>5.0f}s  turns {len(ts)}{flag}")
    if slow:
        print(f"over {a.budget:.0f}s a turn: {', '.join(slow)}")


# ---------- character ----------

def check_char(c):
    errs = [f"missing {k}" for k in SCHEMA_REQUIRED if k not in c]
    ab = c.get("abilities", {})
    if isinstance(ab, dict):
        errs += [f"abilities missing {k}" for k in ABILITIES if k not in ab]
        errs += [f"ability {k} is not a number" for k, v in ab.items() if not isinstance(v, (int, float))]
    else:
        errs.append("abilities must be an object")
    if "level" in c and not (isinstance(c["level"], int) and 1 <= c["level"] <= 20):
        errs.append("level must be 1 to 20")
    return errs


def load_char(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"{path}: {e}")


def cmd_check(a):
    errs = check_char(load_char(a.character))
    for e in errs:
        print("error: " + e)
    print("ok" if not errs else f"{len(errs)} problem(s)")
    sys.exit(1 if errs else 0)


def mod(c, k):
    v = c["abilities"][k]
    return v if c.get("modifiers") else (v - 10) // 2


def cmd_sheet(a):
    c = load_char(a.character)
    errs = check_char(c)
    if errs:
        die("; ".join(errs))
    L = [f"# {c['name']}", f"Level {c['level']} {c['ancestry']} {c['class']} ({c['system']})", ""]
    L.append("| " + " | ".join(k.upper() for k in ABILITIES) + " |")
    L.append("|" + "---|" * len(ABILITIES))
    L.append("| " + " | ".join(f"{mod(c, k):+d}" for k in ABILITIES) + " |")
    L += ["", f"**HP** {c['hp']}" + (f"  **AC** {c['ac']}" if "ac" in c else "") + (f"  **Speed** {c['speed']}" if "speed" in c else "")]
    for key, head in (("saves", "Saves"), ("skills", "Skills")):
        if c.get(key):
            L += ["", f"## {head}", ", ".join(f"{k} {v:+d}" if isinstance(v, int) else f"{k} {v}" for k, v in c[key].items())]
    for key, head in (("attacks", "Attacks"), ("feats", "Feats and abilities"), ("gear", "Gear")):
        if c.get(key):
            L += ["", f"## {head}"]
            for x in c[key]:
                if isinstance(x, dict):
                    L.append("- " + " ".join(str(v) for v in x.values()))
                else:
                    L.append(f"- {x}")
    if c.get("notes"):
        L += ["", "## Notes", c["notes"]]
    md = "\n".join(L) + "\n"
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(md)


def prep_sections(text):
    sec, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip().lower()
            sec[cur] = []
        elif cur is not None and line.strip():
            sec[cur].append(line.strip())
    return sec


def cmd_prep(a):
    """Check a session card: an opening, N leads, NPCs that each want something, fights with a way out."""
    sec = prep_sections(Path(a.card).read_text(encoding="utf-8"))
    bullets = lambda k: [l[2:].strip() for l in sec.get(k, []) if l[:2] in ("- ", "* ")]
    errs, warns = [], []
    if not sec.get("opening"):
        errs.append("no ## Opening: write how the session starts")
    leads = bullets("leads")
    if len(leads) != a.leads:
        errs.append(f"## Leads has {len(leads)}, want {a.leads}: enough for a real choice, few enough to prep")
    npcs = bullets("npcs")
    if not npcs:
        errs.append("no ## NPCs bullets")
    for n in npcs:
        if ":" not in n or not n.split(":", 1)[1].strip():
            errs.append(f"NPC without a goal (write 'Name: what they want now'): {n}")
    for f in bullets("fights"):
        if "out:" not in f.lower():
            warns.append(f"fight without a way to end early (add 'out: ...'): {f}")
    for h in bullets("hazards"):
        if "warned:" not in h.lower():
            errs.append(f"hazard with no warning before players can prepare (add 'warned: where they learn of it'): {h}")
    for x in bullets("fights") + bullets("hazards"):
        lx = x.lower()
        if "lethal" in lx and "hidden: yes" in lx:
            errs.append(f"lethal and hidden: players get no fair chance; make it visible or weaker: {x}")
        elif "lethal" in lx and "tell:" not in lx and "warned:" not in lx:
            warns.append(f"lethal threat with no tell (add 'tell: the sign players can notice'): {x}")
    false = [l for l in leads if "(false)" in l.lower()]
    if false and len(false) >= len(leads) - len(false):
        warns.append(f"{len(false)} false leads of {len(leads)}; keep them fewer than the real ones")
    for l in false:
        if "ends:" not in l.lower():
            warns.append(f"false lead with no ending (add 'ends: how players learn it is a dead end'): {l}")
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print(f"ok: opening, {len(leads)} leads, {len(npcs)} NPCs with goals")


def cmd_world(a):
    """Check a setting card: 6 to 8 traits, each tied to a place, NPC or faction the players can meet."""
    sec = prep_sections(Path(a.card).read_text(encoding="utf-8"))
    traits = [l[2:].strip() for l in sec.get("traits", []) if l[:2] in ("- ", "* ")]
    errs = []
    if not 6 <= len(traits) <= 8:
        errs.append(f"## Traits has {len(traits)}, want 6 to 8: enough to feel distinct, few enough to remember")
    for t in traits:
        if ":" not in t or not t.split(":", 1)[1].strip():
            errs.append(f"trait not tied to a place, NPC or faction (write 'trait: where it shows'): {t}")
    for k, one, need, why in (
            ("nations", "nation", ("internal:", "external:"), "a conflict inside and one with a neighbour"),
            ("societies", "society", ("leader:", "goal:", "rule:"), "a leader, a goal now and a reward or punishment rule"),
            ("cities", "city", ("theme:", "food:", "shelter:", "shop:", "twist:"),
             "one theme, a standout food, shelter and shop, and an unwelcome twist")):
        for x in (l[2:].strip() for l in sec.get(k, []) if l[:2] in ("- ", "* ")):
            miss = [n.rstrip(":") for n in need if n not in x.lower()]
            if miss:
                errs.append(f"{one} missing {', '.join(miss)} (wants {why}): {x.split(':', 1)[0]}")
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print(f"ok: {len(traits)} traits, each with an anchor")


def cmd_threads(a):
    """Promises and planted objects: '- thread: open' or '- thread: paid'. --finale fails on any still open."""
    sec = prep_sections(Path(a.card).read_text(encoding="utf-8"))
    th = [l[2:].strip() for l in sec.get("threads", []) if l[:2] in ("- ", "* ")]
    if not th:
        die("no ## Threads bullets")
    opened = [t.rsplit(":", 1)[0].strip() for t in th if t.rsplit(":", 1)[-1].strip().lower() != "paid"]
    print(f"{len(th) - len(opened)} paid, {len(opened)} open")
    if opened:
        # Bring threads back roughly in reverse order: the latest promise pays off first.
        print("pay off next (latest first): " + "; ".join(reversed(opened)))
    if a.finale and opened:
        print(f"error: finale with {len(opened)} open promise(s); pay them off or drop them on purpose")
        sys.exit(1)


def cmd_npcs(a):
    """Three-line NPC cards: '- Name: look; doing now; hook because why'."""
    sec = prep_sections(Path(a.card).read_text(encoding="utf-8"))
    npcs = [l[2:].strip() for l in sec.get("npcs", []) if l[:2] in ("- ", "* ")]
    if not npcs:
        die("no ## NPCs bullets")
    errs = []
    for n in npcs:
        name, _, rest = n.partition(":")
        parts = [x.strip() for x in rest.split(";")]
        if len(parts) != 3 or not all(parts):
            errs.append(f"{name.strip()}: want three parts 'look; doing now; hook because why'")
        elif "because" not in parts[2].lower():
            errs.append(f"{name.strip()}: hook has no why (add 'because ...')")
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print(f"ok: {len(npcs)} NPCs, each with look, activity and a hook with a why")


FIVE = ["entrance", "puzzle", "setback", "climax", "reward"]


def cmd_fiveroom(a):
    """Check an adventure plan against the five-role arc (entrance, puzzle, setback, climax, reward)."""
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    areas, party = plan.get("areas", []), plan.get("party")
    errs, warns = [], []
    roles = [x.get("role") for x in areas]
    if not 3 <= len(areas) <= 10:
        errs.append(f"{len(areas)} areas, want 3 to 10")
    elif not 4 <= len(areas) <= 6:
        warns.append(f"{len(areas)} areas; 4 to 6 fits one session")
    bad = [r for r in roles if r not in FIVE]
    if bad:
        errs.append(f"unknown roles {bad}; use {FIVE}")
    order = [FIVE.index(r) for r in roles if r in FIVE]
    if order != sorted(order):
        errs.append("roles out of order: " + " > ".join(map(str, roles)))
    if roles.count("climax") != 1:
        errs.append(f"{roles.count('climax')} climax areas, want exactly 1")
    elif roles.index("climax") < len(roles) - 2:
        errs.append("climax is not at or next to the end")
    for i, x in enumerate(areas):
        n, r = i + 1, x.get("role")
        if r == "puzzle":
            if len(x.get("solutions", [])) < 2:
                errs.append(f"area {n}: puzzle needs at least 2 solutions")
            if not x.get("fail_cost"):
                warns.append(f"area {n}: puzzle has no fail_cost (what a wrong answer costs)")
            if x.get("lock_in") and not x.get("reset"):
                errs.append(f"area {n}: puzzle locks in with no reset; a stuck party cannot recover")
            mp = x.get("min_players")
            if mp and party and mp > party:
                errs.append(f"area {n}: needs {mp} players, party has {party}")
            c = x.get("clue_in")
            if not isinstance(c, int) or not 1 <= c < n:
                warns.append(f"area {n}: no clue planted in an earlier area (clue_in)")
        if r == "setback" and not x.get("cost"):
            errs.append(f"area {n}: setback costs nothing (name a cost)")
        if r == "climax":
            if not x.get("lever"):
                errs.append(f"area {n}: climax needs a lever that is not damage")
            if not x.get("terrain"):
                warns.append(f"area {n}: climax has no terrain that matters")
            if x.get("immune") and not x.get("weakness"):
                warns.append(f"area {n}: climax foe is immune ({x['immune']}) with no weakness to find in the room")
        if r == "reward" and not (x.get("twist") or x.get("hook")):
            warns.append(f"area {n}: reward has no twist or next hook")
    if len(areas) > 1 and areas[0].get("mode") and areas[0].get("mode") == areas[1].get("mode"):
        warns.append("areas 1 and 2 use the same mode; vary them (fight, talk, explore, puzzle)")
    plan_budget = plan.get("fight_budget")
    hard = sum(x.get("xp", 0) for x in areas if x.get("role") in ("setback", "climax"))
    if plan_budget and hard > plan_budget:
        warns.append(f"setback and climax fights total {hard} XP, over one fight's budget of {plan_budget}; "
                     "the party meets them without a full rest")
    mins = sum(x.get("minutes", 0) for x in areas)
    if mins and not 120 <= mins <= 240:
        warns.append(f"{mins} minutes planned; one session is about 120 to 240")
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print(f"ok: {len(areas)} areas in five-role order")


TIERS = ["minor", "moderate", "major", "legendary", "campaign"]
YES = ("yes", "y", "true", "1")


def roll_range(r):
    lo, _, hi = r["roll"].strip().partition("-")
    return int(lo), int(hi or lo)


def cmd_table(a):
    """Check a random encounter table CSV (roll,kind,difficulty,avoidable): gaps, fight share, unavoidable easy fights."""
    with open(a.table, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    errs, warns, covered, fights = [], [], set(), 0
    for r in rows:
        lo, hi = roll_range(r)
        span = set(range(lo, hi + 1))
        if covered & span:
            errs.append(f"roll {r['roll']} overlaps another row")
        covered |= span
        kind = r["kind"].strip().lower()
        if kind == "fight":
            fights += len(span)
            if r.get("difficulty", "").strip().lower() in ("trivial", "easy", "low") and r.get("avoidable", "").strip().lower() not in YES:
                warns.append(f"roll {r['roll']}: easy fight the party cannot avoid (a speed bump; make it avoidable)")
    top = max(covered) if covered else 0
    gaps = sorted(set(range(1, top + 1)) - covered)
    if gaps:
        errs.append(f"rolls with no row: {gaps[:10]}{' ...' if len(gaps) > 10 else ''}")
    share = fights / top if top else 0
    if share > a.max_fight:
        warns.append(f"fights fill {share:.0%} of the table, over {a.max_fight:.0%}; travel should be mostly other things")
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print(f"ok: d{top} table, {len(rows)} rows, fights {share:.0%}")


def cmd_item(a):
    """Check magic items (JSON list) for a drawback at least as strong as the boon."""
    items = json.loads(Path(a.items).read_text(encoding="utf-8"))
    errs, warns = [], []
    for it in items if isinstance(items, list) else [items]:
        n, b, d = it.get("name", "?"), it.get("benefit_tier"), it.get("drawback_tier")
        if b not in TIERS:
            errs.append(f"{n}: benefit_tier must be one of {TIERS}")
        elif not d:
            errs.append(f"{n}: no drawback")
        elif d not in TIERS:
            errs.append(f"{n}: drawback_tier must be one of {TIERS}")
        elif TIERS.index(d) < TIERS.index(b):
            errs.append(f"{n}: {d} drawback under a {b} boon; random items inflate power")
        elif d == "campaign":
            warns.append(f"{n}: drawback changes the campaign; confirm you will run it and the players agree")
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print("ok: every boon has a matching drawback")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tt.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("encounter", cmd_encounter), ("budget", cmd_budget)):
        s = sub.add_parser(name)
        s.add_argument("--system", choices=["pf2e", "sf2e", "5e"], required=True)
        s.add_argument("--party", type=int, default=4)
        s.add_argument("--level", type=int, required=True)
        if name == "encounter":
            s.add_argument("--foe", action="append", required=True, help="creature level (pf2e/sf2e) or CR (5e); repeat per foe")
            s.add_argument("--mission", help="what the party must do: kill, rescue, hold, escape, steal, ritual...")
            s.add_argument("--clock", type=int, help="rounds before the mission fails")
            s.add_argument("--healers", type=int, default=0, help="foes that heal or grant temp HP")
        else:
            s.add_argument("--threat", default="moderate")
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=fn)
    t = sub.add_parser("tracker", help="initiative and HP tracker")
    t.add_argument("action", choices=["init", "add", "hit", "heal", "next", "cond", "show"])
    t.add_argument("args", nargs="*")
    t.add_argument("--file", default=str(Path(os.environ.get("TABLEWRIGHT_HOME") or Path.home() / ".tablewright") / "tracker.json"))
    t.add_argument("--remove", action="store_true")
    t.add_argument("--public", action="store_true", help="players' board: damage taken, no HP")
    t.set_defaults(fn=cmd_tracker)
    s = sub.add_parser("sheet", help="character JSON to markdown sheet")
    s.add_argument("character"); s.add_argument("--out"); s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("check", help="check a character JSON")
    s.add_argument("character"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("prep", help="check a session prep card")
    s.add_argument("card"); s.add_argument("--leads", type=int, default=3); s.set_defaults(fn=cmd_prep)
    s = sub.add_parser("combat-log", help="turn times of a real fight from a CSV log")
    s.add_argument("log"); s.add_argument("--budget", type=float, default=90); s.add_argument("--gm", default="GM")
    s.set_defaults(fn=cmd_combatlog)
    s = sub.add_parser("threads", help="open and paid story promises")
    s.add_argument("card"); s.add_argument("--finale", action="store_true"); s.set_defaults(fn=cmd_threads)
    s = sub.add_parser("npcs", help="check three-line NPC cards")
    s.add_argument("card"); s.set_defaults(fn=cmd_npcs)
    s = sub.add_parser("world", help="check a setting card's traits")
    s.add_argument("card"); s.set_defaults(fn=cmd_world)
    s = sub.add_parser("fiveroom", help="check an adventure plan against the five-role arc")
    s.add_argument("plan"); s.set_defaults(fn=cmd_fiveroom)
    s = sub.add_parser("table", help="check a random encounter table CSV")
    s.add_argument("table"); s.add_argument("--max-fight", type=float, default=0.35); s.set_defaults(fn=cmd_table)
    s = sub.add_parser("item", help="check magic items pair each boon with a drawback")
    s.add_argument("items"); s.set_defaults(fn=cmd_item)
    s = sub.add_parser("licence", help="notices for the bundled tables")
    s.set_defaults(fn=lambda a: print(LICENCE))
    a = p.parse_args(argv)
    if getattr(a, "party", 1) < 1:
        die("party must be at least 1")
    a.fn(a)


if __name__ == "__main__":
    main()
