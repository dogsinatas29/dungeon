# dungeon/engine.py - 게임의 실행 흐름을 관리하는 메인 모듈

import os
import time
import random
import readchar # readchar 임포트 추가
from typing import List, Dict, Tuple, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import PositionComponent, RenderComponent, MapComponent, MonsterComponent, MessageComponent, StatsComponent, LevelComponent
from .systems import InputSystem, MovementSystem, RenderSystem 
from .renderer import Renderer



class Engine:
    """게임 루프, 초기화, 시스템 관리를 담당하는 메인 클래스"""
    def __init__(self, player_name="Hero", game_data=None):
        self.is_running = False
        self.world = World(self) # World 초기화 시 Engine 자신을 참조
        self.turn_number = 0
        self.player_name = player_name

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
            self.turn_number += 1
            
            # 1. 사용자 입력 처리
            action = self._get_input()
            
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
                
                # time.sleep(0.1) # 필요하다면 딜레이 추가
                
        print("--- 게임 종료 ---")

    def _render(self):
        """World 상태를 기반으로 Renderer를 사용하여 화면을 그립니다."""
        self.renderer.clear_buffer()
        
        # 1. 맵 렌더링
        map_comp_list = self.world.get_entities_with_components({MapComponent})
        if map_comp_list:
            map_comp = map_comp_list[0].get_component(MapComponent)
            for y, row in enumerate(map_comp.tiles):
                for x, char in enumerate(row):
                    # 맵 타일 색상은 단순하게 처리 (추후 개선 가능)
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
            
            self.renderer.draw_char(pos.x, pos.y, render.char, render.color)

        # 3. 메시지 로그 렌더링
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        y_offset = (map_comp_list[0].get_component(MapComponent).height if map_comp_list else 10)
        
        # 구분선
        self.renderer.draw_text(0, y_offset, "-" * 80, "dark_grey")
        current_y = y_offset + 1

        # 4. 스탯 패널 렌더링 (플레이어 정보)
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats:
                # LINE 1: HP, MP, STAMINA
                hp_str = f"HP: {stats.current_hp}/{stats.max_hp}"
                mp_str = f"MP: {stats.current_mp}/{stats.max_mp}"
                stm_str = f"STM: {int(stats.current_stamina)}/{int(stats.max_stamina)}"
                
                self.renderer.draw_text(2, current_y, f"{hp_str} | {mp_str} | {stm_str}", "white")
                current_y += 1
                
                # LINE 2: LV, EXP, JOB
                level_comp = player_entity.get_component(LevelComponent)
                if level_comp:
                    lv_str = f"LV: {level_comp.level}"
                    exp_str = f"EXP: {level_comp.exp}/{level_comp.exp_to_next}"
                    job_str = f"Job: {level_comp.job}"
                    
                    self.renderer.draw_text(2, current_y, f"{lv_str} | {exp_str} | {job_str}", "white")
                else:
                    self.renderer.draw_text(2, current_y, "LV: 1 | EXP: 0/100 | Job: Unknown", "white")
                
                current_y += 1

        # 5. 메시지 로그 (최근 3개만 표시)
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            for i, msg in enumerate(message_comp.messages[-3:]):
                self.renderer.draw_text(0, current_y + i, f"> {msg}", "grey")
        
        # 6. 입력 가이드
        guide_y = self.renderer.height - 1
        self.renderer.draw_text(0, guide_y, "[Move] Arrow Keys/WASD | [Q] Quit", "green")

        self.renderer.render()

if __name__ == '__main__':
    engine = Engine()
    engine.run()
