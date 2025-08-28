from datetime import datetime
import re

def parse_oddsportal_date_to_datetime(date_str, reference_date=None):
    """
    Parse les dates d'OddsPortal en objets datetime
    Version simplifiée mais tout aussi robuste
    """
    if isinstance(date_str, datetime):
        return date_str
    
    if not isinstance(date_str, str):
        return None
    
    if reference_date is None:
        reference_date = datetime.now()
    
    date_str = date_str.strip().lower()
    
    # Mapping des mois (version simplifiée)
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # Pattern unique plus flexible
    pattern = r'(?:(\w+),)?\s*(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?[,\s]*(\d{1,2}):(\d{2})'
    
    match = re.search(pattern, date_str, re.IGNORECASE)
    if not match:
        return None
    
    # Extraire les composants
    _, day_str, month_str, year_str, hour_str, minute_str = match.groups()
    
    try:
        # Convertir les composants
        day = int(day_str)
        month = month_map.get(month_str.lower()[:3])
        if not month:
            return None
        
        hour = int(hour_str)
        minute = int(minute_str)
        
        # Gérer l'année
        if year_str:
            year = int(year_str)
        else:
            year = reference_date.year
            # Créer une date temporaire pour l'ajustement d'année
            temp_date = datetime(year, month, day, hour, minute)
            days_diff = (temp_date - reference_date).days
            
            # Ajuster l'année si nécessaire
            if days_diff > 180:
                year -= 1
            elif days_diff < -180:
                year += 1
        
        return datetime(year, month, day, hour, minute)
    except (ValueError, TypeError):
        return None

# La fonction add_missing_year reste identique
def add_missing_year(odds_date_input, match_datetime):
    dt = parse_oddsportal_date_to_datetime(odds_date_input, match_datetime)
    if dt is None:
        print(f"Erreur lors du traitement de la date '{odds_date_input}'")
        return None
    return dt.strftime("%Y-%m-%d %H:%M")