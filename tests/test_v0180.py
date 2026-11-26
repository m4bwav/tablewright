import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return f


def adv(name, **kw):
    return dict({"name": name, "phase": "1", "why": "x", "opposed_by": "y"}, **kw)


def test_campaign_link_guide(tmp_path):
    r = run("campaign", jw(tmp_path, "c.json", {"adventures": [adv("A"), adv("B")]}))
    assert "B: no link:" in r.stdout and "A: no link" not in r.stdout and "no guide:" in r.stdout
    ok = {"guide": "the hermit", "adventures": [adv("A"), adv("B", link="letter")]}
    assert "warn:" not in run("campaign", jw(tmp_path, "d.json", ok)).stdout


def test_campaign_level_gate(tmp_path):
    plan = {"guide": "g", "party_level": 3, "adventures": [adv("A", level=5)]}
    assert "A: level 5 is 2 above the party" in run("campaign", jw(tmp_path, "c.json", plan)).stdout
    plan["adventures"][0]["warned"] = True
    assert "above the party" not in run("campaign", jw(tmp_path, "d.json", plan)).stdout


def test_campaign_motif(tmp_path):
    plan = {"guide": "g", "motif": "ravens", "adventures": [adv("A", beats=["ravens"]), adv("B", link="l"), adv("C", link="l"),
                                                             adv("D", link="l")]}
    assert "motif 'ravens' is in the beats of 1 of 4" in run("campaign", jw(tmp_path, "c.json", plan)).stdout
    plan["adventures"][1]["beats"] = ["ravens"]
    assert "motif" not in run("campaign", jw(tmp_path, "d.json", plan)).stdout


VIL = "## Vex\n- wants: crown\n- public: priest\n- reach: guarded\n- harm: a\n- harm: b\n- escape: tunnel\n- absent: wins\n"


def test_villain_goal_meet(tmp_path):
    r = run("villain", jw(tmp_path, "v.md", VIL + "- goal: the bell\n- goal: the heir\n- meet: the bell at the fair\n"))
    assert "goal 'the heir' has no meet:" in r.stdout and "'the bell' has no" not in r.stdout
    assert "1 meet: lines before the showdown" in r.stdout
    ok = VIL + "- goal: the bell\n- meet: the bell\n- meet: road\n- meet: inn\n"
    assert "meet" not in run("villain", jw(tmp_path, "w.md", ok)).stdout


MYS = {"conclusions": [{"id": "c"}], "suspects": [{"name": s} for s in "abc"],
       "clues": [{"id": f"k{i}", "points_to": "c"} for i in range(3)]}


def test_mystery_schedule(tmp_path):
    m = dict(MYS, schedule=[{"clue": "k0", "at": 2, "partial": "p"}, {"clue": "k1", "at": 1}, {"clue": "k2", "lead_from": "k9", "partial": "p"}])
    r = run("mystery", jw(tmp_path, "m.json", m))
    assert r.returncode == 1 and "k1: no lead_from" in r.stdout and "k1: no partial" in r.stdout
    assert "at 1 comes before" in r.stdout and "'k9' is not a known clue" in r.stdout
    m["schedule"] = [{"clue": "k0", "at": 1, "partial": "p"}, {"clue": "k1", "at": 2, "lead_from": "k2", "partial": "p"},
                     {"clue": "k2", "at": 3, "lead_from": "k0", "partial": "p"}]
    r = run("mystery", jw(tmp_path, "n.json", m))
    assert r.returncode == 0 and "'k2' is not an earlier clue" in r.stdout


def test_groupcheck():
    assert "more than half" in run("groupcheck", "--party", "4", "--successes", "3").stdout
    r = run("groupcheck", "--party", "4", "--successes", "1")
    assert "some" in r.stdout and "3 failing" in r.stdout
    assert "back foot" in run("groupcheck", "--successes", "0").stdout
    assert run("groupcheck", "--party", "3", "--successes", "5").returncode == 2
    a = run("groupcheck", "--roll", "--dc", "12", "--bonus", "2,5", "--seed", "4").stdout
    assert a == run("groupcheck", "--roll", "--dc", "12", "--bonus", "2,5", "--seed", "4").stdout and a.count("PC ") == 4
    assert run("groupcheck", "--roll").returncode == 2


def test_threshold():
    assert "threshold: 28 damage" in run("threshold", "--party", "4", "--apl", "3").stdout
    r = run("threshold", "--party", "4", "--apl", "3", "--shield", "2")
    assert "threshold: 39 damage" in r.stdout and "guide only" in r.stdout
    assert run("threshold", "--apl", "0").returncode == 2


def test_convert(tmp_path):
    r = run("convert", jw(tmp_path, "c.json", [{"name": "x"}]))
    assert r.returncode == 1 and "no treat_as" in r.stdout and "no cr" in r.stdout
    ents = [{"name": n, "treat_as": "goblin", "cr": "1/4"} for n in ("kobold", "orc", "gnoll")] + [
        {"name": "ogre", "treat_as": "ogre", "cr": 6}, {"name": "dragon", "treat_as": "drake", "cr": 8, "boss": True}]
    r = run("convert", jw(tmp_path, "d.json", ents), "--levels", "1-3")
    assert r.returncode == 0 and "3 foes use goblin" in r.stdout and "ogre: CR 6 is over level 3" in r.stdout
    assert "dragon: CR" not in r.stdout and "goblin: 3 stand-in(s), CR 1/4 50 XP" in r.stdout
    for e in ents[:2]:
        e["tweaks"] = "spear"
    assert "use goblin" not in run("convert", jw(tmp_path, "e.json", ents)).stdout


def test_table_side(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("roll,kind,side\n1-3,fight,party\n4-6,omen,party\n", encoding="utf-8")
    assert "never trouble the dungeon's own dwellers" in run("table", f).stdout
    f.write_text("roll,kind,side\n1-3,fight,party\n4-6,omen,both\n", encoding="utf-8")
    assert "dwellers" not in run("table", f).stdout
    f.write_text("roll,kind,side\n1-6,omen,them\n", encoding="utf-8")
    assert "side values ['them']" in run("table", f).stdout


def test_npcs_roles_tell_revealed(tmp_path):
    card = jw(tmp_path, "n.md", "## NPCs\n- Bram: tall; mending nets; wants help because his boat sank; secret: smuggler; "
                                "major: yes; flaw: greedy; roles: fence\n- Cora: old; sweeping; hates rats because they bit her; "
                                "secret: a witch; tell: herb smell; revealed: the town turns\n")
    r = run("npcs", card)
    assert "Bram: secret with no tell:" in r.stdout and "Bram: secret with no revealed:" in r.stdout
    assert "Bram: major NPC with 1 roles:" in r.stdout and "Cora:" not in r.stdout


DEV = {"origin": "o", "why_now": "w", "if_ignored": "i",
       "variants": [{"tier": 1, "encounters": [{"name": "e", "warning": "w", "bystanders": "b"}], "rewards": [{"name": "r", "where": "x"}]},
                    {"tier": 2, "encounters": [{"name": "e", "warning": "w", "bystanders": "b"}], "rewards": [{"name": "r", "from": "y"}]}]}


def test_develop(tmp_path):
    assert "warn:" not in run("develop", jw(tmp_path, "ok.json", DEV)).stdout
    r = run("develop", jw(tmp_path, "a.json", {"variants": [{"tier": 1}]}))
    assert r.returncode == 1 and "no origin" in r.stdout and "no why_now" in r.stdout and "no if_ignored" in r.stdout
    assert "1 variant(s)" in r.stdout and "tier 1: no encounters" in r.stdout and "tier 1: no rewards" in r.stdout
    bad = dict(DEV, variants=[{"tier": 1, "encounters": [{"name": "e"}], "rewards": [{"name": "r"}]}] * 2)
    r = run("develop", jw(tmp_path, "b.json", bad))
    for s in ("tier 1 used twice", "e: no warning", "e: no bystanders", "reward r: neither where nor from"):
        assert s in r.stdout


REALM = {"ruler": {"name": "Q", "chosen_by": "council", "goal": "peace"}, "relations": [{"name": "N", "deterrent": "fleet", "posture": "wary"}],
         "entry": "the gate", "places": [{"name": "fen", "controlled": False, "hook": "bandits"}], "culture": {"custom": "bells"}}


def test_realm(tmp_path):
    assert "warn:" not in run("realm", jw(tmp_path, "ok.json", REALM)).stdout
    r = run("realm", jw(tmp_path, "a.json", {"places": [{"name": "p"}]}))
    assert r.returncode == 1 and "no ruler.name" in r.stdout and "no relations" in r.stdout
    for s in ("no ruler.chosen_by", "no ruler.goal", "no entry", "controlled: false", "place p: no hook", "no culture.custom"):
        assert s in r.stdout
    weak = dict(REALM, relations=[{"name": "N"}])
    r = run("realm", jw(tmp_path, "b.json", weak))
    assert r.returncode == 0 and "relation N: no deterrent" in r.stdout and "relation N: no posture" in r.stdout
    assert run("realm", jw(tmp_path, "b.json", weak), "--strict").returncode == 1
