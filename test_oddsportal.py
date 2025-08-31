import re
import asyncio
from playwright.async_api import async_playwright, expect, Page
import pytest
from datetime import datetime 
from manage_date import add_missing_year, parse_oddsportal_date_to_datetime
from save_data import save_odds_data
import random, asyncio

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


async def handle_cookie_consent(page: Page):
    try:
        accept_cookies = page.get_by_role("button", name=re.compile("Accept", re.IGNORECASE))
        if await accept_cookies.is_visible(timeout=5000):
            await accept_cookies.click()
            await asyncio.sleep(1)
    except:
        pass

async def goto_with_retry(page, url, retries=3, timeout=30000):
    for attempt in range(1, retries+1):
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            return True
        except Exception as e:
            print(f"Attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                await asyncio.sleep(2 * attempt)  # Exponential backoff
            else:
                print(f"Failed to load page after {retries} attempts: {url}")
                return False

@pytest.mark.asyncio
async def process_game(context, game_url, bookmaker_name):
    # Open a new page for each game
    game_page = await context.new_page()
    
    try:
        print(f"Navigating to match URL: {game_url}")
        success = await goto_with_retry(game_page, game_url)
        if not success:
            await game_page.close()
            print(f"Skipping match due to load failure: {game_url}")
            return None
        
        # Await the main elements to load
        await game_page.wait_for_selector("[data-testid='game-host']", timeout=15000)
        
        # Extract game details
        home_team = await game_page.text_content("[data-testid='game-host']")
        
        home_point_element = home_point_element = await game_page.query_selector('[data-testid="game-host"] + div')
        home_point = await home_point_element.text_content() if home_point_element else "N/A"
        
        away_team = await game_page.text_content("[data-testid='game-guest']")
        
        away_point_element = await game_page.query_selector('//div[@data-testid="game-guest"]/preceding-sibling::div[1]')
        away_point = await away_point_element.text_content() if away_point_element else "N/A"

        game_time = await game_page.text_content("[data-testid='game-time-item']")
        game_datetime = parse_oddsportal_date_to_datetime(game_time)
        
        event_data = {
            "home_team": home_team.strip() if home_team else "N/A",
            "away_team": away_team.strip() if away_team else "N/A",
            "date_time": game_datetime.strftime("%Y-%m-%d %H:%M"),
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
        
        if await link_bookmaker.count() > 0:
            bookmaker_block = link_bookmaker.locator("xpath=../../..")
            await bookmaker_block.wait_for(state="visible")
            odds_cells = bookmaker_block.locator('[data-testid="odd-container"]')
            
            for i in range(await odds_cells.count()):
                await expect(odds_cells.nth(i)).to_be_visible(timeout=5000)
                await odds_cells.nth(i).hover(force=True)
                
                # Extraction of odds and timestamps
                try:
                    odds_text = None
                    for _ in range(3):
                        odds_headers = game_page.locator("h3", has_text="Odds movement")
                        if await odds_headers.count() > 0:
                            odds_block = odds_headers.locator("..")
                            await odds_block.wait_for(state="visible", timeout=3000)
                            odds_text = await odds_block.text_content()
                            break
                        await asyncio.sleep(1)
                    if odds_text is None:
                        print("Odds movement not found after 3 retries")
                    
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
        
        await game_page.close()
        return event_data
        
    except Exception as e:
        print(f"Failed to process match {game_url}: {e}")
        await game_page.close()
        return None
    finally:
        if not game_page.is_closed():
            await game_page.close()

@pytest.mark.asyncio()
async def test_get_historical_events(sport_name, region_name, competition_name, season, bookmaker_name):
    # Use Playwright to navigate and extract data
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = await context.new_page()

        await page.goto("https://www.oddsportal.com/standings", wait_until='networkidle')
        
        # Manage cookie consent if present
        await handle_cookie_consent(page)
        
        # Navigate through the site to reach the desired competition and season
        await page.locator('li[data-testid="sport-tab-list-item"]', has_text=sport_name).first.click()
        await asyncio.sleep(2)
        
        await page.get_by_role("link", name=region_name).first.click()
        await asyncio.sleep(2)
        
        pattern_competition = rf"^{competition_name} \(\d+\)$"
        await page.get_by_role("link", name=re.compile(pattern_competition)).click()
        await asyncio.sleep(2)
        
        await page.get_by_role("link", name="Results").first.click()
        await asyncio.sleep(2)
        
        await page.get_by_role("link", name=season).click()
        await asyncio.sleep(2)

        game_urls = []
        while True:
            # Wait for the game list to load
            await page.wait_for_selector("a.next-m\\:flex > div[data-testid='game-row']", state='visible', timeout=15000)
            
            # Extract game URLs
            game_elements = await page.query_selector_all("a.next-m\\:flex > div[data-testid='game-row']")
            
            for element in game_elements:
                # Try to get the href directly
                parent_a = await element.evaluate_handle('el => el.parentElement')
                href = await parent_a.get_attribute('href')
                
                if href and not href.startswith('javascript:'):
                    full_url = f"https://www.oddsportal.com{href}"
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
                            print(f"URL du match (via click): {current_url}")
                        await page.go_back()
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Failed to retrieve URL for an item: {e}")

            print(f"Number of match URLs retrieved: {len(game_urls)}")
            # Check if there's a next page
            next_page = page.locator('a.pagination-link', has_text="Next")
            if not await next_page.is_visible() or not await next_page.is_enabled():
                break
            await next_page.click()
        
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
            print("Aucune URL de match valide trouvée")
            # Closing context and browser before returning
            await context.close()
            await browser.close()
            return

        # Limit the number of concurrent pages to avoid overwhelming the browser
        semaphore = asyncio.Semaphore(3)  # 3 concurrent pages

        async def limited_process_game(ctx, url):
            async with semaphore:
                return await process_game(ctx, url, bookmaker_name)

        # Batch processing configuration
        batch_size = 30  # reduced batch size to limit memory usage
        odds_data["events"] = []

        for i in range(0, len(game_urls), batch_size):
            batch = game_urls[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(game_urls)+batch_size-1)//batch_size} "
                f"({len(batch)} matches)...")

            # Process each batch of games
            tasks = [limited_process_game(context, url) for url in batch]
            results = await asyncio.gather(*tasks)
            odds_data["events"].extend([r for r in results if r is not None])

            # Close all pages in the context to free memory
            for page in context.pages:
                try:
                    await page.close()
                except:
                    pass

            # Random sleep between batches to mimic human behavior and avoid rate limiting
            await asyncio.sleep(random.uniform(2, 5))

            # Restart browser and context every batch to manage memory usage
            if i + batch_size < len(game_urls):
                print("Restarting browser and context to avoid memory/leak issues...")
                await context.close()
                await browser.close()
                browser = await p.chromium.launch()
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto("https://www.oddsportal.com", wait_until="networkidle")
                await handle_cookie_consent(page)
                await page.close()
        
        # Save the extracted data to a JSON file
        save_odds_data(odds_data)
        print(f"Number of successfully processed events: {len(odds_data['events'])}")
        
        # Close the browser context and browser
        await context.close()
        await browser.close()