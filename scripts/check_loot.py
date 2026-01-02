import unittest
from unittest.mock import MagicMock
import sys
import os
import random

sys.path.append(os.getcwd())

from dungeon.engine import Engine

class TestLootSystem(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(player_name="TestHero")
        # Mock dependencies if strictly needed, but _get_rarity is pure logic mostly
        
    def test_rarity_distribution_tier1(self):
        # Lv 1-25: Normal 85%, Magic 14.5%, Unique 0.5%
        floor = 10
        stats = {"NORMAL": 0, "MAGIC": 0, "UNIQUE": 0}
        n = 10000
        for _ in range(n):
            r = self.engine._get_rarity(floor, magic_find=0)
            stats[r] += 1
            
        # Allow 2% margin
        self.assertAlmostEqual(stats["NORMAL"]/n, 0.85, delta=0.02)
        self.assertAlmostEqual(stats["MAGIC"]/n, 0.145, delta=0.02)
        self.assertAlmostEqual(stats["UNIQUE"]/n, 0.005, delta=0.005)

    def test_rarity_distribution_tier2(self):
        # Lv 26-50: Normal 70%, Magic 24.5%, Unique 5.5%
        floor = 40
        stats = {"NORMAL": 0, "MAGIC": 0, "UNIQUE": 0}
        n = 10000
        for _ in range(n):
            r = self.engine._get_rarity(floor, magic_find=0)
            stats[r] += 1
            
        self.assertAlmostEqual(stats["NORMAL"]/n, 0.70, delta=0.02)
        self.assertAlmostEqual(stats["MAGIC"]/n, 0.245, delta=0.02)
        self.assertAlmostEqual(stats["UNIQUE"]/n, 0.055, delta=0.01)

    def test_rarity_distribution_tier3(self):
        # Lv 51+: Normal 30%, Magic 44.5%, Unique 25.5%
        floor = 60
        stats = {"NORMAL": 0, "MAGIC": 0, "UNIQUE": 0}
        n = 10000
        for _ in range(n):
            r = self.engine._get_rarity(floor, magic_find=0)
            stats[r] += 1
            
        self.assertAlmostEqual(stats["NORMAL"]/n, 0.30, delta=0.02)
        self.assertAlmostEqual(stats["MAGIC"]/n, 0.445, delta=0.02)
        self.assertAlmostEqual(stats["UNIQUE"]/n, 0.255, delta=0.02)

    def test_affix_rolling(self):
        # Prefix 40%, Suffix 40%, Both 20%
        # Mock prefix_defs and suffix_defs to allow all
        self.engine.prefix_defs = {'P1': MagicMock(allowed_types={'WEAPON'}, min_level=1)}
        self.engine.suffix_defs = {'S1': MagicMock(allowed_types={'WEAPON'}, min_level=1)}
        
        # We need to mock _create_item_with_affix or check internal logic by mocking random?
        # Better: mock random.random to check thresholds OR run statistics.
        # Let's run stats on _roll_magic_affixes directly.
        # But _roll_magic_affixes returns IDs. We need to catch what it tried to roll.
        
        counts = {"P": 0, "S": 0, "B": 0, "N": 0}
        n = 10000
        for _ in range(n):
             # Force roll
             pid, sid = self.engine._roll_magic_affixes('WEAPON', 10)
             if pid and sid: counts["B"] += 1
             elif pid: counts["P"] += 1
             elif sid: counts["S"] += 1
             else: counts["N"] += 1
        
        # Note: _roll_magic_affixes logic:
        # roll < 0.4 -> want prefix (only prefix? wait)
        # 0.4 <= roll < 0.8 -> want suffix
        # roll >= 0.8 -> want both
        
        # However, it also checks if valid prefix/suffix exists. 
        # With our mock, they always exist.
        
        self.assertAlmostEqual(counts["P"]/n, 0.40, delta=0.02)
        self.assertAlmostEqual(counts["S"]/n, 0.40, delta=0.02)
        self.assertAlmostEqual(counts["B"]/n, 0.20, delta=0.02)


if __name__ == '__main__':
    unittest.main()
