# Start.py

import os
import json
import sys
import shutil
import logging # 로깅 모듈 임포트

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='game_debug.log',
    filemode='w'
)

from dungeon import engine
from dungeon.player import Player
from dungeon.map import DungeonMap
from dungeon.data_manager import (
    load_item_definitions, get_item_definition, load_skill_definitions,
    save_game_data, load_game_data, delete_save_data
)
from dungeon.ui import ConsoleUI

# --- 데이터 로드 ---
ITEM_DEFINITIONS = load_item_definitions()
SKILL_DEFINITIONS = load_skill_definitions()

def start_game(ui, player_name: str, new_game=False):
    """새 게임 또는 이어하기를 시작합니다."""
    game_state_data = None

    if not new_game:
        game_state_data = load_game_data()

    if new_game or not game_state_data:
        if new_game and game_state_data:
            delete_save_data() # 새 게임 선택 시 기존 데이터 삭제

        ui.add_message(f"디버그: 플레이어 이름 입력됨 - {player_name}")
        player_instance = Player(name=player_name)
        # 새 게임 시작 시 초기 게임 상태 데이터 생성 (ECS 컴포넌트 포함)
        initial_game_state = {
            "entities": {
                player_instance.entity_id: {
                    "PositionComponent": {'x': 0, 'y': 0, 'map_id': "1F"},
                    "MovableComponent": {},
                    "StatsComponent": {
                        'max_hp': 100, 
                        'current_hp': 100, 
                        'attack': 10,
                        'defense': 5,
                        'max_mp': 50,
                        'current_mp': 50,
                        'max_stamina': 100,
                        'current_stamina': 100
                    },
                    "NameComponent": {'name': player_name},
                    "InventoryComponent": {'items': {}, 'equipped': {}},
                }
            },
            "player_specific_data": player_instance.to_dict(),
            "dungeon_maps": {}
        }
        game_state_data = initial_game_state
        ui.add_message(f"{player_name}, 던전에 온 것을 환영하네.")

    ui_instance = ui
    ui.add_message("디버그: 게임 엔진 시작 전...")
    
    # Engine 인스턴스 생성 및 실행
    # game_state_data를 전달하여 로드된 데이터(또는 초기 데이터)로 시작
    game_engine = engine.Engine(player_name, game_state_data)
    game_engine.run()
    
    ui.add_message("디버그: 게임 엔진 종료 후.")
    
    # TODO: 게임 종료 코드를 Engine에서 반환받는 로직 추가 필요
    game_result = "QUIT" 

    
    if game_result == "DEATH":
        delete_save_data()
        ui.show_game_over_screen("당신은 죽었습니다!")


def main_menu():
    """메인 메뉴를 표시하고 사용자 입력을 처리합니다."""
    ui = ConsoleUI()
    while True:
        choice = ui.show_main_menu()
        if choice == 0: # 새 게임
            player_name = ui.get_player_name()
            start_game(ui, player_name, new_game=True)
        elif choice == 1: # 이어하기
            player_name = ui.get_player_name() # 이어하기 시에도 플레이어 이름 필요
            if not load_game_data():
                ui.add_message("저장된 게임이 없습니다. 새 게임을 시작합니다.")
                start_game(ui, player_name, new_game=True)
            else:
                start_game(ui, player_name, new_game=False)
        elif choice == 2: # 게임 종료
            break
    del ui

if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        # 예외 발생 시 터미널 상태를 복구하고 에러 메시지 출력
        sys.stdout.write("\033[?25h") # Show cursor directly using code
        sys.stdout.write("\033[0m")
        shutil.os.system('clear')
        print("치명적인 오류 발생:", e)
        import traceback
        traceback.print_exc()