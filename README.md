# UEFA Champions League 2026/27 — Who are the real contenders?

An interactive dashboard that combines five seasons of Champions League history with the
current 2026/27 season to find out which teams are genuinely strong. Built with
**Panel + hvPlot / HoloViews (Bokeh)** from the PyViz ecosystem for a university course on
interactive data visualization.

![Dashboard screenshot](docs/screenshot.png)
<!-- TODO: add a screenshot of the running dashboard as docs/screenshot.png -->

## Analytical questions

| # | Question | View |
|---|---|---|
| Q1 | **Contenders** — which teams are strong this season, and who is over- or under-performing their underlying strength? | Scatter: Elo rating vs points, with an "expected from Elo" fit line |
| Q2 | **Early form** — how well does the table position after matchday 4 predict a deep run? (2024-25, 2025-26: the 36-team format) | Bump chart of table position by matchday + strip plot of MD4 position vs furthest round |
| Q3 | **Strength by country** — which national leagues send the strongest clubs, and how has that changed? | Heatmap: country × season (points per match, Elo, win rate, clubs in R16) |
| Q4 | **Title probability** — given current standings and Elo, what is each team's chance? | Horizontal probability bars from a 10,000-run Monte Carlo model (clearly labelled as a model) |

Plus a **match explorer**: a searchable, filterable table of all 897 matches.

**Interaction:** sidebar filters (season, searchable team, country, matchday range); hover
tooltips on every chart; zoom/pan; **linked views** — the selected team is highlighted in every
chart, and clicking a dot in the Q1 or Q2 chart selects that team everywhere.

## Data sources

| Data | Source | Seasons | How obtained |
|---|---|---|---|
| Match results (plain text) | [openfootball/champions-league](https://github.com/openfootball/champions-league) — public domain | 2021-22 → 2025-26 | `python scripts/fetch_data.py` |
| Matches, standings, teams (JSON) | [football-data.org](https://www.football-data.org/) API v4, free tier | 2026-27 (league phase, matchdays 1–4 played) | `python scripts/fetch_data.py` (needs an API key) |
| Team strength (Elo) | **Computed by us** in `src/elo.py` from the matches above ([Elo method](https://en.wikipedia.org/wiki/Elo_rating_system)) | 2021-22 → 2026-27 | `python src/prepare.py` |

Elo ratings are self-computed because the ClubElo API was unavailable (HTTP 502) for over a week.

## Data preparation (summary)

Documented step by step in [`notebooks/01_data_preparation.ipynb`](notebooks/01_data_preparation.ipynb);
the code is in `src/`.

1. **Parse** openfootball's text files with regular expressions: four score formats (normal,
   no half-time, extra time, penalties), dates without a year, team name + country code in one
   string. Match counts are checked against each file's header.
2. **Load** the football-data.org JSON for 2026-27; the 72 not-yet-played matches are kept
   (`played = False`) because the simulation needs them.
3. **Clean names:** 97 raw team spellings → 80 canonical clubs via one explicit mapping table
   (`src/team_names.py`); unknown names raise an error instead of being dropped. Country codes →
   country names; Monaco counts as France for league analysis.
4. **Fix types:** nullable integers for goals (missing = unplayed), real dates, derived flags.
5. **Reshape** wide (home/away columns) → long (one row per team per match).
6. **Derive:** own Elo ratings; the league table after every matchday (UEFA tie-breakers);
   furthest round reached per team and season; current table + Elo, **verified against the
   official API table**.
7. **Aggregate** by country × season for Q3.
8. **Simulate** the rest of 2026-27 (`src/simulate.py`) for Q4.

No rows are dropped; every missing value has a documented reason (see the notebook).

## Install and run

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# Optional — raw data is already in data/raw/. To re-download, put
# FOOTBALL_DATA_API_KEY=<your key> in a .env file, then:
python scripts/fetch_data.py

python src/prepare.py           # raw -> data/processed/*.parquet
python src/simulate.py          # Monte Carlo -> data/processed/simulation_2026.parquet

panel serve app/app.py --show   # opens the dashboard at http://localhost:5006/app
```

The processed Parquet files are committed, so `panel serve app/app.py --show` also works on its own.

## Project structure

```
scripts/fetch_data.py               download raw data
src/parse_openfootball.py           parse openfootball .txt -> matches table
src/team_names.py                   canonical team-name mapping (+ checks)
src/elo.py                          self-computed Elo ratings
src/prepare.py                      full pipeline: raw -> data/processed/*.parquet
src/simulate.py                     Monte Carlo title-probability model
notebooks/01_data_preparation.ipynb narrated data preparation
app/app.py                          Panel dashboard (reads only data/processed/)
docs/defense_notes.md               questions, design decisions, insights, limitations
```

## Limitations

- **Small current-season sample:** only 4 of 8 league matchdays of 2026-27 have been played.
- **Elo from UCL matches only** (8–17 per team per season), so ratings are noisier than ClubElo's,
  which also uses domestic leagues; 2021-22 is a warm-up season where everyone starts at 1500.
- **Simple model:** frozen ratings, a fixed knockout bracket, and goal difference not simulated —
  the probabilities show what the Elo ratings imply, not a prediction.
- **Q2 rests on two seasons** (72 team-seasons), because the 36-team format only began in 2024-25.
