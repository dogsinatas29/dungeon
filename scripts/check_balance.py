import csv
import os
import unittest

DATA_DIR = 'data'

class TestBalance(unittest.TestCase):
    def test_player_nerf(self):
        # Warrior base HP was 90. 90 * 0.6 = 54.
        found = False
        with open(os.path.join(DATA_DIR, 'classes.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['class_id'] == 'WARRIOR':
                    hp = int(row['hp'])
                    self.assertEqual(hp, 54, f"Warrior HP should be 54, got {hp}")
                    found = True
                    break
        self.assertTrue(found, "Warrior class not found")

    def test_monster_buff(self):
        # Goblin HP was 20. 20 * 1.2 = 24.
        found = False
        with open(os.path.join(DATA_DIR, 'monsters.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                if row['ID'].strip() == 'GOBLIN':
                    hp = int(row['HP'])
                    self.assertEqual(hp, 24, f"Goblin HP should be 24, got {hp}")
                    found = True
                    break
        self.assertTrue(found, "Goblin monster not found")

    def test_boss_buff(self):
        # Butcher HP was 5000. 5000 * 1.8 = 9000.
        found = False
        with open(os.path.join(DATA_DIR, 'Boss.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                if row['ID'].strip() == 'BUTCHER':
                    hp = int(row['HP'])
                    # 9000
                    self.assertEqual(hp, 9000, f"Butcher HP should be 9000, got {hp}")
                    found = True
                    break
        self.assertTrue(found, "Butcher boss not found")

if __name__ == '__main__':
    unittest.main()
