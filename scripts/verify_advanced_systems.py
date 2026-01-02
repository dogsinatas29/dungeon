
import sys
import os
import types
import random

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

from dungeon.components import StatsComponent, PositionComponent, RenderComponent, MonsterComponent, LootComponent, CorpseComponent, InventoryComponent, MapComponent
from dungeon.systems import CombatSystem, MoveSuccessEvent
from dungeon.ecs import World
from dungeon.constants import ELEMENT_FIRE, ELEMENT_COLORS
from dungeon.items import Item

def test_advanced_systems():
    class MockEngine:
        def __init__(self):
            self.item_defs = {"Potion": Item("potion_01", "Potion", "CONSUMABLE", "A red potion")}
            self.player_name = "Hero"

    engine = MockEngine()
    world = World(engine)
    combat_system = CombatSystem(world)
    
    # 1. 속성 색상 확인
    # 첫 번째 엔티티 (플레이어 ID=1 예상)
    player = world.create_entity()
    player.add_component(PositionComponent(1, 1))
    player.add_component(InventoryComponent(items={}, equipped={}))
    player.add_component(StatsComponent(100, 100, 10, 5, gold=0))
    
    monster = world.create_entity()
    monster.add_component(StatsComponent(100, 100, 10, 5, element=ELEMENT_FIRE))
    color = ELEMENT_COLORS[ELEMENT_FIRE]
    monster.add_component(RenderComponent(char='g', color=color))
    print(f"Monster Color: {monster.get_component(RenderComponent).color} (Expected: {color})")
    assert monster.get_component(RenderComponent).color == "red"

    # 2. 루팅 시스템 확인

    # 루팅 대상 생성
    loot_entity = world.create_entity()
    loot_entity.add_component(PositionComponent(2, 2))
    item = engine.item_defs["Potion"]
    loot_entity.add_component(LootComponent(items=[{'item': item, 'qty': 1}], gold=50))
    loot_entity.add_component(CorpseComponent(original_name="Goblin"))

    # 플레이어가 (2, 2)로 이동하는 이벤트 발생
    event = MoveSuccessEvent(entity_id=player.entity_id, old_x=1, old_y=1, new_x=2, new_y=2)
    combat_system.handle_move_success_event(event)

    # 검증: 플레이어 인벤토리에 아이템이 있고, 루팅 엔티티가 삭제되었는지 확인
    inv = player.get_component(InventoryComponent)
    print(f"Player Inventory: {inv.items.keys()}")
    assert "Potion" in inv.items
    assert inv.items["Potion"]["qty"] == 1
    
    # 루팅 엔티티가 world에서 삭제되었는지 확인
    assert loot_entity.entity_id not in world._entities
    print("Loot system test passed!")

if __name__ == "__main__":
    test_advanced_systems()
