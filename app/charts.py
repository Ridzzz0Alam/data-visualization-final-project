"""Chart builders. Each function takes plain values (team name, filters) and
returns a HoloViews object — no widgets here, so every chart can be tested alone."""

from __future__ import annotations

from typing import Callable

import holoviews as hv
import hvplot.pandas  # noqa: F401  (registers .hvplot on DataFrames)
import numpy as np
import pandas as pd
import panel as pn

import data as d
from theme import ACCENT, CHART_OPTS, GOLD, GREY, HEAT_CMAP, REF


def message(text: str) -> pn.pane.Markdown:
    """Shown instead of an empty chart."""
    return pn.pane.Markdown(f"*{text}*", styles={"color": "#8b95ba", "font-size": "15px"})


def clickable(points: hv.Element, data: pd.DataFrame, on_select: Callable[[str], None]) -> hv.Element:
    """Linked views: clicking a dot calls on_select(team) (which sets the focus team).

    Selection1D reports the row index of the clicked dot; `data` is the DataFrame the
    dots were drawn from, so data.iloc[index] is that team.
    """
    stream = hv.streams.Selection1D(source=points)
    stream.add_subscriber(lambda index: index and on_select(data["team"].iloc[index[0]]))
    return points.opts(tools=["tap", "hover"], nonselection_alpha=1.0)


def _filter(df: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    return df[df["league_country"].isin(countries)] if countries else df


# --- Q1 Contenders ------------------------------------------------------------------
Q1_DIMS = dict(
    kdims=[hv.Dimension("elo", label="Elo rating"), hv.Dimension("points", label="Points")],
    vdims=[hv.Dimension("team", label="Team"), hv.Dimension("league_country", label="Country"),
           hv.Dimension("goal_diff", label="Goal difference"),
           hv.Dimension("vs_expected", label="Points vs expected"),
           hv.Dimension("position", label="Table position")],
)


def q1_scatter(team, countries, matchdays, on_select):
    if matchdays[0] > d.LATEST_MD:
        return message(f"Only matchdays 1–{d.LATEST_MD} have been played — move the slider down.")
    df = d.q1_data(matchdays)
    shown = _filter(df, countries)
    others, focus = shown[shown["team"] != team], df[df["team"] == team]
    notable = pd.concat([shown.nlargest(4, "vs_expected"), shown.nsmallest(4, "vs_expected"), focus])

    line = hv.Curve(df.sort_values("elo"), "elo", "expected", label="Expected from Elo").opts(
        color=REF, line_dash="dashed", line_width=2)
    grey = clickable(hv.Points(others, **Q1_DIMS).opts(
        color=GREY, size=11, line_color="#0e1530", line_width=1.5), others, on_select)
    accent = hv.Points(focus, **Q1_DIMS).opts(color=ACCENT, size=18, line_color="white",
                                              line_width=2, tools=["hover"])
    labels = hv.Labels(notable, ["elo", "points"], "team").opts(
        text_font_size="9pt", yoffset=0.5, text_color="#c9d1f0")
    md = f"MD {matchdays[0]}–{min(matchdays[1], d.LATEST_MD)}"
    return (line * grey * accent * labels).opts(
        title=f"Who beats their Elo? Points vs Elo rating ({md})",
        xlabel="Elo rating (rating points)", ylabel=f"Points won ({md})",
        height=460, show_legend=True, legend_position="top_left", **CHART_OPTS)


def q1_lollipop(team, countries, matchdays):
    """Ranking of over/under-performance: the 8 biggest each way (+ focus team)."""
    if matchdays[0] > d.LATEST_MD:
        return message("No matches in this range yet.")
    df = _filter(d.q1_data(matchdays), countries)
    df = pd.concat([df.nlargest(8, "vs_expected"), df.nsmallest(8, "vs_expected"),
                    d.q1_data(matchdays).query("team == @team")])
    df = df.drop_duplicates("team").sort_values("vs_expected").reset_index(drop=True)
    df["y"] = np.arange(len(df))
    df["colour"] = np.where(df["team"].eq(team), ACCENT, np.where(df["vs_expected"] > 0, "#9aa6d1", GREY))

    stems = hv.Segments(df.assign(zero=0), ["zero", "y", "vs_expected", "y"]).opts(
        color="colour", line_width=3)
    dots = hv.Points(df, ["vs_expected", "y"], ["team", "points", "colour"]).opts(
        color="colour", size=12, tools=["hover"], line_color=None,
        hover_tooltips=[("Team", "@team"), ("Points", "@points"), ("Vs expected", "@vs_expected")])
    zero = hv.VLine(0).opts(color=REF, line_width=1)
    return (stems * dots * zero).opts(
        title="Biggest over- and under-performers (points vs Elo expectation)",
        xlabel="Points above (+) or below (−) expectation", ylabel="",
        yticks=list(zip(df["y"], df["team"])), height=460, **CHART_OPTS)


# --- Q2 Early form --------------------------------------------------------------------
def q2_bump(season, team, matchdays):
    df = d.league_tables[d.league_tables["season"].eq(season)
                         & d.league_tables["matchday"].between(*matchdays)]
    if df.empty:
        return message(f"No matchdays {matchdays[0]}–{matchdays[1]} played in {season} yet.")
    others, focus = df[df["team"] != team], df[df["team"] == team]
    tips = dict(hover_tooltips=[("Team", "@team"), ("Matchday", "@matchday"),
                                ("Position", "@position"), ("Points", "@points")],
                hover_cols=["team", "points"])
    plot = others.hvplot.line(x="matchday", y="position", by="team", color=GREY, line_width=1.5,
                              alpha=0.6, legend=False, responsive=True, **tips)
    if not focus.empty:
        plot = plot * focus.hvplot.line(x="matchday", y="position", color=ACCENT, line_width=5,
                                        responsive=True, **tips)
        plot = plot * focus.hvplot.scatter(x="matchday", y="position", color=ACCENT, size=90,
                                           responsive=True, **tips)
    cut = (hv.HLine(8.5) * hv.HLine(24.5)).opts(hv.opts.HLine(color=REF, line_dash="dashed"))
    zones = hv.Labels({"x": [matchdays[0]] * 3, "y": [4.5, 16.5, 30.5],
                       "text": ["  TOP 8 → R16", "  9–24 → PLAY-OFFS", "  25+ → OUT"]},
                      ["x", "y"], "text").opts(text_font_size="8pt", text_color=REF,
                                               text_align="left")
    note = "" if not focus.empty else f" — {team} did not play"
    return (plot * cut * zones).opts(
        title=f"How did the table move? {season}{note}",
        xlabel="League matchday", ylabel="Table position (1 = top)", invert_yaxis=True,
        xticks=list(range(matchdays[0], matchdays[1] + 1)), yticks=[1, 8, 16, 24, 36],
        ylim=(0, 37), height=440, show_legend=False, **CHART_OPTS)


def q2_strip(team, on_select):
    df = d.q2_outcomes.copy()
    offset = {d.Q2_SEASONS[0]: -0.15, d.Q2_SEASONS[-1]: 0.15}
    markers = {d.Q2_SEASONS[0]: "circle", d.Q2_SEASONS[-1]: "triangle"}
    df["y"] = df["round_idx"] + df["season"].map(offset)
    tips = dict(hover_cols=["team", "season", "position_md4", "furthest"],
                hover_tooltips=[("Team", "@team"), ("Season", "@season"),
                                ("Position after MD4", "@position_md4"),
                                ("Furthest round", "@furthest")])
    layers = []
    for season, marker in markers.items():
        s = df[df["season"].eq(season) & df["team"].ne(team)]
        layers.append(clickable(s.hvplot.scatter(
            x="position_md4", y="y", color=GREY, marker=marker, size=80, label=season,
            responsive=True, **tips), s, on_select))
    for season, marker in markers.items():
        s = df[df["season"].eq(season) & df["team"].eq(team)]
        if not s.empty:
            layers.append(s.hvplot.scatter(x="position_md4", y="y", color=ACCENT, marker=marker,
                                           size=200, line_color="white", responsive=True, **tips))
    cut = (hv.VLine(8.5) * hv.VLine(24.5)).opts(hv.opts.VLine(color=REF, line_dash="dashed"))
    return hv.Overlay(layers + [cut]).opts(
        title="Does an early top-8 spot lead to a deep run? (2024-25 ● and 2025-26 ▲)",
        xlabel="Table position after matchday 4", ylabel="Furthest round reached",
        yticks=list(enumerate(d.Q2_ROUNDS)), xticks=[1, 8, 16, 24, 36], xlim=(0, 37),
        ylim=(-0.6, len(d.Q2_ROUNDS) - 0.4), height=440, legend_position="bottom_right",
        **CHART_OPTS)


# --- Q3 Countries ----------------------------------------------------------------------
Q3_METRICS = {"Points per match": "points_per_match", "Average Elo": "mean_elo",
              "Win rate": "win_rate", "Clubs in R16": "clubs_in_r16"}


def q3_heatmap(metric_label, team, countries):
    metric = Q3_METRICS[metric_label]
    df = d.country_season[d.country_season["league_country"].isin(
        countries or d.Q3_DEFAULT_COUNTRIES)].copy()
    df["value"] = df[metric].round(0 if metric == "mean_elo" else 2)
    order = df.groupby("league_country")["value"].mean().sort_values().index.tolist()
    played = d.team_matches.loc[d.team_matches["team"].eq(team), ["league_country", "season"]]
    df = df.merge(played.drop_duplicates().assign(is_team=True), how="left")
    df["is_team"] = df["is_team"].fillna(False).astype(bool)
    fmt = {"win_rate": "{:.0%}", "mean_elo": "{:.0f}", "clubs_in_r16": "{:.0f}"}.get(metric, "{:.2f}")
    df["text"] = df["value"].map(fmt.format)

    kdims = [hv.Dimension("season", label="Season"), hv.Dimension("league_country", label="Country")]
    vdims = [hv.Dimension("value", label=metric_label), hv.Dimension("clubs", label="Clubs"),
             hv.Dimension("matches", label="Matches"), hv.Dimension("titles", label="Titles")]
    heat = hv.HeatMap(df, kdims, vdims).redim.values(league_country=order).opts(
        cmap=HEAT_CMAP, colorbar=True, tools=["hover"], line_color="#060a18", line_width=3,
        clabel=metric_label)
    plain = hv.Labels(df[~df["is_team"]], kdims, "text").opts(text_font_size="9pt", text_color="white")
    mark = hv.Labels(df[df["is_team"]], kdims, "text").opts(
        text_font_size="11pt", text_color="#06101f", text_font_style="bold")
    ring = hv.Points(df[df["is_team"]], kdims).opts(marker="square", size=34, fill_alpha=0.9,
                                                    color=ACCENT, line_color="white")
    return (heat * plain * ring * mark).opts(
        title=f"Which leagues send the strongest clubs? {metric_label} by season",
        xlabel="Season (2026-27 in progress)", ylabel="", height=max(340, 46 * len(order) + 110),
        **CHART_OPTS)


# --- Q4 Title odds --------------------------------------------------------------------
Q4_STAGES = {"Win the title": "p_win", "Reach the final": "p_final", "Reach the semis": "p_sf",
             "Reach the quarters": "p_qf", "Reach the Round of 16": "p_r16",
             "Finish top 8": "p_top8", "Reach the knockouts": "p_knockouts"}
_sim = d.simulation.assign(**{c.replace("p_", "pct_"): (d.simulation[c] * 100).round(1)
                              for c in Q4_STAGES.values()})


def q4_bars(stage, team, top_n=16):
    col = Q4_STAGES[stage].replace("p_", "pct_")
    df = pd.concat([_sim.nlargest(top_n, col), _sim[_sim["team"].eq(team)]])
    df = df.drop_duplicates("team").sort_values(col)
    df["colour"] = np.where(df["team"].eq(team), ACCENT, GREY)
    tips = [("Team", "@team"), ("Points now", "@points")] + [
        (k, f"@{v.replace('p_', 'pct_')}{{0.0}}%") for k, v in Q4_STAGES.items()]
    return df.hvplot.barh(x="team", y=col, color="colour", line_color=None, responsive=True,
                          hover_cols=["points", *[v.replace("p_", "pct_") for v in Q4_STAGES.values()]],
                          hover_tooltips=tips).opts(
        title=f"Chance to {stage.lower()} (% of 10,000 simulated seasons)",
        xlabel="", ylabel="Probability (%)", height=max(360, 26 * len(df) + 100), **CHART_OPTS)


ROAD = [("Knockouts", "p_knockouts"), ("Round of 16", "p_r16"), ("Quarters", "p_qf"),
        ("Semis", "p_sf"), ("Final", "p_final"), ("Champion", "p_win")]


def q4_road(team):
    """Road to the final: chance of reaching each stage, focus team vs the favourite."""
    fav = d.simulation.iloc[0]["team"]
    if team not in set(d.simulation["team"]):
        return message(f"{team} is not in the {d.CURRENT_SEASON} Champions League.")
    rows = []
    for t in dict.fromkeys([team, fav]):               # keeps order, drops duplicate
        r = d.simulation.set_index("team").loc[t]
        rows += [{"team": t, "stage": s, "pct": round(r[c] * 100, 1)} for s, c in ROAD]
    df = pd.DataFrame(rows)
    plots = []
    for t, colour in zip(dict.fromkeys([team, fav]), [ACCENT, GOLD]):
        sub = df[df["team"].eq(t)]
        plots.append(hv.Area(sub, "stage", "pct").opts(color=colour, alpha=0.12, line_alpha=0))
        plots.append(hv.Curve(sub, "stage", "pct", label=t).opts(color=colour, line_width=3))
        plots.append(hv.Scatter(sub, "stage", ["pct", "team"]).opts(
            color=colour, size=10, tools=["hover"],
            hover_tooltips=[("Team", "@team"), ("Stage", "@stage"), ("Chance", "@pct{0.0}%")]))
    return hv.Overlay(plots).opts(
        title=f"Road to the final: {team}" + (f" vs favourite {fav}" if team != fav else " (favourite)"),
        xlabel="", ylabel="Chance to reach (%)", ylim=(0, 105), height=360,
        legend_position="top_right", **CHART_OPTS)


# --- Head-to-head ------------------------------------------------------------------------
def h2h_elo(team_a, team_b):
    df = d.elo_history[d.elo_history["team"].isin([team_a, team_b])]
    plots = [hv.HLine(1500).opts(color=REF, line_dash="dotted", line_width=1)]
    for t, colour in [(team_a, ACCENT), (team_b, GOLD)]:
        sub = df[df["team"].eq(t)].sort_values("date")
        if sub.empty:
            continue
        plots.append(sub.hvplot.step(x="date", y="elo_after", color=colour, line_width=3, label=t,
                                     where="post", responsive=True, hover_cols=["team", "season", "opponent"],
                                     hover_tooltips=[("Team", "@team"), ("Season", "@season"),
                                                     ("Elo", "@elo_after{0}"), ("Opponent", "@opponent")]))
    return hv.Overlay(plots).opts(
        title="Elo rating over time (every UCL match since 2021-22; 1500 = starting rating)",
        xlabel="Date", ylabel="Elo rating", height=380, legend_position="top_left", **CHART_OPTS)
