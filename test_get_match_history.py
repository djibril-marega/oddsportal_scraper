import asyncio
import re
from playwright.async_api import TimeoutError
import pytest
from test_website_navigation import goto_with_retry, remove_overlays, handle_cookie_consent
from manage_date import add_missing_year, parse_oddsportal_date_to_datetime
from manage_links import get_team_links, get_competition_link
from extract_data import extract_region_competition, extract_season
from date_sorting import check_season_position, season_to_date
import traceback


@pytest.mark.asyncio
async def get_match_details(game_page, game_url, bookmaker_name, season): 
    """
    Asynchronously retrieves detailed information for a single match.
    Handles odds extraction that appears on hover.
    """

    try:
        print(f"Navigating to match URL: {game_url}")
        success = await goto_with_retry(game_page, game_url)
        if not success:
            await game_page.close()
            print(f"Skipping match due to load failure: {game_url}")
            return None

        # ✅ GESTION DES POPUPS BLOQUANTES
        try:
            # Bannière cookies (OneTrust)
            await handle_cookie_consent(game_page)

            # Supprime les overlays bloquants
            await remove_overlays(game_page) 
        except Exception as e:
            print(f"Popup handling failed: {e}")

        # Attendre la fin du chargement
        try:
            await game_page.wait_for_selector("div[class*='Loader']", state="detached", timeout=15000)
        except Exception:
            print("Loader not detected or already gone.")

        await remove_overlays(game_page)
        await asyncio.sleep(2)

        # Attendre les éléments principaux
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

        # Extraction des infos du match
        home_team = await game_page.text_content("[data-testid='game-host']")
        home_point_element = await game_page.query_selector('[data-testid="game-host"] + div')
        home_point = await home_point_element.text_content() if home_point_element else "N/A"

        away_team = await game_page.text_content("[data-testid='game-guest']")
        away_point_element = await game_page.query_selector('//div[@data-testid="game-guest"]/preceding-sibling::div[1]')
        away_point = await away_point_element.text_content() if away_point_element else "N/A"

        # Date du match
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
            "odds": {"home_win_odds": [], "draw_odds": [], "away_win_odds": []}
        }

        # Trouver la section du bookmaker
        pattern_bookmaker = rf"^{bookmaker_name}(?:\.[a-z]+)?$"
        link_bookmaker = game_page.locator('a > p', has_text=re.compile(pattern_bookmaker, re.IGNORECASE))

        # Extraire région et compétition
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
                        await game_page.mouse.move(0, 0)
                        if _ == 2:
                            print(f"Skipping odds extraction due to persistent load issues: {game_url}")
                            break

                # ✅ Survoler la cote
                try:
                    await remove_overlays(game_page)
                    await odds_cells.nth(i).hover()
                    await asyncio.sleep(1.5)
                except Exception as e:
                    print(f"Hover failed: {e}")
                    continue

                # Extraire les cotes affichées
                try:
                    odds_block = None
                    odds_text = None
                    for _ in range(3):
                        try:
                            await game_page.wait_for_selector("h3:has-text('Odds movement')", timeout=12000)
                            odds_headers = game_page.locator("h3", has_text="Odds movement")
                            if await odds_headers.count() > 0:
                                odds_block = odds_headers.locator("..")
                                await odds_block.wait_for(state="attached", timeout=10000)
                                odds_text = await odds_block.text_content()
                                break
                        except Exception as e:
                            print(f"Retry {_+1}/3: Error while trying to find odds movement: {e}")
                            await remove_overlays(game_page) 
                            await asyncio.sleep(2)
                            await odds_cells.nth(i).hover()

                    if not odds_block or not odds_text:
                        print(f"No odds block found for {game_url}")
                        continue

                    pattern = r"(\d{1,2} \w{3,}, \d{2}:\d{2})([0-9]+\.[0-9]+)"
                    matches_odds_datetime = re.findall(pattern, odds_text)

                    for date_odds_str, value in matches_odds_datetime:
                        date_odds = add_missing_year(date_odds_str, game_datetime)
                        key = ["home_win_odds", "draw_odds", "away_win_odds"][i]
                        event_data["odds"][key].append({
                            "value": float(value),
                            "date_time": date_odds
                        })

                except Exception as e:
                    print(f"Failed to extract odds: {e}")

                await game_page.mouse.move(0, 0)

        return event_data, (region_name, competition_name)
        
    except Exception as e:
        print(f"Failed to process match {game_url}: {e}")
        traceback.print_exc()
        return None


@pytest.mark.asyncio
async def process_game(context, game_url, bookmaker_name, season, type_historical="competition"):
    """Asynchronously processes a single game with pytest-asyncio."""
    game_page = await context.new_page()
    try:
        result = await get_match_details(game_page, game_url, bookmaker_name, season)
        if not result:
            print(f"Skipping match due to failed details extraction: {game_url}")
            return None

        event_data, region_competion_names = result
        home_team_link, away_team_link = await get_team_links(game_page)
        if event_data == 1 and type_historical == "competition":
            print("Stop processing due to exceeded date limit for team historical data")
            return None
        return event_data, (home_team_link, away_team_link), game_page, region_competion_names
    except Exception as e:
        print(f"Failed to process match {game_url}: {e}")
        return None
    finally:
        if not game_page.is_closed():
            await game_page.close()


async def limited_process_game(semaphore, ctx, url, bookmaker_name, season, type_historical="competition"):
    """Processes a single game with concurrency control."""
    async with semaphore:
        return await process_game(ctx, url, bookmaker_name, season, type_historical)
    

async def get_history_matchs_urls(page, url, season):
    """Retrieves match URLs for a given competition page and season."""
    game_urls = []
    #await asyncio.sleep(5)
    await remove_overlays(page)
    while True:
        try:
            for _ in range(3):
                try:
                    await page.wait_for_selector("a.next-m\\:flex > div[data-testid='game-row']", state='visible', timeout=15000)
                    break
                except Exception as e:
                    print(f"Failed to load game list: {e}") 
                    #await goto_with_retry(page, url)
                    await asyncio.sleep(2)
                    if _ == 2:
                        print("Skipping due to persistent load issues on game list")
        except Exception:
            print("No game list found, ending URL retrieval.")
            continue
        
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
            parent_a = await element.evaluate_handle('el => el.parentElement')
            href = await parent_a.get_attribute('href')
            
            if href and not href.startswith('javascript:'):
                full_url = f"https://www.oddsportal.com{href}"
                season_game = extract_season(full_url)
                if season_game:
                    game_datetime = season_to_date(season_game)
                    game_temporal_position = check_season_position(season, game_datetime, season_boundary="08-01")
                    if game_temporal_position == 1:
                        print(f"Skipping match before season start date: {game_datetime} for season {season}")
                        return game_urls or None
                    if game_temporal_position == 3:
                        print(f"Skipping match after season end date: {game_datetime} for season {season}") 
                        continue
                game_urls.append(full_url)
                print(f"Fetched match URL: {full_url}")
            else:
                try:
                    await parent_a.click()
                    await asyncio.sleep(1)
                    current_url = await page.url
                    if current_url and 'match' in current_url:
                        game_urls.append(current_url)
                        print(f"Fetched match URL via click: {current_url}")
                    await page.go_back()
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Failed to retrieve URL for an item: {e}")

        print(f"Number of match URLs retrieved: {len(game_urls)}")

        next_page = page.locator('a.pagination-link', has_text="Next")
        try:
            # Attendre que le bouton soit attaché, visible et stable
            await next_page.wait_for(state="attached", timeout=10000)
            await next_page.wait_for(state="visible", timeout=10000)
            #await next_page.wait_for(state="stable", timeout=10000)
            
            # Vérifier qu'il est cliquable
            if not await next_page.is_enabled():
                print("No more pages to navigate.")
                break
            
            # Scroll pour éviter overlay
            await next_page.scroll_into_view_if_needed() 
            await next_page.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # petite pause pour que les éléments se chargent
        except TimeoutError:
            print("No more pages to navigate.")
            break
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break
            
    if not game_urls:
        print("No match URLs found.")
        return []
    else:
        return game_urls
