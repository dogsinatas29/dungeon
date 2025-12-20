# dungeon/engine.py - 게임의 실행 흐름을 관리하는 메인 모듈

import os
import time
import random
import readchar # readchar 임포트 추가
from typing import List, Dict, Tuple, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import PositionComponent, RenderComponent, MapComponent, MonsterComponent, MessageComponent, StatsComponent, LevelComponent, InventoryComponent, AIComponent
from .systems import InputSystem, MovementSystem, RenderSystem, MonsterAISystem, CombatSystem 
from .renderer import Renderer
from .data_manager import load_item_definitions



import enum

class GameState(enum.Enum):
    PLAYING = 0
    INVENTORY = 1

class Engine:
    """게임 루프, 초기화, 시스템 관리를 담당하는 메인 클래스"""
    def __init__(self, player_name="Hero", game_data=None):
        self.is_running = False
        self.world = World(self) # World 초기화 시 Engine 자신을 참조
        self.turn_number = 0
        self.player_name = player_name
        self.state = GameState.PLAYING # 초기 상태
        self.selected_item_index = 0 # 인벤토리 선택 인덱스
        self.inventory_category_index = 0 # 0: 아이템, 1: 장비, 2: 스크롤, 3: 스킬

        # 렌더러 초기화
        self.renderer = Renderer() 

        self._initialize_world(game_data)
        self._initialize_systems()
        
        # 시스템 등록 후, 이벤트 리스너를 한 번 더 초기화하여 시스템-이벤트 간 연결 완료
        initialize_event_listeners(self.world)

    def _initialize_world(self, game_data=None):
        """맵, 플레이어, 몬스터 등 초기 엔티티 생성"""
        # TODO: game_data(저장된 데이터)가 있으면 그것을 로드하는 로직 추가 필요
        # 현재는 하드코딩된 초기화만 유지
        
        # 맵 생성 (DungeonMap 사용)
        width = 120
        height = 60
        rng = random.Random()
        
        # DungeonMap 인스턴스 생성 (자동으로 generate_map 호출됨)
        dungeon_map = DungeonMap(width, height, rng)
        
        # 맵 데이터 가져오기
        map_data = dungeon_map.map_data
        
        # 1. 플레이어 엔티티 생성 (ID=1)
        player_x, player_y = dungeon_map.start_x, dungeon_map.start_y
        player_entity = self.world.create_entity() 
        self.world.add_component(player_entity.entity_id, PositionComponent(x=player_x, y=player_y))
        self.world.add_component(player_entity.entity_id, RenderComponent(char='@', color='yellow'))
        self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
        self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))
        
        # 샘플 아이템 추가 (UI 검증용)
        item_defs = load_item_definitions()
        sample_items = {}
        if item_defs:
            # WEAPON, ARMOR, CONSUMABLE 등 다양한 타입 준비
            for name, item in item_defs.items():
                sample_items[name] = {'item': item, 'qty': 1}
        
        self.world.add_component(player_entity.entity_id, InventoryComponent(
            items=sample_items, 
            equipped={
                "머리": None, "몸통": "가죽 갑옷", "장갑": None, 
                "신발": None, "손1": "낡은 검", "손2": None, 
                "액세서리1": None, "액세서리2": None
            },
            quick_slots=["체력 물약", "마력 물약", None, None, None]
        ))
        
        # 2. 맵 엔티티 생성 (ID=2)
        map_entity = self.world.create_entity()
        # map_data는 이미 2D 리스트이므로 바로 전달
        map_component = MapComponent(width=width, height=height, tiles=map_data) 
        self.world.add_component(map_entity.entity_id, map_component)
        
        # 3. 메시지 로그 엔티티 생성 (ID=3)
        message_entity = self.world.create_entity()
        self.world.add_component(message_entity.entity_id, MessageComponent())
        
        # 4. 몬스터 엔티티 생성 (각 방의 중앙에 배치, 시작 방 제외)
        for i, room in enumerate(dungeon_map.rooms[1:]): # 첫 번째 방(플레이어 시작) 제외
            monster_x, monster_y = room.center
            monster_entity = self.world.create_entity()
            self.world.add_component(monster_entity.entity_id, PositionComponent(x=monster_x, y=monster_y))
            
            # AI 패턴 결정 (0: 정지, 1: 도망, 2: 추적)
            behavior = i % 3
            color = "green"
            type_name = "Goblin"
            
            # 능력치 초기화 (기본값)
            max_hp, atk, df = 30, 5, 2
            
            if behavior == AIComponent.CHASE: 
                color = "red"
                type_name = "Aggressive Goblin"
                atk = 8  # 추적형은 공격력이 높음
            elif behavior == AIComponent.FLEE: 
                color = "blue"
                type_name = "Cowardly Goblin"
                df = 5   # 도망형은 방어력이 높음
            else:
                type_name = "Lazy Goblin"
                max_hp = 50 # 정지형은 맷집이 좋음
            
            self.world.add_component(monster_entity.entity_id, RenderComponent(char='g', color=color))
            self.world.add_component(monster_entity.entity_id, MonsterComponent(type_name=type_name))
            self.world.add_component(monster_entity.entity_id, AIComponent(behavior=behavior, detection_range=8))
            self.world.add_component(monster_entity.entity_id, StatsComponent(max_hp=max_hp, current_hp=max_hp, attack=atk, defense=df))

    def _initialize_systems(self):
        """시스템 등록 (실행 순서가 중요함)"""
        self.input_system = InputSystem(self.world)
        self.monster_ai_system = MonsterAISystem(self.world)
        self.movement_system = MovementSystem(self.world)
        self.combat_system = CombatSystem(self.world)
        self.render_system = RenderSystem(self.world)
        
        # 시스템 순서 등록: 입력 -> AI -> 이동 -> 전투(이벤트 기반) -> 렌더링
        self.world.add_system(self.input_system)
        self.world.add_system(self.monster_ai_system)
        self.world.add_system(self.movement_system)
        self.world.add_system(self.combat_system)
        self.world.add_system(self.render_system)

    def _get_input(self) -> str:
        """사용자 입력을 받아 반환 (readchar 사용)"""
        # input() 대신 readchar.readkey()를 사용하여 Enter 없이 즉시 입력 처리
        return readchar.readkey()

    # dungeon/engine.py 내 Engine.run 메서드 수정 (주요 부분만)

    def run(self):
        """메인 게임 루프"""
        self.is_running = True
        
        # 첫 렌더링
        self._render()
        
        while self.is_running:
            # 1. 사용자 입력 처리
            action = self._get_input()
            
            if self.state == GameState.PLAYING:
                if action == 'i' or action == 'I':
                    self.state = GameState.INVENTORY
                    self._render()
                    continue

                self.turn_number += 1
                
                # InputSystem에서 턴 소모 여부 결정
                turn_spent = self.input_system.handle_input(action)
                
                if turn_spent:
                    # 2. 게임 상태 업데이트 (모든 시스템 순차 실행)
                    # InputSystem은 handle_input에서 이미 처리했으므로 제외하고 실행
                    for system in self.world._systems:
                        if system is not self.input_system and system is not None:
                            system.process()
                    
                    # 3. 이벤트 처리 (충돌 메시지 등 처리)
                    self.world.event_manager.process_events()
                    
                    # 4. 상태 변경 후 화면 다시 그리기
                    self._render()
            
            elif self.state == GameState.INVENTORY:
                self._handle_inventory_input(action)
                self._render()
                
    def _handle_inventory_input(self, action):
        """인벤토리 상태에서의 입력 처리"""
        if action == 'i' or action == 'I' or action == readchar.key.ESC:
            self.state = GameState.PLAYING
            return
        
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        from .components import InventoryComponent
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 1. 현재 카테고리에 해당하는 아이템 필터링
        filtered_items = []
        if self.inventory_category_index == 0: # 아이템 (소모품)
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type == 'CONSUMABLE']
        elif self.inventory_category_index == 1: # 장비
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type in ['WEAPON', 'ARMOR']]
        elif self.inventory_category_index == 2: # 스크롤
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type == 'SCROLL']
        elif self.inventory_category_index == 3: # 스킬
            # TODO: 스킬 시스템 연동 후 리스트업
            filtered_items = []

        item_count = len(filtered_items)

        # 2. 내비게이션 처리
        if action == readchar.key.UP:
             self.selected_item_index = max(0, self.selected_item_index - 1)
        elif action == readchar.key.DOWN:
             if item_count > 0:
                 self.selected_item_index = min(item_count - 1, self.selected_item_index + 1)
        elif action == readchar.key.LEFT:
             self.inventory_category_index = (self.inventory_category_index - 1) % 4
             self.selected_item_index = 0
        elif action == readchar.key.RIGHT:
             self.inventory_category_index = (self.inventory_category_index + 1) % 4
             self.selected_item_index = 0
        elif action == readchar.key.ENTER or action == '\r' or action == '\n':
             if filtered_items and 0 <= self.selected_item_index < len(filtered_items):
                 self._equip_selected_item(filtered_items[self.selected_item_index][1])

    def _equip_selected_item(self, item_data):
        """선택된 아이템을 조건에 맞춰 장착"""
        item = item_data['item']
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        from .components import InventoryComponent
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 타입별 장착 로직
        if item.type == 'WEAPON':
            if item.hand_type == 2: # 양손 무기
                inv.equipped["손1"] = item.name
                inv.equipped["손2"] = "(양손 점유)"
            else: # 한손 무기
                # 만약 기존에 양손 무기를 들고 있었다면 손2 비우기
                if inv.equipped.get("손2") == "(양손 점유)":
                    inv.equipped["손2"] = None
                
                # 손1이 비어있으면 손1, 아니면 손2 (이도류)
                if not inv.equipped.get("손1"):
                    inv.equipped["손1"] = item.name
                elif not inv.equipped.get("손2"):
                    inv.equipped["손2"] = item.name
                else:
                    # 둘 다 차있으면 손1 교체
                    inv.equipped["손1"] = item.name
        
        elif item.type == 'SHIELD':
            # 양손 무기 사용 중이면 해제
            if inv.equipped.get("손2") == "(양손 점유)":
                inv.equipped["손1"] = None
            inv.equipped["손2"] = item.name
            
        elif item.type == 'ARMOR':
            inv.equipped["몸통"] = item.name
        # TODO: 머리, 장갑, 신발 등 타입 추가 시 매핑 확장
        
        # 장착 메시지 추가
        message_entity = self.world.get_entities_with_components([MessageComponent])
        if message_entity:
            msg_comp = message_entity[0].get_component(MessageComponent)
            from .systems import MessageEvent
            self.world.event_manager.push(MessageEvent(f"{item.name}을(를) 장착했습니다."))

    def _render(self):
        """World 상태를 기반으로 Renderer를 사용하여 화면을 그립니다."""
        self.renderer.clear_buffer()
        
        RIGHT_SIDEBAR_X = 81
        SIDEBAR_WIDTH = self.renderer.width - RIGHT_SIDEBAR_X
        # 한글 너비 문제를 방지하기 위해 맵 가시 영역을 약간 줄임 (안전 마진 확보)
        MAP_VIEW_WIDTH = 78 
        MAP_VIEW_HEIGHT = self.renderer.height - 12 # 하단 스탯 창 공간 확보
        
        # 0. 구분선 복구 (레이아웃 틀어짐 방지 가이드 역할)
        for y in range(self.renderer.height):
            self.renderer.draw_char(80, y, "|", "dark_grey")
        
        player_entity = self.world.get_player_entity()
        player_pos = player_entity.get_component(PositionComponent) if player_entity else None
        
        # 카메라 오프셋 계산 (플레이어를 중앙에)
        if player_pos:
            camera_x = max(0, min(player_pos.x - MAP_VIEW_WIDTH // 2, 120 - MAP_VIEW_WIDTH))
            camera_y = max(0, min(player_pos.y - MAP_VIEW_HEIGHT // 2, 60 - MAP_VIEW_HEIGHT))
        else:
            camera_x, camera_y = 0, 0

        # 1. 맵 렌더링 (Left Top - Viewport 적용)
        map_comp_list = self.world.get_entities_with_components([MapComponent])
        map_height = 0
        if map_comp_list:
            map_comp = map_comp_list[0].get_component(MapComponent)
            map_height = MAP_VIEW_HEIGHT
            
            for screen_y in range(MAP_VIEW_HEIGHT):
                world_y = camera_y + screen_y
                if world_y >= map_comp.height: break
                
                for screen_x in range(MAP_VIEW_WIDTH):
                    world_x = camera_x + screen_x
                    if world_x >= map_comp.width: break
                    
                    char = map_comp.tiles[world_y][world_x]
                    color = "dark_grey" if char == "." else "brown"
                    self.renderer.draw_char(screen_x, screen_y, char, color)

        # 구분선 (Horizontal) - 맵과 스탯 창 사이
        status_start_y = map_height + 1
        self.renderer.draw_text(0, status_start_y, "-" * 80, "dark_grey")

        # 2. 엔티티 렌더링 (플레이어, 몬스터 등 - 카메라 오프셋 적용)
        renderable_entities = self.world.get_entities_with_components([PositionComponent, RenderComponent])
        for entity in renderable_entities:
            pos = entity.get_component(PositionComponent)
            render = entity.get_component(RenderComponent)
            
            # 맵 컴포넌트 엔티티는 제외
            if entity.get_component(MapComponent):
                continue
            
            screen_x = pos.x - camera_x
            screen_y = pos.y - camera_y
            
            if 0 <= screen_x < MAP_VIEW_WIDTH and 0 <= screen_y < MAP_VIEW_HEIGHT:
                self.renderer.draw_char(screen_x, screen_y, render.char, render.color)

        # 3. 캐릭터 스탯 렌더링 (Left Bottom - below Map)
        status_start_y = map_height + 1
        current_y = status_start_y + 1
        player_entity = self.world.get_player_entity()
        
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            level_comp = player_entity.get_component(LevelComponent)
            
            if stats:
                # Name
                self.renderer.draw_text(2, current_y, f"NAME: {self.player_name}", "gold")
                
                # HP, MP, STM Bar 스타일
                hp_str = f"HP  : {stats.current_hp:3}/{stats.max_hp:3}"
                mp_str = f"MP  : {stats.current_mp:3}/{stats.max_mp:3}"
                stm_str = f"STM : {int(stats.current_stamina):3}/{int(stats.max_stamina):3}"
                
                self.renderer.draw_text(20, current_y, hp_str, "red")
                self.renderer.draw_text(40, current_y, mp_str, "blue")
                self.renderer.draw_text(60, current_y, stm_str, "green")
                current_y += 1
                
                # Level info
                if level_comp:
                    lv_str = f"LV  : {level_comp.level}"
                    exp_str = f"EXP : {level_comp.exp}/{level_comp.exp_to_next}"
                    job_str = f"JOB : {level_comp.job}"
                    self.renderer.draw_text(2, current_y, f"{lv_str:<10} {job_str:<15} {exp_str}", "white")
                current_y += 1
                
                # Stats
                atk_str = f"ATK : {stats.attack}"
                def_str = f"DEF : {stats.defense}"
                self.renderer.draw_text(2, current_y, f"{atk_str:<10} {def_str:<10}", "white")


        # 4. 오른쪽 사이드바 (Right Sidebar)
        # 4-1. 로그 (Logs)
        log_start_y = 0
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, log_start_y, "[ LOGS ]", "gold")
        
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            # 최근 8개 메시지 표시
            recent_messages = message_comp.messages[-8:]
            for i, msg in enumerate(recent_messages):
                # 너비 제한으로 자르기
                truncated_msg = (msg[:SIDEBAR_WIDTH-4] + '..') if len(msg) > SIDEBAR_WIDTH-4 else msg
                self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, log_start_y + 1 + i, f"> {truncated_msg}", "white")

        # 4-2. 장비 (Equipment)
        eq_start_y = 10
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, eq_start_y, "[ EQUIP ]", "gold")
        eq_y = eq_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp:
                slots = ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]
                for i, slot in enumerate(slots):
                    if eq_y >= 19: break # 사이드바 높이 제한 (스크롤/스킬 영역 확보)
                    item = inv_comp.equipped.get(slot)
                    item_display = item if item else "----"
                    color = "white"
                    if item_display == "(양손 점유)":
                        color = "dark_grey"
                    
                    # 슬롯명과 아이템명을 정돈해서 표시
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, eq_y, f"{slot:<5}: {item_display}", color)
                    eq_y += 1

        # 4-3. 퀵슬롯 (Quick Slots)
        qs_start_y = 19  # 장비 슬롯이 늘어났으므로 시작 위치 조정
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, qs_start_y, "[ QUICK SLOTS ]", "gold")
        qs_y = qs_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'quick_slots'):
                for i, item in enumerate(inv_comp.quick_slots):
                    item_name = item if item else "----"
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, qs_y + i, f"{i+1}: {item_name}", "white")

        # 4-4. 스킬 리스트 (Skill List)
        skill_start_y = 25  # 여기도 조정
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y, "[ SKILLS ]", "gold")
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y + 1, "- Basic Attack", "white")

        # 5. 입력 가이드 (Bottom fixed)
        guide_y = self.renderer.height - 1
        self.renderer.draw_text(0, guide_y, " [MOVE] WASD/Arrows | [I] Inventory | [Q] Quit", "green")
        
        # 6. 인벤토리 팝업 렌더링 (INVENTORY 상태일 때만)
        if self.state == GameState.INVENTORY:
            self._render_inventory_popup()

        self.renderer.render()

    def _render_inventory_popup(self):
        """항목 목록을 보여주는 중앙 팝업창 렌더링 (카테고리 분류 포함)"""
        MAP_WIDTH = 80
        POPUP_WIDTH = 60
        POPUP_HEIGHT = 20
        # 맵 영역(80) 내에 중앙 정렬
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. 배경 및 테두리 그리기 (불투명 처리 보강)
        for y in range(start_y, start_y + POPUP_HEIGHT):
            for x in range(start_x, start_x + POPUP_WIDTH):
                if y == start_y or y == start_y + POPUP_HEIGHT - 1:
                    char = "-"
                elif x == start_x or x == start_x + POPUP_WIDTH - 1:
                    char = "|"
                else:
                    char = " "
                
                # 배경색을 어둡게 지정하여 뒤쪽이 보이지 않도록 함 (다만 현재 렌러더엔 배경색 기능이 없으므로 공백으로 확실히 채움)
                self.renderer.draw_char(x, y, char, "white")
                
        # 2. 카테고리 탭 표시
        categories = ["아이템", "장비", "스크롤", "스킬"]
        tab_x = start_x + 2
        for i, cat in enumerate(categories):
            color = "yellow" if i == self.inventory_category_index else "dark_grey"
            # 선택된 탭은 대괄호 표시
            text = f"[{cat}]" if i == self.inventory_category_index else f" {cat} "
            self.renderer.draw_text(tab_x, start_y + 1, text, color)
            tab_x += len(text) + 2
        
        # 3. 구분선
        self.renderer.draw_text(start_x + 1, start_y + 2, "-" * (POPUP_WIDTH - 2), "dark_grey")
        
        # 4. 아이템 목록 필터링 및 표시
        player_entity = self.world.get_player_entity()
        if player_entity:
             from .components import InventoryComponent
             inv_comp = player_entity.get_component(InventoryComponent)
             
             if inv_comp:
                 # 필터링 로직
                 filtered_items = []
                 if self.inventory_category_index == 0: # 아이템
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type == 'CONSUMABLE']
                 elif self.inventory_category_index == 1: # 장비
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type in ['WEAPON', 'ARMOR']]
                 elif self.inventory_category_index == 2: # 스크롤
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type == 'SCROLL']
                 elif self.inventory_category_index == 3: # 스킬
                     filtered_items = [] # TODO: Skill list

                 if not filtered_items and self.inventory_category_index != 3:
                     self.renderer.draw_text(start_x + 2, start_y + 4, "  (비어 있음)", "dark_grey")
                 elif self.inventory_category_index == 3:
                     self.renderer.draw_text(start_x + 2, start_y + 4, "  - 기본 공격 (Lv.1)", "white")
                 else:
                     current_y = start_y + 4
                     for idx, (item_id, item_data) in enumerate(filtered_items):
                         if current_y >= start_y + POPUP_HEIGHT - 2: break
                         
                         name = item_data['item'].name
                         qty = item_data['qty']
                         prefix = "> " if idx == self.selected_item_index else "  "
                         color = "green" if idx == self.selected_item_index else "white"
                         
                         self.renderer.draw_text(start_x + 2, current_y, f"{prefix}{name} x{qty}", color)
                         current_y += 1
        
        # 5. 하단 도움말
        help_text = "[←/→] 탭 전환  [↑/↓] 선택  [ESC/I] 닫기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(help_text)) // 2, start_y + POPUP_HEIGHT - 2, help_text, "dark_grey")

if __name__ == '__main__':
    engine = Engine()
    engine.run()
