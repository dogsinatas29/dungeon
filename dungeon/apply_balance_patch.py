import csv
import os

DATA_DIR = 'data'

def parse_damage_range(val_str):
    if '-' in val_str:
        parts = val_str.split('-')
        return int(parts[0]), int(parts[1])
    else:
        return int(val_str), int(val_str)

def format_damage_range(min_val, max_val):
    if min_val == max_val:
        return str(min_val)
    return f"{min_val}-{max_val}"

def apply_player_nerf():
    filepath = os.path.join(DATA_DIR, 'classes.csv')
    print(f"Applying Player Nerf to {filepath}...")
    
    rows = []
    fieldnames = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            # Nerf stats by 0.6x
            for key in ['hp', 'mp', 'strength', 'mag', 'dex', 'vit']:
                if key in row:
                    original = int(row[key])
                    row[key] = int(original * 0.6)
            rows.append(row)
            
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("Player Nerf Applied.")

def apply_monster_buff():
    filepath = os.path.join(DATA_DIR, 'monsters.csv')
    print(f"Applying Monster Buff to {filepath}...")
    
    rows = []
    fieldnames = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        # csv.DictReader might struggle with spaces in headers if strict.
        # Based on typical usage, let's assume standard CSV.
        # The file content showed earlier had spaces: "ID, Name, Symbol..."
        # But DictReader normally handles keys as is.
        # Let's read first line to strip spaces from keys.
        lines = f.readlines()
    
    header = lines[0].strip().split(',')
    clean_header = [h.strip() for h in header]
    
    # Process content
    output_lines = [",".join(clean_header)]
    
    for line in lines[1:]:
        if not line.strip(): continue
        parts = line.strip().split(',') 
        # CAUTION: split(',') breaks if description has commas in quotes.
        # Better use csv module properly.
        pass

    # Reread using CSV module with skipinitialspace to handle " Name"
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        fieldnames = reader.fieldnames
        for row in reader:
            # Buff HP by 1.2x
            if 'HP' in row:
                row['HP'] = int(int(row['HP']) * 1.2)
            
            # Buff ATT by 1.2x
            if 'ATT' in row:
                try:
                    min_d, max_d = parse_damage_range(row['ATT'])
                    min_d = int(min_d * 1.2)
                    max_d = int(max_d * 1.2)
                    row['ATT'] = format_damage_range(min_d, max_d)
                except ValueError:
                    pass # Keep as is if invalid
            
            rows.append(row)

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("Monster Buff Applied.")

def apply_boss_buff():
    filepath = os.path.join(DATA_DIR, 'Boss.csv')
    print(f"Applying Boss Buff to {filepath}...")
    
    rows = []
    fieldnames = []
    
    # Bosses get 1.8x total (already buffed logic or separately?)
    # The requirement was "monsters +20%, bosses +50% ON TOP OF THAT".
    # So 1.2 * 1.5 = 1.8x.
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        fieldnames = reader.fieldnames
        for row in reader:
            # Buff HP by 1.8x
            if 'HP' in row:
                row['HP'] = int(int(row['HP']) * 1.8)
            
            # Buff ATT by 1.8x
            if 'ATT' in row:
                try:
                    min_d, max_d = parse_damage_range(row['ATT'])
                    min_d = int(min_d * 1.8)
                    max_d = int(max_d * 1.8)
                    row['ATT'] = format_damage_range(min_d, max_d)
                except ValueError:
                    pass
            
            rows.append(row)

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("Boss Buff Applied.")

if __name__ == "__main__":
    apply_player_nerf()
    # Note: Boss.csv is separate from monsters.csv, so we process them independently.
    apply_monster_buff()
    apply_boss_buff()
