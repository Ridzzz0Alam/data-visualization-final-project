"""Self-computed Elo ratings from UCL match results (replaces ClubElo, whose API was down).

The Elo idea: every team has a rating. Before a match we compute how likely each
team is to win from the rating gap; afterwards the winner takes points from the
loser — more points if the result was a surprise.

    expected_home = 1 / (1 + 10 ** (-(R_home + HOME_ADVANTAGE - R_away) / 400))
    actual_home   = 1 (win), 0.5 (draw), 0 (loss)
    R_home_new    = R_home + K * (actual_home - expected_home)
    R_away_new    = R_away - K * (actual_home - expected_home)   # zero-sum

Choices (all explained in the notebook):
  * START_RATING = 1500 for every team at its first UCL match.
  * K = 20: how fast ratings react (ClubElo also uses 20).
  * HOME_ADVANTAGE = 50 rating points, added to the home side's rating only when
    computing the expectation. Not applied to the final (neutral venue).
  * Result = score after extra time; a penalty shoot-out counts as a draw
    (the shoot-out says little about which team is stronger).
Limitation: only UCL matches (8-17 per team per season), so ratings are noisier
than ClubElo's, and 2021-22 is a "warm-up" season where everyone starts equal.
"""

from __future__ import annotations

import pandas as pd

START_RATING = 1500.0
K = 20.0
HOME_ADVANTAGE = 50.0


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probability-like expected score of team A against team B (0..1)."""
    return 1.0 / (1.0 + 10 ** (-(rating_a - rating_b) / 400))


def compute_elo(matches: pd.DataFrame, k: float = K, home_advantage: float = HOME_ADVANTAGE,
                start_rating: float = START_RATING) -> pd.DataFrame:
    """Walk through finished matches in date order and update ratings.

    `matches` needs: date, season, home_team, away_team, home_goals, away_goals,
    neutral (bool). Returns one row per team per match (long format):
    date, season, team, opponent, elo_before, elo_after, elo_change, expected.
    """
    ratings: dict[str, float] = {}
    rows = []
    # Stable sort: matches on the same day keep file order (a team never plays twice a day).
    for m in matches.sort_values("date", kind="stable").itertuples(index=False):
        r_home = ratings.get(m.home_team, start_rating)
        r_away = ratings.get(m.away_team, start_rating)

        bonus = 0.0 if m.neutral else home_advantage
        exp_home = expected_score(r_home + bonus, r_away)
        if m.home_goals > m.away_goals:
            actual_home = 1.0
        elif m.home_goals < m.away_goals:
            actual_home = 0.0
        else:
            actual_home = 0.5  # includes matches decided on penalties

        change = k * (actual_home - exp_home)
        ratings[m.home_team] = r_home + change
        ratings[m.away_team] = r_away - change

        for team, opp, before, sign, exp in [
            (m.home_team, m.away_team, r_home, +1, exp_home),
            (m.away_team, m.home_team, r_away, -1, 1 - exp_home),
        ]:
            rows.append({
                "date": m.date, "season": m.season, "team": team, "opponent": opp,
                "elo_before": before, "elo_after": before + sign * change,
                "elo_change": sign * change, "expected": exp,
            })
    return pd.DataFrame(rows)


def latest_ratings(history: pd.DataFrame) -> pd.Series:
    """Most recent rating of every team (index = team)."""
    return history.sort_values("date", kind="stable").groupby("team")["elo_after"].last()
