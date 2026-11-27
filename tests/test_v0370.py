import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes((data if isinstance(data, str) else json.dumps(data)).encode("utf-8"))
    return f


def test_threads_spotlight(tmp_path):
    card = ("## PCs\n- Ana\n- Bo\n- Cy\n\n## Threads\n- lost sister; pc: Ana\n- old debt; pc: Ana\n"
            "- the duel; pc: Ana; kind: conflict\n- map; pc: Bo\n")
    r = run("threads", jw(tmp_path, "t.md", card), "--spotlight")
    assert r.returncode == 1
    assert "Cy owns no thread" in r.stdout and "over 40%" in r.stdout and "no opposes" in r.stdout
    ok = ("## Threads\n- a; pc: Ana\n- b; pc: Bo; kind: conflict; opposes: the baron\n- c; pc: Cy\n")
    assert run("threads", jw(tmp_path, "o.md", ok), "--spotlight", "--pcs", "Ana,Bo,Cy").returncode == 0


def test_party_check_stakes(tmp_path):
    d = {"pcs": [{"name": "Ana", "goal": "g", "stake": "s", "blocker": "b", "threads": ["x", "y"]},
                 {"name": "Bo", "goal": "g", "threads": ["x"]}]}
    r = run("party", jw(tmp_path, "p.json", d), "--check-stakes")
    assert r.returncode == 1 and "Bo: no stake, blocker" in r.stdout and "Bo: 1 thread" in r.stdout
    assert "Ana" not in r.stdout


def test_campaign_pacing(tmp_path):
    bad = {"sessions": [
        {"name": "s1", "advances": "x", "scenes": [{"kind": "side"}, {"kind": "combat", "deadly": True}]},
        {"name": "s2", "scenes": [{"kind": "combat"}, {"kind": "combat"}, {"kind": "combat"}]},
        {"name": "fin", "finale": True, "advances": "end", "scenes": [{"kind": "combat"}]}]}
    r = run("campaign", jw(tmp_path, "c.json", bad), "--pacing")
    assert r.returncode == 1
    for s in ("no stake_raise", "s2: no advances", "non-plot", "s1: no hook", "no earlier warning", "combat is"):
        assert s in r.stdout, s
    good = {"sessions": [
        {"advances": "a", "hook": "h", "stake_raise": True,
         "scenes": [{"kind": "plot", "warning": True}, {"kind": "combat", "deadly": True}, {"kind": "plot"}]},
        {"advances": "b", "scenes": [{"kind": "plot"}]}]}
    assert run("campaign", jw(tmp_path, "g.json", good), "--pacing").returncode == 0


def test_prep_players(tmp_path):
    card = "## Scenes\n- market; serves: loot, Bo; lead: Cy\n- tower; serves: mystery\n"
    pl = [{"name": "Ana", "wants": ["mystery"]}, {"name": "Bo", "wants": []},
          {"name": "Cy", "wants": ["combat"], "engagement": "low"}]
    r = run("prep", jw(tmp_path, "p.md", card), "--players", jw(tmp_path, "pl.json", pl))
    assert r.returncode == 0
    assert "Cy: no scene serves" in r.stdout and "low engagement but leads market" in r.stdout
    assert "Ana: no scene" not in r.stdout and "Bo: no scene" not in r.stdout


def test_prep_finale(tmp_path):
    card = ("## PCs\n- Ana\n- Bo\n\n## Scenes\n- inn; conflict: debt\n- road; conflict: feud\n\n"
            "## Finale\n- duel; beat: duel; pc: Ana; opponent: Rival; conflict: feud\n- riot; beat: mayhem\n")
    r = run("prep", jw(tmp_path, "f.md", card), "--finale")
    assert r.returncode == 1
    assert "conflict debt has no finale beat" in r.stdout and "out of order" in r.stdout
    assert "no resolution beat" in r.stdout and "Bo has no personal opponent" in r.stdout


def test_villain_clues(tmp_path):
    card = "## Vex\n- wants: x\n- public: y\n- reach: z\n- harm: a\n- harm: b\n- stimuli: bells\n- weakness: salt\n- clue: chalk marks; reveals: stimuli\n"
    f = jw(tmp_path, "v.md", card)
    r = run("villain", f)
    assert r.returncode == 1 and "weakness: with no planted clue" in r.stdout and "stimuli: with no" not in r.stdout
    clues = [{"points_to": "vex", "reveals": "weakness"}, {"points_to": "vex"}]
    r = run("villain", f, "--clues", jw(tmp_path, "c.json", clues))
    assert r.returncode == 0 and "vex: 2 clue(s) point at them" in r.stdout and "3+" in r.stdout


def test_rooms_skip_and_rally(tmp_path):
    rooms = {"rooms": [
        {"name": "gate", "entry": True, "exits": ["hall"], "shortcuts": [{"door": "grate", "to": "vault"}]},
        {"name": "hall", "exits": ["den"], "xp": 40, "awards": ["idol"], "foes": [{"name": "imp", "count": 2, "flee_to": "vault"}]},
        {"name": "den", "exits": ["vault"], "xp": 60, "foes": [{"name": "rat", "flees": True}]},
        {"name": "vault", "goal": True, "foes": [{"name": "Mara"}, {"name": "guard", "count": 2}]}]}
    f = jw(tmp_path, "r.json", rooms)
    r = run("rooms", f, "--skip", "grate")
    assert r.returncode == 0, r.stderr
    assert "cut off: hall, den; 100 XP; awards idol" in r.stdout
    r = run("rooms", f, "--rally", "Mara")
    assert "min 3" in r.stdout and "max 6" in r.stdout
    assert run("rooms", f, "--skip", "nope").returncode == 2


def test_escort(tmp_path):
    rooms = {"rooms": [{"name": "a", "xp": 40, "linger": 2}, {"name": "b", "foes": [{"name": "x"}], "xp": 40},
                       {"name": "c", "linger": 2}]}
    r = run("escort", jw(tmp_path, "r.json", rooms), "Pip", "--route", "a,b,c")
    assert r.returncode == 0, r.stderr
    assert "Pip flees on the first blow and rejoins in c" in r.stdout
    assert "runs out of patience" in r.stdout and "adds 20 XP" in r.stdout


def test_tracker_curse_and_rest(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Ana:15:20", "--file", f)
    run("tracker", "hit", "Ana", "5", "--file", f)
    r = run("tracker", "curse", "Ana", "rot", "--stack", "3", "--clear-flag", "blessed", "--upkeep", "24h", "--dc", "16", "--file", f)
    assert "save now, DC 16" in r.stdout and "step 1/3" in r.stdout
    run("tracker", "curse", "Ana", "rot", "--file", f)
    r = run("tracker", "curse", "Ana", "rot", "--file", f)
    assert "no save" in r.stdout and "permanent until blessed" in r.stdout
    r = run("tracker", "rest", "Ana", "--failed", "--file", f)
    assert "rest voided" in r.stdout
    assert "15/20" in run("tracker", "show", "--file", f).stdout
    assert run("tracker", "curse", "clear", "Ana", "rot", "water", "--file", f).returncode == 2
    assert "cleared" in run("tracker", "curse", "clear", "Ana", "rot", "blessed", "--file", f).stdout
    assert "rested to 20" in run("tracker", "rest", "Ana", "--failed", "--file", f).stdout


def test_encounter_phase():
    r = run("encounter", "--system", "pf2e", "--level", "3", "--foe", "5", "--phase", "flooded floor",
            "--summons", "eel,eel", "--hazard", "3")
    assert r.returncode == 0, r.stderr
    assert "first action the field becomes flooded floor" in r.stdout and "removed at her death: eel, eel" in r.stdout
    assert "not a hazard" in r.stdout


def test_twist_prophecy(tmp_path):
    ps = [{"name": "p1", "kind": "when", "symbols": [{"symbol": "crow", "hints": ["a"]}]},
          {"name": "p2", "kind": "maybe"},
          {"name": "p3", "kind": "if", "symbols": [{"symbol": "key", "referent": "heir", "hints": ["a", "b"]}]}]
    r = run("twist", jw(tmp_path, "p.json", ps), "--prophecy")
    assert r.returncode == 1
    assert "p1: a when prophecy needs a goal" in r.stdout and "crow has no referent" in r.stdout
    assert "crow has 1 hint" in r.stdout and "p2: kind 'maybe'" in r.stdout and "p3" not in r.stdout


def test_check_lint_and_uncertain(tmp_path):
    cs = [{"name": "climb", "mods": ["rain", "rope"], "fail": "hazardous"}, {"name": "pick", "mods": []}]
    r = run("check", jw(tmp_path, "c.json", cs), "--lint")
    assert r.returncode == 1 and "climb: 2 stacked" in r.stdout and "pick: no fail tag" in r.stdout
    r = run("check", "--uncertain", "--dc", "15", "--bonus", "5", "--seed", "1")
    assert r.returncode == 0 and "odds: full 55%, partial 20%, false 25%" in r.stdout and "GM only" in r.stdout
    assert run("check", "--uncertain").returncode == 2


def test_table_roll_d1000_and_columns(tmp_path):
    t = jw(tmp_path, "t.csv", "roll,who,what\n1-500,a,x\n501-1000,b,y\n")
    r = run("table", "roll", t, "--seed", "2", "--count", "3")
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("d1000 ") == 3
    r = run("table", "roll", t, "--columns", "--seed", "2", "--count", "1")
    assert "who=" in r.stdout and "what=" in r.stdout and r.stdout.count("d1000") == 2
    assert "not a standard die" not in run("table", t).stdout
