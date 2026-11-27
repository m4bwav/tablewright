import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return f


def test_weather_days():
    r = run("weather", "--days", "30", "--band", "cold,cool,mild", "--seed", "1")
    assert r.returncode == 0, r.stderr
    lines = [l for l in r.stdout.splitlines() if l.startswith("day ")]
    assert len(lines) == 30 and all(l.split(": ")[1].split(" ")[0] in ("cold", "cool", "mild") for l in lines)
    assert "gust peak" in r.stdout and "rest of the day" in r.stdout
    p = run("weather", "--days", "3", "--view", "player", "--seed", "1")
    assert "gust peak" not in p.stdout and "d6" not in p.stdout
    assert run("weather").returncode == 2


def test_weather_edge_push():
    r = run("weather", "--days", "60", "--band", "a,b", "--seed", "5")
    assert "pushed back from the edge" in r.stdout or "off the edge" in r.stdout


def test_travel_navigators():
    r = run("travel", "--miles", "40", "--terrain", "forest", "--navigate", "0", "--navigators", "3", "--seed", "3")
    assert r.returncode == 0, r.stderr
    assert "GM only" in r.stdout and "navigator 3" in r.stdout
    assert "disagree" in r.stdout and ("veered 90" in r.stdout or "reversed" in r.stdout)
    one = run("travel", "--miles", "40", "--terrain", "forest", "--navigate", "0", "--seed", "3")
    assert "navigator 1" not in one.stdout and "d20" in one.stdout


def test_travel_light():
    base = run("travel", "--miles", "48", "--terrain", "road", "--known")
    dark = run("travel", "--miles", "48", "--terrain", "road", "--known", "--light", "dark", "--obscure", "fog")
    assert "24.0 miles a day" in base.stdout and "3.0 miles a day" in dark.stdout
    assert "speed x0.125" in dark.stdout
    push = run("travel", "--miles", "48", "--terrain", "road", "--known", "--light", "moon", "--push")
    assert "24.0 miles a day" in push.stdout and "capped at double" in push.stdout


def test_forage_spoil(tmp_path):
    table = {"terrains": {"forest": {str(k): {"item": f"herb{k}"} for k in range(2, 13)}}}
    t = jw(tmp_path, "f.json", table)
    for seed in range(20):
        r = run("forage", "forest", "--table", t, "--dc", "1", "--spoil", "--seed", seed)
        if "spoil d6" in r.stdout:
            break
    assert "spoil d6" in r.stdout
    assert any(w in r.stdout for w in ("poisonous", "spoiled", "filler", "good"))


def test_rest_sleep_log():
    r = run("rest", "--sleep-log", "5,8,5,3,2,8")
    assert r.returncode == 0, r.stderr
    out = r.stdout.splitlines()
    assert "no effect yet" in out[0] and "no effect yet" in out[2]
    assert "-1 to checks" in out[3] and "-2 to checks" in out[4]
    assert "debt cleared" in out[5] and "sleep debt now -0" in r.stdout


def test_air():
    r = run("air", "--volume", "2000", "--breathers", "rest:2,work:2", "--fires", "1", "--vent", "poor")
    assert r.returncode == 0, r.stderr
    assert "drain 12/turn" in r.stdout and "air out in 20.0 turn" in r.stdout
    assert "head height (5.5 ft) in 9.0 turn" in r.stdout
    assert "air holds" in run("air", "--volume", "500", "--vent", "good").stdout
    assert run("air", "--volume", "500", "--breathers", "nap:2").returncode == 2


def test_collapse(tmp_path):
    cells = {"cells": {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "D"], "D": ["B", "C", "E"], "E": ["D"]}}
    f = jw(tmp_path, "c.json", cells)
    r = run("collapse", f, "--start", "A", "--chance", "100", "--step", "100", "--seed", "1")
    assert r.returncode == 0, r.stderr
    assert "ok: 3 of 5" in r.stdout
    r = run("collapse", f, "--start", "A", "--chance", "100", "--rotten", "--seed", "1")
    assert "ok: 5 of 5" in r.stdout and "rotten" in r.stdout
    bad = jw(tmp_path, "b.json", {"cells": {"A": ["Z"]}})
    assert run("collapse", bad, "--start", "A").returncode == 1
    d = run("collapse", "--daily", "--odds", "1", "--seed", "2")
    assert "collapse" in d.stdout and "reroutes" in d.stdout


def test_site_stronghold_extras(tmp_path):
    s = {"stronghold": {"purpose": "defensive", "interior": "wood", "defence_scale": "army", "hidden": True,
                        "secret_exits": [{"name": "well", "known_to_former": True}],
                        "outposts": [{"name": "tower", "lit": True}], "watch_posts": [{"name": "gate", "watchers": 1}],
                        "traps": [{"name": "pit"}], "value": 10000, "income": ["toll", "farms"],
                        "neighbours": [{"name": "Baron"}]},
         "rooms": [{"name": "Chapel", "kind": "chapel"}, {"name": "Hall", "kind": "hall"}],
         "staff": [{"role": "steward", "level": 3}, {"role": "guard captain", "level": 3}]}
    f = jw(tmp_path, "s.json", s)
    r = run("site", f, "--lint")
    assert r.returncode == 0
    for w in ("no water", "no food", "wooden interior", "sized only for armies", "well is known", "tower cannot signal",
              "gives the hidden site away", "one watcher", "pit has no one"):
        assert w in r.stdout, w
    r = run("site", f, "--upkeep")
    assert "Chapel (chapel) wants a priest" in r.stdout and "clash" in r.stdout
    assert "upkeep 100-300 gp" in r.stdout and "more than one source" in r.stdout
    s["staff"] = [{"role": "cook"}]
    assert run("site", jw(tmp_path, "s2.json", s), "--upkeep").returncode == 1
    t = run("site", f, "--threats", "--seed", "1")
    assert "neighbour Baron:" in t.stdout and "why nobody built here before:" in t.stdout


def test_wander_risk():
    r = run("wander", "--risk", "extreme")
    assert "risk extreme" in r.stdout and "add 4" in r.stdout


def test_travel_road_segment(tmp_path):
    segs = [{"name": "Old Road", "mundane": ["farmers"], "dangerous": ["bandits"]}, {"name": "Pass"}]
    r = run("travel", "--road-segment", jw(tmp_path, "r.json", segs), "--segment-odds", "1/2", "--seed", "1")
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("Old Road") == 3 and r.stdout.count("Pass ") == 3
    assert "-> bandits" in r.stdout or "-> farmers" in r.stdout
    assert "ok: 2 segment(s)" in r.stdout


def test_settlement_purchase(tmp_path):
    for size, pop, cap in (("thorp", 10, "50"), ("village", 500, "200"), ("metropolis", 30000, "6400")):
        r = run("settlement", jw(tmp_path, f"{pop}.json", {"size": size, "population": pop}), "--purchase-limit")
        assert f"{size}: buys up to {cap} gp a month" in r.stdout


def test_realm_changing_times(tmp_path):
    d = {"name": "March", "ruler": {"name": "Ana"}, "changing_times": {"trend": "the old duke weakens", "clock": 6, "filled": 6},
         "jurisdiction": {"roads": "governors", "cities": "mayors"}}
    r = run("realm", jw(tmp_path, "r.json", d), "--changing-times")
    assert r.returncode == 0
    assert "tension clock: 6/6" in r.stdout and "trend lands now" in r.stdout and "no sign" in r.stdout
    assert "template: no capital" in r.stdout and "who answers for courts" in r.stdout
    assert "jurisdiction roads: governors" in r.stdout
    d["changing_times"]["clock"] = 1
    assert run("realm", jw(tmp_path, "r2.json", d), "--changing-times").returncode == 1


def test_encounter_cascade(tmp_path):
    d = {"master": {"wilds": [{"roll": "1-2", "to": "creature"}, {"roll": "3", "to": "weather"}, {"roll": "4", "to": "twice"}],
                    "city": [{"roll": "1", "to": "creature"}]},
         "categories": {"creature": {"forest": ["wolves", "bear"], "desert": "-"}, "weather": {"forest": ["fog"]}}}
    f = jw(tmp_path, "c.json", d)
    seen = ""
    for seed in range(30):
        seen += run("encounter", "--cascade", f, "--terrain", "forest", "--seed", seed).stdout
    assert "check every 4 h; master d4" in seen and "roll twice more on d3" in seen
    assert "wolves" in seen or "bear" in seen
    r = run("encounter", "--cascade", f, "--context", "city", "--terrain", "desert", "--seed", "1")
    assert "every 2 h" in r.stdout and "never in desert" in r.stdout
    d["master"]["wilds"].append({"roll": "5", "to": "ghosts"})
    assert run("encounter", "--cascade", jw(tmp_path, "c2.json", d)).returncode == 1


def test_adventure_seed(tmp_path):
    d = {"question": "who poisoned the well?", "twists": [{"type": "framed"}, {"type": "framed"}, {"type": "backer"}],
         "epilogue": {"text": "The villain escapes to plot again", "twist": "pc_keyed"},
         "patron": {"name": "Mayor"}, "routes": [{"kind": "combat"}]}
    f = jw(tmp_path, "a.json", d)
    r = run("adventure", f, "--twists", "3", "--epilogue", "--hook")
    assert r.returncode == 0, r.stdout
    for w in ("two twists of type framed", "villain escaping", "assumes twist pc_keyed", "no selfish motive",
              "no non-combat route", "no slot tied"):
        assert w in r.stdout, w
    g = run("adventure", jw(tmp_path, "b.json", {}), "--twists", "3", "--seed", "1")
    assert "twists to write" in g.stdout and g.stdout.split("write")[1].count(",") >= 2
    assert run("adventure", jw(tmp_path, "c.json", {"twists": [{"type": "alien"}]}), "--twists", "1").returncode == 1
