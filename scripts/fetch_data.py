"""Download the raw data for the UCL dashboard.

Run from the project root:
    python scripts/fetch_data.py

Downloads:
  1. openfootball Champions League match files (past seasons, plain text)
  2. football-data.org: current 2026/27 UCL matches, league-phase table, teams and
     top scorers (JSON)

ClubElo is no longer used: its API returned HTTP 502 for over a week, so team
strength is computed by us from match results instead (see src/elo.py).

Why football-data.org: openfootball has no 2026-27 file yet and FootyStats
puts its match CSV behind a paywall. football-data.org has a free tier that
includes the Champions League, but it needs a personal API key, read from the
FOOTBALL_DATA_API_KEY environment variable or from a git-ignored .env file in
the project root (so the key never ends up in the code or in git).
"""

from pathlib import Path
import os
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

OPENFOOTBALL_SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/champions-league/master/{season}/cl.txt"
# football-data.org v4 API. "CL" = Champions League; season=2026 means 2026/27.
FOOTBALL_DATA_SEASON = 2026
FOOTBALL_DATA_ENDPOINTS = {
    "matches": "https://api.football-data.org/v4/competitions/CL/matches?season={season}",
    "standings": "https://api.football-data.org/v4/competitions/CL/standings?season={season}",
    # teams: gives each club's country ("area"), which the matches endpoint lacks (needed for Q3).
    "teams": "https://api.football-data.org/v4/competitions/CL/teams?season={season}",
    # scorers: goals/assists/penalties per player, current season only (no history in any
    # free source). limit=100 so we get far more than the API's default top 10.
    "scorers": "https://api.football-data.org/v4/competitions/CL/scorers?season={season}&limit=100",
}


def read_api_key() -> str | None:
    """Return the football-data.org key from the environment or the .env file."""
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if key:
        return key
    env_file = ROOT / ".env"
    if env_file.exists():
        # Minimal KEY=VALUE parser, so we don't need the python-dotenv dependency.
        for line in env_file.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "FOOTBALL_DATA_API_KEY" and value.strip():
                return value.strip()
    return None


def download(url: str, target: Path, extra_headers: dict | None = None) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        headers = {"User-Agent": "ucl-dashboard-student-project", **(extra_headers or {})}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            target.write_bytes(resp.read())
        print(f"  OK   {target.relative_to(ROOT)}  ({target.stat().st_size / 1024:.0f} KB)")
        return True
    except Exception as exc:  # noqa: BLE001 - report and continue
        print(f"  --   {url}  ({exc})")
        return False


def main() -> None:
    print("1) openfootball Champions League seasons")
    for season in OPENFOOTBALL_SEASONS:
        download(OPENFOOTBALL_URL.format(season=season), RAW / "openfootball" / season / "cl.txt")
    print("   (a missing 2026-27 file is normal until openfootball adds it)")

    print("\n2) football-data.org 2026/27 matches, standings, teams, scorers")
    key = read_api_key()
    if not key:
        print("  MISSING API KEY - register for free at https://www.football-data.org/client/register")
        print("  then put  FOOTBALL_DATA_API_KEY=<your key>  into a .env file in the project root.")
        return
    for name, url in FOOTBALL_DATA_ENDPOINTS.items():
        target = RAW / "footballdata" / f"cl_{FOOTBALL_DATA_SEASON}_{name}.json"
        download(url.format(season=FOOTBALL_DATA_SEASON), target, {"X-Auth-Token": key})


if __name__ == "__main__":
    main()
