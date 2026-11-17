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
matches = load("matches")

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


# --- Linked views: clicking a dot selects that team everywhere ---------------------------
def click_selects_team(points: hv.Element, data: pd.DataFrame) -> hv.Element:
    """Make the dots clickable: a click sets the sidebar team selector.

    Selection1D reports the *row index* of the clicked dot; `data` is the
    DataFrame the dots were drawn from, so data.iloc[index] is that team.
    Every view is bound to team_w, so all of them update (= linked views).
    """
    stream = hv.streams.Selection1D(source=points)

    def on_click(index: list[int]) -> None:
        if index:
            team_w.value = data["team"].iloc[index[0]]

    stream.add_subscriber(on_click)
    # Tap tool = click to select; nonselection_alpha=1 stops Bokeh fading the other dots.
    return points.opts(tools=["tap", "hover"], nonselection_alpha=1.0)


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
    grey_points = click_selects_team(
        hv.Points(others, **Q1_DIMS).opts(color=GREY, size=9, line_color="white"), others)
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


# --- Q2: position after matchday 4 vs furthest round reached ----------------------------
# Only completed seasons in the 36-team format can answer "how far did they get?".
Q2_SEASONS = [s for s in LEAGUE_SEASONS if s != CURRENT_SEASON]          # 2024-25, 2025-26
Q2_ROUNDS = ["League phase", "Knockout playoffs", "Round of 16", "Quarterfinals",
             "Semifinals", "Final", "Winner"]
Q2_MARKERS = {Q2_SEASONS[0]: "circle", Q2_SEASONS[-1]: "triangle"}
Q2_OFFSET = {Q2_SEASONS[0]: -0.15, Q2_SEASONS[-1]: 0.15}   # separate the two seasons vertically

q2_outcomes = season_outcomes[season_outcomes["season"].isin(Q2_SEASONS)].copy()
q2_outcomes["round_idx"] = q2_outcomes["furthest"].astype(str).map(Q2_ROUNDS.index)
q2_outcomes["y"] = q2_outcomes["round_idx"] + q2_outcomes["season"].map(Q2_OFFSET)
q2_outcomes["furthest"] = q2_outcomes["furthest"].astype(str)
q2_outcomes["band"] = pd.cut(q2_outcomes["position_md4"].astype(float), [0, 8, 24, 36],
                             labels=["1–8", "9–24", "25–36"])


def q2_summary() -> str:
    """Share of teams per MD4 band that reached the Round of 16 / semi-finals."""
    rates = q2_outcomes.groupby("band", observed=True)[["reached_r16", "reached_sf"]].mean()
    parts = [f"**{band}**: {r.reached_r16:.0%} reached R16, {r.reached_sf:.0%} the semis"
             for band, r in rates.iterrows()]
    return f"After MD4, by position ({' and '.join(Q2_SEASONS)}, all 72 teams) — " + " · ".join(parts)


def q2_strip(team: str, countries: list[str]):
    df = q2_outcomes
    shown = df[df["league_country"].isin(countries)] if countries else df
    hover = ["team", "season", "position_md4", "position_final", "furthest"]
    # Explicit tooltips: hide the internal, vertically shifted "y" value.
    tips = dict(hover_tooltips=[("Team", "@team"), ("Season", "@season"),
                                ("Position after MD4", "@position_md4"),
                                ("Final league position", "@position_final"),
                                ("Furthest round", "@furthest")])

    layers = []
    for season, marker in Q2_MARKERS.items():
        s = shown[shown["season"].eq(season) & shown["team"].ne(team)]
        layers.append(click_selects_team(
            s.hvplot.scatter(x="position_md4", y="y", color=GREY, marker=marker,
                             size=70, hover_cols=hover, label=season, **tips), s))
    for season, marker in Q2_MARKERS.items():   # selected team drawn last = on top
        s = df[df["season"].eq(season) & df["team"].eq(team)]
        if not s.empty:
            layers.append(s.hvplot.scatter(x="position_md4", y="y", color=ACCENT, marker=marker,
                                           size=160, line_color="black", hover_cols=hover, **tips))

    cutoffs = (hv.VLine(8.5) * hv.VLine(24.5)).opts(
        hv.opts.VLine(color=PRIMARY, line_dash="dashed", line_width=1))
    played = df.loc[df["team"].eq(team), "season"].tolist()
    note = f"{team}: {', '.join(played)}" if played else f"{team} played in neither season"
    return hv.Overlay(layers + [cutoffs]).opts(
        title=f"Does an early top-8 spot lead to a deep run? ({note})",
        xlabel="Table position after matchday 4", ylabel="Furthest round reached",
        yticks=list(enumerate(Q2_ROUNDS)), xticks=[1, 8, 16, 24, 36], xlim=(0, 37),
        ylim=(-0.6, len(Q2_ROUNDS) - 0.4),
        responsive=True, height=380, legend_position="bottom_right",
    )


# --- Q3: country x season heatmap -----------------------------------------------------
Q3_METRICS = {   # label shown to the user -> column in country_season
    "Points per match": "points_per_match",
    "Average Elo (end of season)": "mean_elo",
    "Win rate": "win_rate",
    "Clubs reaching R16": "clubs_in_r16",
}
# Default rows: countries with >= 50 UCL matches over all seasons. Smaller samples
# (e.g. one club, 6 matches) give noisy values. The country filter overrides this.
Q3_MIN_MATCHES = 50
_matches_per_country = country_season.groupby("league_country")["matches"].sum()
Q3_DEFAULT_COUNTRIES = _matches_per_country[_matches_per_country >= Q3_MIN_MATCHES].index.tolist()

q3_metric_w = pn.widgets.RadioButtonGroup(options=list(Q3_METRICS), value="Points per match",
                                          button_type="light", button_style="outline")


def q3_heatmap(metric_label: str, team: str, countries: list[str]):
    metric = Q3_METRICS[metric_label]
    df = country_season[country_season["league_country"].isin(countries or Q3_DEFAULT_COUNTRIES)].copy()
    df["value"] = df[metric].round(0 if metric == "mean_elo" else 2)   # tidy hover values
    # Rows sorted by the metric's average over all seasons: strongest league on top.
    order = df.groupby("league_country")["value"].mean().sort_values().index.tolist()

    # Cells where the selected team played: their numbers are drawn in the accent colour.
    team_cells = team_matches.loc[team_matches["team"].eq(team), ["league_country", "season"]] \
        .drop_duplicates()
    df = df.merge(team_cells.assign(is_team=True), on=["league_country", "season"], how="left")
    df["is_team"] = df["is_team"].fillna(False).astype(bool)
    df["text"] = df["value"].map(lambda v: f"{v:.0%}" if metric == "win_rate" else
                                 f"{v:.0f}" if metric in ("mean_elo", "clubs_in_r16") else f"{v:.2f}")

    vdims = [hv.Dimension("value", label=metric_label), hv.Dimension("clubs", label="Clubs"),
             hv.Dimension("matches", label="Matches"), hv.Dimension("clubs_in_r16", label="Clubs in R16"),
             hv.Dimension("titles", label="Titles")]
    kdims = [hv.Dimension("season", label="Season"), hv.Dimension("league_country", label="Country")]
    heat = hv.HeatMap(df, kdims, vdims).redim.values(league_country=order).opts(
        cmap="Blues", colorbar=True, tools=["hover"], line_color="white", line_width=2,
        clabel=metric_label)
    plain = hv.Labels(df[~df["is_team"]], kdims, "text").opts(text_font_size="8pt", text_color="#333")
    highlight = hv.Labels(df[df["is_team"]], kdims, "text").opts(
        text_font_size="10pt", text_color=ACCENT, text_font_style="bold")

    return (heat * plain * highlight).opts(
        title=f"Which leagues send the strongest clubs? {metric_label} by country and season",
        xlabel="Season (2026-27 = in progress)", ylabel="League country",
        responsive=True, height=max(300, 34 * len(order) + 120),
    )


# --- Match explorer: searchable table (all views' raw data) -------------------------------
def _score(m) -> str:
    """'2–1', '1–1 a.e.t. (4–3 pens)', or 'scheduled' for unplayed matches."""
    if not m.played:
        return "scheduled"
    s = f"{m.home_goals}–{m.away_goals}"
    if m.extra_time:
        s += " a.e.t."
    if pd.notna(m.home_pens):
        s += f" ({m.home_pens}–{m.away_pens} pens)"
    return s


# Built once: a readable version of `matches` for display.
match_table = pd.DataFrame({
    "Date": matches["date"].dt.date,
    "Season": matches["season"],
    "Round": matches["round"],
    "Home": matches["home_team"],
    "Score": [_score(m) for m in matches.itertuples()],
    "Away": matches["away_team"],
    "Home country": matches["home_country"],
    "Away country": matches["away_country"],
}).sort_values("Date", ascending=False).reset_index(drop=True)

all_teams_w = pn.widgets.Checkbox(name="Show all teams (not only the selected one)", value=False)


def match_rows(team: str, all_teams: bool) -> pd.DataFrame:
    if all_teams:
        return match_table
    return match_table[match_table["Home"].eq(team) | match_table["Away"].eq(team)]


# Header filters: a search box per column; dropdowns where there are few values.
match_tabulator = pn.widgets.Tabulator(
    pn.bind(match_rows, team_w, all_teams_w),   # value updates when the team changes
    show_index=False, disabled=True, pagination="local", page_size=12,
    layout="fit_data_stretch", sizing_mode="stretch_width",
    header_filters={
        "Date": {"type": "input", "func": "like", "placeholder": "e.g. 2026-10"},
        "Season": {"type": "list", "valuesLookup": True, "clearable": True},
        "Round": {"type": "list", "valuesLookup": True, "clearable": True},
        "Home": {"type": "input", "func": "like", "placeholder": "search"},
        "Score": {"type": "input", "func": "like", "placeholder": "e.g. pens"},
        "Away": {"type": "input", "func": "like", "placeholder": "search"},
        "Home country": {"type": "list", "valuesLookup": True, "clearable": True},
        "Away country": {"type": "list", "valuesLookup": True, "clearable": True},
    },
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
        "Elo (straight-line fit through all 36 teams). **Above the line = over-performing.** "
        "**Click a dot** to select that team in every view.",
        styles={"font-size": "0.85em", "color": "#666"}),
)
q2 = card(
    "Q2 · Early form: does position after matchday 4 predict a deep run?",
    pn.panel(pn.bind(q2_bump, season_w, team_w, country_w, matchday_w)),
    pn.panel(pn.bind(q2_strip, team_w, country_w)),
    pn.pane.Markdown(q2_summary() + ". Click a dot to select that team. Uses the two completed 36-team seasons; the season "
                     "and matchday filters do not apply to this chart.",
                     styles={"font-size": "0.85em", "color": "#666"}),
)
q3 = card(
    "Q3 · Strength by country: which leagues send the strongest clubs?",
    q3_metric_w,
    pn.panel(pn.bind(q3_heatmap, q3_metric_w, team_w, country_w)),
    pn.pane.Markdown(
        f"Default rows: the {len(Q3_DEFAULT_COUNTRIES)} countries with at least {Q3_MIN_MATCHES} UCL "
        "matches since 2021-22 (smaller samples are too noisy); pick countries in the sidebar to "
        "change this. **Red numbers** = seasons the selected team played. Monaco counts as France.",
        styles={"font-size": "0.85em", "color": "#666"}),
)
q4 = card("Q4 · Title probability: who is most likely to win? (model, not a forecast)",
          *placeholder("Monte Carlo simulation of the remaining matches."))

explorer = card(
    "Match explorer · every UCL match 2021-22 → 2026-27 (search with the boxes under each header)",
    all_teams_w, match_tabulator,
)

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
    main=[pn.Row(q1, q2), pn.Row(q3, q4), explorer, footer],
    accent=PRIMARY,
    header_background=PRIMARY,
)
template.servable()
