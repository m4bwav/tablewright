import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_safety_lowest_comfort_wins(tmp_path):
    base = {"cut_call": "stop", "brake_call": "slow", "debrief_minutes": 15}
    ok = jw(tmp_path, "s.json", {**base, "comfort": {"Ann": {"gore": "full"}, "Bo": {"gore": "offscreen"}},
                                 "planned": {"gore": "offscreen"}})
    r = run("safety", ok)
    assert r.returncode == 0 and "gore offscreen" in r.stdout
    bad = jw(tmp_path, "b.json", {**base, "comfort": {"Ann": {"gore": "full"}, "Bo": {"gore": "offscreen"}},
                                  "planned": {"gore": "limited"}})
    r = run("safety", bad)
    assert r.returncode == 1 and "lowest level wins" in r.stdout
    unrated = jw(tmp_path, "u.json", {**base, "planned": {"spiders": "limited"}, "takebacks": ""})
    r = run("safety", unrated)
    assert "no player rated" in r.stdout and "takebacks empty" in r.stdout


def test_battle_three_fights_and_results(tmp_path):
    plan = {"fights": [{"shape": "hold the gate", "carry": "archers on the wall"},
                       {"shape": "break the ram", "carry": "the gate holds"},
                       {"shape": "duel the captain"}]}
    f = jw(tmp_path, "b.json", plan)
    r = run("battle", f, "--results", "won,won,lost")
    assert r.returncode == 0 and "archers on the wall" in r.stdout and "win at a cost" in r.stdout
    assert "rout" in run("battle", f, "--results", "lost,lost,lost").stdout
    two = jw(tmp_path, "t.json", {"fights": plan["fights"][:2]})
    assert run("battle", two).returncode == 1
    assert run("battle", f, "--results", "won,won").returncode == 2


def test_tracker_timer_and_late(tmp_path):
    t = tmp_path / "t.json"
    r = run("tracker", "init", "Ash:15:20", "Orc:10:15", "--timer", "60", "--file", t)
    assert "turn timer 60 s" in r.stdout
    r = run("tracker", "late", "--file", t)
    d = json.loads(t.read_text(encoding="utf-8"))
    assert "delayed" in d["order"][0]["conditions"] and d["turn"] == 1


def test_sessionlog_template_and_review(tmp_path):
    assert "## Highlights" in run("session-log").stdout
    a = tmp_path / "s1.md"
    a.write_text("## Highlights\n- bridge fight; Ann, Bo; the rope trick\n\n## Weak points\n"
                 "- shop scene; Cy; dragged on; cut to the street\n", encoding="utf-8")
    b = tmp_path / "s2.md"
    b.write_text("## Highlights\n- court; Ann; won the duke over\n", encoding="utf-8")
    r = run("review", a, b)
    assert r.returncode == 0 and "Ann: 2 highlights" in r.stdout
    assert "cut to the street" in r.stdout and "Cy has no highlight" in r.stdout


CARD = """## Opening
- at the docks
## Leads
- the ledger; for: Ann; likely: definite
- the smuggler; likely: possible
- the old map; for: Bo; likely: unlikely
## NPCs
- Mara: wants her brother back
## Players
- Ann: lost her ship
- Bo: owes the guild
- Cy: seeks a teacher
## Fights
- dock thugs; out: run; diff: easy
- guild guards; out: surrender; diff: moderate
- the brute; out: bribe; diff: moderate
"""


def test_prep_spotlight_likely_and_rhythm(tmp_path):
    f = tmp_path / "c.md"
    f.write_text(CARD, encoding="utf-8")
    r = run("prep", f)
    assert r.returncode == 0
    assert "Cy has no moment" in r.stdout and "Ann has no moment" not in r.stdout
    assert "no hard fight" in r.stdout
    f.write_text(CARD.replace("likely: definite", "likely: maybe"), encoding="utf-8")
    assert run("prep", f).returncode == 1


def test_houserules(tmp_path):
    f = jw(tmp_path, "h.json", [{"rule": "no flanking", "kind": "remove", "why": "slows play", "review_after": 3},
                               {"rule": "hero points", "kind": "add"}])
    r = run("houserules", f)
    assert r.returncode == 1 and "no offset" in r.stdout and "hero points: no why" in r.stdout


def test_fiveroom_climax_tiers(tmp_path):
    areas = [{"role": "entrance"}, {"role": "setback", "cost": "a torch"},
             {"role": "climax", "lever": "the bell", "terrain": "ledge",
              "tiers": {"minimum": "kill the priest", "middle": "x", "full": "y"}},
             {"role": "reward", "hook": "a letter"}]
    r = run("fiveroom", jw(tmp_path, "p.json", {"areas": areas}))
    assert "minimum tier needs a kill" in r.stdout
    areas[2]["tiers"] = {"minimum": "escape"}
    assert "minimum, middle and full" in run("fiveroom", jw(tmp_path, "q.json", {"areas": areas})).stdout


def test_challenge(tmp_path):
    good = {"goal": "cross the pass", "successes": 6, "failures": 3, "on_fail": "arrive late and frostbitten",
            "shown": "a track of six marks", "skills": [{"name": "survival", "kind": "knowledge"},
                                                         {"name": "athletics", "kind": "physical"},
                                                         {"name": "diplomacy", "kind": "social"}],
            "pool": 10, "milestones": [{"at": 5, "gives": "a cave"}], "minutes": 30, "limit": 120}
    r = run("challenge", jw(tmp_path, "g.json", good))
    assert r.returncode == 0 and "the clock beats a flawless run" in r.stdout
    bad = dict(good, on_fail="", milestones=[{"at": 12}])
    r = run("challenge", jw(tmp_path, "b.json", bad))
    assert r.returncode == 1 and "on_fail" in r.stdout and "outside the pool" in r.stdout


def test_travel():
    r = run("travel", "--miles", "48", "--terrain", "forest", "--known")
    assert r.returncode == 0 and "12.0 miles a day" in r.stdout and "4 day(s)" in r.stdout
    r = run("travel", "--miles", "48", "--hours", "10")
    assert "unknown route" in r.stdout and "fatigue: 2 point(s)" in r.stdout
    assert run("travel", "--miles", "5", "--terrain", "lava").returncode == 2


def test_table_when_column(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("roll,kind,difficulty,avoidable,when\n1-3,fight,moderate,yes,moving\n4-6,sight,,,moving\n",
                 encoding="utf-8")
    assert "every row is moving" in run("table", f).stdout
