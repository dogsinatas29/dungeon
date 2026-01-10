#!/usr/bin/env python3
import os
import sys
import logging
import json
import readchar
import shutil
from . import config
from .ui import ConsoleUI, COLOR_MAP
from .engine import Engine
from .data_manager import load_class_definitions
from .localization import _

def select_language(ui):
    ui._clear_screen()
    terminal_width = shutil.get_terminal_size().columns
    
    # ANSI escape code for centering text roughly
    lines = [
        "========================================",
        "      Select Language / 언어 선택       ",
        "========================================",
        "",
        "  1. 한국어 (Korean)",
        "  2. English",
        "",
        "========================================"
    ]
    
    for line in lines:
        padding = (terminal_width - len(line)) // 2
        print(f"{COLOR_MAP['yellow']}{' ' * padding}{line}{COLOR_MAP['reset']}")
        
    while True:
        key = readchar.readkey()
        if key == '1':
            return "ko"
        elif key == '2':
            return "en"

def main():
    # 로깅 설정
    logging.basicConfig(filename='game_debug.log', level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    ui = ConsoleUI()
    
    # 1. 게임 시작 시 언어 선택
    selected_lang = select_language(ui)
    config.LANGUAGE = selected_lang
    
    # 클래스 정의 미리 로드 (직업 선택용) - 언어 설정 후에 로드해야 함
    class_defs = load_class_definitions()
    
    while True:
        choice = ui.show_main_menu()
        
        if choice == 0: # New Game
            # 캐릭터 생성
            player_name = ui.get_player_name()
            class_id = ui.show_class_selection(class_defs)
            
            if class_id:
                # Engine 초기화 및 실행
                engine = Engine(player_name=player_name, game_data={"selected_class": class_id})
                engine.run(ui)
        
        elif choice == 1: # Load Game
            save_dir = os.path.join(os.path.dirname(__file__), "game_data")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            save_files = [f for f in os.listdir(save_dir) if f.endswith(".json")]
            
            action, filename = ui.show_save_list(save_files)
            
            if action == "LOAD":
                save_path = os.path.join(save_dir, filename)
                try:
                    with open(save_path, "r", encoding="utf-8") as f:
                        save_data = json.load(f)
                    engine = Engine(game_data=save_data)
                    engine.run(ui)
                except Exception as e:
                    logging.error(f"Failed to load save file {filename}: {e}")
            elif action == "DELETE":
                save_path = os.path.join(save_dir, filename)
                if ui.show_confirmation_dialog(_("정말로 삭제하시겠습니까?")):
                    try:
                        os.remove(save_path)
                    except Exception as e:
                        logging.error(f"Failed to delete save file {filename}: {e}")
                
        elif choice == 2: # Exit
            sys.exit(0)

if __name__ == "__main__":
    main()
