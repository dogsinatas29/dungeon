import sys
import os
import time
import random
import logging
from typing import Dict, List, Optional

# 상위 디렉토리 임포트 허용
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from . import config
config.LANGUAGE = "ko" # 한국어 자원 사용 (maps.csv와 불일치 해결)

from .engine import Engine, GameState
# ... imports ...

# ... (omitted code) ...


from .components import PositionComponent, StatsComponent, MapComponent, MonsterComponent, InventoryComponent, LevelComponent, LootComponent
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
            if "체력 물약" in inv.items:
                self.metrics["potions_used"] += 1
                pot = inv.items["체력 물약"]
                # 효과 적용
                stats.current_hp = min(stats.max_hp, stats.current_hp + 50) # 가정된 수치 or item lookup
                pot['qty'] -= 1
                if pot['qty'] <= 0: del inv.items["체력 물약"]
                return None # 포션 사용은 턴 소모 없음? or 턴 소모? 여기선 return None -> loop continues? No, action required.
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
        stats.strength = class_def.str + (level * 2.0)
        stats.vit = class_def.vit + (level * 2.0)
        stats.mag = class_def.mag + (level * 1.5)
        stats.dex = class_def.dex + (level * 2.0)
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
        
    # [Fix] Give Potions for Survival
    inv.add_item(engine.item_defs["체력 물약"], 10)
    inv.add_item(engine.item_defs["마력 물약"], 10)

    # Class Specific Assignment
    if floor >= 20:
        if class_id == "WARRIOR":
            equip("브로드 소드", "손1")
            equip("체인 메일", "몸통")
        elif class_id == "ROGUE":
            equip("단궁", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("가죽 갑옷", "몸통")
        elif class_id == "SORCERER":
            equip("긴 지팡이", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("로브", "몸통")
            if "FIREBALL" not in inv.skills: inv.skills.append("FIREBALL")
        elif class_id == "BARBARIAN":
            equip("배틀 액스", "손1")
            inv.equipped["손2"] = "(양손 점유)"
            equip("스플린트 메일", "몸통")
            if "RAGE" not in inv.skills: inv.skills.append("RAGE")
            
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

    # 스탯 재계산
    if hasattr(engine, '_recalculate_stats'):
        engine._recalculate_stats()
    
    # HP/MP 회복
    stats.current_hp = stats.max_hp
    stats.current_mp = stats.max_mp

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

def run_drop_rate_test(floor: int, iterations: int = 10):
    print(f"\n[Drop Rate Test] Floor {floor} - {iterations} trials")
    total_items = 0
    rarity_counts = {"NORMAL": 0, "MAGIC": 0, "UNIQUE": 0}
    skill_book_counts = 0
    
    for i in range(iterations):
        engine = HeadlessEngine()
        engine.current_level = floor
        
        # [Fix] Force empty item pool in map config for testing diversity
        map_config = engine.map_defs.get(str(floor))
        if map_config:
            map_config.item_pool = [] # Clear restriction for test
            
        engine._initialize_world(spawn_at="START")
        
        # Count Items
        loot_entities = engine.world.get_entities_with_components({LootComponent})
        for ent in loot_entities:
            loot = ent.get_component(LootComponent)
            if loot.items:
                for item_data in loot.items:
                    item = item_data['item']
                    rarity = getattr(item, 'rarity', 'NORMAL')
                    rarity_counts[rarity] += 1
                    total_items += 1
                    if item.type == "SKILLBOOK":
                        skill_book_counts += 1
                        
    print(f"  Total: {total_items} (Avg {total_items/iterations:.1f})")
    print(f"  Rarity: {rarity_counts}")
    print(f"  Skillbooks: {skill_book_counts} ({(skill_book_counts/total_items*100) if total_items else 0:.1f}%)")
    
    total = sum(rarity_counts.values()) or 1
    print(f"  Ratios: N {rarity_counts['NORMAL']/total*100:.1f}% | M {rarity_counts['MAGIC']/total*100:.1f}% | U {rarity_counts['UNIQUE']/total*100:.1f}%")

if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    print("Starting Dungeon Crawler Balance Simulation...")
    
    # Drop Rate Tests (Prioritize first)
    run_drop_rate_test(10, 50)
    # run_drop_rate_test(50, 50)
    # run_drop_rate_test(90, 50)
    
    # Boss Tests (All Classes)
    run_test_scenario(25, 20, 3)  # Butcher
    run_test_scenario(50, 45, 3)  # Leoric
    # run_test_scenario(75, 65, 3)  # Lich King (Optional)
