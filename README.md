# UEFA Champions League 2026/27 — Who are the real contenders?

Interactive dashboard built with Panel + hvPlot/HoloViews (PyViz).
Course project: interactive data visualization.

> Work in progress — see `WORKFLOW.md` for the build plan and `CLAUDE.md` for the project brief.

## Run
```bash
pip install -r requirements.txt
python scripts/fetch_data.py
panel serve app/app.py --show
```

## Data sources
- openfootball/champions-league — https://github.com/openfootball/champions-league
- football-data.org (current 2026/27 season, free API key required) — https://www.football-data.org

Team strength ratings are **computed by us** with the Elo method (see `src/elo.py`), because the ClubElo API was unavailable. Method: https://en.wikipedia.org/wiki/Elo_rating_system
