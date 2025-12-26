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

def start_game(ui, player_name: str, new_game=False, game_state_data=None):
    """새 게임 또는 이어하기를 시작합니다."""

    if new_game or not game_state_data:
        # 새 게임 시작 전 기존 같은 이름의 데이터가 있는지 확인 (선택적)
        # 여기서는 단순히 덮어쓰거나 무시

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
                        'max_stamina': 100,\
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
    else: # 저장된 게임을 로드한 경우
        # 저장된 데이터에서 플레이어 이름을 추출하여 사용
        player_name = game_state_data["player_specific_data"]["name"]
        ui.add_message(f"{player_name}님, 다시 던전으로 돌아오신 것을 환영합니다!")

    ui_instance = ui
    
    # Engine 인스턴스 생성 및 실행
    # game_state_data를 전달하여 로드된 데이터(또는 초기 데이터)로 시작
    game_engine = engine.Engine(player_name, game_state_data)
    game_result = game_engine.run()
    
    if game_result == "DEATH":
        delete_save_data(player_name)
        ui.show_game_over_screen("당신은 던전에서 장렬히 전사했습니다...")


def main_menu():
    """메인 메뉴를 표시하고 사용자 입력을 처리합니다."""
    ui = ConsoleUI()
    while True:
        choice = ui.show_main_menu()
        if choice == 0: # 새 게임
            player_name = ui.get_player_name()
            start_game(ui, player_name, new_game=True)
        elif choice == 1: # 이어하기
            from dungeon.data_manager import list_save_files
            save_files = list_save_files()
            
            action, selected_name = ui.show_save_list(save_files)
            if action == "LOAD":
                game_state_data = load_game_data(selected_name)
                if game_state_data:
                    start_game(ui, selected_name, new_game=False, game_state_data=game_state_data)
                else:
                    ui.add_message("파일 로드에 실패했습니다.")
            elif action == "DELETE":
                delete_save_data(selected_name)
                ui.add_message(f"{selected_name}의 저장 데이터를 삭제했습니다.")
            # action이 None이면 다시 루프로 돌아감
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