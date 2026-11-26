import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_calendar_drift_and_order(tmp_path):
    f = jw(tmp_path, "c.json", {"groups": {
        "Scouts": [{"day": 1, "event": "leave town"}, {"day": 5, "event": "reach the ford"}],
        "Main": [{"day": 1, "event": "leave town"}, {"day": 2, "event": "camp"}]}})
    r = run("calendar", f)
    assert r.returncode == 0 and "day 5: reach the ford" in r.stdout
    assert "Main is on day 2, 3 days behind Scouts" in r.stdout
    assert "warn" not in run("calendar", f, "--drift", "4").stdout
    bad = jw(tmp_path, "b.json", {"groups": {"A": [{"day": 4}, {"day": 2}]}})
    assert run("calendar", bad).returncode == 1


def test_hirelings_base_and_roll(tmp_path):
    f = jw(tmp_path, "h.json", {"going_rate": 10, "leader_cha_mod": 2, "hirelings": [
        {"name": "Torchbearer", "pay": 15, "treatment": "good"},
        {"name": "Porter", "pay": 5, "treatment": "poor"}]})
    r = run("hirelings", f)
    assert r.returncode == 0 and "Torchbearer: loyalty 85" in r.stdout and "Porter: loyalty 20" in r.stdout
    assert "unpaid" in r.stdout and "leader-down" in r.stdout
    r = run("hirelings", f, "--roll", "Porter", "--event", "bribe", "--die", "50")
    assert "d100 50 vs 5" in r.stdout and "breaks" in r.stdout
    assert "stays loyal" in run("hirelings", f, "--roll", "Torchbearer", "--die", "40").stdout
    assert run("hirelings", f, "--roll", "Nobody").returncode == 2


def test_district_cards(tmp_path):
    f = jw(tmp_path, "d.json", [
        {"name": "Docks", "watch": "2 patrols", "bribe": "5 sp", "gate": "open", "curfew": "none", "owner": "Eel Guild"},
        {"name": "Hill", "watch": "strong"}])
    r = run("district", f)
    assert r.returncode == 0 and "[Docks] watch 2 patrols" in r.stdout
    assert "Hill: no bribe" in r.stdout and "Hill: no owner" in r.stdout and "Docks: no" not in r.stdout


def test_chase_seeded_and_table(tmp_path):
    a = run("chase", "--seed", "7")
    assert a.stdout == run("chase", "--seed", "7").stdout
    assert "caught" in a.stdout or "escaped" in a.stdout or "goes to ground" in a.stdout
    t = tmp_path / "c.txt"
    t.write_text("a wall too high;-3\n", encoding="utf-8")
    r = run("chase", "--seed", "1", "--lead", "2", "--table", t)
    assert "a wall too high" in r.stdout and "caught in round 1" in r.stdout
    assert run("chase", "--lead", "5", "--escape", "4").returncode == 2


def test_encounter_roles():
    r = run("encounter", "--system", "pf2e", "--level", "3", *sum([["--foe", "1:brute"]] * 4, []))
    assert "roles: brute 4" in r.stdout and "all brute" in r.stdout
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "1:brute", "--foe", "1 role:artillery",
            "--foe", "1:brute", "--foe", "1")
    assert "artillery 1" in r.stdout and "none 1" in r.stdout and "all brute" not in r.stdout
    assert "threat" in r.stdout


PREP = "## Opening\nrain\n\n## Leads\n- a\n- b\n- c\n\n## NPCs\n- Vel: the key\n\n## Fights\n"


def test_prep_treat_and_levers(tmp_path):
    f = tmp_path / "p.md"
    f.write_text(PREP + "- rats; out: flee; diff: easy; treat: oil jar\n"
                 "- ogre; out: bribe; diff: hard; damage: big club\n", encoding="utf-8")
    r = run("prep", f)
    assert "harder fight turns 1 lever(s) (damage)" in r.stdout
    assert "no timer and no treat" in r.stdout and "rats" not in r.stdout.split("no timer and no treat")[1].split("\n")[0]
    f.write_text(PREP + "- rats; out: flee; diff: easy; treat: oil jar\n"
                 "- ogre; out: bribe; diff: hard; damage: big club; timer: 4 rounds\n"
                 "- climax duel; out: yield; levers: damage, disruption, duration; treat: high ground\n", encoding="utf-8")
    r = run("prep", f)
    assert r.returncode == 0 and "lever" not in r.stdout and "no treat" not in r.stdout


def test_session_endings(tmp_path):
    assert "ending:" in run("session-log").stdout
    for i, e in enumerate(["hook", "ran-long", "hook"]):
        (tmp_path / f"s{i}.md").write_text(f"## Next opening\n- ending: {e}\n", encoding="utf-8")
    r = run("review", *sorted(tmp_path.glob("s*.md")))
    assert r.returncode == 0 and "endings: hook 2, ran-long 1" in r.stdout


def test_houserules_distinguishes(tmp_path):
    base = {"kind": "add", "why": "speed", "review_after": 3, "situation": "falling"}
    f = jw(tmp_path, "h.json", [{**base, "rule": "1d6 per 10 ft"}, {**base, "rule": "no damage into water"}])
    assert "rule the same situation (falling)" in run("houserules", f).stdout
    g = jw(tmp_path, "g.json", [{**base, "rule": "1d6 per 10 ft"},
                                {**base, "rule": "no damage into water", "distinguishes": "landing in deep water"}])
    assert "same situation" not in run("houserules", g).stdout


def test_prep_stakes(tmp_path):
    f = tmp_path / "p.md"
    f.write_text(PREP + "- rats; out: flee; treat: oil; stakes: assets\n"
                 "- climax ogre; out: yield; treat: ledge; levers: damage, duration; stakes: assets\n", encoding="utf-8")
    r = run("prep", f)
    assert "every rated fight risks assets" in r.stdout and "climax risks only assets" in r.stdout
    f.write_text(PREP + "- rats; stakes: lunch\n", encoding="utf-8")
    assert run("prep", f).returncode == 1


def test_review_recap_and_mid_fight(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("- ending: countdown\n- ended_mid_fight: yes\n", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("- ending: hook\n- recap: the vault is open\n", encoding="utf-8")
    r = run("review", a, b)
    assert "a.md: ended mid-fight" in r.stdout and "a.md: no recap" in r.stdout and "b.md: no recap" not in r.stdout


def test_attendance(tmp_path):
    f = jw(tmp_path, "r.json", ["Ash", "Bo", "Cy", "Di"])
    r = run("attendance", f, "--present", "2", "--dynamic", "competitive")
    assert "half or fewer" in r.stdout and "step out of the story" in r.stdout
    r = run("attendance", f, "--present", "3")
    assert "half" not in r.stdout and "collective" in r.stdout
    assert run("attendance", f, "--present", "5").returncode == 2


def test_trap(tmp_path):
    ok = {"name": "pit", "trigger": "plate", "detection": "loose dust", "disable": "wedge", "effect": "fall", "severity": "setback"}
    assert run("trap", jw(tmp_path, "t.json", [ok])).returncode == 0
    r = run("trap", jw(tmp_path, "b.json", [{"name": "dart", "trigger": "wire", "severity": "lethal"}]))
    assert r.returncode == 1 and "dart: no detection" in r.stdout and "severity 'lethal'" in r.stdout


def test_downtime(tmp_path):
    good = {"name": "run a shop", "time": "a week", "cost": "upkeep", "repeatable": True, "outcomes": "shop.csv", "hook": "a rival"}
    assert run("downtime", jw(tmp_path, "d.json", [good])).returncode == 0
    r = run("downtime", jw(tmp_path, "b.json", [{"name": "rumor", "time": "days", "repeatable": True}]))
    assert r.returncode == 1 and "no cost or sink" in r.stdout and "no outcomes table" in r.stdout


def test_npcs_major(tmp_path):
    f = tmp_path / "n.md"
    f.write_text("## NPCs\n- Vel: tall; counting coins; wants the map because debt; major: true; ideal: order; bond: her ship\n"
                 "- Rook: short; sweeping; knows a door because bored\n", encoding="utf-8")
    r = run("npcs", f)
    assert r.returncode == 1 and "Vel: major NPC with no flaw or secret" in r.stdout and "Rook" not in r.stdout
    f.write_text("## NPCs\n- Vel: tall; counting coins; wants the map because debt; major: true; ideal: order; "
                 "bond: her ship; secret: she sank it\n", encoding="utf-8")
    assert run("npcs", f).returncode == 0


def test_item_reward_condition(tmp_path):
    r = run("item", jw(tmp_path, "i.json", [{"name": "river blessing", "reward": "blessing"}]))
    assert r.returncode == 1 and "no condition or expectation" in r.stdout
    r = run("item", jw(tmp_path, "j.json", [{"name": "river blessing", "reward": "blessing", "expectation": "guard the ford"}]))
    assert r.returncode == 0
