
import sys
import os

# 프로젝트 루트 디렉토리를 path에 추가
sys.path.append('/home/dogsinatas/python_project/dungeon')

# readchar 모듈이 없는 환경을 위해 mock 처리
import types
mock_readchar = types.ModuleType("readchar")
mock_readchar.key = types.SimpleNamespace()
mock_readchar.key.UP = "UP"
mock_readchar.key.DOWN = "DOWN"
mock_readchar.key.LEFT = "LEFT"
mock_readchar.key.RIGHT = "RIGHT"
sys.modules["readchar"] = mock_readchar

from dungeon.components import StatsComponent, InventoryComponent
from dungeon.constants import ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_NONE
from dungeon.systems import CombatSystem
from dungeon.ecs import World
from unittest.mock import MagicMock

def test_elemental_damage():
    # Mock World and EventManager
    world = World(None) 
    # Mock engine for _get_entity_name if needed, or patching
    world.engine = MagicMock()
    world.engine._get_entity_name.side_effect = lambda e: "Entity"
    
    combat_system = CombatSystem(world)
    
    # 1. Stats based Advantage (WATER > FIRE)
    print("\n[Test 1] Stats Element: WATER(Atk 100) vs FIRE(Def 0)")
    a_stats = StatsComponent(max_hp=100, current_hp=100, attack=100, defense=0, element=ELEMENT_WATER)
    t_stats = StatsComponent(max_hp=200, current_hp=200, attack=50, defense=0, element=ELEMENT_FIRE)
    
    attacker = world.create_entity()
    attacker.add_component(a_stats)
    attacker.add_component(InventoryComponent()) # Empty inventory
    
    target = world.create_entity()
    target.add_component(t_stats)
    target.add_component(InventoryComponent())
    
    # Apply damage
    # Expected: 100 + 1~5% = 101 ~ 105. (Crit 10% + 10% = 20% chance for 1.5x)
    # We loop to check range or average, but single run is checking logic flow
    # Force seed? No, just check if matches logic.
    
    combat_system._apply_damage(attacker, target, distance=1)
    
    damage_dealt = 200 - t_stats.current_hp
    print(f"Damage Dealt: {damage_dealt}")
    
    # Validation: Should be > 100 (Bonus) or huge (Crit)
    if damage_dealt >= 101 or damage_dealt >= 150:
        print("PASS: Bonus applied or Crit")
    else:
        print("FAIL: No bonus applied?")

    # 2. Weapon Element Advantage (Fire Sword > Wood Monster)
    print("\n[Test 2] Weapon Element: Fire Sword(Atk 100) vs WOOD(Def 0)")
    # Attacker has NONE element stats, but Fire Sword
    a_stats_2 = StatsComponent(max_hp=100, current_hp=100, attack=100, defense=0, element=ELEMENT_NONE)
    t_stats_2 = StatsComponent(max_hp=200, current_hp=200, attack=50, defense=0, element=ELEMENT_WOOD)
    
    attacker_2 = world.create_entity()
    attacker_2.add_component(a_stats_2)
    # Mock Item with flags
    fire_sword = MagicMock()
    fire_sword.flags = {"ELEMENT_FIRE"}
    inv_2 = InventoryComponent(equipped={'weapon': fire_sword})
    attacker_2.add_component(inv_2)
    
    target_2 = world.create_entity()
    target_2.add_component(t_stats_2) # Wood Element
    target_2.add_component(InventoryComponent())
    
    combat_system._apply_damage(attacker_2, target_2, distance=1)
    damage_2 = 200 - t_stats_2.current_hp
    print(f"Damage Dealt: {damage_2}")
    
    # FIRE > WOOD: Advantage
    if damage_2 >= 101:
        print("PASS: Weapon Element Advantage applied")
    else:
        print("FAIL: Weapon Element ignored")

    # 3. Armor Element Disadvantage (Fire Monster > Water Armor)
    print("\n[Test 3] Armor Element: FIRE(Atk 100) vs Water Armor(Def 0)")
    # Attacker FIRE stats
    a_stats_3 = StatsComponent(max_hp=100, current_hp=100, attack=100, defense=0, element=ELEMENT_FIRE)
    # Target NONE stats stats, but Water Armor
    t_stats_3 = StatsComponent(max_hp=200, current_hp=200, attack=50, defense=0, element=ELEMENT_NONE)
    
    attacker_3 = world.create_entity()
    attacker_3.add_component(a_stats_3)
    attacker_3.add_component(InventoryComponent())
    
    target_3 = world.create_entity()
    target_3.add_component(t_stats_3)
    water_armor = MagicMock()
    water_armor.flags = {"ELEMENT_WATER"}
    inv_3 = InventoryComponent(equipped={'armor': water_armor})
    target_3.add_component(inv_3)
    
    # FIRE vs WATER Armor -> Disadvantage (FIRE < WATER)
    combat_system._apply_damage(attacker_3, target_3, distance=1)
    damage_3 = 200 - t_stats_3.current_hp
    print(f"Damage Dealt: {damage_3}")
    
    # Disadvantage: 100 - 1~5% = 95~99. (Crit reduced)
    if damage_3 < 100:
        print("PASS: Armor Element Disadvantage applied")
    elif damage_3 >= 150:
         print("WARN: Critical hit despite disadvantage (unlikely but possible if crit chance > -10%)")
    else:
        print("FAIL: No damage reduction?")

if __name__ == "__main__":
    test_elemental_damage()
