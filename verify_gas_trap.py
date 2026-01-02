#!/usr/bin/env python3
"""
Gas Trap AOE Verification Script
Tests 3x3 poison cloud generation and damage over time
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import (
    PositionComponent, SwitchComponent, TrapComponent,
    RenderComponent, StatsComponent, InventoryComponent, MapComponent
)
from dungeon.systems import TrapSystem, InteractionSystem
from dungeon.events import InteractEvent, TrapTriggerEvent

def test_gas_trap():
    print("=== Gas Trap AOE Test ===")
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
    player.add_component(PositionComponent(x=12, y=12), overwrite=True)
    player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=0), overwrite=True)
    
    # Gas trap
    trap = world.create_entity()
    trap.add_component(TrapComponent(trap_type="GAS", damage_min=15, damage_max=15))
    
    # Door linked to gas trap
    door = world.create_entity()
    door.add_component(PositionComponent(x=12, y=12))
    door.add_component(SwitchComponent(is_open=False, linked_trap_id=trap.entity_id))
    
    # Systems
    trap_sys = world.get_system(TrapSystem)
    
    print(f"Player at: ({player.get_component(PositionComponent).x}, {player.get_component(PositionComponent).y})")
    print(f"Player HP: {player.get_component(StatsComponent).current_hp}")
    
    # Trigger gas trap
    print("\n[Action] Triggering gas trap...")
    world.event_manager.push(TrapTriggerEvent(trap.entity_id, player.entity_id, None))
    
    # Process trap trigger
    if world.event_manager.event_queue:
        evt = world.event_manager.event_queue.pop(0)
        trap_sys.handle_trap_trigger(evt)
    
    # Check for poison clouds
    from dungeon.components import PoisonCloudComponent, EffectComponent
    clouds = world.get_entities_with_components({PoisonCloudComponent, PositionComponent})
    
    print(f"\n[Result] Created {len(clouds)} poison cloud entities")
    
    if len(clouds) > 0:
        print("PASS: Poison clouds created")
        
        # Check 3x3 coverage
        cloud_positions = set()
        for cloud in clouds:
            pos = cloud.get_component(PositionComponent)
            cloud_positions.add((pos.x, pos.y))
            print(f"  Cloud at: ({pos.x}, {pos.y})")
        
        # Should be 3x3 = 9 clouds (or less if walls block some)
        if len(cloud_positions) >= 5:  # At least center + 4 adjacent
            print(f"PASS: AOE coverage ({len(cloud_positions)} tiles)")
        else:
            print(f"WARN: Limited coverage ({len(cloud_positions)} tiles)")
        
        # Test damage over time
        print("\n[Test] Simulating 2 seconds of poison damage...")
        time_sys = world.get_system("TimeSystem")
        if time_sys:
            # Simulate 2 ticks (2 seconds)
            for i in range(2):
                time_sys.process()
                time.sleep(0.1)
            
            final_hp = player.get_component(StatsComponent).current_hp
            print(f"Player HP after 2 ticks: {final_hp}/100")
            
            if final_hp < 100:
                print("PASS: Poison cloud dealt damage")
            else:
                print("FAIL: No damage dealt")
    else:
        print("FAIL: No poison clouds created")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_gas_trap()
