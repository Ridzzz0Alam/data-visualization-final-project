"""UEFA Champions League 2026/27 — who are the real contenders?

Panel dashboard. Run from the project root:
    panel serve app/app.py --show --autoreload

Reads ONLY data/processed/*.parquet (built by src/prepare.py).
Phase 5 = skeleton: sidebar filters + four placeholder cards (one per question).
"""

from __future__ import annotations

from pathlib import Path

import holoviews as hv
import hvplot.pandas  # noqa: F401  (registers .hvplot on DataFrames, loads the Bokeh backend)
import numpy as np
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
standings_2026 = load("standings_2026")

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


# --- Q1: Elo vs points scatter (current season) ------------------------------------
CURRENT_TABLES = league_tables[league_tables["season"].eq(CURRENT_SEASON)]
LATEST_MD = int(CURRENT_TABLES["matchday"].max())   # matchdays played so far (4)


def q1_data(matchdays: tuple[int, int]) -> pd.DataFrame:
    """Points and GD won *within* the matchday range, plus Elo and expected points.

    league_tables is cumulative, so points in matchdays a..b =
    cumulative after b  minus  cumulative after a-1.
    """
    start, end = matchdays[0], min(matchdays[1], LATEST_MD)
    cum = CURRENT_TABLES.set_index(["matchday", "team"])[["points", "goal_diff"]]
    after_end = cum.loc[end]
    before = cum.loc[start - 1] if start > 1 else after_end * 0
    df = (after_end - before).join(
        standings_2026.set_index("team")[["league_country", "elo", "position"]]).reset_index()

    # "Expected" points = straight line fitted through all 36 teams (least squares).
    # Fitted before any country filter, so the reference line doesn't move when filtering.
    slope, intercept = np.polyfit(df["elo"], df["points"], deg=1)
    df["expected"] = intercept + slope * df["elo"]
    df["vs_expected"] = (df["points"] - df["expected"]).round(1)  # + = over-performing
    df["elo"] = df["elo"].round(0)
    return df


# Dimension labels make axis titles and hover tooltips readable.
Q1_DIMS = dict(
    kdims=[hv.Dimension("elo", label="Elo rating (pts)"), hv.Dimension("points", label="Points")],
    vdims=[hv.Dimension("team", label="Team"), hv.Dimension("league_country", label="Country"),
           hv.Dimension("goal_diff", label="Goal difference"),
           hv.Dimension("vs_expected", label="Points vs expected"),
           hv.Dimension("position", label="Table position")],
)


def q1_scatter(team: str, countries: list[str], matchdays: tuple[int, int]):
    if matchdays[0] > LATEST_MD:
        return pn.pane.Markdown(f"Only matchdays 1–{LATEST_MD} of {CURRENT_SEASON} have been played. "
                                "Move the matchday slider down.")
    df = q1_data(matchdays)
    line = df.sort_values("elo")
    shown = df[df["league_country"].isin(countries)] if countries else df
    others, selected = shown[shown["team"] != team], df[df["team"] == team]

    # Label only what matters, to avoid 36 overlapping names: the selected team
    # plus the 4 biggest over- and under-performers.
    notable = pd.concat([shown.nlargest(4, "vs_expected"), shown.nsmallest(4, "vs_expected"), selected])

    expected_line = hv.Curve(line, "elo", "expected", label="Expected from Elo").opts(
        color=PRIMARY, line_dash="dashed", line_width=1.5)
    grey_points = hv.Points(others, **Q1_DIMS).opts(color=GREY, size=9, line_color="white", tools=["hover"])
    accent_point = hv.Points(selected, **Q1_DIMS).opts(color=ACCENT, size=15, line_color="black", tools=["hover"])
    labels = hv.Labels(notable, ["elo", "points"], "team").opts(
        text_font_size="8pt", yoffset=0.45, text_color="#444")

    md_text = f"MD {matchdays[0]}–{min(matchdays[1], LATEST_MD)}"
    return (expected_line * grey_points * accent_point * labels).opts(
        title=f"Who beats their Elo? Points vs Elo rating, {CURRENT_SEASON} ({md_text})",
        xlabel="Elo rating (pts)", ylabel=f"Points won ({md_text})",
        responsive=True, height=420, show_legend=True, legend_position="top_left",
    )


# --- Q2 (and Q1): bump chart — table position after every matchday --------------------
LEAGUE_SEASONS = sorted(league_tables["season"].unique())   # 36-team format only


def q2_bump(season: str, team: str, countries: list[str], matchdays: tuple[int, int]):
    if season not in LEAGUE_SEASONS:
        return pn.pane.Markdown(
            f"**{season}** used the old group format (no 36-team table). "
            f"Pick one of: {', '.join(LEAGUE_SEASONS)}.")
    df = league_tables[league_tables["season"].eq(season)
                       & league_tables["matchday"].between(*matchdays)]
    if df.empty:
        return pn.pane.Markdown(f"No matchdays in range {matchdays[0]}–{matchdays[1]} for {season}.")

    shown = df[df["league_country"].isin(countries)] if countries else df
    others, selected = shown[shown["team"] != team], df[df["team"] == team]
    hover = ["team", "points", "goal_diff"]

    # One grey line per team; `by="team"` draws 36 separate lines in one call.
    grey = others.hvplot.line(x="matchday", y="position", by="team", color=GREY,
                              line_width=1.5, alpha=0.7, hover_cols=hover, legend=False)
    plot = grey
    if not selected.empty:  # the selected team may not have played this season
        plot = plot * selected.hvplot.line(x="matchday", y="position", color=ACCENT,
                                           line_width=4, hover_cols=hover)
        plot = plot * selected.hvplot.scatter(x="matchday", y="position", color=ACCENT,
                                              size=60, hover_cols=hover)

    # Qualification cut-offs: top 8 -> Round of 16, 9-24 -> knockout play-offs, 25+ out.
    cutoffs = (hv.HLine(8.5) * hv.HLine(24.5)).opts(
        hv.opts.HLine(color=PRIMARY, line_dash="dashed", line_width=1))
    zone_labels = hv.Labels({"x": [matchdays[0]] * 3, "y": [4.5, 16.5, 30.5],
                             "text": ["Top 8 → R16", "9–24 → play-offs", "25+ → out"]},
                            ["x", "y"], "text").opts(
        text_font_size="8pt", text_color=PRIMARY, text_align="left", text_alpha=0.6)

    note = "" if not selected.empty else f" ({team} did not play)"
    return (plot * cutoffs * zone_labels).opts(
        title=f"How did {team}'s table position change? {season}{note}",
        xlabel="League matchday", ylabel="Table position (1 = top)",
        invert_yaxis=True, xticks=list(range(matchdays[0], matchdays[1] + 1)),
        yticks=[1, 8, 16, 24, 36], ylim=(0, 37),
        responsive=True, height=420, show_legend=False,
    )


def card(title: str, *content) -> pn.Card:
    return pn.Card(
        *content, title=title, collapsible=False,
        header_background=PRIMARY, header_color="white", min_height=280,
    )


def placeholder(plan: str) -> tuple:
    return pn.pane.Markdown(f"*Placeholder — {plan}*"), filters_md


q1 = card(
    "Q1 · Contenders: who is over- or under-performing their Elo?",
    # pn.panel (not pn.pane.HoloViews) because q1_scatter may return a plot OR a message.
    pn.panel(pn.bind(q1_scatter, team_w, country_w, matchday_w)),
    pn.pane.Markdown(
        f"Always the current season ({CURRENT_SEASON}). Dashed line = points expected from "
        "Elo (straight-line fit through all 36 teams). **Above the line = over-performing.**",
        styles={"font-size": "0.85em", "color": "#666"}),
)
q2 = card(
    "Q2 · Early form: does position after matchday 4 predict a deep run?",
    pn.panel(pn.bind(q2_bump, season_w, team_w, country_w, matchday_w)),
    *placeholder("MD4 position vs furthest round reached (2024-26) — Phase 6c."),
)
q3 = card("Q3 · Strength by country: which leagues send the strongest clubs?",
          *placeholder("heatmap of country × season (points per match / Elo)."))
q4 = card("Q4 · Title probability: who is most likely to win? (model, not a forecast)",
          *placeholder("Monte Carlo simulation of the remaining matches."))

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
