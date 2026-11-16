"""Canonical team names and countries — the single place where names are cleaned.

Why: the same club is spelled differently across seasons and sources
("Real Madrid" in openfootball 2021-23, "Real Madrid CF" from 2023-24 and in
football-data.org). Without this mapping one club would count as two teams.

Rules (from CLAUDE.md):
  * Every raw spelling is listed explicitly — no fuzzy matching, so every
    mapping can be checked by eye and explained at the defense.
  * An unknown name raises an error; it is never silently dropped.

Run `python src/team_names.py` to check that every team in every source maps.
"""

from __future__ import annotations

import pandas as pd

# --- Team names ---------------------------------------------------------------
# raw spelling (as in the source)  ->  canonical short name (used in the dashboard)
# Short names are chosen because they must fit as chart labels.
TEAM_NAMES: dict[str, str] = {
    # Austria
    "FC Red Bull Salzburg": "Salzburg",
    "RB Salzburg": "Salzburg",
    "SK Sturm Graz": "Sturm Graz",
    "LASK Linz": "LASK",
    # Azerbaijan
    "Qarabağ Ağdam FK": "Qarabağ",
    "Sabah FK": "Sabah",
    # Belgium
    "Club Brugge KV": "Club Brugge",
    "Royal Antwerp FC": "Antwerp",
    "Royale Union Saint-Gilloise": "Union SG",
    # Croatia
    "Dinamo Zagreb": "Dinamo Zagreb",
    "GNK Dinamo Zagreb": "Dinamo Zagreb",
    # Cyprus
    "Paphos FC": "Pafos",
    # Czech Republic
    "AC Sparta Praha": "Sparta Prague",
    "SK Slavia Praha": "Slavia Prague",
    "Viktoria Plzeň": "Viktoria Plzeň",
    # Denmark
    "FC København": "Copenhagen",
    # England
    "Arsenal FC": "Arsenal",
    "Aston Villa FC": "Aston Villa",
    "Chelsea FC": "Chelsea",
    "Liverpool FC": "Liverpool",
    "Manchester City": "Man City",
    "Manchester City FC": "Man City",
    "Manchester United": "Man United",
    "Manchester United FC": "Man United",
    "Newcastle United FC": "Newcastle",
    "Tottenham Hotspur": "Tottenham",
    "Tottenham Hotspur FC": "Tottenham",
    # France
    "Lille OSC": "Lille",
    "Olympique Marseille": "Marseille",
    "Olympique de Marseille": "Marseille",
    "Paris Saint-Germain": "PSG",
    "Paris Saint-Germain FC": "PSG",
    "Racing Club de Lens": "Lens",
    "Stade Brestois 29": "Brest",
    # Germany
    "1. FC Union Berlin": "Union Berlin",
    "Bayer 04 Leverkusen": "Leverkusen",
    "Bayer Leverkusen": "Leverkusen",
    "Bayern München": "Bayern Munich",
    "FC Bayern München": "Bayern Munich",
    "Borussia Dortmund": "Dortmund",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "RB Leipzig": "RB Leipzig",
    "VfB Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg",
    # Greece
    "PAE Olympiakos SFP": "Olympiacos",
    "PAE AEK": "AEK Athens",
    # Israel
    "Maccabi Haifa": "Maccabi Haifa",
    # Italy
    "AC Milan": "AC Milan",
    "AS Roma": "Roma",
    "Atalanta": "Atalanta",
    "Atalanta BC": "Atalanta",
    "Bologna FC 1909": "Bologna",
    "Como 1907": "Como",
    "FC Internazionale Milano": "Inter",
    "Inter": "Inter",
    "Juventus": "Juventus",
    "Juventus FC": "Juventus",
    "SS Lazio": "Lazio",
    "SSC Napoli": "Napoli",
    # Kazakhstan
    "FK Kairat": "Kairat",
    # Moldova
    "FC Sheriff": "Sheriff",
    # Monaco (plays in the French league, see LEAGUE_COUNTRY below)
    "AS Monaco FC": "Monaco",
    # Netherlands
    "AFC Ajax": "Ajax",
    "Feyenoord Rotterdam": "Feyenoord",
    "PSV": "PSV",
    # Norway
    "FK Bodø/Glimt": "Bodø/Glimt",
    "Viking FK": "Viking",
    # Portugal
    "FC Porto": "Porto",
    "SL Benfica": "Benfica",
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting CP": "Sporting CP",
    "Sporting Clube de Portugal": "Sporting CP",
    "Sporting Clube de Braga": "Braga",
    # Russia
    "Zenit St. Petersburg": "Zenit",
    # Scotland
    "Celtic FC": "Celtic",
    "Rangers FC": "Rangers",
    # Serbia
    "FK Crvena Zvezda": "Red Star Belgrade",
    # Slovakia
    "ŠK Slovan Bratislava": "Slovan Bratislava",
    # Spain
    "Athletic Club": "Athletic Club",
    "Atlético Madrid": "Atlético Madrid",
    "Club Atlético de Madrid": "Atlético Madrid",
    "FC Barcelona": "Barcelona",
    "Girona FC": "Girona",
    "Real Betis Balompié": "Real Betis",
    "Real Madrid": "Real Madrid",
    "Real Madrid CF": "Real Madrid",
    "Real Sociedad de Fútbol": "Real Sociedad",
    "Sevilla FC": "Sevilla",
    "Villarreal CF": "Villarreal",
    # Sweden
    "Malmö FF": "Malmö",
    # Switzerland
    "BSC Young Boys": "Young Boys",
    # Turkey
    "Beşiktaş": "Beşiktaş",
    "Fenerbahçe SK": "Fenerbahçe",
    "Galatasaray SK": "Galatasaray",
    # Ukraine
    "Dinamo Kiev": "Dynamo Kyiv",
    "FK Shakhtar Donetsk": "Shakhtar Donetsk",
    "Shakhtar Donetsk": "Shakhtar Donetsk",
}

# --- Countries ----------------------------------------------------------------
# openfootball uses 3-letter codes, football-data.org uses full names.
# We convert codes to football-data's names so both sources share one spelling.
COUNTRY_CODES: dict[str, str] = {
    "AUT": "Austria", "AZE": "Azerbaijan", "BEL": "Belgium", "CRO": "Croatia",
    "CYP": "Cyprus", "CZE": "Czech Republic", "DEN": "Denmark", "ENG": "England",
    "ESP": "Spain", "FRA": "France", "GER": "Germany", "GRE": "Greece",
    "ISR": "Israel", "ITA": "Italy", "KAZ": "Kazakhstan", "MCO": "Monaco",
    "MDA": "Moldova", "NED": "Netherlands", "NOR": "Norway", "POR": "Portugal",
    "RUS": "Russia", "SCO": "Scotland", "SRB": "Serbia", "SUI": "Switzerland",
    "SVK": "Slovakia", "SWE": "Sweden", "TUR": "Turkey", "UKR": "Ukraine",
}

# Q3 is about *national leagues*. Monaco is a separate country but AS Monaco
# plays in France's Ligue 1, so for league analysis it counts as France.
LEAGUE_COUNTRY: dict[str, str] = {"Monaco": "France"}


def canonical_team(raw: str) -> str:
    """One raw spelling -> canonical name. Raises KeyError if unknown."""
    try:
        return TEAM_NAMES[raw]
    except KeyError:
        raise KeyError(f"Unmapped team name {raw!r}: add it to TEAM_NAMES in src/team_names.py") from None


def map_teams(names: pd.Series) -> pd.Series:
    """Map a whole column. Reports *all* unmapped names at once, not just the first."""
    unmapped = sorted(set(names.dropna()) - TEAM_NAMES.keys())
    if unmapped:
        raise KeyError(f"Unmapped team names (add to src/team_names.py): {unmapped}")
    return names.map(TEAM_NAMES)


def country_from_code(code: str) -> str:
    """'ENG' -> 'England'. Raises KeyError if unknown."""
    try:
        return COUNTRY_CODES[code]
    except KeyError:
        raise KeyError(f"Unknown country code {code!r}: add it to COUNTRY_CODES") from None


def league_country(country: str) -> str:
    """Country whose national league the club plays in ('Monaco' -> 'France')."""
    return LEAGUE_COUNTRY.get(country, country)


# --- Checks (run this file directly) ------------------------------------------
def _check_all_sources() -> None:
    import json
    from pathlib import Path

    from parse_openfootball import parse_all

    root = Path(__file__).resolve().parents[1] / "data" / "raw" / "footballdata"

    # 1) openfootball: every team and every country code must map.
    of = parse_all()
    of_teams = pd.concat([
        pd.DataFrame({"season": of["season"], "raw": of["home_team"], "code": of["home_country"]}),
        pd.DataFrame({"season": of["season"], "raw": of["away_team"], "code": of["away_country"]}),
    ]).drop_duplicates()
    of_teams["team"] = map_teams(of_teams["raw"])
    of_teams["country"] = of_teams["code"].map(country_from_code)

    # 2) football-data.org: teams file and both team columns of the matches file.
    fd_teams = json.loads((root / "cl_2026_teams.json").read_text(encoding="utf-8"))["teams"]
    fd = pd.DataFrame({"raw": [t["name"] for t in fd_teams],
                       "country": [t["area"]["name"] for t in fd_teams]})
    fd["team"] = map_teams(fd["raw"])
    fd_matches = json.loads((root / "cl_2026_matches.json").read_text(encoding="utf-8"))["matches"]
    match_names = pd.Series([m[side]["name"] for m in fd_matches for side in ("homeTeam", "awayTeam")])
    map_teams(match_names)
    assert set(match_names) <= set(fd["raw"]), "matches file has teams missing from teams file"

    # 3) No wrong merges: within one season, two different raw spellings must
    #    never become the same canonical team (that would mean two real clubs merged).
    per_season = of_teams.groupby(["season", "team"])["raw"].nunique()
    assert (per_season == 1).all(), f"Merged clubs: {per_season[per_season > 1]}"
    assert len(fd) == fd["team"].nunique() == 36, "football-data: 36 distinct teams expected"
    for season, n in of_teams.groupby("season")["team"].nunique().items():
        expected = 32 if season < "2024" else 36
        assert n == expected, f"{season}: {n} teams, expected {expected}"

    # 4) Each club has exactly one country across both sources.
    both = pd.concat([of_teams[["team", "country"]], fd[["team", "country"]]]).drop_duplicates()
    clash = both[both.duplicated("team", keep=False)]
    assert clash.empty, f"Club with two countries:\n{clash}"

    unused = TEAM_NAMES.keys() - set(of_teams["raw"]) - set(fd["raw"])
    assert not unused, f"Mappings not used by any source (typo?): {unused}"

    print(f"OK: {of_teams['raw'].nunique()} openfootball + {len(fd)} football-data spellings "
          f"-> {both['team'].nunique()} canonical clubs from {both['country'].nunique()} countries")


if __name__ == "__main__":
    _check_all_sources()
