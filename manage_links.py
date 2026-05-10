import re
from datetime import datetime

async def get_team_links(page):
    """Retrieves team links from the match page"""
    home_team_link = await page.get_attribute("[data-testid='game-host'] a", "href")
    away_team_link = await page.get_attribute("[data-testid='game-guest'] a", "href")
    return home_team_link, away_team_link

async def get_competition_link(page):
    """Retrieves competition link from the match page"""
    await page.wait_for_selector("a[data-testid='3']", timeout=10000)
    competition_link = await page.get_attribute("a[data-testid='3']", "href")
    return "https://www.oddsportal.com" + competition_link

def generate_links_game(data, season=None, type_game="historcal"):
    """
    Generates URLs for football competition results on OddsPortal.

    Parameters
    ----------
    data : list of tuple
        List of (country, competition) pairs representing the country and competition.
        Example: [("France", "Ligue 1"), ("England", "Premier League")]
    season : str
        Season in the format "YYYY/YYYY". Example: "2023/2024"

    Returns
    -------
    list of str
        List of URLs corresponding to each competition for the given season.
        Example: ["https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
                "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"]
    """
    def normalize_string_for_link(string):
        string = (string.replace('&', 'and')
                        .replace("'", '')
                        .replace('é', 'e')
                        .replace('è', 'e')
                        .replace('ê', 'e')
                        .replace('à', 'a')
                        .replace(' ', '-'))
        return string
    
    if season is None and type_game == "historcal":
        raise ValueError("Season must be provided for historical game links.")
    
    base_url = "https://www.oddsportal.com/football"
    links = []
    for country, competition in data:
        country_slug = country.lower()
        competition_slug = competition.lower()

        # clearing country and competition names
        competition_slug = normalize_string_for_link(competition_slug)
        country_slug = normalize_string_for_link(country_slug)
        if season is not None:
            season = (
                season.replace('/', '-')
            )
        if type_game == "historcal":
            if not is_current_season(season):
                link = f"{base_url}/{country_slug}/{competition_slug}-{season}/results/"
            else:
                link = f"{base_url}/{country_slug}/{competition_slug}/results/"
        elif type_game == "upcoming":
            link = f"{base_url}/{country_slug}/{competition_slug}/"
        links.append(link)

    return links

def generate_year_links(url, season):
    """
    Takes an existing URL and a season in the format 'YYYY-YYYY' or 'YYYY/YYYY',
    and returns two URLs, one for each year of the season.
    """
    try:
        year1, year2 = season.split('-')
    except ValueError:
        try:
            year1, year2 = season.split('/')
        except Exception as e:
            raise ValueError(
                f"Season format is incorrect: {season}. Expected 'YYYY-YYYY' or 'YYYY/YYYY'."
            ) from e

    # Cas 1 : year in the URL → we replace it
    pattern_with_year = r'-\d{4}/results/'
    if re.search(pattern_with_year, url):
        link1 = re.sub(r'-\d{4}/results/', f'-{year1}/results/', url)
        link2 = re.sub(r'-\d{4}/results/', f'-{year2}/results/', url)
        return link1, link2

    # Cas 2 : year not in the URL → we add it before "/results/"
    pattern_no_year = r'/results/?$'
    if re.search(pattern_no_year, url):
        link1 = re.sub(pattern_no_year, f'-{year1}/results/', url)
        link2 = re.sub(pattern_no_year, f'-{year2}/results/', url)
        return link1, link2

    raise ValueError("Link format is incorrect, cannot generate year-specific links.")


def is_current_season(season, start_month=8, end_month=7):
    """
    Vérifie si la saison donnée est en cours.
    
    :param season: str, format "YYYY" ou "YYYY-YYYY"
    :param start_month: mois de début de la saison (1-12)
    :param end_month: mois de fin de la saison (1-12)
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    if '-' in season:
        year1, year2 = map(int, season.split('-'))

        # La saison couvre year1.start_month → year2.end_month
        if (current_year == year1 and current_month >= start_month) or \
           (current_year == year2 and current_month <= end_month):
            return True
        else:
            return False
    else:
        # Saison sur une seule année civile
        return int(season) == current_year