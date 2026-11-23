"""UEFA Champions League 2026/27 — who are the real contenders?

Run from the project root:
    panel serve app/app.py --show --autoreload

Structure (one tab per topic, one 'focus team' that drives every view):
    data.py    loads data/processed/*.parquet + headline facts
    theme.py   dark 'UCL night' palette, CSS, chart style
    charts.py  one function per chart (testable on its own)
    app.py     this file: widgets, tabs, linking
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))   # so data/theme/charts import when served

import holoviews as hv
import pandas as pd
import panel as pn

import charts as c
import data as d
from theme import (ACCENT, BUTTON_CSS, CARD_BG, CARD_BORDER, CARD_CSS, GOLD, HTML_CSS, MUTED,
                   PAGE_CSS, PLAYER_CSS, SEARCH_CSS, TABS_CSS, TEXT)

pn.extension("tabulator", "plotly", sizing_mode="stretch_width", raw_css=[PAGE_CSS])

TABLE_CSS = f"""
.tabulator {{ background: {CARD_BG}; border: none; font-family: Outfit, sans-serif; font-size: 14px; }}
.tabulator .tabulator-header, .tabulator .tabulator-header .tabulator-col {{
    background: #121c40; color: {MUTED}; border-color: {CARD_BORDER}; }}
.tabulator-row {{ background: {CARD_BG}; color: {TEXT}; border-bottom: 1px solid {CARD_BORDER}; }}
.tabulator-row.tabulator-row-even {{ background: #111a38; }}
.tabulator-row.tabulator-selected {{ background: #0e3a4a !important; box-shadow: inset 4px 0 0 {ACCENT}; }}
.tabulator-row:hover {{ background: #18244d !important; cursor: pointer; }}
.tabulator .tabulator-footer {{ background: #121c40; color: {MUTED}; border-color: {CARD_BORDER}; }}
"""


# --- Small layout helpers ---------------------------------------------------------------
def html(markup: str, **kw) -> pn.pane.HTML:
    return pn.pane.HTML(markup, stylesheets=[HTML_CSS], **kw)


def card(*objects, **kw) -> pn.Column:
    return pn.Column(*objects, stylesheets=[CARD_CSS], **kw)


def intro(question: str, takeaway: str) -> pn.pane.HTML:
    """Top of every tab: the question it answers + a one-line answer from the data."""
    return html(f'<div class="hero"><p>{question}</p></div>'
                f'<div class="takeaway" style="margin-top:10px">{takeaway}</div>')


def fmt_pct(x: float) -> str:
    return "–" if pd.isna(x) else f"{x:.1%}"


# --- The focus team (drives every view) -----------------------------------------------
# Dropdown of all 80 clubs, grouped: this season's 36 first, then the rest (2021-26 only).
TEAM_GROUPS = {
    f"In the {d.CURRENT_SEASON} Champions League": sorted(d.standings["team"]),
    "Other clubs since 2021-22": sorted(set(d.TEAMS) - set(d.standings["team"])),
}
team_w = pn.widgets.Select(name="", groups=TEAM_GROUPS, value="Arsenal", width=240,
                           stylesheets=[SEARCH_CSS])


def set_team(name: str) -> None:
    """Called by clickable charts and the table: makes `name` the focus team."""
    team_w.value = name


# ================================ TAB 1: OVERVIEW ======================================
def headline_tiles() -> str:
    tiles = "".join(
        f'<div class="tile"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{who}</div></div>'
        for who, value, label in d.HEADLINES.values())
    return f'<div class="tiles">{tiles}</div>'


hero = html(
    '<div class="hero"><h1>Who are the real contenders?</h1>'
    f'<p>UEFA Champions League {d.CURRENT_SEASON} · after matchday {d.LATEST_MD} of 8 · '
    'five seasons of history · our own Elo ratings · a 10,000-run title model</p></div>')
tiles = html(headline_tiles())

# Current table; clicking a row makes that team the focus team.
CHIP_COLOURS = {"W": "#34d399", "D": "#94a3b8", "L": "#f87171"}


def form_chips(form: str) -> str:
    """'W,W,D,L' -> coloured squares (inline styles: the table cell has no shared CSS)."""
    return "".join(
        f'<span style="display:inline-block;width:20px;height:20px;line-height:20px;'
        f'text-align:center;border-radius:6px;margin-right:3px;font-weight:800;font-size:11px;'
        f'color:#06101f;background:{CHIP_COLOURS[r]}">{r}</span>'
        for r in form.split(",") if r)


table_df = d.standings.merge(d.simulation[["team", "p_win"]], on="team").assign(
    Form=lambda x: x["form"].fillna("").map(form_chips),
    Title=lambda x: (x["p_win"] * 100).round(1),
    Elo=lambda x: x["elo"].round(0).astype(int),
).rename(columns={"position": "#", "team": "Team", "league_country": "Country", "played": "P",
                  "won": "W", "goal_diff": "GD", "points": "Pts"})[
    ["#", "Team", "Country", "P", "W", "GD", "Pts", "Form", "Elo", "Title"]]

standings_table = pn.widgets.Tabulator(
    table_df, show_index=False, disabled=True, selectable=1, theme="midnight",
    formatters={"Form": {"type": "html"},
                "Title": {"type": "progress", "max": float(table_df["Title"].max()),
                          "color": ACCENT, "legend": True}},
    titles={"Title": "Title %"}, layout="fit_columns", height=560,
    widths={"#": 45, "P": 45, "W": 45, "GD": 55, "Pts": 55, "Elo": 65, "Form": 130},
    stylesheets=[TABLE_CSS],
)
standings_table.on_click(lambda e: set_team(table_df.iloc[e.row]["Team"]))


def _sync_selection(event) -> None:
    """Keep the focus team's row highlighted in the table."""
    standings_table.selection = table_df.index[table_df["Team"].eq(event.new)].tolist()


team_w.param.watch(_sync_selection, "value")
standings_table.selection = table_df.index[table_df["Team"].eq(team_w.value)].tolist()


def focus_card(team: str) -> pn.pane.HTML:
    s = d.team_summary(team)
    row = d.standings.set_index("team").loc[team] if s["in_current"] else None
    chips = ""
    if row is not None and isinstance(row["form"], str):
        chips = '<div class="chips">' + "".join(
            f'<div class="chip {r}">{r}</div>' for r in row["form"].split(",")) + "</div>"
    if row is not None:
        stats = (f'<div><span>Position</span><b>{int(row["position"])}</b></div>'
                 f'<div><span>Points</span><b>{int(row["points"])}</b></div>'
                 f'<div><span>Elo (rank)</span><b>{s["elo"]:.0f} <small>#{s["elo_rank"]}</small></b></div>'
                 f'<div><span>Title chance</span><b style="color:{ACCENT}">{fmt_pct(s["p_win"])}</b></div>')
    else:
        stats = f'<div><span>Status</span><b>Not in {d.CURRENT_SEASON}</b></div>'
    stats += (f'<div><span>UCL record since 2021</span><b>{s["won"]}-{s["drawn"]}-{s["lost"]}</b></div>'
              f'<div><span>Best run</span><b>{s["best"]}</b></div>')
    return html(f'<div class="focus"><div class="label muted">FOCUS TEAM</div><h2>{team}</h2>'
                f'<div class="country">{s["country"]}</div>{chips}'
                f'<div class="stats">{stats}</div></div>')


# ================================ TAB 2: CONTENDERS (Q1) ===============================
q1_md_w = pn.widgets.IntRangeSlider(name="League matchdays", start=1, end=8,
                                    value=(1, d.LATEST_MD), step=1)
q1_country_w = pn.widgets.MultiChoice(name="Countries (empty = all)", options=d.COUNTRIES)

# Animation: Elo race over all 163 match dates (starts on the latest date = today's ratings).
elo_player = pn.widgets.Player(name="Match date", start=0, end=len(d.ELO_DATES) - 1,
                               value=len(d.ELO_DATES) - 1, interval=120, loop_policy="once",
                               show_loop_controls=False, width=420, stylesheets=[PLAYER_CSS])
elo_race = hv.DynamicMap(pn.bind(c.elo_race_frame, elo_player, team_w))

contenders_tab = pn.Column(
    intro("Q1 · Which teams are genuinely strong, and who is over- or under-performing their rating?",
          f"<b>{d.Q1_OVER['team']}</b> has {d.Q1_OVER['vs_expected']:+.1f} points more than its Elo "
          f"rating predicts; <b>{d.Q1_UNDER['team']}</b> has {d.Q1_UNDER['vs_expected']:+.1f}. "
          "Above the dashed line = over-performing. Click any dot to focus that team."),
    pn.Row(q1_md_w, q1_country_w),
    pn.Row(
        card(pn.panel(pn.bind(c.q1_scatter, team_w, q1_country_w, q1_md_w, set_team))),
        card(pn.panel(pn.bind(c.q1_lollipop, team_w, q1_country_w, q1_md_w)),
             width=470),
    ),
    card(elo_player, pn.pane.HoloViews(elo_race)),
    html('<p class="muted">How did today\'s ratings come about? Press ▶ to replay every UCL '
         'match date since September 2021 (or drag the slider). The focus team is highlighted.</p>'),
)

# ================================ TAB 3: EARLY FORM (Q2) ===============================
q2_season_w = pn.widgets.RadioButtonGroup(name="Season", options=d.LEAGUE_SEASONS,
                                          value=d.CURRENT_SEASON, button_type="primary",
                                          button_style="outline", width=330)
# Animation: the Player steps through matchdays 1..8 by itself ("replay the season").
# The chart is a DynamicMap, so each step updates the existing plot instead of redrawing it.
q2_player = pn.widgets.Player(name="Matchday", start=1, end=8, value=8, interval=900,
                              loop_policy="once", show_loop_controls=False, width=330,
                              stylesheets=[PLAYER_CSS])
q2_replay = hv.DynamicMap(pn.bind(c.q2_replay_frame, q2_season_w, team_w, q2_player))

# The champion with the worst position after matchday 4 (the "never write them off" fact).
_w = d.q2_outcomes[d.q2_outcomes["won_title"]].sort_values("position_md4").iloc[-1]
_r = d.Q2_RATES
early_tab = pn.Column(
    intro("Q2 · How well does the table position after matchday 4 predict a deep run?",
          f"Top 8 after matchday 4 → <b>{_r.loc['1–8', 'reached_r16']:.0%}</b> reached the Round of 16 "
          f"and <b>{_r.loc['1–8', 'reached_sf']:.0%}</b> the semis; places 9–24 → "
          f"{_r.loc['9–24', 'reached_r16']:.0%} and {_r.loc['9–24', 'reached_sf']:.0%}. "
          f"But <b>{_w['team']} were {int(_w['position_md4'])}th after matchday 4 in {_w['season']} "
          "— and won the title.</b>"),
    pn.Row(q2_season_w, html('<span class="muted">▶ replay the league phase matchday by '
                             'matchday:</span>', align="center", width=280), q2_player),
    pn.Row(card(pn.pane.HoloViews(q2_replay)),
           card(pn.panel(pn.bind(c.q2_strip, team_w, set_team)))),
    html('<p class="muted">Right chart: the two completed 36-team seasons (72 teams); '
         'click a dot to focus that team.</p>'),
)

# ================================ TAB 4: COUNTRIES (Q3) ================================
q3_metric_w = pn.widgets.RadioButtonGroup(options=list(c.Q3_METRICS), value="Points per match",
                                          button_type="primary", button_style="outline",
                                          width=520)
q3_country_w = pn.widgets.MultiChoice(name="Countries (empty = the 8 biggest)", options=d.COUNTRIES)
_ct = d.COUNTRY_TOTALS
countries_tab = pn.Column(
    intro("Q3 · Which national leagues send the strongest clubs, and how has that changed?",
          f"<b>{_ct['ppm'].idxmax()}</b> clubs earn the most points per match "
          f"({_ct['ppm'].max():.2f}, 2021-26), but <b>{_ct['qf'].idxmax()}</b> sent the most "
          f"quarter-finalists ({int(_ct['qf'].max())}) and won the most titles "
          f"({int(_ct['titles'].max())}). Highlighted cells = seasons the focus team played."),
    pn.Row(q3_metric_w, q3_country_w),
    card(pn.panel(pn.bind(c.q3_heatmap, q3_metric_w, team_w, q3_country_w))),
    html(f'<p class="muted">Default rows: the {len(d.Q3_DEFAULT_COUNTRIES)} countries with at least '
         f'{d.Q3_MIN_MATCHES} UCL matches since 2021-22 (smaller samples are noise). '
         'Monaco counts as France (Ligue 1).</p>'),
)

# ================================ TAB 5: TITLE ODDS (Q4) ===============================
q4_stage_w = pn.widgets.Select(name="Chance to…", options=list(c.Q4_STAGES), value="Win the title",
                               width=260)
_top4 = d.simulation.head(4)
assumptions = pn.Accordion(("Model assumptions — read before trusting the numbers", html(
    '<ul class="muted" style="font-size:14px">'
    '<li>The remaining 72 league matches and the knockouts are played 10,000 times (fixed seed).</li>'
    f'<li>Win/draw/loss odds come from current Elo ratings (home side +50); draw rate '
    f'{d.DRAW_RATE:.1%}, measured from 2021-26 league/group matches.</li>'
    '<li>Ratings stay frozen; league ties are broken by current goal difference.</li>'
    '<li>Fixed bracket: 1st vs winner of 16th/17th … 8th vs winner of 9th/24th — '
    'the real UCL draw is partly random.</li>'
    '<li>It shows what the Elo ratings imply. It is <b>not</b> a prediction.</li></ul>')),
    active=[], stylesheets=[CARD_CSS])
def scorer_cards(team: str) -> pn.pane.HTML:
    """Who scores for the focus team and the model's top 4? (Context, not a model input.)"""
    teams = list(dict.fromkeys([team, *_top4["team"]]))
    if team not in set(d.standings["team"]):
        teams = teams[1:]
    cards = ""
    for t in teams:
        rows = "".join(
            f'<div class="srow"><span>{p.player}</span><b>{p.goals} G · {p.assists} A</b>'
            f'<div class="bar"><div style="width:{p.goal_share:.0%}"></div></div></div>'
            for p in d.team_scorers(t).itertuples()) or '<p class="muted">No player in the top 100.</p>'
        p_win = d.simulation.set_index("team")["p_win"][t]
        cards += (f'<div class="scard{" focus-team" if t == team else ""}">'
                  f'<h4>{t}<span>{p_win:.1%} title</span></h4>{rows}</div>')
    return html('<b>Who scores the goals?</b> <span class="muted">· top 3 scorers; bar = share of '
                f'the team\'s goals (MD 1–{d.LATEST_MD})</span><div class="scards" '
                f'style="margin-top:10px">{cards}</div>')


# 3D chart: ONE Plotly pane whose figure is swapped when the focus team changes (a new pane
# per change would lose the click watcher). Clicking a dot makes that team the focus team.
q4_3d_pane = pn.pane.Plotly(c.q4_3d(team_w.value), config={"displaylogo": False, "responsive": True},
                            height=560, sizing_mode="stretch_width")
team_w.param.watch(lambda e: setattr(q4_3d_pane, "object", c.q4_3d(e.new)), "value")


def _click_3d(event) -> None:
    points = (event.new or {}).get("points") or []
    if points and points[0].get("customdata"):
        set_team(points[0]["customdata"])


q4_3d_pane.param.watch(_click_3d, "click_data")

odds_tab = pn.Column(
    intro("Q4 · Given current standings and Elo ratings, what is each team's chance of winning?",
          "The model sees a four-way race: " +
          ", ".join(f"<b>{r.team}</b> {r.p_win:.0%}" for r in _top4.itertuples()) +
          f" — together {_top4['p_win'].sum():.0%}. Everyone else shares the rest."),
    q4_stage_w,
    pn.Row(card(pn.panel(pn.bind(c.q4_bars, q4_stage_w, team_w))),
           pn.Column(card(pn.panel(pn.bind(c.q4_road, team_w))), assumptions)),
    card(q4_3d_pane),
    card(pn.panel(pn.bind(scorer_cards, team_w))),
    card(pn.panel(pn.bind(c.q4_dependence, team_w, set_team))),
    html('<p class="muted">Player numbers are context only: the model does not use them, because '
         'goals are already part of the results the Elo ratings are built from. Click a dot to '
         'focus that team. Dashed line = median share.</p>'),
)

# ================================ TAB 6: HEAD-TO-HEAD ==================================
team_b_w = pn.widgets.Select(name="Compare with", groups=TEAM_GROUPS,
                             value=d.simulation.iloc[0]["team"], width=260,
                             stylesheets=[SEARCH_CSS])


def meetings(team_a: str, team_b: str) -> pd.DataFrame:
    t = d.match_table
    return t[((t["Home"] == team_a) & (t["Away"] == team_b))
             | ((t["Home"] == team_b) & (t["Away"] == team_a))]


def versus(team_a: str, team_b: str) -> pn.pane.HTML:
    a, b = d.team_summary(team_a), d.team_summary(team_b)
    rows = [  # label, value A, value B, format, higher is better? (None = don't compare)
        ("Elo rating", a["elo"], b["elo"], "{:.0f}", True),
        ("Elo rank", a["elo_rank"], b["elo_rank"], "#{}", False),
        ("UCL matches since 2021", a["played"], b["played"], "{}", True),
        ("Win rate", a["win_rate"], b["win_rate"], "{:.0%}", True),
        ("Goals scored / match", a["goals_pm"], b["goals_pm"], "{:.2f}", True),
        ("Goals conceded / match", a["conceded_pm"], b["conceded_pm"], "{:.2f}", False),
        ("Titles (2021-26)", a["titles"], b["titles"], "{}", True),
        ("Best run", a["best"], b["best"], "{}", None),
        (f"Title chance {d.CURRENT_SEASON}", a["p_win"], b["p_win"], "{:.1%}", True),
    ]
    body = ""
    for label, va, vb, f, higher in rows:
        show = lambda v: "–" if (not isinstance(v, str) and pd.isna(v)) else f.format(v)
        win_a = win_b = ""
        if higher is not None and not (pd.isna(va) or pd.isna(vb)) and va != vb:
            win_a, win_b = ("win", "") if (va > vb) == higher else ("", "win")
        body += (f'<tr><td class="a {win_a}">{show(va)}</td><td class="k">{label}</td>'
                 f'<td class="b {win_b}">{show(vb)}</td></tr>')
    return html(f'<table class="vs"><tr><th class="a">{team_a}</th><th></th>'
                f'<th class="b">{team_b}</th></tr>{body}</table>')


def odds_bar(team_a: str, team_b: str) -> pn.pane.HTML:
    if team_a == team_b:
        return html('<p class="muted">Pick two different teams.</p>')
    pa, pdraw, pb = d.match_odds(team_a, team_b)
    n = int((meetings(team_a, team_b)["Score"] != "scheduled").sum())
    met = (f"They have met <b>{n}</b> time{'s' if n != 1 else ''} in the UCL since 2021-22."
           if n else "They have not met in the UCL since 2021-22.")
    return html(
        f'<div class="takeaway">If <b>{team_a}</b> played <b style="color:{GOLD}">{team_b}</b> on '
        f'neutral ground, our Elo model gives these odds. {met}</div>'
        f'<div class="oddsbar"><div style="width:{pa:.0%};background:{ACCENT}">{team_a} {pa:.0%}</div>'
        f'<div style="width:{pdraw:.0%};background:#94a3b8">Draw {pdraw:.0%}</div>'
        f'<div style="width:{pb:.0%};background:{GOLD}">{team_b} {pb:.0%}</div></div>')


meetings_table = pn.widgets.Tabulator(
    pn.bind(meetings, team_w, team_b_w), show_index=False, disabled=True, theme="midnight",
    layout="fit_data_stretch", height=220, stylesheets=[TABLE_CSS])

h2h_tab = pn.Column(
    html('<div class="hero"><p>Head-to-head · the left team is the focus team (dropdown at the top); '
         'choose the team to compare with here.</p></div>'),
    team_b_w,
    pn.panel(pn.bind(odds_bar, team_w, team_b_w)),
    pn.Row(card(pn.panel(pn.bind(versus, team_w, team_b_w)), width=520),
           card(pn.panel(pn.bind(c.h2h_elo, team_w, team_b_w)))),
    card(html('<b>Past meetings</b>'), meetings_table),
)

# ================================ TAB 7: MATCHES =======================================
all_teams_w = pn.widgets.Checkbox(name="Show every team (not only the focus team)", value=False)


def match_rows(team: str, every: bool) -> pd.DataFrame:
    t = d.match_table
    return t if every else t[t["Home"].eq(team) | t["Away"].eq(team)]


match_tabulator = pn.widgets.Tabulator(
    pn.bind(match_rows, team_w, all_teams_w), show_index=False, disabled=True,
    pagination="local", page_size=15, layout="fit_data_stretch", theme="midnight",
    stylesheets=[TABLE_CSS],
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
def scorer_rows(team: str, every: bool) -> pd.DataFrame:
    t = d.scorers if every else d.scorers[d.scorers["team"].eq(team)]
    return t.assign(share=(t["goal_share"] * 100).round(0))[
        ["player", "team", "position", "nationality", "played", "goals", "assists",
         "penalties", "share"]].rename(columns=str.capitalize).rename(columns={"Share": "% of team goals"})


scorers_tabulator = pn.widgets.Tabulator(
    pn.bind(scorer_rows, team_w, all_teams_w), show_index=False, disabled=True,
    pagination="local", page_size=10, layout="fit_data_stretch", theme="midnight",
    stylesheets=[TABLE_CSS],
    header_filters={"Player": {"type": "input", "func": "like", "placeholder": "search"},
                    "Team": {"type": "input", "func": "like", "placeholder": "search"},
                    "Position": {"type": "list", "valuesLookup": True, "clearable": True},
                    "Nationality": {"type": "input", "func": "like", "placeholder": "search"}},
)
matches_tab = pn.Column(
    html('<div class="hero"><p>Every UCL match 2021-22 → 2026-27 (897). Type in the boxes under '
         'each column header to search.</p></div>'),
    all_teams_w, card(match_tabulator),
    card(html(f'<b>Top scorers {d.CURRENT_SEASON}</b> <span class="muted">· the API\'s top 100; '
              'no free source has player data for past seasons</span>'), scorers_tabulator),
)

# ================================ ASSEMBLE ==============================================
tabs = pn.Tabs(
    ("Overview", pn.Column()),           # filled below: its buttons need `tabs` to exist
    ("Contenders", contenders_tab), ("Early form", early_tab), ("Countries", countries_tab),
    ("Title odds", odds_tab), ("Head-to-head", h2h_tab), ("Matches", matches_tab),
    dynamic=True,                         # only the visible tab is rendered -> fast
    stylesheets=[TABS_CSS],
)


def go_to(index: int, label: str) -> pn.widgets.Button:
    """Button that switches to another tab (easy navigation from the overview)."""
    btn = pn.widgets.Button(name=label, stylesheets=[BUTTON_CSS])
    btn.on_click(lambda e: setattr(tabs, "active", index))
    return btn


tabs[0] = ("Overview", pn.Column(
    hero, tiles,
    pn.Row(
        card(html('<b style="font-size:16px">League phase table</b> '
                  '<span class="muted">· click a row to focus that team</span>'), standings_table),
        pn.Column(
            card(pn.panel(pn.bind(focus_card, team_w))),
            card(html('<b>Explore the questions</b>'),
                 go_to(1, "Q1 · Who beats their rating? →"), go_to(2, "Q2 · Does early form matter? →"),
                 go_to(3, "Q3 · Which leagues rule? →"), go_to(4, "Q4 · Who will win? →"),
                 go_to(5, "Head-to-head →")),
            width=380),
    ),
))

footer = html(
    '<div class="footer">Data: <a href="https://github.com/openfootball/champions-league" target="_blank">'
    'openfootball/champions-league</a> (public domain, 2021-22 → 2025-26) · '
    '<a href="https://www.football-data.org/" target="_blank">football-data.org</a> API v4 (2026-27 matches, standings, teams, top scorers) · '
    'Elo ratings computed from these results (<a href="https://en.wikipedia.org/wiki/Elo_rating_system" '
    'target="_blank">Elo method</a>) · title odds are a Monte Carlo model, not a forecast.</div>')

template = pn.template.FastListTemplate(
    title="UCL 2026/27 · The Real Contenders",
    header=[pn.Row(pn.pane.HTML('<span style="color:#8b95ba;font:600 13px Outfit,sans-serif;'
                                'line-height:40px">FOCUS TEAM</span>', width=90),
                   team_w, width=350, align="center")],
    main=[tabs, footer], main_layout=None, theme="dark",
    # The design is dark-only (all colours in theme.py), so hide the template's light/dark
    # switch, and hide its header spinner that flickers on every recalculation.
    theme_toggle=False, busy_indicator=None,
    accent=ACCENT, header_background="#0a1236", background_color="#060a18",
)
template.servable()
