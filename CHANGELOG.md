# Changelog

## 0.25.0 (2026-11-26)
- `xp --award-once`: each encounter's XP is paid once (foes share an `encounter` id), tagged by `how` (kill, sneak, trick, parley). `xp --per-rescue X` adds X per `rescues`. Ideas inspired by Depths of Felk Mor, p. 7, and Throne of God, p. 63.
- `rooms --routes`: every entry-to-goal path with its XP and biggest fight; a room's `alarm_to` foes joining another fight warn. `rooms --hooks`: a hook gated by a check needs `later`. Ideas inspired by A Lesson in Scripture, p. 4.
- `rooms --schedule` (activity weights, surprise per result, lethal windows at 1 in 3 or more warn) and `rooms --muffle` (which rooms hear a `noise` room; `muffled` rooms damp it). `wander --from-rooms`: patrol foes leave their room for the wandering table. `adventure --pillars`: scenes per combat, social, explore pillar. `encounter --buff-source OBJ`: the band with and without a breakable object giving foes advantage (x1.5, our number). Ideas inspired by Lost Temple of Forgotten Evil, pp. 4, 24-29.
- `rooms --teleport`: every teleport result must still reach an exit; a node with no `bypass` warns. `boons [--once-per-pc]`: a once-per-character boon taken twice fails; boon XP jumping 2+ levels warns. Ideas inspired by Depths of Felk Mor, pp. 110-111, and Darker Gifts, p. 3.
- `tt.py ritual --level N [--untrained] [--interrupted]`: whether a ritual attempt rolls for misfortune and its severity, our own ladder. `doomtrack --renewal PERIOD --streak K`: recast schedule, save per recast, permanent after K. Ideas inspired by Occult Ritual Magic, pp. 2-3.
- `doomtrack --stages birth:7,growth:90,formed --acts N --accelerant D` and `chase --collapse FEET`: a staged corruption clock and an outrun-the-edge check. Ideas inspired by Echoes of Heaven, p. 150.
- `encounter --scale 3:0,6:1,8:2`, `encounter --wave ... --trigger bloodied` (warns when the mission is not a fight), `tt.py treasure-gap --level L --party-gold G` (par wealth 100 x level squared, our curve), `objective --hold-rounds N [--wipe-counts]`. Ideas inspired by Throne of God, pp. 19, 21, 31, 52.
- `trap --reset`: a trap that `guards` a puzzle needs `reset` and `retry`. Idea inspired by A Lesson in Scripture, p. 4. `site --recorrupt DAYS --minus-per-live N --live V`: revert day per living villain. Idea inspired by Something Wicked, p. 23.
- All numbers are ours; no book text or tables copied. 9 new tests (231 total).

## 0.24.0 (2026-11-26)
- `rooms --keys` gates: room `requires: [a, b]` (multi-key hub gate), dict locks with `clue_in: ROOM` (warns when the clue is not reachable before the lock), `locked_until: EVENT` (warns on an event no room raises, and on `locked: true` with neither key nor event). `rooms --pieces`: `piece_of` items must lie before their puzzle room. Ideas inspired by Dungeons on Demand / EN5IDER: Out for Blood, pp. 5, 18; Silver Linings, pp. 5, 19; If Looks Could Kill, pp. 12, 14, 19; Time & Time Again, p. 11.
- `tt.py objective FILE --gate FLAG:N --kill-list a,b,c`: boss after N flags (unreachable flag rooms warn), any-order kill list revealed on the last kill. Same sources.
- `encounter --protect OBJ:COUNT:HP --attackers N:DMG`: round each object breaks under fixed damage. Idea inspired by That Sinking Feeling, p. 24.
- `encounter --waves`: the fight and its `--wave` entries as one no-rest day against 3 x moderate (our number). Ideas inspired by Eyes on the Prize, p. 23, and Best Served Cold, p. 27.
- `tt.py rest --interrupt T --step S`: hourly d20 interruption odds, target dropping each quiet hour, expected first event. Idea inspired by No Laughing Matter, p. 5.
- `rumors` quest mode `{quests, rumors}`: each rumour needs `quest` and `true: yes|no|later`; unknown quests and quests with no rumour warn. Idea inspired by Holdenshire Act 1, pp. 4-5.
- `chase --stations N [--pursuer B --quarry B]`: hourly opposed d20 track rolls move the lead; exact catch odds and a seeded sample (added as a chase mode, not a new command). Idea inspired by Holdenshire Act 1, pp. 23-25.
- All numbers are ours; no book text copied. 8 new tests (222 total).

## 0.23.0 (2026-11-26)
- `tt.py xp-gap --party N --level L --award X [--each] [--xp a,b]`: per PC, does the adventure's XP reach the next level and by how much (5e advancement from SRD 5.2.1, CC-BY-4.0). Idea from Dungeons on Demand: Eyes on the Prize, pp. 5, 27.
- `rooms`: a `roleplay: true` room with no `fallback` dice check warns. Idea from Dungeons on Demand: No Laughing Matter, p. 32.
- `rooms --keys` foes: `return_to` must be a room and wants a `return_after`; `fall` damage with no `flee_to` warns. Ideas from Best Served Cold, p. 10, and Eyes on the Prize, p. 13.
- All rules are ours; no book text copied. 3 new tests (214 total).

## 0.22.0 (2026-11-26)
- `rooms --keys` with several entrances: every room with `entry: true` is checked, so a key out of reach from any one entrance is flagged (else the first room is the entrance). Idea from Dungeons on Demand: Insidious Experiments, p. 5.
- `rooms --keys` multi-key locks: a lock given as a list needs all its keys; a key reachable only through that lock is flagged. Idea from Dungeons on Demand: Old Habits, pp. 18, 24.
- `rooms --keys` fleeing foes: room `foes: [{name, flee_to, keys}]`; fails a `flee_to` room that does not exist, warns when the foe flees behind a lock its room holds no key for, and when a foe carries a key past that key's lock. Ideas from Lord of Gloomthrone, pp. 15-18, Mischief Makers, p. 12, and Insidious Experiments, pp. 5, 19.
- All rules are ours; no book text copied. 3 new tests (211 total).

## 0.21.0 (2026-11-26)
- `morale --leader-cumulative N [--seed S]`: after the leader falls, flee chance +N% a round; per-round cumulative odds (to 100% or 10 rounds) and a seeded d100 per round naming the round they flee. Idea from DD2 Stealing the Night Away, p. 5.
- `encounter --boss-dpr X --pc-hp a,b,c`: warns when the boss's all-hit damage a round drops the lowest PC from full, and suggests healing or a buffer first. `--pc-hp` now takes a list (the lowest counts). Idea from Dungeons on Demand: Devils in the Details, p. 24.
- `rooms --keys`: rooms may give `locks` and `keys` (and `exits` for reachability from the first room); flags a lock with no key, a key with no lock, a key in the room it unlocks, and a key reachable only through its own lock. Idea from Dungeons on Demand: The Stuff of Nightmares, p. 24.
- All thresholds are ours; no book text copied. 4 new tests (208 total).

## 0.20.0 (2026-11-26)
- `tt.py rumors` (skills and DCs mixed, a free lead, 2+ leads per key fact, 30-70% of leads on key facts). Idea from A Crown for Strahd, p. 2, and WK1 Caves of the Kobold Queen, pp. 5-7.
- `tt.py recurring` (stages per act, rising threat, an escape until the last stage, an end condition). Idea from WK2 Curse of the Kobold Eye.
- `tt.py burst` (round-one expected damage against one target), `tt.py rollout` (disruptive content over 3+ gated sessions) and `item` `breaks_after`. Idea from The Marksman, pp. 2-7.
- `tt.py casefile` (leads with closers, minutes and varied beats against the slot). Idea from CORE 2-1 Tales of Good & Evil.
- `tt.py lore` (knowledge ladder, DCs up by 5, a twist tier) and `tt.py arc` (chapter levels and finale gold). Idea from Shadow of the Flame and Shadowed Eye of Halagar.
- tt.py back to LF line endings.
- All thresholds are ours; no book text or tables copied. 8 new tests (204 total).

## 0.19.0 (2026-11-26)
- `tt.py doomtrack` (spaces with an event and a `shown_by`, `advance_on`, scene `fail_cost` and `cap`, worst-case cost against the track, an `outcomes` finale per mix of solved `paths`), `tt.py hazard` (multi-problem round: counters with cap round, `lowered_by`, deadlines, `order`) and `challenge` `tiers` (graded gains, botch), timed `complications` (`warning`, `removes` with a `stop`) and expected rounds at an average roll. Idea from CORE: A Hole in the World, pp. 7-10, 13, 18-22, 26.
- `chase --legs FILE [--start LEG] [--party N] [--bonus N]`, `alert noise` and `alert waves --since-alarm R --schedule` (COUNTxFOE entries count XP through the encounter wave code), and `rooms` infiltration lint (an `objective` with under 2 `paths`, a `rolls` entry with no `on_fail`). Idea from CORE: Cog in the Wheel, pp. 18-29.
- `tt.py site` (site prep card with an optional `clock` of `turns` and `signs`). Idea from Dungeons on Demand: Dungeon Delves, pp. 4-12.
- `tt.py interrogate` (DC ladder with truth tags), `encounter --exit` (above the top band with no exit warns) and `tt.py carry` (carry-over foes per group, fleers as a return wave). Idea from the Crow's Rest adventure, pp. 10-15.
- `table combine --filter key=value` (blank or `any` cells always match). Idea from a fan booklet of monster tables, p. 3.
- All thresholds are ours; no book text or tables copied. 11 new tests (196 total).

## 0.18.0 (2026-11-26)
- `campaign`: `link` per adventure, a plan `guide`, level gating with `warned`, and `motif` beats; `villain` `goal:`/`meet:` coverage. Idea from a Curse of Strahd guide.
- `mystery` `schedule` (lead_from, partial, ascending times), `tt.py groupcheck` and `tt.py threshold`; hazard rider advice. Idea from A Scream in the Night.
- `tt.py convert` (old-edition foes as 5e stand-ins) and `table` `side` column. Idea from a Keep on the Borderlands conversion.
- `npcs` `roles`, `tell`, `revealed`. Idea from Dungeons on Demand: NPC Codex.
- `tt.py develop` (hook to tiered adventure variants). Idea from Dungeons on Demand: Adventure Awaits.
- `tt.py realm` (kingdom card). Idea from Dungeons on Demand: Crown and Kingdom.
- All thresholds are ours; no book text copied. 12 new tests (185 total).

## 0.17.0 (2026-11-26)
- `settlement`: optional government, defence (patrol, muster, allies), commerce (banned, black_market), lodgings and sights blocks, each with warnings. Idea from Dungeons on Demand: Cities & Towns.
- `tracker poison --save-each --dc N --potency up|down`, poison cards with `potency` and `shelf_life`. Idea from a poisons supplement, pp. 2-4.
- `tt.py handouts` (purpose, in-world sender, recap after 2+ sessions away) and `npcs` `joins_party` needs an `exit`. Idea from Trail of Tyranny.
- `encounter --spike N --pc-hp N` and `challenge` `on_fail_time` and `lead_in` DC shift. Idea from an adventure shorts collection.
- `prep` `## Flow` (start to finish graph, dead ends, single path, rules cheat sheet) and break planning (`hours:`, `## Break` with `goal_check`). Idea from Focal Point, pp. 98-99, 134, 160.
- `tt.py journey` (rolls your own lead tables, simple or complex, risk labels, clash rerolls; `--check` for a lead slate) with a neutral example table, `tt.py trade` (compounding price walk over road hexes, our flatter band, filled-market cut, no markup for common goods) and `travel --oddity`. Idea from the Borderland Provinces Journey Generator; no setting content carried.
- `prep` `## Scenes` (purpose, closing, session purpose and closing, combat victory and failure, rules lookup words), `--weak`, `--strong`, `--review [--short] [--party]`, `npcs` tactics need a flee point, `tt.py cadence`. Idea from Never Unprepared, pp. 53, 58-60, 82-97, 101, 109.
- `tt.py rival` (rival party with a dated timeline and site states) and `tt.py cascade` (disaster opening rows, fates, patrons), plus a SKILL caution on unexplained PC deaths. Idea from Deep Carbon Observatory.
- `tt.py talk` (petitions with leverage and fallbacks), `npcs --but`, `world` principles and locations, `tt.py islands` with `islands move`, `## Learned` in the session log and `review`, NPC `thread: for Name` in prep, and answer moves in SKILL.md. Idea from Unframed.
- All thresholds are ours; no book text or tables copied. 23 new tests (173 total).

## 0.16.0 (2026-11-26)
- `tt.py variant FILE.json`: monster variant cards (base, axis, keeps, tell, counter, role); fails with no base or axis, control or damage over time with no counter, a changed damage type or immunity with no tell; warns on more than one axis. Idea from New Twists on Old Monsters, pp. 2-8.
- `tt.py template --cr CR --delta N | --scale X [--template NAME...]`: steps the 5e CR ladder (1/8, 1/4, 1/2 included) or scales and rounds up, prints the new XP, exits 1 below 0, warns on stacked templates. Idea from the Tome of Templates. CR XP values are the SRD ones already bundled.
- `tt.py poison FILE.json` (delivery, save, interval, onset, stages; warns with no end condition or a DC outside 10-20) and `tracker poison NAME POISON a,b,c [ROUNDS]` (staged ticks, `poison cure`). Idea from a poisons supplement, pp. 2-4.
- `tt.py portal FILE.json` (location, destination, key, direction, timing; one-way or intermittent needs a return unless `strand: intended`) and `tracker countdown NAME dN --owner C` (a die turned down on its owner's turn). Idea from the Manual of the Planes, pp. 16-18 and 65-66.
- `tt.py short FILE.json`: one site at several tiers, XP and threat per tier, warns when the cache does not grow. `trap --full` also wants avoid, reset and alarm. Idea from an adventure shorts collection.
- `tt.py vote FILE.json [--odds]`: council roll call with hidden support, margin added to a d20, odds by simulation, warns with no undecided faction; `chase --grid N` is a progress-track chase. Idea from Trail of Tyranny, pp. 11-13 and 33-35.
- `encounter --solo` warns without `--tactics`, `--fallback`, `--terrain`; `tt.py hoard FILE.json` wants 3-5 parcels, a magic item and 3+ treasure types. Idea from the Draconomicon (chromatic dragons), pp. 47 and 61-62.
- `challenge`: per-skill `max`, `requires` gates, `assist` skills that score no success, `outcomes` by successes reached; fails when the caps cannot reach the target, warns when one uncapped skill can finish alone. `encounter` warns over 12 foes with no `--wave` (waves of about 8 with a breather) and `--throng COUNTxFOE` counts weak foes as one crowd. Trap `kind: haunt` needs a second detection route, a non-thievery disable, an anchor and `rearm` leave|rest|never. Ideas from Open Grave, pp. 26-32.
- All thresholds are ours; no book text or tables copied. 12 new tests (150 total).

## 0.15.0 (2026-11-26)
- `tt.py travel --watches N [--day-odds] [--watch-odds] [--no-fire]`: a day roll with a time slot, one check per night watch, a cold camp adding odds, weather checks every 4 hours, and the chance of at least one night event. Idea from a wilderness encounters supplement (pp. 2-3).
- `tt.py weather FILE.json`: user weather states with a change chance per check, effect flags, and encounters to reroll when `implausible_in` the current state. Same source, p. 3.
- `tt.py table check FILE.csv --dice 2d10` (gaps, overlaps, each row's probability for any dice expression) and `tt.py table lint FILE.json` (each encounter needs hook, truth, a skill-check follow-up and a morale rule). Same source, pp. 2-4.
- `tt.py encounter --count-foe DICExLEVEL`: min, mean and max XP of a dice-range foe count; notes when the max tops the deadliest band. Same source, pp. 4 and 15.
- `tt.py unit` (troop HP to unit points, one damage per hit, flags hit-only-on-20; `--hero` divides hero damage by scale and adds attack sequences), `tt.py command` (activation cost per unit against leadership, division cap), `morale --break N` and `morale --dice 2d6 --bands`, `battle --resolve` (expected hits per round to a one-third break point, then pursuit throws). Ideas from Domains at War: Battles (Autarch), pp. 12-27 and 65.
- `tt.py march`, `tt.py supply` (weekly cost, weighted line against a cap; `--forage levy|loot` with families lost), `tt.py siege`, `tt.py upkeep --weeks N`. Ideas from Domains at War: Campaigns (Autarch), pp. 54-59, 77-86.
- `tt.py forage TERRAIN --table FILE` (check, 1d4 finds, 2d6 rows, common middle, conditions, a rare swap on the tails) and `forage --check`, `tt.py craft`, `tt.py identify`, `tt.py sell`. Ideas from a herbalism and alchemy supplement (pp. 2-5, 11-12). Herb foraging is `forage`; army foraging is `supply --forage`.
- Every cost, table and band comes from the user's JSON or our own defaults; no book tables are copied. 15 new tests (138 total).

## 0.14.0 (2026-11-26)
- `tt.py xp FILE.json`: counts only faced foes that were not overmatched, with outcome killed, surrendered, routed or persuaded; a routed `group` counts once; fails when the `story` award tops the foe XP or 1/10 of any PC's `xp_to_next` (our cap); splits among survivors. Idea from the AD&D 2e Dungeon Master's Guide (TSR), pp. 101-103.
- `tt.py morale --rating N --mod NAME=V --seed S [--roll R]`: 2d10 against the modified rating; over it breaks. No `morale` command existed (0.8.0 only added `encounter --morale`). Idea from the 2e DMG, pp. 154-155.
- `tt.py awards LOGS...`: `award: player | kind | ability | reason | xp`, `milestone: player`, `coins: player N` lines; fails an award with no reason; warns the same ability twice in a session, a player with no milestone in the last 3 logs, more than 5 coins in a session (our cap). Idea from the 2e DMG, pp. 104-105, and ICRPG 2e Core (Runehammer), p. 79.
- `tt.py loot`: an optional `owner` {`intelligent`, `can_use`, `random`} warns when an intelligent owner leaves an item it could use (`can_use` names or `usable`) in its hoard, and when a random unintelligent monster carries a `magic` item. Idea from the 2e DMG, pp. 181-182.
- `tt.py rooms FILE.json`: each room needs timer, threat and treat (the tags prep reads on fights); warns outside 2-4 rooms, on no stake or wonder, on a third enemy room in a row, and on a hard room with damage, disruption and duration (1-6, prep's lever names) all at 1. Idea from ICRPG 2e Core, pp. 84-92.
- `tt.py tracker clock NAME N --unit turn|round` and `tracker clock tick [NAME] [--fail]`: turn clocks tick on each `next`, round clocks at the round wrap, a failed tick takes 2, and a clock at 0 prints "fires". Idea from ICRPG 2e Core, pp. 78 and 85.
- `tt.py session-end --seed S --die 6 --drop 1 --players A,B,C`: rounds left (dropped faces rerolled) and the final turns in seat order. Idea from ICRPG 2e Core, p. 75.
- `tt.py resize --level L --party N --foe LVL[:role]... --to M [--system]`: one foe per PC of difference, adding brutes then soldiers, cutting controllers and skirmishers first; refuses to cut a lone solo; prints XP and band before and after with the existing budget code. Idea from 4e D&D For Dummies (Wiley), pp. 85-87.
- `tt.py target FILE.json --seed N [--smart]`: the PC that marked the monster, then (with `--smart`) the clearest threat, then the easiest reach, then a seeded roll. Idea from 4e D&D For Dummies, pp. 137-138.
- `tt.py prep --hours H [--learning] [--first]`: warns on more fights than 1 an hour (0.75 with `--learning`; our default from 4e grid play); `--first` needs `## Prologue`, `## Intros` and a `bond:` line, and a later session with `--hours` wants `## Recap`. Idea from 4e D&D For Dummies, pp. 35-37 and 84.
- `tt.py playtest FILE.json`: a blind test needs a new group, an observer who answered no questions, a rule section on each question, a debrief with fun, trouble and improvements, and player counts. Idea from the Kobold Guide to Board Game Design (Kobold Press), pp. 89-90 and 118.
- 10 new tests; all caps and rates are ours and unverified.

## 0.13.0 (2026-11-26)
- `tt.py spell cost --tier 1-4 --power 1-4 [--mastered]`: cost is tier times power, capped at 16; mastered halves it (round down, floor 1); out-of-range values exit 2. Idea from ICRPG Magic (Runehammer), pp. 19 and 21.
- `tt.py spell check FILE.json`: homebrew spells (`tier`, `targets`, `range`, `duration`, `school`, `created`) against our own per-tier caps (`SPELL_CAPS` in tt.py), a creation cooldown (tier II a day, III a week, IV 30 days) and a learn cap (tier up to the spells known in that school, 4 at most). Idea from ICRPG Magic, pp. 19 and 23-24.
- `tt.py tracker effect NAME EFFECT ROUNDS`: a countdown effect on a combatant; each new round takes one off and it ends at 0. Idea from ICRPG Magic, p. 26.
- `tt.py rewards FILE.json`: a reward ladder fails when cadence (`cadence_sessions`) does not lengthen tier to tier or a tier has under 3 `triggers`; warns with no `gate`. Idea from ICRPG Worlds (Runehammer), pp. 8, 15 and 17.
- `tt.py vendors VENDORS.csv PRICES.csv [--wage N]`: fails when an item tier has no vendor, a rarer tier sits at an easier reach, or prices drop as tier rises; prints each price as days of wage. Idea from ICRPG Worlds, p. 16.
- `tt.py party [--roles a,b]`: PCs may list `roles`; warns on a PC covering every role and on a role nobody owns. Idea from ICRPG Worlds, p. 14.
- `tt.py table`: a `sub` column (`file.csv:dN`) names a nested table; its row count must equal its die faces. Idea from ICRPG Worlds, p. 68.
- `tt.py campaign`: `travel: unlimited` needs `travel_limit`; warns with no `nemesis` or one not tied to a roster PC. Idea from ICRPG Worlds, p. 66, and Vigilante City (Hit Point Press), p. 31.
- `tt.py villain`: `drive_die: dN` needs exactly N numbered actions (exit 2). Idea from Vigilante City, p. 31.
- `tt.py mob --count N --hp-each H HITS...`: each hit of H or more drops one member; prints members left and whether the mob routs (half or fewer, our number). Idea from Vigilante City, p. 32.
- `tt.py hack --system own|simple|secure --mods ...`: own is automatic, simple a check, secure an attempt; easy mods (wired, familiar, quiet) and hard mods (remote, foreign, combat, jammed) cancel pairwise to easy, normal or hard. Idea from Altered State (Runehammer), p. 38.
- `tt.py settlement card.json`: our own eight size bands (thorp to metropolis) with our population ranges, a civic kit per band and businesses each function needs. Idea from the Kobold Campaign Builder: Cities and Towns (Kobold Press), pp. 7-20.
- `tt.py favor --relation acquaintance|business|friend --risk low|moderate|high --seed N`: a seeded favor roll with our own odds; a low-risk favor is never major. Idea from Cities and Towns, pp. 182-185.
- 13 new tests; all wording, caps, bands and odds are ours and unverified.

## 0.12.0 (2026-11-26)
- `tt.py oneshot card.json`: a one-shot card with `bond` (professional, family, forced), `plot`, `finish` and `pregens` (`role`, 2+ `questions`, `stake`); fails on no bond, no finish, a pregen with no stake or under two questions; warns on shared roles and a finish that is only a payout. Idea from the Kobold Guide to Gamemastering (Kobold Press), pp. 80-82.
- `tt.py tpk --cause gm-error|bad-luck|player-error [--keep-pcs]`: a support script and a remedy per cause (refight or concede; a short, sure recovery group; let it stand or a costly return); refuses "lesson" and "reset". Idea from the Kobold Guide to Gamemastering, pp. 142-144.
- `tt.py prep`: an opposing NPC (`opposed: yes`) with fewer than two `where:` places warns; `villain` cards warn with no `absent:` (what they do if the party never comes) and on a single `where:`. Idea from the Kobold Guide to Gamemastering, pp. 62-63 and 112.
- `tt.py prep`: a bullet with `roll:` (one check gating progress, also in a new `## Obstacles` section) warns with no `on_fail:` of time, alarm, clock, cost or complication. Idea from the Kobold Guide to Roleplaying, p. 25.
- `tt.py alert init|raise|lower|show`: a dungeon alert track in `TABLEWRIGHT_HOME/alert.json` with 2 to 5 tiers, a reason per change, effects per tier and `--merge TIER:a+b` groups that join forces. Idea from the Kobold Guide to Dungeons, pp. 40-41 and 78-79.
- `tt.py prep`: a card with `## Rooms` or `## Dungeon` warns with no `## Rest` (`where:`, `cost:`). Idea from the Kobold Guide to Dungeons, pp. 75-76.
- `tt.py backlog backlog.json [--min 5 --max 15 --retell 3 --levelup]`: open hooks within a band, each with `worsens`, one tied to a PC or past event, retold hooks flagged, a what-changed prompt per hook at level up. Idea from the Kobold Guide to Plots and Campaigns, pp. 15-16.
- `tt.py prep`: fights may carry `memento:` (clue, loss, gain, plea, curse, known-foe); a card where no fight has one warns. Idea from the Kobold Guide to Plots and Campaigns, p. 14.
- `tt.py campaign`: optional `milestones` (discovery, reversal, change_in_view by session) fail out of order or at or after the climax and warn when one is missing; optional `org` warns on under 4 minion types and sergeants with no plan. Idea from the Kobold Guide to Plots and Campaigns, p. 4.
- `session-log` gains `snapshot:` and `restart:`; `review` warns when a log that ended mid-fight lacks either. Idea from the Kobold Guide to Plots and Campaigns, p. 19.
- `tt.py negotiate --start ATT --exchange MOD ...`: a multi-step negotiation, 2d6 per exchange, at most one attitude step each, talks break at hostile. `travel --navigate BONUS --seed N` rolls a getting-lost check per day off a known route; `--track-age DAYS [--rain --group N]` prints a tracking target. Idea from the D&D 5e Dungeon Master's Guide (2014), social interaction and wilderness survival.
- 10 new tests; all wording, steps and numbers are ours and unverified.

## 0.11.0 (2026-11-26)
- `tt.py calendar FILE [--drift 3]`: a world-day ledger per group; prints each group's timeline and warns when split groups drift 3 or more days apart. Idea from the 1979 AD&D Dungeon Masters Guide (time keeping, pp. 37-50).
- `tt.py hirelings FILE [--roll NAME --event E --seed N]`: hireling loyalty from pay against the going rate, treatment and the leader's charisma modifier; lists the events that call for a check (unpaid, abused, sent ahead, bribe, leader down) and rolls one. Idea from the 1979 AD&D Dungeon Masters Guide (pp. 169-170).
- `tt.py district FILE`: city district cards with watch strength, bribe cost, gate and curfew rules and the block's owner; warns on missing fields and prints a one-line card each. Idea from the Lankhmar GM guide (AD&D 2e).
- `tt.py chase [--lead --escape --rounds --table --seed]`: a seeded city pursuit, opposed d6 per round plus a complication from a built-in list or the user's table, ending when caught or escaped. Idea from the Lankhmar GM guide.
- `encounter --foe 3:brute` (or `"3 role:brute"`): foe roles, a role count, and a warning when 4 or more foes all share one role. Idea from the D&D 4e Dungeon Master's Guide.
- `tt.py prep`: fights and hazards may carry `treat:` (an edge the party can find); a fight with `threat:` or `diff:` but no `timer:`/`clock:` and no treat warns. Idea from ICRPG Master Edition (Runehammer), pp. 92-93.
- `tt.py prep`: a fight rated harder than the one before, or a climax, warns when it turns fewer than two of damage, disruption (`hazard:`, `terrain:`) and duration (`timer:`, `clock:`); `levers:` names them outright. Idea from ICRPG Master Edition, pp. 94-95.
- `session-log` gains an `ending:` line (countdown, hook, choice, ran-long); `tt.py review` counts endings by kind and warns when most ran long. Idea from ICRPG Master Edition, p. 82.
- `tt.py houserules`: entries may name a `situation` (or `trigger`) and `distinguishes`; two rules for the same situation that differ with no `distinguishes` warn. Idea from Arbiter of Worlds (Alexander Macris), ch. 13, pp. 81-82.
- `tt.py prep`: fights may carry `stakes: position|assets|character|party`; all rated fights at one level warn, a climax below character warns. Idea from Arbiter of Worlds, ch. 15, pp. 90-91.
- `session-log` gains `ended_mid_fight:` and `recap:` lines; `review` warns on a mid-fight stop and on a log with no recap. Idea from Arbiter of Worlds, ch. 10, pp. 61-62.
- `tt.py attendance ROSTER --present N [--dynamic collective|competitive|individualist]`: warns at half or fewer present and says how to handle absent PCs for the group's dynamic. Idea from Arbiter of Worlds, ch. 12, p. 77.
- `tt.py trap FILE`: each trap needs a trigger, detection, disable method, effect and a severity band (setback, dangerous, deadly); mostly deadly warns. Idea from the D&D 5e Dungeon Master's Guide (2014), ch. 5, pp. 120-122. No DCs or damage numbers included.
- `tt.py downtime FILE`: each activity needs a time cost and a money cost or sink; repeatable ones need an outcomes table; warns on no hook or one that replaces adventuring. Idea from the 5e DMG, ch. 6, pp. 127-132.
- `tt.py npcs`: a card tagged `major: true` also needs `ideal:`, `bond:` and `flaw:` (or `secret:`). Idea from the 5e DMG, ch. 4, pp. 89-91.
- `tt.py item`: an entry with `reward:` (a blessing, title or favour, not an item) needs a `condition` or `expectation`. Idea from the 5e DMG, ch. 7, p. 227.
- `tt.py villain`: optional `escape:` (how the villain avoids capture, planned in advance); warns without one unless `captured_ok: true`. Idea from the D&D 3.5 Dungeon Master's Guide, pp. 103-104.
- `tt.py fiveroom`: an area with `dynamic: yes` warns without `response` (alarm) and `plan` (left alone). Idea from the 3.5 DMG, pp. 46-47.
- `tt.py party`: optional `entry` (happenstance, rescued, remnant, errand); a PC with `joined_mid: true` and no entry warns. Idea from the 3.5 DMG, pp. 129 and 134.
- 18 new tests; all wording, steps and numbers are ours and unverified.

## 0.10.0 (2026-11-26)
- `tt.py safety`: optional `comfort` per player and topic (none, offscreen, limited, full) and `planned` levels; each topic takes the lowest player's level and a planned level above it fails. Idea from the D&D 3.5 Advanced GM guide (Dungeon Master's Guide II era, "Sensitive Subjects"). Empty `takebacks` or `info_flow` warn; idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py battle plan.json [--results]`: a mass battle played as three representative fights, each with a shape and a carry-over for a win, and a five-step result. Idea from the D&D 3.5 Advanced GM guide.
- `tt.py tracker init --timer N` and `tracker late`: a per-turn timer that delays a player who runs out. Idea from the D&D 3.5 Advanced GM guide.
- `session-log` gains `## Highlights` and `## Weak points`; `tt.py review logs` tallies them per player. Idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py prep`: `## Players` with `for:` tags (every player gets a moment) and `likely:` triage tags, from the D&D 3.5 Dungeon Master's Guide; `diff:` tags warn on a session with no easy or no hard fight, from the D&D 4e Dungeon Master's Guide.
- `tt.py houserules rules.json`: every rule needs a why; removals want an offset. Idea from the D&D 3.5 Dungeon Master's Guide.
- `tt.py fiveroom`: a climax may carry `tiers` (minimum, middle, full); warns on fewer than three or a minimum that needs a kill. Idea from the D&D 3.5 Advanced GM guide.
- `tt.py challenge card.json`: a skill challenge (goal, successes before failures, mixed skill kinds, a failure route, a shown score) from the D&D 4e Dungeon Master's Guide, with an optional progress pool, milestones and time limit from the Fallout 2d20 GM toolkit.
- `tt.py travel`: days and fatigue for an overland trip from pace, terrain, hours and route knowledge. Idea from the Fallout 2d20 GM toolkit; multipliers are ours.
- `tt.py table`: optional `when` column (moving, camped, any); all one state warns. Idea from the Fallout 2d20 GM toolkit.
- 10 new tests; all wording, steps and multipliers are ours and unverified.
- Skipped: faction reputation ladder (`heat standing` already covers it), scavenging-site builder (low checkable value), monster-role count per fight (needs a role field on every foe; later), single-path gate check (`mystery` covers most of it), cut scenes with consent, session-log recap line, 2d10 variance note (ludowright's).

## 0.9.0 (2026-11-26)
- `tt.py strength LEVELS --target-level N [--target-size 5]`: average party level (.5 rounds up) and a five-step strength label from headcount and level against the target; fails under 3 or over 7 players. Idea from the Adventurers League DM Guide 2.0.
- `tt.py loot file.json [--seed]`: gold split evenly with the remainder named; permanent items go to the agreed PC, else the interested PC with the fewest permanent items, ties by a seeded roll; consumables do not count. Idea from the Adventurers League DM Guide 2.0.
- `tt.py reaction`: an improvised NPC's first reaction, 2d6 plus `--mod` and `--approach`, in five bands of our own. Ideas from the Lankhmar GM guide (AD&D 2e) and the 1979 AD&D Dungeon Masters Guide.
- `tt.py heat show|crime|standing|cool`: a faction ledger with standing (-3 to +3, each change needs a reason) and heat that rises by 1 plus witnesses per crime, through five escalation steps (quiet, noticed, collector, enforcers, open hunt). Idea from the Lankhmar GM guide.
- `tt.py premise card.json`: core and twist, a hook layer that is not the same premise with the same root, a finish line for pursuit, an agenda per faction for a race, a losable witness or clue for investigation; warns on defend with no faulty intel or choice and an object found incomplete. Idea from the Game Ideas collection (the Big List of RPG Plots).
- `tt.py wander`: a random-encounter clock (`--every` minutes, 1 in `--chance`, `--hours`, `--budget`), `--placed` areas, and `--run` to roll distance, surprise for each side, reaction and whether the party can evade. All numbers are ours and configurable. Idea from the 1979 AD&D Dungeon Masters Guide.
- 7 new tests; wording, bands and thresholds are ours and unverified.
- Skipped: campaign premise-rut check, premise and twist tables for `table combine`, two-plot physical/personal pairing, district cards, henchman hiring, forced march (outside the six asked for).

## 0.8.0 (2026-11-26)
- `encounter`: `--wave ROUND:COUNTxFOE[:removed_by]` reinforcements with their own XP and band, a finite `--pool`, `--prep` steps that remove waves (warns when one removes nothing), `--morale`, and `--smart` foes warn with no `--escape`. Ideas from A Goblin's Tale (DM guide) and the Book of Challenges.
- `encounter --hazard`: identical hazards count barely more than one (each repeat adds a tenth); `prep` warns on repeated hazard names. Idea from the Book of Challenges.
- `table --die N`: warns when rolls do not run 1 to the die's faces; tables without a `kind` column (step tables) now check too. Idea from the Campaign Planner.
- `threads`: `(opened: session N)` tags; open threads older than `--stale` sessions (default 3) warn. Idea from the Campaign Planner.
- `campaign`: optional `events` (trigger and level each) and a `climax` with trigger, level, session and foreshadowing `signs` scheduled before it (`--signs`, default 3). Idea from the Campaign Planner.
- `fiveroom`: optional puzzle `hints` (with a `baseline:` one) and `reward`. Idea from the Book of Challenges.
- `tt.py session-log`: a session log template whose threads feed `threads`. Idea from the Adventurers League DM Guide 4.0 and the Campaign Planner.
- 9 new tests; wording and thresholds are ours and unverified.
- Skipped: AL party-strength overlay and loot split (more than a small item), a separate set-piece command (folded into `encounter --wave`).

## 0.7.0 (2026-11-26)
- `tt.py mystery`: each conclusion needs 2 clues (3 is safe) a typical party can find, 3+ suspects, and an opening scene that does not point only at the culprit. Idea from the Kobold Guide to Game Design (p. 158-162).
- `tt.py safety`: a cut call, a brake call, a debrief of 10+ minutes, content warnings for lines and veils, and every player confirmed (`--party`). Idea from Beyond Role and Play (the Hamlet safety report, Wieslander).
- `item`: optional `cost_axis`, `uses`, `unpredictable`, `bypasses` and `friction`; old files still pass. Idea from the Kobold Guide to Magic (p. 29-36, 59-60, 83-88).
- `tt.py table combine`: roll 2 to 4 checked tables of 6+ rows together, seeded, no repeats while the tables allow. Idea from the AEG Ultimate Toolbox (p. 353).
- 5 new tests; wording and thresholds are ours and unverified.

## 0.6.0 (2026-11-26)
- `tt.py hooks`: city hook decks (shape, district and stakes tags; two choices per plot hook; followups for framed, accused, mistaken and ambush hooks; rumours keep a separate truth; shape and colour mix). Ideas from Johnn Four, 650 City Encounters (p. 2-45) and Goodman Games, GM Gems (p. 8-9).
- `tt.py tavern`: tavern and inn cards by role (map dot, plot point, encounter, adventure), a house special, a map that fits the expected play, two-sided conflicts, hooks that say where to go, stock encounter variety and a hook per PC. Idea from the RoleplayingTips Inns, Taverns, Restaurants Design Guide (p. 13-52, 139-140).
- `tt.py venues`: taverns, restaurants and inns for a population, with `--anomaly` for a story reason. Same guide (p. 40).
- `tt.py party`: PCs tied to two others and to the main plot; every planned reveal has a fallback. Idea from Panshin, The Game Master (p. 21-24, 153-154).
- 4 new tests; wording and thresholds are ours and unverified.

## 0.5.0 (2026-11-26)
- `tt.py villain`: villain cards (want, public face, reach, indirect harms, offers with more than one option). Idea from Johnn Four, 7 Ways to Improve Your GMing (p. 13-14, 20).
- `tt.py twist`: planned twists need a workaround when they remove an ability, spread over axes and include a positive one. Idea from McDonald, Plot Twists (p. 4-8).
- `tt.py campaign`: PC plotlines, adventure phase and reason, written-out NPCs stay out, opposition, aftermath after major adventures, payback payoffs. Idea from Johnn Four, Campaign Creation Guide (p. 59, 93, 122-133).
- `prep`: optional `## Clock` with a consequence per step and a `shown:` line. Idea from Wick, Play Dirty.
- 4 new tests; wording and thresholds are ours and unverified.

## 0.4.0 (2026-11-26)
- `tt.py table`: random encounter table check (roll gaps and overlaps, fight share, unavoidable easy fights). Idea from Nerzugal's Dungeon Master Toolkit (travel tables).
- `tt.py item`: magic items pair each boon with an equal or stronger drawback. Idea from Nerzugal's Dungeon Master Toolkit.
- `encounter --mission --clock --healers`: warnings for kill-only fights, missing or long clocks, and healing foes. Idea from How to Run Fast and Exciting Combats (2.02, 2.10).
- `fiveroom`: puzzle `fail_cost`, `lock_in`/`reset`, `min_players`; climax `immune` without `weakness`; setback plus climax XP over `fight_budget`. Ideas from Nerzugal's Toolkit, Bill Webb's Book of Dirty Tricks and 5 Room Dungeons.
- `prep`: `## Hazards` need a warning; lethal threats need a tell and may not be hidden; false leads fewer than real ones, each with an ending. Ideas from Nerzugal's Toolkit and Bill Webb's Book of Dirty Tricks.
- `world`: optional nation (internal and external conflict), society (leader, goal, rule) and city (theme, food, shelter, shop, twist) cards. Idea from the Kobold Guide to Worldbuilding.
- 7 new tests; wording and thresholds are ours and unverified.

## 0.3.0 (2026-11-26)
- `tt.py world`: setting card check (6 to 8 traits, each anchored to a place, NPC or faction). Idea from Shea, The Lazy Dungeon Master (ch. XIV).
- `tracker --public`: players' board with damage taken and no HP; `+` marks who is on deck. Ideas from The Lazy Dungeon Master and Johnn Four, How to Run Fast and Exciting Combats (3.04).
- `tt.py combat-log`: turn times of a real fight from a CSV, flags players over 90 s a turn. Idea from How to Run Fast and Exciting Combats (1.01).
- `tt.py threads`: open story promises, latest first, `--finale` check. Idea from Walmsley, Play Unsafe (p. 43-47).
- `tt.py npcs`: three-line NPC card check. Idea from Johnn Four, 3 Line NPCs.
- 7 new tests; wording and thresholds are ours.

## 0.2.0 (2026-11-26)
- `tt.py prep`: checks a session prep card (opening, three leads, NPCs with current goals, a way out of each fight) with 2 tests. Idea from Shea, The Lazy Dungeon Master (session prep and combat chapters); the checks and wording are ours.
- `tt.py fiveroom`: checks an adventure plan against the five-role arc (entrance, puzzle, setback, climax, reward) with 2 tests. Idea from Johnn Four, 5 Room Dungeons (method section); thresholds are one GM's advice, unverified.

## 0.1.1 (2026-11-25)
- Licence fixes: encounter budgets credited to Pathfinder and Starfinder GM Core, ORC notice added, SRD 5.2.1 with the exact CC-BY-4.0 attribution.
- Full eval suite results in TESTS.md.

## 0.1.0 (2026-11-25)
- First version: hub skill (encounters, table tracker, characters, minis and maps routing), references for encounter math, the character schema and minis, `tt.py` (encounter, budget, tracker, sheet, check, licence) with 12 tests. An eval found `--foe 0.25` refused; decimal CRs are accepted. Starfinder character and mini pipelines stay in their project; tablewright routes to them as the first system adapter.
