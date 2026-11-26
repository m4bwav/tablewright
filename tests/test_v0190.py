import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return f


def sp(n, **kw):
    return dict({"n": n, "event": f"e{n}", "shown_by": "runner"}, **kw)


def test_doomtrack_spaces_and_scenes(tmp_path):
    card = {"spaces": [sp(1), {"n": 2, "event": "x"}, {"n": 3}], "advance_on": "encounter",
            "scenes": [{"name": "A", "fail_cost": 2}, {"name": "B", "fail_cost": 1, "cap": 1}, {"name": "End"}]}
    r = run("doomtrack", jw(tmp_path, "d.json", card))
    assert r.returncode == 1 and "space 3: no event" in r.stdout and "space 2: no shown_by" in r.stdout
    assert "A: fail_cost 2 with no cap" in r.stdout and "can lose before it reaches the last scene" in r.stdout
    ok = {"spaces": [sp(i) for i in range(1, 6)], "advance_on": ["rest"], "scenes": [{"name": "A", "fail_cost": 2, "cap": 1}, {"name": "E"}]}
    r = run("doomtrack", jw(tmp_path, "e.json", ok))
    assert r.returncode == 0 and "warn:" not in r.stdout
    ok["spaces"] = [sp(i) for i in range(1, 10)]
    assert "9 spaces" in run("doomtrack", jw(tmp_path, "f.json", ok)).stdout


def test_doomtrack_outcomes(tmp_path):
    card = {"spaces": [sp(1)], "advance_on": "scene", "paths": ["gate", "wall"],
            "outcomes": {"none": "a", "gate": "b", "wall+gate": "c"}}
    r = run("doomtrack", jw(tmp_path, "d.json", card))
    assert r.returncode == 1 and "no outcome for solved paths: wall" in r.stdout and "gate+wall" not in r.stdout
    card["outcomes"]["wall"] = "d"
    assert run("doomtrack", jw(tmp_path, "e.json", card)).returncode == 0


def test_challenge_tiers_and_complications(tmp_path):
    card = {"goal": "g", "successes": 6, "failures": 3, "on_fail": "x", "shown": "y",
            "skills": [{"name": "a", "kind": "body"}, {"name": "b", "kind": "mind"}, {"name": "c", "kind": "social"}],
            "tiers": [{"dc": 10, "gain": 1}, {"dc": 15, "gain": 2}, {"under": 5, "gain": -1}],
            "complications": [{"round": 2, "effect": "collapse", "removes": 2}]}
    r = run("challenge", jw(tmp_path, "c.json", card))
    assert "expected rounds at an average roll (+5, 4 checks a round): 2" in r.stdout
    assert "no warning" in r.stdout and "with no stop" in r.stdout
    card["complications"][0].update(warning="creaks", stop="brace it")
    card["tiers"] = [{"dc": 40, "gain": 1}]
    r = run("challenge", jw(tmp_path, "d.json", card))
    assert "cannot finish on average" in r.stdout and "no warning" not in r.stdout


def test_hazard_round(tmp_path):
    card = {"counters": [{"name": "fire", "start": 0, "cap": 6, "per_round": 2, "lowered_by": "water"},
                         {"name": "smoke", "start": 4, "cap": 5, "per_round": 3}],
            "deadlines": [{"what": "roof falls", "round": 4}]}
    r = run("hazard", jw(tmp_path, "h.json", card))
    assert r.returncode == 1 and "no goal" in r.stdout and "fire: caps in round 3" in r.stdout
    assert "smoke: caps in round 1" in r.stdout and "smoke: no lowered_by" in r.stdout and "no order" in r.stdout
    assert "deadline round 4: roof falls" in r.stdout


def test_chase_legs(tmp_path):
    legs = [{"name": "camp", "rounds": 2, "approaches": [{"skill": "stealth", "dc": 30, "fail": "round"}]},
            {"name": "bridge", "rounds": 1, "approaches": [{"skill": "athletics", "dc": 30, "fail": "damage:1d4"}],
             "complications": True}]
    f = jw(tmp_path, "l.json", legs)
    r = run("chase", "--legs", f, "--party", "2", "--seed", "1")
    assert "PC 2: 4 rounds" in r.stdout and "slowest PC: 4 rounds" in r.stdout and "damage" in r.stdout
    r = run("chase", "--legs", f, "--start", "bridge", "--party", "1", "--seed", "1")
    assert "slowest PC: 1 rounds" in r.stdout
    assert run("chase", "--legs", f, "--start", "nope").returncode == 2


def test_alert_noise_and_waves():
    base = ["alert", "noise", "--quiet", "2", "--check", "3", "--arrive", "5", "--round"]
    assert "hidden" in run(*base, "1").stdout
    assert "checker coming" in run(*base, "4").stdout
    assert "bluff" in run(*base, "5").stdout
    r = run("alert", "waves", "--since-alarm", "9", "--schedule", "8:2x3,10:captain", "--system", "pf2e", "--level", "3")
    assert "arrived (round 8): 2x3" in r.stdout and "next: round 10: captain" in r.stdout and "arrived XP: 80" in r.stdout


def test_rooms_infiltration(tmp_path):
    room = {"name": "Tent", "timer": "t", "threat": "t", "treat": "t", "stake": "s", "wonder": "w",
            "objective": "plans", "paths": ["front"], "rolls": [{"skill": "stealth"}, {"skill": "lie", "on_fail": "alarm"}]}
    r = run("rooms", jw(tmp_path, "r.json", {"rooms": [room, dict(room, name="B", objective=None)]}))
    assert "Tent: objective with 1 paths" in r.stdout and "roll stealth with no on_fail" in r.stdout
    assert "roll lie" not in r.stdout


def test_site_and_clock(tmp_path):
    r = run("site", jw(tmp_path, "s.json", {"entries": ["gate"], "doors": [{"name": "D", "locked": True}],
                                            "drops": [{"name": "pit", "depth": 20}], "treasure": [{"name": "chest"}],
                                            "rumours": [{"text": "ghost"}], "clock": {"turns": 6, "signs": [{"turn": 6}]}}))
    assert r.returncode == 1 and "no location" in r.stdout and "one entry" in r.stdout and "no upkeep" in r.stdout
    for frag in ("door D", "drop pit", "treasure chest", "rumour 'ghost'", "1 signs", "sign at turn 6"):
        assert frag in r.stdout
    ok = {"location": "hill", "entries": ["a", "b"], "upkeep": "u", "ecology": "e", "visitors": "v",
          "clock": {"turns": 6, "signs": [{"turn": 2}, {"turn": 4}]}}
    r = run("site", jw(tmp_path, "t.json", ok))
    assert r.returncode == 0 and "warn:" not in r.stdout


def test_interrogate(tmp_path):
    rungs = [{"dc": 10, "fact": "a", "truth": "true"}, {"dc": 8, "fact": "b", "truth": "half"}, {"dc": 15, "fact": "c"}]
    r = run("interrogate", jw(tmp_path, "i.json", rungs))
    assert r.returncode == 1 and "DC 8: DCs must go up" in r.stdout and "DC 15: truth missing" in r.stdout
    assert "DC 8: half with no real" in r.stdout
    ok = {"rungs": [{"dc": 10, "fact": "a", "truth": "true"}, {"dc": 15, "fact": "b", "truth": "false", "real": "r", "revealed_at": "hall"}]}
    assert run("interrogate", jw(tmp_path, "j.json", ok)).returncode == 0


def test_encounter_exit_and_carry(tmp_path):
    args = ["encounter", "--system", "5e", "--level", "1", "--foe", "2", "--foe", "2"]
    assert "with no --exit" in run(*args).stdout
    assert "with no --exit" not in run(*args, "--exit", "safe room").stdout
    f = tmp_path / "carry.json"
    run("carry", "raiders", "--start", "8", "--file", f)
    r = run("carry", "raiders", "--killed", "3", "--fled", "2", "--file", f)
    assert "next wave 5" in r.stdout and "2 of them fled" in r.stdout
    assert run("carry", "raiders", "--killed", "9", "--file", f).returncode == 2


def test_table_filter(tmp_path):
    a = "roll,thing,size\n" + "".join(f"{i},t{i},{'small' if i % 2 else 'large|huge'}\n" for i in range(1, 7))
    b = "roll,mood\n" + "".join(f"{i},m{i}\n" for i in range(1, 7))
    fa, fb = jw(tmp_path, "a.csv", a), jw(tmp_path, "b.csv", b)
    r = run("table", "combine", fa, fb, "--filter", "size=huge", "--count", "5", "--seed", "1")
    assert r.returncode == 0 and "small" not in r.stdout and "large|huge" in r.stdout
    assert run("table", "combine", fa, fb, "--filter", "color=red").returncode == 2
