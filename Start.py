# Start.py

import os
import json
import sys
import shutil
import readchar
from player import Player
from dungeon_map import DungeonMap
from data_manager import load_item_definitions, get_item_definition
from ui import UI, ANSI # UI 클래스 임포트

# 게임 데이터 저장 경로
SAVE_DIR = "game_data"
PLAYER_SAVE_FILE = os.path.join(SAVE_DIR, "player_data.json")
DUNGEON_MAPS_SAVE_FILE = os.path.join(SAVE_DIR, "all_dungeon_maps.json")

# 아이템 정의 로드 (게임 시작 시 한 번만 로드)
ITEM_DEFINITIONS = {}

def create_save_directory():
    """게임 데이터를 저장할 디렉토리를 생성합니다."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    print(f"DEBUG (Console): Save directory '{SAVE_DIR}' ensured to exist.")

def save_game_data(player, all_dungeon_maps, ui_instance):
    """플레이어와 모든 던전 맵 데이터를 저장합니다."""
    with open(PLAYER_SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(player.to_dict(), f, ensure_ascii=False, indent=4)
    
    serializable_dungeon_maps = {f"{level[0]},{level[1]}": d_map.to_dict() for level, d_map in all_dungeon_maps.items()}
    with open(DUNGEON_MAPS_SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_dungeon_maps, f, ensure_ascii=False, indent=4)
    
    ui_instance.add_message(f"DEBUG (Console): 게임 데이터가 성공적으로 저장되었습니다.")

def load_game_data(ui_instance):
    """저장된 플레이어와 모든 던전 맵 데이터를 로드합니다."""
    if not os.path.exists(SAVE_DIR) or \
       not os.path.exists(PLAYER_SAVE_FILE) or \
       not os.path.exists(DUNGEON_MAPS_SAVE_FILE):
        ui_instance.add_message(f"DEBUG (Console): 저장된 게임 파일이 없거나 디렉토리가 존재하지 않습니다.")
        return None, None

    try:
        with open(PLAYER_SAVE_FILE, 'r', encoding='utf-8') as f:
            player_data = json.load(f)
        
        with open(DUNGEON_MAPS_SAVE_FILE, 'r', encoding='utf-8') as f:
            all_dungeon_maps_data = json.load(f)

        ui_instance.add_message(f"DEBUG (Console): 게임 데이터를 성공적으로 불러왔습니다.")
        return player_data, all_dungeon_maps_data
    except json.JSONDecodeError as e:
        ui_instance.add_message(f"DEBUG (Console): 저장된 파일이 손상되었습니다. 새 게임을 시작합니다. 오류: {e}")
        return None, None
    except Exception as e:
        ui_instance.add_message(f"DEBUG (Console): 게임 로드 중 알 수 없는 오류 발생: {e}. 새 게임을 시작합니다.")
        return None, None

def get_line_input(ui_instance, prompt_y, prompt_x, prompt_text):
    """
    사용자로부터 한 줄 입력을 받습니다. readchar를 사용하여 문자별로 처리하고,
    입력 내용을 터미널에 직접 출력하여 즉각적인 피드백을 제공합니다.
    """
    # 프롬프트 텍스트 출력
    sys.stdout.write(ANSI.cursor_to(prompt_x, prompt_y) + prompt_text)
    
    # 입력 필드 시작 위치 및 너비 계산
    input_start_x = prompt_x + len(prompt_text)
    input_width = ui_instance.terminal_width - input_start_x - 1
    
    sys.stdout.write(ANSI.SHOW_CURSOR) # 커서 표시
    sys.stdout.flush() # 즉시 화면에 반영

    input_string = ""
    while True:
        # 현재 입력된 문자열을 화면에 표시 (이전 내용 지우고 다시 그림)
        sys.stdout.write(ANSI.cursor_to(input_start_x, prompt_y) + " " * input_width) # 입력 영역 초기화
        sys.stdout.write(ANSI.cursor_to(input_start_x, prompt_y) + input_string) # 입력 내용 출력
        sys.stdout.flush() # 즉시 화면에 반영

        key = readchar.readkey()

        if key == readchar.key.ENTER or key == '\r' or key == '\n': # Enter 키
            break
        elif key == readchar.key.BACKSPACE or key == '\x7f': # 백스페이스 키
            if input_string:
                input_string = input_string[:-1]
        elif key == readchar.key.CTRL_C: # Ctrl+C (강제 종료)
            raise KeyboardInterrupt
        elif len(key) == 1 and key.isprintable(): # 출력 가능한 단일 문자만 허용
            # 터미널 너비를 초과하지 않도록 제한
            if len(input_string) < input_width:
                input_string += key
    
    sys.stdout.write(ANSI.HIDE_CURSOR) # 입력 완료 후 커서 숨기기
    sys.stdout.flush() # 즉시 화면에 반영

    # 입력 완료 후 입력 라인 지우기 (선택 사항: 지우지 않으면 입력 내용이 화면에 남음)
    sys.stdout.write(ANSI.cursor_to(prompt_x, prompt_y) + " " * (ui_instance.terminal_width - prompt_x))
    sys.stdout.flush()

    return input_string.strip()

# create_new_game 함수에 ui_instance 인자 추가
def create_new_game(ui_instance):
    """새 게임을 시작하고 플레이어 이름을 입력받습니다."""
    ui_instance.clear_screen() # 새 게임 화면을 위해 화면을 지웁니다.
    
    prompt_y = ui_instance.terminal_height // 2
    prompt_x = ui_instance.terminal_width // 2 - 15 # 중앙 정렬을 위한 x 좌표 조정
    
    # "새 게임 시작" 메시지를 직접 터미널에 출력
    ui_instance.print_at(prompt_y - 2, prompt_x, "=== 새 게임 시작 ===")

    # get_line_input 함수를 사용하여 플레이어 이름을 입력받습니다.
    name = get_line_input(ui_instance, prompt_y, prompt_x, "플레이어 이름을 입력하세요: ")

    if not name: # 이름이 비어있으면 기본값 설정
        name = "Player"

    player_data = Player(name, 100, 50).to_dict()
    all_dungeon_maps_data = {} # 새 게임이므로 맵 데이터는 비어있습니다.

    return player_data, all_dungeon_maps_data

# start_game 함수에 ui_instance 인자 추가
def start_game(ui_instance):
    """게임 플레이를 시작하거나 불러옵니다."""
    global ITEM_DEFINITIONS
    if not ITEM_DEFINITIONS:
        ITEM_DEFINITIONS = load_item_definitions(ui_instance)
        if not ITEM_DEFINITIONS:
            ui_instance.add_message("치명적 오류: 아이템 정의를 로드할 수 없습니다. 게임을 종료합니다.")
            sys.exit(1)

    player_data, all_dungeon_maps_data = load_game_data(ui_instance)

    if player_data:
        ui_instance.clear_screen()
        # "게임 로드됨" 메시지를 직접 터미널에 출력
        ui_instance.print_at(ui_instance.terminal_width // 2 - 10, ui_instance.terminal_height // 2 - 1, "게임 로드됨")
        ui_instance.print_at(ui_instance.terminal_width // 2 - 10, ui_instance.terminal_height // 2, "계속하려면 아무 키나 누르세요...")
        sys.stdout.flush() # 즉시 화면에 반영
        readchar.readkey()
        ui_instance.clear_screen()
    else:
        # 새 게임 시작 로직 (create_new_game은 자체적으로 화면을 지움)
        player_data, all_dungeon_maps_data = create_new_game(ui_instance) # ui_instance 전달

    # game.run_game으로 게임 시작 (ui_instance 전달)
    import game # 여기에 game 모듈을 다시 임포트하여 NameError 방지
    game_result = game.run_game(player_data, all_dungeon_maps_data, ITEM_DEFINITIONS, ui_instance)

    # 게임 종료 후 메시지 출력 (동일 UI 인스턴스 사용)
    ui_instance.clear_screen()
    exit_message_y = ui_instance.terminal_height // 2
    exit_message_x = ui_instance.terminal_width // 2 - 5
    if game_result == "QUIT":
        ui_instance.print_at(exit_message_y, exit_message_x, "게임 종료")
    elif game_result == "DEATH":
        ui_instance.print_at(exit_message_y, exit_message_x, "당신은 죽었습니다!")
    sys.stdout.flush() # 즉시 화면에 반영

    sys.stdout.write(ANSI.SHOW_CURSOR) # 커서 다시 보이게 함
    sys.stdout.flush()
    readchar.readkey()
    ui_instance.clear_screen()


def main_menu():
    """메인 메뉴를 표시하고 사용자 입력을 처리합니다."""
    ui = UI() # 메인 메뉴를 위한 단 하나의 UI 인스턴스 생성
    while True:
        ui.clear_screen() # 매 메뉴 표시 전에 화면을 지웁니다.
        
        # 메뉴 텍스트를 UI 버퍼에 그리는 대신, 직접 터미널에 출력합니다.
        menu_items = [
            "=== 던전 탐험 게임 ===",
            "",
            "1. 새 게임 시작",
            "2. 게임 불러오기",
            "3. 게임 종료",
            "",
            "선택: "
        ]
        
        start_y = ui.terminal_height // 2 - 4
        start_x = ui.terminal_width // 2 - 10
        
        for i, line in enumerate(menu_items):
            sys.stdout.write(ANSI.cursor_to(start_x, start_y + i) + line.ljust(ui.terminal_width - start_x))
        sys.stdout.flush() # 메뉴를 즉시 화면에 출력

        # 커서를 선택 입력 위치로 이동
        input_prompt_y = start_y + len(menu_items) - 1 # "선택: " 줄의 y 좌표
        input_prompt_x = start_x + len(menu_items[-1]) # "선택: " 텍스트 이후의 x 좌표
        sys.stdout.write(ANSI.cursor_to(input_prompt_x, input_prompt_y))
        sys.stdout.flush() # 커서 이동을 즉시 반영
        
        choice = readchar.readkey() # 단일 키 입력 받기
        
        if choice == '1':
            # 새 게임 시작 시 기존 저장 데이터 삭제
            if os.path.exists(SAVE_DIR):
                shutil.rmtree(SAVE_DIR)
                ui.add_message(f"DEBUG (Console): 기존 저장 디렉토리 '{SAVE_DIR}' 삭제됨.")
            create_save_directory() # 새 디렉토리 생성
            start_game(ui) # ui 인스턴스 전달
        elif choice == '2':
            global ITEM_DEFINITIONS
            if not ITEM_DEFINITIONS:
                ITEM_DEFINITIONS = load_item_definitions(ui)
                if not ITEM_DEFINITIONS:
                    # 오류 메시지를 메시지 로그에 추가 후 메시지 로그만 다시 그리기
                    ui.add_message("오류: 아이템 정의를 로드할 수 없습니다. 게임을 시작할 수 없습니다.")
                    ui.draw_message_log() # 메시지 로그만 업데이트
                    readchar.readkey() # 메시지를 볼 수 있도록 대기
                    continue

            player_data, all_dungeon_maps_data = load_game_data(ui)
            if player_data:
                import game # 여기에 game 모듈을 다시 임포트하여 NameError 방지
                game.run_game(player_data, all_dungeon_maps_data, ITEM_DEFINITIONS, ui) # ui 인스턴스 전달
            else:
                ui.clear_screen()
                # "저장된 게임이 없습니다!" 메시지를 직접 터미널에 출력
                ui.print_at(ui.terminal_height // 2, ui.terminal_width // 2 - 10, "저장된 게임이 없습니다!")
                ui.print_at(ui.terminal_height // 2 + 1, ui.terminal_width // 2 - 10, "아무 키나 눌러 메뉴로 돌아가기...")
                sys.stdout.flush() # 즉시 화면에 반영
                readchar.readkey()
        elif choice == '3':
            ui.clear_screen()
            ui.print_at(ui.terminal_height // 2, ui.terminal_width // 2 - 5, "게임 종료")
            sys.stdout.flush() # "게임 종료" 메시지 즉시 출력
            sys.stdout.write(ANSI.SHOW_CURSOR)
            sys.stdout.flush()
            sys.exit()
        else:
            # 잘못된 입력 메시지를 메시지 로그에 추가 후 메시지 로그만 다시 그리기
            ui.add_message(f"잘못된 입력입니다. 다시 시도하세요: '{choice}'")
            ui.draw_message_log() # 메시지 로그만 업데이트
            readchar.readkey()

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

