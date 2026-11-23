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
from theme import TEXT as TEXT_LIGHT
from theme import CARD_BG as CARD_BG_HEX
import plotly.graph_objects as go


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
    # Only the focus team gets a name label: many teams share the same points, so labelling
    # more of them overlaps. The ranking chart next to this one names the outliers; hover
    # shows every team.

    line = hv.Curve(df.sort_values("elo"), "elo", "expected", label="Expected from Elo").opts(
        color=REF, line_dash="dashed", line_width=2)
    grey = clickable(hv.Points(others, **Q1_DIMS).opts(
        color=GREY, size=11, line_color="#0e1530", line_width=1.5), others, on_select)
    accent = hv.Points(focus, **Q1_DIMS).opts(color=ACCENT, size=18, line_color="white",
                                              line_width=2, tools=["hover"])
    labels = hv.Labels(focus, ["elo", "points"], "team").opts(
        text_font_size="10pt", yoffset=0.6, text_color=ACCENT, text_font_style="bold")
    md = f"MD {matchdays[0]}–{min(matchdays[1], d.LATEST_MD)}"
    return (line * grey * accent * labels).opts(
        title=f"Who beats their Elo? Points vs Elo rating ({md})",
        xlabel="Elo rating (rating points)", ylabel=f"Points won ({md})",
        height=460, show_legend=True, legend_position="top_left", padding=0.06, **CHART_OPTS)


def q1_lollipop(team, countries, matchdays):
    """Ranking of over/under-performance: the 8 biggest each way (+ focus team)."""
    if matchdays[0] > d.LATEST_MD:
        return message("No matches in this range yet.")
    df = _filter(d.q1_data(matchdays), countries)
    df = pd.concat([df.nlargest(8, "vs_expected"), df.nsmallest(8, "vs_expected"),
                    d.q1_data(matchdays).query("team == @team")])
    df = df.drop_duplicates("team").sort_values("vs_expected").reset_index(drop=True)
    df["row"] = np.arange(len(df))
    df["colour"] = np.where(df["team"].eq(team), ACCENT, np.where(df["vs_expected"] > 0, "#9aa6d1", GREY))

    stems = hv.Segments(df.assign(zero=0), ["zero", "row", "vs_expected", "row"]).opts(
        color="colour", line_width=3)
    dots = hv.Points(df, ["vs_expected", "row"], ["team", "points", "colour"]).opts(
        color="colour", size=12, tools=["hover"], line_color=None,
        hover_tooltips=[("Team", "@team"), ("Points", "@points"), ("Vs expected", "@vs_expected")])
    zero = hv.VLine(0).opts(color=REF, line_width=1)
    return (stems * dots * zero).opts(
        title="Points above / below Elo expectation",
        xlabel="Points above (+) or below (−) expectation", ylabel="",
        yticks=list(zip(df["row"], df["team"])), height=460, **CHART_OPTS)


# --- Q2 Early form --------------------------------------------------------------------
def q2_strip(team, on_select):
    df = d.q2_outcomes.copy()
    offset = {d.Q2_SEASONS[0]: -0.15, d.Q2_SEASONS[-1]: 0.15}
    markers = {d.Q2_SEASONS[0]: "circle", d.Q2_SEASONS[-1]: "triangle"}
    df["round_pos"] = df["round_idx"] + df["season"].map(offset)
    tips = dict(hover_cols=["team", "season", "position_md4", "furthest"],
                hover_tooltips=[("Team", "@team"), ("Season", "@season"),
                                ("Position after MD4", "@position_md4"),
                                ("Furthest round", "@furthest")])
    layers = []
    for season, marker in markers.items():
        s = df[df["season"].eq(season) & df["team"].ne(team)]
        layers.append(clickable(s.hvplot.scatter(
            x="position_md4", y="round_pos", color=GREY, marker=marker, size=80, label=season,
            responsive=True, **tips), s, on_select))
    for season, marker in markers.items():
        s = df[df["season"].eq(season) & df["team"].eq(team)]
        if not s.empty:
            layers.append(s.hvplot.scatter(x="position_md4", y="round_pos", color=ACCENT, marker=marker,
                                           size=200, line_color="white", responsive=True, **tips))
    cut = (hv.VLine(8.5) * hv.VLine(24.5)).opts(hv.opts.VLine(color=REF, line_dash="dashed"))
    return hv.Overlay(layers + [cut]).opts(
        title="Position after matchday 4 vs furthest round",
        xlabel="Table position after matchday 4", ylabel="Furthest round reached",
        yticks=list(enumerate(d.Q2_ROUNDS)), xticks=[1, 8, 16, 24, 36], xlim=(0, 37),
        ylim=(-0.6, len(d.Q2_ROUNDS) - 0.4), height=440, legend_position="top_right",
        **CHART_OPTS)


def q2_replay_frame(season, team, matchday):
    """One frame of the 'replay the season' bump chart: lines grow up to `matchday`.

    Used inside a DynamicMap, so every frame must have the SAME layers (HoloViews then
    updates the data in place instead of redrawing -> smooth animation). That is why the
    focus layers are drawn even when empty, and the x-axis is fixed at matchdays 1-8.
    """
    df = d.league_tables[d.league_tables["season"].eq(season)]
    md = min(matchday, int(df["matchday"].max()))          # current season: only 4 played
    df = df[df["matchday"].le(md)]
    others, focus = df[df["team"] != team], df[df["team"] == team]
    heads = df[df["matchday"].eq(md)]
    head_focus = heads[heads["team"].eq(team)]

    kd = [hv.Dimension("matchday", label="League matchday"),
          hv.Dimension("position", label="Table position")]
    paths = hv.Path([{"matchday": g["matchday"].to_numpy(), "position": g["position"].to_numpy(),
                      "team": t} for t, g in others.groupby("team")], kd, vdims=["team"]).opts(
        color=GREY, line_width=1.5, alpha=0.55, tools=["hover"])
    line = hv.Curve(focus, kd[0], [kd[1], "team", "points"]).opts(color=ACCENT, line_width=5)
    tips = [("Team", "@team"), ("Position", "@position"), ("Points", "@points")]
    dots = hv.Points(heads, kd, ["team", "points"]).opts(
        color=GREY, size=7, tools=["hover"], hover_tooltips=tips)
    dot = hv.Points(head_focus, kd, ["team", "points"]).opts(
        color=ACCENT, size=16, line_color="white", line_width=2, tools=["hover"], hover_tooltips=tips)
    name = hv.Labels(head_focus.assign(text=head_focus["team"] + "  " + head_focus["position"]
                                       .astype(str) + "."), kd, "text").opts(
        text_color=ACCENT, text_font_style="bold", text_font_size="10pt", text_align="left",
        xoffset=0.18)
    # kdims named explicitly: hv.Text defaults to 'x'/'y', and Panel links the axes of all
    # charts sharing a dimension name (that squashed other charts).
    stamp = hv.Text(9.4, 35.5, f"Matchday {md}", halign="right", valign="bottom",
                    kdims=kd).opts(
        color=REF, text_font_size="22pt", text_alpha=0.5)
    cut = (hv.HLine(8.5) * hv.HLine(24.5)).opts(hv.opts.HLine(color=REF, line_dash="dashed"))
    return (paths * line * dots * dot * name * stamp * cut).opts(
        title=f"Replay the {season} league phase — table position after each matchday",
        xlabel="League matchday", ylabel="Table position (1 = top)", invert_yaxis=True,
        xlim=(0.7, 9.5), ylim=(0, 37), xticks=list(range(1, 9)), yticks=[1, 8, 16, 24, 36],
        height=440, show_legend=False, **CHART_OPTS)


ELO_RACE_N = 12


def elo_race_frame(frame, team):
    """One frame of the Elo race: the 12 highest-rated clubs after match date `frame`.

    Bars are Segments on a numeric y-axis (rank 1..12) with the team name drawn as a label,
    so the axis never changes between frames and the animation stays smooth.
    """
    row = d.ELO_WIDE.iloc[frame].dropna().sort_values(ascending=False)
    top = row.head(ELO_RACE_N).rename("elo").rename_axis("team").reset_index()
    top["rank"] = np.arange(1, len(top) + 1)
    top = top.reindex(range(ELO_RACE_N))                    # early frames: <12 clubs -> pad
    top["rank"] = np.arange(1, ELO_RACE_N + 1)
    top["team"] = top["team"].fillna("")
    top["elo"] = top["elo"].fillna(1400.0)
    top["base"] = 1400.0
    top["colour"] = np.where(top["team"].eq(team), ACCENT, GREY)
    top["text"] = top["team"] + "  " + top["elo"].round(0).astype(int).astype(str)
    top.loc[top["team"].eq(""), "text"] = ""

    # Unique dimension names ('race_*'): the Q1 scatter on the same tab also has an 'elo'
    # axis, and Panel would link the two charts' axes (same lesson as the 'y' dims).
    top = top.rename(columns={"base": "race_base", "elo": "race_elo", "rank": "race_rank"})
    kd = [hv.Dimension("race_elo", label="Elo rating"), hv.Dimension("race_rank", label="Rank")]
    bars = hv.Segments(top, ["race_base", "race_rank", "race_elo", "race_rank"],
                       ["team", "colour"]).opts(color="colour", line_width=18)
    names = hv.Labels(top, kd, "text").opts(
        text_color=TEXT_LIGHT, text_font_size="10pt", text_align="left", xoffset=4)
    rank_now = int((row > row.get(team, -np.inf)).sum()) + 1 if team in row else None
    note = f"{team}: #{rank_now}" if rank_now else f"{team}: not yet in the UCL"
    stamp = hv.Text(1745, 12.4, f"{d.ELO_FRAME_LABEL[frame]}\n{note}",
                    halign="right", valign="bottom", kdims=kd).opts(
        color=REF, text_font_size="12pt")             # named kdims: see q2_replay_frame
    return (bars * names * stamp).opts(
        title="Elo race: the 12 strongest clubs after every UCL match date, 2021 → today",
        xlabel="Elo rating", ylabel="Rank", invert_yaxis=True, xlim=(1400, 1750),
        ylim=(0.3, 12.8), yticks=list(range(1, ELO_RACE_N + 1)), height=470, **CHART_OPTS)


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
    labels = hv.Labels(df[~df["is_team"]], kdims, "text").opts(
        text_font_size="9pt", text_color="white")
    plot = heat * labels
    focus = df[df["is_team"]]
    if not focus.empty:
        # Focus team: same cells drawn again with no fill, only a cyan outline, + bold numbers.
        outline = hv.HeatMap(focus, kdims, vdims).redim.values(league_country=order).opts(
            fill_alpha=0, line_color=ACCENT, line_width=3, colorbar=False, tools=[])
        bold = hv.Labels(focus, kdims, "text").opts(
            text_font_size="10pt", text_color="white", text_font_style="bold")
        plot = plot * outline * bold
    return plot.opts(
        title=f"Which leagues are strongest? {metric_label} by season",
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


def q4_dependence(team, on_select):
    """'One-man team?': team goals vs the share scored by its best scorer.
    Dot size = title chance, so fragile contenders (big dot, high share) stand out."""
    df = d.dependence.dropna(subset=["top_share"]).reset_index(drop=True)
    df["dot"] = 8 + df["title_pct"] * 1.6           # px; 0% -> 8px, 16% -> ~34px
    dims = dict(kdims=[hv.Dimension("goals_for", label="Team goals (MD 1–4)"),
                       hv.Dimension("top_share", label="Share by top scorer (%)")],
                vdims=[hv.Dimension("team", label="Team"),
                       hv.Dimension("top_scorer", label="Top scorer"),
                       hv.Dimension("top_goals", label="His goals"),
                       hv.Dimension("title_pct", label="Title chance (%)"), "dot"])
    others, focus = df[df["team"] != team], df[df["team"] == team]
    grey = clickable(hv.Points(others, **dims).opts(
        color=GREY, size="dot", alpha=0.85, line_color="#0e1530", line_width=1.5), others, on_select)
    accent = hv.Points(focus, **dims).opts(color=ACCENT, size="dot", line_color="white",
                                           line_width=2, tools=["hover"])
    labels = hv.Labels(focus, ["goals_for", "top_share"], "top_scorer").opts(
        text_font_size="9pt", text_color=ACCENT, yoffset=7, text_font_style="bold")
    avg = hv.HLine(df["top_share"].median()).opts(color=REF, line_dash="dashed", line_width=1)
    return (grey * accent * labels * avg).opts(
        title="One-man teams? Goals scored vs share from the top scorer (dot size = title chance)",
        xlabel=f"Team goals (matchdays 1–{d.LATEST_MD})",
        ylabel="Share of team goals by its top scorer (%)",
        height=420, padding=0.08, **CHART_OPTS)


def q4_3d(team):
    """3D view (Plotly): Elo rating x points so far x title chance, one dot per team.

    Why 3D here: the title chance depends on BOTH strength (Elo) and results so far (points),
    so the third axis is the outcome of the other two. Drag to rotate; the vertical stems
    show each dot's height, which is hard to judge in 3D otherwise.
    """
    df = d.standings.merge(d.simulation[["team", "p_win"]], on="team")
    df["title_pct"] = (df["p_win"] * 100).round(1)
    df["elo"] = df["elo"].round(0)
    labelled = {team}          # the top 4 sit close together: their labels overlapped; hover names all

    def stems(sub):  # one line per team from z=0 up to the dot; None breaks the line
        xs, ys, zs = [], [], []
        for r in sub.itertuples():
            xs += [r.elo, r.elo, None]; ys += [r.points, r.points, None]; zs += [0, r.title_pct, None]
        return xs, ys, zs

    traces = []
    for sub, colour, size in [(df[df["team"] != team], GREY, 6), (df[df["team"] == team], ACCENT, 11)]:
        xs, ys, zs = stems(sub)
        traces.append(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip",
                                   line=dict(color=colour, width=3 if colour == ACCENT else 2),
                                   showlegend=False))
        traces.append(go.Scatter3d(
            x=sub["elo"], y=sub["points"], z=sub["title_pct"], customdata=sub["team"],
            mode="markers+text", text=[t if t in labelled else "" for t in sub["team"]],
            textposition="top center", textfont=dict(color=colour if colour == ACCENT else TEXT_LIGHT,
                                                     size=12),
            marker=dict(size=size, color=colour, line=dict(color="#0e1530", width=1)),
            hovertemplate="<b>%{customdata}</b><br>Elo %{x:.0f} · %{y} pts<br>"
                          "Title chance %{z:.1f}%<extra></extra>", showlegend=False))

    axis = dict(backgroundcolor=CARD_BG_HEX, gridcolor="#1f2a4d", zerolinecolor="#1f2a4d",
                color="#8b95ba", showspikes=False)
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text="Strength × results × odds: Elo rating, points and title chance in 3D "
                        "(drag to rotate, click a dot to focus)", font=dict(size=14, color=TEXT_LIGHT)),
        paper_bgcolor=CARD_BG_HEX, font=dict(family="Outfit, Segoe UI, sans-serif", color="#8b95ba"),
        margin=dict(l=0, r=0, t=40, b=0), height=560,
        uirevision="keep",                     # keep the user's rotation when the focus team changes
        scene=dict(xaxis=dict(title="Elo rating", **axis), yaxis=dict(title="Points (MD 1–4)", **axis),
                   zaxis=dict(title="Title chance (%)", **axis),
                   aspectmode="manual", aspectratio=dict(x=1.6, y=1.1, z=0.75),
                   camera=dict(eye=dict(x=1.45, y=-1.7, z=0.55), center=dict(x=0, y=0, z=-0.2))),
        autosize=True,
    )
    return fig


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
