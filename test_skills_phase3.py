import sys
import os
import time

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
    
    # 맵 생성 (20x20)
    tiles = [['.' for _ in range(20)] for _ in range(20)]
    map_comp = MapComponent(width=20, height=20, tiles=tiles)
    map_ent = world.create_entity()
    map_ent.add_component(map_comp)
    
    # 플레이어 생성
    player = world.create_entity()
    player.add_component(PositionComponent(x=10, y=10))
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=500, current_mp=500, dex=100))
    player.add_component(InventoryComponent())
    player.add_component(LevelComponent(level=20, job="소서러"))
    
    return world, player, engine, world.event_manager

def test_flash():
    print("\n--- Testing FLASH ---")
    world, player, engine, em = setup_test()
    
    # 적 9마리 배치 (플레이어 주변 3x3)
    monsters = []
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            if dx == 0 and dy == 0: continue
            m = world.create_entity()
            m.add_component(PositionComponent(x=10+dx, y=10+dy))
            m.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
            monsters.append(m)
            
    # 스킬 정의
    flash_skill = type('obj', (object,), {
        'id': 'FLASH', 'name': '플래시', 'type': 'ATTACK', 'subtype': 'SELF', 'cost_type': 'MP', 'cost_value': 30, 'required_level': 5, 'range': 1, 'damage': 30, 'duration': 0, 'flags': {'AURA', 'SCALABLE'}, 'skill_type': 'MAGIC'
    })
    engine.skill_defs['FLASH'] = flash_skill
    
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='FLASH', dx=0, dy=0))
    em.process_events()
    
    # 모든 몬스터의 HP가 깎였는지 확인
    for m in monsters:
        assert m.get_component(StatsComponent).current_hp < 50

def test_nova():
    print("\n--- Testing NOVA ---")
    world, player, engine, em = setup_test()
    
    # 원형으로 적 배치 (거리 3 위치에)
    m1 = world.create_entity()
    m1.add_component(PositionComponent(x=13, y=10))
    m1.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    m2 = world.create_entity()
    m2.add_component(PositionComponent(x=7, y=10))
    m2.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    # 스킬 정의 (사거리 5)
    nova_skill = type('obj', (object,), {
        'id': 'NOVA', 'name': '노바', 'type': 'ATTACK', 'subtype': 'SELF', 'cost_type': 'MP', 'cost_value': 60, 'required_level': 13, 'range': 5, 'damage': 50, 'duration': 0, 'flags': {'AURA', 'NOVA', 'SCALABLE'}, 'skill_type': 'MAGIC'
    })
    engine.skill_defs['NOVA'] = nova_skill
    
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='NOVA', dx=0, dy=0))
    em.process_events()
    
    assert m1.get_component(StatsComponent).current_hp < 50
    assert m2.get_component(StatsComponent).current_hp < 50

def test_chain_lightning():
    print("\n--- Testing CHAIN_LIGHTNING ---")
    world, player, engine, em = setup_test()
    
    # 징검다리 식으로 적 배치
    # P(10,10) -> M1(12,10) -> M2(14,10) -> M3(14,12)
    m1 = world.create_entity()
    m1.add_component(PositionComponent(x=12, y=10))
    m1.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    m2 = world.create_entity()
    m2.add_component(PositionComponent(x=14, y=10))
    m2.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    m3 = world.create_entity()
    m3.add_component(PositionComponent(x=14, y=12))
    m3.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    chain_skill = type('obj', (object,), {
        'id': 'CHAIN_LIGHTNING', 'name': '체인 라이트닝', 'type': 'ATTACK', 'subtype': 'PROJECTILE', 'cost_type': 'MP', 'cost_value': 30, 'required_level': 9, 'range': 6, 'damage': 40, 'duration': 0, 'flags': {'PROJECTILE', 'CHAIN', 'SCALABLE'}, 'skill_type': 'MAGIC'
    })
    engine.skill_defs['CHAIN_LIGHTNING'] = chain_skill
    
    # 오른쪽으로 발사하여 m1 타격 -> m2 -> m3로 전이 기대
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='CHAIN_LIGHTNING', dx=1, dy=0))
    em.process_events()
    
    assert m1.get_component(StatsComponent).current_hp < 50
    assert m2.get_component(StatsComponent).current_hp < 50
    assert m3.get_component(StatsComponent).current_hp < 50

def test_flame_wave():
    print("\n--- Testing FLAME_WAVE ---")
    world, player, engine, em = setup_test()
    
    # 전방 3칸 너비에 적 배치
    # P(10,10), dx=1 이면 (11,9), (11,10), (11,11) 공격
    m1 = world.create_entity()
    m1.add_component(PositionComponent(x=11, y=9))
    m1.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    m2 = world.create_entity()
    m2.add_component(PositionComponent(x=11, y=11))
    m2.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
    
    wave_skill = type('obj', (object,), {
        'id': 'FLAME_WAVE', 'name': '플레임 웨이브', 'type': 'ATTACK', 'subtype': 'PROJECTILE', 'cost_type': 'MP', 'cost_value': 35, 'required_level': 9, 'range': 4, 'damage': 30, 'duration': 0, 'flags': {'PROJECTILE', 'MOVING_WALL', 'SCALABLE', 'PIERCING'}, 'skill_type': 'MAGIC'
    })
    engine.skill_defs['FLAME_WAVE'] = wave_skill
    
    em.push(SkillUseEvent(attacker_id=player.entity_id, skill_name='FLAME_WAVE', dx=1, dy=0))
    em.process_events()
    
    assert m1.get_component(StatsComponent).current_hp < 50
    assert m2.get_component(StatsComponent).current_hp < 50

if __name__ == "__main__":
    try:
        test_flash()
        test_nova()
        test_chain_lightning()
        test_flame_wave()
        print("\nAll Phase 3 skill tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
