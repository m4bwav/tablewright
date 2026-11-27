import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_encounter_retreat():
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "5", "--foe", "3", "--retreat", "5:0.5")
    assert r.returncode == 0, r.stdout
    assert "retreat 5 at 50% HP: award 40 XP now, 40 when it returns" in r.stdout
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "3", "--retreat", "9:0.5")
    assert "no --foe 9" in r.stdout
    assert run("encounter", "--system", "pf2e", "--level", "3", "--foe", "3", "--retreat", "3:2").returncode == 2


def test_encounter_ally_at():
    r = run("encounter", "--system", "5e", "--level", "3", "--foe", "2", "--ally-at", "5:Smith")
    assert "ally Smith joins at round 5" in r.stdout
    assert "after the 3 rounds" in r.stdout and "no --ally-if" in r.stdout
    r = run("encounter", "--system", "5e", "--level", "3", "--foe", "2", "--ally-at", "2:Smith", "--ally-if", "rescued")
    assert "joins at round 2 if rescued" in r.stdout and "warn: ally" not in r.stdout


def test_tpk_capture():
    r = run("tpk", "--capture", "the cells")
    assert r.returncode == 0, r.stderr
    assert "wakes in the cells" in r.stdout and "no --taken" in r.stdout
    r = run("tpk", "--capture", "the cells", "--taken", "swords", "--taken", "coin")
    assert "taken: swords, coin" in r.stdout and "no --taken" not in r.stdout


def test_morale_outnumbered():
    r = run("morale", "--outnumbered", "2", "--allies", "3", "--foes", "6")
    assert "breaks" in r.stdout and "no roll" in r.stdout
    r = run("morale", "--outnumbered", "2", "--allies", "3", "--foes", "5")
    assert "holds" in r.stdout
    assert run("morale", "--outnumbered", "2").returncode == 2


def test_exposure_stages():
    r = run("exposure", "--stages", "1,3,7", "--fails", "Ana=4", "--fails", "Bo=7", "--fails", "Cy=9", "--cured", "Cy")
    assert r.returncode == 0, r.stdout
    assert "Ana: 4 failed save(s), stage 2 of 3, next stage at 7" in r.stdout
    assert "Bo is at the final stage" in r.stdout
    assert "Cy: 0 failed save(s), stage 0 of 3" in r.stdout
    assert run("exposure", "--stages", "3,1").returncode == 2


def test_endings(tmp_path):
    d = {"flags": ["idol", "duke"], "removes": {"duke": ["guards"]},
         "endings": [{"when": {"idol": True}, "uses": []},
                     {"when": {"idol": False, "duke": True}, "uses": ["guards"]}]}
    r = run("endings", jw(tmp_path, "e.json", d))
    assert r.returncode == 1
    assert "no ending for idol=no, duke=no" in r.stdout and "uses guards, but duke removes" in r.stdout
    d["endings"].append({"when": {}, "uses": []})
    r = run("endings", jw(tmp_path, "f.json", d))
    assert r.returncode == 0, r.stdout
    assert "matches endings" in r.stdout


def test_legacy(tmp_path):
    d = {"item": "Oathblade", "tiers": [{"level": 3, "bonus": 1, "deed": "swear"},
                                        {"level": 5, "bonus": 3, "deed": "duel", "world_event": True}]}
    r = run("legacy", jw(tmp_path, "l.json", d))
    assert r.returncode == 0, r.stdout
    assert "over our cap of +1" in r.stdout and "not planned" in r.stdout
    d["tiers"].append({"level": 4, "bonus": 2, "deed": "x"})
    r = run("legacy", jw(tmp_path, "m.json", d))
    assert r.returncode == 1 and "does not rise" in r.stdout and "drops below" in r.stdout


def test_wander_table(tmp_path):
    rows = [{"name": "wolves", "combat": True, "weight": 4}, {"name": "pilgrims", "weight": 1}]
    r = run("wander", "--table", jw(tmp_path, "t.json", rows))
    assert "non-combat share 20%" in r.stdout and "warn: non-combat" in r.stdout
    rows[1]["weight"] = 2
    r = run("wander", "--table", jw(tmp_path, "u.json", rows))
    assert "warn: non-combat" not in r.stdout


def test_party_healer_fallback(tmp_path):
    d = {"roles": ["healer"], "pcs": [{"name": "A", "plot_tie": "x", "roles": ["tank"]}]}
    r = run("party", jw(tmp_path, "p.json", d))
    assert "no healer and no healer_fallback" in r.stdout
    d["healer_fallback"] = "potions"
    r = run("party", jw(tmp_path, "q.json", d))
    assert "healer_fallback" not in r.stdout


def test_doomtrack_rests():
    r = run("doomtrack", "--hours", "6")
    assert "0 long rest(s)" in r.stdout and "no rest fits" in r.stdout
    r = run("doomtrack", "--hours", "20", "--free-rest")
    assert "2 long rest(s)" in r.stdout and "no bite" in r.stdout
    r = run("doomtrack", "--hours", "20")
    assert "warn:" not in r.stdout
