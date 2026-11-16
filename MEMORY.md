# Project memory — progress log

Read this together with `CLAUDE.md` at the start of every session. Update it at the end of each phase.

## Status (last updated 2026-11-16)

| Phase | Status |
|---|---|
| 0 Setup | Partly done. Packages work. **Not yet a git repo** → run `git init` + first commit |
| 1 Get data | ✅ Done (`python scripts/fetch_data.py`) |
| 2 Explore raw data | ✅ Done (findings below). Student still to write own "Datasets" bullets in `docs/defense_notes.md` |
| 3a Parser `src/parse_openfootball.py` | ✅ Done: 815 matches, 5 seasons, counts match headers |
| 3b `src/team_names.py` | ⏭ **Next** |
| 3c `src/prepare.py` (+ `src/elo.py`) | To do |

**Python on this PC:** `python` is the Windows Store stub and hangs. Use `C:\Users\ridz\AppData\Local\Python\bin\python.exe` (add `-X utf8`).
| 4–8 Notebook, dashboard, simulation, polish | To do |

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
