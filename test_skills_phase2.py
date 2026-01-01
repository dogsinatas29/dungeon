import sys
import os
import random

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.ecs import World, EventManager, initialize_event_listeners
from dungeon.components import (
    PositionComponent, StatsComponent, InventoryComponent, LevelComponent, 
    MapComponent, RenderComponent, EffectComponent
)
from dungeon.systems import CombatSystem, TimeSystem
from dungeon.events import MessageEvent, SkillUseEvent, SoundEvent

class MockEngine:
    def __init__(self, world=None):
        self.world = world
        self.skill_defs = {}
        if world:
            world.engine = self
    def _is_wall(self, x, y):
        # 맵 검사 로직 모방
        map_ent = self.world.get_entities_with_components({MapComponent})[0]
        map_comp = map_ent.get_component(MapComponent)
        if 0 <= x < map_comp.width and 0 <= y < map_comp.height:
            return map_comp.tiles[y][x] == '#'
        return True
    def _render(self):
        pass
    def _get_entity_name(self, entity):
        return "TestPlayer"

class MessagePrinter:
    def handle_message_event(self, event):
        print(f"  [MSG] {event.text}")
    def handle_sound_event(self, event):
        print(f"  [SOUND] {event.sound_type}")

def setup_test():
    engine = MockEngine(None)
    world = World(engine)
    engine.world = world
    
    combat_system = CombatSystem(world)
    world.add_system(combat_system)
    
    initialize_event_listeners(world)
    world.event_manager.register(MessageEvent, MessagePrinter())
    world.event_manager.register(SoundEvent, MessagePrinter())
    
    # 맵 생성 (10x10, 테두리 벽)
    tiles = [['.' for _ in range(10)] for _ in range(10)]
    for i in range(10):
        tiles[0][i] = '#'
        tiles[9][i] = '#'
        tiles[i][0] = '#'
        tiles[i][9] = '#'
    
    # 장애물 추가
    tiles[5][5] = '#'
    
    map_comp = MapComponent(width=10, height=10, tiles=tiles)
    map_ent = world.create_entity()
    map_ent.add_component(map_comp)
    
    # 플레이어 생성
    player = world.create_entity()
    player.add_component(PositionComponent(x=1, y=1))
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=100, current_mp=100))
    player.add_component(InventoryComponent())
    player.add_component(LevelComponent(level=10, job="소서러"))
    
    return world, player, engine, world.event_manager

def test_phasing():
    print("\n--- Testing PHASING ---")
    world, player, engine, em = setup_test()
    pos = player.get_component(PositionComponent)
    
    old_pos = (pos.x, pos.y)
    
    # 스킬 정의
    phasing_skill = type('obj', (object,), {
        'id': 'PHASING', 'name': '페이징', 'type': 'UTILITY', 'subtype': 'SELF', 'cost_type': 'MP', 'cost_value': 10, 'required_level': 1, 'flags': {'TELEPORT_RANDOM'},
        'damage': 0, 'range': 0, 'duration': 0
    })
    engine.skill_defs['PHASING'] = phasing_skill
    
    print(f"Before: ({pos.x}, {pos.y})")
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='PHASING', dx=0, dy=0))
    em.process_events()
    print(f"After: ({pos.x}, {pos.y})")
    
    assert (pos.x, pos.y) != old_pos
    # 벽이 아닌지 확인
    assert engine._is_wall(pos.x, pos.y) == False

def test_teleport():
    print("\n--- Testing TELEPORT ---")
    world, player, engine, em = setup_test()
    pos = player.get_component(PositionComponent)
    pos.x, pos.y = 1, 1
    
    # 스킬 정의 (사거리 5)
    teleport_skill = type('obj', (object,), {
        'id': 'TELEPORT', 'name': '텔레포트', 'type': 'UTILITY', 'subtype': 'PROJECTILE', 'cost_type': 'MP', 'cost_value': 10, 'required_level': 1, 'range': 5, 'flags': {'TELEPORT', 'PIERCING'},
        'damage': 0, 'duration': 0
    })
    engine.skill_defs['TELEPORT'] = teleport_skill
    
    # 오른쪽으로 텔레포트 (장애물 없음)
    print(f"Initial Pos: ({pos.x}, {pos.y})")
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='TELEPORT', dx=1, dy=0))
    em.process_events()
    print(f"Teleport Right (dist 5): ({pos.x}, {pos.y})")
    assert pos.x == 1 + 5
    assert pos.y == 1
    
    # 아래쪽으로 텔레포트 (벽에 막힘)
    # y=1에서 아래로 5칸 가면 y=6. y=9가 벽임.
    # 만약 y=5, x=1가 벽이라면? (setup_test에서 tiles[5][5]만 벽임)
    # x=1, y=1에서 dx=0, dy=1로 5칸 가면 (1, 6)까지 가야 함. 무난함.
    pos.x, pos.y = 1, 1
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='TELEPORT', dx=0, dy=1))
    em.process_events()
    print(f"Teleport Down (dist 5): ({pos.x}, {pos.y})")
    assert pos.y == 6
    
    # 벽 너머로 텔레포트 시도 (사거리가 벽 뒤일 때)
    # x=1, y=1 -> dx=0, dy=1, range=10 이면 y=9(벽)에 막혀야 함.
    teleport_skill.range = 10
    pos.x, pos.y = 1, 1
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='TELEPORT', dx=0, dy=1))
    em.process_events()
    # y=9가 벽이므로 마지막 유효 좌표는 y=8
    print(f"Teleport Down into Wall (range 10, wall at 9): ({pos.x}, {pos.y})")
    assert pos.y == 8

if __name__ == "__main__":
    try:
        test_phasing()
        test_teleport()
        print("\nAll Phase 2 skill tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
