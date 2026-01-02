import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.append(os.getcwd())

from dungeon.engine import Engine
from dungeon.components import MonsterComponent

class TestDensity(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(player_name="TestHero")
        # Mock dungeon to control floor
        self.engine.dungeon = MagicMock()
        self.engine.dungeon.dungeon_level_tuple = (1, 0) # Default
        
    def test_map_size_and_density_tier1(self):
        # Lv 1-25: 60x40, ~60 monsters
        # Engine init already spawned monsters for level 1 (default). 
        # So we just check current state.
        
        self.assertEqual(self.engine.dungeon_map.width, 60)
        self.assertEqual(self.engine.dungeon_map.height, 40)
        
        # Check Monster Count
        monsters = [e for e in self.engine.world.get_entities_with_components([MonsterComponent])]
        count = len(monsters)
        # Allow +/- 20% + corridor variance
        # Target 60. 
        # Rooms (42) -> 42 +/- 20% = 33-51
        # Corridors (18) -> 18 +/- variance
        print(f"Tier 1 (Target 60) Count: {count}")
        self.assertTrue(40 <= count <= 80, f"Tier 1 count {count} not in range")

    def test_map_size_and_density_tier4(self):
        # Lv 76-99: 100x80, ~150 monsters
        # New engine for clean state to avoid dealing with cleanup logic complexity
        self.engine = Engine(player_name="TestHero")
        
        # We need to trick the engine to spawn for level 85.
        # But _initialize_world is called in __init__ with floor 1.
        # We must clear and respawn.
        # Just manually clear monsters.
        monsters = [e for e in self.engine.world.get_entities_with_components([MonsterComponent])]
        for m in monsters:
             self.engine.world.delete_entity(m.entity_id)
             
        self.engine.dungeon = MagicMock()
        self.engine.dungeon.dungeon_level_tuple = (85, 0)
        self.engine.current_level = 85
        
        self.engine._initialize_world()
        
        self.assertEqual(self.engine.dungeon_map.width, 100)
        self.assertEqual(self.engine.dungeon_map.height, 80)
        
        monsters = [e for e in self.engine.world.get_entities_with_components([MonsterComponent])]
        count = len(monsters)
        print(f"Tier 4 (Target 150) Count: {count}")
        # Target 150.
        self.assertTrue(100 <= count <= 200, f"Tier 4 count {count} not in range")

if __name__ == '__main__':
    unittest.main()
