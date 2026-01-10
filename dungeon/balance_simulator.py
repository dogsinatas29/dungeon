import sys
import os
import time
import random
import logging
from typing import Dict, List, Optional

# 상위 디렉토리 임포트 허용
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
config.LANGUAGE = "en" # 영어 자원 사용

from engine import Engine, GameState
from components import PositionComponent, StatsComponent, MapComponent, MonsterComponent, InventoryComponent, LevelComponent
from data_manager import ItemDefinition
from constants import ELEMENT_NONE

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
        import renderer
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
                        from events import MessageEvent, SoundEvent
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
        from components import DoorComponent, SwitchComponent, BlockMapComponent
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

        # 1. 생존 상시 체크: HP가 30% 이하일 때 포션 사용 시도
        if stats.current_hp / stats.max_hp < 0.3:
            # Healing Potion 검색 (단순화: 인벤토리에 있으면 사용)
            if "Healing Potion" in inv.items or any("Healing Potion" in k for k in inv.items):
                self.metrics["potions_used"] += 1
                stats.current_hp = min(stats.max_hp, stats.current_hp + 50) # 보정
                # print("  [Sim] Agent used a potion!")

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
                # 스킬 사용 여부 결정 (MP 충분 시)
                if stats.current_mp > 20 and inv.skills and random.random() < 0.3:
                    self.metrics["skills_used"] += 1
                    return '1' # 첫 번째 스킬 슬롯 시뮬레이션

                return 'd' if dx > 0 else ('a' if dx < 0 else ('s' if dy > 0 else 'w'))

            # 거리 좁히기
            if abs(dx) > abs(dy):
                return 'd' if dx > 0 else 'a'
            else:
                return 's' if dy > 0 else 'w'
        
        return random.choice(['w', 'a', 's', 'd'])

    def _render(self): pass # 렌더링 스킵
    def _get_input(self): return None

def setup_player_for_test(engine, floor, level):
    player = engine.world.get_player_entity()
    stats = player.get_component(StatsComponent)
    lvl_comp = player.get_component(LevelComponent)
    inv = player.get_component(InventoryComponent)
    
    lvl_comp.level = level
    
    # 기본 스탯 보정 (장비 전) - 조금 더 탱탱하게
    stats.base_max_hp = 200 + (level * 25)
    stats.base_max_mp = 100 + (level * 10)
    stats.strength = 20 + (level * 2.0)
    stats.vit = 20 + (level * 2.5)
    stats.mag = 15 + (level * 1.5)
    stats.dex = 20 + (level * 2.0)
    
    # 층수에 따른 장비 및 스탯 보정
    def equip(item_name, slot):
        item_def = engine.item_defs.get(item_name)
        if item_def:
            inv.equipped[slot] = item_def
        else:
            logging.warning(f"Item not found for test: {item_name}")

    if floor >= 25:
        equip("Short Sword", "손1")
        equip("Leather Armor", "몸통")
        equip("Cap", "머리")
        inv.skills.append("HEALING")
    if floor >= 50:
        equip("Broad Sword", "손1")
        equip("Chain Mail", "몸통")
        equip("Helm", "머리")
        if "FIREBALL" not in inv.skills: inv.skills.append("FIREBALL")
    if floor >= 75:
        equip("Bastard Sword", "손1")
        equip("Plate Mail", "몸통")
        equip("Full Helm", "머리")
        if "CHAIN_LIGHTNING" not in inv.skills: inv.skills.append("CHAIN_LIGHTNING")
    if floor >= 99:
        equip("Great Sword", "손1") # 양손 무기일 텐데 손1에 넣고 손2 점유 처리 필요할 수 있음
        inv.equipped["손2"] = "(양손 점유)" # Great Sword는 hand_type 2임
        equip("Full Plate", "몸통")
        equip("Great Helm", "머리")
        if "APOCALYPSE" not in inv.skills: inv.skills.append("APOCALYPSE")
        if "MANA_SHIELD" not in inv.skills: inv.skills.append("MANA_SHIELD")

    # 스탯 재계산 호출
    if hasattr(engine, '_recalculate_stats'):
        engine._recalculate_stats()
    
    # HP/MP를 최대로 채움
    stats.current_hp = stats.max_hp
    stats.current_mp = stats.max_mp

def run_test_scenario(floor: int, player_level: int, iterations: int = 10):
    print(f"\n[Scenario] Floor {floor} (Player Lv {player_level}) - {iterations} trials")
    stats_log = {"WIN": 0, "DEATH": 0, "TIMEOUT": 0, "ERROR": 0}
    total_turns = 0
    
    for i in range(iterations):
        engine = HeadlessEngine()
        engine.current_level = floor
        
        # 맵 초기화 (해당 층 보스 생성 강제)
        engine._initialize_world()
        
        # 플레이어 셋업
        setup_player_for_test(engine, floor, player_level)
        
        outcome = engine.run()
        stats_log[outcome] += 1
        total_turns += engine.current_turns
        print(f"    Trial {i+1}: {outcome} ({engine.current_turns} turns)")
        
    win_rate = (stats_log["WIN"] / iterations) * 100
    avg_turns = total_turns / iterations
    print(f"  Result: {stats_log}")
    print(f"  Win Rate: {win_rate:.1f}% | Avg Turns: {avg_turns:.1f}")
    return stats_log

if __name__ == "__main__":
    # 로깅 비활성화
    logging.basicConfig(level=logging.CRITICAL)
    
    print("Starting Dungeon Crawler Balance Simulation...")
    run_test_scenario(25, 20, 10)  # Butcher
    run_test_scenario(50, 45, 10)  # Leoric
    run_test_scenario(75, 65, 10)  # Lich King
    run_test_scenario(99, 85, 10)  # Diablo
