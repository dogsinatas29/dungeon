import sys
import os
import time
import random
import logging
from typing import Dict, List, Optional

# 상위 디렉토리 임포트 허용
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from . import config
# config.LANGUAGE = "en" # English mode for verifying logs

from .engine import Engine, GameState
# ... imports ...

# ... (omitted code) ...


from .components import PositionComponent, StatsComponent, MapComponent, MonsterComponent, InventoryComponent, LevelComponent, LootComponent, PlayerComponent
from .data_manager import ItemDefinition
from .constants import ELEMENT_NONE

class HeadlessUI:
    """UI 메서드를 무시하거나 로그로 남기는 가짜 UI 클래스"""
    def __init__(self):
        self.blood_overlay_timer = 0
    def _clear_screen(self): pass
    def show_main_menu(self): return 0
    def get_player_name(self): return "Tester"
    def show_class_selection(self, class_defs): return "WARRIOR"
    def show_save_list(self, files): return "LOAD", ""
    def show_confirmation_dialog(self, msg): return True
    def draw_text(self, x, y, text, color="white"): pass
    def render_all(self, engine): pass
    def trigger_shake(self, intensity=2): pass
    def on_message(self, msg, color="white"): pass
    def show_center_dialogue(self, message, color='red'):
        print(f"  [BOSS SKILL ALERT] {message}")

class MockRenderer:
    def __init__(self, *args, **kwargs):
        self.width = 120
        self.height = 30
    def clear_buffer(self): pass
    def draw_char(self, *args, **kwargs): pass
    def draw_text(self, *args, **kwargs): pass
    def draw_box(self, *args, **kwargs): pass
    def render(self): pass

class HeadlessEngine(Engine):
    """터미널 및 입출력 의존성이 없는 시뮬레이션용 엔진"""
    def __init__(self, player_name="Tester", game_data=None):
        # Renderer 생성을 피하기 위해 Renderer 클래스를 Mock으로 패치
        from . import renderer
        original_renderer = renderer.Renderer
        renderer.Renderer = MockRenderer
        
        super().__init__(player_name, game_data)
        
        # 원복 (다른 인스턴스에 영향을 주지 않도록)
        renderer.Renderer = original_renderer
        
        self.ui = HeadlessUI()
        self.agent_actions = []
        self.max_turns = 2000 # 넉넉하게
        self.current_turns = 0
        self.is_headless = True
        self.game_result = "NONE"

    def run(self, ui=None) -> str:
        """UI 없이 실행되는 메인 루프 오버라이드"""
        self.ui = ui or HeadlessUI()
        self.is_running = True
        self.fake_time = 1000.0
        self.metrics = {
            "start_time": time.time(),
            "turns": 0,
            "combat_turns": 0,
            "journey_hp_loss": 0,
            "journey_mp_loss": 0,
            "potions_used": 0,
            "skills_used": 0,
            "boss_hp_at_end": 0,
            "boss_patterns": [],
            "outcome": "NONE",
            "boss_id": None,
            "boss_lv": 0
        }
        
        # time.time() 패치 (시스템의 action_delay 우회용)
        import time as true_time
        from unittest.mock import patch
        
        def mock_time():
            return self.fake_time

        try:
            with patch('time.time', side_effect=mock_time):
                # 0. 여정 시뮬레이션
                player = self.world.get_player_entity()
                if player:
                    stats = player.get_component(StatsComponent)
                    self.metrics["journey_hp_loss"] = int(stats.max_hp * random.uniform(0.1, 0.2))
                    self.metrics["journey_mp_loss"] = int(stats.max_mp * random.uniform(0.1, 0.3))
                    stats.current_hp = max(1, stats.current_hp - self.metrics["journey_hp_loss"])
                    stats.current_mp = max(0, stats.current_mp - self.metrics["journey_mp_loss"])

                combat_started = False
                boss_hp = 0 # Initialize here to prevent UnboundLocalError
                
                while self.is_running and self.current_turns < self.max_turns:
                    self.current_turns += 1
                    self.fake_time += 1.0 # 턴마다 1초씩 진행 가정
                    self.metrics["turns"] = self.current_turns
                    
                    # 1. 에이전트 입력 시뮬레이션
                    if self.state == GameState.PLAYING:
                        if self.current_turns == 1 and self.dungeon_map.map_type == "BOSS":
                            self._teleport_to_boss()
                            self._scale_boss_level()

                        action = self._get_smart_agent_action()
                        if action:
                            self.input_system.handle_input(action)
                    
                    # 2. 로직 처리
                    if self.state == GameState.PLAYING:
                        self.world.event_manager.process_events()
                        for system in self.world._systems:
                            if system: system.process()

                        # 이벤트 스니핑 (패턴 발동 확인) - process_events 전/후에 큐가 비워짐
                        from .events import MessageEvent, SoundEvent
                        
                        # [Debug] Monitor HP
                        p = self.world.get_player_entity()
                        if p:
                            s = p.get_component(StatsComponent)
                            # sys.stdout.write(f"Turn {self.current_turns} HP: {s.current_hp}/{s.max_hp} MP: {s.current_mp}\n")
                            if s.current_hp <= 0:
                                print(f"DEBUG: Player DIED at turn {self.current_turns}")

                        for event in list(self.world.event_manager.event_queue):
                            if isinstance(event, MessageEvent):
                                if "[" in event.text and "]" in event.text:
                                    self.metrics["boss_patterns"].append(event.text)
                            elif isinstance(event, SoundEvent):
                                if "BOSS" in event.sound_type:
                                    self.metrics["boss_patterns"].append(f"Sound: {event.sound_type} - {event.message}")

                        self.world.event_manager.process_events()
                        self._bypass_obstacles()

                    # 플레이어 사망/생존 체크
                    player = self.world.get_player_entity()
                    if not player or not player.get_component(StatsComponent).is_alive:
                        self.is_running = False
                        self.game_result = "DEATH"
                        break
                    
                    # 보스 상태 체크 및 교전 시작 인식
                    boss_alive = False
                    boss_hp = 0
                    for m_ent in self.world.get_entities_with_components({MonsterComponent}):
                        m = m_ent.get_component(MonsterComponent)
                        s = m_ent.get_component(StatsComponent)
                        if s and ("BOSS" in s.flags or m.monster_id in ["BUTCHER", "LEORIC", "LICH_KING", "DIABLO"]):
                            if s.is_alive:
                                boss_alive = True
                                boss_hp = s.current_hp
                                self.metrics["boss_id"] = m.monster_id
                                # 플레이어와의 거리가 가까우면 교전 중으로 간주
                                p_pos = player.get_component(PositionComponent)
                                m_pos = m_ent.get_component(PositionComponent)
                                dist = abs(p_pos.x - m_pos.x) + abs(p_pos.y - m_pos.y)
                                if dist < 5:
                                    combat_started = True
                                break
                    
                    if combat_started:
                        self.metrics["combat_turns"] += 1

                    if not boss_alive and self.dungeon_map.map_type == "BOSS":
                        self.is_running = False
                        self.game_result = "WIN"
                        break

                if self.game_result == "NONE":
                    self.game_result = "TIMEOUT"
            
            self.metrics["outcome"] = self.game_result
            self.metrics["boss_hp_at_end"] = boss_hp
            return self.game_result
        except Exception as e:
            print(f"  [Error] {e}")
            import traceback
            traceback.print_exc()
            return "ERROR"

    def _scale_boss_level(self):
        """보스 레벨을 플레이어 레벨 + 3으로 보정"""
        player = self.world.get_player_entity()
        p_lvl = player.get_component(LevelComponent).level
        
        for m_ent in self.world.get_entities_with_components({MonsterComponent}):
            m = m_ent.get_component(MonsterComponent)
            s = m_ent.get_component(StatsComponent)
            if s and ("BOSS" in s.flags or m.monster_id in ["BUTCHER", "LEORIC", "LICH_KING", "DIABLO"]):
                # 보스 스탯 강화 (레벨차에 따른 보정 시뮬레이션)
                target_lv = p_lvl + 3
                self.metrics["boss_lv"] = target_lv
                # 레벨 1당 약 3~5% 스탯 상승 가정
                scale = 1.0 + (target_lv * 0.05) 
                # 원본 definitions가 아닌 현재 인스턴스 스탯을 조정
                s.max_hp = int(s.max_hp * scale)
                s.current_hp = s.max_hp
                s.attack = int(s.attack * scale)
                s.defense = int(s.defense * scale)
                # print(f"  [Sim] Scaled Boss {m.monster_id} to Lv {target_lv}")

    def _teleport_to_boss(self):
        """플레이어를 보스 근처로 강제 이동"""
        player = self.world.get_player_entity()
        if not player: return
        p_pos = player.get_component(PositionComponent)

        monsters = self.world.get_entities_with_components({MonsterComponent, PositionComponent, StatsComponent})
        for m in monsters:
            m_comp = m.get_component(MonsterComponent)
            m_stats = m.get_component(StatsComponent)
            if "BOSS" in m_stats.flags or m_comp.monster_id in ["BUTCHER", "LEORIC", "LICH_KING", "DIABLO"]:
                m_pos = m.get_component(PositionComponent)
                # 보스 주변 빈 공간 찾기
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nx, ny = m_pos.x + dx, m_pos.y + dy
                    if not self.dungeon_map.is_wall(nx, ny):
                        p_pos.x, p_pos.y = nx, ny
                        return
                # 못 찾으면 걍 옆에
                p_pos.x, p_pos.y = m_pos.x + 1, m_pos.y
                break

    def _bypass_obstacles(self):
        """잠긴 문 등을 강제로 개방"""
        from .components import DoorComponent, SwitchComponent, BlockMapComponent
        player = self.world.get_player_entity()
        if not player: return
        p_pos = player.get_component(PositionComponent)

        # 맵상의 모든 문 개방 (전역 개방)
        interactables = self.world.get_entities_with_components({PositionComponent})
        for ent in interactables:
            door = ent.get_component(DoorComponent)
            if door:
                door.is_open = True
                door.is_locked = False
            sw = ent.get_component(SwitchComponent)
            if sw:
                sw.is_open = True
                sw.locked = False
            # BlockMapComponent가 있으면 해제 (시뮬레이션 편의성)
            block = ent.get_component(BlockMapComponent)
            if block and (door or sw):
                block.blocks_movement = False

    def _get_smart_agent_action(self):
        """플레이어 상태를 고려한 지능형 에이전트 행동"""
        player = self.world.get_player_entity()
        if not player: return None
        stats = player.get_component(StatsComponent)
        inv = player.get_component(InventoryComponent)
        p_pos = player.get_component(PositionComponent)

        # 1. 생존 상시 체크: HP가 60% 이하일 때 포션 사용 시도 (보스전 대비)
        if stats.current_hp / stats.max_hp < 0.6:
            # Healing Potion 검색
            # [Fix] Search for any HP Potion (Tiered)
            pot_names = ["상급 체력 물약", "중급 체력 물약", "하급 체력 물약", "체력 물약"]
            target_pot = None
            healing_amount = 0
            
            for pname in pot_names:
                if pname in inv.items:
                    target_pot = inv.items[pname]
                    # Get healing amount from item def if possible, else defaults.
                    if pname == "상급 체력 물약": healing_amount = 300
                    elif pname == "중급 체력 물약": healing_amount = 100
                    elif pname == "하급 체력 물약": healing_amount = 30
                    else: healing_amount = 50 # Fallback
                    break
            
            if target_pot:
                self.metrics["potions_used"] += 1
                stats.current_hp = min(stats.max_hp, stats.current_hp + healing_amount)
                
                target_pot['qty'] -= 1
                if target_pot['qty'] <= 0:
                    # Search map items to find which key to delete? 
                    # inv.items is dict {name: data}.
                    # p_name key found loop
                    if target_pot['qty'] <= 0:
                         del inv.items[target_pot['item'].name] # Use item name from object or key? Key is safer.
                    # Wait, 'target_pot' is the value. The key is 'pname'.
                    pass
                if target_pot['qty'] <= 0: del inv.items[pname]
                
                return '.' # Consume Turn
                # If checking inside Agent, return special action code 'p'? 
                # InputSystem doesn't handle 'p' usually.
                # Actually, InputSystem handles '1'..'0'. Potion should be in quickslot?
                # Assume potion is in Inventory but not Quickslot for Agent logic unless we slot it.
                # For simplicity, let's just APPLY it here as a "cheat" or auto-use and consume turn.
                return '.' # Wait/Skip turn (consuming time)
            
            # Using English name fallback if needed
            elif "Healing Potion" in inv.items:
                 self.metrics["potions_used"] += 1
                 # ... (similar logic)
                 return '.'

        # 2. 보스 타겟팅 및 이동

        # 2. 보스 타겟팅 및 이동
        monsters = self.world.get_entities_with_components({MonsterComponent, PositionComponent, StatsComponent})
        target_pos = None
        min_dist = 9999
        
        for m_ent in monsters:
            m_stats = m_ent.get_component(StatsComponent)
            if not m_stats.is_alive: continue
            m_pos = m_ent.get_component(PositionComponent)
            m_comp = m_ent.get_component(MonsterComponent)
            dist = abs(p_pos.x - m_pos.x) + abs(p_pos.y - m_pos.y)
            
            is_boss = "BOSS" in m_stats.flags or m_comp.monster_id in ["BUTCHER", "LEORIC", "LICH_KING", "DIABLO"]
            priority_dist = dist - (1000 if is_boss else 0)
            if priority_dist < min_dist:
                min_dist = priority_dist
                target_pos = m_pos

        if target_pos:
            dx = target_pos.x - p_pos.x
            dy = target_pos.y - p_pos.y
            dist = abs(dx) + abs(dy)
            
            # 인접 시 공격
            if dist == 1:
                # 스킬 사용 확률 (Warrior/Barbarian은 근접 스킬 사용 가능성)
                # 현재 슬롯 6번('6')에 할당된 스킬 사용 시도
                if stats.current_mp > 10 and inv.skill_slots[0] and random.random() < 0.3:
                    self.metrics["skills_used"] += 1
                    return '6' 

                return 'd' if dx > 0 else ('a' if dx < 0 else ('s' if dy > 0 else 'w'))

            # 거리 좁히기
            if abs(dx) > abs(dy):
                # 원거리 직업인 경우 거리 유지 또는 스킬 사용
                can_shoot = False
                if inv.skill_slots[0]: # 스킬 보유
                     skill_name = inv.skill_slots[0]
                     # 간단한 원거리 판정 (HEAL 제외)
                     if "HEAL" not in skill_name and "MANA_SHIELD" not in skill_name:
                         can_shoot = True
                
                if can_shoot and dist <= 5 and stats.current_mp > 10 and random.random() < 0.4:
                     self.metrics["skills_used"] += 1
                     return '6'

                return 'd' if dx > 0 else 'a'
            else:
                 return 's' if dy > 0 else 'w'
        
        return random.choice(['w', 'a', 's', 'd'])

    def _render(self): pass # 렌더링 스킵
    def _get_input(self): return None

def setup_player_for_test(engine, floor, level, class_id="WARRIOR"):
    player = engine.world.get_player_entity()
    stats = player.get_component(StatsComponent)
    lvl_comp = player.get_component(LevelComponent)
    inv = player.get_component(InventoryComponent)
    
    lvl_comp.level = level
    lvl_comp.job = class_id
    
    # 클래스 기본 스탯 로드
    class_def = engine.class_defs.get(class_id)
    if class_def:
        stats.base_max_hp = class_def.hp + (level * 20)
        stats.base_max_mp = class_def.mp + (level * 10)
        stats.base_str = int(class_def.str + (level * 2.0))
        stats.base_vit = int(class_def.vit + (level * 2.0))
        stats.base_mag = int(class_def.mag + (level * 1.5))
        stats.base_dex = int(class_def.dex + (level * 2.0))
        # Update current values too for immediate use (though recalc handles it)
        stats.str = stats.base_str
        stats.vit = stats.base_vit
        stats.mag = stats.base_mag
        stats.dex = stats.base_dex
        if hasattr(class_def, 'skills'):
            # 기본 스킬 지급 (CSV 구조에 따라 다를 수 있음)
            pass
    else:
        # Fallback
        stats.base_max_hp = 200 + (level * 25)
        stats.base_max_mp = 100 + (level * 10)

    # 층수에 따른 장비 (클래스별)
    def equip(item_name, slot):
        item_def = engine.item_defs.get(item_name)
        if item_def:
            inv.equipped[slot] = item_def
        else:
            print(f"DEBUG: Failed to equip {item_name}")
    
    # 공통 스킬 (테스트용)
    test_skills = ["HEALING", "MANA_SHIELD"]
    for s in test_skills:
        if s not in inv.skills: inv.skills.append(s)
        
    # [Fix] Give Potions for Survival (Tiered & Plentiful)
    hp_pot_name = "하급 체력 물약"
    mp_pot_name = "하급 마력 물약"
    
    if level >= 20:
        hp_pot_name = "상급 체력 물약"
        mp_pot_name = "상급 마력 물약"
    elif level >= 10:
        hp_pot_name = "중급 체력 물약"
        mp_pot_name = "중급 마력 물약"
        
    if hp_pot_name in engine.item_defs:
        inv.add_item(engine.item_defs[hp_pot_name], 20)
    if mp_pot_name in engine.item_defs:
        inv.add_item(engine.item_defs[mp_pot_name], 20)

    # Class Specific Assignment
    if floor >= 20:
        if class_id == "WARRIOR":
            equip("그레이트 소드", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("체인 메일", "몸통")
            if "REPAIR" not in inv.skills: inv.skills.append("REPAIR")
            
        elif class_id == "ROGUE":
            equip("장기 워 보우", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("가죽 갑옷", "몸통")
            if "DISARM" not in inv.skills: inv.skills.append("DISARM")
            
        elif class_id == "SORCERER":
            equip("워 스태프", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("로브", "몸통")
            if "FIREBALL" not in inv.skills: inv.skills.append("FIREBALL")
            inv.skill_slots[0] = "FIREBALL" # Assign to Quickslot
            
        elif class_id == "BARBARIAN":
            equip("그레이트 액스", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("스플린트 메일", "몸통")
            if "RAGE" not in inv.skills: inv.skills.append("RAGE")
            inv.skill_slots[0] = "RAGE" # Assign to Quickslot

    # Assign Test Skills to Slots if empty
    if not inv.skill_slots[0] and inv.skills:
        inv.skill_slots[0] = inv.skills[0]
        
    # [Enhancement Simulation]
    # Simulate realistic gear progression based on floor depth.
    # Floor 25 (Butcher) -> Avg +3
    # Floor 50 (Leoric) -> Avg +6
    # Floor 75 (Lich) -> Avg +8
    # Floor 99 (Diablo) -> Avg +9 (Max safe is +9 usually)
    target_enhancement = 0
    if floor >= 25: target_enhancement = 3
    if floor >= 50: target_enhancement = 6
    if floor >= 75: target_enhancement = 8
    if floor >= 99: target_enhancement = 9
    
    import random
    
    def apply_enhancement(item, level):
        if not item: return
        item.enhancement_level = level
        item.name = f"+{level} {item.name}"
        
        # Stat Boost Logic (Simplified from shrine_methods)
        # 1. Base Attack/Defense Boost (approx 10% per level? - No, usually linear or constant)
        # Actually shrine methods boost random stats. Here we will boost MAIN stats to be reliable.
        
        # Boost Damage if Weapon
        if hasattr(item, 'attack_min'):
            item.attack_min += int(item.attack_min * (0.1 * level)) + level
            item.attack_max += int(item.attack_max * (0.1 * level)) + level
            
        # Boost Defense if Armor
        if hasattr(item, 'defense'):
            item.defense += int(item.defense * (0.1 * level)) + level
            
        # Boost Bonuses (Str/Dex/Mag)
        for stat in ['str_bonus', 'dex_bonus', 'mag_bonus', 'dt_bonus']:
            val = getattr(item, stat, 0)
            if val > 0:
                setattr(item, stat, val + int(val * 0.1 * level) + 1)

    # Apply to all equipped
    for slot, item in inv.equipped.items():
        if item and not isinstance(item, str):
            # Variance: Randomize +/- 1 level
            actual_level = max(0, target_enhancement + random.randint(-1, 1))
            if actual_level > 0:
                apply_enhancement(item, actual_level)

    # [Fix] Recalculate Stats to apply Str/Dex bonuses from new gear
    engine._recalculate_stats()
            
    # Assign skills to slots (Slot 0 -> Key '6')
    # Prioritize class specific skills
    slot_idx = 0
    special_priority = ["FIREBALL", "RAGE", "CHAIN_LIGHTNING", "APOCALYPSE"]
    
    # 1. Special skills first
    for s in inv.skills:
        if s in special_priority and slot_idx < 5:
            inv.skill_slots[slot_idx] = s
            slot_idx += 1
            
    # 2. Others
    for s in inv.skills:
        if s not in inv.skill_slots and slot_idx < 5:
            inv.skill_slots[slot_idx] = s
            slot_idx += 1

    if floor >= 25:
        # equip("쇼트 소드", "손1") # Already equipped above based on class
        if "HEALING" not in inv.skills: inv.skills.append("HEALING")
        equip("캡", "머리")

    if floor >= 50:
        # equip("브로드 소드", "손1")
        # equip("체인 메일", "몸통")
        equip("헬름", "머리")
        if "FIREBALL" not in inv.skills: inv.skills.append("FIREBALL")
    if floor >= 75:
        equip("바스타드 소드", "손1")
        equip("플레이트 메일", "몸통")
        equip("풀 헬름", "머리")
        if "CHAIN_LIGHTNING" not in inv.skills: inv.skills.append("CHAIN_LIGHTNING")
    if floor >= 99:
        equip("그레이트 소드", "손1") 
        inv.equipped["손2"] = "(양손 점유)"
        equip("풀 플레이트", "몸통")
        equip("그레이트 헬름", "머리")
        if "APOCALYPSE" not in inv.skills: inv.skills.append("APOCALYPSE")
        if "MANA_SHIELD" not in inv.skills: inv.skills.append("MANA_SHIELD")

    # [Oil Simulation]
    # Simulate usage of enhancement oils (Sharpness/Hardening)
    # 50% chance to have oils applied at high levels
    if floor >= 20:
        # Weapn Oil (Sharpness) -> Attack + (Level * 1)
        weapon = inv.equipped.get("손1")
        if weapon and random.random() < 0.5:
             # Logic from engine.py (approx)
             # Actually engine checks flags "OIL_SHARPNESS"
             # So we just add the flag and the stat bonus manually
             if not hasattr(weapon, 'flags'): weapon.flags = []
             # Handle list or set or string
             if isinstance(weapon.flags, str):
                 if "OIL_SHARPNESS" not in weapon.flags:
                     weapon.flags += ",OIL_SHARPNESS"
             elif isinstance(weapon.flags, list):
                 if "OIL_SHARPNESS" not in weapon.flags:
                     weapon.flags.append("OIL_SHARPNESS")
             elif isinstance(weapon.flags, set):
                 weapon.flags.add("OIL_SHARPNESS")
                 
                 # Apply bonus: +10% Damage
                 if hasattr(weapon, 'attack_min'):
                     weapon.attack_min = int(weapon.attack_min * 1.1)
                     weapon.attack_max = int(weapon.attack_max * 1.1)

        # Armor Oil (Hardening) -> Def + (Level * 1)
        armor = inv.equipped.get("몸통")
        if armor and random.random() < 0.5:
             if not hasattr(armor, 'flags'): armor.flags = []
             if isinstance(armor.flags, str):
                 if "OIL_HARDENING" not in armor.flags:
                     armor.flags += ",OIL_HARDENING"
             elif isinstance(armor.flags, list):
                 if "OIL_HARDENING" not in armor.flags:
                     armor.flags.append("OIL_HARDENING")
             elif isinstance(armor.flags, set):
                 armor.flags.add("OIL_HARDENING")
                 
                 if hasattr(armor, 'defense'):
                     armor.defense = int(armor.defense * 1.1)

    # 스탯 재계산
    if hasattr(engine, '_recalculate_stats'):
        engine._recalculate_stats()
    
    # HP/MP 회복
    stats.current_hp = stats.max_hp
    stats.current_mp = stats.max_mp
    if hasattr(stats, 'max_stamina'):
        stats.current_stamina = stats.max_stamina

def run_test_scenario(floor: int, player_level: int, iterations: int = 5):
    print(f"\n[Scenario] Floor {floor} (Lv {player_level}) - {iterations} trials per class")
    classes = ["WARRIOR", "ROGUE", "SORCERER", "BARBARIAN"]
    
    for class_id in classes:
        print(f"  Testing Class: {class_id}")
        stats_log = {"WIN": 0, "DEATH": 0, "TIMEOUT": 0, "ERROR": 0}
        total_turns = 0
        
        for i in range(iterations):
            engine = HeadlessEngine()
            engine.current_level = floor
            # 맵 초기화 (해당 층 보스 생성 강제)
            engine._initialize_world()
            
            # 플레이어 셋업
            setup_player_for_test(engine, floor, player_level, class_id)
            
            outcome = engine.run()
            stats_log[outcome] += 1
            total_turns += engine.current_turns
            # print(f"    Trial {i+1}: {outcome} ({engine.current_turns} t)")
            
        win_rate = (stats_log["WIN"] / iterations) * 100
        avg_turns = total_turns / iterations
        print(f"    Result: {stats_log} | Win: {win_rate:.0f}% | Avg Turns: {avg_turns:.1f}")


def run_enhancement_test(iterations: int = 1000):
    print(f"\n[Enhancement Test] Simulating {iterations} enhancement attempts per level")
    
    # Mock Engine for Shrine Methods
    class MockShrineEngine(HeadlessEngine):
        def _recalculate_stats(self): pass

    engine = MockShrineEngine()
    # engine.world is initialized in super().__init__
    engine.world.engine = engine # Link back
    
    # Mock Player to hold item
    p_ent = engine.world.create_entity()
    engine.world.add_component(p_ent.entity_id, PositionComponent(x=0,y=0))
    engine.world.add_component(p_ent.entity_id, InventoryComponent())
    engine.world.add_component(p_ent.entity_id, PlayerComponent())
    engine.player_id = p_ent.entity_id
    
    # Import Shrine Methods dynamically to bind them
    from .shrine_methods import _shrine_enhance_item
    # Bind method to engine instance
    engine._shrine_enhance_item = _shrine_enhance_item.__get__(engine, MockShrineEngine)
    
    stats = {
        "success": {},
        "fail_durability": {},
        "fail_break": {},
        "fail_destroy": {},
        "max_reached": 0
    }
    
    for _ in range(iterations):
        # Create a fresh item
        item = ItemDefinition("Test Sword", "WEAPON", "Desc", "|", "white", 1, 5, 0, 0, 0, enhancement_level=0)
        item.max_durability = 100
        item.current_durability = 100
        item.enhancement_level = 0
        
        # Equip it so logic works (destruction check uses equipped)
        p_inv = p_ent.get_component(InventoryComponent)
        p_inv.equipped["손1"] = item
        
        while item.enhancement_level < 10: # Try to go to +10 (+11 is max usually?) logic says up to 10
            lvl = item.enhancement_level
            
            # Init stats for this level
            if lvl not in stats["success"]: stats["success"][lvl] = 0
            if lvl not in stats["fail_durability"]: stats["fail_durability"][lvl] = 0
            if lvl not in stats["fail_break"]: stats["fail_break"][lvl] = 0
            if lvl not in stats["fail_destroy"]: stats["fail_destroy"][lvl] = 0
            
            prev_durability = item.current_durability
            
            # Attempt Enhance
            engine._shrine_enhance_item(item)
            
            # Check result
            if item.enhancement_level > lvl:
                stats["success"][lvl] += 1
            else:
                # Failed
                if "손1" not in p_inv.equipped or p_inv.equipped["손1"] is None:
                    stats["fail_destroy"][lvl] += 1
                    break # Item gone
                elif item.current_durability == 0:
                    stats["fail_break"][lvl] += 1
                    item.current_durability = 100 # Repair for next try to simulate persistent user?
                    # Or stop this run? Usually broken item can't be enhanced.
                    break 
                elif item.current_durability < prev_durability:
                    stats["fail_durability"][lvl] += 1
                    item.current_durability = 100 # Repair
                else:
                     # Should not happen based on logic (always penalty)
                     pass
        
        if item.enhancement_level >= 10:
             stats["max_reached"] += 1

    print(f"  Max Level (+10) Reached: {stats['max_reached']} / {iterations} ({stats['max_reached']/iterations*100:.1f}%)")
    
    levels = sorted(stats["success"].keys())
    print("  Level | Success | Fail(Dur) | Fail(Brk) | Fail(Dest)")
    print("  ------+---------+-----------+-----------+-----------")
    for lvl in levels:
        s = stats["success"].get(lvl, 0)
        fd = stats["fail_durability"].get(lvl, 0)
        fb = stats["fail_break"].get(lvl, 0)
        fdest = stats["fail_destroy"].get(lvl, 0)
        total = s + fd + fb + fdest
        if total == 0: continue
        print(f"   +{lvl}  |  {s/total*100:5.1f}% |   {fd/total*100:5.1f}%   |   {fb/total*100:5.1f}%   |   {fdest/total*100:5.1f}%")

def run_drop_rate_test(floor: int, iterations: int = 50):
    print(f"\n[Drop Rate Test] Floor {floor} - {iterations} monster kills")
    total_items = 0
    rarity_counts = {"NORMAL": 0, "MAGIC": 0, "UNIQUE": 0}
    gold_total = 0
    drop_count_dist = {}
    
    engine = HeadlessEngine()
    engine.current_level = floor
    engine._initialize_world()
    
    # Mock Player for Magic Find check
    p_ent = engine.world.get_player_entity()
    p_inv = p_ent.get_component(InventoryComponent)
    # Give some MF gear?
    p_inv.equipped["머리"] = ItemDefinition("MF Helm", "ARMOR", "머리", "|", "white", 1, 0, 0, 0, 0)
    p_inv.equipped["머리"].magic_find = 500 # Extreme MF for testing
    
    combat_sys = engine.world.get_system(CombatSystem)
    
    zero_drops = 0
    gold_only = 0
    
    for i in range(iterations):
        # Create a dummy monster
        m_ent = engine.world.create_entity()
        engine.world.add_component(m_ent.entity_id, PositionComponent(x=1, y=1))
        engine.world.add_component(m_ent.entity_id, MonsterComponent(monster_id="TEST_MOB", type_name="TestMob"))
        engine.world.add_component(m_ent.entity_id, StatsComponent(hp=10, max_hp=10, attack=5, defense=0, current_hp=0)) # Dead
        
        # Kill it using _handle_death logic
        combat_sys._handle_death(p_ent, m_ent)
        
        # Check drops
        has_loot = False
        if m_ent.has_component(LootComponent):
            loot = m_ent.get_component(LootComponent)
            if loot.gold > 0: has_loot = True
            gold_total += loot.gold
            
            n_items = len(loot.items)
            drop_count_dist[n_items] = drop_count_dist.get(n_items, 0) + 1
            
            if n_items > 0:
                has_loot = True
                for item_data in loot.items:
                    item = item_data['item']
                    rarity = getattr(item, 'rarity', 'NORMAL')
                    rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                    total_items += 1
            elif loot.gold > 0:
                gold_only += 1
        
        if not has_loot:
             zero_drops += 1
             drop_count_dist[0] = drop_count_dist.get(0, 0) + 1

    print(f"  Total Items: {total_items} (Avg {total_items/iterations:.2f} per kill)")
    print(f"  Avg Gold: {gold_total/iterations:.1f}")
    print(f"  Zero Loot Kills: {zero_drops}")
    print(f"  Gold Only Kills: {gold_only}")
    print(f"  Rarity: {rarity_counts}")
    total_r = sum(rarity_counts.values()) or 1
    print(f"  Ratios: N {rarity_counts['NORMAL']/total_r*100:.1f}% | M {rarity_counts.get('MAGIC',0)/total_r*100:.1f}% | U {rarity_counts.get('UNIQUE',0)/total_r*100:.1f}%")
    print(f"  Item Count Dist: {dict(sorted(drop_count_dist.items()))}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    print("Starting Dungeon Crawler Integrated Balance Simulation...")
    
    from .systems import CombatSystem # Import here to avoid circular imports if any
    
    # 1. Enhancement Tests
    run_enhancement_test(1000)
    
    # 2. Drop Rate Tests
    run_drop_rate_test(1, 100)   # Early Game
    run_drop_rate_test(30, 100)  # Mid Game (Peak Drop)
    run_drop_rate_test(70, 100)  # Late Game
    
    # 3. Combat Tests
    # run_test_scenario(25, 20, 2)  
