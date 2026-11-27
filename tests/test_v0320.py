import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_alert_waves_pool():
    r = run("alert", "waves", "--pool", "5", "--every", "2", "--size", "2", "--since-alarm", "4")
    assert r.returncode == 0, r.stderr
    assert "round 6: 1 arrive, 0 left in the pool" in r.stdout
    assert "pool spent in round 6" in r.stdout
    assert "by round 4: 4 arrived, 1 defenders still to come" in r.stdout


def test_site_lair_fields(tmp_path):
    base = {"location": "a cave", "entries": ["mouth", "chimney"], "upkeep": "x", "ecology": "x", "visitors": "x"}
    r = run("site", str(jw(tmp_path, "a.json", dict(base, lair=True))))
    assert "lair: no owner" in r.stdout and "no non-fight resolution" in r.stdout and "lair: no after" in r.stdout
    full = dict(base, owner="ogre", level=3, party_size=4, after="goblins move in", resolutions=["bribe"])
    r = run("site", str(jw(tmp_path, "b.json", full)))
    assert "lair:" not in r.stdout and r.returncode == 0


def test_site_snitch(tmp_path):
    d = {"location": "x", "entries": ["a", "b"], "upkeep": "x", "ecology": "x", "visitors": "x",
         "residents": [{"name": "cook"}, {"name": "guard", "hostile": True}, {"name": "boy", "if_left": "runs to warn"}]}
    r = run("site", str(jw(tmp_path, "s.json", d)), "--snitch")
    assert "resident cook: not hostile and no if_left" in r.stdout
    assert "resident guard" not in r.stdout and "resident boy" not in r.stdout


def test_site_factions(tmp_path):
    d = {"location": "x", "entries": ["a", "b"], "upkeep": "x", "ecology": "x", "visitors": "x",
         "factions": [{"name": "rats", "truce_with": ["crows"], "after": "take the cellar"},
                      {"name": "crows", "truce_with": ["snakes"], "price": "a tithe"}]}
    r = run("site", str(jw(tmp_path, "f.json", d)))
    assert "faction rats: a truce with no price" in r.stdout
    assert "truce_with 'snakes' is not a faction here" in r.stdout
    assert "faction crows: no after:" in r.stdout


def test_chase_tally():
    r = run("chase", "--tally", "Ana:ssf s,Bo:fss,Cy:ssss".replace(" ", ""))
    assert "leader: Ana" in r.stdout
    assert "Ana: 3 success, 1 failure, net +2: ahead" in r.stdout  # exactly 2 is ahead (closed band)
    assert "Bo: 2 success, 1 failure, net +1: even" in r.stdout
    assert "warn: PCs rolled a different number" in r.stdout
    assert "defenders removed before the fight: 2" in r.stdout and "surprise: yes" in r.stdout
    r = run("chase", "--tally", "Ana:ff,Bo:ss")
    assert "Ana: 0 success, 2 failure, net -2: behind" in r.stdout and "alerted" in r.stdout
    assert run("chase", "--tally", "Ana:sx").returncode == 2


def test_adventure_elements(tmp_path):
    r = run("adventure", str(jw(tmp_path, "e.json", {"obstacles": [{"name": "gate", "solutions": ["fight"]}],
                                                       "milestones": ["fight", "boss"], "last_milestones": ["fight", "boss"]})),
            "--elements")
    for w in ("no backstory reveal_at", "no unique_foe", "obstacle gate: 1 kind", "no clock", "same pattern", "no lead_on"):
        assert w in r.stdout, w
    ok = {"backstory": {"reveal_at": "the shrine"}, "unique_foe": "the glass wolf", "clock": "dawn",
          "obstacles": [{"name": "gate", "solutions": ["fight", "talk"]}], "lead_on": "a map to the coast"}
    r = run("adventure", str(jw(tmp_path, "o.json", ok)), "--elements")
    assert "warn:" not in r.stdout and r.returncode == 0


def test_adventure_info(tmp_path):
    r = run("adventure", str(jw(tmp_path, "i.json", {"info": {"known": ["the mill burned"], "learned": ["arson"]}})), "--info")
    assert "known: the mill burned" in r.stdout and "understood: (empty)" in r.stdout
    assert "info.understood is empty" in r.stdout and "info.learned is empty" not in r.stdout


def test_puzzle_cipher(tmp_path):
    d = {"puzzles": [{"name": "door", "kind": "cipher", "critical": True, "reward": "door", "at": "hall"},
                     {"name": "plate", "kind": "cipher", "key_at": "attic", "at": "crypt"},
                     {"name": "sphinx", "kind": "riddle", "critical": True, "reward": "door", "bypass": "pay a year"}]}
    r = run("puzzle", str(jw(tmp_path, "p.json", d)))
    assert "door: cipher with no key_at" in r.stdout and r.returncode == 1
    assert "door: cipher on the critical path with no bypass" in r.stdout
    assert "plate: key_at 'attic' is not a place" in r.stdout
    assert "sphinx: riddle" not in r.stdout
    r = run("puzzle", "--encode", "Go North!", "--shift", "3")
    assert r.stdout.strip() == "Jr Qruwk!"


def test_fightcard(tmp_path):
    d = {"name": "ambush", "boss": True,
         "tiers": [{"name": "easy", "tactics": "rush", "roster": {"skeleton": 4}, "hp": 10},
                   {"name": "hard", "tactics": "Rush", "roster": {"skeleton": 6}, "hp": 14},
                   {"name": "brutal", "tactics": "flank and shoot", "roster": {"skeleton": 6, "archer": 2}}],
         "hatches": [{"name": "strain", "trigger": "after 3 rounds"}]}
    r = run("fightcard", str(jw(tmp_path, "f.json", d)))
    assert "tiers easy and hard differ only in HP or count" in r.stdout
    assert "and brutal differ" not in r.stdout
    assert "hatch strain: wants trigger" in r.stdout and "boss fight with 1 hatch" in r.stdout
    assert r.returncode == 1


def test_oneshot_party(tmp_path):
    pre = [{"name": n, "role": r, "stake": "x", "questions": ["a", "b"]}
           for n, r in (("Ash", "healer"), ("Bex", "scout"), ("Cal", "fighter"))]
    d = {"bond": "family", "plot": "heist", "finish": "the vault doors close", "pregens": pre,
         "party": {"min": 2, "max": 5}, "required": ["Bex", "Cal", "Dee"], "roles_min": {"healer": 1},
         "thefts": [{"item": "lute", "pc": "Ash"}]}
    r = run("oneshot", str(jw(tmp_path, "o.json", d)))
    assert "required pregen Dee is not in pregens" in r.stdout
    assert "3 required pregens but the party can be 2" in r.stdout
    assert "3 pregens for up to 5 players" in r.stdout
    assert "role healer: 0 required pregen(s), want 1" in r.stdout
    assert "theft of lute from Ash: tell that player first" in r.stdout


def test_sandbox(tmp_path):
    d = {"overview": {"name": "Test Reach", "grid": {"cols": 10, "rows": 8}},
         "keys": [{"hex": "0101", "title": "tower"}, {"hex": "0305", "title": "camp"}, {"hex": "1109", "title": "far"}],
         "encounters": [{"roll": 2, "kind": "group", "home": "0305", "group": "wolves"},
                        {"roll": 3, "kind": "group", "home": "0404", "group": "bandits"}],
         "factions": [{"name": "wolves", "fighters": 40}],
         "rumors": [{"roll": 1, "truth": "true", "hex": "0202"}, {"roll": 2, "truth": "false", "hex": "0606"}]}
    r = run("sandbox", str(jw(tmp_path, "sandbox.json", d)))
    assert "key far: hex 1109 is outside the 10x8 map" in r.stdout and r.returncode == 1
    assert "encounter 3: home hex 0404 is not keyed" in r.stdout
    assert "no clash entry" in r.stdout
    assert "1 of 2 encounter groups tied" in r.stdout
    assert "faction wolves: no noncombatants" in r.stdout and "40 fighters is too many" in r.stdout
    assert "rumor 1 (true) points at unkeyed hex 0202" in r.stdout
    assert "rumor chart has no half entry" in r.stdout
