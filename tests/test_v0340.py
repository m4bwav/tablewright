import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return f


def test_battle_caster(tmp_path):
    plan = {"caster": {"area_spells": 3, "per_spell": 5},
            "sides": [{"units": []}, {"units": [{"count": 20}, {"count": 10}]}]}
    r = run("battle", jw(tmp_path, "b.json", plan), "--caster")
    assert r.returncode == 0
    assert "removes about 15 foes" in r.stdout and "enemy has 30" in r.stdout
    assert "cannot absorb the caster; suggest 45+" in r.stdout
    r = run("battle", jw(tmp_path, "b2.json", dict(plan, enemy_size=60)), "--caster")
    assert "cannot absorb" not in r.stdout and "ok: enemy 60" in r.stdout


def site(**kw):
    return dict({"location": "hill", "entries": ["gate", "cave"], "upkeep": "x", "ecology": "x", "visitors": "x"}, **kw)


def test_site_food(tmp_path):
    cr = [{"name": "wolf", "diet": "predator", "count": 3}, {"name": "deer", "diet": "prey", "count": 8},
          {"name": "golem", "diet": "guardian"}, {"name": "drake", "diet": "guardian", "hoard_origin": "a sacked shrine"}]
    r = run("site", jw(tmp_path, "s.json", site(creatures=cr)), "--food")
    assert "3 predators need 12 prey (4 each), the site has 8" in r.stdout
    assert "guardian golem: no food source and no hoard_origin" in r.stdout and "drake" not in r.stdout
    r = run("site", jw(tmp_path, "s.json", site(creatures=cr)), "--food", "--prey-per", "2")
    assert "predators need" not in r.stdout


def test_site_purpose(tmp_path):
    areas = [{"name": "1", "kind": "guard post"}, {"name": "2", "kind": "barracks"}]
    r = run("site", jw(tmp_path, "s.json", site(areas=areas)), "--purpose", "defensive")
    assert "defensive site with no armory area" in r.stdout and "no guard area" not in r.stdout
    r = run("site", jw(tmp_path, "s.json", site(areas=areas)), "--purpose", "temple")
    assert "temple site with no shrine area" in r.stdout


def test_site_water(tmp_path):
    d = site(settlements=[{"name": "Ford", "heads": 500, "water": {"source": "the brook", "flow": "spring"}}],
             camps=[{"name": "Raiders", "heads": 30}, {"name": "Mill", "heads": 40, "water": {"source": "x", "flow": "stream"}}])
    r = run("site", jw(tmp_path, "s.json", d), "--water")
    assert "Ford: 500 heads on a spring" in r.stdout and "Raiders: no water source" in r.stdout
    assert "Mill:" not in r.stdout


def test_market_availability():
    r = run("market", "--band", "village", "--availability", "abundant", "--price", "rope=10")
    assert "prices x0.9" in r.stdout and "rope 9 gp" in r.stdout
    r = run("market", "--band", "village", "--availability", "rare", "--price", "lamp=240")
    assert "lamp 264 gp: above" in r.stdout


def test_npcs_recurring(tmp_path):
    card = jw(tmp_path, "n.md", "## NPCs\n"
              "- Vel Arn: tall; counting coins; wants the map because debt; recurring: yes; reacts: Ana=fond | Bo=wary; "
              "danger: hides; questions: lies; survival: pays off foes\n"
              "- Vel Dorr: short; sweeping; knows a door because bored; recurring: yes; reacts: Ana=bored\n")
    r = run("npcs", card, "--recurring", "--pcs", "Ana,Bo")
    assert r.returncode == 0, r.stdout
    assert "Vel Arn:" not in r.stdout
    assert "Vel Dorr: recurring NPC with no danger:" in r.stdout and "Vel Dorr: no reaction to Bo" in r.stdout
    assert "name 'vel' reused" in r.stdout


def test_settlement_farmland(tmp_path):
    c = {"size": "village", "population": 600, "civic": ["authority", "council", "defence", "hall"]}
    f = jw(tmp_path, "c.json", c)
    r = run("settlement", f, "--farmland", "1000")
    assert "population 600 is more than farmland and imports feed (500)" in r.stdout
    r = run("settlement", jw(tmp_path, "c2.json", dict(c, food_imports=200)), "--farmland", "1000")
    assert "is more than" not in r.stdout and "feeds 700" in r.stdout
    assert "is more than" not in run("settlement", f, "--farmland", "1000", "--per-acre", "1").stdout


def realm(**kw):
    return dict({"ruler": {"name": "Ys", "title": "Queen"}, "relations": [{"name": "N"}]}, **kw)


def test_realm_government(tmp_path):
    g = {"type": "monarchy", "titles": [{"title": "Queen", "rank": 1}, {"title": "Duke", "rank": 2},
                                        {"title": "Baron", "rank": 4}]}
    r = run("realm", jw(tmp_path, "r.json", realm(government=g)), "--government")
    assert r.returncode == 1
    assert "gap between rank 2 and 4" in r.stdout and "no government.gained" in r.stdout
    assert "titles: Queen > Duke > Baron" in r.stdout
    g["titles"][2]["rank"] = 3
    g["gained"] = "conquest"
    r = run("realm", jw(tmp_path, "r.json", realm(government=g)), "--government")
    assert r.returncode == 0 and "gap" not in r.stdout


def test_realm_grant(tmp_path):
    gs = [{"land": "Oakmere", "owner": "Ana", "yield": "40 gp a season", "service": "20 spears", "opt_out": "a 500 gp purse"},
          {"land": "Fen", "owner": "Bo", "yield": "eels"}]
    r = run("realm", jw(tmp_path, "r.json", realm(grants=gs)), "--grant")
    assert r.returncode == 1
    assert "grant Oakmere: owner Ana; yields 40 gp a season; owes 20 spears; or a 500 gp purse" in r.stdout
    assert "grant Fen: no service" in r.stdout and "grant Fen: no opt_out" in r.stdout
