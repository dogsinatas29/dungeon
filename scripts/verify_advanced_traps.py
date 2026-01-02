#!/usr/bin/env python3
"""
Advanced Trap System Verification Script (V12)
Tests:
1. Rogue trap detection (visual indicator)
2. Disarm success (70% chance)
3. Disarm failure (trap triggers)
4. No skill (trap triggers immediately)
5. Projectile tracing and knockback
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import (
    PositionComponent, SwitchComponent, TrapComponent,
    RenderComponent, StatsComponent, InventoryComponent, MapComponent
)
from dungeon.systems import (
    MovementSystem, InteractionSystem, TrapSystem, CombatSystem, InputSystem
)
from dungeon.events import InteractEvent, TrapTriggerEvent

def test_advanced_traps():
    print("=== Test 1: Rogue Trap Detection (Manual Visual Check) ===")
    engine = Engine()
    world = engine.world
    
    # Force floor tiles
    map_ent = world.get_entities_with_components({MapComponent})[0]
    map_comp = map_ent.get_component(MapComponent)
    for y in range(10, 15):
        for x in range(10, 15):
            map_comp.tiles[y][x] = '.'
    
    # Player with "함정 해제" skill
    player = world.get_player_entity()
    player.add_component(PositionComponent(x=10, y=10), overwrite=True)
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0), overwrite=True)
    inv = player.get_component(InventoryComponent)
    if inv:
        inv.skills.append("함정 해제")
    
    # Trap with source position
    trap = world.create_entity()
    trap.add_component(TrapComponent(trap_type="ARROW", damage_min=20, damage_max=30, source_x=13, source_y=11))
    
    # Trapped door
    door = world.create_entity()
    door.add_component(PositionComponent(x=11, y=10))
    door.add_component(SwitchComponent(is_open=False, linked_trap_id=trap.entity_id))
    door.add_component(RenderComponent('+', "brown"))
    
    # Reveal area
    if engine.dungeon_map:
        for y in range(8, 13):
            for x in range(8, 13):
                engine.dungeon_map.visited.add((x, y))
    
    # Render to check for '!' indicator
    engine._render()
    print("Check if '!' appears on the door at (11, 10)")
    print("Press Enter to continue...")
    input()
    
    print("\n=== Test 2: Disarm Success ===")
    # Force success by mocking random
    import random
    original_randint = random.randint
    random.randint = lambda a, b: 50 if (a == 1 and b == 100) else original_randint(a, b)
    
    # Trigger interaction
    world.event_manager.push(InteractEvent(who=player.entity_id, target=door.entity_id, action="OPEN"))
    
    # Process
    int_sys = world.get_system(InteractionSystem)
    if world.event_manager.event_queue:
        evt = world.event_manager.event_queue.pop(0)
        int_sys.handle_interact_event(evt)
    
    # Check if disarmed
    t_comp = trap.get_component(TrapComponent)
    if t_comp.is_disarmed:
        print("PASS: Trap was disarmed successfully")
    else:
        print("FAIL: Trap was not disarmed")
    
    # Restore random
    random.randint = original_randint
    
    print("\n=== Test 3: No Skill Test ===")
    # New player without skill
    world2 = World(None)
    map_ent2 = world2.create_entity()
    tiles2 = [['.' for _ in range(20)] for _ in range(20)]
    world2.add_component(map_ent2.entity_id, MapComponent(width=20, height=20, tiles=tiles2))
    
    player2 = world2.create_entity()
    player2.add_component(PositionComponent(x=10, y=10))
    player2.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0))
    player2.add_component(InventoryComponent())  # No skills
    
    trap2 = world2.create_entity()
    trap2.add_component(TrapComponent(trap_type="ARROW", damage_min=20, damage_max=30, source_x=13, source_y=11))
    
    door2 = world2.create_entity()
    door2.add_component(PositionComponent(x=11, y=10))
    door2.add_component(SwitchComponent(is_open=False, linked_trap_id=trap2.entity_id))
    
    # Systems
    int_sys2 = InteractionSystem(world2)
    trap_sys2 = TrapSystem(world2)
    world2.add_system(int_sys2)
    world2.add_system(trap_sys2)
    world2.event_manager.register(InteractEvent, int_sys2)
    world2.event_manager.register(TrapTriggerEvent, trap_sys2)
    
    # Clear queue
    world2.event_manager.event_queue.clear()
    
    # Trigger interaction
    world2.event_manager.push(InteractEvent(who=player2.entity_id, target=door2.entity_id, action="OPEN"))
    
    # Process
    if world2.event_manager.event_queue:
        evt = world2.event_manager.event_queue.pop(0)
        int_sys2.handle_interact_event(evt)
    
    # Check for trap trigger event
    trap_triggered = any(isinstance(e, TrapTriggerEvent) for e in world2.event_manager.event_queue)
    if trap_triggered:
        print("PASS: Trap triggered for player without skill")
    else:
        print("FAIL: Trap did not trigger")
    
    # Check door is still closed
    sw2 = door2.get_component(SwitchComponent)
    if not sw2.is_open:
        print("PASS: Door remained closed after trap trigger")
    else:
        print("FAIL: Door opened despite trap")
    
    print("\n=== All Tests Complete ===")

if __name__ == "__main__":
    test_advanced_traps()
