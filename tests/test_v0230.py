import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def room(name, **kw):
    return dict({"name": name, "timer": "t", "threat": "x", "treat": "y", "stake": "s", "wonder": "w"}, **kw)


def test_rooms_roleplay_fallback(tmp_path):
    r = run("rooms", jw(tmp_path, "a.json", {"rooms": [room("gate", roleplay=True), room("hall")]}))
    assert "gate: roleplay gate with no fallback" in r.stdout
    r = run("rooms", jw(tmp_path, "b.json", {"rooms": [room("gate", roleplay=True, fallback="DC 15 Persuasion"), room("hall")]}))
    assert "fallback" not in r.stdout


def test_rooms_keys_return_and_fall(tmp_path):
    bad = {"rooms": [room("gate", exits=["hall"], foes=[{"name": "ogre", "flee_to": "hall", "return_to": "pit"}]),
                     room("hall", foes=[{"name": "imp", "fall": 6}])]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", bad))
    assert r.returncode == 1 and "ogre returns to pit, no such room" in r.stdout
    assert "imp has fall damage but no flee_to" in r.stdout
    bad["rooms"][0]["foes"][0]["return_to"] = "gate"
    r = run("rooms", "--keys", jw(tmp_path, "b.json", bad))
    assert r.returncode == 0 and "returns to gate with no return_after" in r.stdout


def test_xp_gap():
    r = run("xp-gap", "--party", "4", "--level", "3", "--award", "7000")
    assert "PC 1: 50 XP short of level 4" in r.stdout and "warn: 4 PC(s)" in r.stdout
    r = run("xp-gap", "--party", "4", "--level", "3", "--award", "7600")
    assert "levels with 100 XP to spare" in r.stdout and "ok: every PC reaches level 4" in r.stdout
    r = run("xp-gap", "--level", "1", "--award", "300", "--each", "--xp", "0,100")
    assert "PC 2: levels with 100 XP to spare" in r.stdout
