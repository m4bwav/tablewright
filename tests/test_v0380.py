import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes((data if isinstance(data, str) else json.dumps(data)).encode("utf-8"))
    return f


def test_adventure_day(tmp_path):
    sc = [{"name": "a", "difficulty": "hard"}, {"name": "b", "difficulty": "hard"}, {"name": "c", "difficulty": "deadly"},
          {"name": "d", "difficulty": "deadly"}, {"rest": "long"}, {"name": "e", "difficulty": "easy"}]
    r = run("adventure", jw(tmp_path, "a.json", {"scenes": sc}), "--day")
    assert r.returncode == 0
    assert "day 1: load 14 of 12" in r.stdout and "three hard or deadly" in r.stdout and "over 12" in r.stdout
    assert "day 2: load 1" in r.stdout and "under a third" in r.stdout
    bad = run("adventure", jw(tmp_path, "b.json", {"scenes": [{"name": "x", "difficulty": "silly"}]}), "--day")
    assert bad.returncode == 1


def test_explore_tasks(tmp_path):
    turns = [{"pace": "fast", "tasks": {"Ana": ["watch"]}},
             {"pace": "normal", "tasks": {"Ana": ["map", "navigate"], "Bo": ["sneak"]}}]
    r = run("explore", jw(tmp_path, "e.json", {"turns": turns}), "--tasks")
    assert r.returncode == 1
    for s in ("fast allows no tasks", "two tasks; disadvantage", "sneaking needs slow", "lost DC 10", "no watch"):
        assert s in r.stdout, s
    ok = [{"pace": "slow", "tasks": {"Ana": "watch", "Bo": ["navigate"]}}]
    r = run("explore", jw(tmp_path, "o.json", {"turns": ok}))
    assert r.returncode == 0 and "lost DC 15" in r.stdout


def test_stash_seeded():
    a = run("stash", "--count", "3", "--seed", "4")
    assert a.returncode == 0 and a.stdout.count("stash ") == 3
    assert a.stdout == run("stash", "--count", "3", "--seed", "4").stdout
    assert "warded" in run("stash", "--magic", "100", "--seed", "1").stdout


def test_shop_check(tmp_path):
    shops = [{"name": "Good", "quarter": "docks", "customers": "poor to middling", "keepers": [{"name": "Ola", "role": "owner"}],
              "price": {"lead_time": "3 days"}, "quirk": "q", "hook": "h"},
             {"name": "Bad", "keepers": ["Ola"], "price": {}, "quirk": ["a", "b"]}]
    r = run("shop", jw(tmp_path, "s.json", {"shops": shops}), "--check")
    assert r.returncode == 1
    for s in ("Bad: no quarter", "Bad: no customers", "role each", "price line", "Bad: no hook", "2 quirks"):
        assert s in r.stdout, s
    assert "Good:" not in r.stdout


def test_check_haste_caution():
    r = run("check", "--haste", "--dc", "15", "--bonus", "5", "--time", "10")
    assert "haste: 5 min at DC 19: 35%" in r.stdout and "normal: 10 min at DC 15: 55%" in r.stdout
    r = run("check", "--caution", "--dc", "15", "--bonus", "5")
    assert "caution: 20 min at DC 11: 75%" in r.stdout
    assert run("check", "--haste").returncode == 2


def test_clues_tiers(tmp_path):
    facts = [{"fact": "who", "core": True, "clues": [{"name": "a", "tier": "costly"}, {"name": "b", "tier": "never"}]},
             {"fact": "where", "clues": [{"name": "c", "tier": "never"}]},
             {"fact": "why", "core": True, "clues": [{"name": "d", "tier": "cheap"}]}]
    r = run("clues", jw(tmp_path, "c.json", {"facts": facts}), "--tiers")
    assert r.returncode == 1
    assert "known 0, cheap 1, costly 1, never 2" in r.stdout
    assert "names no cost" in r.stdout and "who: core fact" in r.stdout and "where: every clue is never" in r.stdout
    assert "why:" not in r.stdout


def test_negotiate_bribe():
    r = run("negotiate", "--bribe", "5", "--wealth", "100", "--exchange", "0", "--rolls", "7")
    assert "an insult" in r.stdout and "now: wary" in r.stdout
    r = run("negotiate", "--bribe", "80", "--wealth", "100", "--exchange", "0", "--rolls", "6")
    assert "+4 to the first exchange" in r.stdout and "= 10: moves up" in r.stdout
    r = run("negotiate", "--bribe", "80", "--wealth", "100", "--honest", "--exchange", "0", "--rolls", "7")
    assert "takes offence" in r.stdout
    assert run("negotiate", "--bribe", "5").returncode == 2


def test_repair_stack():
    r = run("repair", "--stack", "minor,destroyed,major", "--bonus", "20", "--seed", "1")
    assert r.returncode == 0
    out = r.stdout
    assert out.index("destroyed") < out.index("major:") < out.index("minor:")
    assert "time: 5.25 hours" in out
    assert run("repair", "--stack", "broken").returncode == 2


def test_trade_week():
    r = run("trade", "--week", "4", "--price", "100", "--upkeep", "5", "--seed", "3")
    assert r.returncode == 0 and r.stdout.count("week ") == 5 and "best: sell in week" in r.stdout
    assert run("trade", "--price", "100").returncode == 2
    assert run("trade", "--price", "100", "--hexes", "0").returncode == 0


def test_hire_rate():
    r = run("hire", "--rate", "2", "--days", "40")
    assert "6 a day, 42 a week, 144 a month" in r.stdout and "40 days: 192" in r.stdout
    assert "12 a day" in run("hire", "--rate", "2", "--danger").stdout


def test_rooms_force(tmp_path):
    d = {"rooms": [{"name": "x"}], "doors": [{"name": "gate", "force": {"dc": 30, "minutes": 2},
                                             "lock": {"dc": 2, "minutes": 10}}]}
    f = jw(tmp_path, "r.json", d)
    r = run("rooms", f, "--force", "gate", "--tries", "3", "--seed", "1")
    assert "still shut after 3 tries, 6 minutes" in r.stdout
    r = run("rooms", f, "--force", "gate", "--pick", "--seed", "1")
    assert "open after 1 tries, 10 minutes" in r.stdout
    assert run("rooms", f, "--force", "nope").returncode == 2


def test_rooms_eras(tmp_path):
    rooms = [{"name": "vault", "eras": {"past": {"treasure": ["crown"], "portal": True},
                                        "present": {"treasure": ["crown"], "portal": True},
                                        "future": {"treasure": ["crown"]}}}]
    f = jw(tmp_path, "r.json", {"rooms": rooms})
    r = run("rooms", f, "--eras", "past,present,future")
    assert "present: vault: crown gone (taken in the past)" in r.stdout
    assert "future: no room with portal" in r.stdout and r.returncode == 1
    r = run("rooms", f, "--eras", "present,past")
    assert "here again before it was taken" in r.stdout and "future is never visited" in r.stdout
    assert r.returncode == 0


def test_site_edge_ward(tmp_path):
    areas = [{"name": "ledge", "edge": "lethal"}, {"name": "rope room", "fall_safe": True},
             {"name": "sanctum", "ward": ["teleport"], "routes": [{"name": "blink", "magic": True}]}]
    r = run("site", jw(tmp_path, "s.json", {"areas": areas}), "--edge", "--ward")
    assert r.returncode == 1 and "ledge: first lethal edge" in r.stdout and "sanctum: warded" in r.stdout
    areas = [areas[1], areas[0], dict(areas[2], routes=[{"name": "stairs"}])]
    assert run("site", jw(tmp_path, "o.json", {"areas": areas}), "--edge", "--ward").returncode == 0


def test_act_quests(tmp_path):
    d = {"system": "pf2e", "pcs": 4, "start_level": 1,
         "quests": [{"name": "a", "xp": 800}, {"name": "b", "xp": 400}, {"name": "gate", "gate": True, "min_level": 3}]}
    r = run("act", jw(tmp_path, "a.json", d), "--quests")
    assert r.returncode == 1 and "reach level 2" in r.stdout and "gate needs 3" in r.stdout
    d5 = {"system": "5e", "pcs": 4, "split": True, "start_level": 1,
          "quests": [{"name": "a", "xp": 3600}, {"name": "gate", "gate": True, "min_level": 3}]}
    r = run("act", jw(tmp_path, "b.json", d5))
    assert r.returncode == 0 and "reach level 3" in r.stdout


def test_carry_resources(tmp_path):
    f = tmp_path / "carry.json"
    run("carry", "orcs", "--start", "10", "--file", f)
    r = run("carry", "orcs", "--killed", "4", "--fled", "6", "--resources", "--hp-lost", "50", "--slots-spent", "2",
            "--xp", "1000", "--file", f)
    assert "rematch: 6 of 10 with 50% HP lost and 2 slot(s) spent" in r.stdout and "rematch XP: 300 of 1000" in r.stdout
    assert json.loads(f.read_text(encoding="utf-8"))["orcs"]["hp_lost"] == 50


def test_pcs_file_and_drift(tmp_path):
    pcs = [{"name": "Ana", "level": 5, "secrets": "s", "devices": "d", "owed": "o", "writeout": "w"},
           {"name": "Bo", "level": 3}, {"name": "Cy", "level": 5}, {"name": "Di", "level": 9}]
    f = jw(tmp_path, "p.json", {"pcs": pcs})
    r = run("pcs", f)
    assert r.returncode == 1 and "Bo: no secrets, devices, owed, writeout" in r.stdout and "Ana:" not in r.stdout
    r = run("pcs", f, "--drift")
    assert "Bo: -2 levels" in r.stdout and "Di: +4 levels" in r.stdout and r.returncode == 1


def test_world_magic(tmp_path):
    bad = "## Magic\n- abundance: rare\n- finite: crystals\n"
    r = run("world", jw(tmp_path, "w.md", bad), "--magic")
    assert r.returncode == 1 and "no cost_per_use" in r.stdout and "no controller" in r.stdout and "0 lever" in r.stdout
    ok = "## Magic\n- abundance: rare\n- cost_per_use: a year of life\n- lever: whispers\n"
    assert run("world", jw(tmp_path, "o.json", ok), "--magic").returncode == 0
