# Project brief for the AI agent

This file gives an AI coding agent (Claude Code, Copilot agent, Cursor, etc.) the context it needs.
Read it at the start of every session, **together with `MEMORY.md` (progress log, decisions, data findings)**. Keep answers short and act on files rather than pasting long code into chat.

## What we are building

An **interactive data visualization dashboard** for a university course project:
**"UEFA Champions League 2026/27 — who are the real contenders?"**

- Framework: **Panel + hvPlot / HoloViews (Bokeh backend)** — all listed on PyViz.org.
- Language: Python 3.11+.
- Run with: `panel serve app/app.py --show --autoreload`

## Assessment criteria (everything we do must serve one of these)

1. **Data preparation** — cleaning, missing values, type conversion, derived variables, aggregation, combining sources, reshaping. Must be documented step by step in `notebooks/01_data_preparation.ipynb`.
2. **Design process** — clear analytical questions, coherent structure, consistent visual design.
3. **Quality of visualizations** — chart type fits the data; readable; diverse. **Not only bar, line and pie charts.**
4. **Analytical capabilities** — filtering, searching, selection, hover, zoom, **linked views**.
5. **Technical implementation** — runs without errors, stable, idiomatic use of Panel/hvPlot.
6. **Defense** — the student must be able to explain every step. Prefer clear, readable code over clever code. Comment the *why*.

## Analytical questions

- **Q1 Contenders:** Which teams are genuinely strong this season, and which are over- or under-performing their underlying strength (points vs Elo rating)?
- **Q2 Early form:** Historically, how well does league-phase position after matchday 4 predict who reaches the knockouts / semis / wins? (uses 2024/25 and 2025/26, the seasons with the 36-team league format)
- **Q3 Strength by country:** Which national leagues send the strongest clubs, and how has that changed across seasons?
- **Q4 Title probability:** Given current standings and Elo ratings, what is each team's estimated chance of winning? (simple Monte Carlo simulation — clearly labelled as a model, not a forecast)

## Data sources (cite all of them in README.md and in the dashboard footer)

| File | Source | How obtained |
|---|---|---|
| `data/raw/openfootball/<season>/cl.txt` | openfootball/champions-league (GitHub, public domain) | `python scripts/fetch_data.py` |
| `data/raw/footballdata/cl_2026_{matches,standings,teams}.json` | football-data.org API v4 (free tier) | `python scripts/fetch_data.py` (needs `FOOTBALL_DATA_API_KEY` in `.env`) |

Source changes (Nov 2026), and why:
- FootyStats dropped: its match CSV is paywalled. openfootball has no 2026-27 file, so football-data.org is the current-season source.
- ClubElo dropped: api.clubelo.com returned HTTP 502 for over a week. Instead, **we compute our own Elo ratings** in `src/elo.py` from all UCL matches 2021-22 → 2026-27 (standard Elo formula, documented in the notebook). Limitation: UCL matches only, so ratings are less precise than ClubElo's (which also uses domestic leagues).

## Data rules

- **Never invent or hand-type data.** If a file is missing, stop and tell the student which file to download.
- Raw files in `data/raw/` are read-only. All outputs go to `data/processed/` (Parquet preferred).
- Team names differ across sources (e.g. "FC Bayern München" vs "Bayern" vs "Bayern Munich"). Build ONE explicit mapping table `src/team_names.py` and test that every team in every source maps to a canonical name. Unmapped names must raise an error, not be silently dropped.
- Log every cleaning decision (rows dropped, values imputed, outliers) in the notebook with a short markdown cell explaining it.

## Code layout

```
scripts/fetch_data.py      download raw data
src/parse_openfootball.py  parse openfootball .txt -> matches DataFrame
src/team_names.py          canonical team-name mapping
src/elo.py                 self-computed Elo ratings from match results (replaces ClubElo)
src/prepare.py             full pipeline: raw -> data/processed/*.parquet
src/simulate.py            Monte Carlo title-probability model
notebooks/01_data_preparation.ipynb  narrated version of prepare.py for the defense
app/app.py                 Panel dashboard (reads only data/processed/)
docs/defense_notes.md      questions, design decisions, insights
```

## Dashboard design rules

- One consistent colour palette; highlight the selected team in one accent colour and grey out others.
- Every chart has a title that states the question it answers, axis labels with units, and hover tooltips.
- Use `pn.template.FastListTemplate` (or similar) with a sidebar of filters: season, team (searchable), country, matchday range.
- Selecting a team must update all views (linked). Use `pn.bind` / `param` for reactivity and HoloViews `link_selections` or `Selection1D` streams where sensible.
- Target chart types: bump chart (rank by matchday), scatter (Elo vs points, with team labels), heatmap (results matrix or country × season), distribution/box plot (goals or margins), simulated probability chart, searchable data table (`pn.widgets.Tabulator`).

## Working style

- Work in small steps. After each step: run it, confirm it works, then stop and summarise in 3–5 lines.
- Do not rewrite files wholesale when a small edit will do.
- Ask before adding new dependencies.
