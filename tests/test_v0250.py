import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def room(name, **kw):
    return dict({"name": name, "timer": "t", "threat": "x", "treat": "y", "stake": "s", "wonder": "w"}, **kw)


def test_xp_award_once_and_rescues(tmp_path):
    d = {"party": [{"name": "Ana", "xp_to_next": 1000}, {"name": "Bo", "xp_to_next": 1000}],
         "rescues": 3,
         "foes": [{"name": "guard", "xp": 100, "outcome": "killed", "encounter": "gate", "how": "kill"},
                  {"name": "guard2", "xp": 100, "outcome": "killed", "encounter": "gate", "how": "kill"},
                  {"name": "ogre", "xp": 200, "outcome": "persuaded", "how": "parley"}]}
    r = run("xp", jw(tmp_path, "a.json", d), "--award-once", "--per-rescue", "50")
    assert r.returncode == 0, r.stdout
    assert "encounter gate already awarded" in r.stdout and "kill 1, parley 1" in r.stdout
    assert "rescues: 3 x 50 = 150 XP" in r.stdout and "foe XP 450" in r.stdout
    d["foes"][2]["how"] = "bribe"
    r = run("xp", jw(tmp_path, "b.json", d), "--award-once")
    assert r.returncode == 1 and "how bribe" in r.stdout


def test_rooms_routes_alarm(tmp_path):
    rooms = [room("gate", exits=["hall", "side"], xp=40), room("hall", exits=["throne"], xp=80),
             room("side", exits=["throne"], xp=30, alarm_to="hall"), room("throne", goal=True, xp=200)]
    r = run("rooms", "--routes", jw(tmp_path, "a.json", {"rooms": rooms}))
    assert "route gate > hall > throne: 320 XP, biggest fight 200 XP" in r.stdout
    assert "side: on alarm its foes join hall; that fight becomes 110 XP" in r.stdout


def test_rooms_schedule_muffle_teleport_hooks(tmp_path):
    rooms = [room("barracks", exits=["shrine"], noise=True, schedule={"asleep": 2, "patrol": 1, "rite": 1},
                  lethal=["patrol", "rite"], hooks=[{"name": "whisper", "dc": 15}]),
             room("shrine", muffled=True, exits=["maze"]),
             room("maze", teleport=["shrine", "pit"]), room("pit"), room("out", exit=True)]
    f = jw(tmp_path, "a.json", {"rooms": rooms})
    r = run("rooms", "--schedule", f)
    assert "barracks: asleep 2/4 (50%), party surprises them" in r.stdout and "lethal window (patrol, rite) 50%" in r.stdout
    r = run("rooms", "--muffle", f)
    assert "barracks: noise heard in no room; damped by shrine" in r.stdout
    r = run("rooms", "--teleport", f)
    assert r.returncode == 1 and "a roll of pit strands the party" in r.stdout and "no bypass" in r.stdout
    r = run("rooms", "--hooks", f)
    assert "hook whisper is gated by a check (dc 15) with no later" in r.stdout


def test_encounter_buff_scale_trigger():
    r = run("encounter", "--json", "--system", "pf2e", "--level", "3", "--party", "6", "--foe", "3", "--foe", "3",
            "--scale", "3:0,6:1", "--buff-source", "idol", "--wave", "1:2x2", "--trigger", "bloodied",
            "--mission", "rescue", "--clock", "3", "--morale", "half")
    d = json.loads(r.stdout)
    assert d["xp"] == 120 and d["buffed_xp"] == 180
    assert any("adds 1 foe" in n for n in d["notes"])
    assert any("enters when a foe on the field is bloodied" in n for n in d["notes"])
    assert any("the mission is rescue" in w for w in d["warnings"])


def test_treasure_gap_and_ritual():
    r = run("treasure-gap", "--level", "5", "--party-gold", "3000")
    assert "par wealth at level 5: 2500 gp a PC" in r.stdout and "pay out 1750 a PC (7000 total)" in r.stdout
    r = run("ritual", "--level", "2")
    assert "no misfortune roll" in r.stdout
    r = run("ritual", "--level", "6", "--interrupted")
    assert "misfortune on d20 11 or less (55%), severity serious" in r.stdout


def test_doomtrack_stages_and_renewal():
    r = run("doomtrack", "--stages", "birth:7,growth:90,formed", "--acts", "2")
    assert "birth: day 0 to 1" in r.stdout and "growth: day 1 to 77" in r.stdout and "formed: from day 77" in r.stdout
    r = run("doomtrack", "--renewal", "28", "--streak", "3")
    assert "permanent after 3 unbroken recasts (day 84)" in r.stdout
    assert run("doomtrack").returncode == 2


def test_chase_collapse_and_site_recorrupt():
    r = run("chase", "--collapse", "120", "--head-start", "10", "--edge-speed", "40")
    assert "safety in 4 round(s)" in r.stdout and "edge catches the party in round 1" in r.stdout
    r = run("chase", "--collapse", "60", "--accel", "0")
    assert "does not catch them" in r.stdout
    r = run("site", "--recorrupt", "10", "--live", "2", "--minus-per-live", "3")
    assert "2 villain(s) alive: the node reverts on day 4" in r.stdout and "0 villain(s) alive: the node reverts on day 10" in r.stdout


def test_boons_once_per_pc(tmp_path):
    d = {"boons": [{"name": "luck", "once_per_pc": True}, {"name": "vigor", "xp": 6000}],
         "pcs": [{"name": "Ana", "level": 3, "boons": ["luck", "luck"]}, {"name": "Bo", "level": 3, "boons": ["vigor"]}]}
    r = run("boons", jw(tmp_path, "a.json", d))
    assert r.returncode == 1 and "Ana: luck taken 2 times" in r.stdout and "Bo: boon XP 6000 jumps level 3 to 5" in r.stdout


def test_hazard_reset_wander_rooms_adventure_objective_hold(tmp_path):
    t = [{"name": "blade", "trigger": "t", "detection": "d", "disable": "x", "effect": "e", "severity": "setback",
          "guards": "dial", "reset": "1 minute"}]
    r = run("trap", jw(tmp_path, "t.json", {"traps": t}), "--reset")
    assert r.returncode == 1 and "blade: guards dial with no retry" in r.stdout
    rooms = [room("a", foes=[{"name": "orc", "xp": 50, "patrol": True}, {"name": "rat", "xp": 10}]), room("b")]
    f = jw(tmp_path, "r.json", {"rooms": rooms})
    r = run("wander", "--from-rooms", str(f))
    assert "1: orc (from a, 50 XP)" in r.stdout and "a: 1 foe(s) stay, 10 XP" in r.stdout
    sc = [{"name": "brawl", "pillar": "combat"}, {"name": "feast", "pillar": "social", "optional": True},
          {"name": "ruin", "pillar": "explore"}, {"name": "duel", "pillar": "either", "optional": True}]
    r = run("adventure", jw(tmp_path, "s.json", {"scenes": sc}), "--pillars")
    assert r.returncode == 0 and "social: 0 required, 1 optional" in r.stdout
    r = run("objective", str(f), "--hold-rounds", "5", "--wipe-counts")
    assert "hold for 5 rounds; the hold counts even if" in r.stdout and "no room has an anchor or rite" in r.stdout
