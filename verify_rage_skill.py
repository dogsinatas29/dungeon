#!/usr/bin/env python3
"""
RAGE Skill Verification Script
Tests Barbarian's Rage buff functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.components import (
    PositionComponent, StatsComponent, InventoryComponent,
    StatModifierComponent
)
from dungeon.events import SkillUseEvent

def test_rage_skill():
    print("=== RAGE Skill Test ===")
    engine = Engine()
    world = engine.world
    
    # Setup player
    player = world.get_player_entity()
    player.add_component(PositionComponent(x=12, y=12), overwrite=True)
    
    stats = player.get_component(StatsComponent)
    if not stats:
        stats = StatsComponent(max_hp=100, current_hp=100, max_mp=50, current_mp=50, attack=20, defense=10)
        player.add_component(stats, overwrite=True)
    
    # Add RAGE skill
    inv = player.get_component(InventoryComponent)
    if "레이지" not in inv.skills:
        inv.skills.append("레이지")
    inv.skill_levels["레이지"] = 3  # Level 3 for testing
    
    print(f"Initial Stats:")
    print(f"  Attack: {stats.attack}")
    print(f"  Defense: {stats.defense}")
    print(f"  MP: {stats.current_mp}/{stats.max_mp}")
    print(f"  Skill Level: 3")
    
    # Use RAGE skill
    print(f"\n[Action] Using RAGE skill...")
    world.event_manager.push(SkillUseEvent(
        attacker_id=player.entity_id,
        skill_name="레이지",
        dx=0,
        dy=0
    ))
    
    # Process event
    combat_sys = world.get_system("CombatSystem")
    if combat_sys and world.event_manager.event_queue:
        event = world.event_manager.event_queue.pop(0)
        combat_sys.handle_skill_use_event(event)
    
    # Check for StatModifierComponent
    stat_mod = player.get_component(StatModifierComponent)
    
    if stat_mod:
        print(f"\n✅ PASS: StatModifierComponent applied")
        print(f"  Source: {stat_mod.source}")
        print(f"  Duration: {stat_mod.duration}s")
        print(f"  Attack Multiplier: {getattr(stat_mod, 'attack_multiplier', 1.0)}x")
        print(f"  Defense Multiplier: {getattr(stat_mod, 'defense_multiplier', 1.0)}x")
        
        # Check if stats recalculated
        if hasattr(engine, '_recalculate_stats'):
            engine._recalculate_stats()
            print(f"\n  Recalculated Attack: {stats.attack}")
            print(f"  Recalculated Defense: {stats.defense}")
    else:
        print(f"\n❌ FAIL: No StatModifierComponent found")
    
    # Check MP consumption
    print(f"\n  MP After: {stats.current_mp}/{stats.max_mp}")
    if stats.current_mp < 50:
        print(f"✅ PASS: MP consumed")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_rage_skill()
