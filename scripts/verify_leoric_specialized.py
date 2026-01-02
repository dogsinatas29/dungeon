import sys
import os
import time
import random

# 프로젝트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dungeon')))

from dungeon.ecs import World, Entity
from dungeon.components import BossComponent, PositionComponent, StatsComponent, MonsterComponent, MapComponent, PetrifiedComponent, AIComponent
from dungeon.systems import BossSystem, CombatSystem
from dungeon.data_manager import load_boss_patterns

class MockEngine:
    def __init__(self, data_path, world):
        self.world = world
        self.boss_patterns = load_boss_patterns(data_path)
        self.last_boss_id = "BUTCHER"
        self.monster_defs = {}
        self.item_defs = {}
        self.player_name = "Player"
    def _spawn_boss(self, x, y, boss_name, is_summoned=False):
        # Create a mock boss
        ent = self.world.create_entity()
        self.world.add_component(ent.entity_id, PositionComponent(x, y))
        self.world.add_component(ent.entity_id, MonsterComponent(boss_name, boss_name, is_summoned=is_summoned))
        self.world.add_component(ent.entity_id, BossComponent(boss_name))
        self.world.add_component(ent.entity_id, StatsComponent(100, 100, 10, 10))
        return ent
    def _spawn_monster_at(self, x, y, pool=None):
        ent = self.world.create_entity()
        self.world.add_component(ent.entity_id, PositionComponent(x, y))
        m_id = pool[0] if pool else "SKELETON"
        self.world.add_component(ent.entity_id, MonsterComponent(m_id, m_id))
        self.world.add_component(ent.entity_id, StatsComponent(20, 20, 5, 2))
        return ent

def test_leoric_patterns():
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dungeon', 'data'))
    
    world = World(None)
    engine = MockEngine(data_path, world)
    world.engine = engine
    
    boss_system = BossSystem(world)
    combat_system = CombatSystem(world)
    
    # 맵 정보
    map_ent = world.create_entity()
    tiles = [['.' for _ in range(50)] for _ in range(50)]
    world.add_component(map_ent.entity_id, MapComponent(50, 50, tiles))
    
    leoric = world.create_entity()
    world.add_component(leoric.entity_id, BossComponent("LEORIC"))
    world.add_component(leoric.entity_id, MonsterComponent("Leoric", "LEORIC"))
    world.add_component(leoric.entity_id, PositionComponent(10, 10))
    l_stats = StatsComponent(500, 500, 20, 15)
    world.add_component(leoric.entity_id, l_stats)
    
    player = world.create_entity()
    world.add_component(player.entity_id, PositionComponent(10, 11))
    p_stats = StatsComponent(100, 100, 10, 10)
    world.add_component(player.entity_id, p_stats)
    
    def mock_get_player_entity(): return player
    world.get_player_entity = mock_get_player_entity

    # 1. Life Steal Test (30% in melee)
    print("--- 1. Life Steal Test (30%) ---")
    l_stats.current_hp = 400 # Damaged Leoric
    # CombatSystem._apply_damage call
    # Damage: 20 -> Player def 10. Net 10.
    # 30% of 10 = 3.
    combat_system._apply_damage(leoric, player, distance=1)
    print(f"Leoric HP after melee hit: {l_stats.current_hp} (Previous: 400)")
    assert l_stats.current_hp > 400
    
    # 2. 10% HP Interval Smite Test
    print("\n--- 2. 10% HP Interval Smite Test ---")
    l_stats.current_hp = 449 # Just below 90% (500*0.9 = 450)
    # BossSystem.process check
    # We expect a Smite message and DirectionalAttackEvents
    boss_system.process()
    assert "smite_90" in leoric.get_component(BossComponent).triggered_hps
    print("Success: 90% Smite triggered.")

    # 3. Minion Swarm (HP > 50%)
    print("\n--- 3. Minion Swarm Test ---")
    # Reset cooldown
    leoric.get_component(BossComponent).last_swarm_time = 0
    # Process multiple times to trigger swarm (30% chance)
    swarmed = False
    for _ in range(50):
        l_stats.last_action_time = 0 # Reset action delay
        boss_system.process()
        m_entities = world.get_entities_with_components({MonsterComponent})
        skeletons = [m for m in m_entities if m.get_component(MonsterComponent).monster_id == "SKELETON"]
        if len(skeletons) > 0:
            swarmed = True
            print(f"Success: Skeletons spawned ({len(skeletons)}).")
            break
    assert swarmed

    # 4. Petrify Test (minions >= 15)
    print("\n--- 4. Petrify Test ---")
    # Add 15 skeletons
    for _ in range(15):
        engine._spawn_monster_at(12, 12, ["SKELETON"])
    
    leoric.get_component(BossComponent).last_petrify_time = 0
    petrified = False
    for _ in range(50):
        l_stats.last_action_time = 0 # Reset action delay
        boss_system.process()
        if player.has_component(PetrifiedComponent):
            petrified = True
            print("Success: Player petrified by Leoric.")
            break
    assert petrified

    # 5. Boss Summon (at 50%)
    print("\n--- 5. Boss Summon at 50% Test ---")
    l_stats.current_hp = 249 # Just below 50%
    # Reset triggered barks if any
    # Boss summon should trigger at 50% for Leoric
    boss_system.process()
    # Check if a new boss ghost spawned
    m_entities = world.get_entities_with_components({MonsterComponent})
    ghosts = [m for m in m_entities if m.get_component(MonsterComponent).is_summoned]
    assert len(ghosts) > 0
    print(f"Success: Ghost boss summoned at 50% HP.")

    print("\n[SUCCESS] Leoric's specialized patterns verified.")

if __name__ == "__main__":
    test_leoric_patterns()
