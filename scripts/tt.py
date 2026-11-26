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
  session-log print a session log template (its threads feed 'threads')
  npcs        check three-line NPC cards (look; doing now; hook because why)
  world       check a setting card (6 to 8 traits, each anchored)
  fiveroom    check an adventure plan against the five-role arc
  table       check a roll table CSV; 'table combine A B' rolls tables together
  item        check magic items (drawback, cost axis, uses, friction)
  mystery     check a mystery's clues per conclusion and its suspects
  safety      check a table safety plan (cut and brake calls, debrief, confirmations)
  calendar    world-day ledger; warns when split groups drift apart
  hirelings   hireling loyalty from pay, treatment, charisma; --roll a check
  district    check city district cards (watch, bribe, gate, curfew, owner)
  chase       seeded city pursuit with complications
  trap        check traps (trigger, detection, disable, effect, severity band)
  downtime    check downtime activities (time, cost or sink, outcome table)
  attendance  players present against the roster; advice for absent PCs
  licence     notices for the bundled rules tables

Exit 2 is a usage or validation error.
"""
import argparse
import csv
import json
import math
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
    a.foe, roles = split_roles(a.foe)
    for f in a.foe:
        xp, note = foe_xp(a.system, f, a.level)
        if xp is None:
            notes.append(f"foe {f}: {note}")
            continue
        total += xp
        if note:
            notes.append(f"foe {f}: {note}")
    haz_xp, haz_notes = hazard_xp(a.system, a.hazard or [], a.level)
    total += haz_xp
    notes += haz_notes
    waves, wave_xp, wave_warns = plan_waves(a)
    band = band_for(total, budgets)
    nxt =[(k, v) for k, v in sorted(budgets.items(), key=lambda kv: kv[1]) if v > total]
    res = {"system": a.system, "party": a.party, "level": a.level, "xp": total, "threat": band,
           "budgets": budgets, "next": {"threat": nxt[0][0], "xp_needed": nxt[0][1] - total} if nxt else None, "notes": notes}
    if a.system == "5e" and total > budgets["high"]:
        res["notes"].append("above the High budget (2024 has no higher band): expect a character to drop")
    if a.system != "5e" and total > budgets["extreme"]:
        res["notes"].append("over the Extreme budget")
    res["warnings"] = mission_warnings(a) + wave_warns + role_warnings(roles, len(a.foe))
    if roles:
        res["roles"] = roles
    if waves:
        res["waves"] = waves
        res["xp_with_waves"] = total + wave_xp
        res["threat_with_waves"] = band_for(total + wave_xp, budgets)
        notes.append(f"with reinforcements: {total + wave_xp} XP, threat {res['threat_with_waves']}")
    bad = any("do not use" in n for n in notes)
    if a.json:
        print(json.dumps(res, indent=2))
        sys.exit(1 if bad else 0)
    print(f"{a.system} party of {a.party} at level {a.level}: {total} XP, threat {band}")
    print("budgets: " + ", ".join(f"{k} {v}" for k, v in budgets.items()))
    if res["next"]:
        print(f"next band: {res['next']['threat']} needs {res['next']['xp_needed']} XP more")
    if roles:
        print("roles: " + ", ".join(f"{k} {v}" for k, v in sorted(roles.items())))
    for n in res["notes"]:
        print("note: " + n)
    for w in res["warnings"]:
        print("warn: " + w)
    sys.exit(1 if bad else 0)


def split_roles(foes):
    """'5:brute' or '5 role:brute' -> level '5' and a role count. Unroled foes count as 'none'."""
    levels, roles = [], {}
    for f in foes:
        f = str(f).strip()
        role = None
        if " role:" in f:
            f, role = f.split(" role:", 1)
        elif ":" in f:
            f, role = f.split(":", 1)
        levels.append(f.strip())
        if role and role.strip():
            r = role.strip().lower()
            roles[r] = roles.get(r, 0) + 1
    if roles and sum(roles.values()) < len(levels):
        roles["none"] = len(levels) - sum(roles.values())
    return levels, roles


def role_warnings(roles, n):
    """A fight of 4+ foes that all share one role plays as one long repeated turn."""
    named = {k: v for k, v in roles.items() if k != "none"}
    if n >= 4 and len(named) == 1 and sum(named.values()) == n:
        return [f"{n} foes, all {next(iter(named))}: mix roles (brute, skirmisher, artillery, controller, leader, lurker) so the fight has more than one problem"]
    return []


HAZARD_REPEAT = 0.1  # each copy of an identical hazard adds this share of one; one answer beats them all


def hazard_xp(system, hazards, level):
    """Identical hazards count barely more than one: the first in full, each repeat a tenth."""
    xp, notes = 0, []
    for h in sorted(set(hazards)):
        n = hazards.count(h)
        one, note = foe_xp(system, h, level)
        if one is None:
            notes.append(f"hazard {h}: {note}")
            continue
        xp += round(one * (1 + HAZARD_REPEAT * (n - 1)))
        if n > 1:
            notes.append(f"hazard {h} x{n}: counted as about one; vary them so one answer does not beat all")
    return xp, notes


def plan_waves(a):
    """Reinforcement waves 'ROUND:COUNTxFOE[:removed_by]'; a finite --pool; --prep steps remove waves."""
    waves, xp, warns = [], 0, []
    done = set(a.prep or [])
    drawn = 0
    for spec in a.wave or []:
        parts = spec.split(":")
        try:
            rnd = int(parts[0])
            cnt, _, foe = parts[1].partition("x")
            cnt = int(cnt)
        except (ValueError, IndexError):
            die(f"bad wave {spec!r} (use ROUND:COUNTxFOE, e.g. 3:2x1, optional :removed_by)")
        foe = foe or str(a.level)
        by = parts[2] if len(parts) > 2 and parts[2] else None
        w = {"round": rnd, "count": cnt, "foe": foe, "removed_by": by, "removed": bool(by and by in done)}
        waves.append(w)
        if w["removed"]:
            continue
        drawn += cnt
        if a.pool is not None and drawn > a.pool:
            warns.append(f"wave at round {rnd} draws past the defender pool ({drawn} of {a.pool}); cut it or grow the pool")
        one, _ = foe_xp(a.system, foe, a.level)
        xp += (one or 0) * cnt
    for p in done - {w["removed_by"] for w in waves}:
        warns.append(f"prep step {p!r} removes no wave; let it change the fight or drop it")
    if waves and a.morale is None:
        warns.append("reinforcements with no --morale: say when the foes retreat (e.g. half) so the fight can end")
    if a.smart and not a.escape:
        warns.append("intelligent foes with no escape route (--escape): they will flee anyway or fight to a pointless death")
    return waves, xp, warns


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
    print(f"round {d['round']}" + (f", turn timer {d['timer']} s (GM may pause it)" if d.get("timer") else ""))
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
        if a.timer:
            d["timer"] = a.timer
    else:
        d = tload(p)
        if a.action in ("hit", "heal"):
            if len(a.args) != 2:
                die(f"{a.action} NAME AMOUNT")
            c = find(d, a.args[0])
            n = int(a.args[1])
            c["hp"] = max(0, c["hp"] - n) if a.action == "hit" else min(c["max_hp"], c["hp"] + n)
            d["log"].append(f"r{d['round']} {c['name']} {a.action} {n} -> {c['hp']}")
        elif a.action == "late":
            c = d["order"][d["turn"]]
            if "delayed" not in c["conditions"]:
                c["conditions"].append("delayed")
            d["log"].append(f"r{d['round']} {c['name']} out of time ({d.get('timer', '?')} s), delayed")
            a.action = "next"
        if a.action == "next":
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


LIKELY = ["definite", "possible", "unlikely"]


def tag(text, key):
    """Value of a 'key: value' tag inside a bullet, up to the next ';' (lower case, '' if absent)."""
    for part in text.split(";"):
        k, _, v = part.partition(":")
        if k.strip().lower().endswith(key) and k.strip().lower().split()[-1:] == [key]:
            return v.strip().lower()
    return ""


DIFF_RANK = {"trivial": 0, "easy": 1, "low": 1, "moderate": 2, "hard": 3, "high": 3, "severe": 4, "deadly": 4, "extreme": 5}
STAKES = ("position", "assets", "character", "party")
LEVERS = {"damage": ("damage",), "disruption": ("hazard", "terrain"), "duration": ("timer", "clock")}


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
    hz = [h.split(":", 1)[0].strip().lower() for h in bullets("hazards")]
    for h in sorted({h for h in hz if hz.count(h) > 1}):
        warns.append(f"{hz.count(h)} hazards named {h!r}: one answer beats them all, so they count as about one; vary them")
    for x in bullets("fights") + bullets("hazards"):
        lx = x.lower()
        if "lethal" in lx and "hidden: yes" in lx:
            errs.append(f"lethal and hidden: players get no fair chance; make it visible or weaker: {x}")
        elif "lethal" in lx and "tell:" not in lx and "warned:" not in lx:
            warns.append(f"lethal threat with no tell (add 'tell: the sign players can notice'): {x}")
    clock = bullets("clock")
    if clock:
        if not any(c.lower().startswith("shown:") for c in clock):
            warns.append("## Clock has no 'shown:' line; players should see it tick")
        for c in clock:
            if not c.lower().startswith("shown:") and (":" not in c or not c.split(":", 1)[1].strip()):
                errs.append(f"clock step without a consequence (write 'step: what happens'): {c}")
    players = [x.split(":", 1)[0].strip() for x in bullets("players")]
    items = leads + bullets("fights") + bullets("hazards") + bullets("scenes")
    for pl in players:
        if not any(pl.lower() in [w.strip() for w in tag(x, "for").split(",")] for x in items):
            warns.append(f"{pl} has no moment (tag a lead, fight or scene 'for: {pl}')")
    tags = [tag(x, "likely") for x in items if tag(x, "likely")]
    for t in tags:
        if t not in LIKELY:
            errs.append(f"likely: {t}, use {LIKELY}")
    if tags:
        if "definite" not in tags:
            warns.append("no item is likely: definite; prep first what will surely happen")
        if tags.count("unlikely") * 2 > len(tags):
            warns.append(f"{tags.count('unlikely')} of {len(tags)} tagged items are unlikely; prep those last or lightly")
    diffs = [tag(x, "diff") for x in bullets("fights") if tag(x, "diff")]
    if len(diffs) >= 3:
        if not set(diffs) & {"trivial", "easy", "low"}:
            warns.append("no easy fight among the rated ones; give the party a fight to feel strong in")
        if not set(diffs) & {"hard", "severe", "extreme", "high", "deadly"}:
            warns.append("no hard fight among the rated ones; one should test them")
    prev = None
    for f in bullets("fights"):
        timed = tag(f, "timer") or tag(f, "clock")
        if (tag(f, "threat") or tag(f, "diff")) and not timed and not tag(f, "treat"):
            warns.append(f"fight with a threat but no timer and no treat (add 'timer: ...' or 'treat: an edge they can find'): {f}")
        rank = DIFF_RANK.get(tag(f, "diff"), None)
        harder = "climax" in f.lower() or (rank is not None and prev is not None and rank > prev)
        if harder:
            lv = {x.strip() for x in tag(f, "levers").split(",") if x.strip()}
            if not lv:
                lv = {k for k, keys in LEVERS.items() if any(tag(f, t) for t in keys)}
            if len(lv) < 2:
                warns.append(f"harder fight turns {len(lv)} lever(s) ({', '.join(sorted(lv)) or 'none'}); "
                             f"raise two of damage, disruption, duration: {f}")
        if rank is not None:
            prev = rank
    stakes = [(f, tag(f, "stakes")) for f in bullets("fights") if tag(f, "stakes")]
    for f, s in stakes:
        if s not in STAKES:
            errs.append(f"stakes: {s}, use {', '.join(STAKES)}")
        elif "climax" in f.lower() and STAKES.index(s) < STAKES.index("character"):
            warns.append(f"climax risks only {s}; a climax should put a character or the party on the line: {f}")
    if len(stakes) >= 2 and len({s for _, s in stakes}) == 1:
        warns.append(f"every rated fight risks {stakes[0][1]}; vary what is at stake")
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
    import re
    since = {}
    for t in th:
        m = re.search(r"\(opened:\s*session\s*(\d+)\)", t, re.I)
        if m:
            since[re.sub(r"\s*\(opened:[^)]*\)", "", t)] = int(m.group(1))
    th = [re.sub(r"\s*\(opened:[^)]*\)", "", t) for t in th]
    opened = [t.rsplit(":", 1)[0].strip() for t in th if t.rsplit(":", 1)[-1].strip().lower() != "paid"]
    print(f"{len(th) - len(opened)} paid, {len(opened)} open")
    now = a.session or max(since.values(), default=0)
    for t in th:
        name = t.rsplit(":", 1)[0].strip()
        if name in opened and t in since and now - since[t] > a.stale:
            print(f"warn: {name}: open {now - since[t]} sessions (since session {since[t]}); "
                  f"pay it off, advance it or drop it on purpose (--stale {a.stale})")
    if opened:
        # Bring threads back roughly in reverse order: the latest promise pays off first.
        print("pay off next (latest first): " + "; ".join(reversed(opened)))
    if a.finale and opened:
        print(f"error: finale with {len(opened)} open promise(s); pay them off or drop them on purpose")
        sys.exit(1)


SESSION_LOG = """# Session {n} log

## Played
- date:
- players present:
- characters present:

## Summary
- (three to five lines; the first becomes next session's recap)

## NPCs met
- Name: what they want now

## Places
-

## Loot
- item: who took it

## Threads
- lead or promise: open (opened: session {n})

## Highlights
- scene; players; what paid off

## Weak points
- scene; players; problem; fix

## Next opening
- where the next session starts
- ending: countdown | hook | choice | ran-long (how this session stopped)
- ended_mid_fight: no
- recap: two lines read aloud to open next session
"""
ENDINGS = ("countdown", "hook", "choice", "ran-long")


def cmd_sessionlog(a):
    """A session log in prep-card markdown; its ## Threads feed 'tt.py threads'."""
    print(SESSION_LOG.format(n=a.session), end="")


NPC_DEPTH = ("ideal", "bond", "flaw")


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
        extra = {p.split(":", 1)[0].strip().lower(): p.split(":", 1)[1].strip()
                 for p in parts if ":" in p and p.split(":", 1)[0].strip().lower() in NPC_DEPTH + ("major", "secret")}
        parts = [p for p in parts if not (":" in p and p.split(":", 1)[0].strip().lower() in extra)]
        if extra.get("major", "").lower() in ("true", "yes"):
            for k in NPC_DEPTH:
                if not extra.get(k) and not (k == "flaw" and extra.get("secret")):
                    errs.append(f"{name.strip()}: major NPC with no {k}" + (" or secret" if k == "flaw" else ""))
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
            if "hints" in x or "reward" in x:
                hints = x.get("hints") or []
                if not hints:
                    warns.append(f"area {n}: puzzle has no hints; write them before play so a stuck table can earn one")
                elif not any(str(h).lower().startswith(("baseline", "any")) for h in hints):
                    warns.append(f"area {n}: no baseline hint (start one 'baseline:'); any check should at least name the puzzle's type")
                if not x.get("reward"):
                    warns.append(f"area {n}: puzzle has no reward; solving it should pay")
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
            tiers = x.get("tiers")
            if tiers is not None:
                if not isinstance(tiers, dict) or len([k for k in ("minimum", "middle", "full") if tiers.get(k)]) < 3:
                    warns.append(f"area {n}: climax tiers want minimum, middle and full outcomes so a worn party still wins something")
                elif "kill" in str(tiers.get("minimum")).lower():
                    warns.append(f"area {n}: the minimum tier needs a kill; make the least win reachable without one")
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


def report(errs, warns, ok):
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print("ok: " + ok)


def cmd_villain(a):
    """Villain cards: one '## Name' section each with wants:, public:, reach:, 2+ harm:, offers with 2+ options."""
    sec = prep_sections(Path(a.card).read_text(encoding="utf-8"))
    errs, warns = [], []
    for name, lines in sec.items():
        b = [l[2:].strip() for l in lines if l[:2] in ("- ", "* ")]
        key = lambda k: [x.split(":", 1)[1].strip() for x in b if x.lower().startswith(k + ":")]
        for k, why in (("wants", "what they want"), ("public", "the face the world sees"),
                       ("reach", "why the party cannot just attack them")):
            if not key(k):
                errs.append(f"{name}: no {k}: ({why})")
        if len(key("harm")) < 2:
            errs.append(f"{name}: {len(key('harm'))} harm: lines, want 2+ indirect ways they hurt the party")
        for o in key("offer"):
            opts = [x.strip() for x in o.split("|") if x.strip()]
            if len(opts) < 2:
                warns.append(f"{name}: offer with one option is an ultimatum; give 2+: {o}")
            for x in opts:
                if "serves:" not in x.lower():
                    warns.append(f"{name}: offer option does not say how it serves the villain: {x}")
    if not sec:
        die("no '## Name' villain sections")
    report(errs, warns, f"{len(sec)} villains")


def cmd_twist(a):
    """Twists (JSON list of {text, axis, sign, removes, workaround}): axis spread, a positive one, workarounds."""
    tw = json.loads(Path(a.twists).read_text(encoding="utf-8"))
    errs, warns = [], []
    for t in tw:
        if t.get("removes") and not t.get("workaround"):
            errs.append(f"twist takes away {t['removes']} with no other route to success: {t.get('text', '?')}")
    axes = {t.get("axis") for t in tw}
    if len(tw) >= 2 and len(axes) == 1:
        warns.append(f"all {len(tw)} twists are on one axis ({axes.pop()}); vary them")
    if tw and not any(t.get("sign") == "+" for t in tw):
        warns.append("no twist helps the party; add one positive")
    report(errs, warns, f"{len(tw)} twists")


def cmd_campaign(a):
    """Campaign plan JSON: every PC has a plotline, adventures have phase and why, NPCs stay out once written out."""
    c = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    adv, errs, warns = c.get("adventures", []), [], []
    for pc in c.get("pcs", []):
        if not any(pc in x.get("plotline", []) for x in adv):
            errs.append(f"PC {pc} has no adventure on their plotline")
    out = {}
    for i, x in enumerate(adv):
        n = x.get("name", f"#{i + 1}")
        for k in ("phase", "why"):
            if not x.get(k):
                errs.append(f"{n}: no {k}:")
        for npc in x.get("npcs", []):
            if npc in out:
                errs.append(f"{n}: uses {npc}, written out in {out[npc]}")
        for npc in x.get("writes_out", []):
            out[npc] = n
        if not (x.get("opposed_by") or x.get("opportunist")):
            warns.append(f"{n}: nobody opposes it or profits from it (opposed_by:, opportunist:)")
        if x.get("major") and i + 1 < len(adv) and not adv[i + 1].get("aftermath"):
            warns.append(f"{n}: major adventure with no aftermath or downtime after it")
    for npc in c.get("payback", []):
        if not any(npc in x.get("payoff", []) for x in adv):
            warns.append(f"{npc} is owed payback with no payoff beat")
    last = 0
    for e in c.get("events", []):
        n = e.get("name", "event")
        for k in ("trigger", "level"):
            if not e.get(k):
                errs.append(f"event {n}: no {k} (plan arcs by what sets them off and the party level, not by date)")
        if isinstance(e.get("level"), int):
            if e["level"] < last:
                warns.append(f"event {n}: level {e['level']} after an event at level {last}")
            last = max(last, e["level"])
    cl = c.get("climax")
    if cl:
        for k in ("trigger", "level"):
            if not cl.get(k):
                errs.append(f"climax: no {k}")
        signs, at = cl.get("signs", []), cl.get("session")
        if len(signs) < a.signs:
            warns.append(f"climax has {len(signs)} foreshadowing signs, want {a.signs}+")
        for s in signs:
            t, when = s.get("text", "?"), s.get("session")
            if not isinstance(when, int):
                errs.append(f"sign {t!r}: no session to show it in")
            elif isinstance(at, int) and when >= at:
                errs.append(f"sign {t!r}: session {when} is not before the climax (session {at})")
        if signs and not isinstance(at, int):
            warns.append("climax has no session, so sign timing cannot be checked")
    report(errs, warns, f"{len(adv)} adventures, {len(c.get('pcs', []))} PCs with plotlines")


FOLLOWUP_SHAPES = ("framed", "accused", "mistaken", "ambush")


def cmd_hooks(a):
    """Hook deck JSON list of {text, shape, district, stakes, choice, followup, truth, rumour}."""
    hs = json.loads(Path(a.deck).read_text(encoding="utf-8"))
    errs, warns = [], []
    shapes = {}
    for i, h in enumerate(hs):
        n = h.get("text", f"#{i + 1}")[:40]
        for k in ("shape", "district", "stakes"):
            if not h.get(k):
                errs.append(f"{n}: no {k}: tag")
        if h.get("stakes") != "colour" and len(h.get("choice", [])) < 2:
            warns.append(f"{n}: plot hook with fewer than two choices")
        if h.get("shape") in FOLLOWUP_SHAPES and not h.get("followup"):
            errs.append(f"{n}: {h['shape']} hook with no followup (who did it, what next)")
        if h.get("rumour") and (not h.get("truth") or h.get("truth") == h.get("text")):
            errs.append(f"{n}: rumour with no separate truth:")
        if h.get("shape"):
            shapes[h["shape"]] = shapes.get(h["shape"], 0) + 1
    if len(hs) >= 5:
        top, cnt = max(shapes.items(), key=lambda kv: kv[1], default=("", 0))
        if cnt / len(hs) > 0.4:
            warns.append(f"{cnt} of {len(hs)} hooks are shape {top}; vary them")
        colour = sum(h.get("stakes") == "colour" for h in hs) / len(hs)
        if colour > 0.8 or colour < 0.2:
            warns.append(f"colour-only share is {colour:.0%}; mix colour with plot hooks")
    report(errs, warns, f"{len(hs)} hooks")


TAVERN_NEEDS = {
    "map_dot": ("name",),
    "plot_point": ("name", "location", "hook"),
    "encounter": ("name", "location", "hook", "rooms", "menu", "npcs", "furnishing"),
    "adventure": ("name", "location", "hook", "rooms", "menu", "npcs", "furnishing", "conflict"),
}


def cmd_tavern(a):
    """Tavern card JSON: fields by role, a house special, map fits play, conflict sides, hooks say where to go."""
    t = json.loads(Path(a.card).read_text(encoding="utf-8"))
    errs, warns = [], []
    role = t.get("role", "encounter")
    if role not in TAVERN_NEEDS:
        die(f"role must be one of {', '.join(TAVERN_NEEDS)}")
    for k in TAVERN_NEEDS[role]:
        if not t.get(k):
            errs.append(f"{role} card has no {k}:")
    if t.get("menu") and not any(m.get("special") for m in t["menu"]):
        warns.append("no house special on the menu")
    exp = t.get("expects", [])
    if "combat" in exp and t.get("map") != "battlemap":
        warns.append("combat expected but no battlemap")
    if {"explore", "stealth"} & set(exp) and t.get("map", "none") == "none":
        warns.append("exploration or stealth expected but no map")
    c = t.get("conflict")
    if c and len(c.get("factions", [])) < 2:
        errs.append("conflict needs at least two factions")
    for h in t.get("hooks", []):
        if not h.get("goto"):
            warns.append(f"hook does not say where to go: {h.get('text', '?')[:40]}")
    kinds = {e.get("type") for e in t.get("encounters", [])}
    if len(t.get("encounters", [])) >= 3 and len(kinds) == 1:
        warns.append(f"every stock encounter is {kinds.pop()}; vary them")
    pcs = t.get("pcs", [])
    for pc in pcs:
        if not any(pc in h.get("for", []) for h in t.get("hooks", [])):
            warns.append(f"no hook for {pc}")
    report(errs, warns, f"{role} card {t.get('name', '?')}")


def cmd_venues(a):
    """Venue counts for a settlement against one tavern per 2,000, restaurant per 3,500, inn per 5,000."""
    errs, warns = [], []
    for kind, per, have in (("taverns", 2000, a.taverns), ("restaurants", 3500, a.restaurants), ("inns", 5000, a.inns)):
        want = max(1 if kind != "restaurants" else 0, round(a.population / per))
        if have is None:
            print(f"{kind}: about {want}")
            continue
        if kind != "restaurants" and have < 1:
            errs.append(f"no {kind[:-1]}; every community has one")
        elif want and (have > 2 * want or have * 2 < want) and not a.anomaly:
            warns.append(f"{have} {kind}, expected about {want}; give a reason with --anomaly or adjust")
    report(errs, warns, f"population {a.population}")


def cmd_party(a):
    """Party JSON {pcs: [{name, ties, plot_tie}], reveals: [{text, fallback}]}: PC ties, plot ties, plan B."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    pcs = d.get("pcs", [])
    names = {p.get("name") for p in pcs}
    errs, warns = [], []
    need = min(2, len(pcs) - 1)
    for p in pcs:
        n = p.get("name", "?")
        ties = p.get("ties", [])
        for t in ties:
            if t not in names or t == n:
                errs.append(f"{n}: tie to {t}, who is not another PC")
        if len(set(ties) & (names - {n})) < need:
            warns.append(f"{n}: tied to fewer than {need} other PCs")
        if not p.get("plot_tie"):
            errs.append(f"{n}: no plot_tie to the main plot")
    for r in d.get("reveals", []):
        if not r.get("fallback"):
            errs.append(f"reveal with no fallback if the players guess or skip it: {r.get('text', '?')[:40]}")
    report(errs, warns, f"{len(pcs)} PCs, {len(d.get('reveals', []))} reveals")


TIERS = ["minor", "moderate", "major", "legendary", "campaign"]
YES = ("yes", "y", "true", "1")


ITEM_NEW = ("cost_axis", "uses", "unpredictable", "bypasses", "friction")
COST_AXES = ["coin", "body", "mind", "time", "social", "risk", "none"]
USES = ["at-will", "per-day", "charges", "once"]


def cmd_mystery(a):
    """Mystery JSON: each conclusion has 3 clues a party can find, 3+ suspects, an opening not aimed at the culprit."""
    m = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    lvl = m.get("party_level", 1)
    dc = 10 + lvl // 2
    clues, sus = m.get("clues", []), m.get("suspects", [])
    concl = m.get("conclusions", [])
    if not concl:
        die("no conclusions")
    for c in concl:
        cid = c.get("id", "?")
        cs = [x for x in clues if x.get("points_to") == cid]
        if len(cs) < 2:
            errs.append(f"conclusion {cid}: {len(cs)} clue(s); one missed roll stalls the case, want 3")
        elif len(cs) == 2:
            warns.append(f"conclusion {cid}: 2 clues; 3 is the safe count")
        if cs and all(isinstance(x.get("dc"), (int, float)) and x["dc"] > dc + 5 for x in cs):
            errs.append(f"conclusion {cid}: every clue needs a DC over {dc + 5} (typical {dc} at level {lvl})")
    if len(sus) < 3:
        warns.append(f"{len(sus)} suspects; 3+ keeps the answer from being obvious")
    culprits = {s.get("name") for s in sus if s.get("culprit")}
    finals = {c.get("id") for c in concl if c.get("final")}
    targets = culprits | finals
    first = min((x.get("scene", 1) for x in clues), default=1)
    opening = [x for x in clues if x.get("scene", 1) == first]
    if opening and targets and all(x.get("points_to") in targets for x in opening):
        warns.append(f"every scene {first} clue points at the culprit; the case ends in the first scene")
    report(errs, warns, f"{len(concl)} conclusions, {len(clues)} clues, {len(sus)} suspects")


COMFORT = ["none", "offscreen", "limited", "full"]


def cmd_safety(a):
    """Safety plan JSON: a cut call, a brake call, a debrief, warnings for lines and veils, every player confirmed."""
    s = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    if not s.get("cut_call"):
        errs.append("no cut_call: the word that stops a scene at once")
    if not s.get("brake_call"):
        warns.append("no brake_call: the word that slows a scene down")
    dm = s.get("debrief_minutes")
    if not isinstance(dm, (int, float)) or dm < 10:
        warns.append(f"debrief_minutes {dm}; plan 10 or more to talk after play")
    if (s.get("lines") or s.get("veils")) and not s.get("content_warnings"):
        warns.append("lines or veils set but no content_warnings for the players before play")
    comfort, planned = s.get("comfort") or {}, s.get("planned") or {}
    floor = {}
    for who, topics in comfort.items():
        for t, lv in topics.items():
            if lv not in COMFORT:
                errs.append(f"{who}: {t} level {lv!r}, use {COMFORT}")
            else:
                floor[t] = min(floor.get(t, 3), COMFORT.index(lv))
    for t, lv in planned.items():
        if lv not in COMFORT:
            errs.append(f"planned {t} level {lv!r}, use {COMFORT}")
        elif t not in floor:
            warns.append(f"planned topic {t} that no player rated; ask before play")
        elif COMFORT.index(lv) > floor[t]:
            errs.append(f"{t} planned {lv} but the most cautious player allows {COMFORT[floor[t]]}; the lowest level wins")
    if floor:
        print("topic levels: " + ", ".join(f"{t} {COMFORT[v]}" for t, v in sorted(floor.items())))
    for k, why in (("takebacks", "when a player may take back an action"), ("info_flow", "what is said openly and what goes by note")):
        if k in s and not s[k]:
            warns.append(f"{k} empty: agree {why}")
    conf = set(s.get("players_confirmed", []))
    if a.party:
        pcs = json.loads(Path(a.party).read_text(encoding="utf-8")).get("pcs", [])
        for p in pcs:
            who = p.get("player") or p.get("name")
            if who not in conf:
                errs.append(f"{who} has not confirmed the safety plan")
    report(errs, warns, f"cut call set, {len(conf)} player(s) confirmed")


DICE = (2, 3, 4, 6, 8, 10, 12, 20, 100)


def roll_range(r):
    lo, _, hi = r["roll"].strip().partition("-")
    return int(lo), int(hi or lo)


def read_table(path):
    """Rows of a roll table CSV plus the covered rolls and gap/overlap errors."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    errs, covered = [], set()
    for r in rows:
        try:
            lo, hi = roll_range(r)
        except (KeyError, ValueError, AttributeError):
            die(f"{path}: bad roll {r.get('roll')!r} (use 3 or 1-4)")
        span = set(range(lo, hi + 1))
        if covered & span:
            errs.append(f"roll {r['roll']} overlaps another row")
        covered |= span
    top = max(covered) if covered else 0
    gaps = sorted(set(range(1, top + 1)) - covered)
    if gaps:
        errs.append(f"rolls with no row: {gaps[:10]}{' ...' if len(gaps) > 10 else ''}")
    return rows, covered, errs


def cmd_combine(a):
    """Roll 2 to 4 tables together: K distinct combinations, seeded."""
    import itertools, random
    if not 2 <= len(a.tables) <= 4:
        die("combine takes 2 to 4 tables")
    tabs = []
    for t in a.tables:
        rows, _, errs = read_table(t)
        if errs:
            die(f"{t}: " + "; ".join(errs))
        if len(rows) < 6:
            die(f"{t}: {len(rows)} rows, want at least 6 so combinations stay varied")
        tabs.append(rows)
    label = lambda r: " / ".join(v.strip() for k, v in r.items() if k != "roll" and v and v.strip()) or r["roll"]
    total = 1
    for rows in tabs:
        total *= len(rows)
    rng = random.Random(a.seed)
    if a.count <= total:
        picks = []
        for i in rng.sample(range(total), a.count):
            idx = []
            for rows in reversed(tabs):
                i, j = divmod(i, len(rows))
                idx.append(j)
            picks.append(tuple(reversed(idx)))
    else:
        print(f"note: {a.count} asked, only {total} distinct combinations; repeats follow")
        picks = [tuple(rng.randrange(len(rows)) for rows in tabs) for _ in range(a.count)]
    for n, p in enumerate(picks, 1):
        print(f"{n}. " + " + ".join(label(tabs[t][j]) for t, j in enumerate(p)))


def cmd_table(a):
    """Check a random encounter table CSV (roll,kind,difficulty,avoidable): gaps, fight share, unavoidable easy fights."""
    if a.table == "combine":
        return cmd_combine(a)
    if a.tables:
        die("table takes one file (or: table combine A.csv B.csv ...)")
    rows, covered, errs = read_table(a.table)
    warns, fights = [], 0
    for r in rows:
        lo, hi = roll_range(r)
        span = set(range(lo, hi + 1))
        kind = (r.get("kind") or "").strip().lower()
        if kind == "fight":
            fights += len(span)
            if r.get("difficulty", "").strip().lower() in ("trivial", "easy", "low") and r.get("avoidable", "").strip().lower() not in YES:
                warns.append(f"roll {r['roll']}: easy fight the party cannot avoid (a speed bump; make it avoidable)")
    top = max(covered) if covered else 0
    low = min(covered) if covered else 1
    if a.die:
        if top != a.die or low != 1:
            warns.append(f"rolls run {low} to {top} but the die is d{a.die}: every face 1 to {a.die} needs exactly one row")
    elif top not in DICE or low != 1:
        warns.append(f"rolls run {low} to {top}, not a standard die; pass --die N if that is meant")
    whens = [(r.get("when") or "").strip().lower() for r in rows if "when" in r]
    if whens:
        bad = sorted(set(whens) - {"moving", "camped", "any"})
        if bad:
            warns.append(f"when values {bad}; use moving, camped or any")
        if len(set(whens)) == 1 and whens[0] != "any":
            warns.append(f"every row is {whens[0]}; give the other state some rows too")
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
        if it.get("reward"):
            if not (it.get("condition") or it.get("expectation")):
                errs.append(f"{n}: {it['reward']} reward with no condition or expectation (what the giver expects, "
                            "and what makes it lapse)")
            continue
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
        if any(k in it for k in ITEM_NEW):
            cost = it.get("cost_axis")
            if cost is not None and cost not in COST_AXES:
                errs.append(f"{n}: cost_axis must be one of {COST_AXES}")
            elif cost in (None, "none") and b in TIERS and b != TIERS[0]:
                errs.append(f"{n}: {b} item with no cost_axis; magic above the lowest tier should cost coin, body, mind, time, standing or risk")
            if it.get("uses") is not None and it["uses"] not in USES:
                errs.append(f"{n}: uses must be one of {USES}")
            if it.get("unpredictable") and it.get("uses") == "at-will":
                warns.append(f"{n}: unpredictable at will; players will spam it until it fires right, limit the uses")
            if it.get("bypasses") and not it.get("friction"):
                errs.append(f"{n}: bypasses {', '.join(it['bypasses'])} with no friction; it erases that part of the game")
    for w in warns:
        print("warn: " + w)
    for e in errs:
        print("error: " + e)
    if errs:
        sys.exit(1)
    print("ok: every boon has a matching drawback")


# 0.9.0: table-running helpers. Bands, steps and odds are ours and configurable.

def cmd_strength(a):
    """Average party level (.5 rounds up) and a strength label from headcount and APL against the target."""
    n = len(a.levels)
    total = sum(a.levels)
    apl = (2 * total + n) // (2 * n)
    errs, warns = [], []
    if n < 3 or n > 7:
        errs.append(f"{n} players; a drop-in table runs 3 to 7")
    size = (n > a.target_size) - (n < a.target_size)
    lvl = (apl > a.target_level) - (apl < a.target_level)
    label = {-2: "very weak", -1: "weak", 0: "average", 1: "strong", 2: "very strong"}[size + lvl]
    print(f"APL {apl} ({total}/{n}); size {n} vs {a.target_size}, level {apl} vs {a.target_level}: {label}")
    if label != "average":
        warns.append("a coarse overlay; check the fight itself with tt.py encounter")
    report(errs, warns, label)


def cmd_loot(a):
    """Loot JSON {gold, pcs: [{name, permanent}], items: [{name, kind, interested, agreed}]}: split and award."""
    import random
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    pcs = d.get("pcs", [])
    if not pcs:
        die("loot needs pcs")
    names = [p["name"] for p in pcs]
    count = {p["name"]: int(p.get("permanent", 0)) for p in pcs}
    rng = random.Random(a.seed)
    share, rest = divmod(int(d.get("gold", 0)), len(pcs))
    print(f"gold: {share} each to {len(pcs)}" + (f", {rest} left over for the party fund" if rest else ""))
    errs = []
    for it in d.get("items", []):
        n = it.get("name", "?")
        if it.get("kind", "permanent") != "permanent":
            print(f"{n}: consumable, players divide it; a dispute goes to a roll")
            continue
        who, why = it.get("agreed"), "agreed"
        if who and who not in names:
            errs.append(f"{n}: agreed PC {who} is not in pcs")
            continue
        if not who:
            want = [w for w in it.get("interested", []) if w in names]
            if not want:
                print(f"{n}: nobody wants it; sell it into the gold")
                continue
            low = min(count[w] for w in want)
            tied = [w for w in want if count[w] == low]
            who = tied[0] if len(tied) == 1 else rng.choice(tied)
            why = f"fewest permanent items ({low})" + (f", won a roll among {len(tied)}" if len(tied) > 1 else "")
        count[who] += 1
        print(f"{n}: {who} ({why})")
    report(errs, [], "loot split")


REACTION_BANDS = [(3, "hostile"), (6, "wary"), (9, "neutral"), (11, "open"), (99, "helpful")]


def reaction_band(total):
    return next(b for top, b in REACTION_BANDS if total <= top)


def cmd_reaction(a):
    """First reaction of an improvised NPC: 2d6 plus modifiers, banded (our bands)."""
    import random
    rng = random.Random(a.seed)
    roll = a.roll if a.roll is not None else rng.randint(1, 6) + rng.randint(1, 6)
    mods = sum(a.mod or []) + {"friendly": 1, "neutral": 0, "hostile": -2}[a.approach]
    total = roll + mods
    print(f"roll {roll} {mods:+d} = {total}: {reaction_band(total)}")
    print("use it for NPCs made on the spot; a written NPC reacts as written")


HEAT_STEPS = [(2, "quiet"), (4, "noticed: rumours, a warning"), (6, "collector: a fine, a bribe or a favour owed"),
              (8, "enforcers sent"), (10 ** 9, "open hunt")]


def heat_step(h):
    return next(s for top, s in HEAT_STEPS if h <= top)


def cmd_heat(a):
    """Faction ledger JSON: standing (-3..3) with reasons, heat that rises with crimes and witnesses."""
    f = Path(a.file)
    led = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if a.action in ("crime", "standing") and not a.faction:
        die(f"heat {a.action} needs a faction")
    if a.action == "standing" and not a.why:
        die("a standing change needs --why")
    if a.action in ("crime", "standing"):
        e = led.setdefault(a.faction, {"standing": 0, "heat": 0, "log": []})
    if a.action == "crime":
        before = heat_step(e["heat"])
        e["heat"] += 1 + a.witnesses
        e["log"].append(f"crime, {a.witnesses} witnesses: {a.why or 'no note'}")
        if heat_step(e["heat"]) != before:
            print(f"{a.faction} escalates: {heat_step(e['heat'])}")
    elif a.action == "standing":
        e["standing"] = max(-3, min(3, e["standing"] + a.by))
        e["log"].append(f"standing {a.by:+d}: {a.why}")
    elif a.action == "cool":
        for e in led.values():
            e["heat"] = max(0, e["heat"] - a.by)
    if a.action != "show":
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(led, indent=2), encoding="utf-8")
    for name, e in sorted(led.items(), key=lambda kv: -kv[1]["heat"]):
        last = e["log"][-1] if e["log"] else "-"
        print(f"{name}: standing {e['standing']:+d}, heat {e['heat']} ({heat_step(e['heat'])}); last: {last}")


def cmd_premise(a):
    """Premise card JSON: core and twist, a hook layer unlike the real one, per-type needs."""
    d = json.loads(Path(a.card).read_text(encoding="utf-8"))
    errs, warns = [], []
    for k in ("type", "core", "twist"):
        if not d.get(k):
            errs.append(f"no {k}")
    hook = d.get("hook")
    if hook and hook.get("type") == d.get("type") and hook.get("root", "") == d.get("root", ""):
        errs.append("hook layer is the same premise with the same root; change one")
    t = d.get("type")
    if t == "pursuit" and not d.get("finish_line"):
        errs.append("pursuit needs a finish_line past which the quarry is lost")
    if t == "race":
        fs = d.get("factions", [])
        if len(fs) < 2:
            errs.append("race needs 2+ factions")
        for fc in fs:
            if not fc.get("agenda"):
                errs.append(f"faction {fc.get('name', '?')} has no agenda")
    if t == "investigation" and not d.get("at_risk"):
        errs.append("investigation needs a witness or clue that can be lost (at_risk)")
    if t == "defend" and not (d.get("faulty_intel") or d.get("choice")):
        warns.append("defend: add faulty_intel or a choice beat")
    if t == "object" and "incomplete" in str(d.get("twist", "")).lower():
        warns.append("an object found incomplete frustrates players; pick another twist")
    report(errs, warns, f"{t} premise")


def cmd_wander(a):
    """Random-encounter clock: checks per period, then distance, surprise, reaction or evasion. Numbers configurable."""
    import random
    if a.chance < 1 or a.every <= 0:
        die("--chance and --every must be positive")
    warns = []
    checks = int(a.hours * 60 // a.every)
    expected = checks / a.chance
    print(f"{checks} checks at 1 in {a.chance}: about {expected:.1f} encounters in {a.hours:g} h")
    if expected > a.budget:
        warns.append(f"about {expected:.1f} encounters, over the budget of {a.budget:g}; check less often or lower the chance")
    if a.placed:
        warns.append(f"placed population in {', '.join(a.placed)}: use it there instead of rolling")
    if a.run:
        rng = random.Random(a.seed)
        for i in range(1, checks + 1):
            if rng.randint(1, a.chance) != 1:
                continue
            dist = (rng.randint(1, 6) + rng.randint(1, 6)) * a.feet
            us = rng.randint(1, a.surprise) == 1
            them = rng.randint(1, a.surprise) == 1
            if us != them:
                dist = max(a.feet, dist // 2)
            r = rng.randint(1, 6) + rng.randint(1, 6)
            line = f"check {i} (minute {i * a.every:g}): encounter at {dist} ft"
            line += ", party surprised" if us else ""
            line += ", foes surprised" if them else ""
            line += f"; reaction {r}: {reaction_band(r)}"
            if not us and dist > 3 * a.feet:
                line += "; party can evade"
            print(line)
    report([], warns, "encounter clock")


# 0.10.0: battles, reviews, house rules, challenges, travel. Steps and multipliers are ours.
BATTLE_STEPS = {2: "decisive win", 1: "win at a cost", 0: "stalemate", -1: "pushed back", -2: "rout"}
RESULT = {"won": 1, "drawn": 0, "lost": -1}


def cmd_battle(a):
    """Mass battle JSON: exactly three fights the PCs play, each with a shape and what a win carries forward."""
    d = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    fights = d.get("fights", [])
    errs, warns = [], []
    if len(fights) != 3:
        errs.append(f"{len(fights)} fights, want 3: the PCs play three moments that stand for the whole battle")
    for i, f in enumerate(fights, 1):
        if not f.get("shape"):
            errs.append(f"fight {i}: no shape (what this moment is: hold the gate, break the line, save the banner)")
        if i < len(fights) and not f.get("carry"):
            warns.append(f"fight {i}: no carry (what winning gives fight {i + 1})")
    shapes = [str(f.get("shape", "")).lower() for f in fights]
    if len(set(shapes)) < len(shapes):
        warns.append("two fights share a shape; vary them")
    if d.get("narration") and any(w in str(d["narration"]).lower() for w in ("pcs ", "the party ", "players ")):
        warns.append("narration describes the PCs; the story between fights covers the armies, the players act for their own")
    if errs:
        return report(errs, warns, "")
    if a.results:
        res = [x.strip().lower() for x in a.results.split(",")]
        if len(res) != 3 or any(x not in RESULT for x in res):
            die("--results wants three of won, drawn, lost")
        for i, x in enumerate(res[:2]):
            if x == "won":
                print(f"fight {i + 2} starts with: {fights[i].get('carry', 'the edge from fight %d' % (i + 1))}")
        score = sum(RESULT[x] for x in res)
        print(f"battle: {BATTLE_STEPS[max(-2, min(2, score))]} (score {score:+d})")
    report([], warns, "three fights with shapes")


def cmd_review(a):
    """Merge '## Highlights' and '## Weak points' from session logs into a per-player tally."""
    hi, weak, fixes, ends = {}, {}, [], {}
    for f in a.logs:
        text = Path(f).read_text(encoding="utf-8")
        recap = False
        for line in text.splitlines():
            k, _, v = line.lstrip("-* ").partition(":")
            v = v.strip().lower()
            if k.strip().lower() == "recap" and v and not v.startswith("two lines read aloud"):
                recap = True
            if k.strip().lower() == "ended_mid_fight" and v in ("yes", "true", "y"):
                print(f"warn: {f}: ended mid-fight; open next time with the board as it stood and a quick recap of positions")
            if k.strip().lower() == "ending" and v and "|" not in v:
                ends[v] = ends.get(v, 0) + 1
                if v not in ENDINGS:
                    print(f"warn: {f}: ending {v!r}, use " + ", ".join(ENDINGS))
        if not recap:
            print(f"warn: {f}: no recap: line; write two lines to read aloud next session")
        sec = prep_sections(text)
        for key, tally in (("highlights", hi), ("weak points", weak)):
            for line in sec.get(key, []):
                if line[:2] not in ("- ", "* "):
                    continue
                parts = [x.strip() for x in line[2:].split(";")]
                if len(parts) < 3 or not parts[0] or parts[0] == "scene":
                    continue
                for who in [w.strip() for w in parts[1].split(",") if w.strip()]:
                    tally.setdefault(who, []).append(parts[2])
                if key == "weak points":
                    fixes.append(f"{parts[0]}: {parts[3] if len(parts) > 3 and parts[3] else 'no fix written'}")
    people = sorted(set(hi) | set(weak))
    if ends:
        print("endings: " + ", ".join(f"{k} {v}" for k, v in sorted(ends.items())))
        if ends.get("ran-long", 0) * 2 > sum(ends.values()):
            print("warn: most sessions ran long instead of stopping on a planned ending")
    if not people and ends:
        return
    if not people:
        die("no filled Highlights or Weak points bullets in those logs")
    for who in people:
        print(f"{who}: {len(hi.get(who, []))} highlights, {len(weak.get(who, []))} weak points"
              + (f"; liked: {', '.join(hi[who])}" if who in hi else ""))
    for x in fixes:
        print("fix: " + x)
    for who in people:
        if who not in hi:
            print(f"warn: {who} has no highlight in {len(a.logs)} session(s); plan a moment for them")


def cmd_houserules(a):
    """House rules JSON list: each rule has kind (add, change, remove) and why; removals want an offset."""
    rules = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    for r in rules:
        name = r.get("rule") or "?"
        if r.get("kind") not in ("add", "change", "remove"):
            errs.append(f"{name}: kind {r.get('kind')!r}, use add, change or remove")
        if not r.get("why"):
            errs.append(f"{name}: no why; a rule nobody can explain is hard to defend or drop")
        if r.get("kind") == "remove" and not r.get("offset"):
            warns.append(f"{name}: removed with no offset; whatever relied on it (a class, a threat) is now off balance")
        if r.get("kind") in ("add", "change") and not r.get("review_after"):
            warns.append(f"{name}: no review_after (sessions until the table decides to keep it)")
    seen = {}
    for r in rules:
        sit = str(r.get("situation") or r.get("trigger") or "").strip().lower()
        if not sit:
            continue
        for o in seen.get(sit, []):
            if o.get("rule") != r.get("rule") and not o.get("distinguishes") and not r.get("distinguishes"):
                warns.append(f"{o.get('rule')!r} and {r.get('rule')!r} rule the same situation ({sit}) differently; "
                             "add 'distinguishes:' saying what sets them apart, or merge them")
        seen.setdefault(sit, []).append(r)
    report(errs, warns, f"{len(rules)} house rule(s) with reasons")


SKILL_KINDS = ("social", "physical", "knowledge", "perception", "stealth", "magic", "craft")


def cmd_challenge(a):
    """Skill challenge or long task JSON: goal, successes before failures, varied skills, a failure route, a shown score."""
    d = json.loads(Path(a.card).read_text(encoding="utf-8"))
    errs, warns = [], []
    succ, fail = d.get("successes"), d.get("failures")
    if not d.get("goal"):
        errs.append("no goal: what the party gets when it succeeds")
    if not isinstance(succ, int) or succ < 2:
        errs.append(f"successes {succ!r}, want 2 or more")
    if not isinstance(fail, int) or fail < 1:
        errs.append(f"failures {fail!r}, want 1 or more")
    elif isinstance(succ, int) and fail > succ:
        warns.append(f"{fail} failures allowed for {succ} successes; it can barely fail")
    skills = d.get("skills", [])
    kinds = {s.get("kind") for s in skills}
    if len(skills) < 3:
        errs.append(f"{len(skills)} skills, want 3 or more so every player can add something")
    elif len(kinds) < 2:
        warns.append("all skills are one kind; mix them (" + ", ".join(SKILL_KINDS) + ")")
    if not d.get("on_fail"):
        errs.append("no on_fail: the story goes on after a failure, at a cost; name it")
    if not d.get("shown"):
        warns.append("no shown: how players see the running score")
    pool, ms = d.get("pool"), d.get("milestones") or []
    if pool is not None:
        if not isinstance(pool, int) or pool < 1:
            errs.append(f"pool {pool!r}, want a positive number")
        else:
            for m in ms:
                if not isinstance(m.get("at"), int) or not 0 < m["at"] < pool:
                    errs.append(f"milestone at {m.get('at')!r} is outside the pool 1 to {pool - 1}")
            if not ms:
                warns.append("long task with no milestones; partial progress should show and pay")
    mins, limit = d.get("minutes"), d.get("limit")
    if mins and limit and isinstance(succ, int) and limit < succ * mins:
        warns.append(f"limit {limit} min is under {succ} attempts x {mins} min; the clock beats a flawless run")
    report(errs, warns, f"{succ} successes before {fail} failures, {len(skills)} skills")


TERRAIN = {"road": 1.0, "plains": 0.75, "forest": 0.5, "hills": 0.5, "swamp": 0.35, "mountain": 0.25, "desert": 0.5}


def cmd_travel(a):
    """Days for a trip: pace times terrain, hours past 8 a day cost fatigue, an unknown route adds a quarter."""
    if a.terrain not in TERRAIN:
        die(f"terrain {a.terrain!r}, use {', '.join(TERRAIN)}")
    if a.miles <= 0 or a.pace <= 0 or not 1 <= a.hours <= 16:
        die("miles and pace above 0, hours 1 to 16")
    per_day = a.pace * TERRAIN[a.terrain] * a.hours / 8
    days = a.miles / per_day * (1 if a.known else 1.25)
    whole = math.ceil(days - 1e-9)
    print(f"{per_day:.1f} miles a day on {a.terrain}; {whole} day(s) for {a.miles:g} miles"
          + ("" if a.known else " (unknown route: +25%, one navigation check a day)"))
    over = max(0, a.hours - 8)
    if over:
        print(f"fatigue: {math.ceil(over)} point(s) a day from {over:g} hour(s) past 8; {math.ceil(over) * whole} over the trip")


# 0.11.0: calendar, hirelings, districts, chases. Numbers and wording are ours.
def cmd_calendar(a):
    """World-day ledger JSON {"groups": {name: [{"day": N, "event": "..."}]}}: flags split groups that drift apart."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    groups = d.get("groups", d) if isinstance(d, dict) else None
    if not isinstance(groups, dict) or not groups:
        die('want {"groups": {"Name": [{"day": 1, "event": "..."}]}}')
    errs, warns, now = [], [], {}
    for name, evs in groups.items():
        last = None
        print(f"{name}:")
        for e in evs:
            day = e.get("day")
            if not isinstance(day, int):
                errs.append(f"{name}: event {e.get('event', '?')!r} has no whole-number day")
                continue
            if last is not None and day < last:
                errs.append(f"{name}: day {day} after day {last}; keep each group's events in order")
            last = day if last is None else max(last, day)
            print(f"  day {day}: {e.get('event', '')}")
        now[name] = last if last is not None else 0
    if len(now) > 1:
        ahead = max(now, key=now.get)
        for name, day in sorted(now.items(), key=lambda kv: kv[1]):
            gap = now[ahead] - day
            if gap >= a.drift:
                warns.append(f"{name} is on day {day}, {gap} days behind {ahead} (day {now[ahead]}); "
                             "play the lagging group forward before the groups meet or trade news")
    report(errs, warns, f"{len(now)} group(s), world day {max(now.values())}")


HIRE_TREAT = {"good": 10, "fair": 0, "poor": -15, "abusive": -30}
HIRE_EVENTS = {"unpaid": -15, "abused": -20, "sent-ahead": -10, "bribe": -15, "leader-down": -10}


def hire_base(h, d):
    """Loyalty base (5 to 95): 50, pay against the going rate, treatment, 5 per point of leader charisma modifier."""
    rate = h.get("going_rate", d.get("going_rate"))
    pay = h.get("pay")
    base, why = 50, []
    if isinstance(rate, (int, float)) and isinstance(pay, (int, float)) and rate > 0:
        r = pay / rate
        adj = 15 if r >= 1.5 else 5 if r >= 1.0 else -10 if r >= 0.75 else -25
        base += adj
        why.append(f"pay {pay:g} vs rate {rate:g} {adj:+d}")
    treat = str(h.get("treatment", "fair")).lower()
    t = HIRE_TREAT.get(treat, 0)
    base += t
    why.append(f"treatment {treat} {t:+d}")
    cha = d.get("leader_cha_mod", 0)
    if isinstance(cha, int) and cha:
        base += 5 * cha
        why.append(f"leader charisma {cha:+d} x5")
    return max(5, min(95, base)), why


def cmd_hirelings(a):
    """Hireling roster JSON: loyalty base from pay vs going rate, treatment, leader charisma; --roll NAME checks it."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    hs = d.get("hirelings", [])
    if not hs:
        die("no hirelings in the roster")
    errs, warns, base = [], [], {}
    for h in hs:
        n = h.get("name") or "?"
        if h.get("pay") is None:
            errs.append(f"{n}: no pay")
        if h.get("going_rate", d.get("going_rate")) is None:
            warns.append(f"{n}: no going_rate (here or roster-wide); pay counts as neutral")
        if str(h.get("treatment", "fair")).lower() not in HIRE_TREAT:
            warns.append(f"{n}: treatment {h.get('treatment')!r}, use " + ", ".join(HIRE_TREAT))
        base[n], why = hire_base(h, d)
        print(f"{n}: loyalty {base[n]} ({'; '.join(why)})")
    print("check loyalty on: " + ", ".join(HIRE_EVENTS) + " (left unpaid, mistreated, sent first into danger, "
          "offered a better deal by a rival, the leader falls)")
    if a.roll:
        if a.roll not in base:
            die(f"no hireling {a.roll!r}")
        if a.event and a.event not in HIRE_EVENTS:
            die("--event is one of " + ", ".join(HIRE_EVENTS))
        target = max(5, min(95, base[a.roll] + HIRE_EVENTS.get(a.event, 0)))
        import random
        r = a.die if a.die else random.Random(a.seed).randint(1, 100)
        res = ("stays loyal" if r <= target else
               "wavers: refuses this order" if r <= target + 20 else "breaks: flees, deserts or takes the deal")
        print(f"check {a.roll}{' (' + a.event + ')' if a.event else ''}: d100 {r} vs {target}: {res}")
    report(errs, warns, f"{len(hs)} hireling(s)")


DISTRICT_FIELDS = ("watch", "bribe", "curfew", "owner")


def cmd_district(a):
    """City district cards JSON list: watch strength, bribe cost, gate and curfew rules, who holds the block."""
    ds = json.loads(Path(a.file).read_text(encoding="utf-8"))
    if isinstance(ds, dict):
        ds = ds.get("districts", [])
    if not ds:
        die("no districts")
    warns = []
    for x in ds:
        n = x.get("name") or "?"
        for f in DISTRICT_FIELDS:
            if x.get(f) in (None, ""):
                warns.append(f"{n}: no {f}")
        if x.get("gate") in (None, ""):
            warns.append(f"{n}: no gate rule (say 'open' if anyone may pass)")
        print(f"[{n}] watch {x.get('watch', '?')} | bribe {x.get('bribe', '?')} | gate {x.get('gate', '?')} | "
              f"curfew {x.get('curfew', '?')} | owner {x.get('owner', '?')}")
    report([], warns, f"{len(ds)} district card(s)")


CHASE_COMPLICATIONS = [
    ("a cart blocks the lane", -1), ("a crowd thickens around a street preacher", -1),
    ("laundry lines drop across the alley", 0), ("a shortcut over a low roof", 1),
    ("a watch patrol turns the corner", -1), ("a dog pack bolts out of a yard", 0),
    ("a bridge choked with porters", -1), ("an open cellar door to dive through", 1),
    ("rain makes the cobbles slick", 0), ("a market stall to tip over behind you", 1),
]


def cmd_chase(a):
    """City pursuit: each round both sides roll d6, the higher moves the lead one step, then a complication shifts it."""
    import random
    rng = random.Random(a.seed)
    comps = CHASE_COMPLICATIONS
    if a.table:
        comps = []
        for line in Path(a.table).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            text, _, shift = line.partition(";")
            try:
                comps.append((text.strip(), int(shift) if shift.strip() else 0))
            except ValueError:
                die(f"bad shift in {line!r}; write 'text;-1'")
        if not comps:
            die("complication table is empty")
    if a.lead < 1 or a.escape <= a.lead:
        die("--lead at least 1 and --escape above it")
    lead = a.lead
    for rnd in range(1, a.rounds + 1):
        q, p = rng.randint(1, 6), rng.randint(1, 6)
        lead += (q > p) - (p > q)
        text, shift = rng.choice(comps)
        lead += shift
        print(f"round {rnd}: quarry {q} vs pursuer {p}; {text} ({shift:+d}); lead {lead}")
        if lead <= 0:
            print(f"caught in round {rnd}")
            return
        if lead >= a.escape:
            print(f"escaped in round {rnd}")
            return
    print(f"after {a.rounds} rounds the lead is {lead}: the quarry goes to ground; search or let them go")


TRAP_FIELDS = ("trigger", "detection", "disable", "effect")
TRAP_BANDS = ("setback", "dangerous", "deadly")


def load_list(path, key):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get(key, []) if isinstance(d, dict) else d
    if not d:
        die(f"no {key}")
    return d


def cmd_trap(a):
    """Traps JSON list: trigger, detection, disable, effect and a severity band each."""
    traps = load_list(a.file, "traps")
    errs = []
    for t in traps:
        n = t.get("name") or "?"
        for f in TRAP_FIELDS:
            if not t.get(f):
                errs.append(f"{n}: no {f}")
        if t.get("severity") not in TRAP_BANDS:
            errs.append(f"{n}: severity {t.get('severity')!r}, use {', '.join(TRAP_BANDS)}")
    warns = []
    deadly = [t for t in traps if t.get("severity") == "deadly"]
    if deadly and len(deadly) * 2 > len(traps):
        warns.append(f"{len(deadly)} of {len(traps)} traps are deadly; most should cost resources, not lives")
    report(errs, warns, f"{len(traps)} trap(s) with all four parts and a band")


def cmd_downtime(a):
    """Downtime activities JSON list: time cost and money cost or sink; repeatable ones need an outcome table."""
    acts = load_list(a.file, "activities")
    errs, warns = [], []
    for x in acts:
        n = x.get("name") or "?"
        if not x.get("time"):
            errs.append(f"{n}: no time cost")
        if not (x.get("cost") or x.get("sink")):
            errs.append(f"{n}: no cost or sink (money in, or where the money goes)")
        if x.get("repeatable") and not x.get("outcomes"):
            errs.append(f"{n}: repeatable with no outcomes table")
        if x.get("replaces_adventure"):
            warns.append(f"{n}: replaces adventuring; downtime should feed play, not stand in for it")
        if not x.get("hook"):
            warns.append(f"{n}: no hook (a lead the activity can turn up)")
    report(errs, warns, f"{len(acts)} downtime activit{'y' if len(acts) == 1 else 'ies'}")


ABSENT_PCS = {
    "collective": "the group shares one goal: absent PCs stay with the group as quiet background, take no risks and earn the same rewards",
    "competitive": "players pursue rival aims: absent PCs step out of the story (busy elsewhere) so nobody gains or loses ground while away",
    "individualist": "each PC follows a separate thread: pause the absent players' threads and play the present ones' own scenes",
}


def cmd_attendance(a):
    """Roster (JSON list, {"pcs": [...]}, or one name per line) and how many came; advice for absent PCs."""
    text = Path(a.roster).read_text(encoding="utf-8")
    try:
        d = json.loads(text)
        pcs = d.get("pcs", []) if isinstance(d, dict) else d
    except json.JSONDecodeError:
        pcs = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    n = len(pcs)
    if not n or not 0 <= a.present <= n:
        die(f"--present must be 0 to {n} (roster size)")
    print(f"{a.present} of {n} present")
    if a.present * 2 <= n:
        print("warn: half or fewer present; consider a side adventure, a one-shot, or moving the session")
    if a.present < n:
        print(f"absent PCs ({a.dynamic}): {ABSENT_PCS[a.dynamic]}")


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
            s.add_argument("--hazard", action="append", help="hazard level or CR; identical repeats count barely more than one")
            s.add_argument("--wave", action="append", help="reinforcements ROUND:COUNTxFOE[:removed_by]")
            s.add_argument("--pool", type=int, help="total defenders the waves can draw from")
            s.add_argument("--prep", action="append", help="a prep step the party finished; removes waves naming it")
            s.add_argument("--morale", help="when the foes retreat, e.g. half or 3")
            s.add_argument("--smart", action="store_true", help="the foes are intelligent")
            s.add_argument("--escape", help="the foes' way out")
        else:
            s.add_argument("--threat", default="moderate")
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=fn)
    t = sub.add_parser("tracker", help="initiative and HP tracker")
    t.add_argument("action", choices=["init", "add", "hit", "heal", "next", "late", "cond", "show"])
    t.add_argument("--timer", type=int, help="init: seconds per player turn; 'late' delays whoever runs out")
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
    s.add_argument("card"); s.add_argument("--finale", action="store_true")
    s.add_argument("--session", type=int, help="the current session number (default: the latest opened)")
    s.add_argument("--stale", type=int, default=3, help="flag open threads older than this many sessions")
    s.set_defaults(fn=cmd_threads)
    s = sub.add_parser("session-log", help="print a session log template that feeds the next prep card")
    s.add_argument("--session", type=int, default=1); s.set_defaults(fn=cmd_sessionlog)
    s = sub.add_parser("npcs", help="check three-line NPC cards")
    s.add_argument("card"); s.set_defaults(fn=cmd_npcs)
    s = sub.add_parser("world", help="check a setting card's traits")
    s.add_argument("card"); s.set_defaults(fn=cmd_world)
    s = sub.add_parser("fiveroom", help="check an adventure plan against the five-role arc")
    s.add_argument("plan"); s.set_defaults(fn=cmd_fiveroom)
    s = sub.add_parser("table", help="check a random encounter table CSV")
    s.add_argument("table", help="CSV, or 'combine' then 2 to 4 CSVs")
    s.add_argument("tables", nargs="*")
    s.add_argument("--max-fight", type=float, default=0.35)
    s.add_argument("--die", type=int, help="faces of the die the table is rolled on")
    s.add_argument("--seed", type=int); s.add_argument("--count", type=int, default=6)
    s.set_defaults(fn=cmd_table)
    s = sub.add_parser("mystery", help="check a mystery's clues and suspects")
    s.add_argument("file"); s.set_defaults(fn=cmd_mystery)
    s = sub.add_parser("safety", help="check a table safety plan")
    s.add_argument("file"); s.add_argument("--party", help="party.json; every PC's player must confirm")
    s.set_defaults(fn=cmd_safety)
    s = sub.add_parser("item", help="check magic items pair each boon with a drawback")
    s.add_argument("items"); s.set_defaults(fn=cmd_item)
    s = sub.add_parser("villain", help="check villain cards")
    s.add_argument("card"); s.set_defaults(fn=cmd_villain)
    s = sub.add_parser("twist", help="check a set of planned twists")
    s.add_argument("twists"); s.set_defaults(fn=cmd_twist)
    s = sub.add_parser("campaign", help="check a campaign plan")
    s.add_argument("plan"); s.add_argument("--signs", type=int, default=3, help="foreshadowing signs wanted per climax")
    s.set_defaults(fn=cmd_campaign)
    s = sub.add_parser("hooks", help="check a city hook deck")
    s.add_argument("deck"); s.set_defaults(fn=cmd_hooks)
    s = sub.add_parser("tavern", help="check a tavern or inn card")
    s.add_argument("card"); s.set_defaults(fn=cmd_tavern)
    s = sub.add_parser("venues", help="taverns, restaurants and inns for a population")
    s.add_argument("--population", type=int, required=True)
    for k in ("taverns", "restaurants", "inns"):
        s.add_argument("--" + k, type=int)
    s.add_argument("--anomaly", help="the story reason for an odd count")
    s.set_defaults(fn=cmd_venues)
    s = sub.add_parser("party", help="check PC ties, plot ties and plan B for reveals")
    s.add_argument("file"); s.set_defaults(fn=cmd_party)
    s = sub.add_parser("strength", help="average party level and party strength against the target")
    s.add_argument("levels", type=int, nargs="+"); s.add_argument("--target-level", type=int, required=True)
    s.add_argument("--target-size", type=int, default=5); s.set_defaults(fn=cmd_strength)
    s = sub.add_parser("loot", help="split gold and award permanent items")
    s.add_argument("file"); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_loot)
    s = sub.add_parser("reaction", help="roll an improvised NPC's first reaction")
    s.add_argument("--mod", type=int, action="append")
    s.add_argument("--approach", choices=["friendly", "neutral", "hostile"], default="neutral")
    s.add_argument("--roll", type=int); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_reaction)
    s = sub.add_parser("heat", help="faction standing and heat ledger")
    s.add_argument("action", choices=["show", "crime", "standing", "cool"]); s.add_argument("faction", nargs="?")
    s.add_argument("--file", default=str(Path(os.environ.get("TABLEWRIGHT_HOME") or Path.home() / ".tablewright") / "heat.json"))
    s.add_argument("--witnesses", type=int, default=0); s.add_argument("--by", type=int, default=1); s.add_argument("--why")
    s.set_defaults(fn=cmd_heat)
    s = sub.add_parser("premise", help="check an adventure premise card")
    s.add_argument("card"); s.set_defaults(fn=cmd_premise)
    s = sub.add_parser("wander", help="random-encounter clock and resolution steps")
    s.add_argument("--every", type=float, default=60, help="minutes between checks")
    s.add_argument("--chance", type=int, default=6, help="1 in N per check")
    s.add_argument("--hours", type=float, default=4); s.add_argument("--budget", type=float, default=2)
    s.add_argument("--feet", type=int, default=10, help="distance is 2d6 times this")
    s.add_argument("--surprise", type=int, default=3, help="each side is surprised on 1 in N")
    s.add_argument("--placed", action="append", help="area with a placed population")
    s.add_argument("--run", action="store_true"); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_wander)
    s = sub.add_parser("battle", help="a mass battle as three representative fights")
    s.add_argument("plan"); s.add_argument("--results", help="outcome of each fight in order: won,lost,drawn")
    s.set_defaults(fn=cmd_battle)
    s = sub.add_parser("review", help="merge highlights and weak points from session logs per player")
    s.add_argument("logs", nargs="+"); s.set_defaults(fn=cmd_review)
    s = sub.add_parser("houserules", help="check a house rules list")
    s.add_argument("file"); s.set_defaults(fn=cmd_houserules)
    s = sub.add_parser("challenge", help="check a skill challenge or long task card")
    s.add_argument("card"); s.set_defaults(fn=cmd_challenge)
    s = sub.add_parser("travel", help="days and fatigue for an overland trip")
    s.add_argument("--miles", type=float, required=True)
    s.add_argument("--pace", type=float, default=24, help="miles per day on open road")
    s.add_argument("--terrain", default="road", help=", ".join(TERRAIN))
    s.add_argument("--hours", type=float, default=8, help="hours marched per day")
    s.add_argument("--known", action="store_true", help="the route is known (a guide or a map)")
    s.set_defaults(fn=cmd_travel)
    s = sub.add_parser("calendar", help="world-day ledger for split groups")
    s.add_argument("file"); s.add_argument("--drift", type=int, default=3, help="warn when groups are this many days apart")
    s.set_defaults(fn=cmd_calendar)
    s = sub.add_parser("hirelings", help="hireling loyalty and loyalty checks")
    s.add_argument("file"); s.add_argument("--roll", help="hireling to check"); s.add_argument("--event")
    s.add_argument("--seed", type=int); s.add_argument("--die", type=int, help="use this d100 result")
    s.set_defaults(fn=cmd_hirelings)
    s = sub.add_parser("district", help="check city district prep cards")
    s.add_argument("file"); s.set_defaults(fn=cmd_district)
    s = sub.add_parser("chase", help="city pursuit tracker")
    s.add_argument("--lead", type=int, default=3); s.add_argument("--escape", type=int, default=6)
    s.add_argument("--rounds", type=int, default=10); s.add_argument("--table", help="file of 'complication;shift' lines")
    s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_chase)
    s = sub.add_parser("attendance", help="who came and what to do with absent PCs")
    s.add_argument("roster"); s.add_argument("--present", type=int, required=True)
    s.add_argument("--dynamic", choices=list(ABSENT_PCS), default="collective")
    s.set_defaults(fn=cmd_attendance)
    s = sub.add_parser("trap", help="check traps: trigger, detection, disable, effect, severity")
    s.add_argument("file"); s.set_defaults(fn=cmd_trap)
    s = sub.add_parser("downtime", help="check downtime activities: time, cost or sink, outcomes")
    s.add_argument("file"); s.set_defaults(fn=cmd_downtime)
    s = sub.add_parser("licence", help="notices for the bundled tables")
    s.set_defaults(fn=lambda a: print(LICENCE))
    a = p.parse_args(argv)
    if isinstance(getattr(a, "party", None), int) and a.party < 1:
        die("party must be at least 1")
    a.fn(a)


if __name__ == "__main__":
    main()
