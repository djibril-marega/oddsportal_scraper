import re

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

def generate_links(data, season):
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

    base_url = "https://www.oddsportal.com/football"
    links = []
    for country, competition in data:
        country_slug = country.lower()
        competition_slug = competition.lower()

        # clearing country and competition names
        competition_slug = (
            competition_slug.replace('&', 'and')
                            .replace("'", '')
                            .replace('é', 'e')
                            .replace('è', 'e')
                            .replace('ê', 'e')
                            .replace('à', 'a')
                            .replace(' ', '-')
        )
        season = (
            season.replace('/', '-')
        )
        link = f"{base_url}/{country_slug}/{competition_slug}-{season}/results/"
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