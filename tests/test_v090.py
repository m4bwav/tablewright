import json

from test_tt import run


def test_strength_apl_rounds_up_and_labels():
    r = run("strength", "3", "4", "4", "4", "--target-level", "4")
    assert r.returncode == 0 and "APL 4" in r.stdout and "weak" in r.stdout
    r = run("strength", "4", "4", "4", "4", "5", "--target-level", "4")
    assert r.returncode == 0 and "average" in r.stdout
    r = run("strength", "5", "5", "5", "5", "5", "5", "--target-level", "4")
    assert "very strong" in r.stdout


def test_strength_fails_outside_three_to_seven():
    assert run("strength", "3", "3", "--target-level", "3").returncode == 1
    assert run("strength", *["3"] * 8, "--target-level", "3").returncode == 1


def test_loot_split_and_fewest_items(tmp_path):
    f = tmp_path / "loot.json"
    f.write_text(json.dumps({
        "gold": 101,
        "pcs": [{"name": "Ash", "permanent": 2}, {"name": "Bry", "permanent": 0}, {"name": "Cel", "permanent": 0}],
        "items": [
            {"name": "potion", "kind": "consumable"},
            {"name": "ring", "agreed": "Ash"},
            {"name": "cloak", "interested": ["Ash", "Bry"]},
            {"name": "boots", "interested": ["Bry", "Cel"]},
        ]}), encoding="utf-8")
    r = run("loot", f, "--seed", "1")
    assert r.returncode == 0
    assert "33 each" in r.stdout and "2 left over" in r.stdout
    assert "potion: consumable" in r.stdout and "ring: Ash (agreed)" in r.stdout
    assert "cloak: Bry" in r.stdout and "boots: Cel" in r.stdout


def test_reaction_bands_and_mods():
    assert "hostile" in run("reaction", "--roll", "4", "--approach", "hostile").stdout
    assert "helpful" in run("reaction", "--roll", "11", "--mod", "1").stdout
    assert "neutral" in run("reaction", "--roll", "7").stdout


def test_heat_escalates_and_cools(tmp_path):
    f = tmp_path / "heat.json"
    r = run("heat", "crime", "Watch", "--witnesses", "3", "--why", "burglary", "--file", f)
    assert "escalates: noticed" in r.stdout
    r = run("heat", "crime", "Watch", "--witnesses", "1", "--file", f)
    assert "collector" in r.stdout
    assert run("heat", "standing", "Guild", "--by", "-1", "--file", f).returncode == 2
    run("heat", "standing", "Guild", "--by", "-5", "--why", "stole their job", "--file", f)
    r = run("heat", "cool", "--by", "3", "--file", f)
    assert "Watch: standing +0, heat 3" in r.stdout and "Guild: standing -3" in r.stdout


def test_premise_checks(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"type": "pursuit", "core": "a thief flees", "twist": "the thief is innocent",
                             "hook": {"type": "pursuit"}}), encoding="utf-8")
    r = run("premise", f)
    assert r.returncode == 1 and "finish_line" in r.stdout and "same premise" in r.stdout
    f.write_text(json.dumps({"type": "race", "core": "c", "twist": "t", "hook": {"type": "escort"},
                             "factions": [{"name": "A", "agenda": "x"}, {"name": "B"}]}), encoding="utf-8")
    r = run("premise", f)
    assert r.returncode == 1 and "B has no agenda" in r.stdout
    f.write_text(json.dumps({"type": "investigation", "core": "c", "twist": "t", "at_risk": ["the clerk"]}),
                 encoding="utf-8")
    assert run("premise", f).returncode == 0


def test_wander_clock_budget_and_run():
    r = run("wander", "--every", "30", "--chance", "2", "--hours", "4")
    assert "8 checks" in r.stdout and "over the budget" in r.stdout
    r = run("wander", "--every", "10", "--chance", "1", "--hours", "1", "--run", "--seed", "3", "--placed", "crypt")
    assert r.returncode == 0 and r.stdout.count("encounter at") == 6 and "reaction" in r.stdout
    assert "placed population in crypt" in r.stdout
