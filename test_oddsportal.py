import asyncio
from playwright.async_api import async_playwright, Page
import pytest
from save_data import save_odds_data
import random
from test_get_competition_match_history import get_competition_match_history, get_several_competitions_match_history
from test_get_team_match_history import get_team_match_history
from test_get_match_history import get_history_matchs_urls 
from manage_links import generate_links_game
from extract_data import is_file_existing, build_team_url
import copy


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.5993.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

@pytest.fixture
def sport_name(request):
    return request.config.getoption("--sport")

@pytest.fixture
def region_name(request):
    return request.config.getoption("--region")

@pytest.fixture
def competition_name(request):
    return request.config.getoption("--competition")

@pytest.fixture
def season(request):
    return request.config.getoption("--season")

@pytest.fixture 
def bookmaker_name(request):
    return request.config.getoption("--bookmaker")

@pytest.fixture 
def team_name(request):
    return request.config.getoption("--team")

@pytest.fixture 
def team_id(request):
    return request.config.getoption("--teamid")

@pytest.fixture 
def spread(request):
    return request.config.getoption("--spread")

@pytest.fixture 
def type_game(request):
    return request.config.getoption("--typegame")



@pytest.mark.asyncio()
async def test_get_historical_events(sport_name, season, bookmaker_name, region_name, competition_name, team_name, team_id, spread, type_game):
    """
    Main asynchronous function that orchestrates the retrieval and storage of historical event data
    for both competitions and teams on OddsPortal.

    The function performs several key tasks:
    1. **Competition data retrieval**:
    - If a competition name is provided, it initializes `odds_data["events"]`,
        retrieves the competition's match history via `get_competition_match_history`,
        and saves the results using `save_odds_data` if any events are found.

    2. **Team data retrieval**:
    - If a team name is provided, it builds and adds the team's URL to `links_teams`.
    - When team links are available, it processes them using `get_team_match_history`
        to retrieve historical match data for each team.
    - The resulting data for each team is saved individually using `save_odds_data`
        with the type set to `"team"`.

    3. **Multiple competition processing**:
    - If competitions exist in `list_regions_competitions`, it retrieves match histories
        for several competitions concurrently via `get_several_competitions_match_history`.
    - Each competition dataset with non-empty events is saved using `save_odds_data`.

    Returns:
        None — The function's main goal is to collect, process, and persist historical match data
        for competitions and teams based on the provided parameters.
    """

    async with async_playwright() as p:
        list_files = is_file_existing(region=region_name, competition=competition_name, season=season)
        if len(list_files) == 0:
            browser = await p.chromium.launch()
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = await context.new_page()
            print(type_game)
            if competition_name is not None:
                if type_game == "historcal":
                    list_links_season = generate_links_game([(region_name, competition_name)], season)
                elif type_game == "upcoming":
                    list_links_season = generate_links_game([(region_name, competition_name)], type_game="upcoming")

                season_url = list_links_season[0]
                await page.goto(season_url, wait_until='domcontentloaded')
                await asyncio.sleep(2)

                #current_url = page.url
                game_urls = await get_history_matchs_urls(page, season_url, season)
                #await Page.pause()
                print(f"Found {len(game_urls)} game URLs for competition '{competition_name}' in season '{season}'.")
                
                odds_data = {
                    "sport": sport_name,
                    "region": region_name,
                    "competition": competition_name,
                    "season": season,
                    "market": "1X2 and Fulltime result",
                    "bookmaker": bookmaker_name,
                    "events": []
                }

                if not game_urls:
                    print("No game URLs found for the specified competition and season.")
                    # Closing context and browser before returning
                    await context.close()
                    await browser.close()
                    return

            # Limit the number of concurrent pages to avoid overwhelming the browser
            semaphore = asyncio.Semaphore(4)  # 4 concurrent pages

            # Batch processing configuration
            batch_size = 100  # reduced batch size to limit memory usage
            links_teams = []

            if competition_name is not None:
                odds_data["events"] = []

                # First, get historical data for competitions
                odds_data, links_teams, browser, context = await get_competition_match_history(context, browser, p, 
                                                                                            semaphore, game_urls, batch_size, 
                                                                                            copy.deepcopy(odds_data), links_teams)
                # Save competition data and free memory
                if len(odds_data["events"]) > 0:
                    save_odds_data(odds_data, type_game=type_game)
                    odds_data["events"] = []
                
                if spread is None:
                    return
            

            # get historical data for teams
            odds_data_teams = {
                "sport": sport_name,
                "region": region_name,
                "competition": competition_name,
                "season": season,
                "market": "1X2 and Fulltime result",
                "bookmaker": bookmaker_name,
                "events": []
            }
            list_data_teams = []
            if team_name is not None:
                links_teams.append(build_team_url(sport_name, team_name, team_id))

            if len(links_teams) > 0:
                links_teams = list(set(links_teams))  # Remove duplicates
                list_data_teams, list_regions_competitions, browser, context = await get_team_match_history(
                    context, browser, p, 
                    semaphore, links_teams, batch_size, 
                    copy.deepcopy(odds_data_teams), list_data_teams, season)
                
                # Save teams data
                for data_team in list_data_teams:
                    if len(data_team["events"]) > 0:
                        save_odds_data(data_team, type_historical="team")
                
                # Free memory
                odds_data_teams["events"] = []
                links_teams = []
                list_data_teams = []
            else:
                print(f"None team finded beacause is already exists")   

            if spread == "team":
                return
            # get historical data for secondary competitions
            if competition_name is not None:
                if len(list_regions_competitions) > 0:
                    list_odds_data_competitions = await get_several_competitions_match_history(browser, context, p, page, 
                                                                                        semaphore, batch_size, copy.deepcopy(odds_data), 
                                                                                        list_regions_competitions, (region_name, competition_name), season)
                    try:
                        for data_competion in list_odds_data_competitions:
                            if len(data_competion["events"]) > 0:
                                save_odds_data(data_competion)
                    except NameError as e:
                        print(f"None competition saved beacaus is already exists: {e}")
                else:
                    print(f"None competitions finded beacause are already exists")
                
                
                try:
                    print(f"Number of successfully processed events: {len(odds_data['events'])}")
                except TypeError as e:
                    print(print(f"Successfully, events already exists"))
            
            # Close the browser context and browser
            await context.close()
            await browser.close()
        else:
            print(f"The primary competiton {region_name, competition_name} at {season} exist already")