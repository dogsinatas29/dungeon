import json
import os
from datetime import datetime

RANKINGS_FILE = os.path.join("game_data", "rankings.json")

def inject_mock_rankings():
    mock_entries = [
        {
            'name': 'LegendHero',
            'class': '워리어',
            'level': 30,
            'floor': 100,
            'outcome': 'WIN',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'boss_kills': 'Diablo',
            'death_cause': 'N/A',
            'turns': 5000,
            'equipment': {'Hand1': 'Grandfather', 'Body': 'Tyrael\'s Might'},
            'skill_levels': {'Slash': 20, 'Bash': 15}
        },
        {
            'name': 'UnluckyOne',
            'class': '소서러',
            'level': 15,
            'floor': 45,
            'outcome': 'DEATH',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'boss_kills': 'The Butcher',
            'death_cause': 'Fireball',
            'turns': 2000,
            'equipment': {'Hand1': 'Staff of Power', 'Body': 'Mage Robe'},
            'skill_levels': {'Firebolt': 10, 'Teleport': 5}
        }
    ]
    
    # Add more to test scrolling
    for i in range(10):
        mock_entries.append({
            'name': f'Ghost_{i}',
            'class': '로그',
            'level': 5 + i,
            'floor': 10 + (i * 5),
            'outcome': 'DEATH',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'boss_kills': '',
            'death_cause': 'Slime',
            'turns': 100 * i,
            'equipment': {'Hand1': f'Dagger + {i}'},
            'skill_levels': {'Stealth': 1 + i}
        })

    os.makedirs(os.path.dirname(RANKINGS_FILE), exist_ok=True)
    with open(RANKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mock_entries, f, ensure_ascii=False, indent=4)
    print("Mock rankings injected successfully.")

if __name__ == "__main__":
    inject_mock_rankings()
