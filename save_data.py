import json
import os
from datetime import datetime

def save_odds_data(odds_data, base_dir="scraped_data", type_historical="competition", type_game="historcal"):
    """
    Save odds data to a JSON file with an descriptive filename.
    
    Args:
        odds_data (dict): The data to be saved
        base_dir (str): The base directory where files will be saved
    Returns:
        str: The file path where data was saved
    """
    # Create directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Generate a descriptive filename based on metadata and date
    sport = odds_data.get("sport", "unknown_sport")
    region = odds_data.get("region", "unknown_region")
    competition = odds_data.get("competition", "unknown_competition")
    season = odds_data.get("season", "unknown_season")
    bookmaker = odds_data.get("bookmaker", "unknown_bookmaker")
    
    # Clean names for filesystem safety
    def clean_filename(text):
        # Replace problematic characters
        text = text.replace('/', '-')  # Replace slashes with hyphens
        text = text.replace('\\', '-')  # Replace backslashes with hyphens
        text = text.replace(':', '-')   # Replace colons with hyphens
        text = text.replace('*', '-')   # Replace asterisks with hyphens
        text = text.replace('?', '-')   # Replace question marks with hyphens
        text = text.replace('"', '-')   # Replace double quotes with hyphens
        text = text.replace('<', '-')   # Replace less than with hyphens
        text = text.replace('>', '-')   # Replace greater than with hyphens
        text = text.replace('|', '-')   # Replace pipes with hyphens
        
        # Keep only alphanumeric characters, spaces, hyphens, and underscores
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if type_historical == "competition":
        if type_game == "upcoming":
            filename = f"{timestamp}_{clean_filename(sport)}_{clean_filename(region)}_{clean_filename(odds_data['competition'])}_{clean_filename(bookmaker)}_upcoming.json"
        else:
            filename = f"{timestamp}_{clean_filename(sport)}_{clean_filename(region)}_{clean_filename(odds_data['competition'])}_{clean_filename(season)}_{clean_filename(bookmaker)}.json"
    elif type_historical == "team":
        filename = f"{timestamp}_{clean_filename(sport)}_{clean_filename(odds_data['team'])}_team_{clean_filename(season)}_{clean_filename(bookmaker)}.json"
    
    # Full file path
    filepath = os.path.join(base_dir, filename)
    
    # Save data as formatted JSON
    json_str = json.dumps(odds_data, indent=2, ensure_ascii=False)

    # Calculer la taille en octets
    size_bytes = len(json_str.encode("utf-8"))

    # Vérifier si la taille dépasse 1 Ko
    if size_bytes > 1024:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Data successfully saved to: {filepath} ({size_bytes} bytes)")
    else:
        print(f"Data not saved due to small size ({size_bytes} octets)")
        

    return filepath