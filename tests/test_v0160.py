import json

from test_tt import run, enc


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_variant(tmp_path):
    ok = jw(tmp_path, "v.json", [{"name": "frost wolf", "base": "wolf", "axis": ["damage_type"], "tell": "rime on the fur",
                                  "keeps": "pack tactics", "role": "skirmisher"}])
    assert run("variant", ok).returncode == 0
    bad = jw(tmp_path, "b.json", [{"name": "x", "axis": ["control", "immunity"]}])
    r = run("variant", bad)
    assert r.returncode == 1 and "no base" in r.stdout and "no counter" in r.stdout and "no tell" in r.stdout
    assert "2 axes changed" in r.stdout


def test_template():
    r = run("template", "--cr", "1/4", "--delta", "2")
    assert r.returncode == 0 and "CR 1 (200 XP)" in r.stdout
    assert "CR 1/2 (100 XP)" in run("template", "--cr", "1/4", "--scale", "1.5").stdout
    assert "CR 5 (1800 XP)" in run("template", "--cr", "3", "--scale", "1.5").stdout
    assert run("template", "--cr", "1/8", "--delta", "-3").returncode == 1
    assert "2 templates stacked" in run("template", "--cr", "2", "--delta", "1", "--template", "a", "--template", "b").stdout
    assert run("template", "--cr", "2").returncode == 2


def test_poison_lint(tmp_path):
    ok = jw(tmp_path, "p.json", [{"name": "nightroot", "delivery": "ingested", "save": "con", "dc": 14, "interval": "1 hour",
                                  "onset": "10 minutes", "stages": ["sick", "weak"], "end": "two saves in a row"}])
    assert run("poison", ok).returncode == 0
    bad = jw(tmp_path, "b.json", [{"name": "x", "dc": 25, "stages": ["a"]}])
    r = run("poison", bad)
    assert r.returncode == 1 and "no delivery" in r.stdout and "outside 10-20" in r.stdout and "no end condition" in r.stdout


def test_tracker_poison_countdown(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Ana:15:20", "Ogre:10:40", "--file", f)
    r = run("tracker", "poison", "Ana", "venom", "queasy,reeling", "1", "--file", f)
    assert "stage 1: queasy" in r.stdout
    run("tracker", "countdown", "collapse", "d2", "--owner", "Ogre", "--file", f)
    r = run("tracker", "next", "--file", f)
    assert "countdown collapse: 1 on the die" in r.stdout
    r = run("tracker", "next", "--file", f)
    assert "venom stage 2: reeling" in r.stdout
    r = run("tracker", "next", "--file", f)
    assert "collapse fires" in r.stdout
    assert "venom ran its course" in run("tracker", "next", "--file", f).stdout
    assert run("tracker", "countdown", "x", "d4", "--file", f).returncode == 2


def test_portal(tmp_path):
    ok = jw(tmp_path, "p.json", [{"name": "arch", "location": "crypt", "destination": "mire", "key": "silver coin",
                                  "direction": "one-way", "timing": "new moon", "strand": "intended"}])
    assert run("portal", ok).returncode == 0
    bad = jw(tmp_path, "b.json", [{"name": "gate", "direction": "intermittent", "location": "a", "destination": "b"}])
    r = run("portal", bad)
    assert r.returncode == 1 and "no key" in r.stdout and "no return route" in r.stdout


def test_short(tmp_path):
    f = jw(tmp_path, "s.json", {"site": "old mill", "tiers": [{"level": 1, "foes": ["1/4", "1/4"], "cache": 50},
                                                             {"level": 5, "foes": ["2", "2"], "cache": 40}]})
    r = run("short", f)
    assert r.returncode == 0 and "level 1: 100 XP" in r.stdout and "does not grow" in r.stdout
    assert run("short", jw(tmp_path, "b.json", {"tiers": [{"level": 1}]})).returncode == 1


def test_trap_full_and_haunt(tmp_path):
    f = jw(tmp_path, "t.json", [{"name": "pit", "trigger": "plate", "detection": "seam", "disable": "wedge", "effect": "fall",
                                 "severity": "setback"},
                                {"name": "weeping bride", "kind": "haunt", "trigger": "enter", "detection": ["chill", "song"],
                                 "disable": "speak her name", "effect": "fear", "severity": "dangerous", "anchor": "veil",
                                 "rearm": "rest", "avoid": "a", "reset": "b", "alarm": "c"}])
    r = run("trap", f, "--full")
    assert r.returncode == 0 and "pit: no avoid, reset, alarm" in r.stdout
    bad = jw(tmp_path, "b.json", [{"name": "h", "kind": "haunt", "trigger": "t", "detection": "d", "disable": "thievery",
                                   "effect": "e", "severity": "setback", "rearm": "often"}])
    r = run("trap", bad)
    assert r.returncode == 1 and "second detection" in r.stdout and "non-thievery" in r.stdout and "anchor" in r.stdout
    assert "rearm 'often'" in r.stdout


def test_vote(tmp_path):
    f = jw(tmp_path, "v.json", [{"name": "guilds", "votes": 3, "support": "for"},
                                {"name": "temple", "votes": 2, "support": "against", "hidden": True},
                                {"name": "nobles", "votes": 2, "support": "undecided"}])
    r = run("vote", f, "--seed", "1", "--odds")
    assert r.returncode == 0 and "temple: 2 vote(s), ?" in r.stdout and "odds:" in r.stdout and "warn" not in r.stdout
    f2 = jw(tmp_path, "w.json", [{"name": "a", "support": "for"}])
    assert "no undecided faction" in run("vote", f2).stdout


def test_chase_grid():
    r = run("chase", "--grid", "12", "--seed", "3")
    assert r.returncode == 0 and "Q" in r.stdout and ("caught" in r.stdout or "escaped" in r.stdout or "ground" in r.stdout)
    assert run("chase", "--grid", "2").returncode == 2


def test_encounter_solo_horde_throng():
    r, d = enc("--system", "5e", "--level", "5", "--foe", "8", "--solo")
    assert sum("solo with no" in w for w in d["warnings"]) == 3
    r, d = enc("--system", "5e", "--level", "5", "--foe", "8", "--solo", "--tactics", "a", "--fallback", "b", "--terrain", "c")
    assert not any("solo" in w for w in d["warnings"])
    r, d = enc("--system", "pf2e", "--level", "3", *sum([["--foe", "-1"] for _ in range(13)], []))
    assert any("waves of about 8" in w for w in d["warnings"])
    r, d = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--throng", "10x2")
    assert d["xp"] == 70 and any("10 weak foes count as one crowd" in n for n in d["notes"])


def test_hoard(tmp_path):
    ok = jw(tmp_path, "h.json", [{"type": "coins"}, {"type": "gems"}, {"type": "magic", "magic": True}])
    assert run("hoard", ok).returncode == 0
    r = run("hoard", jw(tmp_path, "b.json", [{"type": "coins"}, {"type": "coins"}]))
    assert r.returncode == 1 and "no magic" in r.stdout and "2 parcels" in r.stdout


def test_challenge_caps(tmp_path):
    base = {"goal": "g", "successes": 6, "failures": 3, "on_fail": "x", "shown": "y"}
    bad = jw(tmp_path, "b.json", dict(base, skills=[{"name": "a", "kind": "body", "max": 2}, {"name": "b", "kind": "mind", "max": 2},
                                                   {"name": "c", "kind": "social", "assist": True}]))
    r = run("challenge", bad)
    assert r.returncode == 1 and "caps add to 4" in r.stdout
    w = jw(tmp_path, "w.json", dict(base, outcomes={"0": "lost", "3": "hurt"},
                                    skills=[{"name": "a", "kind": "body", "max": 2}, {"name": "b", "kind": "mind"},
                                            {"name": "c", "kind": "social", "requires": "a"}]))
    r = run("challenge", w)
    assert r.returncode == 0 and "b: uncapped" in r.stdout
    g = jw(tmp_path, "g.json", dict(base, outcomes={"9": "x"}, skills=[{"name": "a", "kind": "body", "requires": "zz"},
                                                                      {"name": "b", "kind": "mind"}, {"name": "c", "kind": "x"}]))
    r = run("challenge", g)
    assert r.returncode == 1 and "requires 'zz'" in r.stdout and "outcome at '9'" in r.stdout
