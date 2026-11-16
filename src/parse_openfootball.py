"""Parse openfootball Champions League text files into a tidy matches DataFrame.

One row = one match (one leg). Team names are kept exactly as written in the
file; cleaning them is the job of src/team_names.py (Phase 3b).

File layout (see MEMORY.md, "Data inventory"):
    ▪ League, Matchday 1                  <- section header: stage, round
      Tue Sep 17 2024                     <- date line (year only sometimes!)
        18:45  Home (CTY) v Away (CTY)  2-1 (1-0)   <- match line (time optional)

Usage:
    python src/parse_openfootball.py      # parses all seasons, prints a summary
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "openfootball"

# --- Regular expressions (one per kind of line) ------------------------------

# Any section header, e.g. "▪ League, Matchday 1", "▪ Group A", "▪ Semifinals"
SECTION_RE = re.compile(r"^▪\s*(?P<text>.+?)\s*$")
KNOCKOUT_ROUNDS = {"Round of 16", "Quarterfinals", "Semifinals", "Final"}

# "  Tue Sep 17 2024" or "  Wed Sep 18" (year is optional)
DATE_RE = re.compile(
    r"^\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})"
    r"(?:\s+(?P<year>\d{4}))?\s*$"
)

# "    18:45  Home (CTY) v Away (CTY)  2-1 (1-0)"  (time is optional)
# The score is separated from the away team by 2+ spaces.
MATCH_RE = re.compile(
    r"^\s+(?:\d\d:\d\d\s+)?(?P<home>.+?)\s+v\s+(?P<away>.+?)\s{2,}(?P<score>\d+-\d+.*?)\s*$"
)

# "Real Madrid CF (ESP)" -> name, 3-letter country code
TEAM_RE = re.compile(r"^(?P<name>.+?)\s+\((?P<country>[A-Z]{3})\)$")

# Header line "# Matches    189" -> used to check nothing was missed
HEADER_COUNT_RE = re.compile(r"^#\s*Matches\s+(\d+)")

# The four score shapes seen in the files:
#   "2-1 (1-0)"                     normal, with half-time
#   "0-0"                           normal, no half-time given
#   "3-1 a.e.t. (2-1, 0-0)"         extra time: final (after 90 min, half-time)
#   "4-3 pen. 1-1 a.e.t. (1-1, 0-1)" penalties, then same as extra time
SCORE_RE = re.compile(
    r"^(?:(?P<pen_h>\d+)-(?P<pen_a>\d+)\s+pen\.\s+)?"   # optional penalty shoot-out
    r"(?P<ft_h>\d+)-(?P<ft_a>\d+)"                      # final score (incl. extra time)
    r"(?P<aet>\s+a\.e\.t\.)?"                           # extra-time marker
    r"(?:\s+\((?P<inner>[^)]*)\))?$"                    # bracket: "(ht)" or "(90min, ht)"
)


def parse_score(score: str) -> dict:
    """Turn a score string into numbers. Raises ValueError on an unknown shape."""
    m = SCORE_RE.match(score.strip())
    if not m:
        raise ValueError(f"Unknown score format: {score!r}")

    extra_time = m["aet"] is not None
    result = {
        "home_goals": int(m["ft_h"]),
        "away_goals": int(m["ft_a"]),
        "home_goals_90": int(m["ft_h"]),  # same as final unless extra time was played
        "away_goals_90": int(m["ft_a"]),
        "home_goals_ht": pd.NA,
        "away_goals_ht": pd.NA,
        "extra_time": extra_time,
        "home_pens": int(m["pen_h"]) if m["pen_h"] else pd.NA,
        "away_pens": int(m["pen_a"]) if m["pen_a"] else pd.NA,
    }

    # The bracket holds "ht" for normal matches, or "90min, ht" after extra time.
    parts = [p.strip() for p in m["inner"].split(",")] if m["inner"] else []
    if extra_time and parts:
        h90, a90 = parts[0].split("-")
        result["home_goals_90"], result["away_goals_90"] = int(h90), int(a90)
        parts = parts[1:]
    if parts:
        ht_h, ht_a = parts[0].split("-")
        result["home_goals_ht"], result["away_goals_ht"] = int(ht_h), int(ht_a)
    return result


def split_team(text: str) -> tuple[str, str]:
    """'Real Madrid CF (ESP)' -> ('Real Madrid CF', 'ESP')."""
    m = TEAM_RE.match(text.strip())
    if not m:
        raise ValueError(f"Team without country code: {text!r}")
    return m["name"], m["country"]


def parse_section(text: str) -> tuple[str, str, str | None]:
    """Section header -> (stage, round, group). Three header styles exist:
        2023-26:  'League, Matchday 1' / 'Finals, Quarterfinals'
        2021-23:  'Group A' (sometimes German 'Gruppe G'), and bare 'Semifinals'
    """
    if "," in text:                                   # "Stage, Round"
        stage, round_name = (s.strip() for s in text.split(",", 1))
        return stage, round_name, None
    if m := re.match(r"^(?:Group|Gruppe)\s+([A-H])$", text):
        return "Group", f"Group {m[1]}", m[1]         # normalise German "Gruppe"
    if text in KNOCKOUT_ROUNDS:
        return "Finals", text, None
    raise ValueError(f"Unknown section header: {text!r}")


def season_year(season: str, month: int) -> int:
    """'2024-25', month 9 -> 2024; month 3 -> 2025.
    A UCL season runs Jul-Jun, so autumn months belong to the first year."""
    start_year = int(season[:4])
    return start_year if month >= 7 else start_year + 1


def parse_file(path: Path, season: str) -> pd.DataFrame:
    """Parse one season's cl.txt. Any line we don't understand raises an error,
    so no match can be silently dropped."""
    stage = round_name = group = None
    current_date: date | None = None
    expected_matches: int | None = None
    rows = []

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue  # blank line
        if m := HEADER_COUNT_RE.match(line):
            expected_matches = int(m[1])
            continue
        if line.startswith(("=", "#")):
            continue  # title / other header lines
        if m := SECTION_RE.match(line):
            stage, round_name, group = parse_section(m["text"])
            continue
        if m := DATE_RE.match(line):
            month = datetime.strptime(m["mon"], "%b").month
            # Most date lines have no year. We can't just "add 1 when the month
            # goes backwards", because 2021-23 files restart in September for
            # every group. So we derive the year from the season instead...
            year = season_year(season, month)
            # ...and use any year that IS written as a cross-check.
            if m["year"] and int(m["year"]) != year:
                raise ValueError(f"{path}:{line_no}: year {m['year']} != inferred {year}")
            current_date = date(year, month, int(m["day"]))
            continue
        if m := MATCH_RE.match(line):
            if current_date is None or stage is None:
                raise ValueError(f"{path}:{line_no}: match before any date/section")
            home, home_cty = split_team(m["home"])
            away, away_cty = split_team(m["away"])
            matchday = re.match(r"Matchday (\d+)", round_name)
            rows.append({
                "season": season,
                "stage": stage,                      # Group / League / Playoffs / Finals
                "round": round_name,                 # e.g. "Matchday 3", "Group A", "Final"
                "group": group,                      # A-H in 2021-23 files, else None
                "matchday": int(matchday[1]) if matchday else pd.NA,  # not given 2021-23
                "date": current_date,
                "home_team": home,
                "home_country": home_cty,
                "away_team": away,
                "away_country": away_cty,
                **parse_score(m["score"]),
            })
            continue
        raise ValueError(f"{path}:{line_no}: unrecognised line: {line!r}")

    df = pd.DataFrame(rows)
    # Completeness check: the file header states how many matches it contains.
    if expected_matches is not None and len(df) != expected_matches:
        raise ValueError(f"{path}: header says {expected_matches} matches, parsed {len(df)}")
    return df


def parse_all(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Parse every season folder that has a cl.txt (2026-27 has none -> skipped)."""
    frames = [parse_file(p, p.parent.name) for p in sorted(raw_dir.glob("*/cl.txt"))]
    if not frames:
        raise FileNotFoundError(f"No cl.txt files in {raw_dir}. Run scripts/fetch_data.py")
    df = pd.concat(frames, ignore_index=True)

    # Proper dtypes: dates as datetime, nullable integers where values can be missing.
    df["date"] = pd.to_datetime(df["date"])
    nullable_int = ["matchday", "home_goals_ht", "away_goals_ht", "home_pens", "away_pens"]
    df[nullable_int] = df[nullable_int].astype("Int64")
    return df


if __name__ == "__main__":
    matches = parse_all()
    print(matches.groupby(["season", "stage"]).size().unstack(fill_value=0))
    print(f"\nTotal matches: {len(matches)}")
    print(f"Extra time: {matches['extra_time'].sum()}, "
          f"penalty shoot-outs: {matches['home_pens'].notna().sum()}, "
          f"missing half-time: {matches['home_goals_ht'].isna().sum()}")
    print(matches.dtypes)
