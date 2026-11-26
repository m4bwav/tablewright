import json

from test_tt import run


def jw(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def mw(tmp_path, name, text):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


PRE = [{"name": "Ash", "role": "scout", "questions": ["Who taught you?", "What do you owe the captain?"], "stake": "her brother"},
       {"name": "Bram", "role": "face", "questions": ["Why did you sign on?", "Who wants you dead?"], "stake": "a pardon"}]


def test_oneshot_ok_and_fails(tmp_path):
    ok = jw(tmp_path, "o.json", {"bond": "forced", "plot": "heist", "finish": "escape the vault before the tide", "pregens": PRE})
    r = run("oneshot", ok)
    assert r.returncode == 0 and "warn" not in r.stdout
    bad = jw(tmp_path, "b.json", {"plot": "heist", "finish": "split the treasure",
                                  "pregens": [{"name": "Ash", "role": "scout", "questions": ["one"]},
                                              {"name": "Cy", "role": "scout", "questions": ["a", "b"], "stake": "x"}]})
    r = run("oneshot", bad)
    assert r.returncode == 1 and "no bond" in r.stdout and "Ash: no stake" in r.stdout
    assert "Ash: 1 question" in r.stdout and "share the role scout" in r.stdout and "only a payout" in r.stdout


def test_tpk_causes():
    r = run("tpk", "--cause", "gm-error")
    assert r.returncode == 0 and "refight" in r.stdout and "--keep-pcs" in r.stdout
    assert "captured" in run("tpk", "--cause", "bad-luck", "--keep-pcs").stdout
    assert run("tpk", "--cause", "lesson").returncode == 2
    assert run("tpk", "--cause", "whatever").returncode == 2


def test_alert_track(tmp_path):
    f = tmp_path / "alert.json"
    r = run("alert", "init", "--tiers", "4", "--merge", "3:guards+kennel", "--file", f)
    assert r.returncode == 0 and "alert 0/4: calm" in r.stdout
    assert run("alert", "raise", "--file", f).returncode == 2
    run("alert", "raise", "--why", "guard saw a torch", "--by", "3", "--file", f)
    r = run("alert", "show", "--file", f)
    assert "alert 3/4: mustered" in r.stdout and "merge now: guards + kennel" in r.stdout and "guard saw a torch" in r.stdout
    r = run("alert", "lower", "--why", "a day unseen", "--by", "9", "--file", f)
    assert "alert 0/4" in r.stdout
    assert run("alert", "show", "--file", tmp_path / "none.json").returncode == 2


def test_alert_uses_home(tmp_path, monkeypatch):
    import subprocess, sys
    from test_tt import TT
    env = dict(__import__("os").environ, TABLEWRIGHT_HOME=str(tmp_path))
    subprocess.run([sys.executable, str(TT), "alert", "init"], env=env, capture_output=True)
    assert (tmp_path / "alert.json").exists()


def test_backlog(tmp_path):
    hooks = [{"text": f"hook {i}", "status": "live", "worsens": "x"} for i in range(4)]
    hooks.append({"text": "old map", "status": "live", "worsens": "y", "heard": 5})
    hooks.append({"text": "gone", "status": "dropped"})
    f = jw(tmp_path, "b.json", hooks)
    r = run("backlog", f)
    assert r.returncode == 0 and "5 open hook(s) of 6" in r.stdout
    assert "old map: heard 5" in r.stdout and "no hook is tied" in r.stdout and "want 5 to 15" not in r.stdout
    assert "5 open hooks, want 6 to 15" in run("backlog", f, "--min", "6").stdout
    hooks[0]["tie"] = "pc:Ash"
    hooks[1].pop("worsens")
    f = jw(tmp_path, "c.json", {"hooks": hooks})
    r = run("backlog", f, "--levelup")
    assert "no hook is tied" not in r.stdout and "hook 1: no worsens" in r.stdout and "what changed? worsens: x" in r.stdout
    hooks[2]["status"] = "maybe"
    assert run("backlog", jw(tmp_path, "d.json", hooks)).returncode == 1


PREP = """## Opening
- rain on the docks
## Leads
- a
- b
- c
## NPCs
- Vex: the ledger; opposed: yes; where: docks
## Fights
- smugglers; out: they flee
## Obstacles
- locked sea gate; roll: athletics
- rotten stair; roll: acrobatics; on_fail: alarm wakes the crew
"""


def test_prep_roll_memento_opposed_rest(tmp_path):
    r = run("prep", mw(tmp_path, "p.md", PREP))
    assert r.returncode == 0
    assert "no on_fail" in r.stdout and "rotten stair" not in r.stdout
    assert "no fight leaves a memento" in r.stdout and "opposing NPC found in 1 place" in r.stdout
    assert "## Rest" not in r.stdout
    t = PREP.replace("they flee", "they flee; memento: known-foe").replace("where: docks", "where: docks, chapel")
    t = t.replace("roll: athletics", "roll: athletics; on_fail: time") + "## Rooms\n- 1 hall\n"
    r = run("prep", mw(tmp_path, "q.md", t))
    assert "memento" not in r.stdout and "opposing" not in r.stdout and "on_fail" not in r.stdout
    assert "no ## Rest" in r.stdout
    r = run("prep", mw(tmp_path, "s.md", t + "## Rest\n- where: shrine\n- cost: the alert rises\n"))
    assert "Rest" not in r.stdout


def test_villain_absent_and_where(tmp_path):
    base = "## Mord\n- wants: the crown\n- public: a priest\n- reach: guarded\n- harm: rumours\n- harm: taxes\n- escape: tunnel\n"
    r = run("villain", mw(tmp_path, "v.md", base + "- where: temple\n"))
    assert "no absent:" in r.stdout and "one place only" in r.stdout
    r = run("villain", mw(tmp_path, "w.md", base + "- where: temple, court\n- absent: crowns himself in spring\n"))
    assert "absent" not in r.stdout and "one place" not in r.stdout


def test_campaign_milestones_and_org(tmp_path):
    c = {"pcs": [], "adventures": [], "climax": {"trigger": "t", "level": 10, "session": 20, "signs": []},
         "milestones": [{"kind": "discovery", "session": 5}, {"kind": "reversal", "session": 4}],
         "org": {"minions": ["thug", "cultist"], "sergeants": [{"name": "Kell"}]}}
    r = run("campaign", jw(tmp_path, "c.json", c))
    assert r.returncode == 1 and "reversal (session 4) should come after discovery" in r.stdout
    assert "no change_in_view milestone" in r.stdout and "2 minion types" in r.stdout and "Kell: no plan" in r.stdout
    c["milestones"] = [{"kind": "discovery", "session": 3}, {"kind": "reversal", "session": 8},
                       {"kind": "change_in_view", "session": 21}]
    r = run("campaign", jw(tmp_path, "d.json", c))
    assert "not before the climax" in r.stdout and "should come after" not in r.stdout


def test_review_snapshot(tmp_path):
    a = mw(tmp_path, "a.md", "- recap: we fled\n- ended_mid_fight: yes\n- snapshot: (if mid-fight: positions)\n")
    r = run("review", a)
    assert "no snapshot: line" in r.stdout and "no restart: line" in r.stdout
    b = mw(tmp_path, "b.md", "- recap: we fled\n- ended_mid_fight: yes\n- snapshot: Ash at the door, 4 HP\n- restart: the ogre swings\n")
    assert "no snapshot" not in run("review", b).stdout
    assert "restart:" in run("session-log").stdout


def test_negotiate():
    r = run("negotiate", "--start", "wary", "--goal", "open", "--exchange", "0", "--exchange", "1", "--rolls", "12", "11")
    assert "exchange 1: 2d6 12 +0 = 12: moves up -> neutral" in r.stdout and "goal reached in 2" in r.stdout
    r = run("negotiate", "--start", "wary", "--exchange", "-2", "--rolls", "3")
    assert "talks break off" in r.stdout
    r = run("negotiate", "--exchange", "0", "--rolls", "7")
    assert "holds -> neutral" in r.stdout and "new argument" in r.stdout
    assert run("negotiate", "--start", "angry").returncode == 2


def test_travel_navigation_and_tracking():
    r = run("travel", "--miles", "24", "--terrain", "forest", "--navigate", "3", "--seed", "4")
    assert "day 1: d20" in r.stdout and "vs 15" in r.stdout
    assert r.stdout == run("travel", "--miles", "24", "--terrain", "forest", "--navigate", "3", "--seed", "4").stdout
    assert "no checks" in run("travel", "--miles", "24", "--known", "--navigate", "3").stdout
    r = run("travel", "--miles", "10", "--terrain", "hills", "--track-age", "2", "--rain")
    assert "tracking: target 21" in r.stdout
