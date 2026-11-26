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


def test_spell_cost():
    assert "cost 6 " in run("spell", "cost", "--tier", "2", "--power", "3").stdout
    assert "cost 16 " in run("spell", "cost", "--tier", "4", "--power", "4").stdout
    assert "cost 8 " in run("spell", "cost", "--tier", "4", "--power", "4", "--mastered").stdout
    assert "cost 1 " in run("spell", "cost", "--tier", "1", "--power", "1", "--mastered").stdout
    assert run("spell", "cost", "--tier", "5", "--power", "1").returncode == 2
    assert run("spell", "cost", "--tier", "1", "--power", "0").returncode == 2


def test_spell_check(tmp_path):
    ok = jw(tmp_path, "ok.json", {"known": {"fire": 2}, "spells": [
        {"name": "Spark", "tier": 1, "school": "fire", "targets": 1, "range": "near", "duration": 1},
        {"name": "Burn", "tier": 2, "school": "fire", "targets": 3, "range": "far", "duration": 3, "created": "2026-01-01"},
        {"name": "Blaze", "tier": 2, "school": "fire", "targets": 2, "range": "near", "duration": 2, "created": "2026-01-02"}]})
    r = run("spell", "check", ok)
    assert r.returncode == 0 and "warn" not in r.stdout
    bad = jw(tmp_path, "bad.json", {"known": {"fire": 1}, "spells": [
        {"name": "Nova", "tier": 1, "school": "fire", "targets": 4, "range": "distant", "duration": 9},
        {"name": "A", "tier": 3, "school": "fire", "targets": 1, "range": "near", "duration": 1, "created": "2026-01-01"},
        {"name": "B", "tier": 3, "targets": 1, "range": "near", "duration": 1, "created": "2026-01-05"}]})
    r = run("spell", "check", bad)
    assert r.returncode == 1
    assert "Nova: targets 4" in r.stdout and "Nova: range distant" in r.stdout and "Nova: duration 9" in r.stdout
    assert "A: tier 3 in fire" in r.stdout and "B: tier 3 created 4 days after A" in r.stdout


def test_tracker_effects(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Hero:15:10", "Orc:10:8", "--file", f)
    r = run("tracker", "effect", "Orc", "on fire", "2", "--file", f)
    assert "(on fire 2r)" in r.stdout
    run("tracker", "next", "--file", f)
    r = run("tracker", "next", "--file", f)
    assert "(on fire 1r)" in r.stdout
    run("tracker", "next", "--file", f)
    r = run("tracker", "next", "--file", f)
    assert "on fire ended" in r.stdout and "on fire" not in r.stdout.split("ended", 1)[1]
    assert run("tracker", "effect", "Orc", "x", "zero", "--file", f).returncode == 2


def test_rewards(tmp_path):
    t = ["a", "b", "c"]
    ok = jw(tmp_path, "ok.json", {"tiers": [{"name": "small", "cadence_sessions": 1, "gate": "any", "triggers": t},
                                            {"name": "big", "cadence_sessions": 4, "gate": "boss", "triggers": t}]})
    assert run("rewards", ok).returncode == 0
    bad = jw(tmp_path, "b.json", {"tiers": [{"name": "small", "cadence_sessions": 3, "gate": "g", "triggers": t},
                                            {"name": "big", "cadence_sessions": 2, "triggers": ["a"]}]})
    r = run("rewards", bad)
    assert r.returncode == 1 and "does not lengthen" in r.stdout and "1 triggers" in r.stdout and "big: no gate" in r.stdout


def test_vendors(tmp_path):
    v = tw(tmp_path, "v.csv", "vendor,tier,reach\nstall,1,1\nguild,2,3\n")
    p = tw(tmp_path, "p.csv", "item,tier,price\nrope,1,2\nlamp,1,4\nsword,2,20\n")
    r = run("vendors", v, p, "--wage", "2")
    assert r.returncode == 0 and "10.0 days of wage 2" in r.stdout
    v2 = tw(tmp_path, "v2.csv", "vendor,tier,reach\nstall,1,3\nguild,2,1\n")
    p2 = tw(tmp_path, "p2.csv", "item,tier,price\nrope,1,30\nsword,2,20\nrelic,3,99\n")
    r = run("vendors", v2, p2)
    assert r.returncode == 1 and "tier 3 has no vendor" in r.stdout and "easier to reach" in r.stdout and "prices drop" in r.stdout


def test_party_roles(tmp_path):
    f = jw(tmp_path, "p.json", {"roles": ["fight", "talk", "sneak", "heal"], "pcs": [
        {"name": "A", "ties": ["B"], "plot_tie": "x", "roles": ["fight", "talk", "sneak", "heal"]},
        {"name": "B", "ties": ["A"], "plot_tie": "y", "roles": ["fight"]}]})
    r = run("party", f)
    assert "A covers every role" in r.stdout and "no owner" not in r.stdout
    r = run("party", f, "--roles", "fight,magic")
    assert "role magic has no owner" in r.stdout and "covers every role" not in r.stdout


def test_table_sub(tmp_path):
    tw(tmp_path, "w.csv", "roll,kind\n1,rain\n2,fog\n3,sun\n4,wind\n")
    tw(tmp_path, "s.csv", "roll,kind\n1-2,a\n3-4,b\n")
    ok = tw(tmp_path, "m.csv", "roll,kind,sub\n1-3,weather,w.csv:d4\n4-6,omen,\n")
    assert run("table", ok).returncode == 0
    bad = tw(tmp_path, "b.csv", "roll,kind,sub\n1-3,weather,s.csv:d4\n4-6,omen,nope.csv\n")
    r = run("table", bad)
    assert r.returncode == 1 and "2 rows for a d4" in r.stdout and "nope.csv not found" in r.stdout


def test_campaign_travel_nemesis(tmp_path):
    bad = jw(tmp_path, "c.json", {"pcs": ["Ash"], "adventures": [{"name": "one", "phase": "a", "why": "b", "plotline": ["Ash"], "opposed_by": "x"}],
                                  "travel": "unlimited", "nemesis": {"name": "Vex", "pc": "Bram"}})
    r = run("campaign", bad)
    assert r.returncode == 1 and "travel_limit" in r.stdout and "Vex is not tied" in r.stdout
    ok = jw(tmp_path, "o.json", {"pcs": ["Ash"], "adventures": [{"name": "one", "phase": "a", "why": "b", "plotline": ["Ash"], "opposed_by": "x"}],
                                 "travel": "unlimited", "travel_limit": "one jump a week", "nemesis": {"name": "Vex", "pc": "Ash"}})
    r = run("campaign", ok)
    assert r.returncode == 0 and "warn" not in r.stdout
    r = run("campaign", jw(tmp_path, "n.json", {"adventures": [], "travel": "limited"}))
    assert "no nemesis" in r.stdout


def test_villain_drive_die(tmp_path):
    base = "## Vex\n- wants: x\n- public: y\n- reach: z\n- harm: a\n- harm: b\n- absent: c\n- escape: d\n- drive_die: d3\n"
    assert run("villain", tw(tmp_path, "ok.md", base + "1. rob\n2. lie\n3. flee\n")).returncode == 0
    r = run("villain", tw(tmp_path, "bad.md", base + "1. rob\n2. lie\n"))
    assert r.returncode == 2 and "numbered 1 to 3" in r.stderr


def test_mob():
    r = run("mob", "--count", "6", "--hp-each", "5", "7", "2", "5", "9")
    assert "left 3 of 6, routed" in r.stdout
    assert "left 5 of 6, holding" in run("mob", "--count", "6", "--hp-each", "5", "6").stdout
    assert "destroyed" in run("mob", "--count", "1", "--hp-each", "3", "4").stdout


def test_hack():
    assert "automatic" in run("hack", "--system", "own", "--mods", "remote").stdout
    assert "one check, normal" in run("hack", "--system", "simple", "--mods", "wired", "remote").stdout
    assert "hard" in run("hack", "--system", "secure", "--mods", "wired", "remote", "jammed").stdout
    assert "easy" in run("hack", "--system", "simple", "--mods", "quiet,familiar", "combat").stdout
    assert run("hack", "--system", "simple", "--mods", "magic").returncode == 2


def test_settlement(tmp_path):
    ok = jw(tmp_path, "s.json", {"name": "Fordham", "size": "small town", "population": 1800, "inns": 2,
                                 "civic": ["authority", "council", "defence", "hall", "walls"],
                                 "function": "trade hub", "businesses": ["lodging", "stables", "smith"]})
    assert run("settlement", ok).returncode == 0
    bad = jw(tmp_path, "b.json", {"size": "village", "population": 50, "civic": ["authority"],
                                  "function": "trade hub", "businesses": ["smith"]})
    r = run("settlement", bad)
    assert r.returncode == 1 and "does not fit village" in r.stdout and "no council" in r.stdout and "no stables" in r.stdout
    assert run("settlement", jw(tmp_path, "x.json", {"size": "megacity"})).returncode == 2


def test_favor_seeded_low_never_major():
    a = run("favor", "--relation", "business", "--risk", "moderate", "--seed", "7").stdout
    assert a == run("favor", "--relation", "business", "--risk", "moderate", "--seed", "7").stdout
    for s in range(40):
        assert "major" not in run("favor", "--relation", "friend", "--risk", "low", "--seed", s).stdout
    assert run("favor", "--relation", "enemy", "--risk", "low").returncode == 2
