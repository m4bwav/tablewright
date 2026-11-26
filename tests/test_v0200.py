import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def lead(skill, dc, reveals="cult", **kw):
    return dict({"skill": skill, "dc": dc, "reveals": reveals, "points_to": "mill"}, **kw)


def test_rumors(tmp_path):
    bad = {"leads": [lead("investigation", 12)] * 3}
    r = run("rumors", jw(tmp_path, "a.json", bad))
    assert r.returncode == 1 and "one skill" in r.stdout and "no free lead" in r.stdout and "same dc" in r.stdout
    ok = {"facts": ["cult"], "leads": [lead("insight", 10), lead("history", 15), lead("persuasion", 12, "colour"),
                                       {"free": True, "reveals": "noise", "points_to": "inn"}]}
    r = run("rumors", jw(tmp_path, "b.json", ok))
    assert r.returncode == 0, r.stdout
    ok["facts"].append("boss")
    assert "fact 'boss': 0 lead(s)" in run("rumors", jw(tmp_path, "c.json", ok)).stdout


def test_burst(tmp_path):
    card = {"target": {"ac": 15, "hp": 16},
            "attackers": [{"name": "a", "bonus": 5, "damage": 10, "first_strike": 5, "attacks": 2}]}
    r = run("burst", jw(tmp_path, "a.json", card))
    assert r.returncode == 1 and "dies before it acts" in r.stdout
    card["target"]["hp"] = 20
    r = run("burst", jw(tmp_path, "b.json", card))
    assert r.returncode == 0 and "it may never act" in r.stdout
    card["target"]["hp"] = 200
    assert "warn:" not in run("burst", jw(tmp_path, "c.json", card)).stdout


def test_rollout(tmp_path):
    card = {"stages": [{"name": "rumour", "session": 2, "gate": "g"}, {"name": "remnant", "session": 2}]}
    r = run("rollout", jw(tmp_path, "a.json", card))
    assert r.returncode == 1 and "2 stages" in r.stdout and "not after 2" in r.stdout and "no gate" in r.stdout
    card = {"off_switch": "drop it", "stages": [{"name": n, "session": i, "gate": "g"} for i, n in enumerate("abc", 1)]}
    r = run("rollout", jw(tmp_path, "b.json", card))
    assert r.returncode == 0 and "warn:" not in r.stdout


def test_recurring(tmp_path):
    card = {"acts": 3, "stages": [{"act": 1, "threat": 2}, {"act": 2, "threat": 2}]}
    r = run("recurring", jw(tmp_path, "a.json", card))
    assert r.returncode == 1 and "not above" in r.stdout and "no escape" in r.stdout and "no ends_when" in r.stdout
    assert "cover 2 of 3 acts" in r.stdout
    card = {"ends_when": "cured", "stages": [{"threat": 1, "escape": "smoke"}, {"threat": 3}]}
    assert run("recurring", jw(tmp_path, "b.json", card)).returncode == 0


def test_item_breaks_after(tmp_path):
    base = {"name": "bow", "benefit_tier": "minor", "drawback_tier": "minor", "cost_axis": "risk"}
    r = run("item", jw(tmp_path, "a.json", [dict(base, breaks_after=0)]))
    assert r.returncode == 1 and "breaks_after must be" in r.stdout
    r = run("item", jw(tmp_path, "b.json", [dict(base, breaks_after=2)]))
    assert "with no save" in r.stdout


def test_casefile(tmp_path):
    card = {"slot_minutes": 60, "leads": [{"name": "a", "minutes": 40, "beat": "talk", "points_to": "b", "closed_by": "x"},
                                          {"name": "b", "minutes": 30, "beat": "talk"}]}
    r = run("casefile", jw(tmp_path, "a.json", card))
    assert r.returncode == 1 and "nothing closes" in r.stdout and "in a row" in r.stdout and "70 minutes" in r.stdout


def test_lore(tmp_path):
    r = run("lore", jw(tmp_path, "a.json", {"tiers": [{"dc": 10, "reveals": "a"}, {"dc": 12, "reveals": "b"}]}))
    assert r.returncode == 1 and "use 3 to 5" in r.stdout and "step each tier" in r.stdout
    ok = {"tiers": [{"dc": 10, "reveals": "a"}, {"dc": 15, "reveals": "b"}, {"dc": 20, "reveals": "c", "twist": True}]}
    r = run("lore", jw(tmp_path, "b.json", ok))
    assert r.returncode == 0 and "warn:" not in r.stdout


def test_arc(tmp_path):
    card = {"chapters": [{"name": "1", "level": 3, "gold": 10}, {"name": "2", "level": 2}, {"name": "3", "level": 5, "gold": 90}]}
    r = run("arc", jw(tmp_path, "a.json", card))
    assert r.returncode == 1 and "below the chapter" in r.stdout and "jumps 3" in r.stdout and "finale holds" in r.stdout
