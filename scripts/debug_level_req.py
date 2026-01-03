import os
import sys
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import InventoryComponent, LevelComponent
from dungeon.data_manager import ItemDefinition, load_data_from_csv

def debug_level_req():
    print("=== Debugging Level Requirements ===")
    
    engine = Engine(player_name="DebugUser")
    player = engine.world.get_player_entity()
    inv = player.get_component(InventoryComponent)
    level_comp = player.get_component(LevelComponent)
    level_comp.level = 1
    
    # 데이터 로드
    engine.item_defs = load_data_from_csv('/home/dogsinatas/python_project/dungeon/data/items.csv', ItemDefinition)
    
    # 파이어볼 스킬북 Lv3 확인
    book_name = "파이어볼 스킬북 Lv3"
    book_def = engine.item_defs.get(book_name)
    
    if not book_def:
        print(f"ERROR: {book_name} definition not found!")
        return

    print(f"Item: {book_def.name}, Required Level: {book_def.required_level}")
    
    inv.items[book_name] = {'item': book_def, 'qty': 1}
    
    # Mock EventManager to capture messages
    engine.world.event_manager.push = MagicMock()
    
    print(f"Attempting to use item at Player Level {level_comp.level}...")
    engine._use_item(book_name, inv.items[book_name])
    
    # Check if Skill Learned
    base_name = "파이어볼"
    skill_level = inv.skill_levels.get(base_name, 0)
    print(f"Skill Level after use: {skill_level} (Expected: 0)")
    
    # Check messages
    calls = engine.world.event_manager.push.call_args_list
    for call in calls:
        msg = call[0][0].text
        print(f"Message: {msg}")

if __name__ == "__main__":
    debug_level_req()
