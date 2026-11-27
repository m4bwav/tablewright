import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return f


def test_encounter_card(tmp_path):
    encs = [{"name": "Ambush", "type": "combat", "function": ["hook"], "point": "intermediate", "random": True},
            {"name": "Riddle", "type": "puzzle", "point": "turning"},
            {"name": "Duke", "type": "roleplay", "function": "prospect", "point": "endpoint", "arc": "court"}]
    r = run("encounter", "--card", jw(tmp_path, "e.json", encs))
    assert r.returncode == 0, r.stderr
    assert "Ambush: a random fight tagged hook with nothing that outlives it" in r.stdout
    assert "Riddle: no function" in r.stdout and "arc main: no endpoint" in r.stdout
    assert "arc court" not in r.stdout
    r = run("encounter", "--card", jw(tmp_path, "e2.json", [{"name": "X", "type": "chase", "point": "end"}]))
    assert r.returncode == 1 and "type 'chase'" in r.stdout
    assert run("encounter", "--system", "pf2e").returncode == 2


def test_npcs_roles(tmp_path):
    card = jw(tmp_path, "n.md", "## NPCs\n"
              "- Ama: tall; counting; wants a map because debt; role: patron; activates: the PCs reach town\n"
              "- Bor: short; sweeping; knows a door because bored; role: hinderer; activates: a theft; central: yes\n"
              "- Cid: thin; reading; hides a key because fear\n")
    r = run("npcs", card, "--roles")
    assert r.returncode == 0, r.stdout
    assert "Ama:" not in r.stdout and "Cid: no role:" in r.stdout
    assert "Bor: hinderer with no tell:" in r.stdout and "Bor: central: yes" in r.stdout


def test_triggers(tmp_path):
    ts = [{"if": "the bell rings", "then": "guards lock the gate", "bound": True, "visible": "gate slams"},
          {"if": "the duke dies", "then": "the heir hires killers", "bound": False, "offstage": True}]
    r = run("triggers", jw(tmp_path, "t.json", ts))
    assert r.returncode == 0
    assert "trigger 2: THEN has no visible result for the PCs (offstage)" in r.stdout
    assert "1 bound, 1 unbound" in r.stdout and "[offstage]" in r.stdout
    assert run("triggers", jw(tmp_path, "t2.json", [{"if": "x", "then": "y"}])).returncode == 1


def test_rumors_spread():
    r = run("rumors", "--spread", "6", "--edge", "20")
    assert r.returncode == 0
    assert "district edge (6 blocks): 6 hours" in r.stdout and "city edge (20 blocks): 20 hours" in r.stdout
    assert "3 hours" in run("rumors", "--spread", "6", "--rate", "2").stdout
    assert run("rumors").returncode == 2


def test_rumors_truth(tmp_path):
    d = {"quests": ["a"], "rumors": [{"quest": "a", "true": "yes"}, {"quest": "a", "true": "yes"},
                                     {"quest": "a", "true": "no"}, {"quest": "a", "true": "later"}]}
    r = run("rumors", jw(tmp_path, "r.json", d), "--truth")
    assert "2 of 4 rumours are true, over 25%" in r.stdout and "no partial rumours" in r.stdout
    d["rumors"][1]["true"] = "partial"
    r = run("rumors", jw(tmp_path, "r.json", d), "--truth", "--max-true", "0.3")
    assert "are true" not in r.stdout and "no partial" not in r.stdout and r.returncode == 0


def city(**kw):
    return dict({"size": "small city", "population": 8000, "civic": []}, **kw)


def test_settlement_news(tmp_path):
    r = run("settlement", jw(tmp_path, "c.json", city(news=["notice board"], law=["watch captain"])), "--news")
    assert "small city with no crier" in r.stdout and "small city with no constable" in r.stdout
    assert "1 news channels, a small city wants 3+" in r.stdout
    r = run("settlement", jw(tmp_path, "c.json", city(news=["town crier", "board", "inn"],
                                                      law=["constable", "watch", "bailiff"])), "--news")
    assert "no crier" not in r.stdout
    assert "no constable" not in r.stdout and "news channels, a" not in r.stdout


def test_settlement_temples(tmp_path):
    t = [{"name": "Dawn", "kind": "cathedral", "faithful": 300}, {"name": "Well", "kind": "shrine", "faithful": 40}]
    r = run("settlement", jw(tmp_path, "c.json", city(temples=t)), "--temples")
    assert "temple Dawn: a cathedral with 300 faithful; that fits a chapel" in r.stdout
    assert "Well: a shrine" not in r.stdout
    r = run("settlement", jw(tmp_path, "c.json", city(temples=[{"name": "Big", "faithful": 9000}])), "--temples")
    assert "9000 faithful across temples, more than the population 8000" in r.stdout


def test_settlement_justice(tmp_path):
    r = run("settlement", jw(tmp_path, "c.json", city(law=["constable"])), "--justice")
    assert "guards but no justice" in r.stdout
    j = [{"offence": "theft", "sentence": "stocks, 1 day"}, {"offence": "arson"}]
    r = run("settlement", jw(tmp_path, "c.json", city(law=["constable"], justice=j)), "--justice")
    assert "offence arson: no sentence" in r.stdout and "theft: stocks, 1 day" in r.stdout
    assert "guards but no justice" not in r.stdout


def site(**kw):
    return dict({"location": "hill", "entries": ["gate", "cave"], "upkeep": "x", "ecology": "x", "visitors": "x"}, **kw)


def test_site_stronghold(tmp_path):
    d = site(stronghold={"purpose": "defensive", "builder": "a retired adventurer", "age": 300, "condition": "pristine"},
             areas=[{"name": "1", "kind": "guard post"}])
    r = run("site", jw(tmp_path, "s.json", d), "--stronghold")
    assert r.returncode == 0
    assert "retired adventurer with no traps" in r.stdout and "defensive site with no armory area" in r.stdout
    assert "pristine at 300 years" in r.stdout
    r = run("site", jw(tmp_path, "s.json", site(stronghold={"condition": "shiny"}, traps=["pit"])), "--stronghold")
    assert "condition 'shiny'" in r.stdout and "stronghold: no builder" in r.stdout


def test_site_access(tmp_path):
    halls = [{"name": "Vault", "door": "open"}, {"name": "Gate", "door": "open", "test": "password"},
             {"name": "Yard", "door": "open", "access": "public"}]
    r = run("site", jw(tmp_path, "s.json", site(halls=halls)), "--access", "controlled")
    assert "controlled access with no test_at" in r.stdout
    assert "hall Vault: controlled with an open door and no entry test" in r.stdout
    assert "hall Gate" not in r.stdout and "hall Yard" not in r.stdout
    r = run("site", jw(tmp_path, "s.json", site(halls=halls, test_at="the gatehouse")), "--access", "controlled")
    assert "tested at the gatehouse" in r.stdout and "no test_at" not in r.stdout


def test_guild(tmp_path):
    q = {"ranks": ["copper", "silver"], "quests": [
        {"title": "Rats", "location": "mill", "distance": "1 mile", "contact": "the miller", "proof": "trophy",
         "no_proof": "half pay", "voucher_by": "clerk", "posted_by": "miller", "rank": "copper"},
        {"title": "Wolf", "location": "wood", "contact": "a hunter", "proof": "tail", "voucher_by": "reeve",
         "posted_by": "reeve", "rank": "gold"}]}
    r = run("guild", jw(tmp_path, "g.json", q))
    assert r.returncode == 1
    assert "Rats" not in r.stdout
    assert "Wolf: no distance" in r.stdout and "Wolf: proof 'tail'" in r.stdout
    assert "Wolf: no no_proof" in r.stdout and "voucher paid by reeve, who posted it" in r.stdout
    assert "rank 'gold' is not in ranks" in r.stdout


def test_rooms_shift(tmp_path):
    base = {"timer": "x", "threat": "x", "treat": "x", "stake": "x", "wonder": "x"}
    rooms = [dict(base, name="Hall", day="clerks", night="two guards"),
             dict(base, name="Stair", day="porter", stairs_rank="silver"),
             dict(base, name="Vault", day="x", night="y", stairs_rank="gold", guard="golem")]
    r = run("rooms", jw(tmp_path, "r.json", {"rooms": rooms}), "--shift")
    assert "Stair: only a day shift" in r.stdout and "Stair: stairs gated to rank silver with no guard" in r.stdout
    assert "Hall: only" not in r.stdout and "Vault: stairs" not in r.stdout
