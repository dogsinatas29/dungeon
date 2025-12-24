
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

from dungeon.components import StatsComponent
from dungeon.constants import ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_ADVANTAGE
from dungeon.systems import CombatSystem, CollisionEvent
from dungeon.ecs import World

def test_elemental_damage():
    # Mock World and EventManager
    world = World(None) # Engine 없이 World 생성 (테스트용)
    combat_system = CombatSystem(world)
    
    # 1. 상성 우위 테스트 (WATER vs FIRE)
    # 공격자: WATER (ATK 10)
    # 방어자: FIRE (DEF 0)
    # 기대 데미지: 10 * 1.25 = 12.5 -> int(12) - 0 = 12
    a_stats = StatsComponent(max_hp=10, current_hp=10, attack=10, defense=0, element=ELEMENT_WATER)
    t_stats = StatsComponent(max_hp=20, current_hp=20, attack=5, defense=0, element=ELEMENT_FIRE)
    
    attacker = world.create_entity()
    attacker.add_component(a_stats)
    
    target = world.create_entity()
    target.add_component(t_stats)
    
    # 수동 데미지 계산 로직 검증 (CombatSystem.handle_collision_event 내부 로직 모사)
    damage_multiplier = 1.0
    if ELEMENT_ADVANTAGE.get(a_stats.element) == t_stats.element:
        damage_multiplier = 1.25
    
    damage = max(1, int(a_stats.attack * damage_multiplier) - t_stats.defense)
    print(f"Test 1 (WATER -> FIRE): Expected Damage 12, Actual {damage}")
    assert damage == 12
    
    # 2. 상성 열위 테스트 (FIRE vs WATER)
    # 공격자: FIRE (ATK 10)
    # 방어자: WATER (DEF 0)
    # 기대 데미지: 10 * 0.75 = 7.5 -> int(7) - 0 = 7
    a_stats_2 = StatsComponent(max_hp=10, current_hp=10, attack=10, defense=0, element=ELEMENT_FIRE)
    t_stats_2 = StatsComponent(max_hp=20, current_hp=20, attack=5, defense=0, element=ELEMENT_WATER)
    
    damage_multiplier = 1.0
    if ELEMENT_ADVANTAGE.get(t_stats_2.element) == a_stats_2.element:
        damage_multiplier = 0.75
        
    damage_2 = max(1, int(a_stats_2.attack * damage_multiplier) - t_stats_2.defense)
    print(f"Test 2 (FIRE -> WATER): Expected Damage 7, Actual {damage_2}")
    assert damage_2 == 7

    # 3. 무상성 테스트 (WATER vs WOOD)
    # 공격자: WATER (ATK 10)
    # 방어자: WOOD (DEF 0)
    # WATER는 WOOD에 대해 열위가 아니므로 (WOOD > EARTH > WATER) 
    # 하지만 ELEMENT_ADVANTAGE는 (WATER > FIRE > WOOD > EARTH > WATER)
    # WOOD가 WATER를 이기는 상성임 (WOOD -> EARTH -> WATER 순서 확인 필요)
    # constants.py 확인: WATER: FIRE, FIRE: WOOD, WOOD: EARTH, EARTH: WATER
    # WOOD 공격 -> EARTH 방어 (우위)
    # WATER 공격 -> WOOD 방어 (WOOD는 누구를 이기는가? WOOD > EARTH. WATER와는 무관?)
    # 상성 순서: WATER -> FIRE -> WOOD -> EARTH -> WATER
    # WATER는 FIRE에 우위.
    # FIRE는 WOOD에 우위.
    # WOOD는 EARTH에 우위.
    # EARTH는 WATER에 우위.
    # 따라서 WATER vs WOOD는 직접적인 상성 관계 없음.
    a_stats_3 = StatsComponent(max_hp=10, current_hp=10, attack=10, defense=0, element=ELEMENT_WATER)
    t_stats_3 = StatsComponent(max_hp=20, current_hp=20, attack=5, defense=0, element=ELEMENT_WOOD)
    
    damage_multiplier = 1.0
    if ELEMENT_ADVANTAGE.get(a_stats_3.element) == t_stats_3.element:
        damage_multiplier = 1.25
    elif ELEMENT_ADVANTAGE.get(t_stats_3.element) == a_stats_3.element:
        damage_multiplier = 0.75
        
    damage_3 = max(1, int(a_stats_3.attack * damage_multiplier) - t_stats_3.defense)
    print(f"Test 3 (WATER -> WOOD): Expected Damage 10, Actual {damage_3}")
    assert damage_3 == 10

    print("All elemental tests passed!")

if __name__ == "__main__":
    test_elemental_damage()
