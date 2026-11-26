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
  oneshot     check a one-shot card (bond, plot, finish, pregens with stakes)
  tpk         remedy after a total party kill, by cause
  alert       dungeon alert track (init, raise, lower, show)
  backlog     check a campaign hook backlog (5 to 15 open, worsens, ties)
  negotiate   multi-step negotiation, one attitude step per exchange
  spell       spell cost (tier x power) and homebrew spell checks
  rewards     check a reward ladder (cadence, triggers, gates)
  vendors     vendor tiers, reach and prices as days of wage
  mob         mob members dropped by big hits; left or routed
  hack        hacking difficulty from system and modifiers
  settlement  check a settlement card (size band, civic kit, function)
  favor       seeded favor request by relation and risk
  xp          foe and story XP award split among survivors
  morale      2d10 morale check against a modified rating
  awards      per-player awards, milestones and coins across session logs
  rooms       check rooms (timer, threat, treat, stake, wonder, dials)
  session-end rounds left and final turns in seat order
  resize      add or cut foes for a different party size
  target      pick a monster's target (marked, threat, reach, roll)
  playtest    check a blind playtest log
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
    for spec in a.throng or []:
        cnt, _, crowd = spec.partition("x")
        if not cnt.isdigit() or not crowd:
            die(f"bad throng {spec!r} (use COUNTxFOE: COUNT weak foes fought as one crowd of level or CR FOE)")
        xp, note = foe_xp(a.system, crowd, a.level)
        total += xp or 0
        notes.append(f"throng {spec}: {cnt} weak foes count as one crowd, {xp or 0} XP" + (f" ({note})" if note else ""))
    haz_xp, haz_notes = hazard_xp(a.system, a.hazard or [], a.level)
    total += haz_xp
    notes += haz_notes
    waves, wave_xp, wave_warns = plan_waves(a)
    counted = count_foes(a)
    deadly = "high" if a.system == "5e" else "extreme"
    for spec, lo, mean, hi in counted:
        notes.append(f"count {spec}: {lo} / {mean:g} / {hi} XP (min / mean / max) on top of {total}")
        if total + hi > budgets[deadly]:
            notes.append(f"count {spec}: the max roll ({total + hi} XP) is over the {deadly.title()} budget; cap the count")
    if counted:
        total += sum(round(m) for _, _, m, _ in counted)
    band = band_for(total, budgets)
    nxt =[(k, v) for k, v in sorted(budgets.items(), key=lambda kv: kv[1]) if v > total]
    res = {"system": a.system, "party": a.party, "level": a.level, "xp": total, "threat": band,
           "budgets": budgets, "next": {"threat": nxt[0][0], "xp_needed": nxt[0][1] - total} if nxt else None, "notes": notes}
    if a.system == "5e" and total > budgets["high"]:
        res["notes"].append("above the High budget (2024 has no higher band): expect a character to drop")
    if a.system != "5e" and total > budgets["extreme"]:
        res["notes"].append("over the Extreme budget")
    res["warnings"] = mission_warnings(a) + wave_warns + role_warnings(roles, len(a.foe)) + solo_horde_warnings(a)
    if total > budgets[deadly] and not a.exit:
        res["warnings"].append(f"above {deadly.title()} with no --exit: name the way out (retreat, safe room, parley)")
    if roles:
        res["roles"] = roles
    if waves:
        res["waves"] = waves
        res["xp_with_waves"] = total + wave_xp
        res["threat_with_waves"] = band_for(total + wave_xp, budgets)
        notes.append(f"with reinforcements: {total + wave_xp} XP, threat {res['threat_with_waves']}")
    if a.protect:
        res["protect"] = protect_rounds(a.protect, a.attackers)
        for o in res["protect"]:
            notes.append(f"protect {o['object']} #{o['n']}: breaks in round {o['round']} ({o['hp']} HP)")
    if a.waves:
        day = total + wave_xp
        cap = budgets["moderate"] * DAY_FIGHTS
        res["day_xp"], res["day_budget"] = day, cap
        notes.append(f"waves as one no-rest fight: {day} XP against a day budget of {cap} ({DAY_FIGHTS} x moderate)")
        if day > cap:
            res["warnings"].append(f"waves total {day} XP with no rest, over the day budget of {cap}; cut a wave or allow a breather")
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


DAY_FIGHTS = 3  # a no-rest day's budget in moderate fights; our number


def protect_rounds(spec, attackers):
    """OBJ:COUNT:HP objects hit one at a time by N attackers doing DMG each, no rolls: the round each one breaks."""
    try:
        obj, cnt, hp = spec.split(":")
        cnt, hp = int(cnt), int(hp)
        n, dmg = (int(x) for x in (attackers or "").split(":"))
    except ValueError:
        die("--protect OBJ:COUNT:HP wants --attackers N:DMG, e.g. --protect pillar:3:20 --attackers 4:6")
    if min(cnt, hp, n, dmg) < 1:
        die("--protect and --attackers numbers must be 1 or more")
    hits = -(-hp // dmg)
    return [{"object": obj, "n": i, "hp": hp, "round": -(-(i * hits) // n)} for i in range(1, cnt + 1)]


HORDE = 12  # more single foes than this at once bog the table down; our number
HORDE_WAVE = 8


def solo_horde_warnings(a):
    """--solo needs tactics, a fallback and terrain; a horde over HORDE foes with no --wave should come in waves."""
    w = []
    if a.solo:
        for flag, why in (("tactics", "what the solo does each round"), ("fallback", "what it does when hurt or cornered"),
                          ("terrain", "the ground it uses")):
            if not getattr(a, flag):
                w.append(f"solo with no --{flag}: {why}; a lone foe with only attacks folds to action economy")
    if (a.spike or a.boss_dpr) and not a.pc_hp:
        w.append("--spike with no --pc-hp: give the lowest PC's full HP")
    for sp in a.spike or []:
        if a.pc_hp and sp >= a.pc_hp:
            w.append(f"a foe's burst of {sp} can drop a PC from full ({a.pc_hp} HP) in one turn; cut it or telegraph it")
    if a.boss_dpr and a.pc_hp and a.boss_dpr >= a.pc_hp:
        w.append(f"boss all-hit damage {a.boss_dpr} a round kills the lowest PC ({a.pc_hp} HP) in one round;"
                 " give healing, temp HP or a buffer before the fight")
    if len(a.foe) > HORDE and not a.wave:
        w.append(f"{len(a.foe)} foes at once with no --wave: send waves of about {HORDE_WAVE} with a breather between,"
                 " or fold weak ones into a --throng")
    return w


def pc_hp_arg(v):
    """'24' or '24,31,40' -> the lowest PC's full HP."""
    try:
        return min(int(x) for x in v.split(",") if x.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(f"--pc-hp wants a number or a,b,c, got {v!r}")


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
        conds += "".join(f" ({e['name']} {e['rounds']}r)" for e in c.get("effects", []))
        conds += "".join(f" ({x['name']} stage {x['stage'] + 1}/{len(x['stages'])})" for x in c.get("poisons", []))
        state = " DOWN" if c["hp"] <= 0 else ""
        hp = f"took {c['max_hp'] - c['hp']}" if public else f"{c['hp']}/{c['max_hp']}"
        print(f"{mark} {c['init']:>3} {c['name']:<16} {hp}{state}{conds}")
    for c in d.get("clocks", []):
        print(f"clock {c['name']}: {c['left']} {c['unit']}(s) left" + (f" ({c['owner']})" if c.get("owner") else ""))


def tick_effects(d):
    """A new round: every effect loses a round; at 0 it ends and is logged."""
    for c in d["order"]:
        keep = []
        for e in c.get("effects", []):
            e["rounds"] -= 1
            if e["rounds"] > 0:
                keep.append(e)
            else:
                d["log"].append(f"r{d['round']} {c['name']}: {e['name']} ended")
                print(f"{c['name']}: {e['name']} ended")
        if "effects" in c:
            c["effects"] = keep


def tick_poisons(d):
    """A new round: each poison's interval counts down; at 0 it moves to its next stage, past the last it ends."""
    for c in d["order"]:
        keep = []
        for x in c.get("poisons", []):
            x["left"] -= 1
            if x["left"] <= 0:
                x["stage"] += 1
                x["left"] = x["every"]
                if x["stage"] >= len(x["stages"]):
                    d["log"].append(f"r{d['round']} {c['name']}: {x['name']} ran its course")
                    print(f"{c['name']}: {x['name']} ran its course")
                    continue
                print(f"{c['name']}: {x['name']} stage {x['stage'] + 1}: {x['stages'][x['stage']]} (save again{dc_text(x)})")
            elif x.get("save_each"):
                print(f"{c['name']}: {x['name']} save again{dc_text(x)} (each round)")
            keep.append(x)
        if "poisons" in c:
            c["poisons"] = keep


def dc_text(x):
    return f", DC {x['dc']}" if x.get("dc") else ""


def tick_owner(d, name):
    """A countdown die turns down one on its owner's turn; at 0 it fires."""
    for c in d.get("clocks", []):
        if c["unit"] == "owner" and c.get("owner") == name:
            c["left"] -= 1
            if c["left"] > 0:
                print(f"countdown {c['name']}: {c['left']} on the die")
    tick_clocks(d, None)


def tick_clocks(d, unit):
    """unit turn or round: those clocks lose one; None only reports. A clock at 0 fires and is removed."""
    keep = []
    for c in d.get("clocks", []):
        if unit and c["unit"] == unit:
            c["left"] -= 1
        if c["left"] <= 0:
            d["log"].append(f"r{d['round']} clock {c['name']} fires")
            print(f"clock {c['name']} fires")
        else:
            keep.append(c)
    if "clocks" in d:
        d["clocks"] = keep


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
                    tick_effects(d)
                    tick_poisons(d)
                    tick_clocks(d, "round")
                if d["order"][i]["hp"] > 0:
                    break
            d["turn"] = i
            tick_clocks(d, "turn")
            tick_owner(d, d["order"][i]["name"])
        elif a.action == "clock":
            if a.args and a.args[0] == "tick":
                names = a.args[1:] or [c["name"] for c in d.get("clocks", [])]
                for n in names:
                    c = next((c for c in d.get("clocks", []) if c["name"].lower() == n.lower()), None)
                    if not c:
                        die(f"no clock named {n}")
                    c["left"] -= 2 if a.fail else 1
                tick_clocks(d, None)
            elif len(a.args) == 2:
                try:
                    n = int(a.args[1])
                except ValueError:
                    die("clock NAME N")
                d.setdefault("clocks", []).append({"name": a.args[0], "left": n, "unit": a.unit})
            else:
                die("clock NAME N --unit turn|round, or clock tick [NAME] [--fail]")
        elif a.action == "poison":
            if a.args[:1] == ["cure"] and len(a.args) >= 2:
                c = find(d, a.args[1])
                c["poisons"] = [x for x in c.get("poisons", []) if len(a.args) > 2 and x["name"].lower() != a.args[2].lower()]
                d["log"].append(f"r{d['round']} {c['name']} cured")
            elif len(a.args) in (3, 4):
                c = find(d, a.args[0])
                stages = [x.strip() for x in a.args[2].split(",") if x.strip()]
                try:
                    every = int(a.args[3]) if len(a.args) == 4 else 1
                except ValueError:
                    die("poison interval must be a number of rounds")
                if not stages or every < 1:
                    die("poison needs stages a,b,c and an interval of 1 or more rounds")
                x = {"name": a.args[1], "stages": stages, "stage": 0, "every": every, "left": every}
                if a.save_each:
                    x["save_each"] = True
                if a.dc:
                    x["dc"] = a.dc + POTENCY.get(a.potency, 0)
                elif a.potency:
                    die("--potency needs --dc")
                c.setdefault("poisons", []).append(x)
                print(f"{c['name']}: {a.args[1]} stage 1: {stages[0]}{dc_text(x)}")
            else:
                die("poison NAME POISON STAGE1,STAGE2,... [INTERVAL_ROUNDS], or poison cure NAME [POISON]")
        elif a.action == "countdown":
            if len(a.args) != 2 or not a.owner:
                die("countdown NAME dN --owner COMBATANT")
            try:
                n = int(a.args[1].lstrip("dD"))
            except ValueError:
                die("countdown die as dN, e.g. d6")
            owner = find(d, a.owner)["name"]
            d.setdefault("clocks", []).append({"name": a.args[0], "left": n, "unit": "owner", "owner": owner})
        elif a.action == "cond":
            if len(a.args) < 2:
                die("cond NAME CONDITION [--remove]")
            c = find(d, a.args[0])
            cond = " ".join(a.args[1:])
            if a.remove:
                c["conditions"] = [x for x in c["conditions"] if x != cond]
            elif cond not in c["conditions"]:
                c["conditions"].append(cond)
        elif a.action == "effect":
            if len(a.args) < 3:
                die("effect NAME EFFECT ROUNDS")
            c = find(d, a.args[0])
            try:
                n = int(a.args[-1])
            except ValueError:
                die("effect rounds must be a number")
            if n < 1:
                die("effect rounds must be at least 1")
            c.setdefault("effects", []).append({"name": " ".join(a.args[1:-1]), "rounds": n})
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
FAIL_KINDS = ("time", "alarm", "clock", "cost", "complication")
MEMENTOS = ("clue", "loss", "gain", "plea", "curse", "known-foe")


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
    for x in items + bullets("obstacles"):
        if tag(x, "roll"):
            of = tag(x, "on_fail")
            if not of:
                warns.append(f"one roll gates progress with no on_fail: (time, alarm, clock, cost or complication): {x}")
            elif of.split()[0].strip(",.") not in FAIL_KINDS:
                warns.append(f"on_fail: {of}; a failure should move play: " + ", ".join(FAIL_KINDS))
    fights = bullets("fights")
    if fights and not any(tag(f, "memento") for f in fights):
        warns.append("no fight leaves a memento: (" + ", ".join(MEMENTOS) + "); give one fight something to remember")
    for f in fights:
        m = tag(f, "memento")
        if m and m.split()[0].strip(",.") not in MEMENTOS:
            warns.append(f"memento: {m}, use " + ", ".join(MEMENTOS))
    for n in npcs:
        if tag(n, "opposed") in YES or tag(n, "foe") in YES:
            places = [p for p in tag(n, "where").replace("|", ",").split(",") if p.strip()]
            if len(places) < 2:
                warns.append(f"opposing NPC found in {len(places)} place(s); give two or more (where: a, b) "
                             f"so the party can meet them whichever way they go: {n}")
    if "rooms" in sec or "dungeon" in sec:
        rest = bullets("rest")
        if not rest:
            warns.append("dungeon card with no ## Rest: say where the party can rest (where:) and what it costs (cost:)")
        elif not any("where:" in r.lower() for r in rest) or not any("cost:" in r.lower() for r in rest):
            warns.append("## Rest wants a where: line and a cost: line (a clock, an alarm or a spent resource)")
    if a.hours:
        rate = 0.75 if a.learning else 1.0
        if len(fights) > a.hours * rate:
            warns.append(f"{len(fights)} fights in {a.hours:g} h; about {rate:g} an hour fits (our default, from 4e grid play)")
    if a.first:
        for k in ("prologue", "intros"):
            if not sec.get(k):
                errs.append(f"first session with no ## {k.title()}")
        if not any("bond:" in l.lower() for l in sec.get("intros", [])):
            errs.append("first session: no bond: line in ## Intros (why these PCs travel together)")
    elif a.hours and not sec.get("recap"):
        warns.append("no ## Recap: open a later session with what happened last time")
    prep_flow(bullets("flow"), errs, warns)
    prep_scenes(sec, a, errs, warns)
    threads = [tag(n, "thread") for n in npcs if tag(n, "thread")]
    if players and threads:
        for pl in players:
            if not any(t.startswith("for") and pl.lower() in t[3:].replace(",", " ").split() for t in threads):
                warns.append(f"{pl} has no NPC thread (tag an NPC 'thread: for {pl}')")
    import re
    m = re.search(r"^hours:\s*([\d.]+)", Path(a.card).read_text(encoding="utf-8"), re.M | re.I)
    hours = float(m.group(1)) if m else a.hours
    breaks = bullets("break")
    if hours and hours >= 4 and not breaks:
        warns.append(f"{hours:g} h session with no ## Break (at: hour; goal_check: fallback ending)")
    for b in breaks:
        if not tag(b, "goal_check"):
            warns.append(f"break with no goal_check: (where the night ends if time runs short): {b}")
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


SCENE_KEYS = ("purpose", "closing", "type", "victory", "failure", "rules", "description", "dialog", "weather", "time",
              "tactics", "names", "stats", "treasure", "from", "next", "bypass")
RULES_WORDS = r"\b(water|ice|fall|falls|falling|fire|poison|poisoned|grapple|grappled|chase)\b"
BYPASS = {"flight": ("flight", "fly", "flying"), "teleport": ("teleport", "dimension door", "misty step"),
          "scrying": ("scry", "scrying", "clairvoyance")}
REVIEW_PASSES = ("proofreader", "director", "playtester")
REVIEW_DROP = ("proofreader", "playtester", "director")  # cut first to last when time runs short


def parse_scenes(lines):
    """'### Title' sub-sections of ## Scenes; 'key: value' lines (bullets too) become fields."""
    scenes = []
    for l in lines:
        if l.startswith("### "):
            scenes.append({"title": l[4:].strip(), "f": {}, "text": []})
        elif scenes:
            body = l[2:].strip() if l[:2] in ("- ", "* ") else l
            k, _, v = body.partition(":")
            if k.strip().lower() in SCENE_KEYS and v.strip():
                scenes[-1]["f"][k.strip().lower()] = v.strip()
            scenes[-1]["text"].append(body)
    return scenes


def prep_scenes(sec, a, errs, warns):
    import re
    scenes = parse_scenes(sec.get("scenes", []))
    if not scenes:
        if a.review:
            errs.append("--review needs ## Scenes with ### Title sub-sections")
        return
    sess = " ".join(sec.get("session", [])).lower()
    for k in ("purpose", "closing"):
        if f"{k}:" not in sess:
            errs.append(f"## Scenes with no session {k}: under ## Session")
    weak = [x.strip() for x in (a.weak or "").split(",") if x.strip()]
    strong = [x.strip() for x in (a.strong or "").split(",") if x.strip()]
    for i, sc in enumerate(scenes):
        t, f = sc["title"], sc["f"]
        p = f.get("purpose")
        if not p:
            errs.append(f"scene {t}: no purpose: (what it is for)")
        elif len([x for x in re.split(r"[.!?]+", p) if x.strip()]) > 1:
            warns.append(f"scene {t}: purpose has more than one sentence; split the scene")
        if not f.get("closing"):
            warns.append(f"scene {t}: no closing: (how you know it is over)")
        if f.get("type", "").lower() == "combat":
            for k in ("victory", "failure"):
                if not f.get(k):
                    warns.append(f"scene {t}: combat with no {k}:")
        for k in weak:
            if not f.get(k):
                warns.append(f"scene {t}: no {k}: (a weak spot you listed in --weak)")
        for k in strong:
            if len(f.get(k, "").split()) > 40:
                warns.append(f"scene {t}: {k} runs over 40 words; you are strong there, write less")
        body = " ".join(sc["text"]).lower()
        if not f.get("rules") and re.search(RULES_WORDS, body):
            warns.append(f"scene {t}: mentions {re.search(RULES_WORDS, body).group(1)} with no rules: line; note the rule and page")
    if a.review:
        prep_review(scenes, a, warns)


def prep_review(scenes, a, warns):
    print("review passes, run separately: " + ", ".join(REVIEW_PASSES))
    if a.short:
        print("short on time, drop in this order: " + ", ".join(REVIEW_DROP) + " (director last)")
    for sc in scenes:
        f = sc["f"]
        if f.get("type", "").lower() == "combat" and not f.get("stats"):
            warns.append(f"proofreader: scene {sc['title']}: foes with no stats:")
        if "treasure" in [x.split(":", 1)[0].strip().lower() for x in sc["text"]] and not f.get("treasure") or \
                f.get("treasure", "").lower() in ("tbd", "?", "todo"):
            warns.append(f"proofreader: scene {sc['title']}: treasure not filled in")
    for prev, sc in zip(scenes, scenes[1:]):
        linked = prev["title"].lower() in sc["f"].get("from", "").lower() or sc["title"].lower() in prev["f"].get("next", "").lower()
        if not linked:
            warns.append(f"director: scene {sc['title']} is not linked from {prev['title']} (add from: or next:)")
    for path in a.party or []:
        c = load_char(path)
        blob = json.dumps(c).lower()
        for power, words in BYPASS.items():
            if any(w in blob for w in words):
                open_ = [sc["title"] for sc in scenes if not sc["f"].get("bypass")]
                if open_:
                    warns.append(f"playtester: {c.get('name', path)} has {power}; could it skip "
                                 + ", ".join(open_) + "? add bypass: to each")


def prep_flow(lines, errs, warns):
    """## Flow bullets '- id: text -> a, b; rules: chase, social'. start and finish required."""
    if not lines:
        return
    nxt, rules = {}, {}
    for l in lines:
        sid, _, rest = l.partition(":")
        sid = sid.strip().lower()
        parts = rest.split(";")
        _, arrow, tgt = parts[0].partition("->")
        nxt[sid] = [t.strip().lower() for t in tgt.split(",") if t.strip()] if arrow else []
        for r in (x.strip() for x in tag(rest, "rules").split(",") if x.strip()):
            rules.setdefault(r, []).append(sid)
    for k in ("start", "finish"):
        if k not in nxt:
            errs.append(f"## Flow has no {k} scene")
    for sid, ts in nxt.items():
        for t in ts:
            if t not in nxt:
                errs.append(f"flow: {sid} leads to unknown scene {t}")
    if "start" not in nxt or "finish" not in nxt:
        return

    def reach(src, edges):
        seen, todo = set(), [src]
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo += edges.get(x, [])
        return seen
    back = {}
    for sid, ts in nxt.items():
        for t in ts:
            back.setdefault(t, []).append(sid)
    fwd, rev = reach("start", nxt), reach("finish", back)
    for sid in sorted(fwd - rev):
        errs.append(f"flow: {sid} is reachable from start but cannot reach finish (a dead end)")
    for sid in sorted(set(nxt) - {"start"} - set(back)):
        errs.append(f"flow: nothing leads to {sid}")

    def paths(x, seen):
        if x == "finish":
            return 1
        return sum(paths(t, seen | {t}) for t in nxt.get(x, []) if t in nxt and t not in seen)
    n = paths("start", {"start"})
    if n == 1:
        warns.append("flow has one path from start to finish; add a second route so choices matter")
    print(f"flow: {len(nxt)} scenes, {n} path(s) start to finish")
    for r, ids in sorted(rules.items()):
        print(f"rules cheat sheet: {r} ({', '.join(ids)})")


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
    pr = [l for l in sec.get("principles", []) if l[:2] in ("- ", "* ")]
    if "principles" in sec and not 3 <= len(pr) <= 7:
        print(f"warn: ## Principles has {len(pr)}, want 3 to 7")
    for l in (l[2:].strip() for l in sec.get("locations", []) if l[:2] in ("- ", "* ")):
        name, _, rest = l.partition(":")
        parts = [x.strip() for x in rest.split(";") if x.strip()]
        det = [x for x in parts if not x.lower().startswith("weather:")]
        if not 3 <= len(det) <= 5:
            print(f"warn: location {name.strip()}: {len(det)} details, want 3 to 5")
        if len(det) == len(parts):
            print(f"warn: location {name.strip()}: no weather:")
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

## Learned
- Player: a; b; c

## Next opening
- where the next session starts
- ending: countdown | hook | choice | ran-long (how this session stopped)
- ended_mid_fight: no
- snapshot: (if mid-fight: positions, HP, effects, initiative)
- restart: (if mid-fight: the line that starts the next session)
- recap: two lines read aloud to open next session
"""
ENDINGS = ("countdown", "hook", "choice", "ran-long")


def cmd_sessionlog(a):
    """A session log in prep-card markdown; its ## Threads feed 'tt.py threads'."""
    print(SESSION_LOG.format(n=a.session), end="")


NPC_DEPTH = ("ideal", "bond", "flaw")
NPC_EXTRA = ("major", "secret", "joins_party", "exit", "tactics", "but", "roles", "tell", "revealed")


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
                 for p in parts if ":" in p and p.split(":", 1)[0].strip().lower() in NPC_DEPTH + NPC_EXTRA}
        parts = [p for p in parts if not (":" in p and p.split(":", 1)[0].strip().lower() in extra)]
        if extra.get("major", "").lower() in ("true", "yes"):
            for k in NPC_DEPTH:
                if not extra.get(k) and not (k == "flaw" and extra.get("secret")):
                    errs.append(f"{name.strip()}: major NPC with no {k}" + (" or secret" if k == "flaw" else ""))
        if extra.get("joins_party", "").lower() in ("true", "yes") and not extra.get("exit"):
            print(f"warn: {name.strip()}: joins the party with no exit: (how and when they leave so the PCs stay the heroes)")
        if extra.get("tactics") and "flee" not in extra["tactics"].lower():
            print(f"warn: {name.strip()}: tactics with no flee (the HP fraction where they run, e.g. flee 1/3)")
        if extra.get("secret") and not extra.get("tell"):
            print(f"warn: {name.strip()}: secret with no tell: (players cannot discover it)")
        if extra.get("secret") and not extra.get("revealed"):
            print(f"warn: {name.strip()}: secret with no revealed: (what changes when it comes out)")
        roles = [x for x in extra.get("roles", "").replace("|", ",").split(",") if x.strip()]
        if extra.get("major", "").lower() in ("true", "yes") and len(roles) < 2:
            print(f"warn: {name.strip()}: major NPC with {len(roles)} roles:, give 2+ so they stay useful (e.g. roles: fence, informant)")
        if getattr(a, "but", False) and not extra.get("but") and " but " not in f" {' '.join(parts).lower()} ":
            print(f"warn: {name.strip()}: no contradiction; add a 'but' to the look, activity or hook, or a but: field")
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
        if str(x.get("dynamic", "")).lower() in ("yes", "true"):
            for k, why in (("response", "what happens when the alarm goes up"), ("plan", "what the occupants do if left alone")):
                if not x.get(k):
                    warns.append(f"area {n}: dynamic with no {k} ({why})")
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
        if not key("escape") and [v.lower() for v in key("captured_ok")] != ["true"]:
            warns.append(f"{name}: no escape: (how they avoid capture, planned before the showdown); "
                         "or 'captured_ok: true' if capture is a fine ending")
        if not key("absent"):
            warns.append(f"{name}: no absent: (what they do if the party never comes for them)")
        where = [p for w in key("where") for p in w.replace("|", ",").split(",") if p.strip()]
        dd = key("drive_die")
        if dd:
            import re
            m = re.fullmatch(r"d(\d+)", dd[0].lower())
            if not m:
                die(f"{name}: drive_die {dd[0]!r}, use dN")
            nums = sorted(int(x.split(".", 1)[0]) for x in (l.strip() for l in lines) if re.match(r"\d+\.\s", x))
            if nums != list(range(1, int(m.group(1)) + 1)):
                die(f"{name}: drive_die {dd[0]} wants actions numbered 1 to {m.group(1)}, found {nums}")
        goals, meets = key("goal"), key("meet")
        if goals:
            for g in goals:
                if not any(g.lower() in m.lower() for m in meets):
                    warns.append(f"{name}: goal {g!r} has no meet: line naming it (where the party runs into it)")
            if len(meets) < 3:
                warns.append(f"{name}: {len(meets)} meet: lines before the showdown, want 3+ so the villain is known before the fight")
        if key("where") and len(where) < 2:
            warns.append(f"{name}: met in one place only; give two or more (where: a, b) so a missed scene is not a lost villain")
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
    for i, x in enumerate(adv):
        n = x.get("name", f"#{i + 1}")
        if i and not x.get("link"):
            warns.append(f"{n}: no link: (what sends the party here from the last adventure)")
        lv, pl = x.get("level"), x.get("party_level", c.get("party_level"))
        if isinstance(lv, int) and isinstance(pl, int) and lv - pl >= 2 and x.get("warned") is not True:
            warns.append(f"{n}: level {lv} is {lv - pl} above the party (level {pl}) with no warned: true (a sign it is too deadly yet)")
    if len(adv) > 1 and not c.get("guide"):
        warns.append("no guide: (a person, omen or rumour source that nudges the party to the next adventure)")
    if c.get("motif") and adv:
        hit = sum(1 for x in adv if c["motif"] in x.get("beats", []))
        if hit * 3 < len(adv):
            warns.append(f"motif {c['motif']!r} is in the beats of {hit} of {len(adv)} adventures, want a third or more")
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
    ms = c.get("milestones", [])
    if ms:
        at = (cl or {}).get("session")
        seen = {}
        for m in ms:
            k, s = m.get("kind"), m.get("session")
            if k not in MILESTONES:
                errs.append(f"milestone kind {k!r}, use " + ", ".join(MILESTONES))
                continue
            if not isinstance(s, int):
                errs.append(f"milestone {k}: no session")
                continue
            seen[k] = s
            if isinstance(at, int) and s >= at:
                errs.append(f"milestone {k} at session {s} is not before the climax (session {at})")
        order = [k for k in MILESTONES if k in seen]
        for x, y in zip(order, order[1:]):
            if seen[x] >= seen[y]:
                errs.append(f"milestone {y} (session {seen[y]}) should come after {x} (session {seen[x]})")
        for k in MILESTONES:
            if k not in seen:
                warns.append(f"no {k} milestone")
    org = c.get("org")
    if org:
        if len(org.get("minions", [])) < 4:
            warns.append(f"org has {len(org.get('minions', []))} minion types, want 4+ so fights vary")
        for sg in org.get("sergeants", []):
            if not sg.get("plan"):
                warns.append(f"sergeant {sg.get('name', '?')}: no plan of their own")
        if not org.get("sergeants"):
            warns.append("org has no sergeants (mid-level leaders with their own plans)")
    if c.get("travel") == "unlimited" and not c.get("travel_limit"):
        errs.append("travel: unlimited with no travel_limit (what still costs or stops a jump)")
    if "nemesis" in c or "travel" in c:
        nem = c.get("nemesis")
        roster = c.get("roster") or c.get("pcs") or []
        if not nem:
            warns.append("no nemesis (a foe tied to one PC)")
        elif roster and nem.get("pc") not in roster:
            warns.append(f"nemesis {nem.get('name', '?')} is not tied to a roster PC")
    report(errs, warns, f"{len(adv)} adventures, {len(c.get('pcs', []))} PCs with plotlines")


MILESTONES = ("discovery", "reversal", "change_in_view")


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


PARTY_ENTRY = ("happenstance", "rescued", "remnant", "errand")


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
        e = p.get("entry")
        if e and e not in PARTY_ENTRY:
            errs.append(f"{n}: entry {e!r}, use {', '.join(PARTY_ENTRY)}")
        elif p.get("joined_mid") and not e:
            warns.append(f"{n}: joined mid-campaign with no entry ({', '.join(PARTY_ENTRY)}): how they meet the party")
    roles = [x for x in (a.roles.split(",") if a.roles else d.get("roles", [])) if x]
    if roles:
        for p in pcs:
            if len(pcs) > 1 and set(roles) <= set(p.get("roles", [])):
                warns.append(f"{p.get('name', '?')} covers every role; spread them so each PC has a job")
        for r in roles:
            if not any(r in p.get("roles", []) for p in pcs):
                warns.append(f"role {r} has no owner")
    for r in d.get("reveals", []):
        if not r.get("fallback"):
            errs.append(f"reveal with no fallback if the players guess or skip it: {r.get('text', '?')[:40]}")
    report(errs, warns, f"{len(pcs)} PCs, {len(d.get('reveals', []))} reveals")


TIERS = ["minor", "moderate", "major", "legendary", "campaign"]
YES = ("yes", "y", "true", "1")


ITEM_NEW = ("cost_axis", "uses", "unpredictable", "bypasses", "friction", "breaks_after")
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
    sched = m.get("schedule", [])
    names = {x.get("id") or x.get("name") for x in clues} | {e.get("clue") for e in sched}
    seen, last = set(), None
    for i, e in enumerate(sched):
        n, lf = e.get("clue", f"#{i + 1}"), e.get("lead_from")
        if i and not lf:
            warns.append(f"schedule {n}: no lead_from (which earlier clue points here)")
        elif lf and lf not in names:
            errs.append(f"schedule {n}: lead_from {lf!r} is not a known clue")
        elif lf and lf not in seen:
            warns.append(f"schedule {n}: lead_from {lf!r} is not an earlier clue")
        if not e.get("partial"):
            warns.append(f"schedule {n}: no partial (what a half-solved clue still gives)")
        at = e.get("at")
        if isinstance(at, (int, float)):
            if last is not None and at < last:
                warns.append(f"schedule {n}: at {at} comes before the previous entry ({last}); keep times ascending")
            last = at
        seen.add(n)
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


def filter_rows(rows, filters, name):
    """Keep rows whose column matches each key=value; a blank or 'any' cell matches all; '|' or ';' list several."""
    for f in filters:
        k, _, v = f.partition("=")
        if not k or not v:
            die(f"--filter {f!r}: write key=value")
        if rows and k not in rows[0]:
            continue
        v = v.strip().lower()
        rows = [r for r in rows if (r.get(k) or "").strip().lower() in ("", "any")
                or v in [x.strip().lower() for x in (r.get(k) or "").replace(";", "|").split("|")]]
    if not rows:
        die(f"{name}: no rows left after --filter")
    return rows


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
        rows = filter_rows(rows, a.filter or [], t)
        tabs.append(rows)
    for f in a.filter or []:
        if not any(f.partition("=")[0] in rows[0] for rows in tabs):
            die(f"--filter {f!r}: no table has that column")
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
    if a.table == "check":
        return table_check(a)
    if a.table == "lint":
        return table_lint(a)
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
    for r in rows:
        ref = (r.get("sub") or "").strip()
        if not ref:
            continue
        f, _, dn = ref.partition(":")
        sp = Path(a.table).parent / f
        if not sp.exists():
            errs.append(f"roll {r['roll']}: sub-table {f} not found")
            continue
        srows, scov, serrs = read_table(sp)
        faces = int(dn.lstrip("dD")) if dn else (max(scov) if scov else 0)
        if len(srows) != faces:
            errs.append(f"roll {r['roll']}: sub-table {f} has {len(srows)} rows for a d{faces}; one row per face")
    sides = [(r.get("side") or "").strip().lower() for r in rows if "side" in r]
    if sides:
        bad = sorted(set(sides) - {"party", "residents", "both"})
        if bad:
            warns.append(f"side values {bad}; use party, residents or both")
        if not {"residents", "both"} & set(sides):
            warns.append("no row is residents or both; wanderers never trouble the dungeon's own dwellers")
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
            if it.get("breaks_after") is not None:
                if not isinstance(it["breaks_after"], int) or it["breaks_after"] < 1:
                    errs.append(f"{n}: breaks_after must be a whole number of failures per rest, 1 or more")
                elif not it.get("save"):
                    warns.append(f"{n}: breaks_after with no save; say what roll counts as a failure")
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
    warns = []
    own = d.get("owner")
    if own:
        use = {str(x).lower() for x in own.get("can_use", [])}
        for it in d.get("items", []):
            n = it.get("name", "?")
            if own.get("intelligent") and (n.lower() in use or it.get("usable")):
                warns.append(f"{n}: an intelligent owner would use it, not leave it in the hoard")
            if not own.get("intelligent") and own.get("random") and it.get("magic"):
                warns.append(f"{n}: a random unintelligent monster carrying a magic item; put it in a lair instead")
    report(errs, warns, "loot split")


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
    if a.resolve:
        return battle_resolve(a)
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
    seen_in, learned = {}, set()
    for f in a.logs:
        text = Path(f).read_text(encoding="utf-8")
        recap, mid, have = False, False, set()
        for line in text.splitlines():
            k, _, v = line.lstrip("-* ").partition(":")
            v = v.strip().lower()
            if k.strip().lower() in ("snapshot", "restart") and v and not v.startswith("("):
                have.add(k.strip().lower())
            if k.strip().lower() == "ended_mid_fight" and v in ("yes", "true", "y"):
                mid = True
            if k.strip().lower() == "recap" and v and not v.startswith("two lines read aloud"):
                recap = True
            if k.strip().lower() == "ended_mid_fight" and v in ("yes", "true", "y"):
                print(f"warn: {f}: ended mid-fight; open next time with the board as it stood and a quick recap of positions")
            if k.strip().lower() == "ending" and v and "|" not in v:
                ends[v] = ends.get(v, 0) + 1
                if v not in ENDINGS:
                    print(f"warn: {f}: ending {v!r}, use " + ", ".join(ENDINGS))
        for k in ("snapshot", "restart"):
            if mid and k not in have:
                print(f"warn: {f}: ended mid-fight with no {k}: line"
                      + (" (positions, HP, effects)" if k == "snapshot" else " (how next session opens)"))
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
        pres = [l for l in text.splitlines() if l.lstrip("-* ").lower().startswith("players present:")]
        for l in pres:
            for who in (x.strip() for x in l.split(":", 1)[1].split(",") if x.strip()):
                seen_in[who] = seen_in.get(who, 0) + 1
        for line in sec.get("learned", []):
            who, _, items = line.lstrip("-* ").partition(":")
            if who.strip() and who.strip() != "Player" and [x for x in items.split(";") if x.strip()]:
                learned.add(who.strip())
    for who, n in sorted(seen_in.items()):
        if n >= 3 and who not in learned:
            print(f"warn: {who} was present in {n} logs and never named anything learned (## Learned)")
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
    errs += challenge_caps(d, skills, succ, warns)
    challenge_tiers(d, succ, errs, warns)
    ft = d.get("on_fail_time")
    if ft is not None:
        if not isinstance(ft, int) or ft < 1:
            errs.append(f"on_fail_time {ft!r}, want minutes lost per failed check (1 or more)")
        elif d.get("limit") and d.get("minutes") and isinstance(succ, int) and isinstance(fail, int):
            worst = succ * d["minutes"] + (fail - 1) * (d["minutes"] + ft)
            if worst > d["limit"]:
                warns.append(f"with {fail - 1} failures at {ft} min each the run takes {worst} min, over the limit {d['limit']}")
    li = d.get("lead_in")
    if li is not None:
        sh = li.get("dc_shift") if isinstance(li, dict) else None
        if not isinstance(sh, int):
            errs.append("lead_in wants dc_shift: how many points the opening scene moves every DC")
        elif abs(sh) > 5:
            warns.append(f"lead_in shifts DCs by {sh}; more than 5 decides the challenge before it starts")
        else:
            print(f"lead_in: a won opening moves DCs {-abs(sh):+d}, a lost one {abs(sh):+d}")
    mins, limit = d.get("minutes"), d.get("limit")
    if mins and limit and isinstance(succ, int) and limit < succ * mins:
        warns.append(f"limit {limit} min is under {succ} attempts x {mins} min; the clock beats a flawless run")
    report(errs, warns, f"{succ} successes before {fail} failures, {len(skills)} skills")


def challenge_caps(d, skills, succ, warns):
    """Per-skill max, requires gates and assists (no success). Only checked when some skill has a max."""
    errs = []
    names = {s.get("name") for s in skills}
    for s in skills:
        if s.get("requires") and s["requires"] not in names:
            errs.append(f"{s.get('name')}: requires {s['requires']!r}, which is not a skill here")
    outs = d.get("outcomes") or {}
    for k in outs:
        if not str(k).isdigit() or (isinstance(succ, int) and int(k) >= succ):
            errs.append(f"outcome at {k!r} successes; use 0 to {succ - 1 if isinstance(succ, int) else '?'}")
    if not isinstance(succ, int) or not any("max" in s for s in skills):
        return errs
    scoring = [s for s in skills if not s.get("assist")]
    if all("max" in s for s in scoring) and sum(s["max"] for s in scoring) < succ:
        errs.append(f"skill caps add to {sum(s['max'] for s in scoring)}, under the {succ} successes needed")
    for s in scoring:
        if s.get("max", succ) >= succ and not s.get("requires"):
            warns.append(f"{s.get('name')}: uncapped, it can finish the challenge alone; give it a max")
    return errs


CHALLENGE_BONUS = 5  # an average PC's skill bonus at low level; our number


def challenge_tiers(d, succ, errs, warns):
    """Graded tiers [{dc, gain}] and botch [{under, gain<0}], timed complications, and expected rounds at an average roll."""
    import math
    tiers = d.get("tiers") or []
    comps = d.get("complications") or []
    for c in comps:
        rnd, every = c.get("round"), c.get("every")
        if not isinstance(rnd, int) and not isinstance(every, int):
            errs.append(f"complication {c.get('effect', '?')!r}: give round or every")
        if not c.get("warning"):
            warns.append(f"complication {c.get('effect', '?')!r}: no warning; show it coming a round before")
        if c.get("removes") and not c.get("stop"):
            warns.append(f"complication {c.get('effect', '?')!r} removes successes with no stop: name how the party prevents it")
    if not tiers or not isinstance(succ, int):
        return
    up = sorted((t for t in tiers if "dc" in t), key=lambda t: t["dc"])
    if any(not isinstance(t.get("gain"), int) for t in tiers):
        errs.append("every tier wants an integer gain")
        return
    bonus = d.get("bonus", CHALLENGE_BONUS)
    eg = 0.0
    for face in range(1, 21):
        tot, g = face + bonus, 0
        for t in up:
            if tot >= t["dc"]:
                g = t["gain"]
        for t in tiers:
            if "under" in t and tot < t["under"]:
                g = t["gain"]
        eg += g / 20
    per = d.get("checks_per_round", d.get("party", 4))
    if eg <= 0:
        warns.append(f"expected gain per check is {eg:.2f} at +{bonus}; the party cannot finish on average")
        return
    prog, rnd = 0.0, 0
    while prog < succ and rnd < 50:
        rnd += 1
        prog += eg * per
        for c in comps:
            hit = c.get("round") == rnd or (isinstance(c.get("every"), int) and c["every"] > 0 and rnd % c["every"] == 0)
            if hit and prog < succ:
                prog = max(0.0, prog - (c.get("removes") or 0))
    print(f"expected rounds at an average roll (+{bonus}, {per} checks a round): "
          + (str(rnd) if prog >= succ else "over 50") + f"; {eg:.2f} successes a check")


TERRAIN = {"road": 1.0, "plains": 0.75, "forest": 0.5, "hills": 0.5, "swamp": 0.35, "mountain": 0.25, "desert": 0.5}


def travel_oddity(a):
    """One colour event per journey from {events: [{text, repeat, slow_offroad}], used: []}; writes the pick back."""
    import random
    p = Path(a.oddity)
    d = json.loads(p.read_text(encoding="utf-8"))
    evs = [jrow(e) for e in d.get("events", [])]
    used = d.setdefault("used", [])
    pool = [e for e in evs if e.get("repeat") or e["text"] not in used]
    if not pool:
        print("oddity: every event used; add more or tag some repeat")
        return 1
    e = random.Random(a.seed).choice(pool)
    used.append(e["text"])
    p.write_text(json.dumps(d, indent=2), encoding="utf-8", newline="\n")
    f = e.get("slow_offroad")
    print(f"oddity: {e['text']}" + (f" (off-road miles x{f:g})" if f and a.terrain != "road" else ""))
    return f if f and a.terrain != "road" else 1


def cmd_travel(a):
    """Days for a trip: pace times terrain, hours past 8 a day cost fatigue, an unknown route adds a quarter."""
    if a.watches is not None:
        travel_watches(a)
        if a.miles is None:
            return
    if a.miles is None:
        die("travel needs --miles (or --watches N for the day and night rhythm)")
    if a.terrain not in TERRAIN:
        die(f"terrain {a.terrain!r}, use {', '.join(TERRAIN)}")
    if a.miles <= 0 or a.pace <= 0 or not 1 <= a.hours <= 16:
        die("miles and pace above 0, hours 1 to 16")
    per_day = a.pace * TERRAIN[a.terrain] * a.hours / 8
    if a.oddity:
        per_day *= travel_oddity(a)
    days = a.miles / per_day * (1 if a.known else 1.25)
    whole = math.ceil(days - 1e-9)
    print(f"{per_day:.1f} miles a day on {a.terrain}; {whole} day(s) for {a.miles:g} miles"
          + ("" if a.known else " (unknown route: +25%, one navigation check a day)"))
    over = max(0, a.hours - 8)
    if over:
        print(f"fatigue: {math.ceil(over)} point(s) a day from {over:g} hour(s) past 8; {math.ceil(over) * whole} over the trip")
    travel_checks(a, whole)


# 0.11.0 and up: calendar, hirelings, districts, chases. Numbers and wording are ours.
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
    if a.legs:
        return chase_legs(a, rng)
    if a.stations:
        return chase_pursuit(a, rng)
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
    if a.grid:
        if a.grid <= a.lead:
            die("--grid must be longer than --lead")
        quarry, hunter = a.lead, 0
        for rnd in range(1, a.rounds + 1):
            q, h = rng.randint(1, 3), rng.randint(1, 3)
            text, shift = rng.choice(comps)
            quarry, hunter = quarry + q + max(shift, 0), hunter + h - min(shift, 0)
            track = "".join("Q" if i == quarry else "P" if i == hunter else "." for i in range(a.grid + 1))
            print(f"round {rnd}: quarry +{q}, pursuer +{h}; {text} ({shift:+d}) {track}")
            if hunter >= quarry:
                print(f"caught in round {rnd}")
                return
            if quarry >= a.grid:
                print(f"escaped in round {rnd}")
                return
        print(f"after {a.rounds} rounds the gap is {quarry - hunter}: the quarry goes to ground")
        return
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
TRAP_FULL = ("avoid", "reset", "alarm")
HAUNT_REARM = ("leave", "rest", "never")


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
        if t.get("kind") == "haunt":
            det = t.get("detection")
            if not (isinstance(det, list) and len(det) >= 2):
                errs.append(f"{n}: a haunt needs a second detection route (detection as a list of 2+)")
            if "thiever" in str(t.get("disable", "")).lower():
                errs.append(f"{n}: a haunt is laid to rest, not picked; give a non-thievery disable")
            if not t.get("anchor"):
                errs.append(f"{n}: a haunt needs an anchor (what holds it here)")
            if t.get("rearm") not in HAUNT_REARM:
                errs.append(f"{n}: rearm {t.get('rearm')!r}, use {', '.join(HAUNT_REARM)}")
    warns = []
    if a.full:
        for t in traps:
            miss = [f for f in TRAP_FULL if not t.get(f)]
            if miss:
                warns.append(f"{t.get('name') or '?'}: no {', '.join(miss)}")
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


# 0.12.0: one-shots, TPK triage, dungeon alert, hook backlog, negotiation, navigation. Numbers and wording are ours.
ONESHOT_BONDS = ("professional", "family", "forced")
ONESHOT_PLOTS = ("duty", "heist", "investigation", "survival", "other")
LOOT_WORDS = ("loot", "treasure", "gold", "reward", "payday", "coin")
DEED_WORDS = ("defeat", "escape", "stop", "save", "rescue", "decide", "choose", "choice", "confront", "reveal",
              "survive", "win", "catch", "expose", "finish", "deliver", "seal", "kill", "capture")


def cmd_oneshot(a):
    """One-shot card JSON: a group bond, a plot shape, a finish scene, pregens with role, 2+ questions and a stake."""
    c = json.loads(Path(a.card).read_text(encoding="utf-8"))
    errs, warns = [], []
    bond = str(c.get("bond") or "").lower()
    if not bond:
        errs.append("no bond: say why these characters are together (" + ", ".join(ONESHOT_BONDS) + ")")
    elif bond not in ONESHOT_BONDS:
        warns.append(f"bond {bond!r}; the usual kinds are " + ", ".join(ONESHOT_BONDS))
    plot = str(c.get("plot") or "").lower()
    if plot and plot not in ONESHOT_PLOTS:
        warns.append(f"plot {plot!r}, use " + ", ".join(ONESHOT_PLOTS))
    elif not plot:
        warns.append("no plot: name the shape (" + ", ".join(ONESHOT_PLOTS) + ")")
    finish = str(c.get("finish") or "").lower()
    if not finish:
        errs.append("no finish: write the scene that ends the night, so it ends in one sitting")
    elif any(w in finish for w in LOOT_WORDS) and not any(w in finish for w in DEED_WORDS):
        warns.append("finish is only a payout; end on a deed or a choice, with the loot after it")
    pre = c.get("pregens", [])
    if not pre:
        errs.append("no pregens")
    roles = {}
    for p in pre:
        n = p.get("name") or "?"
        if not p.get("stake"):
            errs.append(f"{n}: no stake (what this character personally wins or loses tonight)")
        if len(p.get("questions") or []) < 2:
            errs.append(f"{n}: {len(p.get('questions') or [])} question(s), want 2+ for the player to answer at the table")
        r = str(p.get("role") or "").lower()
        if not r:
            warns.append(f"{n}: no role")
        else:
            roles.setdefault(r, []).append(n)
    for r, ns in roles.items():
        if len(ns) > 1:
            warns.append(f"{' and '.join(ns)} share the role {r}; give each pregen its own job")
    report(errs, warns, f"{len(pre)} pregen(s), bond {bond or '?'}, finish set")


TPK_CAUSES = {
    "gm-error": ("The fight was mis-built or a ruling went wrong. Own it out loud.",
                 "Offer a refight from the start of the encounter with the fix in place, or concede: the party "
                 "wakes up beaten but alive, and the foes take what they came for."),
    "bad-luck": ("The dice turned on a fair fight. Say so, and say the choices were sound.",
                 "Keep it short and sure: a recovery group (kin, comrades, hirelings) goes in for the bodies in one "
                 "session, with the odds tilted their way, and a raise or a return waits at the end."),
    "player-error": ("The party took a risk they were warned about. No blame; name the warning they had.",
                     "Let the death stand and start fresh characters tied to the fallen, or run a story return "
                     "that costs something real (a debt, a geas, a lost item)."),
}
TPK_KEEP = {
    "gm-error": "they keep their characters: refight or concede, nothing else is needed",
    "bad-luck": "they keep their characters: the party is captured, left for dead or pulled out by an ally instead of killed",
    "player-error": "they keep their characters: the return comes with a lasting cost the table agrees to",
}


def cmd_tpk(a):
    """Support script and remedy after a total party kill, chosen by cause."""
    cause = a.cause.lower()
    if cause in ("lesson", "reset", "punish", "punishment"):
        die(f"{cause!r} is not a cause; a wipe is never a lesson to teach. Use gm-error, bad-luck or player-error")
    if cause not in TPK_CAUSES:
        die("--cause is one of " + ", ".join(TPK_CAUSES))
    say, fix = TPK_CAUSES[cause]
    print("1. Stop play. Thank the players; check in with anyone upset before any rules talk.")
    print("2. " + say)
    print("3. Remedy: " + fix)
    if a.keep_pcs:
        print("4. The players want their characters back: " + TPK_KEEP[cause] + ".")
    else:
        print("4. Ask whether the players want these characters back (--keep-pcs) before you pick for them.")
    print("5. Decide together before the next session; write it in the session log under ending.")


ALERT_EFFECTS = [
    "calm: wandering check once an hour, guards at their posts",
    "wary: wandering check every half hour, sentries doubled, doors barred",
    "alarmed: wandering check in every room entered, patrols hunt the intruders, traps reset and armed",
    "mustered: groups merge into strong points, the way out is watched",
    "lockdown: the lair is held to the last; its owner gets ready to flee or bargain",
]


def alert_effect(tier, tiers):
    return ALERT_EFFECTS[round(tier * (len(ALERT_EFFECTS) - 1) / tiers)]


def cmd_alert(a):
    """Dungeon alert track in a JSON file: init --tiers N, raise/lower --why, show."""
    if a.action == "noise":
        return alert_noise(a)
    if a.action == "waves":
        return alert_waves(a)
    f = Path(a.file)
    if a.action == "init":
        if not 2 <= a.tiers <= 5:
            die("--tiers 2 to 5")
        merge = {}
        for m in a.merge or []:
            t, _, groups = m.partition(":")
            if not t.isdigit() or not groups:
                die(f"--merge {m!r}: write TIER:group+group")
            merge[t] = [g.strip() for g in groups.split("+") if g.strip()]
        d = {"tier": 0, "tiers": a.tiers, "merge": merge, "history": []}
    else:
        if not f.exists():
            die(f"no alert track at {f}; run 'alert init' first")
        d = json.loads(f.read_text(encoding="utf-8"))
    if a.action in ("raise", "lower"):
        if not a.why:
            die("--why: say what raised or lowered the alert")
        old = d["tier"]
        d["tier"] = max(0, min(d["tiers"], old + (a.by if a.action == "raise" else -a.by)))
        d["history"].append({"from": old, "to": d["tier"], "why": a.why})
        if a.action == "raise" and old == d["tiers"]:
            print("warn: already at the top tier")
    if a.action != "show":
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, indent=1), encoding="utf-8")
    t = d["tier"]
    print(f"alert {t}/{d['tiers']}: {alert_effect(t, d['tiers'])}")
    if d.get("merge", {}).get(str(t)):
        print("merge now: " + " + ".join(d["merge"][str(t)]))
    for h in d["history"][-3:]:
        print(f"  {h['from']} -> {h['to']}: {h['why']}")
    if t and a.action == "show":
        print("lower it with time unseen, a believable cover story, or by removing the one who raised the alarm")


BACKLOG_STATUS = ("live", "back-burner", "dropped")


def cmd_backlog(a):
    """Hook backlog JSON: live and back-burner hooks within a band, each worsening if ignored, some tied to the party."""
    hooks = load_list(a.file, "hooks")
    if a.min < 1 or a.max < a.min:
        die("--min at least 1 and --max at least --min")
    errs, warns = [], []
    open_ = []
    for h in hooks:
        t = h.get("text") or "?"
        st = str(h.get("status") or "live").lower()
        if st not in BACKLOG_STATUS:
            errs.append(f"{t}: status {st!r}, use " + ", ".join(BACKLOG_STATUS))
            continue
        if st == "dropped":
            continue
        open_.append(h)
        if not h.get("worsens"):
            warns.append(f"{t}: no worsens: (what gets worse if the party ignores it)")
        heard = h.get("heard", 0)
        if st == "live" and isinstance(heard, int) and heard > a.retell:
            warns.append(f"{t}: heard {heard} times with no bite; retell it with new stakes or drop it")
    if not a.min <= len(open_) <= a.max:
        warns.append(f"{len(open_)} open hooks, want {a.min} to {a.max}: "
                     + ("too few for a real choice" if len(open_) < a.min else "too many to keep alive"))
    if open_ and not any(str(h.get("tie") or "").lower().startswith(("pc:", "past:")) for h in open_):
        warns.append("no hook is tied to a PC (tie: pc:Name) or a past event (tie: past:what happened)")
    if a.levelup:
        print("level-up review: for each hook, what changed while the party was busy?")
        for h in open_:
            print(f"- {h.get('text', '?')} [{h.get('status', 'live')}]: what changed? worsens: {h.get('worsens', '?')}")
    report(errs, warns, f"{len(open_)} open hook(s) of {len(hooks)}")


ATTITUDES = ["hostile", "wary", "neutral", "open", "helpful"]


def cmd_negotiate(a):
    """Multi-step negotiation: start attitude, one 2d6 check per exchange, at most one step of shift each."""
    import random
    rng = random.Random(a.seed)
    if a.start not in ATTITUDES:
        die("--start is one of " + ", ".join(ATTITUDES))
    i = ATTITUDES.index(a.start)
    goal = ATTITUDES.index(a.goal)
    mods = a.exchange or []
    rolls = a.rolls or []
    print(f"start: {a.start}; goal: {a.goal}")
    for n, m in enumerate(mods, 1):
        r = rolls[n - 1] if n - 1 < len(rolls) else rng.randint(1, 6) + rng.randint(1, 6)
        total = r + m
        step = 1 if total >= 10 else -1 if total <= 4 else 0
        i = max(0, min(len(ATTITUDES) - 1, i + step))
        print(f"exchange {n}: 2d6 {r} {m:+d} = {total}: {('moves up' if step > 0 else 'moves down' if step else 'holds')}"
              f" -> {ATTITUDES[i]}")
        if i == 0:
            print("talks break off: the other side walks away or turns to force")
            return
        if i >= goal:
            print(f"goal reached in {n} exchange(s)")
            return
    print(f"after {len(mods)} exchange(s): {ATTITUDES[i]}"
          + ("" if i >= goal else "; more exchanges need a new argument, an offer or leverage, not the same plea"))


NAV_DC = {"road": 0, "plains": 10, "forest": 15, "hills": 12, "swamp": 15, "mountain": 15, "desert": 13}


def travel_checks(a, whole):
    """Seeded navigation per day off a known route, and a tracking target number."""
    import random
    rng = random.Random(a.seed)
    if a.navigate is not None:
        dc = NAV_DC[a.terrain]
        lost = 0
        if a.known or not dc:
            print("navigation: no checks (known route or road)")
        else:
            for day in range(1, whole + 1):
                r = rng.randint(1, 20)
                ok = r + a.navigate >= dc
                lost += not ok
                print(f"day {day}: d20 {r} {a.navigate:+d} vs {dc}: " + ("on course" if ok else "lost: half a day gone"))
            if lost:
                print(f"lost {lost} time(s): about {lost * 0.5:g} extra day(s)")
    if a.track_age is not None:
        dc = max(NAV_DC[a.terrain], 10) + 2 * a.track_age + (5 if a.rain else 0) - (3 if a.group >= 6 else 0)
        print(f"tracking: target {dc} ({a.terrain} base, +2 a day old, {'+5 rain, ' if a.rain else ''}"
              f"{'-3 big group, ' if a.group >= 6 else ''}one check per half day; a failure loses the trail until a new sign)")


# ---- 0.13.0 ----

def cmd_spell(a):
    if a.action == "cost":
        if a.tier not in range(1, 5) or a.power not in range(1, 5):
            die("--tier and --power must be 1 to 4")
        c = min(16, a.tier * a.power)
        if a.mastered:
            c = max(1, c // 2)
        print(f"cost {c} (tier {a.tier} x power {a.power}, cap 16{', mastered: halved, floor 1' if a.mastered else ''})")
        return
    if not a.file:
        die("spell check FILE.json")
    spell_check(json.loads(Path(a.file).read_text(encoding="utf-8")))


# Our own per-tier caps for homebrew spells (tablewright defaults, not from any book):
# tier: (max targets, max range band, max duration in rounds).
SPELL_CAPS = {1: (1, "near", 1), 2: (3, "far", 3), 3: (6, "far", 10), 4: (12, "distant", 100)}
SPELL_RANGES = ("close", "near", "far", "distant")
SPELL_COOLDOWN = {2: 1, 3: 7, 4: 30}


def spell_check(d):
    import datetime
    spells = d if isinstance(d, list) else d.get("spells", [])
    known = d.get("known", {}) if isinstance(d, dict) else {}
    errs, warns, last, dated = [], [], {}, []
    for s in spells:
        n, t = s.get("name", "?"), s.get("tier")
        if t not in SPELL_CAPS:
            errs.append(f"{n}: tier {t!r}, use 1 to 4")
            continue
        mt, mr, md = SPELL_CAPS[t]
        if not isinstance(s.get("targets"), int) or s["targets"] > mt:
            errs.append(f"{n}: targets {s.get('targets')!r}, tier {t} cap is {mt}")
        r = s.get("range")
        if r not in SPELL_RANGES:
            errs.append(f"{n}: range {r!r}, use " + ", ".join(SPELL_RANGES))
        elif SPELL_RANGES.index(r) > SPELL_RANGES.index(mr):
            errs.append(f"{n}: range {r}, tier {t} cap is {mr}")
        if not isinstance(s.get("duration"), int) or s["duration"] > md:
            errs.append(f"{n}: duration {s.get('duration')!r} rounds, tier {t} cap is {md}")
        sch = s.get("school")
        if sch is not None:
            cap = min(4, max(1, known.get(sch, 0)))
            if t > cap:
                errs.append(f"{n}: tier {t} in {sch}, but {known.get(sch, 0)} known there allows tier {cap} at most")
        if t in SPELL_COOLDOWN:
            if not s.get("created"):
                warns.append(f"{n}: no created date, cooldown not checked")
                continue
            try:
                dated.append((datetime.date.fromisoformat(s["created"]), t, n))
            except ValueError:
                errs.append(f"{n}: created {s['created']!r} is not YYYY-MM-DD")
    for day, t, n in sorted(dated):
        if t in last and (day - last[t][0]).days < SPELL_COOLDOWN[t]:
            errs.append(f"{n}: tier {t} created {(day - last[t][0]).days} days after {last[t][1]}, "
                        f"cooldown is {SPELL_COOLDOWN[t]} days")
        last[t] = (day, n)
    report(errs, warns, f"{len(spells)} spells")


def cmd_rewards(a):
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    tiers = d if isinstance(d, list) else d.get("tiers", [])
    errs, warns, prev = [], [], None
    for t in tiers:
        n, c = t.get("name", "?"), t.get("cadence_sessions")
        if not isinstance(c, (int, float)):
            errs.append(f"{n}: no cadence_sessions")
        else:
            if prev is not None and c <= prev:
                errs.append(f"{n}: cadence {c} sessions does not lengthen past the tier before ({prev})")
            prev = c
        if len(t.get("triggers", [])) < 3:
            errs.append(f"{n}: {len(t.get('triggers', []))} triggers, want 3+")
        if not t.get("gate"):
            warns.append(f"{n}: no gate (what must happen before this tier opens)")
    report(errs, warns, f"{len(tiers)} reward tiers")


def cmd_vendors(a):
    with open(a.vendors, encoding="utf-8", newline="") as f:
        vend = list(csv.DictReader(f))
    with open(a.prices, encoding="utf-8", newline="") as f:
        prices = list(csv.DictReader(f))
    try:
        vend = [(v["vendor"], int(v["tier"]), int(v["reach"])) for v in vend]
        prices = [(p["item"], int(p["tier"]), float(p["price"])) for p in prices]
    except (KeyError, ValueError, TypeError) as e:
        die(f"vendors want vendor,tier,reach and prices item,tier,price: {e}")
    if a.wage <= 0:
        die("--wage must be above 0")
    errs = []
    have = {t for _, t, _ in vend}
    for t in sorted({t for _, t, _ in prices} - have):
        errs.append(f"item tier {t} has no vendor")
    for v1, t1, r1 in vend:
        for v2, t2, r2 in vend:
            if t2 > t1 and r2 < r1:
                errs.append(f"{v2} (tier {t2}) is easier to reach ({r2}) than {v1} (tier {t1}, reach {r1})")
    by = {}
    for _, t, p in prices:
        by.setdefault(t, []).append(p)
    ts = sorted(by)
    for x, y in zip(ts, ts[1:]):
        if min(by[y]) < max(by[x]):
            errs.append(f"prices drop from tier {x} (up to {max(by[x]):g}) to tier {y} (from {min(by[y]):g})")
    for n, t, p in prices:
        print(f"{n} (tier {t}): {p:g} = {p / a.wage:.1f} days of wage {a.wage:g}")
    report(errs, [], f"{len(vend)} vendors, {len(prices)} prices")


def cmd_mob(a):
    if a.count < 1 or a.hp_each < 1:
        die("--count and --hp-each must be at least 1")
    left = a.count
    for h in a.hits:
        if h >= a.hp_each and left > 0:
            left -= 1
    state = "destroyed" if left == 0 else ("routed" if left <= a.count // 2 else "holding")
    print(f"left {left} of {a.count}, {state} (a hit of {a.hp_each}+ drops one member; routs at half or fewer)")


HACK_EASY = ("wired", "familiar", "quiet")
HACK_HARD = ("remote", "foreign", "combat", "jammed")


def cmd_hack(a):
    mods = [m for x in (a.mods or []) for m in x.split(",") if m]
    bad = [m for m in mods if m not in HACK_EASY + HACK_HARD]
    if bad:
        die(f"unknown mods {bad}; easy: {', '.join(HACK_EASY)}; hard: {', '.join(HACK_HARD)}")
    net = sum(m in HACK_HARD for m in mods) - sum(m in HACK_EASY for m in mods)
    diff = "easy" if net < 0 else "hard" if net > 0 else "normal"
    if a.system == "own":
        print("own system: automatic, no roll")
    elif a.system == "simple":
        print(f"simple system: one check, {diff}")
    else:
        print(f"secure system: an attempt (a failure costs something), {diff}")


# Our own settlement bands and population ranges (tablewright defaults).
SETTLE_BANDS = [("thorp", 1, 20), ("hamlet", 21, 100), ("village", 101, 1000), ("small town", 1001, 2500),
                ("large town", 2501, 6000), ("small city", 6001, 12000), ("large city", 12001, 25000),
                ("metropolis", 25001, 10 ** 9)]
SETTLE_FUNCTIONS = {"trade hub": ("lodging", "stables", "smith"), "port": ("docks", "lodging", "chandler"),
                    "mining": ("smith", "assayer", "provisioner"), "farming": ("mill", "market"),
                    "religious": ("temple", "lodging"), "military": ("barracks", "smith", "armory")}


def cmd_settlement(a):
    c = json.loads(Path(a.card).read_text(encoding="utf-8"))
    names = [b[0] for b in SETTLE_BANDS]
    size, pop = c.get("size"), c.get("population")
    errs, warns = [], []
    if size not in names:
        die(f"size {size!r}, use " + ", ".join(names))
    i = names.index(size)
    _, lo, hi = SETTLE_BANDS[i]
    if not isinstance(pop, int) or not lo <= pop <= hi:
        errs.append(f"population {pop!r} does not fit {size} ({lo} to {hi})")
    civic = {x.lower() for x in c.get("civic", [])}
    need = ["authority"] if i >= 1 else []
    if i >= 2:
        need += ["council", "defence", "hall"]
    if i >= 3:
        need.append("walls")
        if c.get("inns", 0) < 2:
            errs.append(f"{size}: {c.get('inns', 0)} inns, a town or bigger wants 2+")
    for k in need:
        if k not in civic:
            errs.append(f"{size}: no {k} in civic")
    biz = {x.lower() for x in c.get("businesses", [])}
    fns = c.get("function") or []
    for fn in [fns] if isinstance(fns, str) else fns:
        if fn not in SETTLE_FUNCTIONS:
            warns.append(f"function {fn!r} has no kit; known: " + ", ".join(SETTLE_FUNCTIONS))
            continue
        for b in SETTLE_FUNCTIONS[fn]:
            if b not in biz:
                errs.append(f"function {fn}: no {b} among businesses")
    warns += settlement_extras(c, i)
    report(errs, warns, f"{c.get('name', 'settlement')}: {size}, {pop}")


def settlement_extras(c, i):
    """Optional government, defence, commerce, lodgings and sights blocks; all checks are warnings."""
    w = []
    if i >= 3:
        for k in ("government", "defence", "commerce"):
            if not c.get(k):
                w.append(f"{c.get('size')}: no {k} block; a town or bigger wants who rules, who guards and what trades")
    d = c.get("defence")
    if isinstance(d, dict) and d.get("patrol") and not d.get("muster"):
        w.append("defence has a patrol but no muster: who answers when the patrol cannot cope")
    com = c.get("commerce")
    if isinstance(com, dict) and com.get("banned") and not com.get("black_market"):
        w.append("commerce bans goods but has no black_market: banned goods still find a seller; say where")
    lod = c.get("lodgings") or []
    if len(lod) >= 2 and len({str(x.get("price")) for x in lod}) == 1:
        w.append(f"{len(lod)} lodgings all at one price; vary them so the choice says something")
    if lod and not any(x.get("hook") for x in lod):
        w.append("no lodging carries a hook; give one a reason to stay there")
    for x in c.get("sights") or []:
        if not x.get("npc") and not x.get("hook"):
            w.append(f"sight {x.get('name', '?')}: no npc and no hook; scenery the players will walk past")
    return w


# Our own favor odds: base percent by relation, minus a risk penalty; the debt size by risk.
FAVOR_BASE = {"acquaintance": 30, "business": 50, "friend": 75}
FAVOR_RISK = {"low": (0, ("minor",)), "moderate": (15, ("minor", "moderate")), "high": (30, ("moderate", "major"))}


def cmd_favor(a):
    import random
    rng = random.Random(a.seed)
    pen, sizes = FAVOR_RISK[a.risk]
    chance = FAVOR_BASE[a.relation] - pen
    roll = rng.randint(1, 100)
    if roll > chance:
        print(f"d100 {roll} vs {chance}: refused")
    else:
        print(f"d100 {roll} vs {chance}: granted, a {rng.choice(sizes)} favor; you owe one back")


# ---------- 0.14.0 ----------

XP_OUTCOMES = ("killed", "surrendered", "routed", "persuaded")
STORY_CAP = 10  # our default: a story award above 1/10 of any PC's xp_to_next is too big


def cmd_xp(a):
    """XP JSON {party: [{name, level, xp_to_next, alive}], foes: [{name, xp, faced, overmatched, outcome, group}], story}."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    party, foes = d.get("party", []), d.get("foes", [])
    if not party:
        die("xp needs party")
    errs, seen, total = [], set(), 0
    for f in foes:
        n = f.get("name", "?")
        out = str(f.get("outcome", "")).lower()
        if out not in XP_OUTCOMES:
            errs.append(f"{n}: outcome {out or 'missing'}, use " + ", ".join(XP_OUTCOMES))
            continue
        if not f.get("faced", True):
            print(f"{n}: not faced, 0 XP")
            continue
        if f.get("overmatched"):
            print(f"{n}: overmatched (no real risk), 0 XP")
            continue
        g = f.get("group")
        if out == "routed" and g is not None:
            if g in seen:
                print(f"{n}: routed group {g} already counted")
                continue
            seen.add(g)
        total += int(f.get("xp", 0))
    story = int(d.get("story", 0))
    if story > total:
        errs.append(f"story award {story} is more than the foe XP {total}")
    for p in party:
        cap = int(p.get("xp_to_next", 0)) // STORY_CAP
        if story > cap:
            errs.append(f"story award {story} is over 1/{STORY_CAP} of {p.get('name', '?')}'s xp_to_next ({cap})")
    alive = [p["name"] for p in party if p.get("alive", True)]
    if not alive:
        errs.append("no survivors to split among")
    if errs:
        return report(errs, [], "")
    share, rest = divmod(total + story, len(alive))
    print(f"foe XP {total} + story {story} = {total + story}: {share} each to " + ", ".join(alive)
          + (f" ({rest} left over)" if rest else ""))
    report([], [], "xp award")


def cmd_morale(a):
    """2d10 against the rating plus modifiers; a roll over the modified rating breaks."""
    import random
    mod = 0
    for m in a.mod or []:
        k, _, v = m.partition("=")
        try:
            mod += int(v)
        except ValueError:
            die(f"--mod NAME=V, got {m}")
        print(f"{k}: {int(v):+d}")
    if a.leader_cumulative is not None:
        return morale_leader(a)
    if a.break_units is not None or a.dice == "2d6":
        if a.dice == "2d6" and a.rating is None:
            die("--dice 2d6 needs --rating (the morale score)")
        return morale_extra(a, mod)
    if a.rating is None:
        die("morale needs --rating (or --break UNITS)")
    target = a.rating + mod
    roll = a.roll
    if roll is None:
        rng = random.Random(a.seed)
        roll = rng.randint(1, 10) + rng.randint(1, 10)
    print(f"2d10 {roll} vs {target}: " + ("breaks (flee or surrender)" if roll > target else "holds"))


LEADER_ROUNDS = 10  # list at most this many rounds after the leader falls; our cap


def morale_leader(a):
    """After the leader falls the flee chance rises N% a round; print the odds they have fled by each round."""
    import random
    n = a.leader_cumulative
    if not 1 <= n <= 100:
        die("--leader-cumulative N wants 1 to 100 (percent added each round)")
    rng = random.Random(a.seed) if a.seed is not None else None
    stay, fled = 1.0, None
    for r in range(1, LEADER_ROUNDS + 1):
        p = min(100, n * r)
        stay *= 1 - p / 100
        line = f"round {r}: {p}% this round, {round((1 - stay) * 100)}% fled by now"
        if rng and fled is None:
            roll = rng.randint(1, 100)
            line += f", d100 {roll}" + (" flee" if roll <= p else " stay")
            if roll <= p:
                fled = r
        print(line)
        if p >= 100:
            break
    if rng:
        print(f"they flee in round {fled}" if fled else f"they stay through round {r}")


COIN_CAP = 5  # our default: more coins than this in one session is generous


def cmd_awards(a):
    """Session logs (oldest first): 'award: player | kind | ability | reason | xp', 'milestone: player', 'coins: player N'."""
    errs, warns, last, players = [], [], [], set()
    for path in a.logs:
        seen, ms, coins = {}, set(), {}
        for ln in Path(path).read_text(encoding="utf-8").splitlines():
            k, _, v = ln.strip().lstrip("-* ").partition(":")
            k = k.strip().lower()
            if k == "award":
                f = [x.strip() for x in v.split("|")] + [""] * 5
                pl, kind, ab, reason, xp = f[:5]
                players.add(pl)
                if not reason:
                    errs.append(f"{path}: award to {pl} has no reason")
                if ab:
                    key = (pl, ab.lower())
                    seen[key] = seen.get(key, 0) + 1
                    if seen[key] == 2:
                        warns.append(f"{path}: {pl} got {ab} awarded twice this session; reward something new")
                print(" ".join(x for x in (f"{pl}:", kind or "award", ab, xp, f"({reason or 'no reason'})") if x))
            elif k == "milestone":
                pl = v.strip()
                players.add(pl)
                ms.add(pl)
            elif k == "coins":
                pl, _, n = v.strip().rpartition(" ")
                pl = pl.strip()
                players.add(pl)
                try:
                    coins[pl] = coins.get(pl, 0) + int(n)
                except ValueError:
                    errs.append(f"{path}: coins line wants 'player N': {ln.strip()}")
        for pl, n in coins.items():
            if n > COIN_CAP:
                warns.append(f"{path}: {pl} got {n} coins in one session (over {COIN_CAP}, our default)")
        last.append(ms)
    if len(last) >= 3:
        recent = set().union(*last[-3:])
        for pl in sorted(players - recent):
            warns.append(f"{pl}: no milestone in the last 3 logs")
    report(errs, warns, f"{len(a.logs)} log(s), {len(players)} player(s)")


ROOM_KEYS = ("timer", "threat", "treat")  # the same tags prep's fight check reads


def cmd_rooms(a):
    """Rooms JSON {rooms: [{name, timer, threat, treat, stake, wonder, enemies, difficulty, damage, disruption, duration}]}."""
    rooms = load_list(a.file, "rooms")
    errs, warns = [], []
    if not 2 <= len(rooms) <= 4:
        warns.append(f"{len(rooms)} rooms; 2 to 4 keeps a session moving (our default)")
    streak = 0
    for r in rooms:
        n = r.get("name", "?")
        miss = [k for k in ROOM_KEYS if not r.get(k)]
        if miss:
            errs.append(f"{n}: no " + ", ".join(miss))
        for k in ("stake", "wonder"):
            if not r.get(k):
                warns.append(f"{n}: no {k}")
        dials = {k: r.get(k, 1) for k in LEVERS}
        for k, v in dials.items():
            if not isinstance(v, int) or not 1 <= v <= 6:
                errs.append(f"{n}: {k} {v}, use 1 to 6")
        if str(r.get("difficulty", "")).lower() == "hard" and all(v == 1 for v in dials.values()):
            warns.append(f"{n}: hard with every dial at 1; turn up damage, disruption or duration")
        if r.get("objective") and len(r.get("paths") or []) < 2:
            warns.append(f"{n}: objective with {len(r.get('paths') or [])} paths; give 2+ ways to reach it")
        if r.get("roleplay") and not r.get("fallback"):
            warns.append(f"{n}: roleplay gate with no fallback; give a dice check for when the talk stalls")
        for roll in r.get("rolls") or []:
            if not roll.get("on_fail"):
                warns.append(f"{n}: roll {roll.get('skill', '?')} with no on_fail; a failed roll must still move the scene")
        streak = streak + 1 if r.get("enemies") else 0
        if streak == 3:
            warns.append(f"{n}: third room in a row with enemies; give one a breather")
    if a.keys:
        e2, w2 = lock_key_errors(rooms)
        errs += e2
        warns += w2
    if a.pieces:
        e2, w2 = piece_errors(rooms)
        errs += e2
        warns += w2
    report(errs, warns, f"{len(rooms)} rooms")


def lock_needs(r):
    """A room's locks as sets of keys; a list item is one lock needing all its keys."""
    out = []
    for x in r.get("locks") or []:
        if isinstance(x, dict):
            x = x.get("requires") or [x.get("key")]
        out.append(set(x) if isinstance(x, list) else {x})
    if r.get("requires"):
        out.append(set(r["requires"]))
    return out


def lock_specs(r):
    """(keys needed, clue room) per lock; dict locks may give clue_in."""
    clues = [x.get("clue_in") if isinstance(x, dict) else None for x in r.get("locks") or []]
    if r.get("requires"):
        clues.append(r.get("clue_in"))
    return list(zip(lock_needs(r), clues))


def room_keys(r):
    return set(r.get("keys") or []).union(*[set(f.get("keys") or []) for f in r.get("foes") or []])


def grow_keys(by, start, given):
    """Every key the party can pick up from start, starting with these."""
    found, grew = set(given), True
    while grew:
        grew = False
        for rn in reach_rooms(by, start, found):
            new = room_keys(by[rn]) - found
            if new:
                found |= new
                grew = True
    return found


def entry_rooms(rooms):
    return [r.get("name", "?") for r in rooms if r.get("entry")] or [rooms[0].get("name", "?")]


def lock_name(need):
    return "+".join(sorted(need))


def reach_rooms(by, start, found):
    """Rooms open from start with these keys in hand."""
    seen, todo = set(), [start]
    while todo:
        rn = todo.pop()
        r = by.get(rn)
        if rn in seen or r is None or not all(n <= found for n in lock_needs(r)):
            continue
        seen.add(rn)
        todo += list(r.get("exits") or [])
    return seen


def lock_key_errors(rooms):
    """Rooms may give locks: [key or [keys all needed]] and keys: [..]; exits: [room names] give reachability
    from every room with entry: true (else the first room); foes: [{name, flee_to, keys}] are checked too."""
    errs, warns, locks, keys = [], [], {}, {}
    by = {r.get("name", "?"): r for r in rooms}
    for r in rooms:
        rn = r.get("name", "?")
        for need in lock_needs(r):
            for k in need:
                locks.setdefault(k, []).append(rn)
        for k in r.get("keys") or []:
            keys.setdefault(k, []).append(rn)
        for f in r.get("foes") or []:
            for k in f.get("keys") or []:
                keys.setdefault(k, []).append(rn)
    for k in sorted(set(locks) - set(keys)):
        errs.append(f"lock {k} ({', '.join(locks[k])}) has no key")
    for k in sorted(set(keys) - set(locks)):
        errs.append(f"key {k} ({', '.join(keys[k])}) opens no lock")
    for k in sorted(set(locks) & set(keys)):
        for rn in sorted(set(locks[k]) & set(keys[k])):
            errs.append(f"key {k} is in {rn}, the room it unlocks")
    events = {e for r in rooms for e in r.get("events") or []}
    for r in rooms:
        rn = r.get("name", "?")
        until = r.get("locked_until")
        if r.get("locked") and not lock_needs(r) and not until:
            warns.append(f"{rn}: locked with neither a key nor a locked_until event; say how it opens")
        if until and events and until not in events:
            warns.append(f"{rn}: locked until {until}, but no room raises that event")
    for r in rooms:
        for f in r.get("foes") or []:
            to = f.get("flee_to")
            if to and to not in by:
                errs.append(f"{r.get('name', '?')}: {f.get('name', 'foe')} flees to {to}, no such room")
            back = f.get("return_to")
            if back and back not in by:
                errs.append(f"{r.get('name', '?')}: {f.get('name', 'foe')} returns to {back}, no such room")
            elif back and not f.get("return_after"):
                warns.append(f"{r.get('name', '?')}: {f.get('name', 'foe')} returns to {back} with no return_after; say when")
            if f.get("fall") and not to:
                warns.append(f"{r.get('name', '?')}: {f.get('name', 'foe')} has fall damage but no flee_to")
    if not any("exits" in r for r in rooms):
        return errs, warns
    entries = entry_rooms(rooms)

    def reach(start, given):
        return grow_keys(by, start, given)

    for start in entries:
        found = reach(start, ())
        where = f" from {start}" if len(entries) > 1 else ""
        for k in sorted(set(keys) - found):
            if any(f"key {k} is in" in e for e in errs):
                continue
            own = [n for r in rooms for n in lock_needs(r) if k in n]
            if any(set(keys[k]) & reach_rooms(by, start, reach(start, n)) for n in own):
                errs.append(f"key {k} can only be reached through its own lock ({', '.join(lock_name(n) for n in own)}){where}")
            else:
                errs.append(f"key {k} is never reachable from {start}")
        for r in rooms:
            for need, clue in lock_specs(r):
                if not clue:
                    continue
                if clue not in by:
                    errs.append(f"{r.get('name', '?')}: lock {lock_name(need)} has its clue in {clue}, no such room")
                elif start == entries[0] and clue not in reach_rooms(by, start, grow_keys(by, start, ()) - need):
                    warns.append(f"{r.get('name', '?')}: the clue for lock {lock_name(need)} is in {clue}, not reachable before the lock")
        for r in rooms:
            rn = r.get("name", "?")
            held = set(r.get("keys") or [])
            for f in r.get("foes") or []:
                to, fk = f.get("flee_to"), set(f.get("keys") or [])
                if to not in by or to == rn:
                    continue
                if start == entries[0]:
                    shut = [lock_name(n) for n in lock_needs(by[to]) if not n <= held | fk]
                    if shut:
                        warns.append(f"{rn}: {f.get('name', 'foe')} flees to {to} behind lock {', '.join(shut)} with no key in {rn}")
                for k in sorted(fk & found):
                    if to not in reach_rooms(by, start, found - {k}):
                        warns.append(f"{rn}: {f.get('name', 'foe')} carries key {k} and flees past its lock to {to}; the key goes out of reach{where}")
    return errs, warns


def piece_errors(rooms):
    """Items {name, piece_of: PUZZLE} must lie in rooms reachable without passing the room with puzzle: PUZZLE."""
    errs, warns = [], []
    by = {r.get("name", "?"): r for r in rooms}
    puzzles = {r.get("puzzle"): r.get("name", "?") for r in rooms if r.get("puzzle")}
    pieces = [(it.get("name", "item"), it.get("piece_of"), r.get("name", "?"))
              for r in rooms for it in r.get("items") or [] if isinstance(it, dict) and it.get("piece_of")]
    for pz, pr in puzzles.items():
        if not any(p == pz for _, p, _ in pieces):
            warns.append(f"puzzle {pz} ({pr}) has no pieces")
    start = entry_rooms(rooms)[0]
    for name, pz, rn in pieces:
        if pz not in puzzles:
            errs.append(f"{rn}: {name} is a piece of {pz}, no room has that puzzle")
            continue
        cut = dict(by)
        cut[puzzles[pz]] = dict(by[puzzles[pz]], exits=[])
        if rn not in reach_rooms(cut, start, grow_keys(cut, start, ())):
            errs.append(f"{rn}: {name} (piece of {pz}) lies past the puzzle room {puzzles[pz]}; move it before the gate")
    return errs, warns


def cmd_objective(a):
    """Boss gates over a rooms JSON: --gate FLAG:N needs N rooms with flags: [FLAG]; --kill-list a,b,c any order."""
    rooms = load_list(a.file, "rooms")
    by = {r.get("name", "?"): r for r in rooms}
    start = entry_rooms(rooms)[0]
    open_rooms = reach_rooms(by, start, grow_keys(by, start, ())) if any("exits" in r for r in rooms) else set(by)
    errs, warns, done = [], [], []
    if not a.gate and not a.kill_list:
        die("give --gate FLAG:N and/or --kill-list a,b,c")
    for g in a.gate or []:
        flag, _, n = g.rpartition(":")
        if not flag or not n.isdigit():
            die(f"bad gate {g!r} (use FLAG:N)")
        where = [r.get("name", "?") for r in rooms if flag in (r.get("flags") or [])]
        if len(where) < int(n):
            errs.append(f"gate {flag}: needs {n}, only {len(where)} room(s) set it")
        for rn in where:
            if rn not in open_rooms:
                warns.append(f"gate {flag}: {rn} sets it but is unreachable from {start}")
        done.append(f"boss appears after {n} {flag} of {len(where)}")
    if a.kill_list:
        names = [x.strip() for x in a.kill_list.split(",") if x.strip()]
        home = {f.get("name"): r.get("name", "?") for r in rooms for f in r.get("foes") or []}
        for x in names:
            if x not in home:
                errs.append(f"kill list: {x} is in no room's foes")
            elif home[x] not in open_rooms:
                warns.append(f"kill list: {x} is in {home[x]}, unreachable from {start}")
        done.append(f"any-order kill list of {len(names)}; reveal on the last kill")
    report(errs, warns, "; ".join(done))


# D&D 5e 2024 (SRD 5.2.1, CC-BY-4.0, attribution above): XP total needed for levels 1 to 20.
LEVEL_XP_5E = (0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000,
               165000, 195000, 225000, 265000, 305000, 355000)


def cmd_xp_gap(a):
    """Does an adventure's total XP award carry each PC to the next level? Award split evenly unless --each."""
    if not 1 <= a.level <= 20:
        die("level 1 to 20")
    if a.level == 20:
        print("level 20 is the cap; XP no longer levels")
        return
    share = a.award if a.each else a.award // max(1, a.party)
    start = [int(x) for x in a.xp.split(",")] if a.xp else [LEVEL_XP_5E[a.level - 1]] * a.party
    short = 0
    for i, have in enumerate(start, 1):
        need = LEVEL_XP_5E[a.level] - have
        if need <= 0:
            print(f"PC {i}: already at level {a.level + 1} XP")
        elif share >= need:
            print(f"PC {i}: levels with {share - need} XP to spare")
        else:
            short += 1
            print(f"PC {i}: {need - share} XP short of level {a.level + 1} ({share} of {need})")
    if short:
        print(f"warn: {short} PC(s) end below level {a.level + 1}; add {a.award} more or plan a milestone")
    else:
        print(f"ok: every PC reaches level {a.level + 1}")


def cmd_session_end(a):
    """Roll the rounds left (rerolling dropped values) and list the final turns in seat order."""
    import random
    rng = random.Random(a.seed)
    drop = set(a.drop or [])
    if set(range(1, a.die + 1)) <= drop:
        die("every face is dropped")
    while True:
        r = rng.randint(1, a.die)
        if r not in drop:
            break
    players = [p.strip() for p in a.players.split(",") if p.strip()]
    print(f"d{a.die} {r}: {r} round(s) left")
    print("final turns: " + ", ".join(players))


ADD_FIRST = ("brute", "soldier")
CUT_FIRST = ("controller", "skirmisher")


def cmd_resize(a):
    """Resize an encounter to a new party size: one foe per PC of difference."""
    foes = [(f.partition(":")[0], f.partition(":")[2].lower()) for f in a.foe]

    def xp(fs, party):
        tot = sum(foe_xp(a.system, lv, a.level)[0] or 0 for lv, _ in fs)
        b = dnd_budgets(party, a.level) if a.system == "5e" else pf_budgets(party)
        return tot, band_for(tot, b)

    before = xp(foes, a.party)
    new = list(foes)
    diff = a.to - a.party
    if diff < 0:
        if len(foes) == 1 and foes[0][1] == "solo":
            die("a lone solo cannot lose a foe; lower its level instead")
        for _ in range(-diff):
            if len(new) <= 1:
                print("one foe left; lower its level instead")
                break
            idx = next((i for i, f in enumerate(new) if f[1] in CUT_FIRST), len(new) - 1)
            print(f"cut: level {new[idx][0]} {new[idx][1] or 'foe'}")
            new.pop(idx)
    else:
        lv = sorted(foes, key=lambda f: float(eval_cr(f[0])))[len(foes) // 2][0]
        for i in range(diff):
            role = ADD_FIRST[i % 2]
            print(f"add: level {lv} {role}")
            new.append((lv, role))
    after = xp(new, a.to)
    print(f"before: {a.party} PCs, {before[0]} XP, {before[1]}")
    print(f"after: {a.to} PCs, {after[0]} XP, {after[1]}")


def eval_cr(x):
    n, _, d = x.partition("/")
    try:
        return float(n) / float(d) if d else float(n)
    except ValueError:
        die(f"foe level must be a number: {x}")


def cmd_target(a):
    """Target JSON {pcs: [{name, marked, threat, reach}]}: marked first, then (--smart) threat, then reach, then a roll."""
    import random
    pcs = load_list(a.file, "pcs")
    rng = random.Random(a.seed)
    marked = [p for p in pcs if p.get("marked")]
    pick, why = (marked, "marked it") if marked else (pcs, "")
    if not marked and a.smart:
        top = max(int(p.get("threat", 0)) for p in pick)
        pick = [p for p in pick if int(p.get("threat", 0)) == top]
        why = "clearest threat"
    if len(pick) > 1:
        near = min(int(p.get("reach", 0)) for p in pick)
        pick = [p for p in pick if int(p.get("reach", 0)) == near]
        why = "easiest to reach"
    if len(pick) > 1:
        t = rng.choice(pick)
        print(f"target: {t['name']} (tie among {', '.join(p['name'] for p in pick)}, rolled)")
    else:
        print(f"target: {pick[0]['name']} ({why})")


PLAYTEST_DEBRIEF = ("fun", "trouble", "improvements")


def cmd_playtest(a):
    """Blind playtest JSON {new_group, questions: [{text, answered, section}], debrief: {fun, trouble, improvements}, player_counts}."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs = []
    if not d.get("new_group"):
        errs.append("not a new group; a blind test needs players who never saw the game")
    for q in d.get("questions", []):
        t = q.get("text", "?")
        if q.get("answered"):
            errs.append(f"observer answered a question: {t}")
        if not q.get("section"):
            errs.append(f"question with no rule section: {t}")
    for k in PLAYTEST_DEBRIEF:
        if not d.get("debrief", {}).get(k):
            errs.append(f"debrief has no {k}")
    if not d.get("player_counts"):
        errs.append("no player_counts")
    report(errs, [], f"{len(d.get('questions', []))} question(s) logged")



# 0.15.0: wilderness rhythm, mass battles, army logistics, herbalism. Every number is ours or the user's file.
def parse_dice(expr):
    """'2d10', 'd100', '3d6+2', '4' -> (count, faces, plus)."""
    s = str(expr).strip().lower().replace(" ", "")
    try:
        if "d" not in s:
            return 0, 0, int(s)
        n, _, rest = s.partition("d")
        plus = 0
        for sign in "+-":
            if sign in rest:
                rest, _, k = rest.partition(sign)
                plus = int(k) * (1 if sign == "+" else -1)
        n, f = int(n or 1), int(rest)
        if n < 1 or f < 2:
            raise ValueError
        return n, f, plus
    except ValueError:
        die(f"bad dice {expr!r}; use NdM, NdM+K or a number")


def dice_dist(expr):
    """Exact distribution {total: probability} of a dice expression."""
    n, f, plus = parse_dice(expr)
    dist = {0: 1.0}
    for _ in range(n):
        nxt = {}
        for t, p in dist.items():
            for k in range(1, f + 1):
                nxt[t + k] = nxt.get(t + k, 0) + p / f
        dist = nxt
    return {t + plus: p for t, p in dist.items()}


def roll_expr(expr, rng):
    n, f, plus = parse_dice(expr)
    return sum(rng.randint(1, f) for _ in range(n)) + plus


def parse_odds(s):
    """'1/6', '0.2' or '20%' -> a probability."""
    s = str(s).strip()
    try:
        if "/" in s:
            x, y = s.split("/")
            p = int(x) / int(y)
        elif s.endswith("%"):
            p = float(s[:-1]) / 100
        else:
            p = float(s)
    except (ValueError, ZeroDivisionError):
        die(f"bad odds {s!r}; use 1/6, 0.2 or 20%")
    if not 0 <= p <= 1:
        die(f"odds {s} outside 0 to 1")
    return p


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"{path}: {e}")


DAY_SLOTS = ("morning", "midday", "afternoon", "evening")


def travel_watches(a):
    """A day roll with a time slot, one check per night watch (a cold camp adds odds), weather every few hours."""
    import random
    rng = random.Random(a.seed)
    day_p, watch_p = parse_odds(a.day_odds), parse_odds(a.watch_odds)
    if a.no_fire:
        watch_p = min(1.0, watch_p + parse_odds(a.no_fire_odds))
    any_night = 1 - (1 - watch_p) ** a.watches
    print(f"day: {day_p:.0%} event chance; night: {a.watches} watch(es) at {watch_p:.0%} each"
          + (" (no fire)" if a.no_fire else "") + f"; at least one night event {any_night:.1%}")
    if a.no_fire:
        base = 1 - (1 - parse_odds(a.watch_odds)) ** a.watches
        print(f"a fire would make it {base:.1%}; the cold camp hides you less well, the fire shows you from afar")
    print(f"weather checks: every {a.weather_every:g} hours, {math.ceil(24 / a.weather_every)} a day")
    if a.seed is not None:
        if rng.random() < day_p:
            print(f"day roll: event in the {rng.choice(DAY_SLOTS)}")
        else:
            print("day roll: quiet")
        for w in range(1, a.watches + 1):
            print(f"watch {w}: " + ("event" if rng.random() < watch_p else "quiet"))


def cmd_weather(a):
    """Weather states from a JSON file: change chance per check, effect flags, encounters implausible in a state."""
    import random
    d = load_json(a.file)
    states = d.get("states") or {}
    if not states:
        die("weather file needs states: {name: {change, next, effects}}")
    cur = a.start or d.get("start") or next(iter(states))
    if cur not in states:
        die(f"start state {cur!r} not in states")
    errs = [f"state {k}: next names unknown {n}" for k, v in states.items() for n in v.get("next", []) if n not in states]
    if errs:
        report(errs, [], "")
    rng = random.Random(a.seed)
    hours = 0
    while hours < a.hours:
        st = states[cur]
        eff = st.get("effects") or []
        print(f"hour {hours:g}: {cur}" + (f" ({', '.join(eff)})" if eff else ""))
        hours += a.every
        if hours < a.hours and st.get("next") and rng.random() < float(st.get("change", 0)):
            cur = rng.choice(st["next"])
    for e in d.get("encounters", []):
        if cur in (e.get("implausible_in") or []):
            print(f"reroll: {e.get('name')} makes no sense in {cur}")


def table_check(a):
    """Coverage of a roll table against a dice expression: gaps, overlaps, and each row's chance."""
    if not a.dice or len(a.tables) != 1:
        die("table check FILE.csv --dice 2d10 (or d100, 3d6...)")
    with open(a.tables[0], encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    dist = dice_dist(a.dice)
    seen, errs = {}, []
    for r in rows:
        try:
            lo, hi = roll_range(r)
        except (KeyError, ValueError, AttributeError):
            die(f"bad roll {r.get('roll')!r} (use 3 or 1-4)")
        for v in range(lo, hi + 1):
            if v in seen:
                errs.append(f"{v} is in rows {seen[v]} and {r['roll']}")
            seen.setdefault(v, r["roll"])
        outside = [v for v in range(lo, hi + 1) if v not in dist]
        if outside:
            errs.append(f"row {r['roll']}: {a.dice} cannot roll {outside[:5]}")
        p = sum(dist.get(v, 0) for v in range(lo, hi + 1))
        name = r.get("result") or r.get("kind") or r.get("name") or ""
        print(f"{r['roll']:>7} {p:6.1%} {name}")
    gaps = sorted(v for v in dist if v not in seen)
    if gaps:
        errs.append(f"{a.dice} can roll {gaps[:10]} with no row")
    report(errs, [], f"{len(rows)} rows cover {a.dice}")


def table_lint(a):
    """Encounter entries (JSON list) each need a hook, a truth, a skill-check follow-up and a morale rule."""
    if len(a.tables) != 1:
        die("table lint FILE.json")
    d = load_json(a.tables[0])
    ents = d.get("encounters", []) if isinstance(d, dict) else d
    errs = []
    for i, e in enumerate(ents, 1):
        miss = [k for k in ("hook", "truth", "check", "morale") if not e.get(k)]
        if miss:
            errs.append(f"{e.get('name', 'entry %d' % i)}: no {', '.join(miss)}")
    report(errs, [], f"{len(ents)} encounter entries")


def count_foes(a):
    """--count-foe DICExLVL: (spec, min, mean, max) XP of a dice-range foe count."""
    rows = []
    for spec in a.count_foe or []:
        expr, _, lvl = spec.partition("x")
        if not lvl:
            die(f"--count-foe DICExLEVEL, got {spec}")
        xp, note = foe_xp(a.system, lvl, a.level)
        if xp is None:
            die(f"--count-foe {spec}: {note}")
        dist = dice_dist(expr)
        mean = sum(k * p for k, p in dist.items())
        rows.append((spec, min(dist) * xp, mean * xp, max(dist) * xp))
    return rows


def cmd_unit(a):
    """A troop type as a unit rating: HP in blocks, one damage per hit; flags foes that hit only on a 20. Or hero scale."""
    if a.hero is not None:
        if a.scale < 1:
            die("--scale at least 1")
        dmg = a.hero // a.scale
        print(f"hero at unit scale: {a.hero} damage / {a.scale} = {dmg} to a unit per hit"
              + (" (too small to wound a unit; count it as 1 on a hit)" if dmg == 0 else ""))
        print(f"attack sequences a round: {a.sequences} (give the hero more swings, not more damage)")
        return
    if a.hp is None or a.block < 1:
        die("unit needs --hp (and --block at least 1), or --hero")
    pts = max(1, math.ceil(a.hp / a.block))
    print(f"unit: {pts} point(s) of HP ({a.hp:g} HP / {a.block}), {a.attacks} attack(s), AC {a.ac}, morale {a.morale}; each hit does 1")
    warns = []
    if a.enemy_hit is not None:
        need = a.ac - a.enemy_hit
        if need >= 20:
            warns.append(f"enemy at {a.enemy_hit:+d} needs {need} on the d20: hits only on a natural 20")
        else:
            print(f"enemy at {a.enemy_hit:+d} hits on {max(2, need)}+ ({(21 - max(2, need)) / 20:.0%})")
    report([], warns, f"rating {pts * max(1, a.attacks)} (points x attacks)")


def cmd_command(a):
    """Divisions' activation cost against each commander's leadership, and division count against the general's cap."""
    d = load_json(a.file)
    errs, warns = [], []
    divs = d.get("divisions", [])
    cap = d.get("general", {}).get("cap")
    if cap is not None and len(divs) > cap:
        errs.append(f"{len(divs)} divisions, the general can lead {cap}")
    for dv in divs:
        cost = 0
        for u in dv.get("units", []):
            c = 1 + bool(u.get("out_of_radius")) + bool(u.get("disordered")) - bool(u.get("lieutenant"))
            cost += max(1, c)
        lead = dv.get("leadership", 0)
        who = dv.get("commander", "?")
        print(f"{who}: {len(dv.get('units', []))} unit(s) cost {cost} of {lead}")
        if cost > lead:
            errs.append(f"{who} needs {cost} to activate all, has {lead}")
        elif cost == lead:
            warns.append(f"{who} has no spare points")
    report(errs, warns, f"{len(divs)} division(s)")


def battle_resolve(a):
    """Expected hits each round per side, run until one side loses a third of its units, then pursuit throws."""
    import random
    d = load_json(a.plan)
    sides = d.get("sides") or []
    if len(sides) != 2:
        die("--resolve wants sides: [two armies of units]")
    hp = [[u.get("hp", 1) for u in s["units"]] for s in sides]
    start = [len(s["units"]) for s in sides]
    brk = [math.ceil(n / 3) for n in start]
    carry = [0.0, 0.0]
    broken = [False, False]
    for rnd in range(1, a.rounds + 1):
        hits = []
        for i in (0, 1):
            alive_foe = [u for u, h in zip(sides[1 - i]["units"], hp[1 - i]) if h > 0]
            ac = sum(u.get("ac", 10) for u in alive_foe) / max(1, len(alive_foe))
            e = 0.0
            for u, h in zip(sides[i]["units"], hp[i]):
                if h > 0:
                    need = max(2, min(20, math.ceil(ac - u.get("to_hit", 0))))
                    e += u.get("attacks", 1) * (21 - need) / 20
            hits.append(e)
        for i in (0, 1):
            carry[1 - i] += hits[i]
            while carry[1 - i] >= 1 and any(h > 0 for h in hp[1 - i]):
                j = next(k for k, h in enumerate(hp[1 - i]) if h > 0)
                hp[1 - i][j] -= 1
                carry[1 - i] -= 1
        lost = [sum(h <= 0 for h in hp[i]) for i in (0, 1)]
        print(f"round {rnd}: {sides[0].get('name', 'A')} {hits[0]:.1f} hits, {sides[1].get('name', 'B')} {hits[1]:.1f} hits;"
              f" lost {lost[0]}/{start[0]} and {lost[1]}/{start[1]}")
        broken = [lost[i] >= brk[i] for i in (0, 1)]
        if any(broken):
            break
    if not any(broken):
        print(f"no side broke in {a.rounds} rounds")
        return
    if all(broken):
        print("both sides reach their break point: a mutual withdrawal")
        return
    loser = broken.index(True)
    win = 1 - loser
    print(f"{sides[loser].get('name', 'side')} breaks (lost {lost[loser]} of {start[loser]}, break point {brk[loser]})")
    rng = random.Random(a.seed)
    for u, h in zip(sides[win]["units"], hp[win]):
        if h > 0 and u.get("pursue", True):
            print(f"pursuit: {u.get('name', 'unit')} throws 2d6 {rng.randint(1, 6) + rng.randint(1, 6)}")


def parse_bands(spec):
    """'rout<=4,fall back<=7,hold' -> [(name, max or None)]."""
    out = []
    for part in spec.split(","):
        name, _, mx = part.partition("<=")
        try:
            out.append((name.strip(), int(mx) if mx.strip() else None))
        except ValueError:
            die(f"--bands: bad part {part!r}")
    if out[-1][1] is not None:
        die("--bands: the last band takes no <= (it is everything above)")
    return out


def morale_extra(a, mod):
    """--break N: the army break point. --dice 2d6: odds of each band for 2d6 + rating + mods."""
    if a.break_units is not None:
        print(f"break point: the army breaks after losing {math.ceil(a.break_units / 3)} of {a.break_units} units (a third)")
    if a.dice == "2d6":
        dist = dice_dist("2d6")
        prev = -999
        for name, mx in parse_bands(a.bands):
            top = mx if mx is not None else 999
            p = sum(q for t, q in dist.items() if prev < t + a.rating + mod <= top)
            print(f"{name}: {p:.1%}")
            prev = top


MARCH_REST = 6  # our default: days marched before a rest day is owed


def cmd_march(a):
    """Tactical speed to daily and weekly miles, with terrain and road, rest debt and forced-march fatigue."""
    daily = a.speed / a.per_mile * a.terrain_mult * (a.road_mult if a.road else 1) * (1.5 if a.forced else 1)
    print(f"{daily:.1f} miles a day, {daily * MARCH_REST:.0f} a week (one rest day)")
    warns = []
    debt = max(0, a.days_marched - MARCH_REST)
    if debt:
        warns.append(f"{debt} rest day(s) owed after {a.days_marched} days without one: -{debt} to fighting until rested")
    if a.forced:
        warns.append("forced march: -1 fatigue per forced day; each rest day clears one")
    report([], warns, f"speed {a.speed:g}")


def supply_cost(d):
    mult = d.get("multipliers", {})
    base = d.get("base_value", 1)
    total, errs = 0.0, []
    for u in d.get("units", []):
        c = d.get("costs", {}).get(u.get("type"))
        if c is None:
            errs.append(f"no cost for unit type {u.get('type')}")
            continue
        m = (mult.get("mounted", 1) if u.get("mounted") else 1) * (mult.get("meat", 1) if u.get("meat") else 1)
        total += c * m * base * u.get("count", 1)
    return total, errs


def cmd_supply(a):
    """Weekly supply cost, weighted supply line length against a cap, or foraging (levy or loot)."""
    d = load_json(a.file)
    if a.forage:
        f = d.get("forage") or die("--forage needs a forage block: families, levy_yield, loot_yield, loot_loss")
        fam = f.get("families", 0)
        if a.forage == "levy":
            print(f"levy: {fam * f.get('levy_yield', 0):g} from {fam} families, none lost")
        else:
            lost = math.ceil(fam * f.get("loot_loss", 0))
            print(f"loot: {fam * f.get('loot_yield', 0):g} from {fam} families; {lost} families lost (dead or fled)")
            print("warn: looted land yields less next season and turns the locals against you")
        return
    total, errs = supply_cost(d)
    warns = []
    print(f"weekly supply: {total:g}")
    line = d.get("line")
    if line is not None:
        length = sum(d.get("weights", {}).get(h, 1) for h in line)
        cap = d.get("line_cap")
        print(f"supply line: {len(line)} hexes, weighted {length:g}" + (f" of {cap}" if cap is not None else ""))
        if cap is not None and length > cap:
            warns.append(f"line {length:g} over the cap {cap}: out of supply")
    report(errs, warns, "supply")


def cmd_siege(a):
    """Structure points to a garrison capacity, the blockade, breaches from bombardment, and days to fall."""
    d = load_json(a.file)
    f, s = d.get("fortress", {}), d.get("siege", {})
    warns = []
    cap = f.get("structure", 0) // max(1, f.get("per_unit", 1))
    gar = f.get("garrison", 0)
    print(f"capacity {cap} unit(s), garrison {gar}")
    if gar > cap:
        warns.append(f"garrison {gar} over capacity {cap}")
    block = s.get("units", 0) + s.get("ships", 0) * s.get("ship_weight", 1) + (s.get("circumvallation_bonus", 0) if s.get("circumvallation") else 0)
    need = f.get("blockade_need", 0)
    print(f"blockade {block:g} of {need} needed")
    if block < need:
        warns.append("blockade too thin: the fortress can be resupplied")
    bomb = s.get("bombard_per_day", 0)
    if bomb and f.get("breach_at"):
        print(f"first breach after {math.ceil(f['breach_at'] / bomb)} day(s) of bombardment")
    net = s.get("advantage", 0) - f.get("advantage", 0)
    if net <= 0:
        print("no net advantage: the siege does not end by itself")
    else:
        days = math.ceil(d.get("base_days", 30) / net * f.get("site_mult", 1))
        print(f"falls in about {days} day(s) (net advantage {net:g}, site x{f.get('site_mult', 1)})")
    report([], warns, "siege")


def cmd_upkeep(a):
    """Weekly campaign tick: income minus supply and wages, treasury per week; fails a week that goes negative."""
    d = load_json(a.file)
    cost, errs = supply_cost(d)
    cost += d.get("wages", 0)
    tre = d.get("treasury", 0)
    for wk in range(1, a.weeks + 1):
        tre += d.get("income", 0) - cost
        print(f"week {wk}: +{d.get('income', 0):g} -{cost:g} = {tre:g}")
        if tre < 0 and not errs:
            errs.append(f"treasury negative in week {wk}: cut units, forage or raise income")
    report(errs, [], f"{a.weeks} week(s)")


RARITY = ("common", "uncommon", "rare", "very rare", "legendary")


def forage_check(d):
    errs, warns = [], []
    for name, t in (d.get("terrains") or {}).items():
        miss = [k for k in range(2, 13) if str(k) not in t]
        if miss:
            errs.append(f"{name}: no rows {miss}")
            continue
        rar = {k: t[str(k)].get("rarity", "common") for k in range(2, 13)}
        bad = [k for k, v in rar.items() if v not in RARITY]
        if bad:
            errs.append(f"{name}: unknown rarity on {bad}; use {', '.join(RARITY)}")
            continue
        rk = {k: RARITY.index(v) for k, v in rar.items()}
        if any(rk[k] for k in (6, 7, 8)):
            warns.append(f"{name}: rows 6-8 should be common (or route to the common table)")
        if any(rk[k] > rk[k + 1] for k in range(7, 12)) or any(rk[k] > rk[k - 1] for k in range(3, 8)):
            errs.append(f"{name}: rarity should rise from 7 toward both 2 and 12")
    return errs, warns


def cmd_forage(a):
    """Roll a forage check, 1d4 finds, each a 2d6 row on the user's terrain table; or --check the table."""
    import random
    if not a.table:
        die("forage needs --table FILE.json (terrains: {name: {'2'..'12': {item, rarity, conditions}}}, common: [...])")
    d = load_json(a.table)
    if a.check:
        errs, warns = forage_check(d)
        return report(errs, warns, f"{len(d.get('terrains', {}))} terrain(s)")
    t = (d.get("terrains") or {}).get(a.terrain)
    if t is None:
        die(f"terrain {a.terrain!r} not in the table ({', '.join(d.get('terrains', {}))})")
    rng = random.Random(a.seed)
    r = rng.randint(1, 20)
    found = r + a.mod >= a.dc
    print(f"check d20 {r} {a.mod:+d} vs {a.dc}: " + ("found something" if found else "nothing"))
    if not found:
        return
    have = {c for c, on in (("night", a.night), ("rain", a.rain)) if on}
    for i in range(rng.randint(1, 4)):
        k = rng.randint(1, 6) + rng.randint(1, 6)
        row = t.get(str(k), {})
        item = row.get("item", "?")
        if 6 <= k <= 8 and d.get("common"):
            item = rng.choice(d["common"])
        conds = set(row.get("conditions", []))
        qty = 2 if "x2" in conds else 1
        need = conds - {"x2"} - have
        if need:
            print(f"find {i + 1}: 2d6 {k} {item} needs {', '.join(sorted(need))}; nothing")
            continue
        if k in (2, 12) and d.get("rare") and rng.randint(1, 6) == 6:
            item = rng.choice(d["rare"]) + " (rare swap)"
        print(f"find {i + 1}: 2d6 {k} {qty} x {item} ({row.get('rarity', 'common')})")


def cmd_craft(a):
    """One base, up to three modifiers (none with a catalyst); DC 10 plus their values; output save DC 8 + mod."""
    import random
    ing = load_json(a.recipes).get("ingredients", {})
    mods = [m.strip() for m in (a.mods or "").split(",") if m.strip()]
    if a.base not in ing:
        die(f"base {a.base!r} not in ingredients")
    errs = [f"unknown ingredient {m}" for m in mods if m not in ing]
    if ing[a.base].get("catalyst") and mods:
        errs.append("a catalyst base takes no modifiers")
    if len(mods) > 3:
        errs.append(f"{len(mods)} modifiers, 3 at most")
    if errs:
        report(errs, [], "")
    dc = 10 + ing[a.base].get("value", 0) + sum(ing[m].get("value", 0) for m in mods)
    r = a.roll if a.roll is not None else random.Random(a.seed).randint(1, 20)
    m = r + a.mod - dc
    print(f"DC {dc}; d20 {r} {a.mod:+d}: " + (f"pass by {m}" if m >= 0 else f"fail by {-m}") + f"; save DC {8 + a.mod}")


def cmd_identify(a):
    """Identify check: a tier per 5 of margin (per 10 when rare); a failure locks retries until something changes."""
    import random
    r = a.roll if a.roll is not None else random.Random(a.seed).randint(1, 20)
    m = r + a.mod - a.dc
    if m < 0:
        print(f"d20 {r} {a.mod:+d} vs {a.dc}: fail; no retry until a new clue, tool or a day's study")
        return
    step = 10 if a.rare else 5
    print(f"d20 {r} {a.mod:+d} vs {a.dc}: pass by {m}, tier {1 + m // step} (a tier per {step})")


def cmd_sell(a):
    """Find a buyer (check), days to the buyer (die), then d% plus modifier into the user's offer bands."""
    import random
    d = load_json(a.market)
    rng = random.Random(a.seed)
    key = a.rarity or ("ingredients" if a.ingredients else None)
    if not key:
        die("sell --rarity R or --ingredients K")
    dc = (d.get("search_dc") or {}).get(key)
    if dc is None:
        die(f"no search_dc for {key}")
    r = rng.randint(1, 20)
    if r + a.mod < dc:
        print(f"buyer search d20 {r} {a.mod:+d} vs {dc}: no buyer this time")
        return
    days = roll_expr(d.get("days_die", "1d4"), rng)
    pct = rng.randint(1, 100) + a.mod + (d.get("risky_bonus", 0) if a.risky else 0)
    bands = d.get("bands") or [{"max": 999, "offer": "?"}]
    band = next((b for b in bands if pct <= b["max"]), bands[-1])
    print(f"buyer in {days} day(s); d% {pct}: offer {band['offer']}" + (f" ({a.ingredients} ingredient lot)" if a.ingredients else ""))
    if a.risky:
        print(f"risky buyer: {d.get('risk', 'the deal may go bad')}")


VARIANT_CONTROL = ("control", "dot")
VARIANT_TELL = ("damage_type", "immunity")


def cmd_variant(a):
    """Monster variant cards: base, axis (what changed), keeps, tell, counter, role. One axis at a time reads best."""
    cards = load_list(a.file, "variants")
    errs, warns = [], []
    for v in cards:
        n = v.get("name") or "?"
        axis = v.get("axis") or []
        axis = [axis] if isinstance(axis, str) else axis
        if not v.get("base"):
            errs.append(f"{n}: no base creature")
        if not axis:
            errs.append(f"{n}: no axis (what the variant changes)")
        if any(x in VARIANT_CONTROL for x in axis) and not v.get("counter"):
            errs.append(f"{n}: adds control or damage over time with no counter the players can use")
        if any(x in VARIANT_TELL for x in axis) and not v.get("tell"):
            errs.append(f"{n}: changes damage type or immunity with no tell the players can see first")
        if len(axis) > 1:
            warns.append(f"{n}: {len(axis)} axes changed ({', '.join(axis)}); one reads as a twist, more as a new monster")
        for f in ("keeps", "role"):
            if not v.get(f):
                warns.append(f"{n}: no {f}")
    report(errs, warns, f"{len(cards)} variant(s)")


CR_LADDER = list(CR_XP)


def cr_value(cr):
    num, _, den = cr.partition("/")
    return int(num) / int(den) if den else float(cr)


def cmd_template(a):
    """Apply a template to a 5e CR: step along the ladder (0, 1/8, 1/4, 1/2, 1, 2...) or scale and round up."""
    cr = {"0.125": "1/8", "0.25": "1/4", "0.5": "1/2"}.get(a.cr, a.cr)
    if cr not in CR_XP:
        die(f"unknown challenge rating: {a.cr}")
    if (a.delta is None) == (a.scale is None):
        die("give --delta N or --scale X")
    i = CR_LADDER.index(cr)
    if a.delta is not None:
        j = i + a.delta
        if j < 0:
            print(f"CR {cr} {a.delta:+d} steps falls below 0; pick a smaller step")
            sys.exit(1)
        new = CR_LADDER[min(j, len(CR_LADDER) - 1)]
    else:
        want = cr_value(cr) * a.scale
        new = next((c for c in CR_LADDER if cr_value(c) >= want - 1e-9), CR_LADDER[-1])
    if len(a.template or []) > 1:
        print(f"warn: {len(a.template)} templates stacked ({', '.join(a.template)}); the math drifts, playtest it")
    print(f"CR {cr} ({CR_XP[cr]} XP) -> CR {new} ({CR_XP[new]} XP)")


POISON_FIELDS = ("delivery", "save", "interval", "onset", "stages")


def cmd_poison(a):
    """Poison cards: delivery, save, interval, onset, stages and an end condition; DC 10-20."""
    ps = load_list(a.file, "poisons")
    errs, warns = [], []
    for p in ps:
        n = p.get("name") or "?"
        for f in POISON_FIELDS:
            if not p.get(f):
                errs.append(f"{n}: no {f}")
        if not p.get("end"):
            warns.append(f"{n}: no end condition (saves in a row, a cure, a time); it could run forever")
        dc = p.get("dc")
        if dc is not None and (not isinstance(dc, int) or not 10 <= dc <= 20):
            warns.append(f"{n}: DC {dc!r} is outside 10-20")
        pot = p.get("potency")
        if pot is not None:
            if pot not in POTENCY:
                errs.append(f"{n}: potency {pot!r}, use up or down")
            elif isinstance(dc, int):
                print(f"{n}: potency {pot}, DC {dc} -> {dc + POTENCY[pot]}")
        life, age = p.get("shelf_life"), p.get("age")
        if isinstance(life, (int, float)) and isinstance(age, (int, float)) and age > life:
            warns.append(f"{n}: dose is {age:g} days old, past its {life:g}-day shelf life; it has lost its bite")
    report(errs, warns, f"{len(ps)} poison(s)")


POTENCY = {"up": 2, "down": -2}  # our step: a stronger or weaker dose moves the DC by 2


PORTAL_FIELDS = ("location", "destination", "key", "direction", "timing")
PORTAL_DIRS = ("two-way", "one-way", "intermittent")


def cmd_handouts(a):
    """Handouts JSON {sessions_away, recap, handouts: [{name, purpose, sender}]}."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    hs = d.get("handouts", []) if isinstance(d, dict) else d
    errs, warns = [], []
    if not hs:
        die("no handouts")
    for h in hs:
        n = h.get("name") or "?"
        if not h.get("purpose"):
            errs.append(f"{n}: no purpose (the clue, lead or feeling it delivers)")
        if not h.get("sender"):
            errs.append(f"{n}: no sender (who in the world wrote or sent it)")
    if isinstance(d, dict) and (d.get("sessions_away") or 0) >= 2 and not d.get("recap"):
        warns.append(f"{d['sessions_away']} sessions since this thread came up and no recap handout; remind them first")
    report(errs, warns, f"{len(hs)} handout(s) with a purpose and a sender")


RISKS = ("low", "mid", "high")
MISSION = ("objective", "location", "group", "threat", "object", "complication")


def jrow(r):
    return r if isinstance(r, dict) else {"text": str(r)}


def jroll(rng, rows, picked):
    """Pick a row; reroll (up to 20 times) when it clashes with a part already picked."""
    rows = [jrow(r) for r in rows]
    for _ in range(20):
        r = rng.choice(rows)
        bad = {c.lower() for p in picked for c in p.get("clashes", [])} | {c.lower() for c in r.get("clashes", [])}
        if not any(p.get("text", "").lower() in bad for p in picked) and r.get("text", "").lower() not in bad:
            return r
    return r


def cmd_journey(a):
    """Roll journey leads from your own tables, or --check a lead slate."""
    import random
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    if a.check:
        return journey_check(d.get("leads", []) if isinstance(d, dict) else d)
    rng = random.Random(a.seed)
    need = ["destination", "patron", "motive", "arrival"] + (["purpose"] if a.kind == "simple" else [])
    miss = [k for k in need if not d.get(k)] + ([f"mission.{k}" for k in MISSION if not (d.get("mission") or {}).get(k)]
                                                if a.kind == "complex" else [])
    if miss:
        die("tables missing: " + ", ".join(miss))
    for i in range(1, a.leads + 1):
        picked, out = [], []
        dest = jroll(rng, d["destination"], picked)
        picked.append(dest)
        place = jroll(rng, dest["places"], picked) if dest.get("places") else None
        if place:
            picked.append(place)
        out.append("destination: " + dest["text"] + (f" / {place['text']}" if place else ""))
        parts = ["patron", "motive"] + (["purpose"] if a.kind == "simple" else [])
        for k in parts:
            r = jroll(rng, d[k], picked)
            picked.append(r)
            out.append(f"{k}: {r['text']}")
        if a.kind == "complex":
            for k in MISSION:
                r = jroll(rng, d["mission"][k], picked)
                picked.append(r)
                out.append(f"{k}: {r['text']}")
        r = jroll(rng, d["arrival"], picked)
        out.append(f"arrival: {r['text']}")
        risks = [p["risk"] for p in picked if p.get("risk") in RISKS]
        risk = max(risks, key=RISKS.index) if risks else "unrated"
        print(f"lead {i} (risk {risk}):")
        for o in out:
            print("  " + o)


def journey_check(leads):
    errs, warns = [], []
    if len(leads) < 2:
        warns.append(f"{len(leads)} lead(s); offer 2 or more so the party chooses")
    rs = [l.get("risk") for l in leads]
    for l in leads:
        n = l.get("name") or "?"
        if l.get("risk") not in RISKS:
            warns.append(f"{n}: no risk label (low, mid, high) the players can weigh")
        if not l.get("moral") and not l.get("reward"):
            warns.append(f"{n}: neither a moral stake nor a reward; nothing to weigh")
        if l.get("kind") == "complex":
            m = l.get("mission") or {}
            for k in MISSION:
                if not m.get(k):
                    (errs if k in ("objective", "location", "threat") else warns).append(f"{n}: mission has no {k}")
        elif not l.get("constraint"):
            warns.append(f"{n}: simple purpose with no travel constraint (deadline, fragile charge, quarry)")
        arr = l.get("arrival") or []
        arr = [arr] if isinstance(arr, str) else arr
        if not arr or all(any(w in str(x).lower() for w in ("pay", "paid", "fee")) for x in arr):
            warns.append(f"{n}: payment is the only arrival outcome; add a bonus, delay or a too-late result")
    if len(leads) >= 2 and len(set(rs)) == 1 and rs[0] in RISKS:
        warns.append(f"every lead is {rs[0]} risk; vary it so the choice means something")
    report(errs, warns, f"{len(leads)} lead(s)")


TRADE_BAND = "down20,down10,flat,up10,up20"  # ours, flatter than the source
TRADE_WEIGHTS = "2,4,8,4,2"  # out of 20, a d20
SECOND_BATCH = 0.8  # our cut for a batch sold into a filled market


def band_pct(step):
    step = step.strip().lower()
    if step == "flat":
        return 0
    for pre, sign in (("down", -1), ("up", 1)):
        if step.startswith(pre) and step[len(pre):].isdigit():
            return sign * int(step[len(pre):])
    die(f"band step {step!r}: use flat, upN or downN")


def cmd_trade(a):
    """Price of a regional haul: one compounding step per --step road hexes."""
    import random
    rng = random.Random(a.seed)
    band = [band_pct(x) for x in a.band.split(",")]
    try:
        weights = [int(x) for x in a.weights.split(",")]
    except ValueError:
        die("--weights as numbers, e.g. 2,4,8,4,2")
    if len(weights) != len(band) or sum(weights) < 1:
        die("--weights needs one positive number per band step")
    if a.price <= 0 or a.hexes < 0 or a.step < 1:
        die("price above 0, hexes 0 or more, step 1 or more")
    price = float(a.price)
    if not a.regional:
        print("warn: goods sold in many regions have nearer sources; no distance markup (add --regional for local goods)")
    else:
        for i in range(a.hexes // a.step):
            pct = rng.choices(band, weights)[0]
            price *= 1 + pct / 100
            print(f"step {i + 1}: {pct:+d}% -> {price:.0f}")
    if a.capacity is not None and (a.sold or 0) >= a.capacity:
        price *= SECOND_BATCH
        print(f"market filled ({a.sold} of {a.capacity}): next batch at {SECOND_BATCH:.0%}")
    print(f"price: {price:.0f} (from {a.price:g} over {a.hexes} hexes)")


CADENCE_SLACK = 1.2  # our 20% slack


def cmd_cadence(a):
    """Prep phases (name=hours) against the hours you have between sessions, with 20% slack."""
    total = 0.0
    for ph in a.phase:
        n, _, h = ph.partition("=")
        try:
            total += float(h)
        except ValueError:
            die(f"phase as name=hours, got {ph!r}")
    need = total * CADENCE_SLACK
    print(f"phases {total:g} h, with 20% slack {need:g} h; you have {a.hours:g} h every {a.every_days} days")
    if need <= a.hours:
        print("ok: it fits")
        return
    days = math.ceil(need / (a.hours / a.every_days) - 1e-9)
    print(f"error: does not fit; the shortest interval that fits at this rate is {days} days")
    sys.exit(1)


RIVAL_WATCH = ("healer", "caster", "terrain", "support", "friction", "none")
RIVAL_TACTICS = ("separate", "lure", "deny", "deceive", "attack")


def cmd_rival(a):
    """A rival party racing the PCs: members, principles, tactics with tells, a dated timeline."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    ms, tl = d.get("members", []), d.get("timeline", [])
    if len(ms) < 2:
        errs.append(f"{len(ms)} member(s); a rival party wants 2 or more")
    if not d.get("principles"):
        errs.append("no principles (the rules the rivals act by)")
    for m in ms:
        n = m.get("name") or "?"
        if m.get("watches") not in RIVAL_WATCH:
            warns.append(f"{n}: no watches (" + "|".join(RIVAL_WATCH) + "): which PC strength they answer")
        if not m.get("bond"):
            warns.append(f"{n}: no bond to the others")
    tac = d.get("tactics", [])
    if tac and all(t.get("kind") == "attack" for t in tac):
        warns.append("every tactic is attack; add separate, lure, deny or deceive")
    for t in tac:
        if not t.get("tell"):
            warns.append(f"tactic {t.get('name', '?')}: no tell the players can read")
    arr = d.get("arrival_day")
    if arr is not None and not any(isinstance(e.get("day"), int) and e["day"] < arr for e in tl):
        warns.append(f"no timeline entry before arrival_day {arr}; the rivals should leave traces first")
    if not any(e.get("site") and e.get("state") for e in tl):
        warns.append("no timeline entry changes a site's state")
    if not d.get("foreshadow"):
        warns.append("no foreshadow: where the party first sees them")
    if a.day is not None:
        state = {}
        for e in sorted(tl, key=lambda e: e.get("day", 0)):
            if e.get("day", 0) <= a.day:
                print(f"day {e.get('day')}: {e.get('event', '')}")
                if e.get("site"):
                    state[e["site"]] = e.get("state", "")
        for k, v in state.items():
            print(f"{k}: {v}")
    report(errs, warns, f"{len(ms)} rivals, {len(tl)} timeline entries")


CASCADE_OFFERS = ("money", "info", "gear")


def cmd_cascade(a):
    """A disaster opening: rows of events with fates and next links, a timer, patrons with offers."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    rows = d.get("rows", [])
    errs, warns = [], []
    if not rows:
        die("no rows")
    ids = {e.get("id") for r in rows for e in r}
    for i, r in enumerate(rows):
        if len(r) < 2:
            warns.append(f"row {i + 1}: {len(r)} event; give the party a choice of 2 or more")
        for e in r:
            if not e.get("fate"):
                errs.append(f"{e.get('id', '?')}: no fate (what happens if nobody helps)")
            for n in e.get("next", []):
                if n not in ids:
                    errs.append(f"{e.get('id', '?')}: next {n!r} is not an event")
            if i and not any(e.get("id") in p.get("next", []) for r2 in rows for p in r2):
                warns.append(f"{e.get('id', '?')}: nothing leads to it")
    kinds = {p.get("offer") for p in d.get("patrons", []) if p.get("offer") in CASCADE_OFFERS}
    if len(kinds) < 2:
        warns.append(f"{len(kinds)} patron offer kind(s); want 2+ of " + ", ".join(CASCADE_OFFERS))
    print(f"timer: {d.get('timer', 'd4 minutes')} per row")
    report(errs, warns, f"{len(rows)} rows, {len(ids)} events")


TALK_KINDS = {"trade": "something for something", "bribe": "a gift that buys the answer", "threat": "or else",
              "love": "do it because you care for me", "guilt": "you owe it for what you did", "debt": "you owe me a favour",
              "duty": "your role demands it", "identity": "someone like you would", "appearance": "think how it looks",
              "approval": "others will think well of you", "etiquette": "custom requires it", "plea": "I beg you"}


def cmd_talk(a):
    """Petitions: who asks whom for what, the opening leverage, fallbacks and a bottom line."""
    if a.list:
        for k, v in TALK_KINDS.items():
            print(f"{k}: {v}")
        return
    if not a.file:
        die("talk FILE.json, or --list")
    ts = load_list(a.file, "talks")
    errs, warns = [], []
    for t in ts:
        n = f"{t.get('petitioner', '?')} -> {t.get('granter', '?')}"
        for k in ("petitioner", "granter", "want"):
            if not t.get(k):
                errs.append(f"{n}: no {k}")
        if t.get("opening") not in TALK_KINDS:
            warns.append(f"{n}: opening {t.get('opening')!r} is not a leverage kind (talk --list)")
        fb = t.get("fallback") or []
        if str(t.get("resist", "yes")).lower() == "no":
            if fb:
                warns.append(f"{n}: resist: no with fallbacks; make it a quick answer")
        else:
            if len(fb) < 2:
                warns.append(f"{n}: {len(fb)} fallback(s); want 2 or more")
            if not t.get("bottom_line"):
                warns.append(f"{n}: no bottom_line (what the granter will never give)")
    report(errs, warns, f"{len(ts)} petition(s)")


ISLAND_BANDS = ("start", "middle", "end")


def cmd_islands(a):
    """Floating prep: islands placed where the players go. 'islands move FILE NAME --to PLACE' re-places one."""
    if a.args[0] == "move":
        if len(a.args) != 3 or not a.to:
            die("islands move FILE NAME --to PLACE")
        p = Path(a.args[1])
        d = json.loads(p.read_text(encoding="utf-8"))
        isl = d["islands"] if isinstance(d, dict) else d
        x = next((i for i in isl if i.get("name", "").lower() == a.args[2].lower()), None)
        if not x:
            die(f"no island named {a.args[2]}")
        old = x.get("at")
        x["at"] = a.to
        x.setdefault("moved", []).append(old)
        p.write_text(json.dumps(d, indent=2), encoding="utf-8", newline="\n")
        print(f"{x['name']}: {old or 'unplaced'} -> {a.to}")
        return
    isl = load_list(a.args[0], "islands")
    warns = []
    for b in ISLAND_BANDS:
        if not any(i.get("band") == b for i in isl):
            warns.append(f"no island in band {b}" + ("; the players need a goal to reach" if b == "end" else ""))
    for i in isl:
        n = i.get("name", "?")
        if len(i.get("entries") or []) < 2:
            warns.append(f"{n}: {len(i.get('entries') or [])} entry; give 2 or more ways to reach it")
        if i.get("kind") == "fight" and i.get("at") and str(i["at"]).lower() in n.lower():
            warns.append(f"{n}: fight named for its place; name it for what happens so it can move")
    report([], warns, f"{len(isl)} islands")


def cmd_portal(a):
    """Portal cards: location, destination, key, direction, timing; one-way or intermittent needs a way back."""
    ps = load_list(a.file, "portals")
    errs = []
    for p in ps:
        n = p.get("name") or "?"
        for f in PORTAL_FIELDS:
            if not p.get(f):
                errs.append(f"{n}: no {f}")
        d = p.get("direction")
        if d and d not in PORTAL_DIRS:
            errs.append(f"{n}: direction {d!r}, use {', '.join(PORTAL_DIRS)}")
        if d in ("one-way", "intermittent") and not p.get("return") and p.get("strand") != "intended":
            errs.append(f"{n}: {d} with no return route; add return or strand: intended")
    report(errs, [], f"{len(ps)} portal(s) with all five attributes")


def cmd_short(a):
    """One site, several tiers: each tier's encounter against its budget; the cache should grow tier to tier."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    if not d.get("site"):
        errs.append("no site")
    tiers = d.get("tiers") or []
    if len(tiers) < 2:
        errs.append(f"{len(tiers)} tier(s); a short runs at two or more")
    system = d.get("system", "5e")
    last = None
    for t in tiers:
        lvl, party = t.get("level"), t.get("party", 4)
        if not isinstance(lvl, int):
            errs.append(f"tier with level {lvl!r}")
            continue
        budgets = pf_budgets(party) if system != "5e" else dnd_budgets(party, lvl)
        total = 0
        for f in t.get("foes", []):
            xp, _ = foe_xp(system, str(f), lvl)
            total += xp or 0
        c = t.get("cache")
        print(f"level {lvl}: {total} XP, threat {band_for(total, budgets)}; cache {c}")
        if not isinstance(c, (int, float)):
            warns.append(f"level {lvl}: no cache value")
            continue
        if last is not None and c <= last:
            warns.append(f"level {lvl}: cache {c} does not grow from {last}")
        last = c
    report(errs, warns, f"{d.get('site')}: {len(tiers)} tiers")


def cmd_vote(a):
    """Council roll call: factions vote for, against or undecided (hidden ones show ?); the margin adds to a d20."""
    import random
    fs = load_list(a.file, "factions")
    rng = random.Random(a.seed)
    if not any(f.get("support") == "undecided" for f in fs):
        print("warn: no undecided faction; nothing for the party to win over")

    def tally(r):
        m = 0
        for f in fs:
            s = f.get("support")
            if s == "undecided":
                s = r.choice(("for", "against"))
            m += f.get("votes", 1) * (1 if s == "for" else -1 if s == "against" else 0)
        return m

    for f in fs:
        shown = "?" if f.get("hidden") else f.get("support")
        print(f"{f.get('name')}: {f.get('votes', 1)} vote(s), {shown}")
    m = tally(rng)
    r = rng.randint(1, 20)
    print(f"margin {m:+d}; d20 {r} {m:+d} = {r + m} vs DC {a.dc}: {'passes' if r + m >= a.dc else 'fails'}")
    if a.odds:
        sim = random.Random(a.seed)
        n = 10000
        wins = sum(1 for _ in range(n) if sim.randint(1, 20) + tally(sim) >= a.dc)
        print(f"odds: {100 * wins / n:.1f}% over {n} trials")


def cmd_hoard(a):
    """Treasure hoard parcels: 3 to 5, at least one magic item, at least 3 kinds."""
    ps = load_list(a.file, "parcels")
    errs, warns = [], []
    if not 3 <= len(ps) <= 5:
        warns.append(f"{len(ps)} parcels; 3 to 5 keeps a hoard memorable without a ledger")
    if not any(p.get("magic") for p in ps):
        errs.append("no magic item parcel")
    kinds = {p.get("type") for p in ps if p.get("type")}
    if len(kinds) < 3:
        errs.append(f"{len(kinds)} treasure type(s), want 3 or more (coins, gems, art, magic...)")
    report(errs, warns, f"{len(ps)} parcels, {len(kinds)} types")


GROUP_TIERS = ("all start well placed", "split start: successes ahead, failures behind", "everyone starts on the back foot")


def cmd_groupcheck(a):
    """Group check: more than half succeed, some succeed, or none; where each result starts the next scene."""
    import random
    if a.roll:
        if a.dc is None:
            die("--roll needs --dc")
        bon = [int(x) for x in (a.bonus or "0").split(",")]
        bon = (bon * a.party)[:a.party]
        rng = random.Random(a.seed)
        k = 0
        for i, b in enumerate(bon, 1):
            r = rng.randint(1, 20)
            ok = r + b >= a.dc
            k += ok
            print(f"PC {i}: d20 {r} + {b} = {r + b} {'success' if ok else 'fail'}")
    else:
        if a.successes is None:
            die("give --successes K or --roll --dc N")
        k = a.successes
    if not 0 <= k <= a.party:
        die(f"successes {k} outside 0 to {a.party}")
    tier = 0 if k * 2 > a.party else 1 if k else 2
    print(f"{k} of {a.party} succeed: {('more than half', 'some', 'none')[tier]}")
    print(f"start: {GROUP_TIERS[tier]}")
    if tier == 1:
        print(f"  {k} succeeding PC(s) pick their spot; {a.party - k} failing PC(s) start where the GM puts them")


def cmd_threshold(a):
    """Damage the party must deal in one round to break a set piece, as a guide: party x (4 + level), +20% per shield."""
    if a.apl < 1:
        die("apl must be at least 1")
    if a.shield < 0:
        die("shield must be 0 or more")
    base = a.party * (4 + a.apl)
    total = round(base * (1 + 0.2 * a.shield))
    print(f"threshold: {total} damage in one round (party {a.party} x {4 + a.apl}"
          + (f", +{a.shield * 20}% for {a.shield} shield(s)" if a.shield else "") + ")")
    print("guide only: tune it to your party's real round damage")


def cmd_convert(a):
    """Old-edition foes to stand-ins: name, treat_as, cr, tweaks, boss; flags clones and over-level foes."""
    ents = load_list(a.file, "entries")
    lo, _, hi = a.levels.partition("-")
    top = int(hi or lo)
    errs, warns, by = [], [], {}
    for e in ents:
        n = e.get("name") or "?"
        if not e.get("treat_as"):
            errs.append(f"{n}: no treat_as (the stat block it borrows)")
        cr = str(e.get("cr", "")).strip()
        cr = {"0.125": "1/8", "0.25": "1/4", "0.5": "1/2"}.get(cr, cr)
        if not cr:
            errs.append(f"{n}: no cr")
        elif cr not in CR_XP:
            errs.append(f"{n}: cr {cr!r} not on the 5e ladder")
        else:
            e["_cr"] = cr
            if cr_value(cr) > top + 2 and e.get("boss") is not True:
                warns.append(f"{n}: CR {cr} is over level {top} + 2 with no boss: true (a party of {a.levels} may not survive it)")
        if e.get("treat_as"):
            by.setdefault(e["treat_as"], []).append(e)
    for t, es in by.items():
        if len(es) >= 3 and sum(1 for e in es if e.get("tweaks")) < len(es) - 1:
            warns.append(f"{len(es)} foes use {t} with too few tweaks; they will play identically (tweak all but one)")
        crs = sorted({e["_cr"] for e in es if "_cr" in e}, key=cr_value)
        if crs:
            print(f"{t}: {len(es)} stand-in(s), " + ", ".join(f"CR {c} {CR_XP[c]} XP" for c in crs))
    report(errs, warns, f"{len(ents)} entries, {len(by)} stand-ins")


def cmd_develop(a):
    """Develop a hook into an adventure: origin, why_now, if_ignored, 2+ tier variants with encounters and rewards."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    for k, why in (("origin", "where the trouble began"), ("why_now", "why it comes to a head now")):
        if not d.get(k):
            errs.append(f"no {k} ({why})")
    if not d.get("if_ignored"):
        warns.append("no if_ignored (what happens if the party walks away)")
    vs = d.get("variants", [])
    if len(vs) < 2:
        warns.append(f"{len(vs)} variant(s); give 2+ tiers so the hook fits more than one party level")
    tiers = [v.get("tier") for v in vs]
    for t in sorted({t for t in tiers if tiers.count(t) > 1}, key=str):
        warns.append(f"tier {t} used twice")
    for v in vs:
        vn = f"tier {v.get('tier', '?')}"
        if not v.get("encounters"):
            errs.append(f"{vn}: no encounters")
        if not v.get("rewards"):
            errs.append(f"{vn}: no rewards")
        for e in v.get("encounters", []):
            en = e.get("name", "?")
            if not e.get("warning"):
                warns.append(f"{vn} {en}: no warning (a sign before it hits)")
            if not e.get("bystanders"):
                warns.append(f"{vn} {en}: no bystanders (who else is at risk)")
        for r in v.get("rewards", []):
            if not (r.get("where") or r.get("from")):
                warns.append(f"{vn} reward {r.get('name', '?')}: neither where nor from (how the party gets it)")
    report(errs, warns, f"{len(vs)} variants")


def cmd_realm(a):
    """Kingdom or region card: ruler, relations with deterrent and posture, entry, an uncontrolled place, hooks, a custom."""
    d = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs, warns = [], []
    ru = d.get("ruler") or {}
    if not ru.get("name"):
        errs.append("no ruler.name")
    if not d.get("relations"):
        errs.append("no relations (neighbours and how the realm stands with them)")
    if not ru.get("chosen_by"):
        warns.append("no ruler.chosen_by (how the ruler got the seat)")
    if not ru.get("goal"):
        warns.append("no ruler.goal")
    for r in d.get("relations", []):
        for k in ("deterrent", "posture"):
            if not r.get(k):
                warns.append(f"relation {r.get('name', '?')}: no {k}")
    if not d.get("entry"):
        warns.append("no entry (how the party arrives and what they see first)")
    places = d.get("places", [])
    if not any(p.get("controlled") is False for p in places):
        warns.append("no place with controlled: false (a hole in the crown's reach)")
    for p in places:
        if not p.get("hook"):
            warns.append(f"place {p.get('name', '?')}: no hook")
    if not (d.get("culture") or {}).get("custom"):
        warns.append("no culture.custom (one local custom the party will notice)")
    if a.strict:
        errs, warns = errs + warns, []
    report(errs, warns, f"realm with {len(places)} places")


DOOM_ADVANCE = ("encounter", "rest", "switch", "scene")
DOOM_MAX = 7  # more spaces than this and the track stops feeling close; our number


def cmd_doomtrack(a):
    """Doom track JSON: spaces with an event and a shown_by, scenes with fail_cost and cap, outcomes per solved paths."""
    import itertools
    d = load_json(a.file)
    errs, warns = [], []
    spaces = d.get("spaces") or []
    if not spaces:
        die("no spaces")
    for i, s in enumerate(spaces, 1):
        n = s.get("n", i)
        if not s.get("event"):
            errs.append(f"space {n}: no event (what happens off-screen when the track lands here)")
        elif not s.get("shown_by"):
            warns.append(f"space {n}: no shown_by; show the off-screen event through a messenger or a visible sign")
    if len(spaces) > DOOM_MAX:
        warns.append(f"{len(spaces)} spaces; over {DOOM_MAX} the doom feels far off")
    adv = d.get("advance_on")
    adv = [adv] if isinstance(adv, str) else (adv or [])
    if not adv:
        warns.append("no advance_on: say what moves the track (" + ", ".join(DOOM_ADVANCE) + ")")
    for x in adv:
        if x not in DOOM_ADVANCE:
            errs.append(f"advance_on {x!r}; use " + ", ".join(DOOM_ADVANCE))
    scenes = d.get("scenes") or []
    worst = 0
    for s in scenes[:-1]:
        cost, cap = s.get("fail_cost"), s.get("cap")
        if cost and cap is None:
            warns.append(f"{s.get('name', '?')}: fail_cost {cost} with no cap; a bad run can eat the whole track")
        worst += cap if isinstance(cap, int) else (cost or 0)
    if scenes and worst >= len(spaces):
        warns.append(f"worst case the scenes before {scenes[-1].get('name', 'the last')} cost {worst} spaces of"
                     f" {len(spaces)}; the party can lose before it reaches the last scene")
    for st in d.get("states") or []:
        b = st.get("by_space")
        if not isinstance(b, int) or not 1 <= b <= len(spaces):
            errs.append(f"state {st.get('place', '?')}: by_space {b!r}, want 1 to {len(spaces)}")
    paths, outs = d.get("paths") or [], d.get("outcomes")
    if outs is not None:
        if not paths:
            errs.append("outcomes with no paths: list the problem paths the party can solve")
        keys = {"+".join(sorted(str(p).strip() for p in k.split("+"))) if k != "none" else "none" for k in outs}
        for r in range(len(paths) + 1):
            for combo in itertools.combinations(sorted(paths), r):
                k = "+".join(combo) or "none"
                if k not in keys:
                    errs.append(f"no outcome for solved paths: {k}")
    elif len(paths) > 1:
        warns.append(f"{len(paths)} paths and no outcomes; map each mix of solved paths to a finale")
    report(errs, warns, f"{len(spaces)} spaces, {len(scenes)} scenes, worst-case scene cost {worst}")


def cmd_rumors(a):
    """Rumour or lead list JSON: each lead has a skill, a dc, what it reveals and where it points; mixed skills and DCs."""
    d = load_json(a.file)
    if isinstance(d, dict) and "rumors" in d:
        return rumor_quests(d)
    leads = d.get("leads") if isinstance(d, dict) else d
    errs, warns = [], []
    if not leads:
        die("no leads")
    for i, l in enumerate(leads, 1):
        n = l.get("name", f"lead {i}")
        for k in ("reveals", "points_to"):
            if not l.get(k):
                errs.append(f"{n}: no {k}")
        if not l.get("free") and (not l.get("skill") or not isinstance(l.get("dc"), int)):
            errs.append(f"{n}: needs a skill and an integer dc, or free: true")
        if l.get("gives_answer"):
            warns.append(f"{n}: gives the answer away; make it a clue toward it")
    skills = {l.get("skill") for l in leads if l.get("skill")}
    dcs = {l.get("dc") for l in leads if isinstance(l.get("dc"), int)}
    if len(leads) > 1 and len(skills) < 2:
        errs.append("every lead uses one skill; spread them over 2+ so more players can find one")
    if len(leads) > 1 and len(dcs) < 2:
        warns.append("every lead has the same dc; mix easy and hard ones")
    if not any(l.get("free") for l in leads):
        errs.append("no free lead (no roll): a failed set of checks must still point somewhere")
    facts = d.get("facts") if isinstance(d, dict) else None
    for f in facts or []:
        c = sum(1 for l in leads if l.get("reveals") == f)
        if c < 2:
            errs.append(f"fact {f!r}: {c} lead(s); give each key fact 2+ so one missed roll does not hide it")
    if facts:
        share = sum(1 for l in leads if l.get("reveals") in facts) / len(leads)
        if not 0.3 <= share <= 0.7:
            warns.append(f"{share:.0%} of leads point at key facts; keep it between 30% and 70% (the rest colour and false leads)")
    report(errs, warns, f"{len(leads)} leads over {len(skills)} skills and {len(dcs)} dcs")


def rumor_quests(d):
    """{quests: [id or {id}], rumors: [{text, quest, true: yes|no|later}]}: each rumour tied to a known quest."""
    quests = [q.get("id") if isinstance(q, dict) else q for q in d.get("quests") or []]
    rumors = d.get("rumors") or []
    errs, warns = [], []
    if not rumors:
        die("no rumors")
    for i, r in enumerate(rumors, 1):
        n = r.get("name", f"rumor {i}")
        q = r.get("quest")
        if not q:
            errs.append(f"{n}: no quest")
        elif quests and q not in quests:
            warns.append(f"{n}: quest {q} is not in quests")
        t = r.get("true")
        t = {True: "yes", False: "no"}.get(t, t)
        if t not in ("yes", "no", "later"):
            errs.append(f"{n}: true must be yes, no or later")
    for q in quests:
        if not any(r.get("quest") == q for r in rumors):
            warns.append(f"quest {q} has no rumour pointing at it")
    report(errs, warns, f"{len(rumors)} rumours over {len(quests)} quests")


def cmd_rest(a):
    """Hourly d20 interruption: an event on TARGET or more; each quiet hour the target drops by STEP."""
    if not 1 <= a.interrupt <= 21 or a.step < 0 or a.hours < 1:
        die("--interrupt 1 to 21, --step 0 or more, --hours 1 or more")
    quiet, exp, target = 1.0, 0.0, a.interrupt
    for h in range(1, a.hours + 1):
        p = min(max(21 - target, 0), 20) / 20
        first = quiet * p
        exp += h * first
        quiet *= 1 - p
        print(f"hour {h}: event on {max(target, 1)}+ ({p:.0%}); first event this hour {first:.1%}, quiet so far {quiet:.1%}")
        target -= a.step
    hit = 1 - quiet
    if hit:
        print(f"expected first event at hour {exp / hit:.1f} (when one comes); {hit:.1%} chance of an event in {a.hours} hours")
    else:
        print(f"no event can come in {a.hours} hours")


def cmd_burst(a):
    """Party round-one damage JSON against one target: expected damage with hit chance, first-strike bonus, HP share."""
    d = load_json(a.file)
    t = d.get("target") or {}
    ac, hp = t.get("ac"), t.get("hp")
    if not isinstance(ac, int) or not isinstance(hp, int) or hp < 1:
        die("target needs integer ac and hp")
    total = 0.0
    attackers = d.get("attackers") or []
    if not attackers:
        die("no attackers")
    for at in attackers:
        p = min(0.95, max(0.05, (21 - (ac - at.get("bonus", 0))) / 20))
        dmg = at.get("damage", 0) + (at.get("first_strike", 0) if at.get("acts_first", True) else 0)
        e = p * dmg * at.get("attacks", 1)
        total += e
        print(f"  {at.get('name', '?')}: {p:.0%} to hit, {e:.1f} expected")
    share = total / hp
    errs, warns = [], []
    if share >= 1:
        errs.append(f"round one expects {total:.1f} of {hp} HP; the target dies before it acts")
    elif share >= 0.75:
        warns.append(f"round one expects {total:.1f} of {hp} HP ({share:.0%}); it may never act")
    report(errs, warns, f"round one expects {total:.1f} of {hp} HP ({share:.0%})")


def cmd_rollout(a):
    """Staged rollout JSON for disruptive content (rumour, remnant, teacher): 3+ stages in session order, each with a gate."""
    d = load_json(a.file)
    st = d.get("stages") or []
    errs, warns = [], []
    if len(st) < 3:
        errs.append(f"{len(st)} stages; bring disruptive content in over 3+ (rumour, remnant, teacher)")
    last = 0
    for x in st:
        n, ses = x.get("name", "?"), x.get("session")
        if not isinstance(ses, int):
            errs.append(f"{n}: no session number")
        elif ses <= last:
            errs.append(f"{n}: session {ses} not after {last}")
        else:
            last = ses
        if not x.get("gate"):
            errs.append(f"{n}: no gate (what the players must do to reach the next stage)")
    if not d.get("off_switch"):
        warns.append("no off_switch: say how the GM can stop the rollout if the table dislikes it")
    report(errs, warns, f"{len(st)} stages over sessions up to {last}")


def cmd_recurring(a):
    """Recurring villain JSON: a stage per act, threat rising, an escape on every stage but the last, an end condition."""
    d = load_json(a.file)
    st = d.get("stages") or []
    errs, warns = [], []
    if len(st) < 2:
        die("need 2+ stages")
    acts = d.get("acts")
    if isinstance(acts, int) and len({x.get("act") for x in st}) < acts:
        warns.append(f"stages cover {len({x.get('act') for x in st})} of {acts} acts")
    prev = None
    for i, x in enumerate(st):
        n, th = x.get("name", f"stage {i + 1}"), x.get("threat")
        if not isinstance(th, (int, float)):
            errs.append(f"{n}: no numeric threat")
        elif prev is not None and th <= prev:
            errs.append(f"{n}: threat {th} not above the stage before ({prev})")
        else:
            prev = th
        if i < len(st) - 1 and not x.get("escape"):
            errs.append(f"{n}: no escape; say how the villain gets away so the return is fair")
    if st[-1].get("escape"):
        warns.append("the last stage has an escape; the final meeting should be able to end it")
    if not d.get("ends_when"):
        errs.append("no ends_when: what finally stops the villain")
    report(errs, warns, f"{len(st)} stages, threat rising")


def cmd_casefile(a):
    """Investigation case file JSON: leads with closed_by, minutes, beat and points_to; fits the slot, beats vary."""
    d = load_json(a.file)
    leads = d.get("leads") or []
    errs, warns = [], []
    if not leads:
        die("no leads")
    total, prev = 0, None
    for i, l in enumerate(leads, 1):
        n = l.get("name", f"lead {i}")
        if not l.get("closed_by"):
            errs.append(f"{n}: nothing closes it (closed_by)")
        if not l.get("points_to") and i < len(leads):
            warns.append(f"{n}: points nowhere; say which lead it opens")
        total += l.get("minutes", 0)
        b = l.get("beat")
        if b and b == prev:
            warns.append(f"{n}: second {b} beat in a row; vary talk, fight and explore")
        prev = b
    slot = d.get("slot_minutes")
    if isinstance(slot, int) and total > slot:
        warns.append(f"leads take {total} minutes of a {slot}-minute slot")
    report(errs, warns, f"{len(leads)} leads, {total} minutes")


def cmd_lore(a):
    """Knowledge-check ladder JSON: 3 to 5 tiers, DCs rising by 5, one tier that turns the lower ones around."""
    d = load_json(a.file)
    tiers = d.get("tiers") if isinstance(d, dict) else d
    errs, warns = [], []
    if not tiers or not 3 <= len(tiers) <= 5:
        errs.append(f"{len(tiers or [])} tiers; use 3 to 5")
    dcs = [t.get("dc") for t in tiers or []]
    for x, y in zip(dcs, dcs[1:]):
        if not (isinstance(x, int) and isinstance(y, int)) or y - x != 5:
            errs.append(f"dc {x} then {y}; step each tier up by 5")
    for t in tiers or []:
        if not t.get("reveals"):
            errs.append(f"dc {t.get('dc')}: no reveals")
    if tiers and not any(t.get("twist") for t in tiers[1:]):
        warns.append("no tier with twist: true; a high roll should change what the lower tiers meant")
    report(errs, warns, f"{len(tiers or [])} tiers")


def cmd_arc(a):
    """Adventure arc JSON: chapters with level and gold; levels never drop, rise at most 2 a chapter, finale gold share."""
    d = load_json(a.file)
    ch = d.get("chapters") or []
    errs, warns = [], []
    if not ch:
        die("no chapters")
    for x, y in zip(ch, ch[1:]):
        lx, ly = x.get("level"), y.get("level")
        if isinstance(lx, int) and isinstance(ly, int):
            if ly < lx:
                errs.append(f"{y.get('name', '?')}: level {ly} below the chapter before ({lx})")
            elif ly - lx > 2:
                warns.append(f"{y.get('name', '?')}: level jumps {ly - lx}; at most 2 a chapter")
    gold = sum(c.get("gold", 0) for c in ch)
    if gold and ch[-1].get("gold", 0) > gold / 2:
        warns.append(f"finale holds {ch[-1].get('gold', 0)} of {gold} gold; players cannot spend it during the adventure")
    report(errs, warns, f"{len(ch)} chapters, {gold} gold")


def cmd_hazard(a):
    """Multi-problem hazard round JSON: counters rising each round, deadlines, a goal and an order to read them out."""
    import math
    d = load_json(a.file)
    errs, warns = [], []
    if not d.get("goal"):
        errs.append("no goal: what the party is trying to save or stop")
    counters = d.get("counters") or []
    if len(counters) < 2:
        warns.append(f"{len(counters)} counters; a hazard round wants 2+ problems pulling the party apart")
    if not d.get("order"):
        warns.append("no order: say which counter goes up first each round")
    for c in counters:
        n = c.get("name", "?")
        start, cap, per = c.get("start", 0), c.get("cap"), c.get("per_round", 0)
        if not isinstance(cap, int):
            errs.append(f"{n}: no cap (the value at which it is lost)")
            continue
        if per and per > 0:
            rnd = max(1, math.ceil((cap - start) / per))
            extra = f" (faster if {c['extra_if']})" if c.get("extra_if") else ""
            print(f"{n}: caps in round {rnd} if nobody acts{extra}")
            if rnd < 2:
                warns.append(f"{n}: caps in round {rnd}; the party gets no turn to answer it")
        else:
            print(f"{n}: does not rise on its own")
        if not c.get("lowered_by"):
            warns.append(f"{n}: no lowered_by; name a PC action that pushes it down")
    for dl in d.get("deadlines") or []:
        print(f"deadline round {dl.get('round', '?')}: {dl.get('what', '?')}")
    report(errs, warns, f"{len(counters)} counters")


INTERROGATE_TRUTH = ("true", "half", "believed", "false")


def cmd_interrogate(a):
    """Interrogation ladder JSON: rungs of ascending dc, each with a fact and a truth tag; non-true rungs want real and revealed_at."""
    d = load_json(a.file)
    rungs = d.get("rungs", []) if isinstance(d, dict) else d
    if not rungs:
        die("no rungs")
    errs, warns, last = [], [], None
    for r in rungs:
        dc, t = r.get("dc"), str(r.get("truth", "")).lower()
        label = f"DC {dc}"
        if not isinstance(dc, int):
            errs.append(f"{label}: dc must be a number")
        elif last is not None and dc <= last:
            errs.append(f"{label}: DCs must go up rung by rung (after DC {last})")
        last = dc if isinstance(dc, int) else last
        if not r.get("fact"):
            errs.append(f"{label}: no fact")
        if t not in INTERROGATE_TRUTH:
            errs.append(f"{label}: truth {t or 'missing'}; use " + ", ".join(INTERROGATE_TRUTH))
        elif t != "true":
            for k, why in (("real", "what is actually so"), ("revealed_at", "where the party learns the real story")):
                if not r.get(k):
                    warns.append(f"{label}: {t} with no {k} ({why})")
    report(errs, warns, f"{len(rungs)} rungs")


SITE_SIGNS = 2


def cmd_site(a):
    """Site prep JSON: location, entries, upkeep, ecology, visitors; doors, drops, treasure, rumours; a clock with signs."""
    d = load_json(a.file)
    errs, warns = [], []
    if not d.get("location"):
        errs.append("no location: where the site is and how the party hears of it")
    entries = d.get("entries") or []
    if not entries:
        errs.append("no entries: how the party gets in")
    elif len(entries) < 2:
        warns.append("one entry; give a second way in (or out)")
    for k, why in (("upkeep", "who keeps the light and order"), ("ecology", "what eats, drinks and sleeps here"),
                   ("visitors", "who comes and goes")):
        if not d.get(k):
            warns.append(f"no {k} ({why})")
    for x in d.get("doors") or []:
        if x.get("locked") and not (x.get("lock") and x.get("beyond")):
            warns.append(f"door {x.get('name', '?')}: locked, wants lock (who holds the key) and beyond (why it is locked)")
    for x in d.get("drops") or []:
        if not (x.get("depth") and x.get("bottom")):
            warns.append(f"drop {x.get('name', '?')}: wants depth and bottom")
    for x in d.get("treasure") or []:
        if not x.get("guard"):
            warns.append(f"treasure {x.get('name', '?')}: no guard")
    for x in d.get("rumours") or []:
        if not isinstance(x.get("true"), bool):
            warns.append(f"rumour {x.get('text', '?')!r}: mark true: true or false")
    clock = d.get("clock")
    if clock is not None:
        turns, signs = clock.get("turns"), clock.get("signs") or []
        if not isinstance(turns, int) or turns < 1:
            errs.append(f"clock turns {turns!r}, want 1 or more")
        else:
            if len(signs) < SITE_SIGNS:
                warns.append(f"clock has {len(signs)} signs; give {SITE_SIGNS}+ so the party sees it coming")
            for s in signs:
                at = s.get("turn") if isinstance(s, dict) else None
                if isinstance(at, int) and at >= turns:
                    warns.append(f"sign at turn {at} is at or past the end ({turns}); a sign must come before it")
    report(errs, warns, f"site {d.get('location', '?')}, {len(entries)} entries")


def cmd_carry(a):
    """Carry-over foes per named group between fights: next wave is start minus killed; fleers come back as a return wave."""
    f = Path(a.file)
    d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    g = d.get(a.group)
    if a.start is not None:
        g = {"start": a.start, "killed": 0, "fled": 0}
    if g is None:
        die(f"no group {a.group!r}; set it with --start N")
    g["killed"] += a.killed
    g["fled"] += a.fled
    if g["killed"] + g["fled"] > g["start"]:
        die(f"{a.group}: killed and fled ({g['killed'] + g['fled']}) exceed the start ({g['start']})")
    d[a.group] = g
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=1), encoding="utf-8")
    left = g["start"] - g["killed"]
    print(f"{a.group}: started {g['start']}, killed {g['killed']}, fled {g['fled']}; next wave {left}")
    if g["fled"]:
        print(f"  {g['fled']} of them fled: they come back as a return wave, warned")


def chase_pursuit(a, rng):
    """Overland pursuit: each hour (station) d20+pursuer vs d20+quarry track; pursuers win, lead -1; quarry wins, +1."""
    if a.lead < 1 or a.stations < 1:
        die("--lead and --stations at least 1")
    pw = sum(1 for x in range(1, 21) for y in range(1, 21) if x + a.pursuer > y + a.quarry) / 400
    qw = sum(1 for x in range(1, 21) for y in range(1, 21) if y + a.quarry > x + a.pursuer) / 400
    dist, caught = {a.lead: 1.0}, 0.0
    for h in range(1, a.stations + 1):
        nxt = {}
        for lead, p in dist.items():
            for d, q in ((-1, pw), (1, qw), (0, 1 - pw - qw)):
                nxt[lead + d] = nxt.get(lead + d, 0) + p * q
        caught += nxt.pop(0, 0.0)
        dist = nxt
        print(f"station {h}: caught by now {caught:.1%}")
    print(f"pursuers win an hour {pw:.0%}, quarry {qw:.0%}; catch odds over {a.stations} stations {caught:.1%} (exact)")
    lead = a.lead
    for h in range(1, a.stations + 1):
        x, y = rng.randint(1, 20) + a.pursuer, rng.randint(1, 20) + a.quarry
        lead += (y > x) - (x > y)
        if lead <= 0:
            print(f"sample: caught at station {h}")
            return
    print(f"sample: not caught; lead {lead} after {a.stations} stations")


def chase_legs(a, rng):
    """Legged chase: each PC runs each leg; a failed approach costs a round, an attack or damage; complications pass on."""
    d = load_json(a.legs)
    legs = d.get("legs", []) if isinstance(d, dict) else d
    if not legs:
        die("no legs")
    names = [l.get("name") for l in legs]
    if a.start:
        if a.start not in names:
            die(f"--start {a.start!r} is not a leg: " + ", ".join(map(str, names)))
        legs = legs[names.index(a.start):]
    totals = []
    for pc in range(1, a.party + 1):
        rounds, notes, pending = 0, [], 0
        for leg in legs:
            aps = leg.get("approaches") or []
            if not aps:
                die(f"leg {leg.get('name')}: no approaches")
            ap = min(aps, key=lambda x: x.get("dc", 99))
            rounds += leg.get("rounds", 1)
            roll = rng.randint(1, 20)
            ok = roll + a.bonus >= ap.get("dc", 10) + pending
            pending = 0
            if not ok:
                fail = str(ap.get("fail", "round"))
                if fail == "round":
                    rounds += 1
                elif fail == "attack":
                    notes.append(f"{leg.get('name')}: takes an attack")
                elif fail.startswith("damage:"):
                    dice = fail[7:]
                    try:
                        n, _, s = dice.partition("d")
                        dmg = sum(rng.randint(1, int(s)) for _ in range(int(n or 1)))
                    except ValueError:
                        die(f"bad fail {fail!r}; use round, attack or damage:XdY")
                    notes.append(f"{leg.get('name')}: {dmg} damage")
                if leg.get("complications"):
                    pending = 2
                    notes.append(f"{leg.get('name')}: complication passed on (+2 DC to the next check)")
        totals.append(rounds)
        print(f"PC {pc}: {rounds} rounds" + ("; " + "; ".join(notes) if notes else ""))
    print(f"slowest PC: {max(totals)} rounds since the alarm"
          f" (feed it to: tt.py alert waves --since-alarm {max(totals)} --schedule ...)")


def alert_noise(a):
    """Noise before the alarm: hidden for --quiet rounds, a checker sets off at --check, arrives at --arrive."""
    if a.quiet is None or a.check is None or a.arrive is None or a.round is None:
        die("alert noise wants --quiet, --check, --arrive and --round")
    if not 0 <= a.quiet < a.check <= a.arrive:
        die("want --quiet < --check <= --arrive")
    r = a.round
    if r <= a.quiet:
        state = f"hidden; {a.check - r} round(s) of noise before someone comes to check"
    elif r < a.check:
        state = f"heard; a checker sets off in round {a.check}"
    elif r < a.arrive:
        state = f"checker coming; here in round {a.arrive}"
    else:
        state = "checker here: bluff them or the alarm goes up (alert raise)"
    print(f"round {r}: {state}")


def alert_waves(a):
    """What has arrived by --since-alarm R from a 'ROUND:what' schedule; COUNTxFOE entries get XP via plan_waves."""
    import re
    from types import SimpleNamespace
    if a.since_alarm is None or not a.schedule:
        die("alert waves wants --since-alarm and --schedule 'ROUND:what,...'")
    items = []
    for part in a.schedule.split(","):
        rnd, _, what = part.strip().partition(":")
        if not rnd.strip().isdigit() or not what.strip():
            die(f"bad schedule entry {part!r}; write ROUND:what")
        items.append((int(rnd), what.strip()))
    items.sort()
    here = [w for w in items if w[0] <= a.since_alarm]
    for rnd, what in here:
        print(f"arrived (round {rnd}): {what}")
    nxt = [w for w in items if w[0] > a.since_alarm]
    if nxt:
        print(f"next: round {nxt[0][0]}: {nxt[0][1]}")
    if not here:
        print(f"nothing has arrived by round {a.since_alarm}")
    counted = [f"{r}:{w}" for r, w in here if re.fullmatch(r"\d+x\S+", w)]
    if counted and a.level and a.system:
        ns = SimpleNamespace(wave=counted, prep=None, pool=None, morale="-", smart=False, escape=None,
                             system=a.system, level=a.level)
        _, xp, _ = plan_waves(ns)
        print(f"arrived XP: {xp} (add it to the last fight)")


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
            s.add_argument("--count-foe", action="append", help="DICExLEVEL: a dice-range count of one foe, e.g. 2d4x1")
            s.add_argument("--throng", action="append", help="COUNTxFOE: COUNT weak foes fought as one crowd of level or CR FOE")
            s.add_argument("--solo", action="store_true", help="one foe against the party; wants --tactics, --fallback, --terrain")
            s.add_argument("--tactics"); s.add_argument("--fallback"); s.add_argument("--terrain")
            s.add_argument("--spike", type=int, action="append", help="one foe's max burst damage in a turn; repeat per foe")
            s.add_argument("--pc-hp", type=pc_hp_arg, help="PC full HP, one number or a,b,c (the lowest counts), for --spike and --boss-dpr")
            s.add_argument("--boss-dpr", type=int, help="the boss's damage a round if every attack hits")
            s.add_argument("--exit", help="the party's way out of a fight above the top band")
            s.add_argument("--protect", help="OBJ:COUNT:HP objects the party must protect")
            s.add_argument("--attackers", help="N:DMG for --protect: N attackers, fixed DMG each a round")
            s.add_argument("--waves", action="store_true", help="sum the fight and its --wave entries as one no-rest day")
        else:
            s.add_argument("--threat", default="moderate")
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=fn)
    t = sub.add_parser("tracker", help="initiative and HP tracker")
    t.add_argument("action", choices=["init", "add", "hit", "heal", "next", "late", "cond", "effect", "clock", "poison", "countdown", "show"])
    t.add_argument("--owner", help="countdown: the combatant whose turn turns the die down")
    t.add_argument("--save-each", action="store_true", help="poison: a save every round, not only at a stage change")
    t.add_argument("--dc", type=int, help="poison: save DC shown with each save")
    t.add_argument("--potency", choices=["up", "down"], help="poison: a stronger or weaker dose, DC +/-2")
    t.add_argument("--unit", choices=["turn", "round"], default="round", help="clock: ticks on each next or at the round wrap")
    t.add_argument("--fail", action="store_true", help="clock tick: a failure ticks one extra")
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
    s.add_argument("card"); s.add_argument("--leads", type=int, default=3)
    s.add_argument("--hours", type=float, help="session length; warns on more fights than fit (1 an hour, a 4e-grid number)")
    s.add_argument("--learning", action="store_true", help="new players: 0.75 fights an hour")
    s.add_argument("--first", action="store_true", help="first session: needs ## Prologue, ## Intros and bond: lines")
    s.add_argument("--weak", help="fields you tend to skip (description,dialog,weather,time,tactics,rules,names)")
    s.add_argument("--strong", help="fields you overwrite; warns past 40 words")
    s.add_argument("--review", action="store_true", help="proofreader, director and playtester passes over ## Scenes")
    s.add_argument("--short", action="store_true", help="with --review: print the drop order")
    s.add_argument("--party", action="append", help="with --review: a character JSON to check for bypass powers")
    s.set_defaults(fn=cmd_prep)
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
    s.add_argument("card"); s.add_argument("--but", action="store_true", help="warn on NPCs with no contradiction")
    s.set_defaults(fn=cmd_npcs)
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
    s.add_argument("--dice", help="table check: the dice rolled on it, e.g. 2d10 or d100")
    s.add_argument("--filter", action="append", help="combine: keep rows where column key=value (blank or any always match)")
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
    s.add_argument("file"); s.add_argument("--roles", help="comma list of roles the party needs (else the file's roles)")
    s.set_defaults(fn=cmd_party)
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
    s.add_argument("--resolve", action="store_true", help="plan is two sides of units: resolve without a map")
    s.add_argument("--rounds", type=int, default=20); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_battle)
    s = sub.add_parser("review", help="merge highlights and weak points from session logs per player")
    s.add_argument("logs", nargs="+"); s.set_defaults(fn=cmd_review)
    s = sub.add_parser("houserules", help="check a house rules list")
    s.add_argument("file"); s.set_defaults(fn=cmd_houserules)
    s = sub.add_parser("challenge", help="check a skill challenge or long task card")
    s.add_argument("card"); s.set_defaults(fn=cmd_challenge)
    s = sub.add_parser("travel", help="days and fatigue for an overland trip")
    s.add_argument("--miles", type=float)
    s.add_argument("--watches", type=int, help="night watches: day roll, per-watch checks, chance of a night event")
    s.add_argument("--day-odds", default="1/6"); s.add_argument("--watch-odds", default="1/6")
    s.add_argument("--no-fire", action="store_true", help="a cold camp"); s.add_argument("--no-fire-odds", default="1/12", help="added per watch with no fire")
    s.add_argument("--weather-every", type=float, default=4, help="hours between weather checks")
    s.add_argument("--pace", type=float, default=24, help="miles per day on open road")
    s.add_argument("--terrain", default="road", help=", ".join(TERRAIN))
    s.add_argument("--hours", type=float, default=8, help="hours marched per day")
    s.add_argument("--known", action="store_true", help="the route is known (a guide or a map)")
    s.add_argument("--navigate", type=int, help="navigator's bonus; rolls a getting-lost check per day")
    s.add_argument("--track-age", type=int, help="days old the trail is; prints the tracking target")
    s.add_argument("--rain", action="store_true"); s.add_argument("--group", type=int, default=1, help="size of the tracked group")
    s.add_argument("--seed", type=int)
    s.add_argument("--oddity", help="JSON of colour events; draws one per journey, no repeats unless tagged repeat")
    s.set_defaults(fn=cmd_travel)
    s = sub.add_parser("journey", help="roll journey leads from your tables, or --check a lead slate")
    s.add_argument("file"); s.add_argument("--kind", choices=["simple", "complex"], default="simple")
    s.add_argument("--leads", type=int, default=3); s.add_argument("--seed", type=int)
    s.add_argument("--check", action="store_true", help="file is a lead slate to check")
    s.set_defaults(fn=cmd_journey)
    s = sub.add_parser("trade", help="price of a regional haul over road hexes")
    s.add_argument("--price", type=float, required=True); s.add_argument("--hexes", type=int, required=True)
    s.add_argument("--step", type=int, default=5); s.add_argument("--band", default=TRADE_BAND)
    s.add_argument("--weights", default=TRADE_WEIGHTS)
    s.add_argument("--capacity", type=int); s.add_argument("--sold", type=int)
    s.add_argument("--regional", action="store_true", help="goods found only in the source region")
    s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_trade)
    s = sub.add_parser("cadence", help="do your prep phases fit between sessions (20% slack)")
    s.add_argument("--every-days", type=int, required=True); s.add_argument("--hours", type=float, required=True)
    s.add_argument("--phase", nargs="+", required=True, help="name=hours, e.g. brainstorm=1 select=0.5")
    s.set_defaults(fn=cmd_cadence)
    s = sub.add_parser("rival", help="check a rival party: members, principles, tactics, timeline")
    s.add_argument("file"); s.add_argument("--day", type=int, help="print events and site states up to this day")
    s.set_defaults(fn=cmd_rival)
    s = sub.add_parser("cascade", help="check a disaster opening: rows of events, fates, patrons")
    s.add_argument("file"); s.set_defaults(fn=cmd_cascade)
    s = sub.add_parser("talk", help="check petitions: leverage, fallbacks, bottom line")
    s.add_argument("file", nargs="?"); s.add_argument("--list", action="store_true", help="print the leverage kinds")
    s.set_defaults(fn=cmd_talk)
    s = sub.add_parser("islands", help="check floating prep islands, or move one")
    s.add_argument("args", nargs="+", help="FILE, or move FILE NAME"); s.add_argument("--to")
    s.set_defaults(fn=cmd_islands)
    s = sub.add_parser("handouts", help="check handouts: purpose, in-world sender, a recap after a gap")
    s.add_argument("file"); s.set_defaults(fn=cmd_handouts)
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
    s.add_argument("--grid", type=int, help="progress-track mode: a track this long; each side moves 1-3 a round")
    s.add_argument("--legs", help="JSON legs [{name, rounds, approaches [{skill, dc, fail}], complications}]")
    s.add_argument("--start", help="--legs: the leg where the alarm went off"); s.add_argument("--party", type=int, default=4)
    s.add_argument("--bonus", type=int, default=5, help="--legs: each PC's skill bonus")
    s.add_argument("--stations", type=int, help="pursuit mode: hourly opposed track rolls for N stations")
    s.add_argument("--pursuer", type=int, default=0, help="--stations: the pursuers' track bonus")
    s.add_argument("--quarry", type=int, default=0, help="--stations: the quarry's track bonus")
    s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_chase)
    s = sub.add_parser("attendance", help="who came and what to do with absent PCs")
    s.add_argument("roster"); s.add_argument("--present", type=int, required=True)
    s.add_argument("--dynamic", choices=list(ABSENT_PCS), default="collective")
    s.set_defaults(fn=cmd_attendance)
    s = sub.add_parser("trap", help="check traps: trigger, detection, disable, effect, severity")
    s.add_argument("file"); s.add_argument("--full", action="store_true", help="also want avoid, reset and alarm")
    s.set_defaults(fn=cmd_trap)
    s = sub.add_parser("downtime", help="check downtime activities: time, cost or sink, outcomes")
    s.add_argument("file"); s.set_defaults(fn=cmd_downtime)
    s = sub.add_parser("oneshot", help="check a one-shot card: bond, plot, finish, pregens")
    s.add_argument("card"); s.set_defaults(fn=cmd_oneshot)
    s = sub.add_parser("tpk", help="what to do after a total party kill, by cause")
    s.add_argument("--cause", required=True, help="gm-error, bad-luck or player-error")
    s.add_argument("--keep-pcs", action="store_true", help="the players want their characters back")
    s.set_defaults(fn=cmd_tpk)
    s = sub.add_parser("alert", help="dungeon alert track")
    s.add_argument("action", choices=["init", "raise", "lower", "show", "noise", "waves"])
    s.add_argument("--quiet", type=int, help="noise: rounds of fighting nobody hears")
    s.add_argument("--check", type=int, help="noise: round a checker sets off"); s.add_argument("--arrive", type=int)
    s.add_argument("--round", type=int, help="noise: the round now")
    s.add_argument("--since-alarm", type=int, help="waves: rounds since the alarm")
    s.add_argument("--schedule", help="waves: 'ROUND:what,...'; COUNTxFOE entries count XP with --system and --level")
    s.add_argument("--system", choices=["pf2e", "sf2e", "5e"]); s.add_argument("--level", type=int)
    s.add_argument("--tiers", type=int, default=3); s.add_argument("--why"); s.add_argument("--by", type=int, default=1)
    s.add_argument("--merge", action="append", help="init: TIER:group+group that join forces at that tier")
    s.add_argument("--file", default=str(Path(os.environ.get("TABLEWRIGHT_HOME") or Path.home() / ".tablewright") / "alert.json"))
    s.set_defaults(fn=cmd_alert)
    s = sub.add_parser("backlog", help="check a campaign hook backlog")
    s.add_argument("file"); s.add_argument("--min", type=int, default=5); s.add_argument("--max", type=int, default=15)
    s.add_argument("--retell", type=int, default=3, help="warn when a live hook was heard more times than this")
    s.add_argument("--levelup", action="store_true", help="print a what-changed prompt per open hook")
    s.set_defaults(fn=cmd_backlog)
    s = sub.add_parser("negotiate", help="multi-step negotiation, one attitude step per exchange at most")
    s.add_argument("--start", default="neutral"); s.add_argument("--goal", choices=ATTITUDES, default="helpful")
    s.add_argument("--exchange", type=int, action="append", help="modifier for one exchange; repeat per exchange")
    s.add_argument("--rolls", type=int, nargs="*", help="use these 2d6 results in order")
    s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_negotiate)
    s = sub.add_parser("spell", help="spell cost, or check homebrew spells")
    s.add_argument("action", choices=["cost", "check"]); s.add_argument("file", nargs="?")
    s.add_argument("--tier", type=int); s.add_argument("--power", type=int); s.add_argument("--mastered", action="store_true")
    s.set_defaults(fn=cmd_spell)
    s = sub.add_parser("rewards", help="check a reward ladder: cadence lengthens, 3+ triggers, gates")
    s.add_argument("file"); s.set_defaults(fn=cmd_rewards)
    s = sub.add_parser("vendors", help="vendor tiers and reach against item prices")
    s.add_argument("vendors"); s.add_argument("prices"); s.add_argument("--wage", type=float, default=1.0)
    s.set_defaults(fn=cmd_vendors)
    s = sub.add_parser("mob", help="a mob as one stat block: big hits drop members")
    s.add_argument("--count", type=int, required=True); s.add_argument("--hp-each", type=int, required=True)
    s.add_argument("hits", nargs="*", type=int); s.set_defaults(fn=cmd_mob)
    s = sub.add_parser("hack", help="hacking difficulty from system and modifiers")
    s.add_argument("--system", choices=["own", "simple", "secure"], required=True)
    s.add_argument("--mods", nargs="*"); s.set_defaults(fn=cmd_hack)
    s = sub.add_parser("settlement", help="check a settlement card: band, civic kit, function")
    s.add_argument("card"); s.set_defaults(fn=cmd_settlement)
    s = sub.add_parser("favor", help="ask an NPC a favor, seeded")
    s.add_argument("--relation", choices=list(FAVOR_BASE), required=True)
    s.add_argument("--risk", choices=list(FAVOR_RISK), required=True); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_favor)
    s = sub.add_parser("xp", help="story and foe XP award, split among survivors")
    s.add_argument("file"); s.set_defaults(fn=cmd_xp)
    s = sub.add_parser("xp-gap", help="does an adventure's XP award reach the next level (5e)")
    s.add_argument("--party", type=int, default=4); s.add_argument("--level", type=int, required=True)
    s.add_argument("--award", type=int, required=True, help="total XP the adventure gives")
    s.add_argument("--each", action="store_true", help="the award is per PC, not split")
    s.add_argument("--xp", help="each PC's current XP, comma list (default: the level's floor)")
    s.set_defaults(fn=cmd_xp_gap)
    s = sub.add_parser("morale", help="2d10 morale check against a modified rating")
    s.add_argument("--rating", type=int); s.add_argument("--mod", action="append", help="NAME=V")
    s.add_argument("--break", dest="break_units", type=int, help="starting units: print the army break point")
    s.add_argument("--dice", choices=["2d10", "2d6"], default="2d10", help="2d6: odds of each band for 2d6 + rating + mods")
    s.add_argument("--bands", default="rout<=4,fall back<=7,hold", help="2d6 bands, low to high")
    s.add_argument("--leader-cumulative", type=int, metavar="N", help="after the leader falls, flee chance +N%% a round")
    s.add_argument("--seed", type=int); s.add_argument("--roll", type=int); s.set_defaults(fn=cmd_morale)
    s = sub.add_parser("awards", help="check per-player awards, milestones and coins in session logs")
    s.add_argument("logs", nargs="+"); s.set_defaults(fn=cmd_awards)
    s = sub.add_parser("rooms", help="check rooms: timer, threat, treat, stake, wonder, dials")
    s.add_argument("--keys", action="store_true", help="check locks and keys: orphans, a key behind its own lock")
    s.add_argument("--pieces", action="store_true", help="puzzle pieces (piece_of) must lie before the puzzle room")
    s.add_argument("file"); s.set_defaults(fn=cmd_rooms)
    s = sub.add_parser("session-end", help="rounds left and the final turns")
    s.add_argument("--seed", type=int); s.add_argument("--die", type=int, default=6)
    s.add_argument("--drop", type=int, action="append"); s.add_argument("--players", required=True)
    s.set_defaults(fn=cmd_session_end)
    s = sub.add_parser("resize", help="resize an encounter for a different party size")
    s.add_argument("--system", choices=["pf2e", "sf2e", "5e"], default="pf2e")
    s.add_argument("--level", type=int, required=True); s.add_argument("--party", type=int, required=True)
    s.add_argument("--foe", action="append", required=True, help="LVL[:role]"); s.add_argument("--to", type=int, required=True)
    s.set_defaults(fn=cmd_resize)
    s = sub.add_parser("target", help="pick a monster's target")
    s.add_argument("file"); s.add_argument("--seed", type=int); s.add_argument("--smart", action="store_true")
    s.set_defaults(fn=cmd_target)
    s = sub.add_parser("playtest", help="check a blind playtest log")
    s.add_argument("file"); s.set_defaults(fn=cmd_playtest)
    s = sub.add_parser("weather", help="weather states over hours, effects, encounters to reroll")
    s.add_argument("file"); s.add_argument("--hours", type=float, default=24); s.add_argument("--every", type=float, default=4)
    s.add_argument("--start"); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_weather)
    s = sub.add_parser("unit", help="a troop type as a unit rating, or a hero at unit scale")
    s.add_argument("--hp", type=float); s.add_argument("--block", type=int, default=10, help="HP per unit point")
    s.add_argument("--attacks", type=int, default=1); s.add_argument("--ac", type=int, default=10)
    s.add_argument("--morale", type=int, default=0); s.add_argument("--enemy-hit", type=int, help="the enemy's attack bonus")
    s.add_argument("--hero", type=int, help="hero damage per hit"); s.add_argument("--scale", type=int, default=10)
    s.add_argument("--sequences", type=int, default=1, help="hero attack sequences a round")
    s.set_defaults(fn=cmd_unit)
    s = sub.add_parser("command", help="check divisions' activation cost against leadership")
    s.add_argument("file"); s.set_defaults(fn=cmd_command)
    s = sub.add_parser("march", help="army march: miles a day and week, rest debt, forced march")
    s.add_argument("--speed", type=float, required=True, help="tactical speed in feet")
    s.add_argument("--per-mile", type=float, default=5, help="feet of speed per daily mile")
    s.add_argument("--terrain-mult", type=float, default=1); s.add_argument("--road", action="store_true")
    s.add_argument("--road-mult", type=float, default=1.5); s.add_argument("--forced", action="store_true")
    s.add_argument("--days-marched", type=int, default=0); s.set_defaults(fn=cmd_march)
    s = sub.add_parser("supply", help="army weekly supply cost and line, or --forage levy|loot")
    s.add_argument("file"); s.add_argument("--forage", choices=["levy", "loot"]); s.set_defaults(fn=cmd_supply)
    s = sub.add_parser("siege", help="siege capacity, blockade, breaches, days to fall")
    s.add_argument("file"); s.set_defaults(fn=cmd_siege)
    s = sub.add_parser("upkeep", help="weekly campaign tick: treasury against supply and wages")
    s.add_argument("file"); s.add_argument("--weeks", type=int, default=1); s.set_defaults(fn=cmd_upkeep)
    s = sub.add_parser("forage", help="forage herbs on a terrain table, or --check the table")
    s.add_argument("terrain", nargs="?"); s.add_argument("--table"); s.add_argument("--check", action="store_true")
    s.add_argument("--mod", type=int, default=0); s.add_argument("--dc", type=int, default=15)
    s.add_argument("--night", action="store_true"); s.add_argument("--rain", action="store_true")
    s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_forage)
    s = sub.add_parser("craft", help="brew: one base, up to three modifiers, DC and save DC")
    s.add_argument("--recipes", required=True); s.add_argument("--base", required=True); s.add_argument("--mods")
    s.add_argument("--mod", type=int, default=0); s.add_argument("--roll", type=int); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_craft)
    s = sub.add_parser("identify", help="identify a brew or herb: margin tiers, retry lock")
    s.add_argument("--dc", type=int, default=10); s.add_argument("--mod", type=int, default=0); s.add_argument("--rare", action="store_true")
    s.add_argument("--roll", type=int); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_identify)
    s = sub.add_parser("sell", help="find a buyer, days to them, and the offer")
    s.add_argument("--market", required=True); s.add_argument("--rarity"); s.add_argument("--ingredients", type=int)
    s.add_argument("--mod", type=int, default=0); s.add_argument("--risky", action="store_true"); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_sell)
    s = sub.add_parser("variant", help="check monster variant cards: base, axis, keeps, tell, counter, role")
    s.add_argument("file"); s.set_defaults(fn=cmd_variant)
    s = sub.add_parser("template", help="5e CR after a template: ladder steps or a scale, rounded up")
    s.add_argument("--cr", required=True); s.add_argument("--delta", type=int); s.add_argument("--scale", type=float)
    s.add_argument("--template", action="append", help="template name; repeat to stack (warns)")
    s.set_defaults(fn=cmd_template)
    s = sub.add_parser("poison", help="check poison cards: delivery, save, interval, onset, stages, end")
    s.add_argument("file"); s.set_defaults(fn=cmd_poison)
    s = sub.add_parser("portal", help="check portal cards: five attributes and a way back")
    s.add_argument("file"); s.set_defaults(fn=cmd_portal)
    s = sub.add_parser("short", help="one site at several tiers: encounter per tier, cache grows")
    s.add_argument("file"); s.set_defaults(fn=cmd_short)
    s = sub.add_parser("vote", help="council roll call with hidden support; margin adds to a d20")
    s.add_argument("file"); s.add_argument("--dc", type=int, default=10); s.add_argument("--odds", action="store_true")
    s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_vote)
    s = sub.add_parser("hoard", help="check hoard parcels: 3-5, a magic item, 3+ types")
    s.add_argument("file"); s.set_defaults(fn=cmd_hoard)
    s = sub.add_parser("groupcheck", help="group check tier and where each result starts")
    s.add_argument("--party", type=int, default=4); s.add_argument("--successes", type=int)
    s.add_argument("--roll", action="store_true"); s.add_argument("--dc", type=int)
    s.add_argument("--bonus", help="comma list of bonuses, one per PC (repeats if short)"); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_groupcheck)
    s = sub.add_parser("threshold", help="damage needed in one round to break a set piece (a guide)")
    s.add_argument("--party", type=int, default=4); s.add_argument("--apl", type=int, required=True)
    s.add_argument("--shield", type=int, default=0); s.set_defaults(fn=cmd_threshold)
    s = sub.add_parser("convert", help="check old-edition foe stand-ins: treat_as, cr, tweaks, boss")
    s.add_argument("file"); s.add_argument("--levels", default="1-3"); s.add_argument("--system", choices=["5e"], default="5e")
    s.set_defaults(fn=cmd_convert)
    s = sub.add_parser("develop", help="check a hook developed into tiered adventure variants")
    s.add_argument("file"); s.set_defaults(fn=cmd_develop)
    s = sub.add_parser("realm", help="check a kingdom or region card")
    s.add_argument("file"); s.add_argument("--strict", action="store_true", help="warnings fail too")
    s.set_defaults(fn=cmd_realm)
    s = sub.add_parser("doomtrack", help="check a doom track: spaces with events, scene costs, outcomes per solved paths")
    s.add_argument("file"); s.set_defaults(fn=cmd_doomtrack)
    s = sub.add_parser("hazard", help="check a multi-problem hazard round: counters, caps, deadlines, order")
    s.add_argument("file"); s.set_defaults(fn=cmd_hazard)
    s = sub.add_parser("site", help="check a site prep card: entries, upkeep, doors, drops, rumours, clock")
    s.add_argument("file"); s.set_defaults(fn=cmd_site)
    s = sub.add_parser("interrogate", help="check an interrogation ladder: ascending DCs, truth tags, the real story")
    s.add_argument("file"); s.set_defaults(fn=cmd_interrogate)
    s = sub.add_parser("carry", help="carry-over foes per group between fights")
    s.add_argument("group"); s.add_argument("--start", type=int, help="set the group's size")
    s.add_argument("--killed", type=int, default=0); s.add_argument("--fled", type=int, default=0)
    s.add_argument("--file", default=str(Path(os.environ.get("TABLEWRIGHT_HOME") or Path.home() / ".tablewright") / "carry.json"))
    s.set_defaults(fn=cmd_carry)
    s = sub.add_parser("rumors", help="check a lead list, or {quests, rumors} with quest and true: yes|no|later each")
    s.add_argument("file"); s.set_defaults(fn=cmd_rumors)
    s = sub.add_parser("rest", help="hourly interruption odds for a rest whose target drops each quiet hour")
    s.add_argument("--interrupt", type=int, required=True, help="d20 target for an event in hour 1")
    s.add_argument("--step", type=int, default=1, help="target drops by this each quiet hour")
    s.add_argument("--hours", type=int, default=8); s.set_defaults(fn=cmd_rest)
    s = sub.add_parser("objective", help="boss gates over a rooms JSON: flag counts and an any-order kill list")
    s.add_argument("file"); s.add_argument("--gate", action="append", help="FLAG:N, the boss appears after N rooms set FLAG")
    s.add_argument("--kill-list", help="a,b,c foes to kill in any order; reveal on the last")
    s.set_defaults(fn=cmd_objective)
    s = sub.add_parser("burst", help="party round-one expected damage against one target")
    s.add_argument("file"); s.set_defaults(fn=cmd_burst)
    s = sub.add_parser("rollout", help="check a staged rollout of disruptive content over sessions")
    s.add_argument("file"); s.set_defaults(fn=cmd_rollout)
    s = sub.add_parser("recurring", help="check a recurring villain: stages, rising threat, escapes, end condition")
    s.add_argument("file"); s.set_defaults(fn=cmd_recurring)
    s = sub.add_parser("casefile", help="check an investigation case file: closers, minutes, beats, links")
    s.add_argument("file"); s.set_defaults(fn=cmd_casefile)
    s = sub.add_parser("lore", help="check a knowledge-check ladder: 3-5 tiers, DCs up by 5, a twist tier")
    s.add_argument("file"); s.set_defaults(fn=cmd_lore)
    s = sub.add_parser("arc", help="check an adventure arc: levels per chapter, finale gold share")
    s.add_argument("file"); s.set_defaults(fn=cmd_arc)
    s = sub.add_parser("licence", help="notices for the bundled tables")
    s.set_defaults(fn=lambda a: print(LICENCE))
    a = p.parse_args(argv)
    if isinstance(getattr(a, "party", None), int) and a.party < 1:
        die("party must be at least 1")
    a.fn(a)


if __name__ == "__main__":
    main()
