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

def start_game(ui, player_name: str, new_game=False, game_state_data=None, class_data=None):
    """새 게임 또는 이어하기를 시작합니다."""

    if new_game or not game_state_data:
        # 새 게임 시작 전 기존 같은 이름의 데이터가 있는지 확인 (선택적)
        # 여기서는 단순히 덮어쓰거나 무시

        player_instance = Player(name=player_name)
        # 새 게임 시작 시 초기 게임 상태 데이터 생성 (ECS 컴포넌트 포함)
        initial_game_state = {
            "entities": {
                "1": {
                    "PositionComponent": {'x': 0, 'y': 0, 'map_id': "1F"},
                    "MovableComponent": {},
                    # StatsComponent는 Engine._initialize_world에서 class_data를 기반으로 생성됨
                    # InventoryComponent도 Engine._initialize_world에서 시작 아이템과 함께 생성됨
                    "NameComponent": {'name': player_name},
                }
            },
            "player_specific_data": player_instance.to_dict(),
            "dungeon_maps": {},
            "selected_class": class_data.class_id if class_data else None
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
    game_result = game_engine.run(ui)
    
    if game_result == "DEATH":
        ui.show_death_screen()
        # 저장 파일 삭제
        delete_save_data(player_name)
    elif game_result == "MENU":
        # 메인 메뉴로 복귀 (게임 저장)
        return "MENU"
    
    return game_result


def main_menu():
    """메인 메뉴 표시 및 선택 처리"""
    ui = ConsoleUI()
    
    while True:
        lang_choice = ui.show_language_selection()
        if lang_choice == 2: # Exit
             break
        
        from dungeon import config
        config.LANGUAGE = "ko" if lang_choice == 0 else "en"
        
        while True:  # 메인 메뉴 루프
            choice = ui.show_main_menu()  # Returns 0, 1, or 2
            
            if choice == 0:  # 새 게임
                # 직업 선택
                from dungeon.data_manager import load_class_definitions
                class_defs = load_class_definitions()
                selected_class = ui.show_class_selection(class_defs)
                if not selected_class:
                    continue  # 취소 시 메인 메뉴로
                
                # 이름 입력 루프
                while True:
                    player_name = ui.get_player_name()
                    if not player_name:
                        break  # 취소 시 메인 메뉴로 (inner loop break -> outer loop continue)
                    
                    # [Check Overwrite]
                    from dungeon.data_manager import list_save_files
                    existing_saves = list_save_files()
                    if player_name in existing_saves:
                        confirm = ui.show_confirmation_dialog(f"'{player_name}' 파일이 이미 존재합니다. 덮어쓰시겠습니까?")
                        if not confirm:
                            continue # 다시 이름 입력 받음
                    
                    result = start_game(ui, player_name, new_game=True, class_data=selected_class)
                    if result == "QUIT":
                        # return # 전체 종료가 아니라 언어 선택 화면으로? 아니면 그냥 종료?
                        # 보통 QUIT는 완전 종료
                        return 
                    
                    break # 메인 메뉴로 복귀 (start_game returned MENU or DEATH handled inside)
                
                if 'result' in locals() and result == "QUIT":
                     return

            elif choice == 1:  # 이어하기
                while True:
                    from dungeon.data_manager import list_save_files
                    save_files = list_save_files()
                    action, selected_name = ui.show_save_list(save_files)
                    
                    if action == "LOAD":
                        game_state_data = load_game_data(selected_name)
                        if game_state_data:
                            result = start_game(ui, selected_name, new_game=False, game_state_data=game_state_data)
                            if result == "QUIT":
                                return
                            break # Main Menu (MENU, DEATH)
                        else:
                            ui.add_message(f"오류: {selected_name} 파일을 로드할 수 없습니다. (데이터 손상 가능성)")
                            ui._clear_screen()
                            print(f"\n  [오류] {selected_name} 파일을 로드하는 중 문제가 발생했습니다.")
                            print("  데이터가 손상되었거나 형식이 맞지 않습니다.")
                            print("\n  아무 키나 눌러 목록으로 돌아갑니다.")
                            ui.get_key_input()
                    elif action == "DELETE":
                        delete_save_data(selected_name)
                        # Loop continues, refreshing list
                    else:
                        break # Back to Main Menu
            
            elif choice == 2:  # 언어 선택으로 돌아가기 (이전엔 게임 종료였으나, 계층 구조상 위로 올라감)
                break
    
    # del ui

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