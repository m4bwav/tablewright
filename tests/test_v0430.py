import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes(json.dumps(data).encode("utf-8"))
    return f


def test_adventure_false_patron(tmp_path):
    full = {"name": "Mira", "motive": "wants the mine", "knows": "the map", "intermediaries": ["a clerk"],
            "betrayal_trigger": "the party finds the deed", "escape": "a boat", "tell": "pays too much"}
    r = run("adventure", jw(tmp_path, "a.json", {"patron": full}), "--false-patron")
    assert r.returncode == 0 and "ok: false patron Mira" in r.stdout
    r = run("adventure", jw(tmp_path, "b.json", {"patron": {"name": "X", "motive": "m"}}), "--false-patron")
    assert r.returncode == 1 and "no escape:" in r.stdout and "no intermediaries" in r.stdout


def test_site_bluffs():
    r = run("site", "--bluffs", "4", "--guardian", "9", "--seed", "3")
    assert r.stdout.count("(fake)") == 3 and r.stdout.count("(REAL") == 1
    assert "9 defenders; they break and flee after 3 fall" in r.stdout
    assert run("site", "--bluffs", "1").returncode == 2


def test_npcs_whereabouts():
    r = run("npcs", "--whereabouts", "day", "--roll", "90")
    assert "day: home 20%, out 60%, disguised in the crowd 20%" in r.stdout and "d100 90: disguised in the crowd" in r.stdout
    assert "d100 5: home" in run("npcs", "--whereabouts", "morning", "--roll", "5").stdout


def test_venues_den():
    r = run("venues", "--den", "--cap", "300", "--seed", "1")
    assert "at most 300 gp a night" in r.stdout and r.stdout.count("game: ") == 3
    assert r.stdout.count("(any order)") == 2
    assert run("venues").returncode == 2


def test_odds_shown():
    r = run("odds", "Q", "--unlikely", "--shown", "deadly", "--roll", "50")
    assert "shown as deadly, true chance 25%" in r.stdout and "warn:" not in r.stdout
    assert "warn: shown safe is safer" in run("odds", "Q", "--shown", "safe", "--roll", "50").stdout


def test_travel_carry():
    r = run("travel", "--miles", "40", "--terrain", "plains", "--known", "--carry")
    assert "day 1: 18.0 miles, hex 3 plus 0.00 carried" in r.stdout
    assert "day 2: 36.0 miles, hex 6 plus 0.00" in r.stdout and "day 2: goal is in this hex, 4.0 miles on" in r.stdout
    r = run("travel", "--miles", "40", "--terrain", "plains", "--known", "--carry", "--hex-miles", "5")
    assert "hex 3 plus 0.60 carried" in r.stdout


def test_travel_transition():
    assert "6 miles left today become 1.5 (x0.25)" in run("travel", "--transition", "road-mountain", "--left", "6").stdout
    assert "4 miles left today become 8 (x2)" in run("travel", "--transition", "mountain-road", "--left", "4").stdout
    assert "x1.5" in run("travel", "--transition", "forest-plains", "--left", "4").stdout
    assert run("travel", "--transition", "road-lava").returncode == 2


def test_wander_per_hex():
    r = run("wander", "--per-hex", "--status", "wild", "--hexes", "12")
    assert "wild: one check per hex entered, 1 in 6; 12 hex(es): about 2.0" in r.stdout
    assert run("wander", "--per-hex", "--town-miles", "5").stdout.startswith("civilized")
    assert run("wander", "--per-hex", "--city-miles", "50").stdout.startswith("wild")
    assert "roll on the swamp table" in run("wander", "--per-hex", "--status", "border", "--mixed", "plains,swamp").stdout


def test_wander_build():
    r = run("wander", "--build", "d4+d6")
    assert "  2:  4.2%  rare" in r.stdout and "  5: 16.7%  common" in r.stdout and " 10:  4.2%  rare" in r.stdout
    assert run("wander", "--build", "d6+d6").returncode == 2


def test_rumors_calendar(tmp_path):
    items = [{"id": "fire", "happened": 1, "month": 2, "text": "the mill burned"},
             {"id": "fire2", "happened": 3, "month": 3, "text": "arson suspected", "updates": "fire"},
             {"id": "duke", "happened": 2, "month": 4, "text": "the duke travels", "cancelled_by": "PCs held the road"},
             {"id": "ghost", "month": 4, "text": "a ghost on the hill", "dead_end": True}]
    r = run("rumors", "--calendar", jw(tmp_path, "c.json", {"items": items}))
    assert r.returncode == 0 and "month 2: fire: the mill burned (lag 1)" in r.stdout
    assert "updates fire" in r.stdout and "cancelled by PCs held the road" in r.stdout and "[dead end]" in r.stdout
    bad = [{"id": "a", "happened": 5, "month": 3}, {"id": "b", "month": 1, "updates": "a"}]
    r = run("rumors", "--calendar", jw(tmp_path, "d.json", {"items": bad}))
    assert r.returncode == 1 and "before it happened" in r.stdout and "not an earlier item" in r.stdout
