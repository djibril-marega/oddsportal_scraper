from datetime import datetime

def add_missing_year(odds_date_input, match_datetime):
    """
    Ajoute l'année manquante à une date de cotes en se basant sur la date du match.
    Prend en compte les changements d'année.
    
    Args:
        odds_date_input (str ou datetime): Date des cotes (string ou objet datetime)
        match_datetime (datetime): Date complète du match
    
    Returns:
        datetime: Date complète avec l'année appropriée
    """
    # Si l'entrée est déjà un objet datetime, le retourner directement
    if isinstance(odds_date_input, datetime):
        return odds_date_input
    
    # Si c'est une string, la traiter
    elif isinstance(odds_date_input, str):
        try:
            # Nettoyer la chaîne
            odds_date_str = odds_date_input.strip()
            
            # Parser la date des cotes sans année
            odds_date = datetime.strptime(odds_date_str, '%d %b, %H:%M')
            
            # Ajouter l'année du match par défaut
            odds_date = odds_date.replace(year=match_datetime.year)
            
            # Calculer la différence en jours entre la date des cotes et la date du match
            days_difference = (odds_date - match_datetime).days
            
            # Si la date des cotes est plus de 30 jours après la date du match,
            # c'est probablement de l'année précédente
            if days_difference > 30:
                odds_date = odds_date.replace(year=match_datetime.year - 1)
            # Si la date des cotes est plus de 330 jours avant la date du match,
            # c'est probablement de l'année suivante (cas moins fréquent)
            elif days_difference < -330:
                odds_date = odds_date.replace(year=match_datetime.year + 1)
            
            return odds_date.strftime("%Y-%m-%d %H:%M")
        except ValueError as e:
            print(f"Erreur lors de l'ajout de l'année à '{odds_date_input}': {e}")
            return None
    else:
        print(f"Type d'entrée non géré: {type(odds_date_input)}")
        return None