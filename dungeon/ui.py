# dungeon/ui.py - 콘솔 기반 UI 및 렌더링 클래스

import os
import sys
import logging
import readchar # readchar 임포트 추가
import shutil
from .localization import _

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
    "white_bg": "\033[30;47m", # Black on White BG (Hit Flash)
    "red_bg": "\033[97;41m",   # White on Red BG (Trap Trigger)
    "gold_bg": "\033[30;43m",  # Black on Gold BG (Mimic/Treasure)
    "invert": "\033[7m",       # Invert Message
    "cyan": "\033[96m",        # Add Cyan (often used)
    "reset": "\033[0m"
}

class ConsoleUI:
    """콘솔에 게임 화면을 렌더링하고 UI 상호작용을 처리합니다."""
    
    def __init__(self):
        # 화면을 지우는 명령 설정 ('nt'는 윈도우, 나머지는 유닉스 계열)
        self.clear_command = 'cls' if os.name == 'nt' else 'clear'
        self.messages = [] # 메시지 로그를 저장할 리스트
        self.shake_duration = 0 # 쉐이크 효과 남은 프레임
        self.import_random()

    def import_random(self):
        import random
        self.random = random

    def trigger_shake(self, frames=5):
        """화면 흔들림 효과를 트리거합니다."""
        self.shake_duration = frames

    def show_language_selection(self):
        """언어 선택 메뉴를 표시합니다."""
        selected_idx = 0
        options = ["한국어 (Korean)", "English", "Exit"]
        
        while True:
            self._clear_screen()
            terminal_width = shutil.get_terminal_size().columns
            
            # ASCII Art Title "LANGUAGE"
            title = [
                "",
                "  ██╗      █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗  ██████╗ ███████╗",
                "  ██║     ██╔══██╗████╗  ██║██╔════╝ ██║   ██║██╔══██╗██╔════╝ ██╔════╝",
                "  ██║     ███████║██╔██╗ ██║██║  ███╗██║   ██║███████║██║  ███╗█████╗  ",
                "  ██║     ██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██║██║   ██║██╔══╝  ",
                "  ███████╗██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████╗",
                "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
                ""
            ]
            
            for line in title:
                padding = (terminal_width - len(line)) // 2
                print(f"{COLOR_MAP['gold']}{' ' * padding}{line}{COLOR_MAP['reset']}")

            print("\n") # Spacing after title

            for i, option in enumerate(options):
                prefix = ">" if i == selected_idx else " "
                color = COLOR_MAP['yellow'] if i == selected_idx else COLOR_MAP['dark_grey'] # Dark grey for unselected for style? Or White. Main menu uses White.
                # Let's use White for consistency with main menu options usually
                if i == selected_idx:
                     color = COLOR_MAP['yellow']
                else:
                     color = COLOR_MAP['white']

                content = f"{prefix} {option} {prefix[::-1]}" # Add symmetric arrow? Or just left.
                # User asked to remove border, usually that implies a cleaner look.
                # Let's just do "> Option" centered.
                
                content = f"{prefix} {option}"
                padding = (terminal_width - len(content)) // 2
                print(f"{' ' * padding}{color}{content}{COLOR_MAP['reset']}")
            
            # Controls
            controls = "[↑/↓ or W/S] Select | [ENTER] Confirm"
            ctrl_padding = (terminal_width - len(controls)) // 2
            print(f"\n{COLOR_MAP['dark_grey']}{' ' * ctrl_padding}{controls}{COLOR_MAP['reset']}")
            
            key = self.get_key_input()
            if key in [readchar.key.UP, 'w', 'W', '\x1b[A']:
                selected_idx = (selected_idx - 1) % len(options)
            elif key in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
                selected_idx = (selected_idx + 1) % len(options)
            elif key in [readchar.key.ENTER, '\r', '\n', ' ']:
                return selected_idx
            elif key in ['q', 'Q', readchar.key.ESC]:
                return 2 # Exit

    def show_skill_selection_menu(self, known_skills, game_renderer=None):
        """충전할 스킬 선택 메뉴 표시 (Identifiy Menu와 유사)
        
        Args:
            known_skills: [skill_name, ...] 형식의 스킬 이름 리스트
            game_renderer: 게임 화면 재렌더링 콜백
            
        Returns:
            선택된 skill_name 또는 None
        """
        if not known_skills:
            self.add_message(_("No skills available!"))
            return None
            
        selected_idx = 0
        
        while True:
            # Redraw game
            if game_renderer:
                game_renderer()
                
            # Popup Layout
            menu_width = 40
            menu_height = len(known_skills) + 5
            start_y = 5
            start_x = 20
            
            # Box
            print(f"\033[{start_y};{start_x}H", end="")
            print("┌" + "─" * (menu_width - 2) + "┐")
            
            header = _("Select skill to recharge")
            padding = (menu_width - len(header) - 2) // 2
            print(f"\033[{start_y + 1};{start_x}H", end="")
            print("│" + " " * padding + header + " " * (menu_width - len(header) - padding - 2) + "│")
            
            print(f"\033[{start_y + 2};{start_x}H", end="")
            print("├" + "─" * (menu_width - 2) + "┤")
            
            # List
            for i, skill_name in enumerate(known_skills):
                prefix = " >" if i == selected_idx else "  "
                if i == selected_idx:
                    color = "\033[93m" # Yellow
                    reset = "\033[0m"
                else:
                    color = ""
                    reset = ""
                
                line_y = start_y + 3 + i
                print(f"\033[{line_y};{start_x}H", end="")
                
                content = f"{prefix} {skill_name}"
                print(f"│{color}{content:<{menu_width - 2}}{reset}│")

            # Footer
            print(f"\033[{start_y + 3 + len(known_skills)};{start_x}H", end="")
            print("└" + "─" * (menu_width - 2) + "┘")
            
            sys.stdout.flush()
            
            # Input
            key = self.get_key_input()
            if key in [readchar.key.UP, 'w', 'W', '\x1b[A']:
                selected_idx = max(0, selected_idx - 1)
            elif key in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
                selected_idx = min(len(known_skills) - 1, selected_idx + 1)
            elif key in ['\r', '\n', readchar.key.ENTER, ' ']:
                return known_skills[selected_idx]
            elif key in [readchar.key.ESC, 'q', 'Q']:
                return None

    def show_repair_menu(self, repairable_items, game_renderer=None):
        """수리할 아이템 선택 메뉴 표시
        
        Args:
            repairable_items: [ItemDefinition, ...]
            game_renderer: 게임 화면 재렌더링 콜백
            
        Returns:
            선택된 ItemDefinition 또는 None
        """
        if not repairable_items:
            self.add_message(_("No items to repair!"))
            return None
            
        selected_idx = 0
        
        while True:
            # Redraw game
            if game_renderer:
                game_renderer()
                
            # Popup Layout
            menu_width = 50
            menu_height = len(repairable_items) + 5
            start_y = 5
            start_x = 15
            
            # Box
            print(f"\033[{start_y};{start_x}H", end="")
            print("┌" + "─" * (menu_width - 2) + "┐")
            
            header = _("Select equipment to repair")
            padding = (menu_width - len(header) - 2) // 2
            print(f"\033[{start_y + 1};{start_x}H", end="")
            print("│" + " " * padding + header + " " * (menu_width - len(header) - padding - 2) + "│")
            
            print(f"\033[{start_y + 2};{start_x}H", end="")
            print("├" + "─" * (menu_width - 2) + "┤")
            
            # List
            for i, item in enumerate(repairable_items):
                prefix = " >" if i == selected_idx else "  "
                if i == selected_idx:
                    color = "\033[93m" # Yellow
                    reset = "\033[0m"
                else:
                    color = ""
                    reset = ""
                
                line_y = start_y + 3 + i
                cur_d = getattr(item, 'current_durability', 0)
                max_d = getattr(item, 'max_durability', 0)
                dur_str = f"({cur_d}/{max_d})"
                
                print(f"\033[{line_y};{start_x}H", end="")
                
                name_display = item.name[:20] # Truncate check
                content = f"{prefix} {name_display:<20} {dur_str}"
                print(f"│{color}{content:<{menu_width - 2}}{reset}│")

            # Footer
            print(f"\033[{start_y + 3 + len(repairable_items)};{start_x}H", end="")
            print("└" + "─" * (menu_width - 2) + "┘")
            
            sys.stdout.flush()
            
            # Input
            key = self.get_key_input()
            if key in [readchar.key.UP, 'w', 'W', '\x1b[A']:
                selected_idx = max(0, selected_idx - 1)
            elif key in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
                selected_idx = min(len(repairable_items) - 1, selected_idx + 1)
            elif key in ['\r', '\n', readchar.key.ENTER, ' ']:
                return repairable_items[selected_idx]
            elif key in [readchar.key.ESC, 'q', 'Q']:
                return None

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
        terminal_width = shutil.get_terminal_size().columns
        
        # ASCII Art Title - ENTER YOUR NAME
        title = [
            "",
            "  ███████╗███╗   ██╗████████╗███████╗██████╗ ",
            "  ██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗",
            "  █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝",
            "  ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗",
            "  ███████╗██║ ╚████║   ██║   ███████╗██║  ██║",
            "  ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝",
            "",
            "  ██╗   ██╗ ██████╗ ██╗   ██╗██████╗     ███╗   ██╗ █████╗ ███╗   ███╗███████╗",
            "  ╚██╗ ██╔╝██╔═══██╗██║   ██║██╔══██╗    ████╗  ██║██╔══██╗████╗ ████║██╔════╝",
            "   ╚████╔╝ ██║   ██║██║   ██║██████╔╝    ██╔██╗ ██║███████║██╔████╔██║█████╗  ",
            "    ╚██╔╝  ██║   ██║██║   ██║██╔══██╗    ██║╚██╗██║██╔══██║██║╚██╔╝██║██╔══╝  ",
            "     ██║   ╚██████╔╝╚██████╔╝██║  ██║    ██║ ╚████║██║  ██║██║ ╚═╝ ██║███████╗",
            "     ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝",
            ""
        ]
        
        # Center the title
        for line in title:
            padding = (terminal_width - len(line)) // 2
            print(f"{COLOR_MAP['yellow']}{' ' * padding}{line}{COLOR_MAP['reset']}")
        
        # Prompt (centered)
        prompt_text = _("Enter your name") + " " + _("(Max 10 chars)")
        prompt_padding = (terminal_width - len(prompt_text) - 4) // 2
        prompt = f"{' ' * prompt_padding}{prompt_text} > "
        
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
            "  1. " + _("New Game"),
            "  2. " + _("Continue"),
            "  3. " + _("Exit Game"),
            "═" * 40,
            ""
        ]
        
        for line in menu_lines:
            padding = (terminal_width - len(line)) // 2
            print(f"{' ' * padding}{line}")
        
        print(f"{COLOR_MAP['green']}[{_('Select')}] 1, 2, 3...{COLOR_MAP['reset']}", end='', flush=True)

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
        print(f"{COLOR_MAP['red']}        {_('GAME OVER')}           {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['red']}==================================={COLOR_MAP['reset']}")
        print(f"\n    {message}\n")
        print("    " + _("Press any key to return to Main Menu."))
        self.get_key_input()

    def show_death_screen(self):
        """플레이어 사망 화면을 표시합니다."""
        self.show_game_over_screen(_("You died..."))

    def show_confirmation_dialog(self, message):
        """사용자에게 예/아니오 확인을 받습니다."""
        selected_index = 0 # 0: No, 1: Yes
        
        while True:
            self._clear_screen()
            terminal_width = shutil.get_terminal_size().columns
            
            # Message Box
            lines = [
                "╔═════════════════════════════════════╗",
                f"║               {_('Confirm'):^13}               ║",
                "╠═════════════════════════════════════╣",
                f"║ {message:^35} ║",
                "╚═════════════════════════════════════╝",
                ""
            ]
            
            for line in lines:
                padding = (terminal_width - len(line)) // 2
                print(f"{' ' * padding}{line}")
                
            options = [_("No") + " (No)", _("Yes") + " (Yes)"]
            
            for i, option in enumerate(options):
                prefix = "> " if i == selected_index else "  "
                color = COLOR_MAP['green'] if i == selected_index else COLOR_MAP['white']
                line = f"{prefix}{option}"
                line_padding = (terminal_width - len(line)) // 2
                print(f"{color}{' ' * line_padding}{line}{COLOR_MAP['reset']}")
                
            controls = "[↑/↓] 이동 | [ENTER] 선택"
            controls_padding = (terminal_width - len(controls)) // 2
            print(f"\n{COLOR_MAP['yellow']}{' ' * controls_padding}{controls}{COLOR_MAP['reset']}")
            
            key = self.get_key_input()
            
            if key == readchar.key.UP:
                selected_index = 0
            elif key == readchar.key.DOWN:
                selected_index = 1
            elif key in [readchar.key.ENTER, '\r', '\n']:
                return selected_index == 1 # Returns True for Yes
            elif key.lower() == 'y':
                return True
            elif key.lower() == 'n':
                return False

    def show_class_selection(self, class_defs: dict):
        """직업 선택 메뉴를 표시하고 선택된 직업 정의를 반환합니다."""
        selected_index = 0
        class_list = list(class_defs.values())
        
        while True:
            self._clear_screen()
            terminal_width = shutil.get_terminal_size().columns
            
            # ASCII Art Title
            title = [
                "",
                "  ███████╗███████╗██╗     ███████╗ ██████╗████████╗",
                "  ██╔════╝██╔════╝██║     ██╔════╝██╔════╝╚══██╔══╝",
                "  ███████╗█████╗  ██║     █████╗  ██║        ██║   ",
                "  ╚════██║██╔══╝  ██║     ██╔══╝  ██║        ██║   ",
                "  ███████║███████╗███████╗███████╗╚██████╗   ██║   ",
                "  ╚══════╝╚══════╝╚══════╝╚══════╝ ╚═════╝   ╚═╝   ",
                "",
                "  ██╗   ██╗ ██████╗ ██╗   ██╗██████╗      ██████╗██╗      █████╗ ███████╗███████╗",
                "  ╚██╗ ██╔╝██╔═══██╗██║   ██║██╔══██╗    ██╔════╝██║     ██╔══██╗██╔════╝██╔════╝",
                "   ╚████╔╝ ██║   ██║██║   ██║██████╔╝    ██║     ██║     ███████║███████╗███████╗",
                "    ╚██╔╝  ██║   ██║██║   ██║██╔══██╗    ██║     ██║     ██╔══██║╚════██║╚════██║",
                "     ██║   ╚██████╔╝╚██████╔╝██║  ██║    ╚██████╗███████╗██║  ██║███████║███████║",
                "     ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝",
                ""
            ]
            
            for line in title:
                padding = (terminal_width - len(line)) // 2
                print(f"{COLOR_MAP['yellow']}{' ' * padding}{line}{COLOR_MAP['reset']}")
            
            # Class list
            prompt = _("Select your class:")
            prompt_padding = (terminal_width - len(prompt)) // 2
            print(f"{' ' * prompt_padding}{prompt}\n")
            
            for i, cls in enumerate(class_list):
                prefix = "> " if i == selected_index else "  "
                color = COLOR_MAP['green'] if i == selected_index else COLOR_MAP['white']
                # Class name/description are already localized via data_manager redirection
                line = f"{prefix}{cls.name} - {cls.description}"
                line_padding = (terminal_width - len(line)) // 2
                print(f"{color}{' ' * line_padding}{line}{COLOR_MAP['reset']}")
            
            # Selected class details
            sel_cls = class_list[selected_index]
            print()
            detail_title = f"--- [ {sel_cls.name} ] {_('Detail Stats')} ---"
            detail_padding = (terminal_width - len(detail_title)) // 2
            print(f"{COLOR_MAP['blue']}{' ' * detail_padding}{detail_title}{COLOR_MAP['reset']}")
            
            stats_line = f" HP: {sel_cls.hp:<4} | MP: {sel_cls.mp:<4}"
            stats_padding = (terminal_width - len(stats_line)) // 2
            print(f"{' ' * stats_padding}{stats_line}")
            
            attrs_line = f" STR: {sel_cls.str:<3} | MAG: {sel_cls.mag:<3} | DEX: {sel_cls.dex:<3} | VIT: {sel_cls.vit:<3}"
            attrs_padding = (terminal_width - len(attrs_line)) // 2
            print(f"{' ' * attrs_padding}{attrs_line}")
            
            skill_line = f" {_('Basic Skill')}: {sel_cls.base_skill}"
            skill_padding = (terminal_width - len(skill_line)) // 2
            print(f"{' ' * skill_padding}{skill_line}")
            
            controls = "[↑/↓] 이동 | [ENTER] 선택"
            controls_padding = (terminal_width - len(controls)) // 2
            print(f"\n{COLOR_MAP['green']}{' ' * controls_padding}{controls}{COLOR_MAP['reset']}")

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
            terminal_width = shutil.get_terminal_size().columns
            
            
            # ASCII Art Title - LOAD YOUR GAME
            title = [
                "",
                "  ██╗      ██████╗  █████╗ ██████╗     ██╗   ██╗ ██████╗ ██╗   ██╗██████╗ ",
                "  ██║     ██╔═══██╗██╔══██╗██╔══██╗    ╚██╗ ██╔╝██╔═══██╗██║   ██║██╔══██╗",
                "  ██║     ██║   ██║███████║██║  ██║     ╚████╔╝ ██║   ██║██║   ██║██████╔╝",
                "  ██║     ██║   ██║██╔══██║██║  ██║      ╚██╔╝  ██║   ██║██║   ██║██╔══██╗",
                "  ███████╗╚██████╔╝██║  ██║██████╔╝       ██║   ╚██████╔╝╚██████╔╝██║  ██║",
                "  ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝        ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝",
                "",
                "   ██████╗  █████╗ ███╗   ███╗███████╗",
                "  ██╔════╝ ██╔══██╗████╗ ████║██╔════╝",
                "  ██║  ███╗███████║██╔████╔██║█████╗  ",
                "  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  ",
                "  ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗",
                "   ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝",
                ""
            ]
            
            for line in title:
                padding = (terminal_width - len(line)) // 2
                print(f"{COLOR_MAP['yellow']}{' ' * padding}{line}{COLOR_MAP['reset']}")
            
            if not save_files:
                no_save_msg = _("No saved games.")
                msg_padding = (terminal_width - len(no_save_msg)) // 2
                print(f"{' ' * msg_padding}{no_save_msg}")
                
                back_msg = "[B] " + _("Back")
                back_padding = (terminal_width - len(back_msg)) // 2
                print(f"\n{COLOR_MAP['green']}{' ' * back_padding}{back_msg}{COLOR_MAP['reset']}")
            else:
                # Save list (centered)
                for i, filename in enumerate(save_files):
                    prefix = "> " if i == selected_index else "  "
                    color = COLOR_MAP['green'] if i == selected_index else COLOR_MAP['white']
                    line = f"{prefix}{filename}"
                    line_padding = (terminal_width - len(line)) // 2
                    print(f"{color}{' ' * line_padding}{line}{COLOR_MAP['reset']}")
                
                # Controls (centered)
                controls = f"[↑/↓] {_('Move')} | [ENTER/L] {_('Load')} | [D/DEL] {_('Delete')} | [B] {_('Back')}"
                controls_padding = (terminal_width - len(controls)) // 2
                print(f"\n{COLOR_MAP['green']}{' ' * controls_padding}{controls}{COLOR_MAP['reset']}")

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
        
        # [Screen Shake] Apply random offset
        shake_x = 0
        shake_y = 0
        if self.shake_duration > 0:
            self.shake_duration -= 1
            shake_x = self.random.randint(-1, 1)
            shake_y = self.random.randint(0, 1) # Y는 아래로만 (위로 가면 짤림)
            
        # Y Offset (Newline at start)
        if shake_y > 0:
            buffer.append("\n" * shake_y)
        
        # X Offset helper
        def add_line(content):
            if shake_x > 0:
                buffer.append(" " * shake_x + content)
            elif shake_x < 0:
                # 왼쪽으로 밀기 (하지만 0 이하로는 못 감, 단순히 공백 제거는 어려우므로 생략하거나 패딩으로 처리)
                # 터미널에서 왼쪽 이동은 어려우므로 우측 이동만 구현하거나, 
                # 단순히 X축 쉐이크는 positive padding만 사용
                pass 
                buffer.append(content) # Negative shake ignored for simplicity or assume only positive jitter
            else:
                buffer.append(content)

        # 1. 맵 렌더링
        add_line(f"{COLOR_MAP['white']}--- 던전 맵 ---{COLOR_MAP['reset']}\n")

        for y_idx, row in enumerate(map_data):
            rendered_row = []
            for x_idx, (char, color) in enumerate(row):
                rendered_row.append(f"{COLOR_MAP[color]}{char}")
            
            # Row 자체에 Shake X 적용
            if shake_x != 0:
                buffer.append(" " * abs(shake_x))
            buffer.append("".join(rendered_row) + f"{COLOR_MAP['reset']}\n")
        
        # 2. 플레이어 상태
        add_line(f"\n{COLOR_MAP['yellow']}--- 플레이어 상태 ---{COLOR_MAP['reset']}\n")
        job_display = player_stats.get('job', 'Adventurer')
        add_line(f" Name : {player_stats.get('name', 'N/A')} ({job_display})\n")
        add_line(f" HP: {COLOR_MAP['red']}{player_stats.get('hp', 0)}/{player_stats.get('max_hp', 0)}{COLOR_MAP['reset']:<15} | MP: {COLOR_MAP['blue']}{player_stats.get('mp', 0)}/{player_stats.get('max_mp', 0)}{COLOR_MAP['reset']:<15} | 골드: {player_stats.get('gold', 0)}G\n")
        
        # 3. 메시지 로그
        add_line(f"\n{COLOR_MAP['blue']}--- 로그 ---{COLOR_MAP['reset']}\n")
        msgs = self.messages[-5:]
        for msg in msgs:
            add_line(f"> {msg:<60}\n")
        # 로그가 5줄 미만일 때 줄 맞춤
        for _ in range(5 - len(msgs)):
            buffer.append("\n")
        
        # 4. 입력 가이드
        add_line(f"\n{COLOR_MAP['green']}[{_('Move')}] 방향키 | [5/.] {_('Wait')} | [I] {_('Inventory')} | [1-0] {_('Quickslot')}{COLOR_MAP['reset']}\n")
        
        # \033[J: 커서 아래의 남은 잔상들을 지움
        buffer.append("\033[J")
        
        # 한 번에 출력하여 원자성 확보
        sys.stdout.write("".join(buffer))
        sys.stdout.flush()

    def render_inventory(self, player_inventory_items: dict, player_equipped_items: dict):
        """인벤토리 화면을 렌더링합니다."""
        self._clear_screen()
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}           {_('Inventory'):^13}           {COLOR_MAP['reset']}")
        print(f"{COLOR_MAP['yellow']}==================================={COLOR_MAP['reset']}")
        
        print(f"\n--- {COLOR_MAP['cyan']}{_('EQUIP')}{COLOR_MAP['reset']} --- ")
        if player_equipped_items:
            # Defined list of standard slots for sorting/display
            slot_order = ["Head", "Neck", "Body", "Hand1", "Hand2", "Gloves", "Ring1", "Ring2", "Boots"]
            
            # Sort items by slot order if possible
            sorted_items = []
            for slot in slot_order:
                if slot in player_equipped_items:
                    sorted_items.append((slot, player_equipped_items[slot]))
            
            # Add any remaining slots not in standard list
            for slot, item in player_equipped_items.items():
                if slot not in slot_order:
                    sorted_items.append((slot, item))

            for slot, item_obj in sorted_items:
                # item_obj가 문자열(ID)일 수도 있고 객체일 수도 있음. 객체라면 이름 사용
                display_name = item_obj
                if hasattr(item_obj, 'name'):
                    display_name = item_obj.name
                
                # Localize Slot Name (Head -> 머리 / Head)
                slot_display = _(slot)
                print(f"  {slot_display:<6}: {display_name}")
        else:
            print("  " + _("No equipped items"))

        print("\n--- " + _("Items") + " --- ")
        if player_inventory_items:
            for item_id, item_data in player_inventory_items.items():
                item_obj = item_data['item']
                qty = item_data['qty']
                print(f"  - {item_obj.name} (x{qty})")
        else:
            print("  " + _("No items"))

        print(f"\n{COLOR_MAP['green']}[I] 닫기{COLOR_MAP['reset']}")
        sys.stdout.flush()

    def show_character_sheet(self, player_entity):
        """캐릭터 정보창 표시 및 스탯 포인트 배분"""
        from .components import StatsComponent, LevelComponent
        
        selected_stat = 0 # 0:STR, 1:MAG, 2:DEX, 3:VIT
        stat_names = [_("STR (Str)"), _("MAG (Mag)"), _("DEX (Dex)"), _("VIT (Vit)")]
        
        while True:
            self._clear_screen()
            
            stats = player_entity.get_component(StatsComponent)
            level_comp = player_entity.get_component(LevelComponent)
            if not stats or not level_comp: return
            
            # --- Header ---
            print(f"\n  [ {level_comp.job or 'Adventurer'} - Level {level_comp.level} ]")
            print("="*60)
            print(f"  Experience: {level_comp.exp} / {level_comp.exp_to_next}")
            print(f"  Stat Points: {level_comp.stat_points}")
            print("-" * 60)
            
            # --- Stats Rows ---
            def get_row(idx, name, value, desc):
                prefix = " >" if idx == selected_stat else "  "
                color = "\033[93m" if idx == selected_stat else "\033[97m" # Yellow if selected
                reset = "\033[0m"
                return f"{color}{prefix} {name:<15}: {value:<4}  | {desc}{reset}"

            print(get_row(0, stat_names[0], stats.base_str, _("Equipment/Req")))
            print(get_row(1, stat_names[1], stats.base_mag, _("Max MP")))
            print(get_row(2, stat_names[2], stats.base_dex, _("AC/Hit")))
            print(get_row(3, stat_names[3], stats.base_vit, _("Max HP")))
            
            print("-" * 60)
            print(f"  HP: {stats.current_hp}/{stats.max_hp}  MP: {stats.current_mp}/{stats.max_mp}")
            print(f"  Attack: {stats.attack_min}-{stats.attack_max}  Defense: {stats.defense}")
            print("="*60)
            print("\n  [UP/DOWN]: Select  [RIGHT/ENTER]: Add Point  [ESC/Q]: Close")

            key = self.get_key_input()
            
            if key in [readchar.key.UP, 'w', 'W', '\x1b[A']:
                selected_stat = max(0, selected_stat - 1)
            elif key in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
                selected_stat = min(3, selected_stat + 1)
            elif key in [readchar.key.RIGHT, 'd', 'D', '\x1b[C', '+', '=', '\r', '\n']:
                if level_comp.stat_points > 0:
                    level_comp.stat_points -= 1
                    if selected_stat == 0: stats.base_str += 1
                    elif selected_stat == 1: stats.base_mag += 1
                    elif selected_stat == 2: stats.base_dex += 1
                    elif selected_stat == 3: stats.base_vit += 1
                    
                    # Recalculate Logic
                    if hasattr(player_entity.world, 'engine') and hasattr(player_entity.world.engine, '_recalculate_stats'):
                        player_entity.world.engine._recalculate_stats()
                else:
                    pass 
            elif key in [readchar.key.ESC, 'q', 'Q', 'c', 'C']:
                break
    
    def show_identify_menu(self, unidentified_items, game_renderer=None):
        """미감정 아이템 선택 메뉴 표시 (게임 화면 위 오버레이)
        
        Args:
            unidentified_items: [(name, data), ...] 형식의 미감정 아이템 목록
            game_renderer: 게임 화면을 다시 그리는 함수 (선택사항)
            
        Returns:
            선택된 (name, data) 튜플 또는 None (취소 시)
        """
        if not unidentified_items:
            self.add_message(_("No items to identify!"))
            return None
        
        selected_idx = 0
        
        while True:
            # Redraw game screen first (if renderer provided)
            if game_renderer:
                game_renderer()
            
            # Calculate popup position (center of screen)
            menu_width = 50
            menu_height = len(unidentified_items) + 5
            start_y = 5
            start_x = 15
            
            # Draw semi-transparent background box
            print(f"\033[{start_y};{start_x}H", end="")
            print("┌" + "─" * (menu_width - 2) + "┐")
            
            # Header
            header = _("Select item to identify") + f" ({len(unidentified_items)}) "
            padding = (menu_width - len(header) - 2) // 2
            print(f"\033[{start_y + 1};{start_x}H", end="")
            print("│" + " " * padding + header + " " * (menu_width - len(header) - padding - 2) + "│")
            
            print(f"\033[{start_y + 2};{start_x}H", end="")
            print("├" + "─" * (menu_width - 2) + "┤")
            
            # Item list
            for i, (name, data) in enumerate(unidentified_items):
                item = data['item']
                qty = data.get('qty', 1)
                
                # Display format: ? [TYPE] xQTY
                item_type = getattr(item, 'type', 'UNKNOWN')
                display = f"? [{item_type}]"
                if qty > 1:
                    display += f" x{qty}"
                
                # Highlight selected
                prefix = " >" if i == selected_idx else "  "
                if i == selected_idx:
                    color = "\033[93m"  # Yellow
                    reset = "\033[0m"
                else:
                    color = ""
                    reset = ""
                
                line_y = start_y + 3 + i
                print(f"\033[{line_y};{start_x}H", end="")
                print("│" + color + prefix + " " + display + reset + " " * (menu_width - len(display) - 5) + "│")
            
            # Footer
            footer_y = start_y + 3 + len(unidentified_items)
            print(f"\033[{footer_y};{start_x}H", end="")
            print("├" + "─" * (menu_width - 2) + "┤")
            
            help_text = f" [↑/↓] 선택  [ENTER] 감정  [ESC] 취소 ({selected_idx}/{len(unidentified_items)-1}) "
            padding = (menu_width - len(help_text) - 2) // 2
            print(f"\033[{footer_y + 1};{start_x}H", end="")
            print("│" + " " * padding + help_text + " " * (menu_width - len(help_text) - padding - 2) + "│")
            
            print(f"\033[{footer_y + 2};{start_x}H", end="")
            print("└" + "─" * (menu_width - 2) + "┘")
            
            sys.stdout.flush()
            
            # Input handling
            key = self.get_key_input()
            
            if key in [readchar.key.UP, 'w', 'W', '\x1b[A']:
                selected_idx = max(0, selected_idx - 1)
            elif key in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
                selected_idx = min(len(unidentified_items) - 1, selected_idx + 1)
            elif key in ['\r', '\n', readchar.key.ENTER]:
                return unidentified_items[selected_idx]
            elif key in [readchar.key.ESC, 'q', 'Q']:
                return None

    def show_center_dialogue(self, message, color='red'):
        """화면 중앙에 메시지를 타이핑 효과로 출력합니다. (Boss Skill Alert)"""
        terminal_width = shutil.get_terminal_size().columns
        terminal_height = shutil.get_terminal_size().lines
        
        # Center coordinates
        start_y = terminal_height // 2
        
        # Box Styling
        padding = 4
        msg_len = 0
        # Calculate max length (ignoring ANSI) - simplified here assuming no ANSI in input msg
        # If input has ANSI, len() will be wrong. We assume clean text input.
        msg_len = len(message)
        box_width = msg_len + (padding * 2) + 2
        
        # Draw Box (Overlay)
        # Using ANSI cursor positioning
        start_x = (terminal_width - box_width) // 2
        
        # Top Border
        print(f"\033[{start_y - 1};{start_x}H{COLOR_MAP['white']}" + "╔" + "═" * (box_width - 2) + "╗" + f"{COLOR_MAP['reset']}")
        
        # Middle (Empty for now)
        print(f"\033[{start_y};{start_x}H{COLOR_MAP['white']}║{' ' * (box_width - 2)}║{COLOR_MAP['reset']}")
        
        # Bottom Border
        print(f"\033[{start_y + 1};{start_x}H{COLOR_MAP['white']}" + "╚" + "═" * (box_width - 2) + "╝" + f"{COLOR_MAP['reset']}")
        
        # Typewriter Effect
        import time
        eff_color = COLOR_MAP.get(color, COLOR_MAP['red'])
        
        # Position cursor for text
        text_start_x = start_x + 1 + padding
        print(f"\033[{start_y};{text_start_x}H{eff_color}", end="", flush=True)
        
        for char in message:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.05) # "Papapak" speed
            
        print(f"{COLOR_MAP['reset']}", flush=True)
        
        # Hold for a moment
        time.sleep(0.8)