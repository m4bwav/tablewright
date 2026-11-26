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


def test_fiveroom_ok():
    r = run("fiveroom", FX / "fiveroom_ok.json")
    assert r.returncode == 0 and "warn" not in r.stdout


def test_fiveroom_flags_gaps():
    r = run("fiveroom", FX / "fiveroom_bad.json")
    assert r.returncode == 1
    for s in ("out of order", "at least 2 solutions", "costs nothing", "needs a lever", "same mode"):
        assert s in r.stdout, s


def test_world_ok():
    r = run("world", FX / "world_ok.md")
    assert r.returncode == 0 and "6 traits" in r.stdout


def test_world_flags_gaps():
    r = run("world", FX / "world_bad.md")
    assert r.returncode == 1 and "want 6 to 8" in r.stdout and "not tied" in r.stdout


def test_tracker_public_hides_hp(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "Ogre:12:30", "Ana:15:20", "--file", f)
    run("tracker", "hit", "Ogre", "7", "--file", f)
    r = run("tracker", "show", "--public", "--file", f)
    assert "took 7" in r.stdout and "23/30" not in r.stdout and "/20" not in r.stdout


def test_combat_log_flags_slow_player():
    r = run("combat-log", FX / "combat_log.csv")
    assert r.returncode == 0 and "over 90s a turn: Bo" in r.stdout and "GM share 22%" in r.stdout


def test_tracker_shows_on_deck(tmp_path):
    f = tmp_path / "t.json"
    run("tracker", "init", "A:20:5", "B:15:5", "C:10:5", "--file", f)
    run("tracker", "hit", "B", "9", "--file", f)
    lines = run("tracker", "show", "--file", f).stdout.splitlines()
    assert lines[1].startswith(">") and lines[3].startswith("+")


def test_threads_latest_first_and_finale():
    r = run("threads", FX / "threads.md")
    assert r.returncode == 0 and "1 paid, 2 open" in r.stdout and "the bell tower fire; the stranger" in r.stdout
    assert run("threads", FX / "threads.md", "--finale").returncode == 1


def test_npc_cards():
    r = run("npcs", FX / "npcs.md")
    assert r.returncode == 1 and "Tov: want three parts" in r.stdout and "Ilse: hook has no why" in r.stdout and "Mera" not in r.stdout


def test_encounter_mission_warnings():
    _, d = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--mission", "kill", "--healers", "1")
    assert any("kill-only" in w for w in d["warnings"]) and any("heal" in w for w in d["warnings"])
    _, d = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--mission", "rescue")
    assert any("no clock" in w for w in d["warnings"])
    _, d = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--mission", "hold", "--clock", "8")
    assert any("1 to 5" in w for w in d["warnings"])
    _, d = enc("--system", "pf2e", "--level", "3", "--foe", "3", "--mission", "hold", "--clock", "4")
    assert d["warnings"] == []


def test_fiveroom_warns_when_hard_fights_exceed_budget():
    r = run("fiveroom", FX / "fiveroom_heavy.json")
    assert r.returncode == 0 and "over one fight's budget" in r.stdout


def test_table_flags_gaps_and_speed_bumps():
    r = run("table", FX / "table_bad.csv")
    assert r.returncode == 1 and "[11]" in r.stdout and "cannot avoid" in r.stdout and "fights fill" in r.stdout
    r = run("table", FX / "table_ok.csv")
    assert r.returncode == 0 and "d12" in r.stdout


def test_item_drawback_tiers():
    r = run("item", FX / "items.json")
    assert r.returncode == 1 and "Lantern" in r.stdout and "Thorn Ring: no drawback" in r.stdout and "warn: Crown" in r.stdout


def test_world_nation_society_city_cards():
    r = run("world", FX / "world_nations.md")
    assert r.returncode == 1 and "nation missing internal" in r.stdout and "city missing twist" in r.stdout
    assert "society" not in r.stdout


def test_prep_hazard_needs_warning():
    r = run("prep", FX / "prep_hazard.md")
    assert r.returncode == 1 and "gas pocket" in r.stdout and "rotten pier" not in r.stdout


def test_fiveroom_puzzle_fields(tmp_path):
    plan = json.loads((FX / "fiveroom_ok.json").read_text(encoding="utf-8"))
    plan["party"] = 3
    for x in plan["areas"]:
        if x["role"] == "puzzle":
            x.update(lock_in=True, min_players=5)
            x.pop("fail_cost", None)
    f = tmp_path / "p.json"
    f.write_text(json.dumps(plan), encoding="utf-8")
    r = run("fiveroom", f)
    assert r.returncode == 1 and "no reset" in r.stdout and "needs 5 players" in r.stdout and "fail_cost" in r.stdout


def test_prep_tells_and_false_leads():
    r = run("prep", FX / "prep_tricks.md")
    assert r.returncode == 1 and "lethal and hidden" in r.stdout and "no tell" in r.stdout
    assert "2 false leads of 3" in r.stdout and "the mill (false)" in r.stdout and "the well" not in r.stdout.split("false lead with no ending")[-1]


def test_villain_cards():
    r = run("villain", FX / "villains.md")
    assert r.returncode == 1 and "old mag: no public:" in r.stdout and "ultimatum" in r.stdout
    assert "salt baron" not in r.stdout


def test_twists():
    r = run("twist", FX / "twists.json")
    assert r.returncode == 1 and "spells" in r.stdout and "one axis" in r.stdout and "positive" in r.stdout


def test_campaign_plan():
    r = run("campaign", FX / "campaign.json")
    assert r.returncode == 1 and "PC Bo" in r.stdout and "Vault: no why:" in r.stdout
    assert "uses Vex, written out in Docks" in r.stdout and "no aftermath" in r.stdout and "payoff" in r.stdout


def test_prep_clock():
    r = run("prep", FX / "prep_clock.md")
    assert r.returncode == 1 and "shown:" in r.stdout and "clock step without a consequence" in r.stdout
