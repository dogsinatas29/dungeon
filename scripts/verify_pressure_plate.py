#!/usr/bin/env python3
"""
Pressure Plate Trap Verification Script
Tests floor-based pressure plate traps
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.components import (
    PositionComponent, PressurePlateComponent, TrapComponent,
    RenderComponent, InventoryComponent, MapComponent, StatsComponent
)
from dungeon.systems import MovementSystem, TrapSystem
from dungeon.events import TrapTriggerEvent

def test_pressure_plate():
    print("=== Pressure Plate Trap Test ===")
    engine = Engine()
    world = engine.world
    
    # Setup map
    map_ent = world.get_entities_with_components({MapComponent})[0]
    map_comp = map_ent.get_component(MapComponent)
    for y in range(10, 15):
        for x in range(10, 15):
            map_comp.tiles[y][x] = '.'
    
    # Player
    player = world.get_player_entity()
    player.add_component(PositionComponent(x=11, y=12), overwrite=True)
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0), overwrite=True)
    
    # Trap
    trap = world.create_entity()
    trap.add_component(TrapComponent(trap_type="ARROW", damage_min=20, damage_max=30, source_x=13, source_y=12))
    
    # Pressure plate at (12, 12)
    plate = world.create_entity()
    plate.add_component(PositionComponent(x=12, y=12))
    plate.add_component(PressurePlateComponent(linked_trap_id=trap.entity_id, is_triggered=False))
    plate.add_component(RenderComponent(char='.', color='white'))  # Hidden initially
    
    plate_comp = plate.get_component(PressurePlateComponent)
    
    print(f"Player at: (11, 12)")
    print(f"Pressure plate at: (12, 12)")
    print(f"Plate triggered: {plate_comp.is_triggered}")
    
    # Move player onto pressure plate
    print("\n[Action] Moving player to (12, 12)...")
    from dungeon.components import DesiredPositionComponent
    player.add_component(DesiredPositionComponent(x=12, y=12))
    
    # Process movement
    move_sys = world.get_system(MovementSystem)
    move_sys.process()
    
    # Check if triggered
    print(f"\n[Result] Plate triggered: {plate_comp.is_triggered}")
    
    if plate_comp.is_triggered:
        print("✅ PASS: Pressure plate triggered")
        
        # Check visual update
        render_comp = plate.get_component(RenderComponent)
        if render_comp and render_comp.char == '▼':
            print("✅ PASS: Visual updated to ▼")
        else:
            print(f"❌ FAIL: Visual not updated (char: {render_comp.char if render_comp else 'None'})")
        
        # Check for trap trigger event
        trap_events = [e for e in world.event_manager.event_queue if isinstance(e, TrapTriggerEvent)]
        if trap_events:
            print("✅ PASS: TrapTriggerEvent created")
        else:
            print("❌ FAIL: No TrapTriggerEvent")
    else:
        print("❌ FAIL: Pressure plate not triggered")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_pressure_plate()
