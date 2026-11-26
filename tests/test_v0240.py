import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def room(name, **kw):
    return dict({"name": name, "timer": "t", "threat": "x", "treat": "y", "stake": "s", "wonder": "w"}, **kw)


def test_rooms_gates_requires_event_clue(tmp_path):
    rooms = [room("hub", exits=["a", "b", "vault", "crypt"], events=["bell"]), room("a", keys=["red"]),
             room("b", keys=["blue"]), room("vault", requires=["red", "blue"]),
             room("crypt", locked_until="bell"), room("cell", locked=True)]
    r = run("rooms", "--keys", jw(tmp_path, "a.json", {"rooms": rooms}))
    assert r.returncode == 0, r.stdout
    assert "cell: locked with neither a key nor a locked_until event" in r.stdout
    rooms[4]["locked_until"] = "moon"
    rooms[1] = room("a", keys=["red"], exits=["note"], locks=[{"key": "x"}])
    rooms[3] = room("vault", locks=[{"requires": ["red", "blue"], "clue_in": "note"}])
    rooms.append(room("note"))
    rooms.append(room("x", keys=["x"]))
    rooms[0]["exits"].append("x")
    r = run("rooms", "--keys", jw(tmp_path, "b.json", {"rooms": rooms}))
    assert "crypt: locked until moon, but no room raises that event" in r.stdout
    assert "vault: the clue for lock blue+red is in note" not in r.stdout
    rooms[3]["locks"][0]["clue_in"] = "nowhere"
    r = run("rooms", "--keys", jw(tmp_path, "c.json", {"rooms": rooms}))
    assert r.returncode == 1 and "has its clue in nowhere, no such room" in r.stdout


def test_rooms_clue_behind_lock(tmp_path):
    rooms = [room("hub", exits=["a", "vault"]), room("a", keys=["k"]),
             room("vault", locks=[{"key": "k", "clue_in": "inner"}], exits=["inner"]), room("inner")]
    r = run("rooms", "--keys", jw(tmp_path, "a.json", {"rooms": rooms}))
    assert "the clue for lock k is in inner, not reachable before the lock" in r.stdout


def test_rooms_pieces(tmp_path):
    rooms = [room("hall", exits=["door", "side"]), room("side", items=[{"name": "cog", "piece_of": "clock"}]),
             room("door", puzzle="clock", exits=["beyond"]), room("beyond", items=[{"name": "gear", "piece_of": "clock"}])]
    r = run("rooms", "--pieces", jw(tmp_path, "a.json", {"rooms": rooms}))
    assert r.returncode == 1 and "beyond: gear (piece of clock) lies past the puzzle room door" in r.stdout
    assert "cog" not in r.stdout


def test_objective_gate_and_kill_list(tmp_path):
    rooms = [room("hall", exits=["a"]), room("a", flags=["rune"], foes=[{"name": "ogre"}]),
             room("far", flags=["rune"], foes=[{"name": "imp"}])]
    f = jw(tmp_path, "a.json", {"rooms": rooms})
    r = run("objective", f, "--gate", "rune:2", "--kill-list", "ogre,imp")
    assert r.returncode == 0
    assert "gate rune: far sets it but is unreachable" in r.stdout and "kill list: imp is in far" in r.stdout
    r = run("objective", f, "--gate", "rune:3", "--kill-list", "ogre,lich")
    assert r.returncode == 1 and "needs 3, only 2" in r.stdout and "lich is in no room's foes" in r.stdout


def test_encounter_protect_and_waves():
    r = run("encounter", "--json", "--system", "pf2e", "--level", "3", "--foe", "3",
            "--protect", "pillar:3:20", "--attackers", "2:6")
    d = json.loads(r.stdout)
    assert [o["round"] for o in d["protect"]] == [2, 4, 6]
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "5", "--foe", "5", "--morale", "half",
            "--wave", "1:4x4", "--wave", "2:4x4", "--waves")
    assert "day budget of 240" in r.stdout and "warn: waves total" in r.stdout


def test_rest_interrupt():
    r = run("rest", "--interrupt", "20", "--step", "5", "--hours", "4")
    assert "hour 1: event on 20+ (5%)" in r.stdout and "hour 3: event on 10+ (55%)" in r.stdout
    assert "expected first event at hour" in r.stdout


def test_rumors_quests(tmp_path):
    d = {"quests": ["mill", "well", "tower"],
         "rumors": [{"quest": "mill", "true": "yes"}, {"quest": "well", "true": "later"}, {"quest": "moon", "true": "no"}]}
    r = run("rumors", jw(tmp_path, "a.json", d))
    assert r.returncode == 0 and "quest moon is not in quests" in r.stdout and "quest tower has no rumour" in r.stdout
    d["rumors"].append({"true": "maybe"})
    r = run("rumors", jw(tmp_path, "b.json", d))
    assert r.returncode == 1 and "rumor 4: no quest" in r.stdout and "true must be yes, no or later" in r.stdout


def test_chase_pursuit_stations():
    r = run("chase", "--lead", "1", "--stations", "1", "--seed", "3")
    assert "over 1 stations 47.5% (exact)" in r.stdout
    assert "sample:" in r.stdout
    r = run("chase", "--lead", "2", "--stations", "6", "--pursuer", "5", "--seed", "1")
    assert "station 6:" in r.stdout
