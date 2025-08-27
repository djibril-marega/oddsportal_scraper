import re
from playwright.sync_api import Page, expect
import pytest
from datetime import datetime

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

def test_get_historical_events(page: Page, sport_name, region_name, competition_name, season, bookmaker_name):
    page.goto("https://www.oddsportal.com/standings")
    # Navigate through the site to reach the desired sport, competition and season
    page.locator('li[data-testid="sport-tab-list-item"]', has_text=sport_name).first.click()
    page.get_by_role("link", name=region_name).click()
    pattern_competition = rf"^{competition_name} \(\d+\)$"
    page.get_by_role("link", name=re.compile(pattern_competition)).click()
    page.get_by_role("link", name="Results").first.click()
    page.get_by_role("link", name=season).click()

    # Select all game links
    page.wait_for_selector("a.next-m\\:flex > div[data-testid='game-row']", state='visible')
    all_page_games = page.locator("a.next-m\\:flex > div[data-testid='game-row']").all()
    print(f"Nombre total d'éléments trouvés: {len(all_page_games)}")
    odds_data = {
        "sport": sport_name,
        "region": region_name,
        "competition": competition_name,
        "season": season,
        "market": "1X2 and Fulltime result",
        "bookmaker": bookmaker_name,
        "events": []
    }

    # Iterate through each game link and extract details
    for game in all_page_games:
        # Click on the game to get detailed information
        game.click()

        # Extract teams and scores
        home_team = page.text_content("[data-testid='game-host']")
        home_point = page.query_selector('[data-testid="game-host"] + div').text_content()
        away_team = page.text_content("[data-testid='game-guest']")
        away_point = page.query_selector('//div[@data-testid="game-guest"]/preceding-sibling::div[1]').text_content()

        # Extract date and time of the match
        game_time = page.text_content("[data-testid='game-time-item']")
        game_datetime = datetime.strptime(game_time, "%A,%d %B %Y,%H:%M")
        odds_data["events"].append({
            "home_team": home_team,
            "away_team": away_team,
            "date_time": game_datetime.strftime("%Y-%m-%d %H:%M"),
            "score": f"{home_point}-{away_point}",
            "odds": {
                "home_win_odds": [],
                "draw_odds": [],
                "away_win_odds": []
            }
        })

        # Find the specified bookmaker in the list
        pattern_bookmaker = rf"^{bookmaker_name}(?:\.[a-z]+)?$"
        link_bookmaker = page.locator('a > p', has_text=re.compile(pattern_bookmaker, re.IGNORECASE))

        # Navigate to the bookmaker's odds table
        bookmaker_block = link_bookmaker.locator("xpath=../../..")
        bookmaker_block.wait_for(state="visible")

        # Extract odds cells
        odds_cells = bookmaker_block.locator('[data-testid="odd-container"]')


        for i in range(odds_cells.count()):
            expect(odds_cells.nth(i)).to_be_visible()
            odds_cells.nth(i).hover()
            odds_block = page.locator("h3", has_text="Odds movement").locator("..")
            odds_block.wait_for(state="visible", timeout=5000)
            
            # Get the odds movement text
            odds_text = odds_block.text_content()
            pattern = r"(\d{1,2} \w{3,}, \d{2}:\d{2})([0-9]+\.[0-9]+)"
            matches_odds_datetime = re.findall(pattern, odds_text)
            for date_odds_str, value in matches_odds_datetime:
                date_odds = datetime.strptime(date_odds_str + " 2025", "%d %B, %H:%M %Y")
                if i == 0:
                    odds_data["events"][-1]["odds"]["home_win_odds"].append({
                        "value": float(value),
                        "date_time": date_odds.strftime("%Y-%m-%d %H:%M")
                    })
                elif i == 1:
                    odds_data["events"][-1]["odds"]["draw_odds"].append({
                        "value": float(value),
                        "date_time": date_odds.strftime("%Y-%m-%d %H:%M")
                    })
                elif i == 2:
                    odds_data["events"][-1]["odds"]["away_win_odds"].append({
                        "value": float(value),
                        "date_time": date_odds.strftime("%Y-%m-%d %H:%M")
                    })
            page.mouse.move(0, 0) 
        
        page.go_back() 
    print(odds_data)


    page.pause()

# Chose a faire 
# - Touver le marché
# - Trouver le bookmaker dans la liste des bookmakers // fait
# depuis le nom de ce bookmaker, naviguer jusqu'au tableau des cotes //fait
# - Extraire les cotes du match //fait 
# - format json

# format json examples
# { sport: 'Football',
#   region: 'England',
#   competition: 'Premier League',
#   season: '2024/2025',
#   market: '1X2 and Fulltime result',
#   bookmaker: 'Betclic', 
#   events: [
#     { home_team: 'Arsenal', away_team: 'Manchester City', 
#       date_time: 'Sunday,25 May 2025,17:00',
#       score: '2-1',
#       odds: [
#         home_win_odds: [ 
#           { value: 1.85, date_time: '25 May, 16:59' },
#           { value: 1.80, date_time: '23 May, 15:10' }],
#         draw_odds: [ { value: 3.50, date_time: '25 May, 16:59' },
#                     { value: 3.60, date_time: '23 May, 15:10' }],
#         away_win_odds: [ { value: 4.20, date_time: '25 May, 16:59' }
#                       { value: 4.10, date_time: '23 May, 15:10' }],
#       ] },
#     { home_team: 'Chelsea', away_team: 'Liverpool', 
#       date_time: 'Saturday,24 May 2025,15:00',
#       score: '1-1',
#       odds: [
#         home_win_odds: [
#           { value: 2.10, date_time: '24 May, 14:59' },
#           { value: 2.00, date_time: '22 May, 13:10' }],
#         draw_odds: [ { value: 3.20, date_time: '24 May, 14:59' },
#                     { value: 3.30, date_time: '22 May, 13:10' }],
#         away_win_odds: [ { value: 3.80, date_time: '24 May, 14:59' }
#                       { value: 3.70, date_time: '22 May, 13:10' }],
#       ] },   
#   ]
#]}
