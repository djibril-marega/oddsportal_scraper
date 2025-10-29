from urllib.parse import urlparse 
import re
import os

def extract_region_competition(url: str):
    """
    Extracts the region and competition from an OddsPortal URL.

    Example:
    https://www.oddsportal.com/football/europe/champions-league-2022-2023/
    -> ('europe', 'champions league')
    https://www.oddsportal.com/football/france/ligue-1/
    -> ('france', 'ligue 1')
    https://www.oddsportal.com/football/world/world-cup/
    -> ('world', 'world cup')
    https://www.oddsportal.com/football/europe/champions-league/
    -> ('europe', 'champions league')
    """

    # URL parsing
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    # check if we have enough parts
    if len(path_parts) < 3:
        raise ValueError("URL non valide ou incomplète")

    region = path_parts[1]
    competition_raw = path_parts[2]

    # delete year suffix if present
    competition_clean = re.sub(r"-\d{4}(-\d{4})?$", "", competition_raw)

    # replace dashes with spaces
    competition_clean = competition_clean.replace("-", " ")

    return region, competition_clean

def extract_id_from_url(url: str) -> str | None:
    """
    Returns the last non-empty segment of a URL path,
    or None if no segment is found.
    Example: '.../los-angeles-fc/txUJt9AR/#results' -> 'txUJt9AR'
    """

    p = urlparse(url)
    parts = [seg for seg in p.path.split('/') if seg]
    return parts[-1] if parts else None

def extract_team_name_from_url(url: str) -> str | None:
    """
    Returns the team name from a team URL.
    Example: '.../los-angeles-fc/txUJt9AR/#results' -> 'los angeles fc'
    """

    p = urlparse(url)
    parts = [seg for seg in p.path.split('/') if seg]
    if len(parts) >= 2:
        team_name_raw = parts[-2]
        team_name_clean = team_name_raw.replace("-", " ")
        return team_name_clean
    return None

def extract_season(url: str) -> str | None:
    """
    Extracts the season (e.g., '2018-2019') from an OddsPortal URL,
    regardless of the league.
    Example:
    https://www.oddsportal.com/football/france/ligue-2-2018-2019/metz-clermont-2TYidOY8/
    -> '2018-2019'
    """

    match = re.search(r'\b\d{4}-\d{4}\b', url)
    return match.group(0) if match else None

def remove_tuple(data, target):
    # Convert target to lowercase for case-insensitive comparison
    target_lower = tuple(x.lower() for x in target)
    return [t for t in data if tuple(x.lower() for x in t) != target_lower]


def is_file_existing(base_dir="scraped_data", type_historical="competition", region=None, competition=None, team=None, season=None):
    """
    Check if a file already exists for given region/competition/team and season.
    """
    if not os.path.exists(base_dir):
        return []

    def clean_filename(text):
        text = text.replace('/', '-').replace('\\', '-').replace(':', '-').replace('*', '-')
        text = text.replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')

    region_clean = clean_filename(region) if region else None
    competition_clean = clean_filename(competition) if competition else None
    team_clean = clean_filename(team) if team else None
    season_clean = clean_filename(season) if season else None

    # Normalize season format
    if season_clean:
        season_clean = season_clean.replace('/', '-')

    matching_files = []

    files_lower = [f.lower() for f in os.listdir(base_dir)]
    for filename in files_lower:
        if not filename.endswith(".json"):
            continue

        # Filter by region/competition/team
        if type_historical == "competition":
            if region_clean and region_clean not in filename:
                continue
            if competition_clean and competition_clean not in filename:
                continue
        elif type_historical in ("team", "teams"):
            if team_clean and team_clean not in filename:
                continue

        # Extract season
        match = re.search(r"(\d{4}[-/]\d{4})", filename)
        if not match:
            continue

        season_in_file = match.group(1).replace('/', '-')
        if season_clean and season_in_file != season_clean:
            continue

        matching_files.append(os.path.join(base_dir, filename))

    return matching_files


def build_team_url(sport: str, team_name: str, team_id: str) -> str:
    """
    Builds an OddsPortal URL for a given team.

    Example:
        build_oddsportal_team_url("football", "bayern munich", "nVp0wiqd")
        -> "https://www.oddsportal.com/football/team/bayern-munich/nVp0wiqd/"
    """

    formatted_team_name = team_name.strip().lower().replace(" ", "-")
    url = f"https://www.oddsportal.com/{sport}/team/{formatted_team_name}/{team_id}/"
    return url
