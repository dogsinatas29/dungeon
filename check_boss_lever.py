
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dungeon')))

from dungeon.engine import Engine
from dungeon.components import PositionComponent, SwitchComponent, DoorComponent, StatsComponent
from dungeon.events import InteractEvent

def test_boss_lever():
    print("Testing Boss Lever Interaction...")
    
    # 1. Initialize Engine
    engine = Engine()
    world = engine.world
    
    # Re-setup: Clear and force Player ID 1
    world.clear_all_entities()
    
    player = world.create_entity() # ID 1
    world.add_component(player.entity_id, PositionComponent(x=5, y=5))
    world.add_component(player.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5))

    
    door = world.create_entity()
    world.add_component(door.entity_id, PositionComponent(x=10, y=10))
    world.add_component(door.entity_id, DoorComponent(is_open=False, is_locked=True))
    
    lever = world.create_entity()
    world.add_component(lever.entity_id, PositionComponent(x=5, y=5))
    world.add_component(lever.entity_id, SwitchComponent(is_open=False, linked_door_pos=(10, 10)))

    print(f"Player ID: {player.entity_id} (Expected 1)")
    
    # 5. Trigger Interaction (Simulate Lever Pull)
    # Push InteractEvent to queue
    event = InteractEvent(player.entity_id, lever.entity_id, "TOGGLE")
    world.event_manager.push(event)
    
    # 6. Process Events
    print("Processing Events...")
    world.event_manager.process_events()
    
    # 7. Check Results
    door_comp = door.get_component(DoorComponent)
    player_stats = player.get_component(StatsComponent)
    
    print(f"Door Final State: Open={door_comp.is_open}, Locked={door_comp.is_locked}")
    print(f"Player HP: {player_stats.current_hp} / 100")
    
    if door_comp.is_open and not door_comp.is_locked:
        print("PASS: Door opened and unlocked.")
    else:
        print("FAIL: Door did not open.")
        
    if player_stats.current_hp < 100:
        print(f"PASS: Player took damage (HP: {player_stats.current_hp}). Trap Triggered.")
    else:
        print("FAIL: Player took no damage. Trap Logic Failed.")

if __name__ == "__main__":
    test_boss_lever()
