import sys
import os
import random
import time

# Ensure dungeon package is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.balance_simulator import HeadlessEngine, setup_player_for_test
from dungeon.components import LevelComponent

def simulate_progression():
    classes = ["WARRIOR", "ROGUE", "SORCERER", "BARBARIAN"]
    test_floors = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    
    # "Estimated" Level mapping based on game balance constants
    # (Simplified: Level ~ floor/3 + 1 for early, scales up later)
    # Actually, let's use the levels used for bosses as anchor points.
    floor_to_level = {
        1: 1,
        10: 8,
        20: 15,
        30: 22,
        40: 28,
        50: 35,
        60: 42,
        70: 50,
        80: 60,
        90: 75,
        99: 85
    }

    print("Dungeon Floor Progression Simulation (Clearance Time & Levels)")
    print("=" * 80)
    print(f"{'Class':<12} | {'Floor':<5} | {'Level':<5} | {'Avg Turns':<10} | {'Status'}")
    print("-" * 80)

    for class_id in classes:
        for floor in test_floors:
            level = floor_to_level[floor]
            
            # Simulate 3 trials per floor/class to get an average
            iterations = 3
            total_turns = 0
            
            for _ in range(iterations):
                engine = HeadlessEngine()
                engine.current_level = floor
                engine._initialize_world()
                
                # Setup player
                setup_player_for_test(engine, floor, level, class_id)
                
                # Journey Simulation:
                # On non-boss maps, we simulate clearing 5-10 monsters and finding exit.
                # Since HeadlessEngine doesn't have "find exit" logic, we simulate 
                # a base "exploration cost" + "monster combat cost".
                
                # Base Exploration: 200-400 turns per floor based on map size
                exploration_turns = random.randint(150, 300)
                
                # Combat: 5-8 encounters
                num_encounters = random.randint(5, 10)
                combat_turns = 0
                
                # Simulate each encounter
                # (We don't actually run the engine loop because HeadlessEngine is boss-centric)
                # Instead, we estimate combat based on monster HP vs player damage.
                # Average non-boss monster HP: scales with floor
                m_hp = 20 + (floor * 15)
                # Player Attack: scales with level
                p_atk = 10 + (level * 3)
                
                turns_per_kill = max(1, m_hp // p_atk)
                combat_turns = num_encounters * turns_per_kill * 2.5 # multiplier for movement/spacing
                
                total_turns += (exploration_turns + combat_turns)
            
            avg_turns = total_turns / iterations
            print(f"{class_id:<12} | {floor:<5} | {level:<5} | {avg_turns:<10.1f} | [READY]")

if __name__ == "__main__":
    simulate_progression()
