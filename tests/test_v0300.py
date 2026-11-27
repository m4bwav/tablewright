import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def md(tmp_path, name, text):
    f = tmp_path / name
    f.write_bytes(text.encode("utf-8"))
    return f


def test_fiveroom_nine(tmp_path):
    links = {"1": ["2", "3"], "2": ["4", "5"], "3": ["5", "6"], "4": ["7"], "5": ["7", "8"],
             "6": ["8"], "7": ["9"], "8": ["9"], "9": []}
    nodes = [{"id": k, "links": v, "end": k == "9"} for k, v in links.items()]
    r = run("fiveroom", jw(tmp_path, "n.json", {"shape": "nine", "nodes": nodes}))
    assert r.returncode == 0, r.stdout
    assert "route(s) from 1 to 9" in r.stdout and "warn:" not in r.stdout
    nodes[5]["links"] = []
    r = run("fiveroom", jw(tmp_path, "d.json", {"shape": "nine", "nodes": nodes}))
    assert "node 6: dead end" in r.stdout
    r = run("fiveroom", jw(tmp_path, "s.json", {"shape": "nine", "nodes": nodes[:8]}))
    assert r.returncode == 1


def test_encounter_hazard_immune():
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "5", "--hazard", "3",
            "--hazard-type", "fire", "--immune", "fire")
    assert "only hurts the party" in r.stdout
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "5", "--hazard", "3",
            "--hazard-type", "cold", "--immune", "fire")
    assert "only hurts the party" not in r.stdout


def test_hazard_gates_and_per_pc(tmp_path):
    f = jw(tmp_path, "h.json", {"goal": "seal the rift", "order": "rift", "counters": [
        {"name": "rift", "start": 0, "start_per_pc": 1, "cap": 6, "cap_per_pc": 1, "per_round": 2,
         "lowered_by": "chant", "notice_dc": 18, "identify_dc": 15, "banish": "dismissal"},
        {"name": "storm", "cap": 5, "per_round": 1, "lowered_by": "ward", "idle_until": "round 2"}]})
    r = run("hazard", f, "--party", "4")
    assert r.returncode == 0, r.stdout
    assert "rift: start 4, cap 10 for 4 PCs" in r.stdout
    assert "identify_dc 15 is not above" in r.stdout and "banish with no on_fail" in r.stdout
    assert "storm: idle until round 2" in r.stdout
    assert run("hazard", f).returncode == 1


def test_npcs_gates_agenda(tmp_path):
    f = md(tmp_path, "n.md", "## NPCs\n"
           "- Vara: tall; counting coins; wants help because debts; secret: smuggler; tell: ink hands; "
           "revealed: guild war; notice: 15; open: 20; goals: pay debt | get out\n"
           "- Bo: short; sweeping; asks about you because lonely; open: 12\n")
    r = run("npcs", f, "--agenda")
    assert r.returncode == 0, r.stdout
    assert "notice DC 15, then open DC 20" in r.stdout
    assert "Bo: open: gate with no notice" in r.stdout and "Bo: agenda wants" in r.stdout
    assert "Vara: agenda" not in r.stdout
    bad = md(tmp_path, "b.md", "## NPCs\n- Cy: old; fishing; warns you because fear; secret: x; notice: hard\n")
    assert run("npcs", bad).returncode == 1


def test_awards_penalty_cancel(tmp_path):
    f = md(tmp_path, "s1.md", "award: Ann | penalty | | broke the oath | 0\n"
           "award: Bob | penalty | | fled | 0 | swear again at a shrine\n")
    r = run("awards", f)
    assert "penalty to Ann with no cancelled_by" in r.stdout and "penalty to Bob" not in r.stdout


def test_wander_night_bump():
    r = run("wander", "--hours", "12", "--every", "60", "--chance", "6", "--night-chance", "3", "--night-hours", "6",
            "--budget", "10")
    assert "6 day checks at 1 in 6, 6 night checks at 1 in 3: about 3.0" in r.stdout
    r = run("wander", "--bump", "3", "--run", "--seed", "1")
    assert "next check is 1 in 3" in r.stdout and r.returncode == 0
    assert run("wander", "--night-chance", "0").returncode == 2


def test_adventure_fake_choice(tmp_path):
    f = jw(tmp_path, "a.json", {"scenes": [
        {"name": "gate", "pillar": "social", "check": {"success": "hall", "fail": "hall"}},
        {"name": "hall", "pillar": "combat", "optional": True, "check": {"success": "vault", "fail": "cells"}}]})
    r = run("adventure", f)
    assert "gate: both outcomes" in r.stdout and "hall: both" not in r.stdout


def test_template_pf2e():
    assert "level 3 elite -> counts as level 4" in run("template", "--adjust", "elite", "--level", "3").stdout
    assert "level 0 elite -> counts as level 2" in run("template", "--adjust", "elite", "--level", "0").stdout
    assert "level 1 weak -> counts as level -1" in run("template", "--adjust", "weak", "--level", "1").stdout
    r = run("template", "--adjust", "elite", "--level", "3", "--party-level", "3")
    assert "level 3 against a level 3 party: 40 XP" in r.stdout and "level 4 against a level 3 party: 60 XP" in r.stdout
    assert run("template", "--adjust", "weak").returncode == 2
    assert run("template", "--delta", "1").returncode == 2


def test_battle_strength(tmp_path):
    u = {"hp": 4, "attacks": 1, "to_hit": 3, "ac": 13}
    f = jw(tmp_path, "b.json", {"sides": [{"name": "Red", "units": [u] * 4}, {"name": "Blue", "units": [u] * 4}]})
    r = run("battle", f, "--strength")
    assert r.returncode == 0 and "(even)" in r.stdout
    f = jw(tmp_path, "c.json", {"sides": [{"name": "Red", "units": [u] * 10}, {"name": "Blue", "units": [u] * 3}]})
    assert "Red is 3.3x stronger" in run("battle", f, "--strength").stdout
