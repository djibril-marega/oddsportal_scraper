import asyncio
import pytest
import re
from playwright.async_api import expect, TimeoutError
import random, asyncio

@pytest.mark.asyncio
async def goto_with_retry(page, url, retries=3, timeout=30000):
    """
    Asynchronously navigates to a URL with retry logic for pytest-asyncio.

    The function attempts to load the given page up to `retries` times, waiting for
    the DOM content to be loaded. If a navigation attempt fails, it retries with
    an exponential backoff (2, 4, 6 seconds, etc.).

    Parameters:
    - page: The Playwright page object to navigate.
    - url: The target URL to open.
    - retries: Maximum number of navigation attempts (default: 3).
    - timeout: Page load timeout in milliseconds (default: 30000).

    Returns:
    - True if the page was successfully loaded.
    - False if all attempts failed.
    """

    for attempt in range(1, retries+1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return True
        except Exception as e:
            print(f"Attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                await asyncio.sleep(2 * attempt)  # Exponential backoff
            else:
                print(f"Failed to load page after {retries} attempts: {url}")
                return False

async def handle_cookie_consent(page):
    """
    Handles cookie consent pop-ups on a webpage.

    The function searches for a button with a name matching "Accept" (case-insensitive)
    and clicks it if it is visible within 5 seconds. A short delay is added after clicking
    to ensure the action is processed. Any exceptions are silently ignored.
    """
    try:
        accept_cookies = page.get_by_role("button", name=re.compile("Accept", re.IGNORECASE))
        if await accept_cookies.is_visible(timeout=5000):
            await accept_cookies.click()
            await asyncio.sleep(1)
    except:
        pass

async def restart_browser_context(batch_size, i, game_urls, browser, context, p):  
    """
    Restarts the browser context after processing a batch of pages.

    This function is intended to refresh or reset the browser context to prevent
    memory leaks or stale sessions when handling large numbers of game URLs.
    It returns the updated browser and context objects.
    """
    if i + batch_size < len(game_urls):
        print("Restarting browser and context to avoid memory/leak issues...")
        await context.close()
        await browser.close()
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        for _ in range(3):
            try:
                await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
                break
            except TimeoutError:
                print("Retrying navigation...")
                if _ > 1:
                    await context.close()
                    await browser.close()
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()
            await asyncio.sleep(random.uniform(3, 6))
        await handle_cookie_consent(page)
        await page.close()
    return browser, context 

async def wait_for_locator(locator, retries=3, timeout=5000):
    for _ in range(retries):
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return True
        except:
            await asyncio.sleep(1)
    return False