import os
import csv
import logging
import balance_simulator

# Path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONSTERS_CSV = os.path.join(BASE_DIR, "data/monsters.csv")

def load_monster_data():
    monsters = []
    if not os.path.exists(MONSTERS_CSV):
        print(f"Error: {MONSTERS_CSV} not found.")
        return []
    with open(MONSTERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            monsters.append(row)
    return monsters

def save_monster_data(monsters):
    if not monsters: return
    fieldnames = monsters[0].keys()
    with open(MONSTERS_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(monsters)

def parse_range(range_str):
    if '-' in range_str:
        low, high = map(int, range_str.split('-'))
        return low, high
    return int(range_str), int(range_str)

def format_range(low, high):
    if low == high:
        return str(low)
    return f"{low}-{high}"

def tune_monster(monster_id, win_rate, avg_combat_turns):
    """승률 및 교전 시간에 따라 몬스터 스탯 조정"""
    monsters = load_monster_data()
    modified = False
    
    # 목표 지표
    TARGET_WIN_MIN, TARGET_WIN_MAX = 40, 60
    TARGET_TURNS_MIN, TARGET_TURNS_MAX = 180, 300 # 3~5분 (턴당 1초 가정)
    
    for m in monsters:
        if m['ID'] == monster_id:
            hp = int(m['HP'])
            att_low, att_high = parse_range(m['ATT'])
            
            needs_buff = False
            needs_nerf = False
            
            # 1. 승률 기반 조정
            if win_rate < 30: needs_nerf = True
            elif win_rate > 70: needs_buff = True
            
            # 2. 교전 시간 기반 조정 (승률이 적당할 때 시간 밸런싱)
            if not needs_buff and not needs_nerf:
                if avg_combat_turns < TARGET_TURNS_MIN: needs_buff = True # 너무 빨리 끝남
                elif avg_combat_turns > TARGET_TURNS_MAX: needs_nerf = True # 너무 오래 걸림
            
            if needs_nerf:
                # 너무 어려움/오래 걸림 -> 스탯 하향 (10%로 가속)
                hp = max(10, int(hp * 0.9))
                att_low = max(1, int(att_low * 0.9))
                att_high = max(2, int(att_high * 0.9))
                print(f"  [Tuner] {monster_id} Nerfed (Win:{win_rate}%, Turns:{avg_combat_turns:.1f})")
                modified = True
            elif needs_buff:
                # 너무 쉬움/빨리 끝남 -> 스탯 상향 (10%로 가속)
                hp = int(hp * 1.1)
                att_low = int(att_low * 1.1)
                att_high = int(att_high * 1.1)
                print(f"  [Tuner] {monster_id} Buffed (Win:{win_rate}%, Turns:{avg_combat_turns:.1f})")
                modified = True
                
            m['HP'] = str(hp)
            m['ATT'] = format_range(att_low, att_high)
            break
            
    if modified:
        save_monster_data(monsters)
    return modified

def run_tuning_cycle(max_cycles=10):
    print(f"Starting Automated Balance Tuning (Max {max_cycles} cycles)...")
    print(f"Targeting: 3-5 min combat (180-300 turns), 40-60% Win Rate")
    
    scenarios = [
        (25, 18, "BUTCHER"),
        (50, 42, "LEORIC"),
        (75, 62, "LICH_KING"),
        (99, 82, "DIABLO")
    ]
    
    for cycle in range(max_cycles):
        print(f"\n--- [Cycle {cycle+1}] ---")
        all_balanced = True
        report = []
        
        for floor, p_level, m_id in scenarios:
            stats_log = {"WIN": 0, "DEATH": 0, "TIMEOUT": 0, "ERROR": 0}
            total_combat_turns = 0
            all_patterns = set()
            iterations = 10
            
            for i in range(iterations):
                engine = balance_simulator.HeadlessEngine()
                engine.current_level = floor
                engine._initialize_world()
                balance_simulator.setup_player_for_test(engine, floor, p_level)
                
                outcome = engine.run()
                stats_log[outcome] += 1
                total_combat_turns += engine.metrics["combat_turns"]
                for p in engine.metrics["boss_patterns"]:
                    all_patterns.add(p)
            
            win_rate = (stats_log["WIN"] / iterations) * 100
            avg_combat_turns = total_combat_turns / iterations
            
            modified = tune_monster(m_id, win_rate, avg_combat_turns)
            if modified:
                all_balanced = False
            
            status = "Adjusted" if modified else "Balanced"
            patterns_desc = f"{len(all_patterns)} patterns triggered"
            report.append(f"| {m_id} | {floor} | {win_rate}% | {avg_combat_turns:.1f} | {status} | {patterns_desc} |")
            
        print("\n| Boss | Floor | Win Rate | Avg Combat Turns | Status | Patterns |")
        print("|---|---|---|---|---|---|")
        for r in report:
            print(r)
            
        if all_balanced:
            print("\n[Target Reached] All bosses are within balance targets.")
            break
    
    print("\n[Tuning Complete]")

if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    run_tuning_cycle()
