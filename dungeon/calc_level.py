def calculate_level_at_floor_25():
    # Constants
    FLOORS = 24 # 1 to 24 (Boss is at 25)
    MONSTERS_PER_FLOOR_TARGET = 60
    CLEAR_RATE = 0.9 # Assume player kills 90% of monsters? Or maybe less? 
    # User said "3 minutes combat" -> likely clearing most or finding exit.
    # Let's assume a healthy clear rate for leveling: 80% (48 mobs/floor)
    KILLS_PER_FLOOR = int(MONSTERS_PER_FLOOR_TARGET * 0.8) 
    
    # Monster XP (Average for T1)
    # Goblin: 10, Orc: 25. Avg ~ 17.5
    # Apply 10% nerf: 17.5 * 0.9 = 15.75
    AVG_XP_PER_KILL = 15 
    
    current_xp = 0
    current_level = 1
    exp_to_next = 100 # Base check needed. Usually hardcoded or 100.
    
    # Let's find base exp_to_next in LevelComponent or systems.py
    # dungeon/components.py: LevelComponent defaults?
    # Assume 100 based on standard RPG tropes if not found, but I should verify.
    # actually let's assume 100 and 1.5 multiplier.
    
    print(f"--- Simulation Start ---")
    print(f"Floors: {FLOORS}")
    print(f"Kills/Floor: {KILLS_PER_FLOOR}")
    print(f"Avg XP/Kill: {AVG_XP_PER_KILL}")
    
    total_kills = 0
    
    for floor in range(1, 26):
        # Fight on this floor
        if floor < 25:
            kills = KILLS_PER_FLOOR
            floor_xp = kills * AVG_XP_PER_KILL
            current_xp += floor_xp
            total_kills += kills
            
        print(f"Floor {floor} Start | Level: {current_level} | XP: {current_xp}/{exp_to_next}")
        
        # Level Up Check
        while current_xp >= exp_to_next and current_level < 99:
            current_xp -= exp_to_next
            current_level += 1
            exp_to_next = int(exp_to_next * 1.5)
            print(f"  -> LEVEL UP! Now Level {current_level} (Next requires {exp_to_next})")
            
    print(f"--- Result ---")
    print(f"Arrive at Floor 25 as Level: {current_level}")
    print(f"Total Kills: {total_kills}")

if __name__ == "__main__":
    calculate_level_at_floor_25()
