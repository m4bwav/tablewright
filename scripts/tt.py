#!/usr/bin/env python3
"""tablewright CLI: tabletop RPG table work, standard library only.

Commands:
  encounter   XP total and threat band of a planned fight (pf2e, sf2e, 5e)
  budget      XP to spend for a threat, with example foe mixes
  tracker     initiative and HP tracker kept in a JSON file
  sheet       character JSON (common schema) to a one-page markdown sheet
  check       check a character JSON against the common schema
  licence     notices for the bundled rules tables

Exit 2 is a usage or validation error.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Pathfinder 2e and Starfinder 2e (ORC): creature XP by level minus party level, budgets for 4 players.
PF_XP = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120, 4: 160}
PF_BUDGET = {"trivial": 40, "low": 60, "moderate": 80, "severe": 120, "extreme": 160}
PF_ADJUST = {"trivial": 10, "low": 20, "moderate": 20, "severe": 30, "extreme": 40}

# D&D 5e 2024 (SRD 5.2, CC-BY-4.0): XP budget per character by level, and XP by challenge rating.
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

LICENCE = """Pathfinder 2e and Starfinder 2e encounter tables: game mechanics under the ORC License
(Paizo, Pathfinder Player Core / Starfinder Player Core encounter building rules).
D&D 2024 encounter tables: System Reference Document 5.2 by Wizards of the Coast LLC,
licensed under CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/).
tablewright bundles numbers only, no rules text, creatures or art."""

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
        res["notes"].append("over the High budget: deadly for this party")
    if a.system != "5e" and total > budgets["extreme"]:
        res["notes"].append("over the Extreme budget")
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
    sys.exit(1 if bad else 0)


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


def show(d):
    print(f"round {d['round']}")
    for i, c in enumerate(d["order"]):
        mark = ">" if i == d["turn"] else " "
        conds = (" [" + ", ".join(c["conditions"]) + "]") if c["conditions"] else ""
        state = " DOWN" if c["hp"] <= 0 else ""
        print(f"{mark} {c['init']:>3} {c['name']:<16} {c['hp']}/{c['max_hp']}{state}{conds}")


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
    show(d)


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
        else:
            s.add_argument("--threat", default="moderate")
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=fn)
    t = sub.add_parser("tracker", help="initiative and HP tracker")
    t.add_argument("action", choices=["init", "add", "hit", "heal", "next", "cond", "show"])
    t.add_argument("args", nargs="*")
    t.add_argument("--file", default=str(Path(os.environ.get("TABLEWRIGHT_HOME") or Path.home() / ".tablewright") / "tracker.json"))
    t.add_argument("--remove", action="store_true")
    t.set_defaults(fn=cmd_tracker)
    s = sub.add_parser("sheet", help="character JSON to markdown sheet")
    s.add_argument("character"); s.add_argument("--out"); s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("check", help="check a character JSON")
    s.add_argument("character"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("licence", help="notices for the bundled tables")
    s.set_defaults(fn=lambda a: print(LICENCE))
    a = p.parse_args(argv)
    if getattr(a, "party", 1) < 1:
        die("party must be at least 1")
    a.fn(a)


if __name__ == "__main__":
    main()
