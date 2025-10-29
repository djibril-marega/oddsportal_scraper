import asyncio
import random
from extract_data import extract_id_from_url, extract_team_name_from_url, is_file_existing
from test_get_match_history import limited_process_game, get_history_matchs_urls
from test_website_navigation import restart_browser_context
import copy

async def go_to_results_match(page, context, team_link):
    """
    Navigates to a team's history page and opens the "Results" tab.

    The function constructs the URLs for the team's results page using the team link
    and attempts to load the page, retrying once if an exception occurs. A new page
    is created in the context if navigation fails. 

    Returns a tuple containing:
    - the results page URL
    - the page object
    """
    if not team_link:
        return
    
    link = "https://www.oddsportal.com" + team_link + "#results"
    team_id = extract_id_from_url(team_link)
    link_show_all_results = f"https://www.oddsportal.com/search/results/:{team_id}/"
    for _ in range(2):
        try:
            await page.goto(link_show_all_results, wait_until='domcontentloaded')
            break
        except Exception as e:
            print(f"Warning while naviguate to {link_show_all_results}: {e}")
            page = await context.new_page() 

    return link, page


async def get_team_match_history(context, browser, p, semaphore, links_teams, batch_size, odds_data_teams, list_data_teams, season):
    """
    Asynchronously retrieves match histories for multiple teams.

    The function processes the provided list of team links in batches, using a semaphore
    to limit concurrency. It updates odds_data_teams with match results and aggregates
    all data into list_data_teams. 

    Returns:
    - list_data_teams: collected match history data for all teams
    - list_regions_competitions: list of (region, competition) tuples processed
    - browser: the browser instance
    - context: the browser context
    """
    page = await context.new_page()
    list_regions_competitions = []
    for url_team in links_teams:
        url_team_complet, page = await go_to_results_match(page, context, url_team)
        game_urls = await get_history_matchs_urls(page, url_team_complet, season)
        team_name = extract_team_name_from_url(url_team) 
        odds_data_teams = {
            "sport": odds_data_teams["sport"],
            "team": team_name,
            "season": odds_data_teams["season"],
            "market": "1X2 and Fulltime result",
            "bookmaker": odds_data_teams["bookmaker"],
            "events": []
        }
        if is_file_existing(type_historical= "team", team=odds_data_teams["team"], season= odds_data_teams["season"]):
            print(f"Team '{odds_data_teams['team']}' data ({odds_data_teams['season']}) already exists. Skipping this season.")
            continue
        try: 
            for i in range(0, len(game_urls), batch_size):
                batch = game_urls[i:i+batch_size]
                game_details = [
                    limited_process_game(
                        semaphore,
                        context,
                        url,
                        odds_data_teams["bookmaker"],
                        odds_data_teams["season"],
                        type_historical="team"
                    )
                    for url in batch if url
                ]

                results = await asyncio.gather(*game_details)
                for result in results:
                    if result is None:
                        continue
                    if result == 1:
                        raise ValueError("Stop processing due to exeded date limit for team historical data")
                    event_data, _, page, region_competion_names = result
                    if event_data is None:
                        continue
                    event_data["region"] = region_competion_names[0]
                    event_data["competition"] = region_competion_names[1]
                    odds_data_teams["events"].append(event_data)
                    list_regions_competitions.append(region_competion_names)

                # Close all pages in the context to free memory
                for page in context.pages:
                    try:
                        await page.close()
                    except:
                        pass

                # Random sleep between batches to mimic human behavior and avoid rate limiting
                await asyncio.sleep(random.uniform(2, 5))

                # Restart browser and context every batch to manage memory usage
                browser, context = await restart_browser_context(batch_size, i, url_team, browser, context, p)
            list_data_teams.append(copy.deepcopy(odds_data_teams))
        except ValueError as ve:
            print(ve)

    list_regions_competitions = list(set(tuple(x) for x in list_regions_competitions))  # Remove duplicates
    return list_data_teams, list_regions_competitions, browser, context