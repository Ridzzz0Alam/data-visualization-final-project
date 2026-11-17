"""Monte Carlo title-probability model for UCL 2026-27 (Q4). A MODEL, not a forecast.

Run:  python src/simulate.py   ->  data/processed/simulation_2026.parquet

Idea: play the rest of the season 10,000 times with random results whose odds
come from Elo ratings, and count how often each team reaches each stage.

Assumptions (keep them in mind when reading the numbers):
 1. Strength = our current Elo rating, frozen (not updated during a simulated season).
 2. One match: expected score E = P(win) + 0.5 * P(draw) from the Elo formula
    (home side +50). Draw probability = historical UCL league/group draw rate
    (measured from our data, ~16.5%), so P(win) = E - draw/2, P(loss) = 1 - E - draw/2.
 3. League table after MD8: points, then current goal difference, then random.
    (Goals in simulated matches are not modelled — keeps the model simple.)
 4. Knockouts, simplified fixed bracket: play-offs 9 v 24, 10 v 23, ... 16 v 17;
    R16: seed k (1-8) v winner of play-off (17-k) v (16+k), i.e. 1 v [16/17] ...
    8 v [9/24]; later rounds follow a standard seeded bracket. UEFA's real draw is partly random.
 5. A two-legged tie or the final is won with probability E (no home advantage:
    both teams host once / the final is neutral).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from elo import HOME_ADVANTAGE, expected_score

DATA = Path(__file__).resolve().parents[1] / "data" / "processed"
SEASON = "2026-27"
N_SIMS = 10_000
SEED = 2027          # fixed seed: the same numbers every run (reproducible)


def draw_rate(matches: pd.DataFrame) -> float:
    """Share of draws in all played league/group matches (2021-22 onwards)."""
    m = matches[matches["played"] & matches["stage"].isin(["League", "Group"])]
    return float((m["home_goals"] == m["away_goals"]).mean())


def simulate_league(standings, fixtures, p_draw, rng):
    """Final table of every simulation, both shape (N_SIMS, 36):
    order[s, place] = team index at that place; ranks[s, team] = 0-based place."""
    teams = standings["team"].tolist()
    idx = {t: i for i, t in enumerate(teams)}
    elo = standings["elo"].to_numpy()
    points = np.tile(standings["points"].to_numpy(dtype=float), (N_SIMS, 1))

    for f in fixtures.itertuples():
        h, a = idx[f.home_team], idx[f.away_team]
        e = expected_score(elo[h] + HOME_ADVANTAGE, elo[a])
        p_home = max(e - p_draw / 2, 0.0)
        u = rng.random(N_SIMS)                       # one random number per simulation
        home_win, draw = u < p_home, (u >= p_home) & (u < p_home + p_draw)
        points[:, h] += 3 * home_win + draw
        points[:, a] += 3 * ~(home_win | draw) + draw

    # Sort key: points, then current goal difference (scaled < 1 point), then random.
    gd = standings["goal_diff"].to_numpy()
    key = points + (gd - gd.min()) / 1000 + rng.random(points.shape) / 1e6
    order = np.argsort(-key, axis=1)                 # order[s, place] = team index
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order, np.arange(36)[None, :].repeat(N_SIMS, 0), axis=1)
    return order, ranks


def play_ties(a: np.ndarray, b: np.ndarray, elo: np.ndarray, rng) -> np.ndarray:
    """Vectorised knockout ties: team-index arrays a, b -> winners."""
    p_a = expected_score(elo[a], elo[b])             # neutral: no home advantage
    return np.where(rng.random(len(a)) < p_a, a, b)


def simulate(matches: pd.DataFrame, standings: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    standings = standings.reset_index(drop=True)
    fixtures = matches[matches["season"].eq(SEASON) & ~matches["played"]]
    p_draw = draw_rate(matches)
    elo = standings["elo"].to_numpy()

    order, ranks = simulate_league(standings, fixtures, p_draw, rng)
    seed = lambda k: order[:, k - 1]                 # team index at place k (1-based)

    reached = {s: np.zeros((N_SIMS, 36), bool) for s in ["r16", "qf", "sf", "final", "win"]}
    rows = np.arange(N_SIMS)

    # Play-offs: place (17-k) v place (16+k), i.e. 16 v 17 (k=1) ... 9 v 24 (k=8).
    # Its winner meets seed k in the R16, so the best seed gets the weakest path.
    po_winner = {k: play_ties(seed(17 - k), seed(16 + k), elo, rng) for k in range(1, 9)}
    bracket = [1, 8, 4, 5, 2, 7, 3, 6]               # adjacent ties meet in the next round
    alive = []
    for k in bracket:
        top, other = seed(k), po_winner[k]
        reached["r16"][rows, top] = reached["r16"][rows, other] = True
        alive.append(play_ties(top, other, elo, rng))

    for stage in ["qf", "sf", "final"]:
        for t in alive:
            reached[stage][rows, t] = True
        alive = [play_ties(alive[i], alive[i + 1], elo, rng) for i in range(0, len(alive), 2)]
    reached["win"][rows, alive[0]] = True

    out = standings[["position", "team", "league_country", "points", "elo"]].copy()
    out["p_top8"] = (ranks < 8).mean(axis=0)
    out["p_knockouts"] = (ranks < 24).mean(axis=0)
    for s, hit in reached.items():
        out[f"p_{s}"] = hit.mean(axis=0)
    out.attrs["draw_rate"] = p_draw
    return out.sort_values("p_win", ascending=False).reset_index(drop=True)


def main() -> None:
    result = simulate(pd.read_parquet(DATA / "matches.parquet"),
                      pd.read_parquet(DATA / "standings_2026.parquet"))
    result.to_parquet(DATA / "simulation_2026.parquet", index=False)
    print(f"{N_SIMS} simulations, draw rate {result.attrs['draw_rate']:.3f}, seed {SEED}")
    print("Sums (should be 8, 24, 16, 8, 4, 2, 1):",
          [round(result[c].sum(), 2) for c in
           ["p_top8", "p_knockouts", "p_r16", "p_qf", "p_sf", "p_final", "p_win"]])
    print(result.head(10)[["team", "points", "elo", "p_top8", "p_sf", "p_win"]].round(3).to_string())


if __name__ == "__main__":
    main()
