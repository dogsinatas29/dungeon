
import unittest
from unittest.mock import MagicMock
from dungeon.ecs import World, Entity
from dungeon.components import LevelComponent, StatsComponent, MonsterComponent
from dungeon.systems import LevelSystem, CombatSystem
from dungeon.data_manager import ClassDefinition, MonsterDefinition

class MockEngine:
    def __init__(self):
        self.class_defs = {}
        self.monster_defs = {
            "SKELETON_KING": MonsterDefinition(
                ID="SKELETON_KING", Name="Skeleton King", Symbol="K", Color="red",
                HP=100, ATT="5-10", DEF=10, LV=5, EXP_GIVEN=500,
                CRIT_CHANCE=0.1, CRIT_MULT=1.5, MOVE_TYPE="WALK", ACTION_DELAY=1.0,
                flags="BOSS,UNDEAD"
            ),
            "DIABLO": MonsterDefinition(
                ID="DIABLO", Name="Diablo", Symbol="D", Color="red",
                HP=500, ATT="10-20", DEF=20, LV=20, EXP_GIVEN=5000,
                CRIT_CHANCE=0.2, CRIT_MULT=2.0, MOVE_TYPE="WALK", ACTION_DELAY=0.8,
                flags="BOSS,DIABLO,DEMON"
            )
        }
        self.ui = MagicMock()
        self.dungeon = MagicMock()
        self.dungeon.dungeon_level_tuple = (1, 1)

    def _get_eligible_items(self, floor):
        return [] # No loot for this test

    def _recalculate_stats(self):
        pass

class TestBonusPoints(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MockEngine()
        self.world = World(self.mock_engine)
        self.level_system = LevelSystem(self.world)
        self.combat_system = CombatSystem(self.world)
        self.world.add_system(self.level_system)
        self.world.add_system(self.combat_system)
        
        # Player
        self.player = self.world.create_entity()
        self.world.add_component(self.player.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="WARRIOR"))
        self.world.engine.player = self.player # CombatSystem access player

        # Boss
        self.boss = self.world.create_entity()
        self.world.add_component(self.boss.entity_id, MonsterComponent(type_name="SKELETON_KING"))
        self.world.add_component(self.boss.entity_id, StatsComponent(max_hp=10, current_hp=10, attack=5, defense=0, base_max_hp=10, base_max_mp=10))
        self.world.add_component(self.boss.entity_id, LevelComponent(level=5, exp=0, exp_to_next=0, job="Boss"))
        
        # Manually Add Position so death logic works (it checks position for corpses)
        from dungeon.components import PositionComponent
        self.world.add_component(self.boss.entity_id, PositionComponent(x=5, y=5))
        self.world.add_component(self.player.entity_id, PositionComponent(x=5, y=4))

    def test_manual_grant(self):
        level_comp = self.player.get_component(LevelComponent)
        self.assertEqual(level_comp.stat_points, 0)
        
        self.level_system.grant_stat_points(self.player, 2, "Quest Reward")
        
        self.assertEqual(level_comp.stat_points, 2)
        # Check Message
        # Mock event manager check is hard without mocking it specifically, 
        # but logic is simple enough.

    def test_boss_kill_reward(self):
        # Trigger Death Logic in CombatSystem
        # We simulate this by setting HP to 0 and calling _apply_damage logic or simulating the check if exposed.
        # However, _apply_damage calls death logic. Let's call _apply_damage with lethal damage.
        
        # Ensure Boss stats has flags (loaded from def in real game, we need to inject into component or ensure system looks up def)
        # System looks up def using MonsterComponent.type_name.
        
        level_comp = self.player.get_component(LevelComponent)
        stats = self.boss.get_component(StatsComponent)
        
        # Lethal Damage
        # _apply_damage (attacker, target, distance=1, skill=None, damage_factor=1.0, allow_splash=True)
        # We grant huge damage to ensure kill
        self.combat_system._apply_damage = MagicMock(wraps=self.combat_system._apply_damage) 
        
        # ACTUALLY, checking _apply_damage internals is hard.
        # But `process` calls `_apply_damage` is not true. `process` handles AI attack.
        # We need to invoke `_apply_damage` manually or mimic death check loop.
        # WAIT: Death check is INSIDE `_apply_damage`.
        
        # Let's direct force HP to 0 and manually run the death block logic? 
        # No, easier to call `_apply_damage` with enough damage.
        
        # Mock player stats for attack calc
        self.world.add_component(self.player.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=1000, defense=0, str=100, dex=10, mag=10, vit=10))
        
        self.combat_system._apply_damage(self.player, self.boss, distance=1)
        
        # Check if points granted
        # Skeleton King (BOSS) -> +1 Point
        # But wait, did it die? 
        # _apply_damage reduces HP. If <= 0, death logic runs.
        
        self.assertTrue(stats.current_hp <= 0)
        self.assertEqual(level_comp.stat_points, 1)

if __name__ == '__main__':
    unittest.main()
