import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes((data if isinstance(data, str) else json.dumps(data)).encode("utf-8"))
    return f


def test_rulings_log(tmp_path):
    f = tmp_path / "r.json"
    r = run("rulings", "add", "--question", "Can you ready a shove?", "--call", "yes, as a reaction",
            "--source", "core p. 10", "--file", f)
    assert r.returncode == 0 and "ruling 1 logged" in r.stdout
    r = run("rulings", "add", "--question", "Flanking with a reach weapon", "--call", "no", "--revisit", "--file", f)
    assert "no source" in r.stdout
    assert "2 of 2" in run("rulings", "--file", f).stdout
    r = run("rulings", "--revisit", "--file", f)
    assert "Flanking" in r.stdout and "shove" not in r.stdout and "1 of 2" in r.stdout
    assert "shove" in run("rulings", "--find", "SHOVE", "--file", f).stdout
    assert len(json.loads(f.read_bytes())) == 2


def test_attendance_roles(tmp_path):
    f = jw(tmp_path, "r.json", ["Ana", "Bo", "Cy"])
    r = run("attendance", f, "--present", "3", "--roles")
    assert "rules marshal (initiative order, conditions, encumbrance): Ana" in r.stdout
    assert "GM (more jobs than players)" in r.stdout
    r = run("attendance", f, "--present", "3", "--roles", "--session", "2")
    assert "encumbrance): Bo" in r.stdout


def test_check_open_choices(tmp_path):
    c = {"name": "Vex", "feats": ["Power Attack", "decide later"], "background": "TBD", "skills": {"stealth": 3}}
    r = run("check", jw(tmp_path, "c.json", c), "--open-choices")
    assert r.returncode == 0
    assert "feats[1]" in r.stdout and "background" in r.stdout and "2 open choice" in r.stdout
    assert "0 open choice" in run("check", jw(tmp_path, "d.json", {"name": "Ok"}), "--open-choices").stdout


def test_dice_norms(tmp_path):
    rules = [{"rule": "crit fumbles", "kind": "remove", "why": "slow", "offset": "none needed"}]
    assert "no dice_norms" in run("houserules", jw(tmp_path, "h.json", rules)).stdout
    r = run("houserules", jw(tmp_path, "h2.json", {"rules": rules, "dice_norms": {"in_view": "tray", "cocked": "reroll"}}))
    assert "dice_norms: no ambiguous" in r.stdout and "no dice_norms (" not in r.stdout
    s = {"cut_call": "stop", "brake_call": "slow", "debrief_minutes": 15, "dice_norms": {"in_view": "yes"}}
    assert "dice_norms: no cocked" in run("safety", jw(tmp_path, "s.json", s)).stdout


def test_rumors_venue():
    r = run("rumors", "--venue", "tavern", "--hours", "2", "--seed", "1")
    assert r.returncode == 0 and "expect 6 in 2 h" in r.stdout and "hour 2" in r.stdout
    r = run("rumors", "--venue", "eatery", "--hours", "4", "--seed", "1")
    assert "about 0.5 an hour, expect 2 in 4 h" in r.stdout


def test_talk_rapport():
    r = run("talk", "--rapport", "--acts", "coin,favour,secret")
    assert "rapport: confidant; use negotiate --start helpful" in r.stdout
    r = run("talk", "--rapport", "--acts", "stand")
    assert "skips a step" in r.stdout and "rapport: stranger" in r.stdout
    assert run("talk", "--rapport", "--acts", "flattery").returncode == 2


def test_district_patrol_style(tmp_path):
    base = {"watch": "strong", "bribe": 5, "curfew": "none", "owner": "guild", "gate": "open"}
    ds = [dict(base, name="A"), dict(base, name="B", patrol_style="biased"), dict(base, name="C", patrol_style="lazy")]
    r = run("district", jw(tmp_path, "d.json", ds))
    assert "A: watch with no patrol_style" in r.stdout and "B: " not in r.stdout.replace("[B]", "")
    assert "C: patrol_style 'lazy'" in r.stdout


def test_npcs_official(tmp_path):
    card = ("## NPCs\n"
            "- Reeve Hal: ink-stained; stamping forms; wants a cut because the post pays badly; kind: official\n"
            "- Clerk Ona: neat; counting coins; wants quiet because she hides debts; kind: official; "
            "controls: market permits; skim: a copper a stall\n")
    r = run("npcs", jw(tmp_path, "n.md", card))
    assert r.returncode == 0
    assert "Reeve Hal: official with no controls" in r.stdout and "Reeve Hal: official with no skim" in r.stdout
    assert "Clerk Ona: official" not in r.stdout


def test_settlement_courts(tmp_path):
    c = {"size": "small city", "population": 8000, "civic": [], "justice": [{"offence": "theft", "sentence": "fine"}]}
    assert "justice but no courts" in run("settlement", jw(tmp_path, "c.json", c), "--justice").stdout
    c["courts"] = [{"case": "debt", "judge": "the Moneyer", "speed": "slow", "predictability": "bought",
                    "tip": "bring a gift"}, {"case": "murder", "judge": "the Duke", "speed": "fast"}]
    r = run("settlement", jw(tmp_path, "c.json", c), "--justice")
    assert "court debt: the Moneyer | slow | bought | tip: bring a gift" in r.stdout
    assert "court murder: no tip" in r.stdout and "speed 'fast'" in r.stdout and "justice but no courts" not in r.stdout
