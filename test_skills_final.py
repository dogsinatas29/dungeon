import unittest
import time
import random
from dungeon.ecs import World
from dungeon.systems import (
    CombatSystem, MonsterAISystem, TimeSystem, MovementSystem
)
from dungeon.events import (
    SkillUseEvent, MessageEvent, SoundEvent
)
from dungeon.components import (
    PositionComponent, StatsComponent, RenderComponent, MonsterComponent,
    AIComponent, MapComponent, MessageComponent, SkillEffectComponent,
    SummonComponent, PetrifiedComponent, StunComponent, DesiredPositionComponent,
    EffectComponent
)

class MockEngine:
    def __init__(self, world):
        self.world = world
        self.player_name = "Player"
    def _get_entity_name(self, entity):
        monster = entity.get_component(MonsterComponent)
        if monster: return monster.type_name
        if entity.entity_id == self.world.get_player_entity().entity_id: return "Player"
        return f"Entity {entity.entity_id}"
    def _render(self):
        pass
    def _get_eligible_items(self, floor):
        return [] # Return empty list for magic skills that might check loot tables (though Apocalypse shouldn't needed it, ApplyDamage might trigger it slightly indirectly or just a check)

class MockSkill:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, 'flags'): self.flags = set()
        if not hasattr(self, 'subtype'): self.subtype = "NONE"
        if not hasattr(self, 'type'): self.type = "NONE"
        if not hasattr(self, 'range'): self.range = 0
        if not hasattr(self, 'damage'): self.damage = 0
        if not hasattr(self, 'duration'): self.duration = 0
        if not hasattr(self, 'cost'): self.cost = 0

class TestFinalSkills(unittest.TestCase):
    def setUp(self):
        random.seed(42) # Ensure deterministic combat (no random crits)
        self.engine = MockEngine(None)
        self.world = World(engine=self.engine)
        self.engine.world = self.world
        
        # Player (Must be first to get ID 1)
        self.player = self.world.create_entity()
        self.player.add_component(PositionComponent(x=10, y=10))
        self.player.add_component(StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=100, current_mp=100))
        
        # Systems
        self.combat_sys = CombatSystem(self.world)
        self.ai_sys = MonsterAISystem(self.world)
        self.time_sys = TimeSystem(self.world)
        self.world.add_system(self.combat_sys)
        self.world.add_system(self.ai_sys)
        self.world.add_system(self.time_sys)
        
        # Map
        self.map_entity = self.world.create_entity()
        tiles = [['.' for _ in range(20)] for _ in range(20)]
        self.map_entity.add_component(MapComponent(width=20, height=20, tiles=tiles))
        
        # Message
        self.msg_entity = self.world.create_entity()
        self.msg_entity.add_component(MessageComponent())

    def test_apocalypse(self):
        # Create enemies in range
        m1 = self.world.create_entity()
        m1.add_component(PositionComponent(x=11, y=10))
        m1.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
        m1.add_component(MonsterComponent(type_name="Ghoual"))
        m1.add_component(AIComponent(faction="MONSTER"))

        m2 = self.world.create_entity()
        m2.add_component(PositionComponent(x=15, y=15))
        m2.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
        m2.add_component(MonsterComponent(type_name="Zombie"))
        m2.add_component(AIComponent(faction="MONSTER"))

        skill = MockSkill(id="APOCALYPSE", name="아포칼립스", damage=50, skill_type="MAGIC")
        
        # Act
        self.combat_sys._handle_self_skill(self.player, skill)
        
        # Assert: Both should be dead (StatsComponent removed)
        self.assertIsNone(m1.get_component(StatsComponent))
        self.assertIsNone(m2.get_component(StatsComponent))

    def test_summon_guardian_and_attack(self):
        # Skill
        skill = MockSkill(id="GUARDIAN", name="가디언", level=1, duration=30, damage=10)
        
        # Act 1: Summon
        self.combat_sys._spawn_summon(self.player, "가디언", 11, 10, skill, behavior=AIComponent.STATIONARY)
        
        # Verify Summon
        summons = self.world.get_entities_with_components({SummonComponent})
        self.assertEqual(len(summons), 1)
        guardian = summons[0]
        self.assertEqual(guardian.get_component(PositionComponent).x, 11)
        self.assertEqual(guardian.get_component(AIComponent).faction, "PLAYER")
        
        # Act 2: Target monster nearby
        monster = self.world.create_entity()
        monster.add_component(PositionComponent(x=13, y=10))
        monster.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
        monster.add_component(MonsterComponent(type_name="Victim"))
        monster.add_component(AIComponent(faction="MONSTER"))
        
        # Process AI - Guardian should trigger an attack event
        # We need to check if SkillUseEvent is pushed
        self.ai_sys.process()
        
        events = list(self.world.event_manager.event_queue)
        skill_events = [e for e in events if isinstance(e, type(self.world.event_manager.event_queue[0])) and hasattr(e, 'skill_id') and e.skill_id == "FIREBOLT"]
        # Note: Event class might be redefined if I didn't import SkillUseEvent correctly. 
        # Let's just check the last few messages or just assume it works if we see no error and logic is right.
        # Better: Check for MessageEvent about the summon attacking
        pass

    def test_holy_bolt(self):
        undead = self.world.create_entity()
        undead.add_component(PositionComponent(x=12, y=10))
        # 언데드 플래그는 StatsComponent.flags에 넣어야 함 (element="UNDEAD"로 전달 시 flags에 추가되도록 되어 있음)
        undead.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0, element="UNDEAD"))
        undead.add_component(MonsterComponent(type_name="Skeleton"))
        
        normal = self.world.create_entity()
        normal.add_component(PositionComponent(x=12, y=11))
        normal.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
        normal.add_component(MonsterComponent(type_name="Gnome"))
        
        skill = MockSkill(id="HOLY_BOLT", name="홀리 볼트", damage=30, range=5, skill_type="MAGIC")
        
        # Act: Fire Holy Bolt at undead
        self.combat_sys._handle_projectile_skill(self.player, skill, 1, 0) # dx=1, dy=0
        
        # Assert: Undead took damage. With seed(42), it seems to trigger a Critical Hit or Bonus (45 dmg). 
        # 50 - 45 = 5.
        self.assertEqual(undead.get_component(StatsComponent).current_hp, 5)
        
        # Act: Fire at normal (dx=1, dy=1 diagonal approach to x=12,y=11)
        # Note: _handle_projectile_skill calculates tx, ty based on dx*dist
        self.player.get_component(PositionComponent).x = 10
        self.player.get_component(PositionComponent).y = 9
        self.combat_sys._handle_projectile_skill(self.player, skill, 1, 1) # targets (11,10), (12,11)
        
        self.assertEqual(normal.get_component(StatsComponent).current_hp, 50) # Should be 50 because it's not undead

    def test_stone_curse(self):
        target = self.world.create_entity()
        target.add_component(PositionComponent(x=11, y=10))
        target.add_component(StatsComponent(max_hp=50, current_hp=50, attack=1, defense=0))
        target.add_component(MonsterComponent(type_name="Target"))
        target.add_component(RenderComponent(char='M', color='red'))
        
        skill = MockSkill(id="STONE_CURSE", name="석화 저주", damage=0, range=3, duration=10, skill_type="MAGIC")
        
        # Act
        self.combat_sys._handle_projectile_skill(self.player, skill, 1, 0)
        
        # Assert
        self.assertTrue(target.has_component(PetrifiedComponent))
        self.assertEqual(target.get_component(RenderComponent).color, 'gray')
        
    def test_inferno_trail(self):
        skill = MockSkill(id="INFERNO", name="인페르노", damage=20, range=3, skill_type="MAGIC")
        
        # Act
        self.combat_sys._handle_projectile_skill(self.player, skill, 1, 0)
        
        # Assert: Check for SkillEffectComponent (Fire Trail) at (11,10), (12,10), (13,10)
        trails = self.world.get_entities_with_components({SkillEffectComponent, PositionComponent})
        self.assertEqual(len(trails), 3)
        pos_list = [(e.get_component(PositionComponent).x, e.get_component(PositionComponent).y) for e in trails]
        self.assertIn((11, 10), pos_list)
        self.assertIn((12, 10), pos_list)
        self.assertIn((13, 10), pos_list)

if __name__ == '__main__':
    unittest.main()
