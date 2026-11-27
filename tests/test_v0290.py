import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_haul(tmp_path):
    f = jw(tmp_path, "h.json", {"entries": [
        {"session": 1, "gp": 100}, {"session": 2, "gp": 300}, {"session": 3, "gp": 20},
        {"kind": "tax", "gp": 10}, {"kind": "tax", "gp": 5}, {"kind": "theft", "gp": 50},
        {"kind": "magic-shop", "gp": 200}]})
    r = run("haul", f, "--plan", "100", "--xp-for-gold")
    assert r.returncode == 0, r.stdout
    assert "session 1: 100 gp" in r.stdout and "over plan" in r.stdout and "under plan" in r.stdout
    assert "removal tax used 2 times" in r.stdout and "magic shop" in r.stdout
    assert "xp for gold: 420 XP" in r.stdout
    r = run("haul", f, "--plan", "100", "--magic-shops")
    assert "magic shop" not in r.stdout
    bad = jw(tmp_path, "b.json", {"entries": [{"kind": "lottery", "gp": 1}]})
    assert run("haul", bad, "--plan", "10").returncode == 1


def test_tpk_reason():
    r = run("tpk", "--reason", "dramatic")
    assert r.returncode == 0 and "death dramatic: earned" in r.stdout
    r = run("tpk", "--reason", "complacent")
    assert "not earned" in r.stdout and "warn:" in r.stdout
    assert run("tpk").returncode == 2
    assert run("tpk", "--cause", "bad-luck").returncode == 0


def test_improvise():
    assert "DC 15" in run("improvise", "--gut", "maybe").stdout
    assert "DC 13" in run("improvise", "--gut", "sure", "--system", "pf2e", "--level", "3").stdout
    assert run("improvise", "--gut", "no", "--system", "sf2e").returncode == 2


def test_encounter_hearts():
    r = run("encounter", "--system", "5e", "--level", "3", "--foe", "1", "--hearts", "200")
    assert "20 hearts, over 3 per PC" in r.stdout and "past 1.5x" in r.stdout, r.stdout
    r = run("encounter", "--system", "5e", "--level", "3", "--foe", "1", "--hearts", "60", "--hearts", "60")
    assert "hearts: 12 block(s)" in r.stdout and "past 1.5x" not in r.stdout and "under half" not in r.stdout


def test_houserules_slump_rebuild(tmp_path):
    f = jw(tmp_path, "r.json", [
        {"rule": "slump", "kind": "add", "why": "cold dice", "review_after": 3, "slump": "d4", "slump_after": 3},
        {"rule": "focus", "kind": "change", "why": "we misread it", "review_after": 2, "rebuild": "yes", "misread": "once a turn"},
        {"rule": "x", "kind": "change", "why": "y", "review_after": 2, "rebuild": "no", "misread": "z"}])
    r = run("houserules", f)
    assert r.returncode == 0 and "let players rebuild" in r.stdout and "rebuild no" in r.stdout, r.stdout
    bad = jw(tmp_path, "b.json", [{"rule": "s", "kind": "add", "why": "w", "slump": "d20", "rebuild": "maybe"}])
    r = run("houserules", bad)
    assert r.returncode == 1 and "slump 'd20'" in r.stdout and "rebuild 'maybe'" in r.stdout


def test_endgame(tmp_path):
    f = jw(tmp_path, "g.json", {"goal": "20 points", "leader_reward": True, "out_of_contention_can_act": True,
                                "turn_minutes": {"early": 2, "late": 6}})
    r = run("endgame", f)
    assert r.returncode == 0 and "runaway leader" in r.stdout and "kingmaking" in r.stdout and "drags" in r.stdout
    ok = jw(tmp_path, "o.json", {"goal": "x", "leader_reward": True, "catch_up": "last player drafts first",
                                 "hidden_score": True, "out_of_contention_can_act": True})
    assert "warn" not in run("endgame", ok).stdout
    assert run("endgame", jw(tmp_path, "n.json", {})).returncode == 1


def test_scout_seeded():
    a = run("scout", "--seed", "3", "--scout-mod", "2", "--hide-mod", "-1").stdout
    assert a == run("scout", "--seed", "3", "--scout-mod", "2", "--hide-mod", "-1").stdout
    assert "8+2 = 10 vs hide 19-1 = 18" in a and "no report" in a
    outs = {run("scout", "--seed", str(s)).stdout.splitlines()[1].split(":")[1] for s in range(30)}
    assert any("false report" in o for o in outs)


def test_tracker_poison_die_and_shelf(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Ana:15:20", "--file", f)
    r = run("tracker", "poison", "Ana", "venom", "weak,sick", "--damage", "1d6", "--potency", "up",
            "--dc", "14", "--shelf-life", "10", "--age", "12", "--file", f)
    assert r.returncode == 0 and "damage 1d8" in r.stdout and "DC 16" in r.stdout and "shelf life" in r.stdout, r.stdout
    r = run("tracker", "poison", "Ana", "v2", "a", "--damage", "1d12", "--potency", "up", "--file", f)
    assert "damage 1d12" in r.stdout
    assert run("tracker", "poison", "Ana", "v3", "a", "--damage", "1d7", "--file", f).returncode == 2
