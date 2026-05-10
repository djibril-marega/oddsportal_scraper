import os
import json
import re

def normalize_name(name):
    """Convertit le nom en minuscules et remplace les espaces/underscores par un espace simple"""
    return re.sub(r'[_\s]+', ' ', name.strip().lower())

def update_competition_files(folder_path, mappings):
    updated_files = []

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(folder_path, filename)

        # Charger le fichier JSON
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Erreur JSON : {filepath}")
                continue

        modified = False

        for mapping in mappings:
            region = mapping["region"]
            comp_true = mapping["competition_True"]
            comp_false = mapping["competition_false"]

            # Normaliser noms
            norm_filename = normalize_name(filename)
            norm_comp_false = normalize_name(comp_false)
            norm_region = normalize_name(region)

            # Vérifier que le fichier correspond au pays ET à la compétition à remplacer
            if norm_region in norm_filename and norm_comp_false in norm_filename:
                # Remplacer dans le nom du fichier
                new_filename = re.sub(re.escape(comp_false), comp_true, filename, flags=re.IGNORECASE)

                # Modifier le champ "competition" dans le JSON
                if "competition" in data:
                    norm_json_comp = normalize_name(data["competition"])
                    if norm_json_comp == norm_comp_false:
                        data["competition"] = comp_true
                        modified = True

                # Renommer le fichier si nécessaire
                if new_filename != filename:
                    new_filepath = os.path.join(folder_path, new_filename)
                    os.rename(filepath, new_filepath)
                    filepath = new_filepath
                    filename = new_filename
                    modified = True

        # Réécrire le JSON si modifié
        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            updated_files.append(filename)

    return updated_files



mappings = [
    {"region": "Chile", "competition_True": "Liga de Primera", "competition_false": "Primera-Division"}
]
updated = update_competition_files("./scraped_data", mappings)
print("Fichiers mis à jour :", updated)


import os
import json
import re

def competitions_summary(folder_path):
    """
    Parcourt tous les fichiers JSON et retourne :
    - un dictionnaire associant chaque pays à ses compétitions uniques
    - le nombre total de compétitions uniques toutes régions confondues
    """
    country_competitions = {}

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(folder_path, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

        # Déduire le pays depuis le nom du fichier (ex: Football_Colombia_Liga_Aguila.json)
        match = re.search(r'_(\w+)_', filename)
        country = match.group(1) if match else data.get("region", "Unknown")

        competition = data.get("competition")
        if competition:
            country_competitions.setdefault(country, set()).add(competition)

    # Convertir les sets en listes triées
    for country in country_competitions:
        country_competitions[country] = sorted(country_competitions[country])

    # Nombre total de compétitions uniques toutes régions confondues
    total_competitions = len(set(
        comp for comps in country_competitions.values() for comp in comps
    ))

    return total_competitions, country_competitions




# Récupérer toutes les compétitions uniques dans un set
total, competitions_by_country = competitions_summary("./scraped_data")

print(f"Nombre total de compétitions uniques : {total}\n")
for country, comps in competitions_by_country.items():
    print(f"{country} : {comps} (total {len(comps)})")



