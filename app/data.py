"""Data layer: loads data/processed/*.parquet once and derives the small tables
and headline facts the dashboard shows. No plotting here."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import panel as pn

DATA = Path(__file__).resolve().parents[1] / "data" / "processed"


@pn.cache  # load once per server process, not once per browser session
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


matches = load("matches")
team_matches = load("team_matches")
elo_history = load("elo_history")
league_tables = load("league_tables")
season_outcomes = load("season_outcomes")
country_season = load("country_season")
standings = load("standings_2026")
simulation = load("simulation_2026")          # src/simulate.py
scorers = load("scorers_2026")                # top 100 scorers, 2026-27 only

SEASONS = sorted(team_matches["season"].unique())
CURRENT_SEASON = SEASONS[-1]
TEAMS = sorted(team_matches["team"].unique())
COUNTRIES = sorted(team_matches["league_country"].unique())
LEAGUE_SEASONS = sorted(league_tables["season"].unique())       # 36-team format
CURRENT_TABLES = league_tables[league_tables["season"].eq(CURRENT_SEASON)]
LATEST_MD = int(CURRENT_TABLES["matchday"].max())                # matchdays played (4)
DRAW_RATE = float(simulation.attrs.get("draw_rate", 0.165))


# --- Q1: points vs Elo ------------------------------------------------------------
def q1_data(matchdays: tuple[int, int]) -> pd.DataFrame:
    """Points/GD won within the matchday range + Elo + points expected from Elo.

    league_tables is cumulative, so points in matchdays a..b = after b - after (a-1).
    'Expected' = least-squares line through all 36 teams (fitted before any filter).
    """
    start, end = matchdays[0], min(matchdays[1], LATEST_MD)
    cum = CURRENT_TABLES.set_index(["matchday", "team"])[["points", "goal_diff"]]
    after_end = cum.loc[end]
    before = cum.loc[start - 1] if start > 1 else after_end * 0
    df = (after_end - before).join(
        standings.set_index("team")[["league_country", "elo", "position"]]).reset_index()
    slope, intercept = np.polyfit(df["elo"], df["points"], deg=1)
    df["expected"] = intercept + slope * df["elo"]
    df["vs_expected"] = (df["points"] - df["expected"]).round(1)     # + = over-performing
    df["elo"] = df["elo"].round(0)
    return df


# --- Q2: MD4 position vs furthest round (completed 36-team seasons) -----------------
Q2_SEASONS = [s for s in LEAGUE_SEASONS if s != CURRENT_SEASON]
Q2_ROUNDS = ["League phase", "Knockout playoffs", "Round of 16", "Quarterfinals",
             "Semifinals", "Final", "Winner"]
q2_outcomes = season_outcomes[season_outcomes["season"].isin(Q2_SEASONS)].copy()
q2_outcomes["furthest"] = q2_outcomes["furthest"].astype(str)
q2_outcomes["round_idx"] = q2_outcomes["furthest"].map(Q2_ROUNDS.index)
q2_outcomes["band"] = pd.cut(q2_outcomes["position_md4"].astype(float), [0, 8, 24, 36],
                             labels=["1–8", "9–24", "25–36"])
Q2_RATES = q2_outcomes.groupby("band", observed=True)[["reached_r16", "reached_sf"]].mean()

# --- Q3: countries ----------------------------------------------------------------------
Q3_MIN_MATCHES = 50
_per_country = country_season.groupby("league_country")["matches"].sum()
Q3_DEFAULT_COUNTRIES = _per_country[_per_country >= Q3_MIN_MATCHES].index.tolist()
_complete = country_season[country_season["season_complete"]
                           & country_season["league_country"].isin(Q3_DEFAULT_COUNTRIES)]
COUNTRY_TOTALS = _complete.groupby("league_country").agg(
    ppm=("points_per_match", "mean"), qf=("clubs_in_qf", "sum"), titles=("titles", "sum"))

# --- Match table (readable) --------------------------------------------------------------
def _score(m) -> str:
    if not m.played:
        return "scheduled"
    s = f"{m.home_goals}–{m.away_goals}"
    if m.extra_time:
        s += " a.e.t."
    if pd.notna(m.home_pens):
        s += f" ({m.home_pens}–{m.away_pens} pens)"
    return s


match_table = pd.DataFrame({
    "Date": matches["date"].dt.date, "Season": matches["season"], "Round": matches["round"],
    "Home": matches["home_team"], "Score": [_score(m) for m in matches.itertuples()],
    "Away": matches["away_team"], "Home country": matches["home_country"],
    "Away country": matches["away_country"],
}).sort_values("Date", ascending=False).reset_index(drop=True)


# --- Team summaries (Overview focus card, Head-to-head) -------------------------------
ELO_NOW = elo_history.sort_values("date").groupby("team")["elo_after"].last()
ELO_RANK = ELO_NOW.rank(ascending=False, method="min").astype(int)


def team_summary(team: str) -> dict:
    """All-time (2021-22 onwards) UCL record of one club."""
    tm = team_matches[team_matches["team"].eq(team)]
    out = season_outcomes[season_outcomes["team"].eq(team)]
    sim = simulation.set_index("team")
    best = out["furthest"].max() if not out.empty else None
    return {
        "team": team,
        "country": tm["league_country"].iloc[0] if not tm.empty else "–",
        "elo": float(ELO_NOW.get(team, np.nan)),
        "elo_rank": int(ELO_RANK.get(team, 0)),
        "seasons": out["season"].nunique(),
        "played": len(tm),
        "won": int(tm["result"].eq("W").sum()), "drawn": int(tm["result"].eq("D").sum()),
        "lost": int(tm["result"].eq("L").sum()),
        "win_rate": tm["result"].eq("W").mean() if len(tm) else np.nan,
        "goals_pm": tm["goals_for"].mean() if len(tm) else np.nan,
        "conceded_pm": tm["goals_against"].mean() if len(tm) else np.nan,
        "titles": int(out["won_title"].sum()),
        "best": str(best) if best is not None else "–",
        "p_win": float(sim["p_win"].get(team, np.nan)),
        "in_current": team in set(standings["team"]),
    }


def match_odds(team_a: str, team_b: str) -> tuple[float, float, float]:
    """Win/draw/loss chance for A vs B on neutral ground, same method as src/simulate.py."""
    e = 1.0 / (1.0 + 10 ** (-(ELO_NOW[team_a] - ELO_NOW[team_b]) / 400))
    p_a = max(e - DRAW_RATE / 2, 0.0)
    p_b = max(1 - e - DRAW_RATE / 2, 0.0)
    return p_a, 1 - p_a - p_b, p_b


# --- Scorers: how much does each team rely on one player? -----------------------------
# One row per 2026-27 team. The API list is the top 100 scorers, so a team whose best
# scorer is not in it has no row in `scorers` -> its share stays NaN (shown as "–").
_top = scorers[scorers["team_rank"].eq(1)].set_index("team")
dependence = (standings[["team", "league_country", "goals_for", "points"]]
              .merge(simulation[["team", "p_win"]], on="team")
              .assign(top_scorer=lambda x: x["team"].map(_top["player"]),
                      top_goals=lambda x: x["team"].map(_top["goals"]),
                      top_share=lambda x: (x["team"].map(_top["goal_share"]) * 100).round(0),
                      title_pct=lambda x: (x["p_win"] * 100).round(1)))


def team_scorers(team: str, n: int = 3) -> pd.DataFrame:
    return scorers[scorers["team"].eq(team)].head(n)


# --- Headline facts (Overview tiles)-------------------------------------------------------
_q1_all = q1_data((1, LATEST_MD))
_leader = standings.iloc[0]
_fav = simulation.iloc[0]
_over = _q1_all.loc[_q1_all["vs_expected"].idxmax()]
_under = _q1_all.loc[_q1_all["vs_expected"].idxmin()]
_played_now = matches[matches["season"].eq(CURRENT_SEASON) & matches["played"]]
_first = matches[matches["season"].eq(SEASONS[0]) & matches["played"]]
_goals_first = (_first["home_goals"] + _first["away_goals"]).mean()

HEADLINES = {
    "leader": (_leader["team"], f"{int(_leader['points'])} pts", "Top of the table"),
    "elo": (ELO_NOW.idxmax(), f"{ELO_NOW.max():.0f}", "Highest Elo rating"),
    "favourite": (_fav["team"], f"{_fav['p_win']:.1%}", "Title favourite (model)"),
    "surprise": (_over["team"], f"+{_over['vs_expected']:.1f}", "Points above Elo expectation"),
    "flop": (_under["team"], f"{_under['vs_expected']:.1f}", "Points below Elo expectation"),
    "goals": (f"up from {_goals_first:.2f} in {SEASONS[0]}",
              f"{(_played_now['home_goals'] + _played_now['away_goals']).mean():.2f}",
              "Goals per match this season"),
}
Q1_OVER, Q1_UNDER = _over, _under
