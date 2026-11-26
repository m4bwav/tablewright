import json
import subprocess
import sys
from pathlib import Path

TT = Path(__file__).resolve().parents[1] / "scripts" / "tt.py"
FX = Path(__file__).parent / "fixtures"


def run(*args):
    return subprocess.run([sys.executable, str(TT), *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def enc(*args):
    r = run("encounter", "--json", *args)
    return r, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else None)


def test_pf2e_moderate_four_players():
    r, d = enc("--system", "pf2e", "--level", "3", "--foe", "4", "--foe", "2", "--foe", "2")
    assert d["xp"] == 60 + 30 + 30 and d["threat"] == "severe"


def test_pf2e_party_of_five_adjusts_budget():
    _, d = enc("--system", "sf2e", "--party", "5", "--level", "1", "--foe", "1", "--foe", "1")
    assert d["budgets"]["moderate"] == 100 and d["threat"] == "low"
    assert d["next"] == {"threat": "moderate", "xp_needed": 20}


def test_pf2e_foe_too_high_fails():
    r, d = enc("--system", "pf2e", "--level", "1", "--foe", "6")
    assert r.returncode == 1 and any("do not use" in n for n in d["notes"])


def test_5e_2024_budget():
    _, d = enc("--system", "5e", "--party", "4", "--level", "5", "--foe", "3", "--foe", "3", "--foe", "1/2")
    assert d["budgets"] == {"low": 2000, "moderate": 3000, "high": 4400}
    assert d["xp"] == 1500 and d["threat"] == "below low"


def test_5e_bad_cr():
    assert run("encounter", "--system", "5e", "--level", "1", "--foe", "1/3").returncode == 2


def test_budget_mixes():
    r = run("budget", "--system", "pf2e", "--level", "3", "--threat", "moderate", "--json")
    d = json.loads(r.stdout)
    assert d["xp"] == 80 and "2 x level 3 (80 XP)" in d["mixes"]


def test_tracker_round_flow(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Hero:15:20", "Goblin:12:6", "Boss:18:40", "--file", f)
    d = json.loads(f.read_text())
    assert [c["name"] for c in d["order"]] == ["Boss", "Hero", "Goblin"]
    run("tracker", "hit", "Goblin", "10", "--file", f)
    run("tracker", "next", "--file", f)
    run("tracker", "next", "--file", f)  # skips the downed goblin, wraps to round 2
    d = json.loads(f.read_text())
    assert d["round"] == 2 and d["turn"] == 0
    run("tracker", "cond", "Hero", "frightened 1", "--file", f)
    out = run("tracker", "heal", "Hero", "50", "--file", f).stdout
    assert "20/20" in out and "frightened 1" in out and "DOWN" in out


def test_tracker_bad_spec(tmp_path):
    assert run("tracker", "init", "Hero:x:1", "--file", tmp_path / "t.json").returncode == 2


def test_sheet_and_check(tmp_path):
    assert run("check", FX / "hero.json").returncode == 0
    out = tmp_path / "s.md"
    run("sheet", FX / "hero.json", "--out", out)
    md = out.read_text(encoding="utf-8")
    assert "Level 1 Human Soldier" in md and "| +3 | +2 | +2 | +0 | +1 | -1 |" in md and "Rotolaser" in md


def test_check_reports_missing(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"name": "X", "abilities": {"str": 10}}))
    r = run("check", p)
    assert r.returncode == 1 and "missing level" in r.stdout and "abilities missing dex" in r.stdout


def test_licence():
    assert "ORC" in run("licence").stdout and "CC-BY-4.0" in run("licence").stdout


def test_5e_decimal_cr():
    _, d = enc("--system", "5e", "--level", "1", "--foe", "0.25", "--foe", "0.5")
    assert d["xp"] == 150


def test_prep_card_ok():
    r = run("prep", FX / "prep_ok.md")
    assert r.returncode == 0 and "3 leads" in r.stdout


def test_prep_card_flags_gaps():
    r = run("prep", FX / "prep_bad.md")
    assert r.returncode == 1
    assert "no ## Opening" in r.stdout and "has 1, want 3" in r.stdout
    assert "without a goal" in r.stdout and "warn: fight without" in r.stdout
