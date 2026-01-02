
import sys
import os
import time

# Ensure dungeon package is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World, Entity
from dungeon.components import (
    PositionComponent, SwitchComponent, TrapComponent, 
    RenderComponent, StatsComponent, InventoryComponent, MapComponent
)
from dungeon.systems import (
    MovementSystem, InteractionSystem, TrapSystem, CombatSystem, InputSystem
)
from dungeon.events import (
    InteractEvent, TrapTriggerEvent, MessageEvent, SkillUseEvent
)

def test_traps():
    print("=== Test 1: Door Interaction ===")
    engine = Engine()
    world = engine.world
    
    # Force tiles to be floor to avoid wall collision
    map_ent = world.get_entities_with_components({MapComponent})[0]
    map_comp = map_ent.get_component(MapComponent)
    map_comp.tiles[10][11] = '.' # Door pos
    map_comp.tiles[10][10] = '.' # Player pos
    
    # 1. Player
    # 1. Player (Use existing one from Engine init)
    player = world.get_player_entity()
    print(f"DEBUG: Player ID is {player.entity_id}")
    player.add_component(PositionComponent(x=10, y=10), overwrite=True)
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0), overwrite=True)
    # player.add_component(InventoryComponent()) # Should already exist
    
    # 2. Door (Closed) at (11, 10)
    door = world.create_entity()
    door.add_component(PositionComponent(x=11, y=10))
    door.add_component(SwitchComponent(is_open=False, locked=False))
    door.add_component(RenderComponent('+', "brown"))
    
    # 3. Systems
    mov_sys = MovementSystem(world)
    int_sys = InteractionSystem(world)
    input_sys = InputSystem(world)
    combat_sys = CombatSystem(world)
    world.add_system(mov_sys)
    world.add_system(int_sys)
    world.add_system(input_sys)
    world.add_system(combat_sys)
    
    # Init listeners
    world.event_manager.register(InteractEvent, int_sys)
    
    # 4. Try Move into Door
    print("[Action] Moving Right (into Door)...")
    # input_sys adds DesiredPositionComponent
    input_sys.handle_input('d') 
    # mov_sys processes DesiredPositionComponent and generates events
    mov_sys.process()
    
    # Check Events
    interact_event = None
    for evt in world.event_manager.event_queue:
        if isinstance(evt, InteractEvent):
            interact_event = evt
            break
            
    if interact_event:
        print(f"PASS: InteractEvent generated for target {interact_event.target}")
        # Manual Process for test (systems loop usually handles this)
        int_sys.handle_interact_event(interact_event)
        
        sw = door.get_component(SwitchComponent)
        if sw.is_open:
            print("PASS: Door is now OPEN")
        else:
            print("FAIL: Door remained CLOSED")
    else:
        print("FAIL: No InteractEvent generated")

    print("\n=== Test 2: Trap Triggering ===")
    # 5. Trap Entity
    trap = world.create_entity()
    trap.add_component(TrapComponent(trap_type="ARROW", damage_min=10, damage_max=20))
    
    # 6. Door linked to Trap
    trapped_door = world.create_entity()
    trapped_door.add_component(PositionComponent(x=12, y=10))
    trapped_door.add_component(SwitchComponent(is_open=False, linked_trap_id=trap.entity_id))
    
    # 7. Trap System
    trap_sys = TrapSystem(world)
    world.add_system(trap_sys)
    world.event_manager.register(TrapTriggerEvent, trap_sys)
    
    # 8. Open Trapped Door
    print(f"[Action] Opening Trapped Door (ID: {trapped_door.entity_id}) linked to Trap (ID: {trap.entity_id})...")
    
    # Clear queue
    world.event_manager.event_queue.clear()
    
    # Manually push interact event (simulating bump)
    world.event_manager.push(InteractEvent(who=player.entity_id, target=trapped_door.entity_id, action="OPEN"))
    
    # Process Interact (opens door -> pushes TrapTrigger)
    # Process TrapTrigger (damages player -> pushes Message)
    
    # We need to process events in order
    # 1. InteractEvent
    if world.event_manager.event_queue:
        evt1 = world.event_manager.event_queue.pop(0)
        int_sys.handle_interact_event(evt1)
    
    # Check TrapTrigger in queue
    trap_evt = None
    for evt in world.event_manager.event_queue:
        if isinstance(evt, TrapTriggerEvent):
            trap_evt = evt
            break
            
    if trap_evt:
        print(f"PASS: TrapTriggerEvent generated for trap {trap_evt.trap_entity_id}")
        trap_sys.handle_trap_trigger(trap_evt)
        
        # Check Message
        msgs = [e.text for e in world.event_manager.event_queue if isinstance(e, MessageEvent)]
        print(f"[Messages]: {msgs}")
        if any("화살" in m for m in msgs):
            print("PASS: 'Arrow' message found")
        else:
            print("FAIL: Trap message missing")
            
    else:
        print("FAIL: TrapTriggerEvent not generated")

if __name__ == "__main__":
    test_traps()
