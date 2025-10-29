import asyncio
import random
from test_website_navigation import restart_browser_context
from test_get_match_history import limited_process_game, get_history_matchs_urls
from extract_data import remove_tuple, extract_region_competition, is_file_existing
from manage_links import generate_links, generate_year_links
import copy

#@pytest.mark.asyncio

async def get_competition_match_history(context, browser, p, semaphore, game_urls, batch_size, odds_data, links_teams): 
    """
    Asynchronously retrieves the match history for a given competition.

    If the data file for the specified region, competition, and season already exists,
    the function prints a message and skips processing, returning the current odds_data
    and None for links_teams. Otherwise, it processes the provided game URLs in batches,
    updating odds_data and links_teams, and returns them along with the browser and context.
    """

    if is_file_existing(region=odds_data["region"], competition=odds_data["competition"], season=odds_data["season"]):
        print(f"Competition '{odds_data['competition']}' data ({odds_data['region']}, {odds_data['season']}) already exists. Skipping this season.")
        return odds_data, None, browser, context
    
    for i in range(0, len(game_urls), batch_size):
        batch = game_urls[i:i+batch_size]
        #print(f"Processing batch {i//batch_size + 1}/{(len(game_urls)+batch_size-1)//batch_size} "f"({len(batch)} matches)...")

        # Process each batch of games
        game_details = [limited_process_game(semaphore, context, url, odds_data["bookmaker"], odds_data["season"]) for url in batch]
        results = await asyncio.gather(*game_details)
        try: 
            for result in results:
                if result is None:
                    continue
                if result == 1:
                    raise ValueError("Stop processing due to exeded date limit for team historical data")
                events_data, tuple_links, _, _ = result
                if events_data is None:
                    continue
                odds_data["events"].append(events_data)
                links_teams.extend([t for t in tuple_links if t is not None])
        except ValueError as ve:
            print(ve)
            break  # Exit the batch processing loop if date limit exceeded

        # Close all pages in the context to free memory
        for page in context.pages:
            try:
                await page.close()
            except:
                pass

        # Random sleep between batches to mimic human behavior and avoid rate limiting
        await asyncio.sleep(random.uniform(2, 5))

        # Restart browser and context every batch to manage memory usage
        browser, context = await restart_browser_context(batch_size, i, game_urls, browser, context, p)
    print(f"Number of events collected so far: {len(odds_data['events'])}") 
    return odds_data, links_teams, browser, context


async def get_several_competitions_match_history(browser, context, p, page, semaphore, batch_size, odds_data, list_regions_competitions, region_competion_tuple, season):
    """
    Asynchronously retrieves match histories for multiple competitions.

    For each competition link, the function extracts the region and competition name,
    updates odds_data accordingly, and initializes links_teams. It then calls
    `get_competition_match_history` to fetch the match data. If any events are found,
    the odds_data is deep-copied and appended to the list of results. Finally, it
    returns a list of odds_data for all processed competitions.
    """
    list_regions_competitions_cleaned = remove_tuple(list_regions_competitions, (region_competion_tuple[0], region_competion_tuple[1]))
    list_competitions_links = generate_links(list_regions_competitions_cleaned, season)
    list_odds_data = []
    for competition_link in list_competitions_links:
            odds_data["events"] = []
                    
            print(f"compeition link :{competition_link}")
            for _ in range(2):
                    try:
                            await page.goto(competition_link, wait_until='domcontentloaded')
                    except Exception as e:
                            page = await context.new_page()
                            if _ == 1:
                                    print(f"Failed to open new page due to: {e}")
                                    return None

            for _ in range(2):
                    game_urls = await get_history_matchs_urls(page, competition_link, season)
                    if game_urls is None:
                            _, competition_link = generate_year_links(competition_link, season)
                            if competition_link is None:
                                    break
                    else:
                            break
            if game_urls is None:
                    continue
                    
            region_name, competition_name = extract_region_competition(competition_link)
            odds_data["region"] = region_name
            odds_data["competition"] = competition_name
            links_teams = []
            odds_data, _, browser, context = await get_competition_match_history(context, browser, p, semaphore, game_urls, batch_size, odds_data, links_teams)
            if len(odds_data['events']) > 0:
                list_odds_data.append(copy.deepcopy(odds_data))
    return list_odds_data


