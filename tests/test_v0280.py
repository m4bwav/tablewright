import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def car(**over):
    parts = {"hull": {"hp": 10, "max": 10, "function": "holds together"},
             "drive": {"hp": 4, "max": 6, "function": "movement"},
             "crew": {"hp": 5, "max": 5, "function": "weapons"}}
    parts.update(over)
    return {"name": "Skiff", "parts": parts}


def test_vehicle_check_and_hit(tmp_path):
    f = jw(tmp_path, "v.json", car())
    r = run("vehicle", "check", f)
    assert r.returncode == 0 and "drive: 4/6" in r.stdout, r.stdout
    r = run("vehicle", "hit", f, "--damage", "5", "--part", "drive")
    assert "drive disabled: no movement" in r.stdout and "warn: drive is at 0" in r.stdout, r.stdout
    assert json.loads(f.read_text(encoding="utf-8"))["parts"]["drive"]["hp"] == 0
    r = run("vehicle", "hit", f, "--damage", "1", "--seed", "3")
    assert "hit location d6" in r.stdout
    assert run("vehicle", "hit", f, "--damage", "1", "--part", "sails").returncode == 2
    two = car(); two["parts"].pop("crew")
    assert run("vehicle", "check", jw(tmp_path, "t.json", two)).returncode == 2
    bad = jw(tmp_path, "b.json", car(hull={"hp": 12, "max": 10, "function": "x"}))
    assert run("vehicle", "check", bad).returncode == 1


def test_ladder_wraps(tmp_path):
    a = tmp_path / "s1.md"
    a.write_text("\n".join(f"- ladder: deed {i}" for i in range(7)) + "\nnote: x\n", encoding="utf-8")
    b = tmp_path / "s2.md"
    b.write_text("ladder: a\nladder: b\nladder: c\nladder: d\n", encoding="utf-8")
    r = run("ladder", a, b, "--big", "a magic item")
    assert r.returncode == 0, r.stdout
    assert "step 10/10 c -> a magic item (wraps to 1)" in r.stdout, r.stdout
    assert "11 step(s), 1 big reward(s) paid, now on step 1" in r.stdout, r.stdout
    r = run("ladder", a, "--start", "2")
    assert "now on step 9 (next is 10, the big one)" in r.stdout, r.stdout


def test_spell_forge_seeded():
    r1 = run("spell", "forge", "--draws", "3", "--seed", "7")
    r2 = run("spell", "forge", "--draws", "3", "--seed", "7")
    assert r1.stdout == r2.stdout and "draw 1:" in r1.stdout
    assert r1.returncode in (0, 1)
    assert ("forged with power 3" in r1.stdout) == (r1.returncode == 0)
    outcomes = {run("spell", "forge", "--draws", "6", "--seed", str(s)).returncode for s in range(12)}
    assert outcomes == {0, 1} or outcomes == {1}
    assert run("spell", "forge", "--draws", "9").returncode == 2


def test_market_band():
    r = run("market", "--band", "village", "--price", "rope=1", "--price", "plate=400")
    assert r.returncode == 0 and "shelf goods up to 250 gp" in r.stdout and "special order" in r.stdout, r.stdout
    r = run("market", "--population", "50", "--price", "sword=500")
    assert r.returncode == 1 and "hamlet" in r.stdout, r.stdout
    assert run("market").returncode == 2


def test_shared_band_table_keeps_settlement_and_venues(tmp_path):
    card = {"name": "Mill", "size": "small town", "population": 1500, "inns": 1,
            "civic": ["authority", "council", "defence", "hall", "walls"]}
    r = run("settlement", jw(tmp_path, "s.json", card))
    assert "a town or bigger wants 2+" in r.stdout and r.returncode == 1
    r = run("venues", "--population", "300")
    assert "taverns: about 1" in r.stdout and "restaurants: about 0" in r.stdout


def test_tax():
    r = run("tax", "--lifestyle", "modest", "--band", "small town", "--period", "week")
    assert "modest: upkeep 7.00 gp, tax 0.70 gp, total 7.70 gp per week" in r.stdout, r.stdout
    r = run("tax", "--lifestyle", "wealthy", "--mult", "2", "--rate", "0.5", "--period", "day", "--people", "2")
    assert "upkeep 16.00 gp, tax 8.00 gp" in r.stdout, r.stdout
    assert len(run("tax").stdout.strip().splitlines()) == 7


def test_district_neighbours(tmp_path):
    base = {"watch": 2, "bribe": 5, "curfew": "none", "owner": "guild", "gate": "open"}
    ds = [dict(base, name="Heights", kind="noble", neighbours=["Pits"]),
          dict(base, name="Pits", kind="tannery", neighbours=["Heights"]),
          dict(base, name="Lone", kind="market")]
    r = run("district", jw(tmp_path, "d.json", ds))
    assert "Heights (noble) next to Pits (tannery)" in r.stdout and "Lone: no neighbours listed" in r.stdout, r.stdout
    assert r.stdout.count("next to") == 1
    r = run("district", jw(tmp_path, "e.json", [dict(base, name="Solo")]))
    assert "neighbours" not in r.stdout


def test_heat_law_told(tmp_path):
    f = tmp_path / "heat.json"
    r = run("heat", "crime", "Watch", "--witnesses", "4", "--file", f)
    assert "law was never told" in r.stdout, r.stdout
    r = run("heat", "told", "Watch", "--told-by", "the baker", "--file", f)
    assert "law told by: the baker" in r.stdout and "never told" not in r.stdout, r.stdout
    assert run("heat", "told", "Watch", "--file", f).returncode == 2
    r = run("heat", "crime", "Guild", "--witnesses", "5", "--file", f, "--law-threshold", "0")
    assert "never told" not in r.stdout


def test_citychange(tmp_path):
    deck = [{"name": "Bridge falls", "trigger": "flood season", "segments": 2, "event": "the east bank is cut off"},
            {"name": "New temple", "trigger": "pilgrims arrive", "segments": 4, "event": "a rival faith"}]
    f = jw(tmp_path, "c.json", deck)
    assert run("citychange", "check", f).returncode == 0
    r = run("citychange", "draw", f, "--seed", "1")
    assert "drawn:" in r.stdout and "1 active" in r.stdout, r.stdout
    run("citychange", "draw", f, "--seed", "1")
    run("citychange", "advance", f)
    r = run("citychange", "advance", f)
    assert "FILLED: Bridge falls: the east bank is cut off" in r.stdout, r.stdout
    bad = jw(tmp_path, "b.json", [{"name": "Riot", "segments": 3, "event": "x"}])
    r = run("citychange", "check", bad)
    assert r.returncode == 1 and "no trigger" in r.stdout
    assert run("citychange", "draw", bad).returncode == 1


def test_downtime_preset_networking():
    r = run("downtime", "--preset", "networking")
    assert r.returncode == 0 and "contact gained" in r.stdout and "owes you a favour" in r.stdout, r.stdout
    assert "rumour" in r.stdout and "ok: 1 downtime activity" in r.stdout
    assert run("downtime").returncode == 2
