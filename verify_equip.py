import sys
import os
sys.path.append('/home/dogsinatas/python_project/dungeon')

from dungeon.engine import Engine, GameState
from dungeon.components import InventoryComponent
from dungeon.data_manager import load_item_definitions

def test_equip_logic():
    engine = Engine()
    player = engine.world.get_player_entity()
    inv = player.get_component(InventoryComponent)
    item_defs = load_item_definitions()
    
    print("--- Initial State ---")
    print(f"Equipped: {inv.equipped}")
    
    # 1. Equip Two-handed Sword
    two_hand_sword = item_defs.get("양손 대검")
    print(f"\nEquipping: {two_hand_sword.name}")
    engine._equip_selected_item({'item': two_hand_sword, 'qty': 1})
    print(f"Equipped: {inv.equipped}")
    assert inv.equipped["손1"] == "양손 대검"
    assert inv.equipped["손2"] == "(양손 점유)"
    
    # 2. Equip Shield (should unequip two-hand sword handle 1)
    shield = item_defs.get("방패")
    print(f"\nEquipping: {shield.name}")
    engine._equip_selected_item({'item': shield, 'qty': 1})
    print(f"Equipped: {inv.equipped}")
    assert inv.equipped["손1"] is None
    assert inv.equipped["손2"] == "방패"
    
    # 3. Equip One-handed Sword
    one_hand_sword = item_defs.get("강철 검")
    print(f"\nEquipping: {one_hand_sword.name}")
    engine._equip_selected_item({'item': one_hand_sword, 'qty': 1})
    print(f"Equipped: {inv.equipped}")
    assert inv.equipped["손1"] == "강철 검"
    assert inv.equipped["손2"] == "방패"
    
    # 4. Equip another One-handed Sword (Dual wield)
    old_sword = item_defs.get("낡은 검")
    print(f"\nEquipping: {old_sword.name}")
    engine._equip_selected_item({'item': old_sword, 'qty': 1})
    print(f"Equipped: {inv.equipped}")
    # Currently my logic replaces 손2 if shield is there? 
    # Let's see: Shield is in 손2. One-hand sword goes to 손1 if empty. 
    # If 손1 is not empty, it goes to 손2 if empty.
    # In step 3, 강철 검 went to 손1 (empty). 손2 had Shield.
    # In step 4, 낡은 검: 손1 is 강철 검, 손2 is 방패. Both full. Replaces 손1.
    assert inv.equipped["손1"] == "낡은 검"
    assert inv.equipped["손2"] == "방패"

    print("\n[SUCCESS] Equip logic verification passed.")

if __name__ == "__main__":
    test_equip_logic()
