# Defense notes

> **DRAFT written with an AI assistant — rewrite every section in your own words before the
> defense.** Check each number by opening the dashboard or the notebook yourself.

## Datasets

- **openfootball/champions-league** (GitHub, public domain): one plain-text file per season,
  2021-22 → 2025-26, 753 matches. Human-readable, not a table → I wrote a parser with regular
  expressions. Problems: dates without a year, 4 score formats, team names that change between
  seasons ("Real Madrid" vs "Real Madrid CF"), two competition formats (groups until 2023-24,
  36-team league from 2024-25).
- **football-data.org API v4** (free tier, JSON): the current 2026-27 season — 144 league-phase
  matches, of which matchdays 1–4 (72) are played, plus the official table and team countries.
  Used because openfootball has no 2026-27 file yet.
- **Elo ratings: computed by me** (`src/elo.py`). The plan was ClubElo, but its API returned
  HTTP 502 for over a week, so I applied the same standard Elo method to my own match data.
- Dropped: FootyStats (match CSV is paywalled).

## Analytical questions → view → key insight

| Q | View | Key insight |
|---|---|---|
| Q1 Contenders | Scatter Elo vs points + least-squares "expected" line | PSG, Real Madrid, Arsenal are strong on both. Over-performers: Club Brugge (+3.9 pts vs expected), Como, Real Betis. Under-performers: Lille (−3.8), **Bayern** (best Elo but only 8 pts, −3.4), Atlético. |
| Q2 Early form | Bump chart + strip plot MD4 position vs furthest round | Top 8 after MD4: 75% reach R16, 31% the semis. Positions 9–24: 56% / 6%. 25–36: 8% / 4%. Early form helps, but **PSG were 25th after MD4 in 2024-25 and won the title.** |
| Q3 Countries | Heatmap country × season with metric toggle | England has the best points per match (1.87, 2021-26), but **Spain** has the most quarter-finalists (12) and titles (2). France: 2 titles, both PSG. Italy fluctuates strongly between seasons. |
| Q4 Title chance | Monte Carlo probability bars | Four clear favourites: PSG 15.9%, Bayern 14.9%, Real Madrid 14.0%, Arsenal 13.6%. Bayern's chance stays high despite few points because the model trusts Elo. |

## Design decisions (and why)

1. **One palette: red = selected team, grey = everyone else, navy = reference lines/headers.**
   The eye goes straight to the selected team in every chart; colour never encodes anything else.
2. **Chart types fit the data:** scatter for two numeric variables (Q1), bump chart for rank over
   time (Q2), strip plot so individual teams stay visible instead of being averaged away (Q2),
   heatmap for two categories × one value (Q3), sorted bars for comparing probabilities (Q4),
   table for looking up raw matches.
3. **Linked views:** every view is bound to one team selector (`pn.bind`); clicking a dot uses a
   HoloViews `Selection1D` stream to set that selector, so one click updates the whole dashboard.
4. **"Expected" line = least-squares fit**, not a diagonal: Elo and points have different units,
   so a y = x line would be meaningless. Above the line = over-performing.
5. **Heatmap shows only countries with ≥ 50 matches by default:** one club with 6 matches gives
   extreme, meaningless averages. The country filter can still show any country.
6. **Every chart title is a question**, and captions say which filters apply and what is a model.

## Data preparation — what I can explain

- Parsing, name mapping (explicit table, error on unknown names), country codes, nullable types.
- Wide → long reshape; cumulative league tables with UEFA tie-breakers, **checked against the
  official API table**; furthest round = "appears in the next round".
- No rows dropped; missing values all explained (unplayed matches, no half-time score, no penalties).
- See `notebooks/01_data_preparation.ipynb` and its decision log.

## The model in two sentences

I replay the rest of the season 10,000 times, with every match's win/draw/loss odds taken from the
Elo ratings (draw rate 16.5%, measured from the data). A team's title chance is the share of those
simulated seasons it wins.

## Limitations

- Only 4 of 8 league matchdays of 2026-27 played → current-season views are a snapshot.
- Elo from UCL matches only (8–17 per team per season) → noisier than ClubElo.
- Model: frozen ratings, fixed knockout bracket (the real draw is partly random), goal difference
  not simulated.
- Q2 is based on 72 team-seasons (two seasons of the new format) → small sample.
- Team-name mapping is manual → correct for these sources, must be extended for new ones.
