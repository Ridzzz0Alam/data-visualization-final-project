# Agentic workflow — UCL dashboard in VS Code

A step-by-step plan for building the project locally with an AI coding agent
(Claude Code in VS Code is assumed; Copilot agent mode or Cursor work the same way).
Each phase has: a **prompt** to paste, what the agent should produce, and a **checkpoint** you verify yourself before moving on.

---

## Phase 0 — Setup (once, ~10 min)

1. Unzip this folder and open it in VS Code (`File → Open Folder`).
2. Create a virtual environment and install packages (VS Code terminal):
   ```bash
   python -m venv .venv
   # Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Select the `.venv` interpreter in VS Code (`Ctrl+Shift+P → Python: Select Interpreter`).
4. Install the **Claude Code** extension from the VS Code Extensions panel and sign in.
   The agent reads `CLAUDE.md` automatically, so it already knows the project brief.
5. `git init` and make a first commit — this gives you an undo button for every phase.

**Checkpoint:** `python -c "import panel, hvplot; print('ok')"` prints `ok`.

---

## Phase 1 — Get the data (~5 min)

Run it yourself (no agent needed, saves tokens):
```bash
python scripts/fetch_data.py
```
Then download the FootyStats **2026/2027 Match CSV** from
https://footystats.org/europe/uefa-champions-league/datasets into `data/raw/footystats/`.

**Checkpoint:** five or six `cl.txt` files, one `clubelo_*.csv`, one FootyStats CSV.
Commit: `git add -A && git commit -m "raw data"`.

---

## Phase 2 — Explore the raw data

> **Prompt:** Look at one file from each source in `data/raw/` (just the first 40 lines of each). Summarise in a short table: columns/fields, date range, number of rows, obvious problems (missing values, inconsistent names, odd formats). Don't write any code files yet.

**Checkpoint:** you understand each source. Write 3–4 bullet points into `docs/defense_notes.md` under "Datasets" in your own words.

---

## Phase 3 — Parse and clean (the heart of "Data Preparation")

Do these as **three separate prompts**, checking each before the next:

> **Prompt 3a:** Write `src/parse_openfootball.py` that parses the openfootball `cl.txt` files into one DataFrame: season, stage, matchday/round, date, home team, away team, home country, away country, home goals, away goals, half-time scores, extra-time/penalty flags. Add a tiny test at the bottom (`if __name__ == "__main__"`) that parses 2025-26 and prints row counts per stage. Run it.

> **Prompt 3b:** Write `src/team_names.py` with a canonical team-name mapping covering every team in openfootball, ClubElo and FootyStats. Write a check that lists any unmapped name per source. Run it and iterate until there are zero unmapped names relevant to UCL teams.

> **Prompt 3c:** Write `src/prepare.py` that builds these tables into `data/processed/` as Parquet:
> - `matches.parquet` — all seasons, canonical names, derived columns: result (H/D/A), goal difference, points for each side, `is_league_phase`.
> - `team_matchday.parquet` — one row per team per league-phase matchday with cumulative points, goal difference and rank (handle ties with UCL tiebreak order: points, GD, goals scored).
> - `teams_current.parquet` — 2026/27 teams with current points, rank, Elo rating, country, and `points_minus_expected` (over/under-performance vs Elo).
> - `country_season.parquet` — aggregates by country and season.
> Log rows dropped and why. Run it.

**Checkpoint:** open each Parquet in a notebook cell (`pd.read_parquet(...).head()`), sanity-check one team you know (e.g. PSG's 2025/26 run ends with the final on 30 May 2026).
Commit.

---

## Phase 4 — Narrated notebook for the defense

> **Prompt:** Create `notebooks/01_data_preparation.ipynb` that walks through `src/prepare.py` step by step: load raw → show a problem → fix it → show the result. Use short markdown cells (2–3 sentences) explaining each decision. Import functions from `src/` rather than duplicating code. Include before/after row counts and a missing-values summary.

**Checkpoint:** "Run All" works top to bottom. You can explain every cell out loud.

---

## Phase 5 — Dashboard skeleton

> **Prompt:** Create `app/app.py` using `pn.template.FastListTemplate`. Sidebar: season selector, searchable team selector, country multi-select, matchday range slider. Main area: four empty placeholder cards titled with Q1–Q4 from CLAUDE.md. Load data only from `data/processed/`. Run `panel serve app/app.py --show` and confirm it opens.

**Checkpoint:** the page opens in your browser and the widgets respond (even with empty charts).

---

## Phase 6 — Build the views (one prompt per view)

> **6a (Q1):** In the Q1 card, add an hvPlot scatter of Elo rating vs points for 2026/27, labelled points, with a diagonal "expected" reference line; the selected team highlighted, others greyed. Hover: team, country, points, Elo, GD.

> **6b (Q1/Q2):** Add a bump chart (rank by matchday, inverted y-axis) for the selected season, highlighting the selected team.

> **6c (Q2):** Add a chart comparing rank after matchday 4 to final outcome (knockout round reached) for 2024/25 and 2025/26 — e.g. a strip/jitter plot or heatmap of rank-band × furthest stage.

> **6d (Q3):** Add a heatmap of country × season (average Elo or points per match), filtered by the country widget.

> **6e:** Add a `pn.widgets.Tabulator` match table with header filters, linked to the team selector.

> **6f (linking):** Make selecting a point in the scatter set the team selector, so all views update. Make sure there are no errors in the browser console.

**Checkpoint after each:** reload the page, click around, try an edge case (a team with no matches in a season). Commit after each working view.

---

## Phase 7 — Title-probability model (Q4)

> **Prompt:** Write `src/simulate.py`: a simple Elo-based Monte Carlo simulation (e.g. 10,000 runs) of the remaining 2026/27 league-phase matches and a simplified knockout bracket, returning each team's probability of top-8, top-24 and winning. Keep it under ~120 lines, fixed random seed, and document assumptions at the top. Add the results to the Q4 card as a horizontal probability chart plus a small "model assumptions" note.

**Checkpoint:** probabilities sum to ~100% for "winner"; strong teams are higher than weak ones. You can explain the model in two sentences.

---

## Phase 8 — Polish, docs, submit

> **Prompt:** Review `app/app.py` for consistent colours, titles that state the question, axis labels, and a footer citing all data sources with links. Then write `README.md`: project goal, analytical questions, data sources, data-prep summary, how to install and run, screenshots placeholder.

Then **you** write `docs/defense_notes.md` (the agent can draft, but put it in your own words):
- the 4 questions, and for each: which view answers it and the key insight
- 3–4 design decisions and why (chart choices, linking, colours)
- limitations (small current-season sample, simple model, name matching)

Final: push to GitHub (`gh repo create` or via VS Code) or zip the folder. Do a full dry-run of your defense demo.

---

## Token- and usage-saving tips

- **Local is cheaper mainly because data downloads just work** — no blocked sites, no back-and-forth.
  The agent still uses your plan's usage, so the habits below are what really save tokens.
- One phase per prompt; start a **new chat/session per phase** so old context isn't re-sent.
- Never paste whole data files into chat. Ask the agent to read `head` / first N lines.
- Run cheap commands yourself (`fetch_data.py`, `panel serve`) instead of asking the agent to.
- Paste the **exact error message** (last ~20 lines) when something fails, not the whole log.
- Commit after every checkpoint; if a prompt goes wrong, `git checkout .` instead of asking for a fix.
- If your plan has optional extra/pay-as-you-go usage, keep it switched off in your account settings so work simply pauses at the limit.
