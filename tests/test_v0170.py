import json
from pathlib import Path

from test_tt import run

EXAMPLE = Path(__file__).resolve().parents[1] / "skills" / "tablewright" / "references" / "journey-example.json"


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return f


def test_settlement_extras(tmp_path):
    base = {"name": "Ash", "size": "small town", "population": 1500, "civic": ["authority", "council", "defence", "hall", "walls"],
            "inns": 2}
    r = run("settlement", jw(tmp_path, "a.json", base))
    assert r.returncode == 0 and "no government block" in r.stdout and "no commerce block" in r.stdout
    full = dict(base, government="reeve", defence={"patrol": "watch"}, commerce={"banned": ["dreamleaf"]},
                lodgings=[{"name": "a", "price": 5}, {"name": "b", "price": 5}], sights=[{"name": "bell tower"}])
    r = run("settlement", jw(tmp_path, "b.json", full))
    for s in ("no muster", "no black_market", "all at one price", "no lodging carries a hook", "sight bell tower"):
        assert s in r.stdout
    ok = dict(full, defence={"patrol": "watch", "muster": "bell"}, commerce={"banned": ["x"], "black_market": "docks"},
              lodgings=[{"name": "a", "price": 5, "hook": "ghost"}, {"name": "b", "price": 2}], sights=[{"name": "t", "npc": "keeper"}])
    assert "warn:" not in run("settlement", jw(tmp_path, "c.json", ok)).stdout


def test_poison_potency_shelf(tmp_path):
    f = jw(tmp_path, "p.json", [{"name": "nightroot", "delivery": "ingested", "save": "con", "dc": 14, "interval": "1 hour",
                                 "onset": "now", "stages": ["a"], "end": "cure", "potency": "up", "shelf_life": 30, "age": 40}])
    r = run("poison", f)
    assert "DC 14 -> 16" in r.stdout and "past its 30-day shelf life" in r.stdout
    assert run("poison", jw(tmp_path, "b.json", [{"name": "x", "potency": "huge"}])).returncode == 1


def test_tracker_poison_save_each(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Ana:15:20", "Ogre:10:40", "--file", f)
    r = run("tracker", "poison", "Ana", "venom", "a,b", "3", "--save-each", "--dc", "15", "--potency", "down", "--file", f)
    assert "DC 13" in r.stdout
    run("tracker", "next", "--file", f)
    assert "venom save again, DC 13 (each round)" in run("tracker", "next", "--file", f).stdout
    assert run("tracker", "poison", "Ana", "x", "a", "--potency", "up", "--file", f).returncode == 2


def test_handouts(tmp_path):
    ok = jw(tmp_path, "h.json", {"handouts": [{"name": "letter", "purpose": "lead to mill", "sender": "the reeve"}]})
    assert run("handouts", ok).returncode == 0
    r = run("handouts", jw(tmp_path, "b.json", {"sessions_away": 3, "handouts": [{"name": "map"}]}))
    assert r.returncode == 1 and "no purpose" in r.stdout and "no sender" in r.stdout and "no recap" in r.stdout


def test_npcs_party_tactics_but(tmp_path):
    card = jw(tmp_path, "n.md", "## NPCs\n- Bram: tall but shy; mending nets; wants help because his boat sank; joins_party: yes; "
                                "tactics: open with a net\n- Cora: old; sweeping; hates rats because they bit her\n")
    r = run("npcs", card, "--but")
    assert r.returncode == 0 and "Bram: joins the party with no exit" in r.stdout and "Bram: tactics with no flee" in r.stdout
    assert "Cora: no contradiction" in r.stdout and "Bram: no contradiction" not in r.stdout


def test_encounter_spike():
    r = run("encounter", "--system", "5e", "--level", "3", "--foe", "2", "--spike", "30", "--pc-hp", "24")
    assert "burst of 30 can drop a PC" in r.stdout
    assert "no --pc-hp" in run("encounter", "--system", "5e", "--level", "3", "--foe", "2", "--spike", "9").stdout


def test_challenge_time_and_lead_in(tmp_path):
    card = {"goal": "cross", "successes": 4, "failures": 3, "skills": [{"name": "a", "kind": "x"}, {"name": "b", "kind": "y"},
            {"name": "c", "kind": "x"}], "on_fail": "time", "shown": "track", "minutes": 10, "limit": 60, "on_fail_time": 20,
            "lead_in": {"dc_shift": 2}}
    r = run("challenge", jw(tmp_path, "c.json", card))
    assert r.returncode == 0 and "takes 100 min" in r.stdout and "moves DCs -2" in r.stdout
    assert run("challenge", jw(tmp_path, "d.json", dict(card, lead_in={}))).returncode == 1


PREP = """## Opening
A bell rings.
## Leads
- a
- b
- c
## NPCs
- Reeve: wants calm
"""


def test_prep_flow(tmp_path):
    ok = PREP + "## Flow\n- start: gate -> a, b; rules: chase\n- a: alley -> finish\n- b: roofs -> finish; rules: social\n- finish: end\n"
    r = run("prep", jw(tmp_path, "a.md", ok))
    assert r.returncode == 0 and "2 path(s)" in r.stdout and "rules cheat sheet: chase (start)" in r.stdout
    bad = PREP + "## Flow\n- start: gate -> a\n- a: pit\n- c: orphan -> finish\n- finish: end\n"
    r = run("prep", jw(tmp_path, "b.md", bad))
    assert r.returncode == 1 and "a is reachable from start but cannot reach finish" in r.stdout and "nothing leads to c" in r.stdout
    one = PREP + "## Flow\n- start: gate -> finish\n- finish: end\n"
    assert "one path" in run("prep", jw(tmp_path, "c.md", one)).stdout


def test_prep_break(tmp_path):
    r = run("prep", jw(tmp_path, "a.md", "hours: 5\n" + PREP))
    assert "5 h session with no ## Break" in r.stdout
    r = run("prep", jw(tmp_path, "b.md", PREP + "## Break\n- at: 2\n"))
    assert "break with no goal_check" in r.stdout


SCENES = PREP + """## Session
- purpose: find the thief
- closing: the thief is named
## Scenes
### Docks
- purpose: meet the smuggler. Learn the price.
- type: combat
- description: wet planks and the water below
### Roof
- purpose: chase
- closing: caught
- treasure: tbd
"""


def test_prep_scenes_weak_strong(tmp_path):
    r = run("prep", jw(tmp_path, "s.md", SCENES), "--weak", "dialog", "--strong", "description")
    assert "Docks: purpose has more than one sentence" in r.stdout and "Docks: no closing" in r.stdout
    assert "combat with no victory" in r.stdout and "no dialog:" in r.stdout and "mentions water" in r.stdout
    assert r.returncode == 0
    r = run("prep", jw(tmp_path, "n.md", SCENES.replace("- purpose: find the thief\n", "").replace("- purpose: chase\n", "")))
    assert r.returncode == 1 and "no session purpose" in r.stdout and "scene Roof: no purpose" in r.stdout
    long = SCENES.replace("wet planks", "word " * 45)
    assert "runs over 40 words" in run("prep", jw(tmp_path, "l.md", long), "--strong", "description").stdout


def test_prep_review(tmp_path):
    hero = jw(tmp_path, "h.json", {"name": "Vex", "feats": ["Flight"]})
    r = run("prep", jw(tmp_path, "s.md", SCENES), "--review", "--short", "--party", hero)
    assert "drop in this order: proofreader, playtester, director" in r.stdout
    assert "proofreader: scene Docks: foes with no stats" in r.stdout and "treasure not filled" in r.stdout
    assert "director: scene Roof is not linked" in r.stdout and "playtester: Vex has flight" in r.stdout


def test_prep_npc_threads(tmp_path):
    card = PREP.replace("- Reeve: wants calm", "- Reeve: wants calm; thread: for Ana") + "## Players\n- Ana: lost brother\n- Bo: debt\n"
    r = run("prep", jw(tmp_path, "t.md", card))
    assert "Bo has no NPC thread" in r.stdout and "Ana has no NPC thread" not in r.stdout


def test_cadence():
    r = run("cadence", "--every-days", "14", "--hours", "6", "--phase", "brainstorm=1", "select=0.5", "write=3")
    assert r.returncode == 0 and "5.4 h" in r.stdout
    r = run("cadence", "--every-days", "7", "--hours", "2", "--phase", "write=3")
    assert r.returncode == 1 and "13 days" in r.stdout


def test_rival(tmp_path):
    d = {"members": [{"name": "Ise", "watches": "healer", "bond": "sister"}, {"name": "Rok"}], "principles": ["never fight fair"],
         "tactics": [{"name": "rush", "kind": "attack"}], "timeline": [{"day": 1, "event": "camp", "site": "gate", "state": "open"},
         {"day": 3, "event": "loot", "site": "vault", "state": "empty"}], "arrival_day": 2}
    r = run("rival", jw(tmp_path, "r.json", d), "--day", "2")
    assert r.returncode == 0 and "Rok: no watches" in r.stdout and "every tactic is attack" in r.stdout
    assert "no tell" in r.stdout and "no foreshadow" in r.stdout and "gate: open" in r.stdout and "vault" not in r.stdout
    assert run("rival", jw(tmp_path, "b.json", {"members": []})).returncode == 1


def test_cascade(tmp_path):
    d = {"rows": [[{"id": "a", "fate": "drowns", "next": ["c"]}, {"id": "b", "fate": "burns"}], [{"id": "c", "fate": "x"},
         {"id": "d", "fate": "y"}]], "patrons": [{"name": "p", "offer": "money"}]}
    r = run("cascade", jw(tmp_path, "c.json", d))
    assert r.returncode == 0 and "d: nothing leads to it" in r.stdout and "patron offer kind" in r.stdout and "d4 minutes" in r.stdout
    d["rows"][0][0]["next"] = ["zz"]
    d["rows"][0][1].pop("fate")
    r = run("cascade", jw(tmp_path, "b.json", d))
    assert r.returncode == 1 and "not an event" in r.stdout and "b: no fate" in r.stdout


def test_talk(tmp_path):
    assert "guilt:" in run("talk", "--list").stdout
    d = [{"petitioner": "Ana", "granter": "Duke", "want": "pardon", "opening": "flattery", "fallback": ["plea"]},
         {"petitioner": "Bo", "granter": "Cook", "want": "bread", "opening": "plea", "resist": "no", "fallback": ["bribe"]},
         {"granter": "x"}]
    r = run("talk", jw(tmp_path, "t.json", d))
    assert r.returncode == 1 and "not a leverage kind" in r.stdout and "1 fallback" in r.stdout and "no bottom_line" in r.stdout
    assert "quick answer" in r.stdout and "no petitioner" in r.stdout


def test_islands_and_move(tmp_path):
    f = jw(tmp_path, "i.json", {"islands": [{"name": "Bridge ambush", "band": "start", "kind": "fight", "at": "bridge",
                                             "entries": ["road"]}, {"name": "The heir", "band": "middle", "kind": "npc",
                                                                    "entries": ["a", "b"]}]})
    r = run("islands", f)
    assert "no island in band end" in r.stdout and "1 entry" in r.stdout and "named for its place" in r.stdout
    assert "bridge -> ford" in run("islands", "move", f, "Bridge ambush", "--to", "ford").stdout
    x = json.loads(f.read_text(encoding="utf-8"))["islands"][0]
    assert x["at"] == "ford" and x["moved"] == ["bridge"]


def test_world_principles_locations(tmp_path):
    traits = "".join(f"- t{i}: place\n" for i in range(6))
    card = "## Traits\n" + traits + "## Principles\n- a\n- b\n## Locations\n- Mill: dusty; loud; one door\n- Fen: reeds; weather: fog\n"
    r = run("world", jw(tmp_path, "w.md", card))
    assert "Principles has 2" in r.stdout and "Mill: no weather" in r.stdout and "Fen: 1 details" in r.stdout


def test_session_log_learned_review(tmp_path):
    assert "## Learned" in run("session-log", "--session", "2").stdout
    logs = []
    for i in range(3):
        logs.append(jw(tmp_path, f"l{i}.md", "- players present: Ana, Bo\n- recap: x\n## Highlights\n- s; Ana; fun\n"
                                            "## Learned\n- Ana: a; b; c\n"))
    r = run("review", *logs)
    assert "Bo was present in 3 logs" in r.stdout and "Ana was present" not in r.stdout


def test_journey_roll_and_check(tmp_path):
    r = run("journey", EXAMPLE, "--kind", "complex", "--leads", "2", "--seed", "3")
    assert r.returncode == 0 and "lead 2 (risk" in r.stdout and "complication:" in r.stdout
    assert "purpose:" in run("journey", EXAMPLE, "--seed", "1").stdout
    assert run("journey", jw(tmp_path, "e.json", {"destination": ["x"]})).returncode == 2
    leads = [{"name": "a", "risk": "low", "kind": "complex", "mission": {"objective": "x"}, "arrival": ["paid"]}]
    r = run("journey", jw(tmp_path, "l.json", leads), "--check")
    assert r.returncode == 1 and "1 lead(s)" in r.stdout and "neither a moral" in r.stdout and "no threat" in r.stdout
    assert "payment is the only" in r.stdout
    two = [{"name": "a", "risk": "low", "reward": 50, "constraint": "6 days", "arrival": ["bonus"]},
           {"name": "b", "risk": "low", "moral": "kids", "arrival": ["delay"]}]
    r = run("journey", jw(tmp_path, "t.json", two), "--check")
    assert r.returncode == 0 and "every lead is low" in r.stdout and "b: simple purpose with no travel constraint" in r.stdout


def test_journey_clash(tmp_path):
    t = {"destination": [{"text": "A"}], "patron": ["p"], "motive": ["m"], "arrival": ["paid"],
         "purpose": [{"text": "bad", "clashes": ["A"]}, {"text": "good"}]}
    out = run("journey", jw(tmp_path, "c.json", t), "--leads", "5", "--seed", "1").stdout
    assert "purpose: good" in out and "purpose: bad" not in out


def test_trade(tmp_path):
    r = run("trade", "--price", "100", "--hexes", "10")
    assert "no distance markup" in r.stdout and "price: 100" in r.stdout
    r = run("trade", "--price", "100", "--hexes", "10", "--regional", "--band", "up10", "--weights", "1", "--seed", "1")
    assert "step 2: +10% -> 121" in r.stdout
    r = run("trade", "--price", "100", "--hexes", "0", "--capacity", "10", "--sold", "10")
    assert "price: 80" in r.stdout
    assert run("trade", "--price", "100", "--hexes", "5", "--band", "up", "--regional").returncode == 2


def test_travel_oddity(tmp_path):
    f = jw(tmp_path, "o.json", {"events": [{"text": "foul week", "slow_offroad": 0.5}]})
    r = run("travel", "--miles", "48", "--terrain", "plains", "--known", "--oddity", f, "--seed", "1")
    assert "oddity: foul week" in r.stdout and "9.0 miles a day" in r.stdout
    assert "every event used" in run("travel", "--miles", "48", "--known", "--oddity", f).stdout
    g = jw(tmp_path, "r.json", {"events": [{"text": "a song", "repeat": True}], "used": ["a song"]})
    r = run("travel", "--miles", "24", "--known", "--oddity", g)
    assert "oddity: a song" in r.stdout and "24.0 miles a day" in r.stdout
