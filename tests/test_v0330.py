import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def mystery_base(clues, **kw):
    return dict({"party_level": 3, "conclusions": [{"id": "a"}],
                 "suspects": [{"name": "x"}, {"name": "y"}, {"name": "z"}], "clues": clues}, **kw)


def test_mystery_payload(tmp_path):
    clues = [{"id": "c1", "points_to": "a", "payload": "lead", "difficulty": "hard"},
             {"id": "c2", "points_to": "a", "payload": ["foe", "backstory"], "fact": "the mill burned", "difficulty": "hard"},
             {"id": "c3", "points_to": "a", "payload": "lead", "difficulty": "easy"}]
    r = run("mystery", str(jw(tmp_path, "m.json", mystery_base(clues, backstory=["the mill burned", "the heir lived"]))),
            "--payload")
    assert r.returncode == 0, r.stdout
    assert "c1: hard (cost 3) for a payload worth 1" in r.stdout
    assert "c2: hard" not in r.stdout
    assert "2 of 3 clues are hard" in r.stdout
    assert "backstory fact 'the heir lived' has no clue" in r.stdout
    assert "'the mill burned'" not in r.stdout


def test_mystery_payload_fake(tmp_path):
    clues = [{"id": "c1", "points_to": "a", "payload": "lead", "fake": True, "planted_by": "the butler"}] * 3
    r = run("mystery", str(jw(tmp_path, "m.json", mystery_base(clues))), "--payload")
    assert r.returncode == 1 and "fake clue with no why" in r.stdout


def test_district_visit(tmp_path):
    ds = [{"name": "Docks", "watch": 2, "bribe": 5, "gate": "open", "curfew": "none", "owner": "guild",
           "goods": "rope", "first_visit": {"image": "gulls on the masts", "risk": "a pickpocket"}},
          {"name": "Hill", "watch": 4, "bribe": 20, "gate": "pass", "curfew": "dusk", "owner": "lords"}]
    r = run("district", str(jw(tmp_path, "d.json", ds)), "--visit", "shopping")
    assert "shopping visit: prep goods, prices" in r.stdout
    assert "Docks: shopping visit with no prices" in r.stdout
    assert "Docks: first_visit" not in r.stdout
    assert "Hill: first_visit has no image" in r.stdout and "Hill: first_visit has no risk or benefit" in r.stdout


def trap(**kw):
    return dict({"name": "t", "trigger": "plate", "detection": "perception", "disable": "thievery",
                 "effect": "darts", "severity": "setback"}, **kw)


def test_trap_fields(tmp_path):
    traps = [trap(name="glyph", kind="magical", detect_dc=20, confirm_dc=15, tell={"dc": 22, "text": "a hum"}),
             trap(name="pit", kind="mechanical", built=True, disarm_fail="drops a stone", bypass="a hidden latch"),
             trap(name="gas", built=True, save_every_turn=True, disarm_fail="x")]
    r = run("trap", str(jw(tmp_path, "t.json", traps)))
    assert r.returncode == 0, r.stdout
    assert "glyph: magical trap countered only by thievery" in r.stdout
    assert "glyph: confirm_dc 15 below detect_dc 20" in r.stdout
    assert "glyph: tell DC 22 is not under detect_dc 20" in r.stdout
    assert "glyph: no disarm_fail" in r.stdout
    assert "pit:" not in r.stdout
    assert "gas: built trap with no bypass" in r.stdout and "gas: a save every turn with no immunity" in r.stdout


def test_trap_complex_and_lockdown(tmp_path):
    traps = [trap(name="flood", complex={"start": 0, "per_round": 2, "harm_at": 5, "delay_action": "bail"},
                  lockdown=True, door={"ac": 18, "hp": 40}),
             trap(name="fast", complex={"per_round": 5, "harm_at": 5, "delay_action": "x", "end": "y"})]
    r = run("trap", str(jw(tmp_path, "t.json", traps)), "--complex")
    assert "flood: harm starts in round 3" in r.stdout
    assert "flood: complex with no end" in r.stdout
    assert "fast: harm in round 1" in r.stdout
    assert "lockdown door has no pick_dc" in r.stdout and "lockdown with no exit" in r.stdout
    assert r.returncode == 1


def test_oneshot_newbies(tmp_path):
    card = {"bond": "family", "plot": "duty", "finish": "stop the flood", "level": 1,
            "pregens": [{"name": "A", "role": "fighter", "stake": "x", "questions": ["q", "r"]},
                        {"name": "B", "role": "healer", "stake": "x", "questions": ["q", "r"]}],
            "scenarios": [{"name": "bridge", "teaches": "checks", "soft_fail": "wet", "retry_easier_by": 2,
                           "debrief": "say why", "ally_gain": "ferryman", "spotlight": ["fighter"]},
                          {"name": "pit", "teaches": "saves", "instant_death": True, "spotlight": "fighter"}]}
    r = run("oneshot", str(jw(tmp_path, "o.json", card)), "--newbies")
    assert "bridge:" not in r.stdout
    assert "pit: no soft_fail" in r.stdout and "pit: no ally_gain" in r.stdout
    assert "pit: instant death at level 1 with no backup characters" in r.stdout
    assert "role healer: no scenario puts it in the spotlight" in r.stdout
    assert "role fighter" not in r.stdout


def test_awards_process_and_end(tmp_path):
    f = tmp_path / "s1.md"
    f.write_text("process: Ana | camp | 50\nprocess: Bo | ambush | 20\nprocess: Ana | ambush | 20\n"
                 "process: Bo | dancing | 10\nend: fled-with | 300\n", encoding="utf-8")
    r = run("awards", str(f))
    assert r.returncode == 0, r.stdout
    assert "process XP ambush 40, camp 50, dancing 10" in r.stdout
    assert "process kind 'dancing'" in r.stdout
    assert "end state fled-with (300 XP)" in r.stdout
    f.write_text("end: escaped | 100\n", encoding="utf-8")
    assert run("awards", str(f)).returncode == 1


def test_wander_table_origins(tmp_path):
    rows = [{"name": "pilgrims", "from": "0304", "weight": 2},
            {"name": "wolves", "combat": True, "from": "0102", "purpose": "hunting"},
            {"name": "clash", "meets": ["pilgrims", "trolls"]},
            {"name": "fog", "soft": True}, {"name": "rain", "soft": True, "complication": 20}]
    r = run("wander", "--table", str(jw(tmp_path, "w.json", rows)))
    assert "pilgrims: comes from 0304 with no purpose" in r.stdout
    assert "wolves:" not in r.stdout
    assert "clash: meets 'trolls', not on the table" in r.stdout
    assert "fog: soft entry with no complication" in r.stdout and "rain:" not in r.stdout


def test_rooms_alarm_lookout_prior_party(tmp_path):
    rooms = {"rooms": [{"name": "gate", "timer": "x", "threat": "x", "treat": "x", "alarm": "warn"},
                       {"name": "hall", "timer": "x", "threat": "x", "treat": "x", "alarm": "dance", "lookout": 2,
                        "prior_party": {"fate": "eaten"}}]}
    r = run("rooms", str(jw(tmp_path, "r.json", rooms)))
    assert "gate: alarm warn with no lookout rounds" in r.stdout
    assert "hall: alarm 'dance'" in r.stdout
    assert "hall: prior_party with no left" in r.stdout
    rooms["rooms"][1]["lookout"] = "soon"
    assert run("rooms", str(jw(tmp_path, "r2.json", rooms))).returncode == 1


def test_site_prior_party(tmp_path):
    d = {"location": "x", "entries": ["a", "b"], "upkeep": "x", "ecology": "x", "visitors": "x",
         "prior_party": {"left": "a torn map"}}
    r = run("site", str(jw(tmp_path, "s.json", d)))
    assert "site: prior_party with no fate" in r.stdout


def test_tavern_staff(tmp_path):
    t = {"role": "map_dot", "name": "Inn", "staff": [
        {"name": "Ma", "role": "owner", "secret": "debts", "tie": "Pip"},
        {"name": "Pip", "role": "cook", "tie": "Ghost"}]}
    r = run("tavern", str(jw(tmp_path, "t.json", t)))
    assert "staff Ma" not in r.stdout
    assert "staff Pip: no secret" in r.stdout and "staff Pip: tie 'Ghost' is not another NPC" in r.stdout
