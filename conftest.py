def pytest_addoption(parser):
    parser.addoption("--sport", action="store", default="Football", help="sport name (eg. Football, Tennis)")
    parser.addoption("--region", action="store", default="England", help="region name (eg. England, France)")
    parser.addoption("--competition", action="store", default=None, help="competition name (eg. Premier League, Ligue 1)")
    parser.addoption("--season", action="store", default="2024/2025", help="season (eg. 2023/2024, 2022/2023)")
    parser.addoption("--bookmaker", action="store", default="Betclic", help="bookmaker name (eg. Pinnacle, Bet365)")
    parser.addoption("--team", action="store", default=None, help="team name (eg. Machester United, PSG, Real madrid)")
    parser.addoption("--teamid", action="store", default=None, help="team id (eg. nVp0wiqd)")
