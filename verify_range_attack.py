
import sys
import os
import types

# 프로젝트 루트 디렉토리를 path에 추가
sys.path.append('/home/dogsinatas/python_project/dungeon')

# readchar 모듈 mock 처리
mock_readchar = types.ModuleType("readchar")
mock_readchar.key = types.SimpleNamespace()
mock_readchar.key.UP = "UP"
mock_readchar.key.DOWN = "DOWN"
mock_readchar.key.LEFT = "LEFT"
mock_readchar.key.RIGHT = "RIGHT"
sys.modules["readchar"] = mock_readchar

from dungeon.components import StatsComponent, PositionComponent, MapComponent
from dungeon.systems import CombatSystem, DirectionalAttackEvent
from dungeon.ecs import World

def test_range_attack():
    # Mock Engine for attack mode handling
    class MockEngine:
        def __init__(self):
            self.is_attack_mode = False
            self.player_name = "Hero"
            
    engine = MockEngine()
    world = World(engine)
    combat_system = CombatSystem(world)
    
    # 1. 일직선상 여러 몬스터 배치 테스트
    # 플레이어: (5, 5)
    # 몬스터1: (5, 4) - 거리 1
    # 몬스터2: (5, 3) - 거리 2
    # 몬스터3: (5, 2) - 거리 3
    # 몬스터4: (5, 1) - 거리 4 (사거리 밖)
    
    player = world.create_entity()
    player.add_component(PositionComponent(5, 5))
    player.add_component(StatsComponent(100, 100, 20, 0)) # ATK 20
    
    monsters = []
    for i in range(1, 5):
        m = world.create_entity()
        m.add_component(PositionComponent(5, 5 - i))
        # current_hp=100으로 시작
        m.add_component(StatsComponent(100, 100, 10, 0))
        monsters.append(m)
        
    # 맵 엔티티 생성 (충돌 체크용)
    map_entity = world.create_entity()
    tiles = [['.' for _ in range(20)] for _ in range(20)]
    map_entity.add_component(MapComponent(20, 20, tiles))
    
    # 공격 이벤트 발생: 위쪽(0, -1) 방향, 사거리 3
    event = DirectionalAttackEvent(attacker_id=player.entity_id, dx=0, dy=-1, range_dist=3)
    combat_system.handle_directional_attack_event(event)
    
    # 결과 검증
    # M1 (거리 1): 20 데미지 -> HP 80
    # M2 (거리 2): 20 * (1.0 - (2-1)*0.1) = 20 * 0.9 = 18 데미지 -> HP 82
    # M3 (거리 3): 20 * (1.0 - (3-1)*0.1) = 20 * 0.8 = 16 데미지 -> HP 84
    # M4 (거리 4): 데미지 없음 -> HP 100
    
    m1_hp = monsters[0].get_component(StatsComponent).current_hp
    m2_hp = monsters[1].get_component(StatsComponent).current_hp
    m3_hp = monsters[2].get_component(StatsComponent).current_hp
    m4_hp = monsters[3].get_component(StatsComponent).current_hp
    
    print(f"M1 HP: {m1_hp} (Expected 80)")
    print(f"M2 HP: {m2_hp} (Expected 82)")
    print(f"M3 HP: {m3_hp} (Expected 84)")
    print(f"M4 HP: {m4_hp} (Expected 100)")
    
    assert m1_hp == 80
    assert m2_hp == 82
    assert m3_hp == 84
    assert m4_hp == 100
    
    print("Range attack test passed!")

if __name__ == "__main__":
    test_range_attack()
