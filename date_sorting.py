from datetime import datetime

def check_season_position(season: str, date_str: str, season_boundary: str) -> int:
    """
    Determines whether a date is before, during, or after a given season.

    Args:
        season (str): Season in the format "YYYY/YYYY" (e.g., "2024/2025")
        date_str (str): Date to check in the format "YYYY-MM-DD HH:MM" (e.g., "2024-08-16 20:45")
        season_boundary (str): Start/end month-day of the season in the format "MM-DD" (e.g., "08-01")

    Returns:
        int: 1, 2, or 3
    """

    start_year, end_year = map(int, season.split('/'))
    start_month, start_day = map(int, season_boundary.split('-'))
    
    # difine start and end dates of the season
    start_date = datetime(start_year, start_month, start_day)
    end_date = datetime(end_year, start_month, start_day)
    
    # convert input date string to datetime object
    current_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    
    # determine position of current_date relative to the season
    if current_date < start_date:
        return 1
    elif current_date >= start_date and current_date < end_date:
        return 2
    else:
        return 3

def season_to_date(season: str) -> str | None:
    """
    Converts a season in the format 'YYYY-YYYY' to a date in the format 'MM-DD-YYYY'.
    Example: '2017-2018' -> '12-31-2017'
    """
    try:
        start_year = int(season.split('-')[0])
        date = datetime(start_year, 12, 31, 0, 0)
        return date.strftime("%Y-%m-%d 00:00")
    except (ValueError, IndexError):
        return None
