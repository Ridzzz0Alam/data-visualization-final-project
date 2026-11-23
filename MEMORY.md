# Project memory — progress log

Read this together with `CLAUDE.md` at the start of every session. Update it at the end of each phase.

## Status (last updated 2026-11-17, all phases built)

| Phase | Status |
|---|---|
| 0 Setup | ✅ Done. Git repo pushed to `git@github.com:Ridzzz0Alam/data-visualization-final-project.git` (`main`) |
| 1 Get data | ✅ Done (`python scripts/fetch_data.py`) |
| 2 Explore raw data | ✅ Done (findings below). Student still to write own "Datasets" bullets in `docs/defense_notes.md` |
| 3a Parser `src/parse_openfootball.py` | ✅ Done: 753 matches, 5 seasons, counts match headers |
| 3b `src/team_names.py` | ✅ Done: 125 spellings → 80 clubs, 28 countries; checks via `python src/team_names.py` |
| 3c `src/prepare.py` (+ `src/elo.py`) | ✅ Done: 7 parquet files in `data/processed/` (see below) |
| 4 Notebook `01_data_preparation.ipynb` | ✅ Done: 10 steps + missing-values table + decision log; executes clean, writes identical Parquet |
| 5 Dashboard skeleton `app/app.py` | ✅ Done (FastListTemplate, 4 filters, Q1–Q4 cards, sources footer) |
| 6a Q1 scatter Elo vs points | ✅ Done: expected line = least-squares fit on all 36 teams; labels = selected + 4 most over/under; always current season |
| 6b Bump chart (Q2 card) | ✅ Done: league seasons only (message for 2021-24), cut-off lines at 8.5/24.5; NB ylim=(0,37)+invert_yaxis (ylim reversed + invert = double flip) |
| 6c Q2 strip plot MD4 position vs furthest round | ✅ Done. 2024-26 only (72 teams); summary line: top-8 75% R16 / 31% SF |
| 6d Q3 heatmap country × season | ✅ Done. Metric toggle (pts/match, mean Elo, win rate, clubs in R16); default rows = 8 countries with ≥50 matches; selected team's cells in red |
| 6e Match explorer (Tabulator) | ✅ Done. Full-width card; follows team selector, 'show all teams' checkbox, header filters per column |
| 6f Linking | ✅ Done. `click_selects_team()` = Selection1D + tap on Q1 scatter and Q2 strip dots → sets team_w → all views update |
| 7 Monte Carlo `src/simulate.py` + Q4 card | ✅ Done. 10k sims, seed 2027, draw rate 16.5% from data, frozen Elo, fixed bracket (seed k v winner of (17-k) v (16+k)); writes `simulation_2026.parquet` — run AFTER prepare.py. Top: PSG 15.9%, Bayern 14.9%, Real 14.0%, Arsenal 13.6% |
| 8 Polish, README, defense notes | ✅ Done. Polish: sidebar 'which filter affects what', readable bump hover, hvPlot charts responsive=True (else fixed 700px), footer cites Elo method + model. README rewritten. defense_notes.md = DRAFT for student to rewrite. |
| 9 Redesign (student feedback: 'looks like the 90s') | ✅ Done. Student chose: dark 'UCL night', tabs (Overview, Contenders, Early form, Countries, Title odds, Head-to-head, Matches), + head-to-head. app/ split into data.py, theme.py, charts.py, app.py. Focus team in header drives all tabs. Palette now cyan #22d3ee focus, gold #fbbf24 2nd team, slate #46527a others. NB width without sizing_mode='fixed' (else Bokeh W-1005). Template: theme_toggle=False (design is dark-only), busy_indicator=None (header spinner flickered) |
| 10 Flat style + chart fixes | ✅ Done. Flat style = commit `4cf1569` ON ITS OWN: to bring back the glossy look run `git revert 4cf1569` (chart fixes are in the next commit and stay). Chart fix lesson: Panel links axes of HoloViews panes sharing a dimension name → never use generic dim names like 'y'. Also: heatmap smooth 256-step palette, toolbar autohide, dark header search box, only focus team labelled in Q1 scatter |
| 11a Top scorers (2026-11-23) | ✅ Commit `eb55c77`. `/scorers?limit=100` → `cl_2026_scorers.json` → `scorers_2026.parquet` (prepare step 10, notebook 9b). Null assists/pens → 0; goal_share vs OUR team goals (both MD1–4). Context only, NOT a model input (double counting, no history). Views: scorer cards + "one-man teams" scatter (Title odds), scorers table (Matches). Bodø/Glimt has no top-100 scorer → not in scatter |
| 11b Animations (2026-11-23) | ✅ Commit `4695d88`, revertible on its own (`git revert 4695d88`). Elo race (Contenders, 163 match dates) + league-phase replay (Early form; replaced range slider + q2_bump). DynamicMap(pn.bind(...)) + pn.widgets.Player → in-place updates. Every frame must have the same layers. Lesson again: hv.Text defaults to x/y dims and 'elo' clashed with Q1 → unique dim names |
| 11c 3D (Plotly) | Proposed, waiting for student OK to add the `plotly` dependency. Idea: Elo × points × title % per team, click → focus team |
| NEXT (later, student's request) | More creative, realistic not glossy. Student may ask to revert 11b if animations aren't good enough |
| Student to do | Screenshot → docs/screenshot.png; rewrite defense_notes in own words; full demo dry-run |

**Processed files** (`python src/prepare.py`): matches (897 = 753 + 144 incl. 72 unplayed), team_matches (long, 1650), elo_history (1650), league_tables (cumulative per matchday, 36-team seasons), season_outcomes (furthest round + reached_* flags, position_md4/final), standings_2026 (+ elo, elo_rank, rank_gap), country_season (Q3).
- Elo: start 1500, K=20, home advantage 50 (not in final), shoot-out = draw. Current top: Bayern, PSG, Arsenal, Real Madrid.
- Knockout progress = "appears in next round"; only the final's winner is computed (goals, then pens).
- Verified: 2024-25 final table and all 5 champions correct; 2026 MD4 table identical to API.
- Smart App Control blocked pyarrow's DLL; the user allowed it (2026-11-16). If Parquet errors return, that's the cause.

Note: 97 *distinct* raw spellings (the "125" above counts names in both sources twice).
Q2 preview (2024-26, MD4 position → reached R16): top-8 75%, 9–24 56%, 25–36 8%.

Name decisions: short canonical names for chart labels (e.g. "PSG", "Man City", "Bayern Munich"). Country = football-data spelling ("England"); `league_country()` maps Monaco → France for Q3 (AS Monaco plays in Ligue 1).

Dashboard: team selector lists all 80 clubs (not per season) so a selection survives season changes; cards warn if the team didn't play that season. Palette: accent #d62728, grey #c7c7c7, navy #1f3a93.

**Python on this PC:** `python` is the Windows Store stub and hangs. Use `C:\Users\ridz\AppData\Local\Python\bin\python.exe` (add `-X utf8`).
| 6–8 Views, simulation, polish | To do |

## Decisions made (and why)

1. **FootyStats dropped**: its match CSV needs a premium account.
2. **football-data.org used for 2026/27**: openfootball has no 2026-27 file (repo last updated July 2026). Free tier includes the Champions League.
   - API key is in `.env` (git-ignored), read by `fetch_data.py`. Never put it in code.
   - Downloads: `data/raw/footballdata/cl_2026_{matches,standings,teams}.json`.
3. **ClubElo dropped**: `api.clubelo.com` returned HTTP 502 for over a week.
   - **We compute our own Elo** in `src/elo.py` from all UCL matches 2021-22 → 2026-27.
   - Formula: new = old + K × (actual − expected), expected = 1 / (1 + 10^(−diff/400)), K ≈ 20 (to confirm).
   - Limitation: UCL-only matches (~8–17 per team per season), so less precise than ClubElo.
   - Defense answer: "ClubElo's API was down, so I applied the same Elo method to my own match data."
4. `CLAUDE.md`, `README.md` and `scripts/fetch_data.py` are updated to reflect 1–3.

## Data inventory (Phase 2 findings)

**openfootball** `data/raw/openfootball/<season>/cl.txt`, seasons 2021-22 … 2025-26
- 2021-23: 32 teams, 125 matches, sections `Group A`…`Group F`, `Gruppe G/H` (German!), then bare `Round of 16 / Quarterfinals / Semifinals / Final`. **No matchday numbers**; each group restarts in September.
- 2023-24: 32 teams, 125 matches, `Group, Matchday 1–6` (no group letter), then `Finals, …`.
- 2024-26: 36 teams, 189 matches, `League, Matchday 1–8`, `Playoffs, Matchday 1–2`, then Finals.
- Line format: `  [HH:MM]  Home Team (CTY) v Away Team (CTY)  <score>`. Date lines (`Wed Sep 17`) rarely carry a year → parser infers it from the season (Jul–Dec = first year), checking it against any year that is written.
- Score shapes: `2-1 (1-0)` · `0-0` (no half-time) · `3-1 a.e.t. (2-1, 0-0)` · `4-3 pen. 1-1 a.e.t. (1-1, 0-1)`.
- Header match counts equal the parsed line counts, so nothing is missing (test regex: `^\s+(?:\d\d:\d\d\s+)?(.+?)\s+v\s+(.+?)\s{2,}(\d+-\d+.*)$`).
- Knockouts are two separate legs with no aggregate score; who advanced must be derived.
- Times are local (CET). Use dates only.

**football-data.org** 2026/27 (read JSON with `encoding="utf-8"`)
- matches: 144 league-stage matches; MD1–4 `FINISHED` (72), MD5–8 `TIMED` (72), 8 Sep 2026 → 27 Jan 2027. Fields: utcDate, status, matchday, stage, homeTeam/awayTeam {id, name, shortName, tla}, score {winner, duration, fullTime, halfTime}. No missing scores. Odds paywalled (not needed).
- standings: 3 tables (TOTAL, HOME, AWAY); rows: position, team, playedGames, form, W/D/L, points, goalsFor/Against, goalDifference. After MD4 the leaders are PSG and Real Madrid (12 pts each), then Arsenal (10).
- teams: 36 teams with `area.name` (country, full name e.g. "England").

**Cleaning problems to solve in Phase 3**
1. Team names inconsistent *within* openfootball (e.g. "Real Madrid" vs "Real Madrid CF", "Inter" vs "FC Internazionale Milano", also Man City, Man Utd, PSG, Juventus, Bayern, Atalanta, Tottenham, Shakhtar, Dinamo Zagreb). 89 distinct spellings → `src/team_names.py`.
2. Country codes: openfootball `ENG` vs football-data `England` → need a code↔name lookup.
3. Year inference, the three score formats, and deriving knockout winners (aggregate, extra time, penalties).
4. Two competition formats (groups 2021-24 vs league 2024-26). Q2 uses only 2024-26; Q3 and Elo use all seasons.
