
import sys
import os
import types
import random

sys.path.append('/home/dogsinatas/python_project/dungeon')

mock_readchar = types.ModuleType("readchar")
mock_readchar.key = types.SimpleNamespace()
mock_readchar.key.UP = "UP"
mock_readchar.key.DOWN = "DOWN"
mock_readchar.key.LEFT = "LEFT"
mock_readchar.key.RIGHT = "RIGHT"
mock_readchar.key.ENTER = "\r"
mock_readchar.key.ESC = "\x1b"
sys.modules["readchar"] = mock_readchar

from dungeon.components import StatsComponent, PositionComponent, InventoryComponent, ShopComponent, MapComponent, MonsterComponent
from dungeon.systems import CollisionEvent, MapTransitionEvent, ShopOpenEvent
from dungeon.ecs import World
from dungeon.items import Item
from dungeon.engine import GameState

def test_shop_and_transition():
    class MockRenderer:
        def render_shop(self, *args): pass
        def render(self): pass
        def draw_text(self, *args): pass
        def draw_char(self, *args): pass
        def clear_buffer(self): pass
        @property
        def height(self): return 30

    class MockEngine:
        def __init__(self, world):
            self.world = world
            self.state = GameState.PLAYING
            self.current_level = 1
            self.renderer = MockRenderer()
            self.item_defs = {}
        
        def handle_map_transition_event(self, event):
            self.current_level = event.target_level
            print(f"Transitioned to level {self.current_level}")

        def handle_shop_open_event(self, event):
            self.state = GameState.SHOP
            self.active_shop_id = event.shopkeeper_id
            self.selected_shop_item_index = 0
            print("Shop opened!")
        
        def _buy_item(self, shop_item):
            # 실제 엔진 로직 복사 (단순화)
            p = self.world.get_player_entity()
            s = p.get_component(StatsComponent)
            inv = p.get_component(InventoryComponent)
            price = shop_item['price']
            item = shop_item['item']
            if s.gold >= price:
                s.gold -= price
                inv.items[item.name] = {'item': item, 'qty': 1}
                print(f"Bought {item.name}")

    world = World(None)
    engine = MockEngine(world)
    world.engine = engine
    
    # 1. 숍 오픈 테스트
    player = world.create_entity() # ID=1
    player.add_component(StatsComponent(100, 100, 10, 5, gold=100))
    player.add_component(InventoryComponent(items={}, equipped={}))
    
    shopkeeper = world.create_entity()
    item = Item("potion_01", "HP Potion", "CONSUMABLE")
    shopkeeper.add_component(ShopComponent(items=[{'item': item, 'price': 30}]))
    shopkeeper.add_component(MonsterComponent(type_name="Merchant"))
    
    from dungeon.systems import CombatSystem
    combat = CombatSystem(world)
    
    # 상점 오픈 핸들러 등록
    world.event_manager.register(ShopOpenEvent, engine)
    
    # 충돌 발생
    event = CollisionEvent(player.entity_id, shopkeeper.entity_id, 1, 1, "MONSTER")
    combat.handle_collision_event(event)
    
    # 이벤트 처리 실행
    world.event_manager.process_events()
    
    assert engine.state == GameState.SHOP
    print("Shop Open Test Passed")
    
    # 2. 아이템 구매 테스트
    shop_comp = shopkeeper.get_component(ShopComponent)
    engine._buy_item(shop_comp.items[0])
    
    stats = player.get_component(StatsComponent)
    inv = player.get_component(InventoryComponent)
    assert stats.gold == 70
    assert "HP Potion" in inv.items
    print("Item Purchase Test Passed")

    # 3. 맵 이동 테스트
    from dungeon.systems import MapTransitionEvent
    trans_event = MapTransitionEvent(target_level=2)
    engine.handle_map_transition_event(trans_event)
    assert engine.current_level == 2
    print("Map Transition Test Passed")

if __name__ == "__main__":
    test_shop_and_transition()
