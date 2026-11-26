import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def room(name, **kw):
    return dict({"name": name, "timer": "t", "threat": "x", "treat": "y", "stake": "s", "wonder": "w"}, **kw)


def test_rooms_keys_multi_entry(tmp_path):
    rooms = {"rooms": [room("gate", entry=True, exits=["den"]), room("den", keys=["iron"], exits=["gate"]),
                       room("sewer", entry=True, exits=["vault"]), room("vault", locks=["iron"])]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", rooms))
    assert r.returncode == 1 and "key iron is never reachable from sewer" in r.stdout
    assert "from gate" not in r.stdout
    rooms["rooms"][2]["exits"] = ["vault", "den"]
    assert run("rooms", "--keys", jw(tmp_path, "b.json", rooms)).returncode == 0


def test_rooms_keys_multi_key_lock(tmp_path):
    bad = {"rooms": [room("gate", exits=["hall", "den"]), room("den", keys=["red"]),
                     room("hall", locks=[["red", "blue"]], exits=["vault"]), room("vault", keys=["blue"])]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", bad))
    assert r.returncode == 1 and "key blue can only be reached through its own lock (blue+red)" in r.stdout
    ok = {"rooms": [room("gate", exits=["hall", "den"]), room("den", keys=["red", "blue"]),
                    room("hall", locks=[["red", "blue"]])]}
    assert run("rooms", "--keys", jw(tmp_path, "b.json", ok)).returncode == 0


def test_rooms_keys_flee_to(tmp_path):
    bad = {"rooms": [room("gate", exits=["hall"], foes=[{"name": "kobolds", "flee_to": "attic"}]), room("hall")]}
    r = run("rooms", "--keys", jw(tmp_path, "a.json", bad))
    assert r.returncode == 1 and "gate: kobolds flees to attic, no such room" in r.stdout
    rooms = {"rooms": [room("gate", exits=["hall", "den"]), room("den", keys=["iron"]),
                       room("hall", foes=[{"name": "boss", "flee_to": "vault"}], exits=["vault"]),
                       room("vault", locks=["iron"])]}
    r = run("rooms", "--keys", jw(tmp_path, "b.json", rooms))
    assert r.returncode == 0 and "hall: boss flees to vault behind lock iron with no key in hall" in r.stdout
    carry = {"rooms": [room("gate", exits=["hall"]),
                       room("hall", foes=[{"name": "boss", "flee_to": "vault", "keys": ["iron"]}], exits=["vault"]),
                       room("vault", locks=["iron"])]}
    r = run("rooms", "--keys", jw(tmp_path, "c.json", carry))
    assert "boss carries key iron and flees past its lock to vault; the key goes out of reach" in r.stdout
    assert "behind lock" not in r.stdout
