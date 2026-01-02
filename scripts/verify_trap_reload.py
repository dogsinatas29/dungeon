#!/usr/bin/env python3
"""
Trap Reload System Verification Script
Tests automatic trap reloading after disarm
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.components import (
    PositionComponent, TrapComponent, SwitchComponent,
    RenderComponent, InventoryComponent
)
from dungeon.systems import TrapSystem

def test_trap_reload():
    print("=== Trap Reload System Test ===")
    engine = Engine()
    world = engine.world
    
    # Create trap with short reload time for testing
    trap = world.create_entity()
    trap.add_component(PositionComponent(x=12, y=12))
    trap.add_component(TrapComponent(
        trap_type="ARROW",
        damage_min=20,
        damage_max=30,
        reload_turns=5,  # Short reload for testing
        is_disarmed=True  # Start disarmed
    ))
    
    # Player nearby
    player = world.get_player_entity()
    player.add_component(PositionComponent(x=12, y=12), overwrite=True)
    
    trap_comp = trap.get_component(TrapComponent)
    trap_sys = world.get_system(TrapSystem)
    
    print(f"Initial state:")
    print(f"  is_disarmed: {trap_comp.is_disarmed}")
    print(f"  turns_since_trigger: {trap_comp.turns_since_trigger}")
    print(f"  reload_turns: {trap_comp.reload_turns}")
    
    # Simulate turns
    print(f"\nSimulating {trap_comp.reload_turns + 1} turns...")
    for turn in range(trap_comp.reload_turns + 1):
        trap_sys.process()
        print(f"  Turn {turn + 1}: turns_since_trigger={trap_comp.turns_since_trigger}, is_disarmed={trap_comp.is_disarmed}")
        
        if not trap_comp.is_disarmed:
            print(f"\n✅ PASS: Trap reloaded after {turn + 1} turns!")
            break
    else:
        print(f"\n❌ FAIL: Trap did not reload after {trap_comp.reload_turns} turns")
        return
    
    # Check final state
    if trap_comp.turns_since_trigger == 0:
        print("✅ PASS: Counter reset to 0")
    else:
        print(f"❌ FAIL: Counter not reset (value: {trap_comp.turns_since_trigger})")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_trap_reload()
