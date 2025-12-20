# dungeon/engine.py - 게임의 실행 흐름을 관리하는 메인 모듈

import os
import time
import random
import readchar # readchar 임포트 추가
from typing import List, Dict, Tuple, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import PositionComponent, RenderComponent, MapComponent, MonsterComponent, MessageComponent, StatsComponent, LevelComponent, InventoryComponent
from .systems import InputSystem, MovementSystem, RenderSystem 
from .renderer import Renderer



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
        width = 80
        height = 15 # UI 공간 확보를 위해 맵 높이 축소
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
        self.world.add_component(player_entity.entity_id, InventoryComponent(items={}, equipped={}))
        
        # 2. 맵 엔티티 생성 (ID=2)
        map_entity = self.world.create_entity()
        # map_data는 이미 2D 리스트이므로 바로 전달
        map_component = MapComponent(width=width, height=height, tiles=map_data) 
        self.world.add_component(map_entity.entity_id, map_component)
        
        # 3. 메시지 로그 엔티티 생성 (ID=3)
        message_entity = self.world.create_entity()
        self.world.add_component(message_entity.entity_id, MessageComponent())
        
        # 4. 몬스터 엔티티 생성 (각 방의 중앙에 배치, 시작 방 제외)
        for room in dungeon_map.rooms[1:]: # 첫 번째 방(플레이어 시작) 제외
            monster_x, monster_y = room.center
            monster_entity = self.world.create_entity()
            self.world.add_component(monster_entity.entity_id, PositionComponent(x=monster_x, y=monster_y))
            self.world.add_component(monster_entity.entity_id, RenderComponent(char='g', color='green'))
            self.world.add_component(monster_entity.entity_id, MonsterComponent(type_name="Goblin"))

    def _initialize_systems(self):
        """시스템 등록 (실행 순서가 중요함)"""
        self.input_system = InputSystem(self.world)
        self.movement_system = MovementSystem(self.world)
        self.render_system = RenderSystem(self.world)
        
        # 시스템 순서 등록: 입력 -> 이동 -> 렌더링
        self.world.add_system(self.input_system)
        self.world.add_system(self.movement_system)
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
        
        print("--- 게임 시작 ---")
        
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
                
        print("--- 게임 종료 ---")

    def _handle_inventory_input(self, action):
        """인벤토리 상태에서의 입력 처리"""
        if action == 'i' or action == 'I' or action == readchar.key.ESC:
            self.state = GameState.PLAYING
            return
        
        player_entity = self.world.get_player_entity()
        item_count = 0
        if player_entity:
            from .components import InventoryComponent
            inv = player_entity.get_component(InventoryComponent)
            if inv:
                item_count = len(inv.items)

        if action == readchar.key.UP:
             self.selected_item_index = max(0, self.selected_item_index - 1)
        elif action == readchar.key.DOWN:
             if item_count > 0:
                 self.selected_item_index = min(item_count - 1, self.selected_item_index + 1)
        
        # TODO: 엔터 키로 아이템 사용 (추후 구현)

    def _render(self):
        """World 상태를 기반으로 Renderer를 사용하여 화면을 그립니다."""
        self.renderer.clear_buffer()
        
        RIGHT_SIDEBAR_X = 81
        SIDEBAR_WIDTH = self.renderer.width - RIGHT_SIDEBAR_X
        MAP_WIDTH = 80
        
        # 0. 구분선 그리기 (Vertical Line)
        for y in range(self.renderer.height):
            self.renderer.draw_char(80, y, "|", "dark_grey")

        # 1. 맵 렌더링 (Left Top)
        map_comp_list = self.world.get_entities_with_components({MapComponent})
        map_height = 0
        if map_comp_list:
            map_comp = map_comp_list[0].get_component(MapComponent)
            map_height = map_comp.height
            for y, row in enumerate(map_comp.tiles):
                for x, char in enumerate(row):
                    if x < MAP_WIDTH: # 맵이 UI 영역 침범하지 않도록 안전장치
                        color = "dark_grey" if char == "." else "brown"
                        self.renderer.draw_char(x, y, char, color)

        # 2. 엔티티 렌더링 (플레이어, 몬스터 등)
        renderable_entities = self.world.get_entities_with_components({PositionComponent, RenderComponent})
        for entity in renderable_entities:
            pos = entity.get_component(PositionComponent)
            render = entity.get_component(RenderComponent)
            
            # 맵 컴포넌트 엔티티는 제외
            if entity.get_component(MapComponent):
                continue
            
            if pos.x < MAP_WIDTH:
                self.renderer.draw_char(pos.x, pos.y, render.char, render.color)

        # 3. 캐릭터 스탯 렌더링 (Left Bottom - below Map)
        # 구분선 (Horizontal)
        status_start_y = map_height + 1
        self.renderer.draw_text(0, status_start_y, "-" * MAP_WIDTH, "dark_grey")
        
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

        # 4-2. 인벤토리 (Inventory)
        inv_start_y = 10
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, inv_start_y, "[ INVENTORY ]", "gold")
        # TODO: 실제 인벤토리 데이터 연동 (현재는 플레이어 인벤토리 컴포넌트 접근 필요)
        # 지금은 임시로 표시
        inv_y = inv_start_y + 1
        if player_entity and hasattr(player_entity, 'components'):
             # InventoryComponent가 있는지 확인해야 함. currently player_entity returns Entity object.
             # but to be safe and quick, just showing placeholder if logic complex
             # Let's try to get InventoryComponent if defined in comments above
             # The initialization added InventoryComponent
             from .components import InventoryComponent # Lazy import to avoid circular checks if top level issues
             inv_comp = player_entity.get_component(InventoryComponent)
             if inv_comp:
                 items = inv_comp.items
                 if not items:
                     self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, inv_y, "Empty", "dark_grey")
                 else:
                     count = 0
                     for item_id, item_data in items.items():
                         if count >= 8: break # 최대 8개
                         name = item_data['item'].name
                         qty = item_data['qty']
                         self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, inv_y + count, f"- {name} x{qty}", "white")
                         count += 1

        # 4-3. 스킬 리스트 (Skill List)
        skill_start_y = 20
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y, "[ SKILLS ]", "gold")
        # Placeholder for skills
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y + 1, "- Basic Attack", "white")

        # 5. 입력 가이드 (Bottom fixed)
        guide_y = self.renderer.height - 1
        self.renderer.draw_text(0, guide_y, " [MOVE] WASD/Arrows | [I] Inventory | [Q] Quit", "green")
        
        # 6. 인벤토리 팝업 렌더링 (INVENTORY 상태일 때만)
        if self.state == GameState.INVENTORY:
            self._render_inventory_popup()

        self.renderer.render()

    def _render_inventory_popup(self):
        """항목 목록을 보여주는 중앙 팝업창 렌더링"""
        POPUP_WIDTH = 40
        POPUP_HEIGHT = 20
        start_x = (self.renderer.width - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. 배경 및 테두리 그리기
        for y in range(start_y, start_y + POPUP_HEIGHT):
            for x in range(start_x, start_x + POPUP_WIDTH):
                if y == start_y or y == start_y + POPUP_HEIGHT - 1:
                    char = "-"
                elif x == start_x or x == start_x + POPUP_WIDTH - 1:
                    char = "|"
                else:
                    char = " " # 배경 공백 지우기
                self.renderer.draw_char(x, y, char, "white")
                
        # 2. 제목
        title = "[ INVENTORY ]"
        title_x = start_x + (POPUP_WIDTH - len(title)) // 2
        self.renderer.draw_text(title_x, start_y + 1, title, "yellow")
        
        # 3. 아이템 목록 표시
        player_entity = self.world.get_player_entity()
        if player_entity:
             from .components import InventoryComponent
             inv_comp = player_entity.get_component(InventoryComponent)
             
             if inv_comp and inv_comp.items:
                 current_y = start_y + 3
                 idx = 0
                 for item_id, item_data in inv_comp.items.items():
                     if current_y >= start_y + POPUP_HEIGHT - 2: break
                     
                     name = item_data['item'].name
                     qty = item_data['qty']
                     prefix = "> " if idx == self.selected_item_index else "  "
                     color = "green" if idx == self.selected_item_index else "white"
                     
                     self.renderer.draw_text(start_x + 2, current_y, f"{prefix}{name} x{qty}", color)
                     current_y += 1
                     idx += 1
             else:
                 self.renderer.draw_text(start_x + 2, start_y + 3, "  (Empty)", "dark_grey")
        
        # 4. 하단 도움말
        self.renderer.draw_text(start_x + 2, start_y + POPUP_HEIGHT - 2, "[ESC/I] Close", "dark_grey")

if __name__ == '__main__':
    engine = Engine()
    engine.run()
