import sys
import os

sys.path.append(os.getcwd())

from dungeon.engine import Engine
from dungeon.components import LootComponent

# Check ItemDefinition loading
from dungeon.data_manager import load_item_definitions
items = load_item_definitions()
print(f"Loaded {len(items)} items manually.")
if items:
    first = list(items.values())[0]
    print(f"First Item: {first.name}, MinFloor: {getattr(first, 'min_floor', 'MISSING')}")

engine = Engine("DebugPlayer")
# Force Normal Map init
engine.current_level = 10
# Debug _get_eligible_items directly
eligible = engine._get_eligible_items(10)
print(f"Eligible items for Floor 10: {len(eligible)}")
if eligible:
    print(f"Example eligible: {eligible[0].name}")

engine._initialize_world(spawn_at="START")

loot = engine.world.get_entities_with_components({LootComponent})
print(f"Loot Entities: {len(loot)}")

for e in loot:
    l = e.get_component(LootComponent)
    if l.items:
        print(f"  - Loot: {[i['item'].name for i in l.items]} Gold: {l.gold}")
    else:
        print(f"  - Loot: EMPTY Gold: {l.gold}")
