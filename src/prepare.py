"""Full data pipeline: data/raw/  ->  data/processed/*.parquet

Run:  python src/prepare.py

Steps (each is one function, narrated in notebooks/01_data_preparation.ipynb):
  1. load_openfootball   2021-22 .. 2025-26 matches (parsed text files)
  2. load_footballdata   2026-27 matches (JSON, incl. not-yet-played fixtures)
  3. combine             one `matches` table, canonical team & country names
  4. to_team_matches     reshape: one row per team per match (long format)
  5. compute Elo         src/elo.py
  6. league_tables       standings after every league matchday (Q2, bump chart)
  7. season_outcomes     how far each team got each season (Q2, Q3)
  8. standings_2026      current table + Elo (Q1, Q4), checked against the API table
  9. country_season      aggregated by league country x season (Q3)
 10. scorers_2026        current-season top scorers + share of their team's goals
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from elo import compute_elo
from parse_openfootball import parse_all
from team_names import country_from_code, league_country, map_teams

ROOT = Path(__file__).resolve().parents[1]
RAW_FD = ROOT / "data" / "raw" / "footballdata"
OUT = ROOT / "data" / "processed"
CURRENT_SEASON = "2026-27"

# Knockout progress, in order. Used to find each team's furthest round.
ROUND_ORDER = ["League phase", "Group stage", "Knockout playoffs",
               "Round of 16", "Quarterfinals", "Semifinals", "Final", "Winner"]


def _read_json(name: str) -> dict:
    return json.loads((RAW_FD / name).read_text(encoding="utf-8"))


# 1 -----------------------------------------------------------------------------
def load_openfootball() -> pd.DataFrame:
    df = parse_all()
    df["status"] = "FINISHED"          # historical seasons: all matches played
    df["source"] = "openfootball"
    return df


# 2 -----------------------------------------------------------------------------
def load_footballdata() -> pd.DataFrame:
    """2026-27 league phase. Unplayed matches keep NaN goals (status TIMED)."""
    rows = []
    for m in _read_json("cl_2026_matches.json")["matches"]:
        if m["stage"] != "LEAGUE_STAGE":
            raise ValueError(f"Unexpected stage {m['stage']}: extend load_footballdata()")
        ft, ht = m["score"]["fullTime"], m["score"]["halfTime"]
        rows.append({
            "season": CURRENT_SEASON, "stage": "League", "round": f"Matchday {m['matchday']}",
            "group": None, "matchday": m["matchday"],
            # utcDate -> calendar date. UCL kick-offs are 16:45-20:00 UTC, so the
            # UTC date equals the local (CET) date used by openfootball.
            "date": pd.to_datetime(m["utcDate"]).tz_localize(None).normalize(),
            "home_team": m["homeTeam"]["name"], "away_team": m["awayTeam"]["name"],
            "home_goals": ft["home"], "away_goals": ft["away"],
            "home_goals_ht": ht["home"], "away_goals_ht": ht["away"],
            "status": m["status"], "source": "football-data.org",
        })
    df = pd.DataFrame(rows)
    # Country comes from the teams file (area.name), not from the matches file.
    country = {t["name"]: t["area"]["name"] for t in _read_json("cl_2026_teams.json")["teams"]}
    df["home_country"] = df["home_team"].map(country)
    df["away_country"] = df["away_team"].map(country)
    # League-phase matches are all 90 minutes: no extra time or penalties.
    df["home_goals_90"], df["away_goals_90"] = df["home_goals"], df["away_goals"]
    df["extra_time"] = False
    df["home_pens"] = df["away_pens"] = pd.NA
    return df


# 3 -----------------------------------------------------------------------------
def combine(of: pd.DataFrame, fd: pd.DataFrame) -> pd.DataFrame:
    """One matches table with canonical names. map_teams raises on unknown names."""
    of = of.copy()
    of["home_country"] = of["home_country"].map(country_from_code)
    of["away_country"] = of["away_country"].map(country_from_code)
    df = pd.concat([of, fd], ignore_index=True)
    df["home_team"] = map_teams(df["home_team"])
    df["away_team"] = map_teams(df["away_team"])

    int_cols = ["matchday", "home_goals", "away_goals", "home_goals_90", "away_goals_90",
                "home_goals_ht", "away_goals_ht", "home_pens", "away_pens"]
    df[int_cols] = df[int_cols].astype("Int64")       # nullable: unplayed / no HT given
    df["date"] = pd.to_datetime(df["date"])
    df["extra_time"] = df["extra_time"].astype(bool)
    df["neutral"] = df["round"].eq("Final")           # only the final is at a neutral venue
    df["played"] = df["status"].eq("FINISHED")
    return df.sort_values(["date", "season"], kind="stable").reset_index(drop=True)


# 4 -----------------------------------------------------------------------------
def to_team_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Reshape wide (home/away columns) -> long (one row per team per match).
    Makes per-team questions ("how many points has X?") a simple groupby."""
    played = matches[matches["played"]]
    sides = []
    for side, other in [("home", "away"), ("away", "home")]:
        sides.append(pd.DataFrame({
            "season": played["season"], "stage": played["stage"], "round": played["round"],
            "matchday": played["matchday"], "date": played["date"],
            "team": played[f"{side}_team"], "opponent": played[f"{other}_team"],
            "country": played[f"{side}_country"], "venue": side,
            "goals_for": played[f"{side}_goals"], "goals_against": played[f"{other}_goals"],
        }))
    tm = pd.concat(sides, ignore_index=True)
    tm["league_country"] = tm["country"].map(league_country)
    tm["goal_diff"] = tm["goals_for"] - tm["goals_against"]
    # Result after extra time; a shoot-out counts as a draw (as in official UEFA stats).
    tm["result"] = np.select([tm["goal_diff"] > 0, tm["goal_diff"] < 0], ["W", "L"], "D")
    tm["points"] = tm["result"].map({"W": 3, "D": 1, "L": 0}).astype("int64")
    return tm.sort_values(["date", "team"]).reset_index(drop=True)


# 6 -----------------------------------------------------------------------------
def league_tables(team_matches: pd.DataFrame) -> pd.DataFrame:
    """Cumulative league-phase table after each matchday (36-team format only).

    Ranking: points, goal difference, goals scored, away goals scored, wins.
    These are UEFA's first five tie-breakers; the rest (opponents' points etc.)
    are rarely needed, so a remaining tie is broken alphabetically. The result is
    verified against the official API table in standings_2026().
    """
    lg = team_matches[team_matches["stage"].eq("League")].copy()
    lg["away_goals_for"] = lg["goals_for"].where(lg["venue"].eq("away"), 0)
    lg["won"] = lg["result"].eq("W").astype(int)
    lg = lg.sort_values(["season", "team", "matchday"])

    stats = ["points", "goal_diff", "goals_for", "away_goals_for", "won"]
    cum = lg.groupby(["season", "team"])[stats].cumsum()
    table = pd.concat([lg[["season", "team", "league_country", "matchday"]], cum], axis=1)
    table["played"] = table.groupby(["season", "team"]).cumcount() + 1

    table = table.sort_values(["season", "matchday", *stats, "team"],
                              ascending=[True, True, False, False, False, False, False, True])
    table["position"] = table.groupby(["season", "matchday"]).cumcount() + 1

    # Every team plays once per matchday, so each (season, matchday) must have 36 rows.
    sizes = table.groupby(["season", "matchday"]).size()
    assert (sizes == 36).all(), f"Incomplete matchday tables:\n{sizes[sizes != 36]}"
    return table.reset_index(drop=True)


# 7 -----------------------------------------------------------------------------
def season_outcomes(matches: pd.DataFrame, team_matches: pd.DataFrame,
                    tables: pd.DataFrame) -> pd.DataFrame:
    """Furthest round reached by every team in every season.

    Who advanced from a two-legged tie is NOT recomputed from aggregates:
    a team that plays in the next round has, by definition, advanced. Only the
    winner of the (single-match) final needs a rule: goals, then penalties.
    """
    first_stage = {"League": "League phase", "Group": "Group stage"}
    out = (team_matches.groupby(["season", "team", "country", "league_country"])["stage"]
           .first().map(first_stage).rename("furthest").reset_index())

    rank = {r: i for i, r in enumerate(ROUND_ORDER)}
    ko = team_matches[team_matches["stage"].isin(["Playoffs", "Finals"])].copy()
    ko["round_name"] = ko["round"].where(ko["stage"].eq("Finals"), "Knockout playoffs")
    furthest_ko = (ko.assign(r=ko["round_name"].map(rank))
                   .groupby(["season", "team"])["r"].max())

    finals = matches[matches["round"].eq("Final") & matches["played"]]
    for f in finals.itertuples():
        home_wins = (f.home_goals, f.home_pens if f.extra_time else 0) > \
                    (f.away_goals, f.away_pens if f.extra_time else 0)
        furthest_ko[(f.season, f.home_team if home_wins else f.away_team)] = rank["Winner"]

    idx = out.set_index(["season", "team"]).index
    ko_rank = furthest_ko.reindex(idx).to_numpy()
    out["furthest"] = np.where(pd.isna(ko_rank), out["furthest"],
                               [ROUND_ORDER[int(r)] if not pd.isna(r) else None for r in ko_rank])
    out["furthest"] = pd.Categorical(out["furthest"], categories=ROUND_ORDER, ordered=True)

    # Binary "reached X" flags make Q2 a simple mean (= share of teams).
    for col, rnd in [("reached_r16", "Round of 16"), ("reached_qf", "Quarterfinals"),
                     ("reached_sf", "Semifinals"), ("reached_final", "Final"),
                     ("won_title", "Winner")]:
        out[col] = out["furthest"] >= rnd
    out["season_complete"] = out["season"].ne(CURRENT_SEASON)

    # League-format seasons: add position after MD4 (early form) and final position.
    pos = tables.pivot_table(index=["season", "team"], columns="matchday", values="position")
    out = out.merge(pos[[4]].rename(columns={4: "position_md4"}), on=["season", "team"], how="left")
    if 8 in pos.columns:
        out = out.merge(pos[[8]].rename(columns={8: "position_final"}),
                        on=["season", "team"], how="left")
    out[["position_md4", "position_final"]] = out[["position_md4", "position_final"]].astype("Int64")
    return out


# 8 -----------------------------------------------------------------------------
def standings_2026(tables: pd.DataFrame, elo_now: pd.Series) -> pd.DataFrame:
    """Current table + Elo. Our computed table is checked against the API's."""
    latest_md = tables.loc[tables["season"].eq(CURRENT_SEASON), "matchday"].max()
    ours = tables[tables["season"].eq(CURRENT_SEASON) & tables["matchday"].eq(latest_md)].copy()

    api = next(t for t in _read_json("cl_2026_standings.json")["standings"] if t["type"] == "TOTAL")
    api = pd.DataFrame([{"team": r["team"]["name"], "api_position": r["position"],
                         "api_points": r["points"], "form": r["form"]} for r in api["table"]])
    api["team"] = map_teams(api["team"])
    ours = ours.merge(api, on="team", how="outer", validate="1:1")

    assert (ours["points"] == ours["api_points"]).all(), "Our points differ from the API table"
    mismatch = ours[ours["position"] != ours["api_position"]]
    if not mismatch.empty:  # only possible on deeper tie-breakers; report, don't hide
        print(f"NOTE: {len(mismatch)} positions differ from API (tie-breaks); using API positions:")
        print(mismatch[["team", "points", "goal_diff", "position", "api_position"]].to_string())
    ours["position"] = ours["api_position"]

    ours["elo"] = ours["team"].map(elo_now)
    ours["elo_rank"] = ours["elo"].rank(ascending=False, method="min").astype(int)
    # Positive = table position better than Elo suggests ("over-performing").
    ours["rank_gap"] = ours["elo_rank"] - ours["position"]
    cols = ["position", "team", "league_country", "played", "points", "goal_diff",
            "goals_for", "won", "form", "elo", "elo_rank", "rank_gap"]
    return ours[cols].sort_values("position").reset_index(drop=True)


# 9 -----------------------------------------------------------------------------
def country_season(team_matches: pd.DataFrame, outcomes: pd.DataFrame,
                   elo_hist: pd.DataFrame) -> pd.DataFrame:
    """Strength of each national league per season (Q3)."""
    elo_end = (elo_hist.sort_values("date").groupby(["season", "team"])["elo_after"].last()
               .rename("elo_end").reset_index())
    teams = outcomes.merge(elo_end, on=["season", "team"], how="left")

    per_team = teams.groupby(["league_country", "season"]).agg(
        clubs=("team", "nunique"),
        mean_elo=("elo_end", "mean"),
        best_elo=("elo_end", "max"),
        clubs_in_r16=("reached_r16", "sum"),
        clubs_in_qf=("reached_qf", "sum"),
        titles=("won_title", "sum"),
    )
    per_match = team_matches.groupby(["league_country", "season"]).agg(
        matches=("result", "size"),
        win_rate=("result", lambda r: (r == "W").mean()),
        points_per_match=("points", "mean"),
        goal_diff_per_match=("goal_diff", "mean"),
    )
    out = per_team.join(per_match).reset_index()
    out["season_complete"] = out["season"].ne(CURRENT_SEASON)
    return out


# 10 ----------------------------------------------------------------------------
def scorers_2026(standings: pd.DataFrame) -> pd.DataFrame:
    """Current-season top scorers (football-data.org, top 100 by goals).

    Cleaning decisions:
    - assists / penalties are null when the player has none -> filled with 0
      (null here means "zero", not "unknown": every player with an assist has a number).
    - goal_share = player's goals / team's goals from OUR match table, so both
      numbers cover the same matchdays. Own goals scored for the team stay in the
      team total, which is why shares of one team don't add up to 100%.
    - Context only: these numbers are NOT used by the title model (src/simulate.py),
      because goals are already part of the results that Elo is built from.
    """
    raw = _read_json("cl_2026_scorers.json")
    df = pd.DataFrame([{
        "player": s["player"]["name"],
        "position": s["player"].get("section") or s["player"].get("position"),
        "nationality": s["player"].get("nationality"),
        "team": s["team"]["name"],
        "played": s["playedMatches"],
        "goals": s["goals"], "assists": s["assists"], "penalties": s["penalties"],
    } for s in raw["scorers"]])
    df["team"] = map_teams(df["team"])
    df[["assists", "penalties"]] = df[["assists", "penalties"]].fillna(0)
    df[["played", "goals", "assists", "penalties"]] = df[["played", "goals", "assists",
                                                          "penalties"]].astype("int64")
    df["goal_contributions"] = df["goals"] + df["assists"]

    team_goals = standings.set_index("team")["goals_for"]
    df["team_goals"] = df["team"].map(team_goals)
    assert df["team_goals"].notna().all(), "scorer's team missing from the 2026 table"
    assert (df["goals"] <= df["team_goals"]).all(), "player has more goals than his team"
    df["goal_share"] = df["goals"] / df["team_goals"]
    df["team_rank"] = df.groupby("team")["goals"].rank(ascending=False, method="first").astype(int)
    return df.sort_values(["goals", "assists"], ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------------------
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matches = combine(load_openfootball(), load_footballdata())
    team_matches = to_team_matches(matches)
    elo_hist = compute_elo(matches[matches["played"]])
    elo_now = elo_hist.sort_values("date").groupby("team")["elo_after"].last()
    tables = league_tables(team_matches)
    outcomes = season_outcomes(matches, team_matches, tables)
    standings = standings_2026(tables, elo_now)
    countries = country_season(team_matches, outcomes, elo_hist)

    outputs = {"matches": matches, "team_matches": team_matches, "elo_history": elo_hist,
               "league_tables": tables, "season_outcomes": outcomes,
               "standings_2026": standings, "country_season": countries,
               "scorers_2026": scorers_2026(standings)}
    for name, df in outputs.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name:16s} {len(df):5d} rows -> data/processed/{name}.parquet")


if __name__ == "__main__":
    main()
