import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, '/home/dogsinatas/python_project/dungeon')

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import MapComponent, BossComponent, StatsComponent, PositionComponent, MessageComponent
from dungeon.constants import EXIT_NORMAL

def verify_enhanced_dialogues():
    print("--- Verifying Enhanced Boss Dialogue System ---")
    from dungeon.events import BossBarkEvent as BBE
    print(f"DEBUG: Script BossBarkEvent ID: {id(BBE)}")
    
    engine = Engine(player_name="TestHero")
    world = engine.world
    engine.current_level = 25
    engine._initialize_world()
    engine._initialize_systems()
    
    # Process initial events
    world.event_manager.process_events()
    
    # 1. Verify Entry Bark is NOT triggered yet (player is at start, boss is at exit)
    msg_ent = world.get_entities_with_components({MessageComponent})[0]
    msg_comp = msg_ent.get_component(MessageComponent)
    
    def get_msgs():
        return [m['text'] for m in msg_comp.messages]

    print("Checking initial state (far away)...")
    if any("I smell someone" in m for m in get_msgs()):
        print("[FAIL] Entry bark triggered too early!")
        return False
    else:
        print("[OK] Entry bark not triggered far away.")

    # 2. Simulate player approach (dist <= 15)
    player = world.get_player_entity()
    p_pos = player.get_component(PositionComponent)
    
    boss_ent = next(iter(world.get_entities_with_components({BossComponent, PositionComponent})))
    b_pos = boss_ent.get_component(PositionComponent)
    b_comp = boss_ent.get_component(BossComponent)

    print(f"Player at ({p_pos.x}, {p_pos.y}), Boss at ({b_pos.x}, {b_pos.y})")
    print(f"Current distance: {abs(p_pos.x - b_pos.x) + abs(p_pos.y - b_pos.y)}")

    # Move player close to boss (dist = 12)
    p_pos.x = b_pos.x - 6
    p_pos.y = b_pos.y - 6
    print(f"Moved player to ({p_pos.x}, {p_pos.y}), new distance: {abs(p_pos.x - b_pos.x) + abs(p_pos.y - b_pos.y)}")

    # Run BossSystem to trigger bark
    boss_sys = next(s for s in world._systems if s.__class__.__name__ == 'BossSystem')
    boss_sys.process()
    world.event_manager.process_events()

    if any("I smell someone" in m for m in get_msgs()):
        print("[OK] Entry bark triggered on approach.")
        print(f"Bark timer: {b_comp.bark_display_timer} (expected ~4.0)")
    else:
        print("[FAIL] Entry bark NOT triggered on approach.")
        return False

    # 3. Simulate Encounter (dist <= 5)
    p_pos.x = b_pos.x - 2
    p_pos.y = b_pos.y - 2
    print(f"Moved player closer, new distance: {abs(p_pos.x - b_pos.x) + abs(p_pos.y - b_pos.y)}")
    
    # Wait for bark cooldown (if any) - BARK_COOLDOWN is 2.0 in systems.py
    # For testing, we might need to bypass or wait. Let's just force last_bark_time back.
    if hasattr(b_comp, 'last_bark_time'):
        b_comp.last_bark_time -= 5.0

    boss_sys.process()
    world.event_manager.process_events()

    if any("Ah... Fresh Meat!" in m for m in get_msgs()):
        print("[OK] Entrance bark triggered (Encounter).")
        print(f"Bark timer: {b_comp.bark_display_timer} (expected ~5.0)")
    else:
        print("[FAIL] Entrance bark NOT triggered.")
        return False

    # 4. Simulate Death and Bark Duration
    print("Simulating boss death...")
    from dungeon.events import BossBarkEvent
    world.event_manager.push(BossBarkEvent(boss_ent, "DEATH", "Meat... is... done..."))
    world.event_manager.process_events() # Handle BossBarkEvent -> Pushes MessageEvent
    world.event_manager.process_events() # Handle MessageEvent -> Adds to log
    
    # Need to run BossSystem to handle the _handle_boss_bark call
    # Actually BossSystem handles it via event listener.
    
    if any("Meat... is... done..." in m for m in get_msgs()):
        print("[OK] Death bark found in log.")
        print(f"Bark timer: {b_comp.bark_display_timer} (expected ~8.0)")
        if b_comp.bark_display_timer >= 7.0:
            print("[OK] Death bark duration is correctly longer.")
        else:
            print(f"[FAIL] Death bark duration too short: {b_comp.bark_display_timer}")
            return False
    else:
        print("[FAIL] Death bark NOT found in log.")
        return False

    return True

if __name__ == "__main__":
    if verify_enhanced_dialogues():
        print("\n[SUCCESS] Enhanced Boss Dialogue verification passed!")
    else:
        print("\n[FAILURE] Enhanced Boss Dialogue verification failed.")
        sys.exit(1)
