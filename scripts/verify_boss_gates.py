import sys
import os

# Ensure project root is in path
sys.path.insert(0, '/home/dogsinatas/python_project/dungeon')

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import MapComponent, BossGateComponent, BossComponent, StatsComponent, PositionComponent, MessageComponent
from dungeon.constants import EXIT_NORMAL

def verify_boss_gate():
    print("--- Verifying Boss-Gated Stairs System (Floor 25) ---")
    
    # 1. Initialize engine
    engine = Engine(player_name="TestHero")
    
    # Reset world to avoid double initialization issues
    engine.world = World(engine)
    engine.current_level = 25
    engine._initialize_world()
    engine._initialize_systems()
    
    # Process initialization events (like on_floor_entry bark)
    engine.world.event_manager.process_events()
    
    engine.world.event_manager.process_events()
    
    # 2. Check if BossGateComponent exists on map entity
    world = engine.world
    print(f"Engine Current Level: {engine.current_level} (type: {type(engine.current_level)})")
    
    print("All Entities and their components:")
    for ent_id, entity in world._entities.items():
        comp_names = [c.__name__ for c in entity._components.keys()]
        print(f"  Entity {ent_id}: {comp_names}")

    # Check MapComponent separately
    map_ents = world.get_entities_with_components({MapComponent})
    print(f"Entities with MapComponent: {[e.entity_id for e in map_ents]}")
    if map_ents:
        e = map_ents[0]
        print(f"Map Entity {e.entity_id} components: {[c.__name__ for c in e._components.keys()]}")

    map_ents = world.get_entities_with_components({MapComponent, BossGateComponent})
    if not map_ents:
        print("[FAIL] BossGateComponent not found on Floor 25")
        return False
    
    map_ent = map_ents[0]
    map_comp = map_ent.get_component(MapComponent)
    boss_gate = map_ent.get_component(BossGateComponent)
    
    print(f"[OK] BossGateComponent found. Next region: {boss_gate.next_region_name}")
    
    # 3. Check if stairs are hidden
    ex, ey = engine.dungeon_map.exit_x, engine.dungeon_map.exit_y
    initial_tile = map_comp.tiles[ey][ex]
    if initial_tile == EXIT_NORMAL:
        print(f"[FAIL] Exit stairs are NOT hidden at ({ex}, {ey}). Tile: {initial_tile}")
        return False
    print(f"[OK] Exit stairs are hidden. Tile at exit pos ({ex}, {ey}) is '{initial_tile}'")
    
    # 4. Find the boss and kill it
    bosses = world.get_entities_with_components({BossComponent, StatsComponent})
    if not bosses:
        print("[FAIL] No boss found on Floor 25")
        return False
    
    butcher = next((b for b in bosses if b.get_component(BossComponent).boss_id == "BUTCHER"), None)
    if not butcher:
        print("[FAIL] Butcher not found on Floor 25")
        return False
    
    print(f"[OK] Found Butcher. HP: {butcher.get_component(StatsComponent).current_hp}")
    
    # Kill the Butcher
    stats = butcher.get_component(StatsComponent)
    stats.current_hp = 0
    
    # We need to trigger CombatSystem to process the death or call _apply_damage logic.
    # In engine.py, death is usually handled in CombatSystem.
    # Let's manually trigger a combat result or just wait for the next turn if systems were running.
    # Since we are in a script, let's look at how we can trigger the death logic.
    
    print("Simulating Butcher death...")
    # The actual death handling is in CombatSystem._apply_damage which is called during combat.
    # To test the system logic, we can manually call a method that emulates the death trigger
    # or just use the system directly.
    
    # In our implementation, we added the logic to CombatSystem._apply_damage.
    # Let's try to trigger a dummy attack that kills it.
    combat_sys = world.get_system(next(s for s in world._systems if s.__class__.__name__ == 'CombatSystem').__class__)
    player = world.get_player_entity()
    
    # This will trigger the death logic inside _apply_damage
    combat_sys._apply_damage(player, butcher, distance=1, damage_factor=9999)
    
    # 5. Check if stairs appeared
    after_tile = map_comp.tiles[ey][ex]
    if after_tile != EXIT_NORMAL:
        print(f"[FAIL] Exit stairs did NOT appear after boss death. Tile: {after_tile}")
        return False
    
    print(f"[OK] Exit stairs revealed! Tile at exit pos ({ex}, {ey}) is '{after_tile}'")
    
    # 6. Check messages
    world.event_manager.process_events() # Process MessageEvents
    msg_ent = world.get_entities_with_components({MessageComponent})[0]
    msgs = msg_ent.get_component(MessageComponent).messages
    all_msgs = [m['text'] for m in msgs]
    print("Recent messages:")
    for m in all_msgs[-10:]:
        print(f"  - {m}")
    
    # Check Entrance Bark (on_floor_entry)
    if any("I smell someone... delicious..." in m for m in all_msgs):
         print("[OK] Entry bark found.")
    else:
         print("[FAIL] Entry bark NOT found.")
         return False

    # Check Death Bark
    if any("Meat... is... done..." in m for m in all_msgs):
        print("[OK] Death bark found in log.")
    else:
        print("[FAIL] Death bark NOT found in log.")
        return False

    # Check visual bark state
    msg_after_death = [m['text'] for m in msgs]
    if any("Catacombs(으)로 가는 계단이 나타났습니다" in m for m in msg_after_death):
        print("[OK] Appearance message found.")
    else:
        print("[FAIL] Appearance message NOT found.")
        return False

    return True

if __name__ == "__main__":
    if verify_boss_gate():
        print("\n[SUCCESS] Boss-Gated Stairs System verified successfully!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Verification failed.")
        sys.exit(1)
