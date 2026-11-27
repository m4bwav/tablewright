import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes((data if isinstance(data, str) else json.dumps(data)).encode("utf-8"))
    return f


REALM = {"ruler": {"name": "Ola", "title": "Margravine", "chosen_by": "birth", "goal": "hold the pass"},
         "relations": [{"name": "East", "deterrent": "forts", "posture": "wary"}], "entry": "a toll bridge",
         "places": [{"name": "Moor", "controlled": False, "hook": "lights"}], "culture": {"custom": "bells"}}


def test_realm_check(tmp_path):
    r = run("realm", jw(tmp_path, "r.json", REALM), "--check")
    assert r.returncode == 0 and "no capital" in r.stdout and "no backers or threats" in r.stdout
    full = dict(REALM, capital="Hold", population=40000, main_population="hill folk", exports=["wool"],
                militia_arms="spears", standing_force="300 riders", threats=["East"],
                minorities=[{"name": "Fen", "band": "few", "share": 0.08, "attitude": "friendly"},
                            {"name": "Ash", "band": "some", "attitude": "hostile"}])
    r = run("realm", jw(tmp_path, "f.json", full), "--check")
    assert "over the few ceiling 5%" in r.stdout and "no capital" not in r.stdout
    bad = dict(full, minorities=[{"name": "Fen", "band": "lots"}])
    r = run("realm", jw(tmp_path, "b.json", bad), "--check")
    assert r.returncode == 1 and "band 'lots' undefined" in r.stdout


def test_realm_patron(tmp_path):
    r = run("realm", jw(tmp_path, "p.json", dict(REALM, patron={"name": "Guild", "pays": "grain"})))
    assert r.returncode == 1 and "no if_stops" in r.stdout
    ok = dict(REALM, patron={"name": "Guild", "pays": "grain", "if_stops": "riots"})
    assert run("realm", jw(tmp_path, "q.json", ok)).returncode == 0


def test_habitation():
    r = run("habitation", "--terrain", "fertile", "--area", "500")
    assert "place 5" in r.stdout and "robber forts (the leftovers): 0" in r.stdout
    r = run("habitation", "--terrain", "harsh", "--area", "1600")
    assert "place 4" in r.stdout and "robber forts (the leftovers): 2" in r.stdout
    assert run("habitation", "--terrain", "rough", "--area", "0").returncode == 2


def test_table_origins(tmp_path):
    t = tmp_path / "t.csv"
    t.write_bytes(b"roll,kind,difficulty,avoidable,where,origin\n1-3,traders,easy,yes,road,Port Ash\n"
                  b"4-5,raiders,hard,yes,water,\n6,weather,,,road,\n")
    r = run("table", t, "--die", "6")
    assert "route or water rows 4-5, 6 have no origin" in r.stdout


def test_site_castle_kind(tmp_path):
    base = {"location": "a crag", "entries": ["gate", "postern"], "upkeep": "x", "ecology": "x", "visitors": "x"}
    r = run("site", jw(tmp_path, "s.json", dict(base, kind="castle")))
    assert "castle with no castle_kind" in r.stdout
    r = run("site", jw(tmp_path, "t.json", dict(base, kind="castle", castle_kind="border fort")))
    assert "castle_kind" not in r.stdout
    assert "castle_kind 'palace'" in run("site", jw(tmp_path, "u.json", dict(base, castle=True, castle_kind="palace"))).stdout


CARD = """## Vane
- wants: the harbour
- public: a kind shipwright
- reach: the guild protects her
- harm: debts
- harm: rumours
- escape: a fast boat
- absent: buys the docks
"""


def test_villain_scheme(tmp_path):
    r = run("villain", jw(tmp_path, "v.md", CARD + "- followers: dockhands\n"), "--scheme")
    for w in ("no motive", "no side_goal", "0 step:", "no if_wins", "0 stop:", "split into hireling"):
        assert w in r.stdout
    good = CARD + ("- motive: envy because the guild passed her over\n- side_goal: see her nephew wed\n"
                   "- step: buy debts; interrupt: the ledger\n- step: call them in; interrupt: the court\n"
                   "- step: seize the docks; interrupt: the strike\n- if_wins: tolls double\n"
                   "- stop: expose the ledger\n- stop: win the guild vote\n- hireling: guards\n- henchman: Rook\n")
    r = run("villain", jw(tmp_path, "w.md", good), "--scheme")
    assert "steps 3, stops 2, hirelings 1, henchmans 1, lackeys 0" in r.stdout
    assert "no motive" not in r.stdout and "interrupt" not in r.stdout.replace("[Vane]", "")


def test_street():
    r = run("street", "--district", "market", "--time", "day", "--season", "summer", "--seed", "1")
    assert r.returncode == 0 and "around you" in r.stdout and "(night)" not in r.stdout
    r = run("street", "--district", "noble", "--time", "night", "--season", "winter", "--seed", "1")
    assert "the street is empty" in r.stdout


def test_pockets():
    r = run("pockets", "--who", "clerk", "--district", "rough", "--seed", "4")
    assert r.returncode == 0 and "clerk (rough district)" in r.stdout
    n = int(r.stdout.split(": ")[1].split()[0])
    assert 1 <= n <= 4 and r.stdout.count("d20") == n
    assert run("pockets", "--who", "x", "--district", "palace").returncode == 2


def test_building_promote(tmp_path):
    led = tmp_path / "b.json"
    r = run("building", "--district", "slum", "--seed", "2")
    assert r.returncode == 0 and r.stdout.startswith("slum: ")
    run("building", "--district", "docks", "--seed", "1", "--promote", "smugglers", "--ledger", led)
    r = run("building", "--district", "noble", "--seed", "1", "--promote", "the heir", "--ledger", led)
    assert "promoted: building 2" in r.stdout and len(json.loads(led.read_bytes())) == 2


def test_district_street_bits(tmp_path):
    base = {"name": "A", "watch": "weak", "bribe": 2, "curfew": "none", "owner": "guild", "gate": "open",
            "patrol_style": "hands-off"}
    city = {"districts": [base], "street_bits": [{"name": "the singing fishwife", "hidden": "a spy"}]}
    r = run("district", jw(tmp_path, "c.json", city))
    assert "1 street bits in the city, want 3 to 6" in r.stdout and "no if_harmed" in r.stdout
    bits = [{"name": f"b{i}", "hidden": "h", "if_harmed": "riot"} for i in range(4)]
    r = run("district", jw(tmp_path, "d.json", {"districts": [base], "street_bits": bits}))
    assert "street bit" not in r.stdout
