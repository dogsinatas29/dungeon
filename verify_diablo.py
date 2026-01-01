
import random
import time
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dungeon')))

from dungeon.engine import Engine
from dungeon.systems import BossSystem, CombatSystem
from dungeon.components import (
    PositionComponent, StatsComponent, BossComponent, MonsterComponent, 
    PetrifiedComponent, StunComponent, MapComponent, AIComponent
)
from dungeon.constants import BOSS_SEQUENCE

class MockWorld:
    def __init__(self):
        self.entities = {}
        self.next_entity_id = 1
        self._systems = []
        self.event_manager = MockEventManager()
        self.engine = MockEngine(self)

    def create_entity(self):
        ent = MockEntity(self.next_entity_id)
        self.entities[self.next_entity_id] = ent
        self.next_entity_id += 1
        return ent

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)
    
    def get_entities_with_components(self, component_types):
        result = []
        for ent in self.entities.values():
            if all(ent.has_component(ct) for ct in component_types):
                result.append(ent)
        return result

    def get_player_entity(self):
        # Assume ID 1 is player
        return self.entities.get(1)

    def add_component(self, entity_id, component):
        if entity_id in self.entities:
            self.entities[entity_id].add_component(component)

class MockEntity:
    def __init__(self, entity_id):
        self.entity_id = entity_id
        self.components = {}

    def add_component(self, component):
        self.components[type(component)] = component

    def get_component(self, component_type):
        return self.components.get(component_type)

    def has_component(self, component_type):
        return component_type in self.components
    
    def remove_component(self, component_type):
        if component_type in self.components:
            del self.components[component_type]

class MockEventManager:
    def __init__(self):
        self.events = []
    def push(self, event):
        # print(f"[Event] {type(event).__name__}: {vars(event)}")
        self.events.append(event)
    def register(self, event_type, listener):
        pass

class MockEngine:
    def __init__(self, world):
        self.world = world
        self.player_name = "Player"
        self.boss_patterns = {}
        self.spawned_bosses = []
        self.dungeon = None # Needed for loot but verify script might not hit it
        
    def trigger_shake(self, duration):
        print(f"[Engine] Screen Shake: {duration}")

    def _spawn_boss(self, x, y, boss_name, is_summoned=False):
        print(f"[Engine] Spawn Boss: {boss_name} (Summoned: {is_summoned})")
        self.spawned_bosses.append(boss_name)
        
        # Create Dummy Entity for summoned boss
        b_ent = self.world.create_entity()
        self.world.add_component(b_ent.entity_id, PositionComponent(x=x, y=y))
        self.world.add_component(b_ent.entity_id, MonsterComponent(monster_id=boss_name, is_summoned=is_summoned, type_name=boss_name))
        self.world.add_component(b_ent.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0, action_delay=0.6))
        
    def _get_entity_name(self, entity):
        return "Entity"

def test_diablo_mechanics():
    print("=== Testing Diablo Patterns ===")
    world = MockWorld()
    
    # Setup Player
    player = world.create_entity() # ID 1
    player.add_component(PositionComponent(x=10, y=10))
    world.add_component(player.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=20, defense=10))

    # Setup Map (Required for BossSystem)
    map_ent = world.create_entity()
    tiles = [['.' for _ in range(20)] for _ in range(20)]
    world.add_component(map_ent.entity_id, MapComponent(width=20, height=20, tiles=tiles))

    # Setup Diablo
    diablo = world.create_entity()
    world.add_component(diablo.entity_id, PositionComponent(x=10, y=5))
    d_stats = StatsComponent(max_hp=2000, current_hp=2000, attack=50, defense=20, flags={"BOSS", "DIABLO"})
    world.add_component(diablo.entity_id, d_stats)
    world.add_component(diablo.entity_id, BossComponent(boss_id="DIABLO"))
    world.add_component(diablo.entity_id, MonsterComponent(monster_id="DIABLO", type_name="Diablo"))

    boss_system = BossSystem(world)
    boss_system.patterns = {
        "DIABLO": {
             "entrance_bark": "Death is not the end... it is the beginning of your torment!",
             "on_hp_85": "Fresh meat for the grinder!",
             "on_hp_70": "The Skeleton King returns!",
             "on_hp_55": "The cold of the grave awaits!",
             "on_hp_20": "ALL SHALL SUFFER!"
        }
    }
    
    # 1. 85% HP Check (Butcher Summon)
    print("\n--- 1. 85% HP Check (Butcher Summon) ---")
    d_stats.current_hp = 1700 # 85% of 2000
    d_stats.last_action_time = 0 # Force action
    boss_system.process()
    
    expected_summons = ["BUTCHER"]
    print(f"Spawned Bosses: {world.engine.spawned_bosses}")
    assert "BUTCHER" in world.engine.spawned_bosses, "Butcher was not summoned at 85% HP"

    # 2. 70% HP Check (Leoric Summon)
    print("\n--- 2. 70% HP Check (Leoric Summon) ---")
    d_stats.current_hp = 1400 # 70% of 2000
    d_stats.last_action_time = 0 # Force action
    boss_system.process()
    
    print(f"Spawned Bosses: {world.engine.spawned_bosses}")
    assert "LEORIC" in world.engine.spawned_bosses, "Leoric was not summoned at 70% HP"

    # 3. 55% HP Check (Lich King Summon)
    print("\n--- 3. 55% HP Check (Lich King Summon) ---")
    d_stats.current_hp = 1100 # 55% of 2000
    d_stats.last_action_time = 0 # Force action
    boss_system.process()
    
    print(f"Spawned Bosses: {world.engine.spawned_bosses}")
    assert "LICH_KING" in world.engine.spawned_bosses, "Lich King was not summoned at 55% HP"
    
    # 4. Enrage Check (20% HP)
    print("\n--- 4. Enrage Check (20% HP) ---")
    d_stats.current_hp = 400 # 20% of 2000
    
    # Check if summon (Butcher) gets speed buff
    # Retrieve the dummy Butcher entity created in mock
    butcher_ent = None
    all_monsters = world.get_entities_with_components({MonsterComponent})
    for m in all_monsters:
        m_comp = m.get_component(MonsterComponent)
        if m_comp.monster_id == "BUTCHER" and m_comp.is_summoned:
            butcher_ent = m
            break
            
    assert butcher_ent is not None, "Butcher entity not found in world for Enrage test"
    b_stats = butcher_ent.get_component(StatsComponent)
    b_stats.action_delay = 0.6 # Reset to normal
    
    boss_system.process() # Should trigger Enrage and apply buff logic calling _process_diablo_logic
    
    # Since _process_diablo_logic is likely called via the "Logic" section which might have chance or condition
    # Wait, check systems.py loop:
    # It calls _process_diablo_logic if boss_id == "DIABLO".
    # And inside _process_diablo_logic, it iterates all_monsters.
    
    # Ensure call to _process_diablo_logic happened.
    # In BossSystem.process, the logic call happens if boss.is_engaged is True.
    diablo.get_component(BossComponent).is_engaged = True
    
    # Also, Logic only runs if HP > 0 (checked).
    # And logic triggers are typically chance based?
    # No, check code:
    # elif boss.boss_id == "DIABLO":
    #    if self._process_diablo_logic(boss_ent, p_pos, dist, map_comp): ...
    
    # So we need to ensure the logic method is reached.
    boss_system.process()
    
    print(f"Butcher Action Delay: {b_stats.action_delay}")
    assert b_stats.action_delay <= 0.3, f"Enrage Speed Buff Failed. Delay: {b_stats.action_delay}"

    print("Verification Script Finished.")

if __name__ == "__main__":
    test_diablo_mechanics()
