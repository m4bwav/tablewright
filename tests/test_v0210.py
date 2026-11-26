import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_morale_leader_cumulative():
    r = run("morale", "--leader-cumulative", "25")
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert lines[0] == "round 1: 25% this round, 25% fled by now"
    assert lines[-1].startswith("round 4: 100% this round, 100%")
    r = run("morale", "--leader-cumulative", "5")
    assert r.stdout.count("round ") == 10
    r = run("morale", "--leader-cumulative", "30", "--seed", "3")
    assert "d100" in r.stdout and "they flee in round" in r.stdout
    assert run("morale", "--leader-cumulative", "0").returncode == 2


def test_encounter_boss_dpr():
    base = ("encounter", "--system", "pf2e", "--level", "3", "--foe", "5")
    r = run(*base, "--boss-dpr", "30", "--pc-hp", "40,28,35")
    assert "kills the lowest PC (28 HP) in one round" in r.stdout
    r = run(*base, "--boss-dpr", "20", "--pc-hp", "40,28,35")
    assert "one round" not in r.stdout
    assert "no --pc-hp" in run(*base, "--boss-dpr", "20").stdout


def room(name, **kw):
    return dict({"name": name, "timer": "t", "threat": "x", "treat": "y", "stake": "s", "wonder": "w"}, **kw)


def test_rooms_keys_orphans(tmp_path):
    rooms = {"rooms": [room("a", locks=["red"]), room("b", keys=["blue"]), room("c", locks=["gold"], keys=["gold"])]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", rooms))
    assert r.returncode == 1
    assert "lock red (a) has no key" in r.stdout and "key blue (b) opens no lock" in r.stdout
    assert "key gold is in c, the room it unlocks" in r.stdout
    assert run("rooms", jw(tmp_path, "a.json", rooms)).returncode == 0


def test_rooms_keys_reach(tmp_path):
    bad = {"rooms": [room("gate", exits=["hall"]), room("hall", locks=["iron"], exits=["vault"]),
                     room("vault", keys=["iron"])]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", bad))
    assert r.returncode == 1 and "key iron can only be reached through its own lock" in r.stdout
    ok = {"rooms": [room("gate", exits=["hall", "den"]), room("hall", locks=["iron"]), room("den", keys=["iron"])]}
    r = run("rooms", "--keys", jw(tmp_path, "b.json", ok))
    assert r.returncode == 0, r.stdout
