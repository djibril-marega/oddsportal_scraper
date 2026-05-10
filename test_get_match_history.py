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


def fractional_to_decimal(frac):
    num, den = map(float, frac.split('/'))
    return round((num / den) + 1, 2)


def american_to_decimal(value):
    v = int(value)
    return round((v / 100) + 1, 2) if v > 0 else round((100 / abs(v)) + 1, 2)


@pytest.mark.asyncio
async def get_match_details(game_page, game_url, bookmaker_name, season):

    try:
        print(f"Navigating to match URL: {game_url}")

        success = await goto_with_retry(game_page, game_url)
        if not success:
            await game_page.close()
            return None

        # POPUPS
        try:
            await handle_cookie_consent(game_page)
            await remove_overlays(game_page)
        except Exception as e:
            print(f"Popup handling failed: {e}")

        try:
            await game_page.wait_for_selector("div[class*='Loader']", state="detached", timeout=15000)
        except:
            pass

        await remove_overlays(game_page)
        await asyncio.sleep(2)

        # MATCH INFO
        await game_page.wait_for_selector("[data-testid='game-host']", timeout=10000)

        home_team = await game_page.text_content("[data-testid='game-host']")
        away_team = await game_page.text_content("[data-testid='game-guest']")
        game_time = await game_page.text_content("[data-testid='game-time-item']")

        game_datetime = parse_oddsportal_date_to_datetime(game_time).strftime("%Y-%m-%d %H:%M")

        game_temporal_position = check_season_position(season, game_datetime, season_boundary="08-01")

        if game_temporal_position == 1:
            return 1
        if game_temporal_position == 3:
            return None

        event_data = {
            "home_team": home_team.strip(),
            "away_team": away_team.strip(),
            "date_time": game_datetime,
            "score": "N/A",
            "odds": {
                "home_win_odds": [],
                "draw_odds": [],
                "away_win_odds": []
            }
        }

        # BOOKMAKER SELECTION
        pattern_bookmaker = rf"^{bookmaker_name}(?:\.[a-z]+)?$"
        link_bookmaker = game_page.locator(
            'a > p',
            has_text=re.compile(pattern_bookmaker, re.IGNORECASE)
        )

        competition_link = await get_competition_link(game_page)
        region_name, competition_name = extract_region_competition(competition_link)

        if await link_bookmaker.count() > 0:

            bookmaker_block = link_bookmaker.locator("xpath=../../..")
            await bookmaker_block.wait_for(state="visible")

            odds_cells = bookmaker_block.locator('[data-testid="odd-container"]')

            for i in range(await odds_cells.count()):

                cell = odds_cells.nth(i)

                # =========================
                # FR: HOVER
                # =========================
                try:
                    await remove_overlays(game_page)
                    await cell.hover()
                    await asyncio.sleep(1)
                except:
                    pass

                # =========================
                # UK/US: CLICK MODAL
                # =========================
                try:
                    await cell.click()
                    await asyncio.sleep(1.5)
                except:
                    pass

                # =========================
                # MODAL (UK/US)
                # =========================
                modal = game_page.locator("div.fixed.z-50")

                odds_text = None

                try:
                    await modal.wait_for(state="visible", timeout=3000)

                    block = modal.locator("text=Odds movement")
                    await block.wait_for(timeout=3000)

                    odds_text = await block.locator("..").text_content()

                except:
                    # =========================
                    # FALLBACK FR INLINE
                    # =========================
                    try:
                        await game_page.wait_for_selector(
                            "h3:has-text('Odds movement')",
                            timeout=3000
                        )

                        odds_header = game_page.locator(
                            "h3",
                            has_text="Odds movement"
                        )

                        if await odds_header.count() > 0:
                            odds_text = await odds_header.locator("..").text_content()

                    except Exception as e:
                        print(f"Odds not found: {e}")
                        continue

                if not odds_text:
                    continue

                # =========================
                # PARSING
                # =========================
                pattern = r"(\d{1,2} \w{3,}, \d{2}:\d{2})([0-9]+(?:\.[0-9]+|/[0-9]+|[+-][0-9]+))"

                matches = re.findall(pattern, odds_text)

                for date_str, value in matches:

                    date_odds = add_missing_year(date_str, game_datetime)
                    key = ["home_win_odds", "draw_odds", "away_win_odds"][i]

                    try:
                        if "/" in value:
                            value = fractional_to_decimal(value)

                        elif value.startswith("+") or value.startswith("-"):
                            value = american_to_decimal(value)

                        else:
                            value = float(value)

                    except:
                        continue

                    event_data["odds"][key].append({
                        "value": float(value),
                        "date_time": date_odds
                    })

                await game_page.mouse.move(0, 0)

        return event_data, (region_name, competition_name)

    except Exception as e:
        print(f"Error processing match {game_url}: {e}")
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
