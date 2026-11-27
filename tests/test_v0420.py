import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes(json.dumps(data).encode("utf-8"))
    return f


def tw(tmp_path, name, text):
    f = tmp_path / name
    f.write_bytes(text.encode("utf-8"))
    return f


def test_reaction_asked_and_caps():
    r = run("reaction", "--asked", "3", "--roll", "9")
    assert "asked 3 time(s) before: -4" in r.stdout and "= 5: wary" in r.stdout
    assert "capped at best case neutral" in run("reaction", "--roll", "12", "--best-case", "neutral").stdout
    assert "floored at worst case wary" in run("reaction", "--roll", "2", "--worst-case", "wary").stdout


def test_odds():
    assert "likely (75%), d100 72: yes, but with a catch" in run("odds", "Q", "--likely", "--roll", "72").stdout
    assert "unlikely (25%), d100 2: yes, and more" in run("odds", "Q", "--unlikely", "--roll", "2").stdout
    assert "even (50%), d100 60: no" in run("odds", "Q", "--roll", "60").stdout


def test_trap_rooms_density(tmp_path):
    t = {"trigger": "plate", "detection": "seam", "disable": "wedge", "effect": "darts", "severity": "hurts"}
    f = jw(tmp_path, "t.json", [dict(t, name=f"T{i}") for i in range(3)])
    r = run("trap", f, "--rooms", "8")
    assert "3 traps in 8 rooms, over about 1 in 4" in r.stdout
    assert "over about 1 in 4" not in run("trap", f, "--rooms", "12").stdout


def test_rooms_surrender(tmp_path):
    f = jw(tmp_path, "r.json", {"rooms": [{"name": "Guard", "enemies": "4 guards", "schedule": "night"},
                                          {"name": "Den", "enemies": "wolves", "flee": "to the cave"},
                                          {"name": "Hall"}]})
    r = run("rooms", f, "--surrender")
    assert r.returncode == 1 and "Guard: occupied with no surrender" in r.stdout
    assert "Den: occupied with no schedule" in r.stdout and "Hall" not in r.stdout


def test_cuts(tmp_path):
    f = jw(tmp_path, "c.json", {"pcs": ["Ana", "Bo"], "cuts": [
        {"group": ["Ana"], "tag": "docks, dusk", "ends": "cliffhanger"},
        {"group": ["Ana"], "tag": "docks, night", "ends": "cliffhanger"},
        {"group": ["Ana"], "tag": "ship", "ends": "cliffhanger"}]})
    r = run("cuts", f)
    assert "Bo is off stage for 3 cuts" in r.stdout and "every cut ends on a cliffhanger" in r.stdout
    assert "no knowledge_rule" in r.stdout and r.returncode == 0
    g = jw(tmp_path, "d.json", {"pcs": ["Ana"], "cuts": [{"group": ["Ana"], "ends": "soon"}]})
    assert run("cuts", g).returncode == 1


def test_contest_presets():
    r = run("contest", "--a", "3", "--b", "0", "--seed", "2")
    assert "winner:" in r.stdout and "hook:" in r.stdout
    r = run("contest", "--preset", "archery", "--seed", "1")
    assert r.stdout.count("end ") == 3 and "ring points 23 to 7" in r.stdout
    assert "unhorsed" in run("contest", "--preset", "joust", "--a", "2", "--b", "1", "--seed", "4").stdout


def test_rumors_retold():
    r = run("rumors", "--retold", "3", "--event", "a goat stolen", "--seed", "1")
    assert "scale 4" in r.stdout and "retelling 3: scale 14" in r.stdout and "the teller" in r.stdout


def test_tpk_reprieve():
    r = run("tpk", "--reprieve", "--seed", "1")
    assert "reprieve: " in r.stdout and "price: " in r.stdout and r.returncode == 0


def test_attendance_leaves(tmp_path):
    f = tw(tmp_path, "r.txt", "Ana\nBo\n")
    r = run("attendance", f, "--leaves", "--combat")
    assert "1. the PC slips away" in r.stdout and "finish the round" in r.stdout
    assert run("attendance", f).returncode == 2


def test_rooms_readaloud(tmp_path):
    f = jw(tmp_path, "r.json", {"rooms": [{"name": "Vault", "read_aloud": "The hall is 40 feet long. Clearly a trap."},
                                          {"name": "Cell", "read_aloud": "Damp straw and a rusted chain."}]})
    r = run("rooms", f, "--readaloud")
    assert "exact distance '40 feet'" in r.stdout and "'clearly'" in r.stdout and "Cell" not in r.stdout


def test_war_peace(tmp_path):
    f = jw(tmp_path, "w.json", {"cause": "a border toll", "goals": ["the toll", "the ford"], "stop": "the ford held",
                                "met": ["the toll"]})
    r = run("war", f, "--peace", "--weeks", "6", "--seed", "1")
    assert "week 1: sue for peace on 20%" in r.stdout and "ok: war plan" in r.stdout
    assert run("war", jw(tmp_path, "x.json", {"goals": ["x"]})).returncode == 1


def test_siege_phases(tmp_path):
    f = jw(tmp_path, "s.json", {"assault": {"attackers": 400, "defenders": 100, "waves": 4}})
    r = run("siege", f, "--phases", "--seed", "1")
    assert "wave 1: attackers lose" in r.stdout and "morale" in r.stdout
    assert any(x in r.stdout for x in ("walls fall", "surrender", "called off", "siege goes on"))
    assert run("siege", jw(tmp_path, "e.json", {}), "--phases").returncode == 2


def test_morale_recover():
    r = run("morale", "--recover", "3", "--day", "5")
    assert "day 5: -3" in r.stdout and "back to base on day 8" in r.stdout


def test_calendar_holidays():
    r = run("calendar", "--holidays", "--seed", "2")
    assert "4 holiday(s) in 12 month(s)" in r.stdout and "farming" in r.stdout
    assert run("calendar").returncode == 2


VILLAIN = "## Mora\n- wants: the mint\n- public: a banker\n- reach: guards\n- harm: debts\n- harm: rumours\n"


def test_villain_org_interview_key(tmp_path):
    org = tw(tmp_path, "o.md", "## Guild\n- delivers: loans\n- resources: gold\n- structure: hierarchy\n"
                              "- edge: ledgers\n- change: buy rivals\n- conformity: high\n- audience: nobles\n"
                              "- committee: 4\n")
    r = run("villain", org, "--org")
    assert "no procedure:" in r.stdout and "1 audience:" in r.stdout and "4d6 days" in r.stdout
    v = tw(tmp_path, "v.md", VILLAIN + "- occupation: banker\n- twist: kind to dogs\n- weakness: greed\n"
                                       "- lair: the vault\n- key: the forged ledger kept: the vault\n")
    r = run("villain", v, "--interview", "--key")
    assert "interview has no success:" in r.stdout and "want exactly one excess:" in r.stdout
    assert "from: which low score" in r.stdout and "key kept in the villain's lair" in r.stdout and r.returncode == 1


def test_adventure_matrix(tmp_path):
    f = jw(tmp_path, "a.json", {"events": [{"name": "fire", "readings": ["a", "b", "c"]}, {"name": "duel", "date": 3}],
                                "scenes": [{"name": "s1"}, {"name": "s2"}, {"name": "s3", "villain": True}]})
    r = run("adventure", f, "--matrix", "time")
    assert "event fire: no date" in r.stdout and "3 readings" in r.stdout and r.returncode == 1
    assert "no villain scene in the first third" in run("adventure", f, "--matrix", "power").stdout


def test_campaign_epic(tmp_path):
    f = jw(tmp_path, "c.json", {"epic": {"pcs": [{"name": "Ana", "identity": "a miller"}, {"name": "Bo"}],
                                         "jobs": [{"name": "watch the king", "role": "observer"},
                                                  {"name": "x", "role": "boss"}],
                                         "goals": ["save the town"]}})
    r = run("campaign", f, "--epic")
    assert "Bo: no identity" in r.stdout and "Ana: no cover_risk" in r.stdout and "superior_hidden" in r.stdout
    assert "role 'boss'" in r.stdout and "no judge" in r.stdout and "ranked ladder" in r.stdout
