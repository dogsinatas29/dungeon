# dungeon/ui.py - 콘솔 기반 UI 및 렌더링 클래스

import os
import sys

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
        """화면을 깨끗하게 지웁니다."""
        os.system(self.clear_command)

    def add_message(self, message: str):
        """메시지 로그에 새로운 메시지를 추가합니다."""
        self.messages.append(message)

    def show_main_menu(self):
        """게임 시작 메뉴를 표시하고 플레이어 이름을 입력받습니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}  PYTHON ECS REAL-TIME DUNGEON     {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print("\n  [조작법] W:위, S:아래, A:왼쪽, D:오른쪽, Q:종료")
        print("  몬스터(M)에게 이동하면 전투가 시작됩니다.")
        print("  키(k)를 찾아서 잠긴 문(+)을 여세요.\n")
        
    def get_player_name(self):
        """플레이어 이름을 입력받습니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}  PYTHON ECS REAL-TIME DUNGEON     {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print("\n  당신의 이름은 무엇입니까? (최대 10자) > ", end='', flush=True)
        name = input()
        return name[:10] if name else "Hero"

    def get_key_input(self):
        """키 입력을 받습니다. Enter를 누를 필요가 없습니다."""
        import readchar # readchar는 이 함수 내에서만 사용되므로 여기에 임포트
        while True:
            key = readchar.readchar()
            if key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            return key

    def show_main_menu(self):
        """메인 메뉴를 표시하고 사용자 입력을 받아 반환합니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}  PYTHON ECS REAL-TIME DUNGEON     {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print("\n  [메뉴]")
        print("  1. 새 게임")
        print("  2. 이어하기")
        print("  3. 게임 종료")
        print(f"\n{COLOR_MAP['green']}[선택] 1, 2, 3을 입력하세요.{COLOR_MAP['reset']}", end='', flush=True)

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
        print("    콘솔 창을 닫아 게임을 종료하십시오.")
        # 입력이 없으면 계속 대기할 수 있으므로, 종료를 위해 sys.exit()을 사용하지 않습니다.
        # 사용자가 수동으로 콘솔을 닫도록 안내합니다.
        
    def render_all(self, map_data, player_stats):
        """
        맵, 로그, 상태를 포함한 전체 화면을 렌더링합니다.
        
        Args:
            map_data (str): 렌더링할 맵 문자열 (RendererSystem에서 생성)
            player_stats (dict): 플레이어 상태 정보
        """
        self._clear_screen()
        
        # 1. 맵 렌더링
        # 이 줄의 닫는 따옴표(")를 추가하여 SyntaxError를 해결했습니다.
        print(f"{COLOR_MAP['white']}--- 던전 맵 ---{COLOR_MAP['reset']}")

        # map_data는 이제 2D 리스트이므로 직접 출력하는 대신, 각 타일을 렌더링해야 합니다.
        for y_idx, row in enumerate(map_data):
            rendered_row = []
            for x_idx, (char, color) in enumerate(row):
                rendered_row.append(f"{COLOR_MAP[color]}{char}")
            print("".join(rendered_row) + f"{COLOR_MAP['reset']}")

        
        # 2. 플레이어 상태
        print(f"\n{COLOR_MAP['yellow']}--- 플레이어 상태 ---{COLOR_MAP['reset']}")
        print(f" 이름: {player_stats.get('name', 'N/A')}")
        print(f" HP: {COLOR_MAP['red']}{player_stats.get('hp', 0)}/{player_stats.get('max_hp', 0)}{COLOR_MAP['reset']} | 공격력: {player_stats.get('attack', 0)} | 방어력: {player_stats.get('defense', 0)}")
        print(f" 열쇠: {', '.join(player_stats.get('inventory', ['없음']))}")
        
        # 3. 메시지 로그
        print(f"\n{COLOR_MAP['blue']}--- 로그 ---{COLOR_MAP['reset']}")
        # 최신 메시지 5개만 출력
        for msg in self.messages[-5:]:
            print(f"> {msg}")
        
        # 4. 입력 가이드
        print(f"\n{COLOR_MAP['green']}[이동] WASD, 방향키, HJKL, YUBN | [Q] 종료 | [I] 인벤토리{COLOR_MAP['reset']}")
        sys.stdout.flush() # 출력 버퍼 강제 비우기
