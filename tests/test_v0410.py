import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes(json.dumps(data).encode("utf-8"))
    return f


def test_trial():
    r = run("trial", "--crime", "grave", "--evidence", "strong", "--against", "9", "--rank", "2", "--purse", "100",
            "--wage", "50", "--seed", "1")
    assert "held before trial" in r.stdout and "verdict: guilty" in r.stdout and "fine 600" in r.stdout
    assert "a month to pay" in r.stdout and "debt servitude for 10 month(s)" in r.stdout
    r = run("trial", "--advocate", "9", "--witnesses", "5", "--rank-gap", "3", "--seed", "1")
    assert "acquitted" in r.stdout and "halved" in r.stdout


def test_blaze(tmp_path):
    f = jw(tmp_path, "b.json", {"buildings": {"A": ["B"], "B": {"near": ["C"], "oil": True}, "C": []}})
    r = run("blaze", f, "--start", "A", "--hours", "8", "--seed", "2")
    assert r.returncode == 0 and "fire starts in A" in r.stdout and "lost:" in r.stdout
    r = run("blaze", f, "--start", "A", "--brigade", "8", "--hours", "8", "--seed", "2")
    assert "caught B" not in r.stdout and "lost: A" in r.stdout
    assert run("blaze", f, "--start", "Z").returncode == 2


def test_haggle():
    r = run("haggle", "--base", "100", "--foreign", "--wealthy", "--vital", "--unaware", "--seed", "1")
    assert "foreign +10, wealthy +15, vital +20, unaware +10" in r.stdout
    r = run("haggle", "--base", "100", "--stalls", "30", "--offer", "80", "--seed", "1")
    assert "best 1" in r.stdout and "floor (GM only): 70" in r.stdout and "offer 80: deal" in r.stdout


def test_negotiate_bribe_ask():
    r = run("negotiate", "--ask", "--wealth", "100", "--danger", "1", "--exposure", "1")
    assert "asking price: 75" in r.stdout
    r = run("negotiate", "--ask", "--wealth", "100", "--rival", "200", "--bribe", "500", "--seed", "1")
    assert "auction" in r.stdout and "meets the price" in r.stdout
    assert run("negotiate", "--ask", "--danger", "1").returncode == 2


def test_populate():
    r = run("populate", "--hexes", "30", "--seed", "5")
    assert "at home" in r.stdout and "lairs in 30 hexes" in r.stdout
    r = run("populate", "--hexes", "10", "--migrate", "--season", "winter", "--cleared", "3", "--seed", "5")
    assert r.stdout.count("newcomers:") == 3 and "hex 3 (cleared)" in r.stdout
    assert run("populate", "--hexes", "10", "--migrate").returncode == 2


def test_invest():
    r = run("invest", "--kind", "farm", "--gp", "1000", "--years", "2")
    assert "250 man-days" in r.stdout and "settlers: 2 group(s)" in r.stdout and "year 1: yield 80" in r.stdout
    r = run("invest", "--kind", "tourism", "--gp", "1000", "--years", "2")
    assert "year 2: yield 62" in r.stdout
    assert "decays to 800" in run("invest", "--kind", "road", "--gp", "1000", "--years", "1", "--no-upkeep").stdout


def test_realm_turn_and_food(tmp_path):
    f = jw(tmp_path, "r.json", {"regime": {"control": 50, "corruption": 40,
                                           "classes": {"nobles": 1, "peasants": -3}},
                                "food": {"population": 10000, "stock": 5, "harvest": 0}})
    r = run("realm", f, "--turn")
    assert "Control -15" in r.stdout and "uproar" in r.stdout and "regime falls" in r.stdout
    r = run("realm", f, "--food", "--months", "2")
    assert "starving" in r.stdout and "eat 10.0 units" in r.stdout


def test_tax_collect_trade_route():
    r = run("tax", "--collect", "1000", "--control", "45", "--kind", "trade")
    assert "collected 450" in r.stdout and "merchants goodwill -1" in r.stdout
    r = run("trade", "--route", "4", "--mods", "war,privateers", "--seed", "1")
    assert "loss chance 28%" in r.stdout and r.stdout.count(": d100 ") == 4
    assert run("trade", "--route", "2", "--mods", "dragons").returncode == 2


def test_plague(tmp_path):
    f = jw(tmp_path, "p.json", {"settlements": [
        {"name": "Ash", "pop": 900, "was": 900, "miles": {"Bree": 10, "Cole": 40}},
        {"name": "Bree", "pop": 300, "was": 900, "miles": {"Ash": 10}},
        {"name": "Cole", "pop": 600, "miles": {"Ash": 40}}]})
    r = run("plague", f, "--start", "Ash", "--months", "1", "--seed", "1")
    assert "Ash loses 300, 600 left" in r.stdout and "Cole" not in r.stdout
    r = run("plague", f, "--mode", "abandon", "--seed", "1")
    assert "Bree: 300 of 900 left" in r.stdout and "Ash: holds" in r.stdout
    assert "fire takes" in run("plague", f, "--mode", "fire", "--start", "Bree", "--seed", "1").stdout


def test_session_log_roster_sheet():
    r = run("session-log", "--roster", "Ana:3,Bo,Cy:-1")
    assert "| 1 | Ana | 45% |" in r.stdout and "victim roll: d3" in r.stdout
    r = run("session-log", "--sheet", "--roster", "Ana,Bo,Cy", "--width", "2")
    assert "| 3 | _ |" in r.stdout and "## Lights" in r.stdout and "turn lit" in r.stdout
    assert "## Unusual events" in r.stdout and "## Treasure found" in r.stdout


def test_reaction_rank_gap_and_sandbox_kit(tmp_path):
    r = run("reaction", "--rank-gap", "3", "--roll", "7")
    assert "+2 to the reaction" in r.stdout and "watch looks away" in r.stdout and "= 9" in r.stdout
    assert "-2 to the reaction" in run("reaction", "--rank-gap", "-4", "--roll", "7").stdout
    kit = ["0303", "0302", "0304", "0203", "0403", "0202", "0402", "0306"]
    f = jw(tmp_path, "s.json", {"overview": {"grid": {"cols": 8, "rows": 8}}, "start": {"hex": "0303", "kit": kit}})
    r = run("sandbox", f)
    assert "spans 8 hexes" in r.stdout and "0306 are not next to" in r.stdout
