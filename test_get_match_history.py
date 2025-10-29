import asyncio
import re
from playwright.async_api import TimeoutError
import pytest
from test_website_navigation import goto_with_retry
from manage_date import add_missing_year, parse_oddsportal_date_to_datetime
from manage_links import get_team_links, get_competition_link
from extract_data import extract_region_competition, extract_season
from date_sorting import check_season_position, season_to_date

@pytest.mark.asyncio
async def get_match_details(game_page, game_url, bookmaker_name, season): 
    """
    Asynchronously retrieves detailed information for a single match.

    The function processes the match page and returns a tuple containing event_data
    and (region_name, competition_name). It handles several edge cases:
    - Returns None if an exception occurs during processing.
    - Skips and returns None if the page fails to load persistently.
    - Skips matches that occur before the season start date, returning 1.
    - Skips matches that occur after the season end date, returning None.
    """

    try:
        print(f"Navigating to match URL: {game_url}")
        success = await goto_with_retry(game_page, game_url)
        if not success:
            await game_page.close()
            print(f"Skipping match due to load failure: {game_url}")
            return None
        
        # Await the main elements to load
        for _ in range(3):
            try:
                await game_page.wait_for_selector("[data-testid='game-host']", timeout=10000)
                break
            except Exception as e:
                print(f"Retrying to find main elements due to: {e}")
                await goto_with_retry(game_page, game_url)
                if _ == 2:
                    print(f"Skipping match due to persistent load issues: {game_url}")
                    await game_page.close()
                    return None

        # Extract game details
        home_team = await game_page.text_content("[data-testid='game-host']")
        
        home_point_element = home_point_element = await game_page.query_selector('[data-testid="game-host"] + div')
        home_point = await home_point_element.text_content() if home_point_element else "N/A"
        
        away_team = await game_page.text_content("[data-testid='game-guest']")
        
        away_point_element = await game_page.query_selector('//div[@data-testid="game-guest"]/preceding-sibling::div[1]')
        away_point = await away_point_element.text_content() if away_point_element else "N/A"

        # Validate match date
        game_time = await game_page.text_content("[data-testid='game-time-item']")
        game_datetime = parse_oddsportal_date_to_datetime(game_time).strftime("%Y-%m-%d %H:%M")
        game_temporal_position = check_season_position(season, game_datetime, season_boundary="08-01")
        if game_temporal_position == 1:
            print(f"Skipping match before season start date: {game_datetime} for season {season}")
            return 1
        if game_temporal_position == 3:
            print(f"Skipping match after season end date: {game_datetime} for season {season}")
            return None

        event_data = {
            "home_team": home_team.strip() if home_team else "N/A",
            "away_team": away_team.strip() if away_team else "N/A",
            "date_time": game_datetime,
            "score": f"{home_point}-{away_point}",
            "odds": {
                "home_win_odds": [],
                "draw_odds": [],
                "away_win_odds": []
            }
        }

        # Find the bookmaker section
        pattern_bookmaker = rf"^{bookmaker_name}(?:\.[a-z]+)?$"
        link_bookmaker = game_page.locator('a > p', has_text=re.compile(pattern_bookmaker, re.IGNORECASE))

        # get competition and region
        competition_link = await get_competition_link(game_page)
        region_name, competition_name = extract_region_competition(competition_link)
        
        if await link_bookmaker.count() > 0:
            bookmaker_block = link_bookmaker.locator("xpath=../../..")
            await bookmaker_block.wait_for(state="visible")
            odds_cells = bookmaker_block.locator('[data-testid="odd-container"]')
            
            for i in range(await odds_cells.count()):
                for _ in range(3):
                    try:
                        await odds_cells.nth(i).wait_for(state="visible", timeout=10000)
                        break
                    except Exception as e:
                        print(f"Retrying to find odds cell due to: {e}")
                        await goto_with_retry(game_page, game_url)
                        if _ == 2:
                            print(f"Skipping odds extraction due to persistent load issues: {game_url}")
                            break
                #await expect(odds_cells.nth(i)).to_be_visible(timeout=10000)
                await odds_cells.nth(i).click(force=True)
                
                # Extraction of odds and timestamps
                try:
                    odds_text = None
                    try:
                        for _ in range(3):
                            await game_page.wait_for_selector('h3:text("Odds movement")', timeout=10000)
                            odds_headers = game_page.locator("h3", has_text="Odds movement")
                            await odds_headers.wait_for(state="visible")

                            if await odds_headers.count() > 0:
                                odds_block = odds_headers.locator("..")
                                await odds_block.wait_for(state="attached", timeout=10000)
                                odds_text = await odds_block.text_content()
                                break
                            await asyncio.sleep(2)
                            if _ > 2:
                                await odds_cells.nth(i).click(force=True)
                        if odds_text is None:
                            print("Odds movement not found after 3 retries") # rouvrir une nouvelle page 
                    except Exception as e:
                        print(f"Error while trying to find odds movement: {e}")
                    
                    odds_text = await odds_block.text_content()
                    pattern = r"(\d{1,2} \w{3,}, \d{2}:\d{2})([0-9]+\.[0-9]+)"
                    matches_odds_datetime = re.findall(pattern, odds_text)
                    
                    for date_odds_str, value in matches_odds_datetime:
                        date_odds = add_missing_year(date_odds_str, game_datetime)
                        if i == 0:
                            event_data["odds"]["home_win_odds"].append({
                                "value": float(value),
                                "date_time": date_odds
                            })
                        elif i == 1:
                            event_data["odds"]["draw_odds"].append({
                                "value": float(value),
                                "date_time": date_odds
                            })
                        elif i == 2:
                            event_data["odds"]["away_win_odds"].append({
                                "value": float(value),
                                "date_time": date_odds
                            })
                except Exception as e:
                    print(f"Failed to extract odds: {e}")
                
                await game_page.mouse.move(0, 0)

        return event_data, (region_name, competition_name)
        
    except Exception as e:
        print(f"Failed to process match {game_url}: {e}")
        return None


@pytest.mark.asyncio
async def process_game(context, game_url, bookmaker_name, season, type_historical="competition"):
    """
    Asynchronously processes a single game for testing with pytest-asyncio.

    The function opens a new page in the given context and attempts to:
    1. Retrieve match details using `get_match_details`.
    2. Extract home and away team links using `get_team_links`.

    If the match occurs before the allowed historical date limit and
    `type_historical` is "competition", processing is stopped. 

    Returns a tuple containing:
    - event_data
    - (home_team_link, away_team_link)
    - the game_page object
    - region and competition names

    Handles exceptions by printing an error message and returning None.
    Ensures the game page is closed in the `finally` block if not already closed.
    """
    game_page = await context.new_page()
    try:
        event_data, region_competion_names = await get_match_details(game_page, game_url, bookmaker_name, season)
        home_team_link, away_team_link = await get_team_links(game_page)
        if event_data == 1 and type_historical == "competition":
            print("Stop processing due to exeded date limit for team historical data")
            return None
        return event_data, (home_team_link, away_team_link), game_page, region_competion_names
    except Exception as e:
        print(f"Failed to process match {game_url}: {e}")
        return None
    finally:
        if not game_page.is_closed():
            await game_page.close()


async def limited_process_game(semaphore, ctx, url, bookmaker_name, season, type_historical="competition"):
    """
    Asynchronously processes a single game with concurrency control.

    The function acquires a semaphore before calling `process_game` to ensure
    that only a limited number of games are processed concurrently. It passes
    all necessary arguments to `process_game` and returns its result.
    """
    async with semaphore:
        return await process_game(ctx, url, bookmaker_name, season, type_historical="competition")
    

async def get_history_matchs_urls(page, url, season):
    """
    Asynchronously retrieves match URLs for a given competition page and season.

    The function attempts to select game elements from the page, retrying up to 3 times
    if an exception occurs. It handles several cases:
    - Returns an empty list if no match URLs are found after retries.
    - Skips matches that occur before the season start date, returning the URLs
    found so far or None if none were found.

    Returns a list of game URLs for the specified season.
    """

    game_urls = []
    while True:
        # Wait for the game list to load
        try:
            for _ in range(3):
                try:
                    await page.wait_for_selector("a.next-m\\:flex > div[data-testid='game-row']", state='visible', timeout=15000)
                    break
                except Exception as e:
                    print(f"Failed to load game list: {e}")
                    await goto_with_retry(page, url)
                    await asyncio.sleep(2)
                    if _ == 2:
                        print("Skipping due to persistent load issues on game list")
        except Exception as e:
            continue
        
        # Extract game URLs
        for _ in range(3):
            try:
                game_elements = await page.query_selector_all("a.next-m\\:flex > div[data-testid='game-row']")
                if game_elements:
                    break
            except Exception as e:
                print(f"Retrying to find game elements due to: {e}")
                await asyncio.sleep(2)
                if _ == 2:
                    print("No game elements found after 3 retries")
                    return []
        
        for element in game_elements:
            # Try to get the href directly
            parent_a = await element.evaluate_handle('el => el.parentElement')
            href = await parent_a.get_attribute('href')
            
            if href and not href.startswith('javascript:'):
                full_url = f"https://www.oddsportal.com{href}"
                season_game = extract_season(full_url)
                if season_game is not None:
                    game_datetime = season_to_date(season_game)
                    game_temporal_position = check_season_position(season, game_datetime, season_boundary="08-01")
                    if game_temporal_position == 1:
                        print(f"Skipping match before season start date: {game_datetime} for season {season}")
                        if game_urls:
                            return game_urls
                        else:
                            return None
                    if game_temporal_position == 3:
                        print(f"Skipping match after season end date: {game_datetime} for season {season}")
                        continue
                game_urls.append(full_url)
                print(f"Fetched match URL: {full_url}")
            else:
                # Alternative: click and get current URL
                try:
                    await parent_a.click()
                    await asyncio.sleep(1)
                    current_url = page.url
                    if current_url and 'match' in current_url:
                        game_urls.append(current_url)
                        print(f"Fetched match URL via click: {current_url}")
                    await page.go_back()
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Failed to retrieve URL for an item: {e}")

        print(f"Number of match URLs retrieved: {len(game_urls)}")
        # Check if there's a next page
        next_page = page.locator('a.pagination-link', has_text="Next")
        try:
            if not await next_page.is_visible() or not await next_page.is_enabled():
                break
            await next_page.click(timeout=5000)
            await page.wait_for_load_state("networkidle") 
        except TimeoutError:
            break 
            
    if not game_urls:
        print("No match URLs found.")
        return []
    else:
        return game_urls