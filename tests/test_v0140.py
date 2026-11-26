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


PARTY = [{"name": "Ann", "level": 3, "xp_to_next": 2000}, {"name": "Bo", "level": 3, "xp_to_next": 2000},
         {"name": "Cy", "level": 3, "xp_to_next": 2000, "alive": False}]


def test_xp(tmp_path):
    foes = [{"name": "orc1", "xp": 100, "outcome": "killed"},
            {"name": "gob1", "xp": 50, "outcome": "routed", "group": "g"},
            {"name": "gob2", "xp": 50, "outcome": "routed", "group": "g"},
            {"name": "rat", "xp": 10, "outcome": "killed", "overmatched": True},
            {"name": "ghost", "xp": 500, "outcome": "persuaded", "faced": False}]
    r = run("xp", jw(tmp_path, "ok.json", {"party": PARTY, "foes": foes, "story": 100}))
    assert r.returncode == 0, r.stdout
    assert "foe XP 150 + story 100 = 250: 125 each to Ann, Bo" in r.stdout
    assert "already counted" in r.stdout and "overmatched" in r.stdout
    r = run("xp", jw(tmp_path, "big.json", {"party": [{**PARTY[0], "xp_to_next": 1500}] + PARTY[1:], "foes": foes, "story": 160}))
    assert r.returncode == 1 and "more than the foe XP 150" in r.stdout and "over 1/10 of Ann" in r.stdout and "of Bo" not in r.stdout
    r = run("xp", jw(tmp_path, "bad.json", {"party": PARTY, "foes": [{"name": "x", "xp": 5, "outcome": "fled"}]}))
    assert r.returncode == 1 and "outcome fled" in r.stdout


def test_morale():
    r = run("morale", "--rating", "12", "--mod", "leader=2", "--mod", "losses=-3", "--roll", "12")
    assert "2d10 12 vs 11: breaks" in r.stdout
    assert "holds" in run("morale", "--rating", "12", "--roll", "12").stdout
    a = run("morale", "--rating", "10", "--seed", "4").stdout
    assert a == run("morale", "--rating", "10", "--seed", "4").stdout and "2d10" in a
    assert run("morale", "--rating", "10", "--mod", "x=y").returncode == 2


def test_awards(tmp_path):
    l1 = tw(tmp_path, "s1.md", "award: Ann | xp | str | broke the gate | 50\naward: Ann | xp | str | again | 50\n"
            "milestone: Bo\ncoins: Ann 6\n")
    l2 = tw(tmp_path, "s2.md", "milestone: Bo\n")
    l3 = tw(tmp_path, "s3.md", "award: Bo | xp | wis | | 10\n")
    r = run("awards", l1, l2, l3)
    assert r.returncode == 1 and "award to Bo has no reason" in r.stdout
    assert "Ann got str awarded twice" in r.stdout and "Ann got 6 coins" in r.stdout
    assert "Ann: no milestone in the last 3 logs" in r.stdout and "Bo: no milestone" not in r.stdout
    assert run("awards", l1, l2).returncode == 0


def test_loot_owner(tmp_path):
    base = {"gold": 10, "pcs": [{"name": "Ann"}],
            "items": [{"name": "Wand", "kind": "consumable", "magic": True}, {"name": "Sword", "kind": "consumable"}]}
    r = run("loot", jw(tmp_path, "a.json", {**base, "owner": {"intelligent": True, "can_use": ["wand"]}}))
    assert r.returncode == 0 and "Wand: an intelligent owner would use it" in r.stdout and "Sword: an" not in r.stdout
    r = run("loot", jw(tmp_path, "b.json", {**base, "owner": {"intelligent": False, "random": True}}))
    assert "Wand: a random unintelligent monster" in r.stdout and "Sword: a random" not in r.stdout
    assert "warn" not in run("loot", jw(tmp_path, "c.json", base)).stdout


def test_rooms(tmp_path):
    room = {"timer": "3 rounds", "threat": "trolls", "treat": "chest", "stake": "the map", "wonder": "a glowing pool",
            "damage": 3, "disruption": 2, "duration": 2}
    ok = jw(tmp_path, "ok.json", {"rooms": [{**room, "name": "A", "enemies": True}, {**room, "name": "B"}]})
    r = run("rooms", ok)
    assert r.returncode == 0 and "warn" not in r.stdout
    rooms = [{**room, "name": n, "enemies": True} for n in "ABCDE"]
    rooms[0] = {"name": "A", "threat": "x", "enemies": True, "difficulty": "hard"}
    rooms[1]["damage"] = 9
    r = run("rooms", jw(tmp_path, "bad.json", {"rooms": rooms}))
    assert r.returncode == 1
    assert "A: no timer, treat" in r.stdout and "A: no stake" in r.stdout and "A: hard with every dial at 1" in r.stdout
    assert "B: damage 9" in r.stdout and "C: third room in a row" in r.stdout and "5 rooms" in r.stdout


def test_tracker_clock(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Hero:15:10", "Orc:10:8", "--file", f)
    run("tracker", "clock", "Fuse", "2", "--unit", "turn", "--file", f)
    run("tracker", "clock", "Flood", "2", "--unit", "round", "--file", f)
    r = run("tracker", "next", "--file", f)
    assert "clock Fuse: 1" in r.stdout and "clock Flood: 2" in r.stdout
    r = run("tracker", "next", "--file", f)
    assert "clock Fuse fires" in r.stdout and "clock Flood: 1" in r.stdout
    r = run("tracker", "clock", "tick", "Flood", "--fail", "--file", f)
    assert "clock Flood fires" in r.stdout
    assert run("tracker", "clock", "tick", "Nope", "--file", f).returncode == 2


def test_session_end():
    r = run("session-end", "--seed", "3", "--die", "6", "--drop", "1", "--players", "A,B,C")
    assert "final turns: A, B, C" in r.stdout and "d6 1:" not in r.stdout
    for s in range(20):
        assert "d6 1:" not in run("session-end", "--seed", s, "--drop", "1", "--players", "A").stdout
    assert run("session-end", "--die", "2", "--drop", "1", "--drop", "2", "--players", "A").returncode == 2


def test_resize():
    r = run("resize", "--level", "3", "--party", "4", "--foe", "3:soldier", "--foe", "3:controller", "--foe", "2:brute", "--to", "3")
    assert r.returncode == 0 and "cut: level 3 controller" in r.stdout
    assert "before: 4 PCs, 110 XP" in r.stdout and "after: 3 PCs, 70 XP" in r.stdout
    r = run("resize", "--level", "3", "--party", "4", "--foe", "3", "--foe", "3", "--to", "6")
    assert "add: level 3 brute" in r.stdout and "add: level 3 soldier" in r.stdout and "after: 6 PCs, 160 XP" in r.stdout
    r = run("resize", "--level", "3", "--party", "5", "--foe", "6:solo", "--to", "4")
    assert r.returncode == 2 and "lower its level" in r.stderr
    r = run("resize", "--system", "5e", "--level", "3", "--party", "4", "--foe", "1", "--foe", "1:skirmisher", "--to", "3")
    assert "cut: level 1 skirmisher" in r.stdout and "after: 3 PCs, 200 XP" in r.stdout


def test_target(tmp_path):
    pcs = [{"name": "Ann", "threat": 1, "reach": 1}, {"name": "Bo", "threat": 3, "reach": 2},
           {"name": "Cy", "threat": 3, "reach": 2}]
    f = jw(tmp_path, "t.json", {"pcs": pcs})
    assert "target: Ann (easiest to reach)" in run("target", f, "--seed", "1").stdout
    r = run("target", f, "--seed", "1", "--smart")
    assert "tie among Bo, Cy, rolled" in r.stdout
    assert r.stdout == run("target", f, "--seed", "1", "--smart").stdout
    m = jw(tmp_path, "m.json", {"pcs": pcs[:2] + [{**pcs[2], "marked": True}]})
    assert "target: Cy (marked it)" in run("target", m, "--smart").stdout


def test_prep_hours_first(tmp_path):
    base = "## Opening\nx\n## Leads\n- a\n- b\n- c\n## NPCs\n- Bob: gold\n## Fights\n- f1 out: run\n- f2 out: run\n- f3 out: run\n"
    c = tw(tmp_path, "c.md", base)
    r = run("prep", c, "--hours", "3", "--learning")
    assert "3 fights in 3 h" in r.stdout and "no ## Recap" in r.stdout
    assert "fights in" not in run("prep", c, "--hours", "3").stdout
    r = run("prep", c, "--first")
    assert r.returncode == 1 and "no ## Prologue" in r.stdout and "no bond: line" in r.stdout
    ok = tw(tmp_path, "ok.md", base + "## Prologue\nstorm\n## Intros\n- Ann bond: owes Bo\n")
    r = run("prep", ok, "--first", "--hours", "4")
    assert r.returncode == 0 and "Recap" not in r.stdout


def test_playtest(tmp_path):
    ok = {"new_group": True, "questions": [{"text": "can I move twice?", "section": "4.2"}],
          "debrief": {"fun": "trading", "trouble": "setup", "improvements": "shorter rules"}, "player_counts": [3, 4]}
    assert run("playtest", jw(tmp_path, "ok.json", ok)).returncode == 0
    bad = {"new_group": False, "questions": [{"text": "q", "answered": True}], "debrief": {"fun": "x"}}
    r = run("playtest", jw(tmp_path, "bad.json", bad))
    assert r.returncode == 1
    for s in ("not a new group", "observer answered", "no rule section", "no trouble", "no improvements", "no player_counts"):
        assert s in r.stdout
