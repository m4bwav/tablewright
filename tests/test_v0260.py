import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def card(tmp_path, fights):
    f = tmp_path / "card.md"
    f.write_text("## Opening\nThe bell rings.\n## Leads\n- a\n- b\n- c\n## NPCs\n- Mara: wants the key\n## Fights\n"
                 + "".join(f"- {x}\n" for x in fights), encoding="utf-8")
    return f


def test_prep_rotation_purpose_climax(tmp_path):
    f = card(tmp_path, ["Guards; type: ambush; purpose: obstacle; out: flee",
                        "More guards; type: ambush; purpose: show-villain; out: flee",
                        "Ghosts; type: siege; purpose: warning; out: flee"])
    r = run("prep", f, "--rotation", "--purpose", "--end", "22:30", "--climax-min", "50")
    assert r.returncode == 1, r.stdout
    assert "fights 1 and 2 are both ambush" in r.stdout
    assert "show-villain with no escape" in r.stdout and "warning with no clues" in r.stdout
    assert "start the climax by 21:40" in r.stdout
    f = card(tmp_path, ["Guards; type: ambush; purpose: obstacle; out: flee",
                        "Duke; type: parley; purpose: show-villain; escape: barge; out: flee"])
    r = run("prep", f, "--rotation", "--purpose")
    assert r.returncode == 0, r.stdout


def scenes(*ds, **extra):
    out = [{"name": f"s{i}", "difficulty": d} for i, d in enumerate(ds)]
    for k, v in extra.items():
        out[int(k[1:])].update(v)
    return {"scenes": out}


def test_adventure_pacing(tmp_path):
    r = run("adventure", jw(tmp_path, "a.json", scenes("hard", "easy", "hard", "easy")), "--pacing", "pendulum")
    assert r.returncode == 0 and "warn" not in r.stdout, r.stdout
    r = run("adventure", jw(tmp_path, "b.json", scenes("easy", "moderate", "hard")), "--pacing", "pendulum")
    assert "s2: third step the same way" in r.stdout
    r = run("adventure", jw(tmp_path, "c.json", scenes("easy", "easy", "deadly", "trivial")), "--pacing", "pit")
    assert "drop back down" in r.stdout and "no escape: true" in r.stdout
    r = run("adventure", jw(tmp_path, "d.json", scenes("easy", "easy", "deadly", "hard", s2={"escape": True})),
            "--pacing", "pit")
    assert "warn" not in r.stdout, r.stdout
    d = scenes("moderate", "hard", "easy")
    d["scenes"].append({"name": "camp", "rest": True})
    r = run("adventure", jw(tmp_path, "e.json", d), "--pacing", "vise")
    assert "s2: easier than s1" in r.stdout and "vise with a rest (camp)" in r.stdout
    r = run("adventure", jw(tmp_path, "f.json", scenes("easy", "hard")), "--pacing", "vise")
    assert r.returncode == 1 and "wants 3+" in r.stdout


def test_rest_awake():
    r = run("rest", "--awake", "40")
    assert "16 past the 24 h allowance: 4 Con save(s)" in r.stdout
    assert "save 4 at hour 40: DC 16" in r.stdout and "doze" in r.stdout
    assert "no saves yet" in run("rest", "--awake", "20").stdout
    assert run("rest").returncode != 0


def test_mystery_every_suspect(tmp_path):
    m = {"conclusions": [{"id": "c", "final": True}],
         "clues": [{"points_to": "c"}, {"points_to": "c", "suspect": "Ada"}, {"points_to": "c"}],
         "suspects": [{"name": "Ada", "could_have": "key"}, {"name": "Bo"}, {"name": "Cy", "culprit": True}]}
    r = run("mystery", jw(tmp_path, "m.json", m), "--every-suspect")
    assert "suspect Bo: no could_have" in r.stdout and "suspect Bo: no clue" in r.stdout
    assert "suspect Ada" not in r.stdout


def test_villain_escapes(tmp_path):
    f = tmp_path / "v.md"
    body = "- wants: x\n- public: y\n- reach: z\n- harm: a\n- harm: b\n- absent: c\n"
    f.write_text(f"## Duke\n{body}- escape: teleport ring\n## Witch\n{body}- escape: teleport circle | smoke\n",
                 encoding="utf-8")
    r = run("villain", f, "--escapes")
    assert "witch: escape 'teleport circle' repeats duke's" in r.stdout and "smoke" not in r.stdout


def test_wander_split():
    r = run("wander", "--split", "3/2/2/1")
    assert "one d8:" in r.stdout and "1-3: nothing" in r.stdout and "8: discovery (12%)" in r.stdout
    assert "warn" in run("wander", "--split", "1/5/1/1").stdout
    assert run("wander", "--split", "3/2").returncode != 0


def test_puzzle(tmp_path):
    d = {"puzzles": [
        {"name": "bells", "deadly": True, "parts": [{"name": "a", "at": "hall"}, {"name": "b"}],
         "order_clue_at": "hall", "hints": [{"source": "gm"}, {"source": "gm"}], "needs": ["mallet"],
         "wrong_cost": "moderate", "tries": 4, "critical": True},
        {"name": "door", "warning": "scorch marks", "deadly": True, "hints": [{"source": "npc"}, {}, {}],
         "wrong_cost": "minor", "tries": 3, "critical": True, "reward": "door"}]}
    r = run("puzzle", jw(tmp_path, "p.json", d), "--have", "rope", "--hp", "30", "--stall-after", "2")
    assert r.returncode == 1, r.stdout
    for s in ("bells: deadly with no warning", "part b has no at", "order clue sits with a part",
              "first hints are the GM", "needs mallet", "4 wrong tries at moderate take 36 of 30",
              "no door reward", "door: hint 1 after 2 wrong tries"):
        assert s in r.stdout, s
    assert "door: deadly" not in r.stdout and "door: 3 wrong" not in r.stdout
