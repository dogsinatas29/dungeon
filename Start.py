# Start.py

import os
import json
import sys
import shutil
import readchar
from player import Player
from dungeon_map import DungeonMap
from data_manager import load_item_definitions, get_item_definition
from ui import UI, ANSI, pad_str_to_width # pad_str_to_width 임포트 추가

# 게임 데이터 저장 경로
SAVE_DIR = "game_data"
PLAYER_SAVE_FILE = os.path.join(SAVE_DIR, "player_data.json")
DUNGEON_MAPS_SAVE_FILE = os.path.join(SAVE_DIR, "all_dungeon_maps.json")

# 아이템 정의 로드 (게임 시작 시 한 번만 로드)
ITEM_DEFINITIONS = {}

def create_save_directory():
    """게임 데이터를 저장할 디렉토리를 생성합니다."""
    os.makedirs(SAVE_DIR, exist_ok=True)

def save_game_data(player, all_dungeon_maps, ui_instance):
    """플레이어와 모든 던전 맵 데이터를 저장합니다."""
    with open(PLAYER_SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(player.to_dict(), f, ensure_ascii=False, indent=4)
    
    serializable_dungeon_maps = {f"{level[0]},{level[1]}": d_map.to_dict() for level, d_map in all_dungeon_maps.items()}
    with open(DUNGEON_MAPS_SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_dungeon_maps, f, ensure_ascii=False, indent=4)
    
    ui_instance.add_message("게임 데이터가 성공적으로 저장되었습니다.")

def load_game_data(ui_instance):
    """저장된 플레이어와 모든 던전 맵 데이터를 로드합니다."""
    if not os.path.exists(PLAYER_SAVE_FILE):
        return None, None

    try:
        with open(PLAYER_SAVE_FILE, 'r', encoding='utf-8') as f:
            player_data = json.load(f)
        
        with open(DUNGEON_MAPS_SAVE_FILE, 'r', encoding='utf-8') as f:
            all_dungeon_maps_data = json.load(f)

        return player_data, all_dungeon_maps_data
    except (json.JSONDecodeError, FileNotFoundError):
        return None, None

def create_new_game(ui_instance):
    """새 게임을 시작하고 플레이어 이름을 입력받습니다."""
    ui_instance.clear_screen()
    
    prompt_y = ui_instance.terminal_height // 2
    prompt_x = ui_instance.terminal_width // 2 - 15
    
    sys.stdout.write(ANSI.cursor_to(prompt_y - 2, prompt_x) + "=== 새 게임 시작 ===")
    
    name = get_line_input(ui_instance, prompt_y, prompt_x, "플레이어 이름을 입력하세요: ")


    if not name:
        name = "용사"

    player_data = Player(name, 100, 50).to_dict()
    return player_data, {}

def get_line_input(ui_instance, prompt_y, prompt_x, prompt_text):
    """한 줄 입력을 받습니다."""
    sys.stdout.write(ANSI.cursor_to(prompt_y, prompt_x) + prompt_text)
    sys.stdout.write(ANSI.SHOW_CURSOR)
    sys.stdout.flush()

    input_string = ""
    input_start_x = prompt_x + len(prompt_text)
    
    while True:
        key = readchar.readkey()
        if key == readchar.key.ENTER:
            break
        elif key == readchar.key.BACKSPACE:
            input_string = input_string[:-1]
        elif len(key) == 1:
            input_string += key
        
        sys.stdout.write(ANSI.cursor_to(prompt_y, input_start_x) + " " * 20)
        sys.stdout.write(ANSI.cursor_to(prompt_y, input_start_x) + input_string)
        sys.stdout.flush()

    sys.stdout.write(ANSI.HIDE_CURSOR)
    return input_string.strip()

def start_game(ui_instance, new_game=False):
    """게임을 시작합니다."""
    global ITEM_DEFINITIONS
    if not ITEM_DEFINITIONS:
        ITEM_DEFINITIONS = load_item_definitions(ui_instance)

    if new_game:
        if os.path.exists(SAVE_DIR):
            shutil.rmtree(SAVE_DIR)
        create_save_directory()
        player_data, all_dungeon_maps_data = create_new_game(ui_instance)
    else:
        player_data, all_dungeon_maps_data = load_game_data(ui_instance)
        if not player_data:
            ui_instance.clear_screen()
            msg = "저장된 게임이 없습니다!"
            sys.stdout.write(ANSI.cursor_to(ui_instance.terminal_height // 2, ui_instance.terminal_width // 2 - len(msg) // 2) + msg)
            sys.stdout.flush()
            readchar.readkey()
            return

    import game
    game.run_game(player_data, all_dungeon_maps_data, ITEM_DEFINITIONS, ui_instance)

def main_menu():
    """메인 메뉴를 표시하고 사용자 입력을 처리합니다."""
    ui = UI()
    while True:
        ui.clear_screen()
        
        menu_items = [
            "=== 던전 탐험 게임 ===",
            "",
            "1. 새 게임",
            "2. 이어하기",
            "3. 종료",
        ]
        
        start_y = ui.terminal_height // 2 - len(menu_items) // 2
        
        for i, item in enumerate(menu_items):
            # pad_str_to_width를 사용하여 중앙 정렬
            padded_item = pad_str_to_width(item, ui.terminal_width, align='center')
            sys.stdout.write(ANSI.cursor_to(start_y + i, 0) + padded_item)

        prompt = "선택: "
        sys.stdout.write(ANSI.cursor_to(start_y + len(menu_items) + 1, ui.terminal_width // 2 - len(prompt) // 2) + prompt)
        sys.stdout.flush()
        
        choice = readchar.readkey()
        
        if choice == '1':
            start_game(ui, new_game=True)
        elif choice == '2':
            start_game(ui, new_game=False)
        elif choice == '3':
            ui.clear_screen()
            sys.stdout.write(ANSI.SHOW_CURSOR)
            sys.exit()


if __name__ == "__main__":
    create_save_directory()
    try:
        main_menu()
    except Exception as e:
        sys.stdout.write(ANSI.SHOW_CURSOR) # 오류 발생 시 커서 보이게 함
        sys.stdout.flush()
        print(f"\n치명적인 오류 발생: {e}")
        import traceback
        traceback.print_exc()

