# dungeon/engine.py - 게임의 실행 흐름을 관리하는 메인 모듈

import os
import time
from typing import List, Dict, Tuple, Any

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import PositionComponent, RenderComponent, MapComponent, MonsterComponent, MessageComponent
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
        
        # 맵 데이터 (임시)
        # 중요: 플레이어('@')와 몬스터('g')의 위치는 '.'으로 비워둡니다.
        map_data = [
            "##########",
            "#........#",
            "#........#", # <--- Y=2: 플레이어 시작 위치 (X=2) 포함. 이전 줄 길이 오류 수정.
            "#.###..#.#",
            "#... ...#.#", # <--- Y=4: 몬스터 위치 (X=4) 포함. (기존 '#...g..#.#')
            "#......#.#",
            "#........#",
            "##########",
        ]
        
        # 몬스터 위치도 맵 데이터에서 제거했습니다.
        
        width = len(map_data[0])
        height = len(map_data)
        
        # 맵 데이터의 문자열 리스트를 타일 리스트로 변환 (엔티티 없이 깨끗한 맵)
        map_tiles = [list(row) for row in map_data]

        # 1. 플레이어 엔티티 생성 (ID=1)
        player_x, player_y = 2, 2 # 의도된 초기 위치 (2, 2)
        player_entity = self.world.create_entity() 
        self.world.add_component(player_entity.entity_id, PositionComponent(x=player_x, y=player_y))
        self.world.add_component(player_entity.entity_id, RenderComponent(char='@', color='yellow'))
        
        # 2. 맵 엔티티 생성 (ID=2)
        map_entity = self.world.create_entity()
        map_component = MapComponent(width=width, height=height, tiles=map_tiles) 
        self.world.add_component(map_entity.entity_id, map_component)
        
        # 3. 메시지 로그 엔티티 생성 (ID=3)
        message_entity = self.world.create_entity()
        self.world.add_component(message_entity.entity_id, MessageComponent())
        
        # 4. 몬스터 엔티티 생성 (ID=4)
        monster_x, monster_y = 4, 4 # 맵 데이터의 몬스터 위치
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
        """사용자 입력을 받아 반환"""
        return input("이동 (w/a/s/d) 또는 q 종료: ").strip().lower()

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
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            y_offset = (map_comp_list[0].get_component(MapComponent).height if map_comp_list else 10) + 1
            
            self.renderer.draw_text(0, y_offset, "--- Messages ---", "blue")
            for i, msg in enumerate(message_comp.messages[-5:]):
                self.renderer.draw_text(0, y_offset + 1 + i, f"> {msg}", "white")

        self.renderer.render()

if __name__ == '__main__':
    engine = Engine()
    engine.run()
