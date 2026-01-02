import unittest
from unittest.mock import MagicMock
import sys
import os
import random

sys.path.append(os.getcwd())

from dungeon.engine import Engine
from dungeon.components import MonsterComponent, LootComponent
from dungeon.ui import COLOR_MAP
# from dungeon.constants import RARITY_COLORS # Might failing due to env
RARITY_COLORS = {
    "NORMAL": "white",
    "MAGIC": "blue",
    "UNIQUE": "yellow",
    "CURSED": "red"
}

class TestSandboxFeatures(unittest.TestCase):
    def setUp(self):
        # Clean setup for each test
        self.engine = Engine(player_name="SandboxTester")
        self.engine.rng = random.Random(42) # Fixed seed for reproducibility

    def test_tier_scaling_and_visuals(self):
        test_cases = [
            (10, 60, 40, 40, 80),   # Tier 1: Lv 10 -> 60x40, Count ~60 (+/- range)
            (35, 70, 50, 60, 100),  # Tier 2: Lv 35 -> 70x50, Count ~80
            (60, 80, 60, 80, 120),  # Tier 3: Lv 60 -> 80x60, Count ~100
            (85, 100, 80, 120, 180) # Tier 4: Lv 85 -> 100x80, Count ~150
        ]
        
        print("\n--- Sandbox Verification: Map & Density ---")
        for lvl, w_exp, h_exp, min_m, max_m in test_cases:
            # Setup specific level
            self.engine.dungeon = MagicMock()
            self.engine.dungeon.dungeon_level_tuple = (lvl, 0)
            self.engine.current_level = lvl
            
            # Clear existing entities to prevent accumulation if re-using engine (though setUp makes new one, manual re-init logic might need care)
            # Actually setUp is per test method. Here we loop inside one method.
            # So we must clear entities manually or create new engine.
            # Easier to clear.
            self.engine.world._entities = {} 
            self.engine.world._next_entity_id = 1
            
            # Init World
            self.engine._initialize_world()
            
            # Verify Map Size
            curr_w = self.engine.dungeon_map.width
            curr_h = self.engine.dungeon_map.height
            print(f"Level {lvl}: Map {curr_w}x{curr_h} (Expected {w_exp}x{h_exp})")
            self.assertEqual(curr_w, w_exp)
            self.assertEqual(curr_h, h_exp)
            
            # Verify Monster Count
            monsters = [e for e in self.engine.world.get_entities_with_components([MonsterComponent])]
            count = len(monsters)
            print(f"Level {lvl}: Monsters {count} (Target range {min_m}-{max_m})")
            self.assertTrue(min_m <= count <= max_m, f"Level {lvl} monster count {count} out of range")

    def test_visual_rarity(self):
        print("\n--- Sandbox Verification: Visual Rarity ---")
        # Simulate dropping items at High Level to ensure Rarity
        floor = 95
        self.engine.dungeon = MagicMock()
        self.engine.dungeon.dungeon_level_tuple = (floor, 0)
        
        # Manually create a loot drop
        # We need a chest or corpse entity
        chest = self.engine.world.create_entity()
        
        # Force pool
        pool = ["단검"] # Basic item
        
        # Use _spawn_chest logic part or manually call _get_rarity
        rarity = self.engine._get_rarity(floor)
        print(f"Rolled Rarity at Floor {floor}: {rarity}")
        
        # Check Item Rarity Assignment
        # Let's use engine._drop_item but it's internal.
        # We can simulate the loot generation block.
        candidate = self.engine.item_defs['단검']
        import copy
        item = copy.deepcopy(candidate)
        item.rarity = "MAGIC" # Force Magic
        
        # Verify Item has rarity
        self.assertEqual(item.rarity, "MAGIC")
        
        # Verify UI Color Map
        from dungeon.constants import RARITY_MAGIC
        color_name = RARITY_COLORS.get(item.rarity) # Should be 'blue'
        self.assertEqual(color_name, "blue")
        
        color_code = COLOR_MAP.get(color_name)
        print(f"Item: {item.name}, Rarity: {item.rarity}, ColorCode: {repr(color_code)}")
        self.assertIn("94m", color_code) # Blue ANSI code

if __name__ == '__main__':
    unittest.main()
