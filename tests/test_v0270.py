import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_item_consumable_needs_sink(tmp_path):
    base = {"name": "Salve", "benefit_tier": "minor", "drawback_tier": "minor", "consumable": True}
    r = run("item", jw(tmp_path, "a.json", [base]))
    assert "no made_by" in r.stdout and r.returncode == 0, r.stdout
    r = run("item", jw(tmp_path, "b.json", [dict(base, made_by="herbalist, 1 day and 5 gp")]))
    assert "warn" not in r.stdout, r.stdout
    r = run("item", jw(tmp_path, "c.json", [dict(base, roll="d6 heal")]))
    assert "warn" not in r.stdout, r.stdout


def test_table_band(tmp_path):
    f = tmp_path / "m.csv"
    f.write_text("power,severity\n1,minor\n3,major\n2,moderate\n", encoding="utf-8")
    assert run("table", f, "--band").returncode == 0
    f.write_text("power,severity\n1,2\n2,3\n3,1\n", encoding="utf-8")
    r = run("table", f, "--band")
    assert r.returncode == 1 and "power 3 mishap" in r.stdout, r.stdout


def test_mastery(tmp_path):
    f = tmp_path / "m.json"
    r = run("mastery", f, "--school", "fire", "--mark", "x")
    assert r.returncode == 2 and "--trigger" in r.stderr
    run("mastery", f, "--school", "fire", "--trigger", "risk", "--mark", "burned a bridge")
    r = run("mastery", f, "--school", "fire", "--trigger", "study", "--mark", "read")
    assert r.returncode == 2 and "come from 'risk'" in r.stderr
    for i in range(3):
        r = run("mastery", f, "--school", "fire", "--mark", f"m{i}", "--cost", "5")
    assert "4/4 marks (risk); mastered: half cost, 5 -> 3" in r.stdout, r.stdout
    r = run("mastery", f, "--school", "fire", "--mark", "more")
    assert r.returncode == 2 and "already has 4" in r.stderr
    assert b"\r\n" not in f.read_bytes()


def oneshot(enc):
    return {"bond": "professional", "plot": "heist", "finish": "stop the ritual",
            "pregens": [{"name": "A", "role": "face", "stake": "debt", "questions": ["q1", "q2"]}],
            "encounters": enc}


def test_oneshot_encounters(tmp_path):
    good = [{"name": "door"}, {"name": "vault", "twist": True}, {"name": "boss", "finale": True}]
    r = run("oneshot", jw(tmp_path, "a.json", oneshot(good)))
    assert r.returncode == 0 and "warn" not in r.stdout, r.stdout
    bad = [{"name": "door", "twist": True}, {"name": "boss", "finale": True}, {"name": "a"}, {"name": "b"},
           {"name": "c"}]
    r = run("oneshot", jw(tmp_path, "b.json", oneshot(bad)))
    assert "5 encounter(s)" in r.stdout and "twist in door, the first" in r.stdout
    assert "finale is not the last" in r.stdout


def test_prep_cues(tmp_path):
    f = tmp_path / "card.md"
    f.write_text("## Opening\nRain.\n## Leads\n- a; cue: a scream\n- b; cue: a map\n- c\n## NPCs\n- Mara: the key\n",
                 encoding="utf-8")
    r = run("prep", f, "--cues")
    assert r.returncode == 1 and "2 lead(s) with a cue:, want 3+" in r.stdout, r.stdout
    assert run("prep", f, "--cues", "2").returncode == 0
    assert run("prep", f).returncode == 0


def test_ties(tmp_path):
    party = jw(tmp_path, "p.json", {"pcs": [{"name": "Ana", "ties": ["Bo"], "plot_tie": "heir"},
                                            {"name": "Bo", "ties": ["Ana"]}, {"name": "Cy", "ties": ["Ana"]}]})
    logs = []
    for i, body in enumerate(["tie: Ana-Bo\nplot_tie: Ana\n", "tie: Bo/Ana\ntie: Ana-Zed\n", "", "", ""]):
        f = tmp_path / f"s{i}.md"
        f.write_text(body, encoding="utf-8")
        logs.append(f)
    r = run("ties", party, *logs)
    assert r.returncode == 0, r.stdout
    assert "Ana-Bo: used in 2 of 5" in r.stdout and "Ana-Cy: never used" in r.stdout
    assert "Ana (plot): unused for the last 4" in r.stdout and "tie 'Ana-Zed' is not a bond" in r.stdout
