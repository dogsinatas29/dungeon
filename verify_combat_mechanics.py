import os
import sys
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import StatsComponent, PositionComponent, InventoryComponent, MonsterComponent
from dungeon.systems import CombatSystem, MessageEvent, SkillUseEvent
from dungeon.data_manager import ItemDefinition, MonsterDefinition
from dungeon.modifiers import ModifierManager
import random

# Mock Random for deterministic results
random.uniform = MagicMock(return_value=0.0) # No bonus
random.random = MagicMock(return_value=0.5) # No crit (chance 0.1)

def verify_combat_mechanics():
    print("=== Verifying Advanced Combat & Affix System ===")
    
    engine = Engine(player_name="Tester")
    engine.world.event_manager.push = MagicMock() # 메시지 캡처용

    # [Test 1] Affix System (Item & Monster)
    print("[Test 1] Affix System Generation...", end=" ")
    modifier = ModifierManager()
    
    # 1-1 Item Prefix (Sharp: Att+3)
    # Name, Type, Desc, Symbol, Color, ReqLv, Att, Def, HP, MP
    base_item = ItemDefinition("sword", "WEAPON", "Desc", "|", "white", 1, 10, 0, 0, 0)
    sharp_item = modifier.apply_item_prefix(base_item, "Sharp")
    
    if sharp_item.attack == 13 and "날카로운" in sharp_item.name:
        pass
    else:
        print(f"FAIL (Item Prefix) - Expected Att 13, got {sharp_item.attack}")
        return

    # 1-2 Monster Prefix (Hard: Def+2, HP+5)
    base_mon = MonsterDefinition("orc", "오크", "o", "green", 30, 10, 2, 1, 10, 0, 1, "CHASE", 1)
    hard_mon = modifier.apply_monster_prefix(base_mon, "Hard")
    
    if hard_mon.defense == 4 and hard_mon.hp == 35 and "단단한" in hard_mon.name:
        print("PASS")
    else:
        print(f"FAIL (Monster Prefix) - Expected Def 4 HP 35, got Def {hard_mon.defense} HP {hard_mon.hp}")
        return

    # [Test 2] Splash Damage
    print("[Test 2] Splash Damage...", end=" ")
    combat = CombatSystem(engine.world)
    combat.event_manager.push = MagicMock() # 캡처

    attacker = engine.world.create_entity()
    engine.world.add_component(attacker.entity_id, StatsComponent(attack=20, defense=0, current_hp=100, max_hp=100, element="SPLASH"))
    engine.world.add_component(attacker.entity_id, PositionComponent(x=10, y=10))

    target = engine.world.create_entity()
    t_stats = StatsComponent(attack=0, defense=0, current_hp=100, max_hp=100)
    engine.world.add_component(target.entity_id, t_stats)
    engine.world.add_component(target.entity_id, PositionComponent(x=11, y=10)) # Right

    splash_target = engine.world.create_entity()
    s_stats = StatsComponent(attack=0, defense=0, current_hp=100, max_hp=100)
    engine.world.add_component(splash_target.entity_id, s_stats)
    engine.world.add_component(splash_target.entity_id, PositionComponent(x=11, y=11)) # Diagonal (Splash range)
    
    # Attack main target
    combat._apply_damage(attacker, target, distance=1, allow_splash=True)
    
    # Check main target damage (Should be 20)
    # Check splash target damage (Should be 10 = 50%)
    if t_stats.current_hp == 80 and s_stats.current_hp == 90:
         print("PASS")
    else:
         print(f"FAIL - MainHP: {t_stats.current_hp} (Exp 80), SplashHP: {s_stats.current_hp} (Exp 90)")

    # [Test 3] Piercing Attack (Projectile)
    print("[Test 3] Piercing Projectile...", end=" ")
    
    # Setup Attacker with PIERCING skill
    p_attacker = engine.world.create_entity()
    engine.world.add_component(p_attacker.entity_id, StatsComponent(attack=10, defense=0, current_hp=100, max_hp=100)) # Base Att 10
    engine.world.add_component(p_attacker.entity_id, PositionComponent(x=20, y=20))
    # Mock Engine reference for render calls inside projectile
    engine.world.engine = MagicMock()
    engine.world.engine._render = MagicMock()
    
    # Targets in line
    t1 = engine.world.create_entity()
    t1_stats = StatsComponent(max_hp=50, current_hp=50, attack=0, defense=0)
    engine.world.add_component(t1.entity_id, t1_stats)
    engine.world.add_component(t1.entity_id, PositionComponent(x=21, y=20))
    
    t2 = engine.world.create_entity()
    t2_stats = StatsComponent(max_hp=50, current_hp=50, attack=0, defense=0)
    engine.world.add_component(t2.entity_id, t2_stats)
    engine.world.add_component(t2.entity_id, PositionComponent(x=22, y=20))
    
    # [Fix] Remove existing random map from Engine init to avoid conflict
    from dungeon.components import MapComponent
    existing_maps = engine.world.get_entities_with_components({MapComponent})
    for m in existing_maps:
        engine.world.delete_entity(m.entity_id)

    # Create Dummy Map for validation
    map_ent = engine.world.create_entity()
    dummy_tiles = [['.' for _ in range(30)] for _ in range(30)]
    engine.world.add_component(map_ent.entity_id, MapComponent(width=30, height=30, tiles=dummy_tiles))

    # Skill with PIERCING flag
    skill_mock = type('obj', (object,), {
        'name': 'Piercing Shot', 'range': 5, 'flags': {'PIERCING'}, 'damage': 10, 'element': '무', 'on_hit_effect': '없음'
    })
    
    # Fire projectile (dx=1, dy=0)
    combat._handle_projectile_skill(p_attacker, skill_mock, 1, 0)
    
    # Both should be hit. 
    # Damage is 10 (base 10, factor 1.0)
    if t1_stats.current_hp == 40 and t2_stats.current_hp == 40:
        print("PASS")
    else:
        print(f"FAIL - T1 HP: {t1_stats.current_hp} (Exp 40), T2 HP: {t2_stats.current_hp} (Exp 40)")

    print("=== Verification Complete ===\n")

if __name__ == "__main__":
    verify_combat_mechanics()
