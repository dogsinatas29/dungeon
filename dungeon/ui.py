# dungeon/ui.py - 콘솔 기반 UI 및 렌더링 클래스

import os
import sys
import logging
import readchar # readchar 임포트 추가
import shutil

# 터미널 색상 코드를 사용한 렌더링을 위한 딕셔너리
COLOR_MAP = {
    "white": "\033[97m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "green": "\033[92m",
    "blue": "\033[94m",
    "gold": "\033[33m",
    "brown": "\033[38;5;130m", # 갈색 (Door)
    "dark_grey": "\033[90m", # 어두운 회색 (Floor)
    "reset": "\033[0m"
}

class ConsoleUI:
    """콘솔에 게임 화면을 렌더링하고 UI 상호작용을 처리합니다."""
    
    def __init__(self):
        # 화면을 지우는 명령 설정 ('nt'는 윈도우, 나머지는 유닉스 계열)
        self.clear_command = 'cls' if os.name == 'nt' else 'clear'
        self.messages = [] # 메시지 로그를 저장할 리스트

    def _clear_screen(self):
        """화면을 깨끗하게 지웁니다. (ANSI 이스케이프 코드 사용으로 깜빡임 최소화)"""
        # \033[H: 커서를 홈 위치(0,0)로 이동
        # \033[J: 커서 위치부터 화면 끝까지 지움
        sys.stdout.write("\033[H\033[J")
        sys.stdout.flush()

    def add_message(self, message: str):
        """메시지 로그에 새로운 메시지를 추가합니다."""
        self.messages.append(message)

    def get_player_name(self):
        """플레이어 이름을 한 글자씩 입력받습니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}  PYTHON ECS REAL-TIME DUNGEON     {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        prompt = "\n  당신의 이름은 무엇입니까? (최대 10자) > "
        sys.stdout.write(prompt)
        sys.stdout.flush()

        name_chars = []
        while True:
            key = readchar.readkey() # readkey()는 특수 키도 처리
            
            if key == readchar.key.ENTER: # Enter 키 입력 시 종료
                break
            elif key == readchar.key.BACKSPACE: # Backspace 처리
                if name_chars:
                    name_chars.pop()
                    sys.stdout.write("\b \b") # 커서 뒤로 이동, 문자 지우기, 다시 뒤로 이동
                    sys.stdout.flush()
            elif len(name_chars) < 10 and key.isprintable(): # 최대 10자, 출력 가능한 문자만
                name_chars.append(key)
                sys.stdout.write(key)
                sys.stdout.flush()
        
        sys.stdout.write("\n") # 마지막 엔터 처리
        return "".join(name_chars) if name_chars else "Hero"

    def get_key_input(self):
        """키 입력을 받습니다. Enter를 누를 필요가 없습니다."""
        while True:
            key = readchar.readkey() # readchar.readkey()로 변경
            if key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            return key

    def show_main_menu(self):
        """메인 메뉴를 표시하고 사용자 입력을 받아 반환합니다."""
        self._clear_screen()
        
        # ASCII Art Title - DUNGEON CRAWL
        title = [
            "",
            "  ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███████╗ ██████╗ ███╗   ██╗",
            "  ██╔══██╗██║   ██║████╗  ██║██╔════╝ ██╔════╝██╔═══██╗████╗  ██║",
            "  ██║  ██║██║   ██║██╔██╗ ██║██║  ███╗█████╗  ██║   ██║██╔██╗ ██║",
            "  ██║  ██║██║   ██║██║╚██╗██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║",
            "  ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗╚██████╔╝██║ ╚████║",
            "  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝",
            "",
            "   ██████╗██████╗  █████╗ ██╗    ██╗██╗     ",
            "  ██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ",
            "  ██║     ██████╔╝███████║██║ █╗ ██║██║     ",
            "  ██║     ██╔══██╗██╔══██║██║███╗██║██║     ",
            "  ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗",
            "   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝",
            ""
        ]
        
        # Center the title
        terminal_width = shutil.get_terminal_size().columns
        for line in title:
            padding = (terminal_width - len(line)) // 2
            print(f"{COLOR_MAP['yellow']}{' ' * padding}{line}{COLOR_MAP['reset']}")
        
        # Menu options (centered)
        menu_lines = [
            "",
            "═" * 40,
            "           [메뉴]",
            "  1. 새 게임",
            "  2. 이어하기",
            "  3. 게임 종료",
            "═" * 40,
            ""
        ]
        
        for line in menu_lines:
            padding = (terminal_width - len(line)) // 2
            print(f"{' ' * padding}{line}")
        
        print(f"{COLOR_MAP['green']}[선택] 1, 2, 3을 입력하세요.{COLOR_MAP['reset']}", end='', flush=True)

        while True:
            choice = self.get_key_input()
            if choice == '1':
                return 0 # Start new game
            elif choice == '2':
                return 1 # Load game
            elif choice == '3':
                return 2 # Exit game
            else:
                # 잘못된 입력 시 메시지 표시 또는 무시 (여기서는 무시)
                pass

    def show_game_over_screen(self, message):
        """게임 종료 화면을 표시합니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['red']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['red']}        G A M E  O V E R           {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['red']}==================================={COLOR_MAP['reset']}")
        print(f"\n    {message}\n")
        print("    아무 키나 눌러 메인 메뉴로 돌아갑니다.")
        self.get_key_input()

    def show_class_selection(self, class_defs: dict):
        """직업 선택 메뉴를 표시하고 선택된 직업 정의를 반환합니다."""
        selected_index = 0
        class_list = list(class_defs.values())
        
        while True:
            self._clear_screen()
            print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
            print(f"{COLOR_MAP['yellow']}      SELECT YOUR CLASS       {COLOR_MAP['reset']}")
            print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
            
            print("\n  당신의 직업을 선택하세요:\n")
            for i, cls in enumerate(class_list):
                prefix = "> " if i == selected_index else "  "
                color = COLOR_MAP['green'] if i == selected_index else COLOR_MAP['white']
                print(f"{color}{prefix}{cls.name} - {cls.description}{COLOR_MAP['reset']}")
            
            # 선택된 직업 상세 정보 표시
            sel_cls = class_list[selected_index]
            print(f"\n{COLOR_MAP['blue']}--- [ {sel_cls.name} ] 상세 능력치 ---{COLOR_MAP['reset']}")
            print(f" HP: {sel_cls.hp:<4} | MP: {sel_cls.mp:<4}")
            print(f" STR: {sel_cls.str:<3} | MAG: {sel_cls.mag:<3} | DEX: {sel_cls.dex:<3} | VIT: {sel_cls.vit:<3}")
            print(f" 기본 스킬: {sel_cls.base_skill}")
            
            print(f"\n{COLOR_MAP['green']}  [↑/↓] 이동 | [ENTER] 선택{COLOR_MAP['reset']}")

            key = self.get_key_input()

            if key == readchar.key.UP:
                selected_index = max(0, selected_index - 1)
            elif key == readchar.key.DOWN:
                selected_index = min(len(class_list) - 1, selected_index + 1)
            elif key == readchar.key.ENTER:
                return class_list[selected_index]

    def show_save_list(self, save_files: list):
        """저장된 게임 목록을 표시하고 선택(L), 삭제(D), 취소(ESC) 입력을 처리합니다."""
        selected_index = 0
        
        while True:
            self._clear_screen()
            print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
            print(f"{COLOR_MAP['yellow']}       저장된 게임 불러오기        {COLOR_MAP['reset']}")
            print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
            
            if not save_files:
                print("\n  저장된 게임이 없습니다.")
                print(f"\n{COLOR_MAP['green']}  [B] 뒤로 가기{COLOR_MAP['reset']}")
            else:
                print("\n  [목록]")
                for i, filename in enumerate(save_files):
                    prefix = "> " if i == selected_index else "  "
                    color = COLOR_MAP['green'] if i == selected_index else COLOR_MAP['white']
                    print(f"{color}{prefix}{filename}{COLOR_MAP['reset']}")
                
                print(f"\n{COLOR_MAP['green']}  [↑/↓] 이동 | [ENTER/L] 불러오기 | [D/DEL] 삭제 | [B] 뒤로 가기{COLOR_MAP['reset']}")

            key = self.get_key_input()

            # 사용자의 환경에서 'b'가 확실히 작동하므로 이를 기본 종료 키로 사용
            if key.lower() == 'b':
                return None, None
            
            if not save_files:
                continue

            if key == readchar.key.UP:
                selected_index = max(0, selected_index - 1)
            elif key == readchar.key.DOWN:
                selected_index = min(len(save_files) - 1, selected_index + 1)
            elif key == readchar.key.ENTER or key == 'l' or key == 'L':
                return "LOAD", save_files[selected_index]
            elif key == readchar.key.DELETE or key in [readchar.key.DELETE, 'd', 'D', '\x1b[3~']: # DEL 키 ANSI 코드 포함
                return "DELETE", save_files[selected_index]
        
    def render_all(self, map_data, player_stats):
        """
        맵, 로그, 상태를 포함한 전체 화면을 렌더링합니다. (버퍼링 및 ANSI 제어로 깜빡임 제로)
        """
        buffer = []
        # \033[H: 커서를 맨 위(0,0)로 이동 (화면을 지우는 것보다 훨씬 빠름)
        buffer.append("\033[H")
        
        # 1. 맵 렌더링
        buffer.append(f"{COLOR_MAP['white']}--- 던전 맵 ---{COLOR_MAP['reset']}\n")

        for y_idx, row in enumerate(map_data):
            rendered_row = []
            for x_idx, (char, color) in enumerate(row):
                rendered_row.append(f"{COLOR_MAP[color]}{char}")
            buffer.append("".join(rendered_row) + f"{COLOR_MAP['reset']}\n")
        
        # 2. 플레이어 상태
        buffer.append(f"\n{COLOR_MAP['yellow']}--- 플레이어 상태 ---{COLOR_MAP['reset']}\n")
        buffer.append(f" 이름: {player_stats.get('name', 'N/A'):<10} | 레벨: {player_stats.get('level', 1)}\n")
        buffer.append(f" HP: {COLOR_MAP['red']}{player_stats.get('hp', 0)}/{player_stats.get('max_hp', 0)}{COLOR_MAP['reset']:<10} | MP: {player_stats.get('mp', 0)} | 골드: {player_stats.get('gold', 0)}G\n")
        
        # 3. 메시지 로그
        buffer.append(f"\n{COLOR_MAP['blue']}--- 로그 ---{COLOR_MAP['reset']}\n")
        msgs = self.messages[-5:]
        for msg in msgs:
            buffer.append(f"> {msg:<60}\n")
        # 로그가 5줄 미만일 때 줄 맞춤
        for _ in range(5 - len(msgs)):
            buffer.append("\n")
        
        # 4. 입력 가이드
        buffer.append(f"\n{COLOR_MAP['green']}[이동] 방향키 | [5/.] 대기 | [I] 인벤토리 | [1-0] 퀵슬롯{COLOR_MAP['reset']}\n")
        
        # \033[J: 커서 아래의 남은 잔상들을 지움 (맵 크기가 줄어들거나 할 때 유용)
        buffer.append("\033[J")
        
        # 한 번에 출력하여 원자성 확보
        sys.stdout.write("".join(buffer))
        sys.stdout.flush()

    def render_inventory(self, player_inventory_items: dict, player_equipped_items: dict):
        """인벤토리 화면을 렌더링합니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}           인 벤 토 리           {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        
        print("\n--- 장비 --- ")
        if player_equipped_items:
            for slot, item_id in player_equipped_items.items():
                print(f"  {slot}: {item_id}")
        else:
            print("  장착된 아이템 없음")

        print("\n--- 아이템 --- ")
        if player_inventory_items:
            for item_id, item_data in player_inventory_items.items():
                item_obj = item_data['item']
                qty = item_data['qty']
                print(f"  - {item_obj.name} (x{qty})")
        else:
            print("  아이템 없음")

        print(f"\n{COLOR_MAP['green']}[I] 닫기{COLOR_MAP['reset']}")
        sys.stdout.flush()