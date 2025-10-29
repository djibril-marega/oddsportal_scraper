from datetime import datetime
import re

def parse_oddsportal_date_to_datetime(date_str, reference_date=None):
    """
    Parses OddsPortal dates into datetime objects.
    Simplified version but just as robust.
    """
    if isinstance(date_str, datetime):
        return date_str
    
    if not isinstance(date_str, str):
        return None
    
    if reference_date is None:
        reference_date = datetime.now()
    elif isinstance(reference_date, str):
        try:
            reference_date = datetime.strptime(reference_date, "%Y-%m-%d %H:%M")
        except ValueError:
            reference_date = datetime.now()
    
    date_str = date_str.strip().lower()
    
    # Mapping months
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # unical regex pattern to capture date components
    pattern = r'(?:(\w+),)?\s*(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?[,\s]*(\d{1,2}):(\d{2})'
    
    match = re.search(pattern, date_str, re.IGNORECASE)
    if not match:
        return None
    
    # extract components
    _, day_str, month_str, year_str, hour_str, minute_str = match.groups()
    
    try:
        # Convert components to integers
        day = int(day_str)
        month = month_map.get(month_str.lower()[:3])
        if not month:
            return None
        
        hour = int(hour_str)
        minute = int(minute_str)
        

        if year_str:
            year = int(year_str)
        else:
            year = reference_date.year
            # create a temporary date to compare
            temp_date = datetime(year, month, day, hour, minute)
            days_diff = (temp_date - reference_date).days
            
            # Adjust year if the date is more than 6 months away
            if days_diff > 180:
                year -= 1
            elif days_diff < -180:
                year += 1
        
        return datetime(year, month, day, hour, minute)
    except (ValueError, TypeError):
        print(f"parse_oddsportal_date_to_datetime: error parsing components")
        return None


def add_missing_year(odds_date_input, match_datetime):
    """Adds missing year to OddsPortal date strings"""
    dt = parse_oddsportal_date_to_datetime(odds_date_input, match_datetime)
    if dt is None:
        print(f"Failed to parse date: {odds_date_input} with reference {match_datetime}")
        return None
    return dt.strftime("%Y-%m-%d %H:%M")