import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def tw(tmp_path, name, text):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


def test_travel_watches():
    r = run("travel", "--watches", "3", "--watch-odds", "1/6")
    assert r.returncode == 0 and "at least one night event 42.1%" in r.stdout and "6 a day" in r.stdout
    r = run("travel", "--watches", "3", "--watch-odds", "1/6", "--no-fire", "--no-fire-odds", "1/6", "--seed", "2")
    assert "33% each (no fire)" in r.stdout and "70.4%" in r.stdout and "a fire would make it 42.1%" in r.stdout
    assert "watch 3:" in r.stdout and "day roll:" in r.stdout
    assert run("travel").returncode == 2


def test_weather(tmp_path):
    f = jw(tmp_path, "w.json", {"start": "clear", "states": {
        "clear": {"change": 1, "next": ["storm"]}, "storm": {"change": 0, "next": ["clear"], "effects": ["sight", "no fire"]}},
        "encounters": [{"name": "kite flyers", "implausible_in": ["storm"]}]})
    r = run("weather", f, "--hours", "12", "--seed", "1")
    assert "hour 0: clear" in r.stdout and "hour 4: storm (sight, no fire)" in r.stdout
    assert "reroll: kite flyers" in r.stdout
    bad = jw(tmp_path, "b.json", {"states": {"a": {"next": ["zz"]}}})
    assert run("weather", bad).returncode == 1


def test_table_check(tmp_path):
    ok = tw(tmp_path, "t.csv", "roll,result\n2-8,quiet\n9-13,tracks\n14-20,beast\n")
    r = run("table", "check", ok, "--dice", "2d10")
    assert r.returncode == 0 and "28.0%" in r.stdout
    bad = tw(tmp_path, "b.csv", "roll,result\n1-8,quiet\n8-12,x\n14-20,y\n")
    r = run("table", "check", bad, "--dice", "2d10")
    assert r.returncode == 1 and "8 is in rows" in r.stdout and "[13]" in r.stdout and "cannot roll [1]" in r.stdout
    d100 = tw(tmp_path, "d.csv", "roll,result\n1-50,a\n51-100,b\n")
    assert "50.0%" in run("table", "check", d100, "--dice", "d100").stdout


def test_table_lint(tmp_path):
    f = jw(tmp_path, "e.json", [{"name": "wolves", "hook": "howls", "truth": "starving", "check": "survival", "morale": "half"},
                                {"name": "hermit", "hook": "smoke"}])
    r = run("table", "lint", f)
    assert r.returncode == 1 and "hermit: no truth, check, morale" in r.stdout and "wolves" not in r.stdout


def test_encounter_count_foe():
    r = run("encounter", "--system", "pf2e", "--level", "1", "--foe", "1", "--count-foe", "1d6x1")
    assert "count 1d6x1: 40 / 140 / 240 XP" in r.stdout and "over the Extreme budget; cap the count" in r.stdout
    r = run("encounter", "--system", "pf2e", "--level", "1", "--foe", "1", "--count-foe", "1d2x-1")
    assert "cap the count" not in r.stdout


def test_unit_and_hero():
    r = run("unit", "--hp", "45", "--attacks", "2", "--ac", "18", "--enemy-hit", "-2")
    assert "5 point(s)" in r.stdout and "natural 20" in r.stdout and "rating 10" in r.stdout
    assert "hits on 14+ (35%)" in run("unit", "--hp", "10", "--ac", "18", "--enemy-hit", "4").stdout
    r = run("unit", "--hero", "25", "--scale", "10", "--sequences", "3")
    assert "= 2 to a unit" in r.stdout and "sequences a round: 3" in r.stdout


def test_command(tmp_path):
    d = {"general": {"cap": 1}, "divisions": [
        {"commander": "Ada", "leadership": 3, "units": [{"out_of_radius": True, "disordered": True}, {"lieutenant": True}]},
        {"commander": "Bo", "leadership": 2, "units": [{}, {}]}]}
    r = run("command", jw(tmp_path, "c.json", d))
    assert r.returncode == 1 and "2 divisions, the general can lead 1" in r.stdout
    assert "Ada needs 4" in r.stdout and "Bo has no spare points" in r.stdout


def test_morale_break_and_2d6():
    r = run("morale", "--break", "10")
    assert "losing 4 of 10" in r.stdout
    r = run("morale", "--dice", "2d6", "--rating", "0", "--bands", "rout<=4,fall back<=7,hold")
    assert "rout: 16.7%" in r.stdout and "fall back: 41.7%" in r.stdout and "hold: 41.7%" in r.stdout
    assert run("morale").returncode == 2
    assert "holds" in run("morale", "--rating", "12", "--roll", "12").stdout


def test_battle_resolve(tmp_path):
    strong = {"name": "Red", "units": [{"name": f"r{i}", "attacks": 4, "to_hit": 8, "ac": 15, "hp": 3} for i in range(3)]}
    weak = {"name": "Blue", "units": [{"name": f"b{i}", "attacks": 1, "to_hit": 0, "ac": 10, "hp": 1} for i in range(6)]}
    r = run("battle", jw(tmp_path, "b.json", {"sides": [strong, weak]}), "--resolve", "--seed", "1")
    assert r.returncode == 0 and "Blue breaks" in r.stdout and "break point 2" in r.stdout
    assert r.stdout.count("pursuit:") == 3


def test_march():
    r = run("march", "--speed", "120", "--road", "--days-marched", "8")
    assert "36.0 miles a day, 216 a week" in r.stdout and "2 rest day(s) owed" in r.stdout
    assert "forced march" in run("march", "--speed", "60", "--forced", "--terrain-mult", "0.5").stdout


ARMY = {"base_value": 2, "multipliers": {"mounted": 3, "meat": 2},
        "costs": {"foot": 1, "horse": 1}, "units": [{"type": "foot", "count": 4}, {"type": "horse", "count": 1, "mounted": True}],
        "weights": {"road": 0.5, "wild": 2}, "line": ["road", "road", "wild", "wild"], "line_cap": 4,
        "forage": {"families": 10, "levy_yield": 1, "loot_yield": 3, "loot_loss": 0.25}}


def test_supply_and_forage_levy(tmp_path):
    f = jw(tmp_path, "a.json", ARMY)
    r = run("supply", f)
    assert "weekly supply: 14" in r.stdout and "weighted 5 of 4" in r.stdout and "out of supply" in r.stdout
    assert "levy: 10 from 10 families, none lost" in run("supply", f, "--forage", "levy").stdout
    assert "loot: 30 from 10 families; 3 families lost" in run("supply", f, "--forage", "loot").stdout
    assert run("supply", jw(tmp_path, "x.json", {"units": [{"type": "elf"}]})).returncode == 1


def test_siege(tmp_path):
    d = {"base_days": 60, "fortress": {"structure": 100, "per_unit": 20, "garrison": 6, "blockade_need": 10,
                                       "breach_at": 50, "advantage": 1, "site_mult": 2},
         "siege": {"units": 5, "ships": 2, "ship_weight": 1, "circumvallation": True, "circumvallation_bonus": 2,
                   "bombard_per_day": 15, "advantage": 4}}
    r = run("siege", jw(tmp_path, "s.json", d))
    assert "capacity 5" in r.stdout and "garrison 6 over capacity 5" in r.stdout
    assert "blockade 9 of 10" in r.stdout and "after 4 day(s)" in r.stdout and "about 40 day(s)" in r.stdout


def test_upkeep(tmp_path):
    f = jw(tmp_path, "u.json", {**ARMY, "treasury": 20, "income": 10, "wages": 2})
    r = run("upkeep", f, "--weeks", "4")
    assert "week 1: +10 -16 = 14" in r.stdout and r.returncode == 1 and "negative in week 4" in r.stdout


def herbs(rare_at_7=False):
    rows = {str(k): {"item": f"h{k}", "rarity": "common"} for k in range(2, 13)}
    for k in (2, 12):
        rows[str(k)] = {"item": f"h{k}", "rarity": "rare", "conditions": ["night"]}
    for k in (3, 11):
        rows[str(k)]["rarity"] = "uncommon"
    if rare_at_7:
        rows["7"]["rarity"] = "rare"
    return {"terrains": {"marsh": rows}, "common": ["reed"], "rare": ["star moss"]}


def test_forage(tmp_path):
    f = jw(tmp_path, "h.json", herbs())
    assert run("forage", "--table", f, "--check").returncode == 0
    r = run("forage", "--table", jw(tmp_path, "bad.json", herbs(True)), "--check")
    assert r.returncode == 1 and "rise from 7" in r.stdout and "rows 6-8" in r.stdout
    r = run("forage", "marsh", "--table", f, "--mod", "20", "--seed", "3")
    assert "found something" in r.stdout and "find 1:" in r.stdout
    assert run("forage", "marsh", "--table", f, "--mod", "20", "--seed", "3").stdout == r.stdout
    assert "nothing" in run("forage", "marsh", "--table", f, "--mod", "-30", "--seed", "3").stdout
    assert run("forage", "dune", "--table", f).returncode == 2


def test_craft_identify_sell(tmp_path):
    rec = jw(tmp_path, "r.json", {"ingredients": {"root": {"value": 2}, "salt": {"value": 1}, "ash": {"value": 3},
                                                  "spark": {"value": 5, "catalyst": True}}})
    r = run("craft", "--recipes", rec, "--base", "root", "--mods", "salt,ash", "--mod", "4", "--roll", "12")
    assert "DC 16; d20 12 +4: pass by 0; save DC 12" in r.stdout
    assert run("craft", "--recipes", rec, "--base", "spark", "--mods", "salt").returncode == 1
    assert run("craft", "--recipes", rec, "--base", "root", "--mods", "salt,ash,salt,ash").returncode == 1
    assert "tier 3" in run("identify", "--dc", "10", "--roll", "20").stdout
    assert "tier 2" in run("identify", "--dc", "10", "--roll", "20", "--rare").stdout
    assert "no retry" in run("identify", "--dc", "15", "--roll", "3").stdout
    m = jw(tmp_path, "m.json", {"search_dc": {"rare": 5, "ingredients": 30}, "days_die": "1d4",
                                "bands": [{"max": 50, "offer": "half"}, {"max": 999, "offer": "full"}],
                                "risky_bonus": 20, "risk": "may be a thief"})
    r = run("sell", "--market", m, "--rarity", "rare", "--mod", "10", "--risky", "--seed", "1")
    assert "buyer in" in r.stdout and "may be a thief" in r.stdout
    assert "no buyer" in run("sell", "--market", m, "--ingredients", "3", "--seed", "1").stdout
    assert run("sell", "--market", m).returncode == 2
