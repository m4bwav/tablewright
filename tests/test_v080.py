import json

from test_tt import enc, run


def test_encounter_waves_pool_prep_and_morale():
    r, d = enc("--system", "pf2e", "--level", "3", "--foe", "3",
               "--wave", "2:2x2", "--wave", "4:3x2:bridge", "--pool", "4")
    assert d["xp_with_waves"] > d["xp"]
    w = " ".join(d["warnings"])
    assert "defender pool" in w and "--morale" in w
    r, d = enc("--system", "pf2e", "--level", "3", "--foe", "3",
               "--wave", "2:2x2", "--wave", "4:3x2:bridge", "--pool", "4",
               "--prep", "bridge", "--prep", "bribe", "--morale", "half")
    w = " ".join(d["warnings"])
    assert "defender pool" not in w and "--morale" not in w and "'bribe' removes no wave" in w
    assert [x["removed"] for x in d["waves"]] == [False, True]


def test_encounter_smart_foes_need_escape():
    _, d = enc("--system", "5e", "--level", "3", "--foe", "2", "--smart")
    assert any("escape" in w for w in d["warnings"])
    _, d = enc("--system", "5e", "--level", "3", "--foe", "2", "--smart", "--escape", "back tunnel")
    assert not any("escape" in w for w in d["warnings"])


def test_identical_hazards_diminish():
    _, one = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--hazard", "3")
    _, four = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--hazard", "3", "--hazard", "3", "--hazard", "3", "--hazard", "3")
    _, mixed = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--hazard", "3", "--hazard", "2")
    assert one["xp"] == 80 and four["xp"] == 92 and mixed["xp"] == 110
    assert any("x4" in n for n in four["notes"])


def test_prep_repeated_hazards_warn(tmp_path):
    card = tmp_path / "c.md"
    card.write_text("## Opening\nx\n## Leads\n- a\n- b\n- c\n## NPCs\n- Ann: food\n## Hazards\n"
                    "- Pit trap: warned: old map\n- Pit trap: warned: bones\n", encoding="utf-8")
    r = run("prep", card)
    assert r.returncode == 0 and "2 hazards named 'pit trap'" in r.stdout


def test_table_die_faces(tmp_path):
    t = tmp_path / "w.csv"
    t.write_text("roll,step\n1-2,down\n3-4,hold\n5-6,up\n", encoding="utf-8")
    assert "warn" not in run("table", t).stdout
    r = run("table", t, "--die", "8")
    assert r.returncode == 0 and "d8" in r.stdout
    t.write_text("roll,step\n1-2,down\n3-4,hold\n5-7,up\n", encoding="utf-8")
    assert "not a standard die" in run("table", t).stdout
    t.write_text("roll,step\n1-3,down\n3-4,hold\n6,up\n", encoding="utf-8")
    r = run("table", t, "--die", "6")
    assert r.returncode == 1 and "overlaps" in r.stdout and "no row: [5]" in r.stdout


def test_threads_stale(tmp_path):
    card = tmp_path / "t.md"
    card.write_text("## Threads\n- the stolen bell: open (opened: session 1)\n- the map: open (opened: session 5)\n"
                    "- the debt: paid (opened: session 1)\n", encoding="utf-8")
    r = run("threads", card)
    assert "the stolen bell: open 4 sessions" in r.stdout and "the map: open" not in r.stdout and "the debt" not in r.stdout.split("warn")[-1]
    assert "1 paid, 2 open" in r.stdout
    assert "warn" not in run("threads", card, "--stale", "5").stdout
    assert "the map: open 4" in run("threads", card, "--session", "9").stdout


def test_session_log_feeds_threads(tmp_path):
    r = run("session-log", "--session", "4")
    assert r.returncode == 0 and "# Session 4 log" in r.stdout and "(opened: session 4)" in r.stdout
    f = tmp_path / "log.md"
    f.write_text(r.stdout, encoding="utf-8")
    assert "0 paid, 1 open" in run("threads", f).stdout


def test_campaign_arc(tmp_path):
    p = tmp_path / "c.json"
    base = {"pcs": ["Ana"], "adventures": [{"name": "A", "phase": "1", "why": "w", "plotline": ["Ana"], "opposed_by": "x"}]}
    good = dict(base, events=[{"name": "Fire", "trigger": "bell stolen", "level": 2}, {"name": "Siege", "trigger": "fire", "level": 4}],
                climax={"trigger": "siege lost", "level": 6, "session": 10,
                        "signs": [{"text": "ash", "session": 2}, {"text": "crows", "session": 5}, {"text": "drums", "session": 8}]})
    p.write_text(json.dumps(good), encoding="utf-8")
    r = run("campaign", p)
    assert r.returncode == 0, r.stdout
    bad = dict(base, events=[{"name": "Fire", "level": 4}, {"name": "Siege", "trigger": "t", "level": 2}],
               climax={"trigger": "t", "session": 6, "signs": [{"text": "ash", "session": 7}, {"text": "crows"}]})
    p.write_text(json.dumps(bad), encoding="utf-8")
    r = run("campaign", p)
    assert r.returncode == 1
    for s in ("event Fire: no trigger", "climax: no level", "'ash': session 7 is not before", "'crows': no session",
              "2 foreshadowing signs", "level 2 after"):
        assert s in r.stdout, s


def test_fiveroom_puzzle_hints_and_reward(tmp_path):
    plan = {"areas": [{"role": "entrance", "mode": "talk"},
                      {"role": "puzzle", "mode": "puzzle", "solutions": ["a", "b"], "fail_cost": "noise", "clue_in": 1,
                       "hints": ["arcana: the runes are a clock"]},
                      {"role": "setback", "cost": "a torch"},
                      {"role": "climax", "lever": "bell", "terrain": "ledge"},
                      {"role": "reward", "hook": "map"}]}
    p = tmp_path / "f.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    out = run("fiveroom", p).stdout
    assert "no baseline hint" in out and "no reward" in out
    plan["areas"][1].update(hints=["baseline: it is a lock", "arcana: a clock"], reward="a key")
    p.write_text(json.dumps(plan), encoding="utf-8")
    out = run("fiveroom", p).stdout
    assert "hint" not in out and "no reward" not in out
    del plan["areas"][1]["hints"], plan["areas"][1]["reward"]
    p.write_text(json.dumps(plan), encoding="utf-8")
    assert "hint" not in run("fiveroom", p).stdout
