"""UEFA Champions League 2026/27 — who are the real contenders?

Panel dashboard. Run from the project root:
    panel serve app/app.py --show --autoreload

Reads ONLY data/processed/*.parquet (built by src/prepare.py).
Phase 5 = skeleton: sidebar filters + four placeholder cards (one per question).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import panel as pn

pn.extension("tabulator", sizing_mode="stretch_width")

# --- Data ---------------------------------------------------------------------
DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


@pn.cache  # load once per server, not once per browser session
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


team_matches = load("team_matches")
league_tables = load("league_tables")
season_outcomes = load("season_outcomes")
country_season = load("country_season")

SEASONS = sorted(team_matches["season"].unique())
CURRENT_SEASON = SEASONS[-1]
TEAMS = sorted(team_matches["team"].unique())
COUNTRIES = sorted(team_matches["league_country"].unique())
MAX_MATCHDAY = int(league_tables["matchday"].max())  # 8 in the 36-team format

# --- Visual design (one palette for every chart) -------------------------------
ACCENT = "#d62728"     # the selected team
GREY = "#c7c7c7"       # all other teams
PRIMARY = "#1f3a93"    # UCL-style navy for headers / neutral marks

# --- Sidebar widgets ------------------------------------------------------------
season_w = pn.widgets.Select(name="Season", options=SEASONS, value=CURRENT_SEASON)

# AutocompleteInput = searchable: type "bay" to find Bayern Munich.
# The list holds all clubs from every season, so a selection survives a season
# change (needed for the across-season view in Q3).
team_w = pn.widgets.AutocompleteInput(
    name="Team (type to search)", options=TEAMS, value="Arsenal",
    case_sensitive=False, search_strategy="includes", restrict=True, min_characters=1,
)
country_w = pn.widgets.MultiChoice(name="Country (empty = all)", options=COUNTRIES)
matchday_w = pn.widgets.IntRangeSlider(
    name="League matchdays", start=1, end=MAX_MATCHDAY, value=(1, MAX_MATCHDAY), step=1,
)


# --- Placeholder content (replaced by real charts in Phase 6) ---------------------
def filter_summary(season: str, team: str, countries: list[str], matchdays: tuple[int, int]) -> str:
    """Echo the current filters so we can see every widget is wired up."""
    in_season = team in set(team_matches.loc[team_matches["season"].eq(season), "team"])
    note = "" if in_season else f"  \n⚠️ {team} did not play in {season}."
    return (f"**Season** {season} · **Team** {team} · "
            f"**Countries** {', '.join(countries) or 'all'} · "
            f"**Matchdays** {matchdays[0]}–{matchdays[1]}{note}")


filters_md = pn.pane.Markdown(pn.bind(filter_summary, season_w, team_w, country_w, matchday_w))


def card(title: str, plan: str) -> pn.Card:
    return pn.Card(
        pn.pane.Markdown(f"*Placeholder — {plan}*"), filters_md,
        title=title, collapsible=False, header_background=PRIMARY, header_color="white",
        min_height=280,
    )


q1 = card("Q1 · Contenders: who is over- or under-performing their Elo?",
          "scatter of Elo vs points with the selected team highlighted.")
q2 = card("Q2 · Early form: does position after matchday 4 predict a deep run?",
          "bump chart of rank by matchday + MD4 position vs furthest round (2024-26).")
q3 = card("Q3 · Strength by country: which leagues send the strongest clubs?",
          "heatmap of country × season (points per match / Elo).")
q4 = card("Q4 · Title probability: who is most likely to win? (model, not a forecast)",
          "Monte Carlo simulation of the remaining matches.")

# --- Layout ---------------------------------------------------------------------
footer = pn.pane.Markdown(
    "Data: [openfootball/champions-league](https://github.com/openfootball/champions-league) "
    "(public domain, 2021-22 → 2025-26) · "
    "[football-data.org](https://www.football-data.org/) API v4 (2026-27) · "
    "Elo ratings computed by the author from UCL results.",
    styles={"font-size": "0.85em", "color": "#666"},
)

template = pn.template.FastListTemplate(
    title="UEFA Champions League 2026/27 — who are the real contenders?",
    sidebar=[season_w, team_w, country_w, matchday_w],
    main=[pn.Row(q1, q2), pn.Row(q3, q4), footer],
    accent=PRIMARY,
    header_background=PRIMARY,
)
template.servable()
