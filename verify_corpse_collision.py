
import sys
import types

sys.path.append('/home/dogsinatas/python_project/dungeon')

mock_readchar = types.ModuleType("readchar")
mock_readchar.key = types.SimpleNamespace()
sys.modules["readchar"] = mock_readchar

from dungeon.components import StatsComponent, PositionComponent, LootComponent, CorpseComponent, MapComponent
from dungeon.systems import MovementSystem
from dungeon.ecs import World

def test_corpse_collision():
    world = World(None)
    movement_system = MovementSystem(world)
    
    # 1. 맵 생성 (비어있는 10x10)
    map_entity = world.create_entity()
    tiles = [['.' for _ in range(10)] for _ in range(10)]
    map_entity.add_component(MapComponent(tiles, 10, 10))
    
    # 2. 플레이어 생성 (ID=1)
    player = world.create_entity()
    player.add_component(PositionComponent(1, 1))
    
    # 3. 시체 생성 (2, 2)
    corpse = world.create_entity()
    corpse.add_component(PositionComponent(2, 2))
    corpse.add_component(CorpseComponent(original_name="Goblin"))
    corpse.add_component(LootComponent(items=[], gold=10))
    
    # 4. (2, 2)로 이동 시 충돌 체크
    collision = movement_system._check_entity_collision(player, 2, 2)
    
    print(f"Collision result: {collision}")
    assert collision is None, f"Expected no collision with corpse, but got {collision}"
    print("Corpse collision test passed!")

if __name__ == "__main__":
    test_corpse_collision()
