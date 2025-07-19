# ui.py

import sys
import os
import shutil
import data_manager # 아이템 표시 이름을 위해 data_manager 임포트
import unicodedata # 유니코드 문자 너비 계산을 위해 임포트

# 표준 출력 인코딩을 UTF-8로 강제 설정
# 이는 터미널이 UTF-8을 지원하지만 파이썬이 다른 인코딩을 사용할 때 발생할 수 있는 문제를 해결합니다.
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

def get_char_width(char):
    """문자의 터미널 표시 너비를 반환합니다 (전각 문자 2, 반각 문자 1)."""
    if unicodedata.east_asian_width(char) in ('F', 'W', 'A'): # Fullwidth, Wide, Ambiguous
        return 2
    return 1

class ANSI:
    """ANSI 이스케이프 코드를 정의합니다."""
    # 텍스트 색상
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 배경 색상
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # 스타일
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    STRIKETHROUGH = '\033[9m'
    RESET = '\033[0m' # 모든 속성을 리셋합니다.

    # 커서 이동 및 화면 제어
    HIDE_CURSOR = '\033[?25l' # 커서 숨기기
    SHOW_CURSOR = '\033[?25h' # 커서 보이기
    CLEAR_SCREEN = '\033[2J' # 화면 전체 지우기
    HOME_CURSOR = '\033[H' # 커서를 홈 위치 (0,0)으로 이동

    @staticmethod
    def cursor_to(x, y):
        """커서를 특정 (x, y) 좌표로 이동합니다. (x: 가로, y: 세로)"""
        # ANSI 코드는 1-based 인덱스를 사용하므로 y, x에 1을 더합니다.
        return f'\033[{y + 1};{x + 1}H'


class UI:
    MAP_VIEWPORT_WIDTH = 60
    MAP_VIEWPORT_HEIGHT = 20

    def __init__(self):
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()
        
        self.map_panel_width = self.MAP_VIEWPORT_WIDTH + 2 # 테두리 포함
        self.map_panel_height = self.MAP_VIEWPORT_HEIGHT + 2 # 테두리 포함

        self.info_panel_x_start = self.map_panel_width + 1 # 맵 패널 바로 옆
        self.info_panel_width = self.terminal_width - self.map_panel_width - 1
        self.info_panel_height = self.map_panel_height

        self.message_log_height = 5
        self.message_log_y_start = self.map_panel_height + 1 # 맵 패널 아래

        self.message_history = []
        self.skill_inventory_visible = False

        # 더블 버퍼링을 위한 화면 버퍼 (문자, 색상) 튜플 저장
        self._screen_buffer = [[(' ', ANSI.RESET) for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]
        self._prev_screen_buffer = [[(' ', ANSI.RESET) for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]

        sys.stdout.write(ANSI.HIDE_CURSOR) # 커서 숨기기
        sys.stdout.write(ANSI.CLEAR_SCREEN) # 화면 전체 지우기
        sys.stdout.flush() # 즉시 적용

    def clear_screen(self):
        """화면을 지우고 커서를 홈 위치로 이동하고, 버퍼를 초기화합니다."""
        sys.stdout.write(ANSI.CLEAR_SCREEN)
        sys.stdout.write(ANSI.HOME_CURSOR)
        sys.stdout.flush()
        # 버퍼도 초기화
        self._screen_buffer = [[(' ', ANSI.RESET) for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]
        self._prev_screen_buffer = [[(' ', ANSI.RESET) for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]

    def add_message(self, message):
        """메시지 로그에 메시지를 추가하고, 최대 길이를 유지합니다."""
        self.message_history.append(message)
        if len(self.message_history) > self.message_log_height:
            self.message_history = self.message_history[-self.message_log_height:]
        # 메시지 로그는 draw_game_screen에서 함께 그려지므로 별도로 draw_message_log를 호출하지 않아도 됨
        # 만약 메시지 추가 시 즉시 화면에 나타나게 하고 싶다면 여기에서 호출 가능
        # self.draw_message_log() # <- 필요하다면 주석 해제

    


    def print_at(self, y, x, text):
        """
        텍스트를 화면 버퍼에 렌더링합니다. ANSI 코드를 파싱하고 문자의 너비를 고려합니다.
        """
        if not (0 <= y < self.terminal_height):
            return

        current_x = x
        current_color = ANSI.RESET # 현재 적용된 색상

        import re
        ansi_pattern = re.compile(r'\x1B\[([0-9;]*)m') # ANSI 색상 코드 패턴

        parts = ansi_pattern.split(text)
        
        # 첫 번째 부분은 항상 텍스트이거나 비어 있습니다.
        # 그 다음부터는 [색상코드, 텍스트, 색상코드, 텍스트 ...] 순서입니다.
        for i, part in enumerate(parts):
            if i % 2 == 1: # ANSI 코드 부분
                if part == '0': # RESET 코드
                    current_color = ANSI.RESET
                else:
                    current_color = f'\033[{part}m'
            else: # 텍스트 부분
                for char in part:
                    if current_x >= self.terminal_width:
                        break # 화면 너비 초과
                    
                    char_width = get_char_width(char)
                    
                    # 버퍼에 (문자, 색상) 튜플 저장
                    if 0 <= y < self.terminal_height and 0 <= current_x < self.terminal_width:
                        self._screen_buffer[y][current_x] = (char, current_color)
                        # 전각 문자의 경우 다음 칸도 동일한 색상으로 공백 처리
                        if char_width == 2 and current_x + 1 < self.terminal_width:
                            self._screen_buffer[y][current_x + 1] = (' ', current_color)
                    
                    current_x += char_width


    def draw_border(self, x1, y1, x2, y2):
        """주어진 좌표에 테두리를 버퍼에 그립니다."""
        width = x2 - x1
        height = y2 - y1

        self.print_at(y1, x1, '╔' + '═' * width + '╗')
        self.print_at(y2, x1, '╚' + '═' * width + '╝')

        for y in range(y1 + 1, y2):
            self.print_at(y, x1, '║')
            self.print_at(y, x2, '║')

    def render_map(self, dungeon_map, player_x, player_y, camera_x, camera_y):
        """
        맵을 화면 버퍼에 렌더링합니다.
        dungeon_map이 None이거나 player_x, player_y가 유효하지 않으면 맵을 그리지 않습니다.
        """
        if dungeon_map is None: # dungeon_map이 None이면 그리지 않습니다.
            return

        viewport_start_x = camera_x
        viewport_start_y = camera_y
        
        # 맵 패널 테두리 그리기
        self.draw_border(0, 0, self.map_panel_width - 1, self.map_panel_height - 1)

        # 맵 내용 렌더링
        for display_y in range(self.MAP_VIEWPORT_HEIGHT):
            map_y = viewport_start_y + display_y
            
            if map_y >= dungeon_map.height:
                break
            
            for display_x in range(self.MAP_VIEWPORT_WIDTH):
                map_x = viewport_start_x + display_x
                
                if map_x >= dungeon_map.width:
                    break
                
                screen_x = 1 + display_x
                screen_y = 1 + display_y
                
                tile_char = dungeon_map.get_tile_for_display(map_x, map_y, player_x, player_y)
                self.print_at(screen_y, screen_x, tile_char) # 버퍼에 기록
    
    def render_info(self, player):
        """
        정보 패널을 화면 버퍼에 렌더링합니다.
        player 객체가 None이면 정보 패널을 그리지 않습니다. (또는 빈 패널을 그립니다.)
        """
        panel_x_start = self.info_panel_x_start
        panel_y_start = 0
        panel_width = self.info_panel_width
        panel_height = self.info_panel_height

        self.draw_border(panel_x_start, panel_y_start, panel_x_start + panel_width - 1, panel_y_start + panel_height - 1)

        current_y = panel_y_start + 1
        
        # player가 None인 경우 빈 정보 패널을 그립니다.
        if player is None:
            self.print_at(current_y, panel_x_start + 2, "Name : N/A".ljust(panel_width - 3))
            current_y += 2
            self.print_at(current_y, panel_x_start + 2, "HP : N/A".ljust(panel_width - 3))
            current_y += 1
            self.print_at(current_y, panel_x_start + 2, "MP : N/A".ljust(panel_width - 3))
            current_y += 2
            self.print_at(current_y, panel_x_start + 2, "Status : N/A".ljust(panel_width - 3))
            current_y += 2
            self.print_at(current_y, panel_x_start + 2, "Inventory : N/A".ljust(panel_width - 3))
            current_y += 2
        else: # player 객체가 유효한 경우 기존 로직 수행
            self.print_at(current_y, panel_x_start + 2, f"Name : {player.name}".ljust(panel_width - 3))
            current_y += 2

            self.print_at(current_y, panel_x_start + 2, f"HP : {player.hp}/{player.max_hp}".ljust(panel_width - 3))
            current_y += 1
            self.print_at(current_y, panel_x_start + 2, f"MP : {player.mp}/{player.max_mp}".ljust(panel_width - 3))
            current_y += 2

            self.print_at(current_y, panel_x_start + 2, "Status : Normal".ljust(panel_width - 3))
            current_y += 2
            
            if self.skill_inventory_visible:
                self.print_at(current_y, panel_x_start + 2, "SKILLS".ljust(panel_width - 3))
                current_y += 1
                skills_data = [
                    "1 Attack (사용 MP 10)",
                    "2 Heal   (사용 MP 20)",
                    "3 Fireb. (사용 MP 30)",
                    "4 Defen. (사용 MP 15)",
                    "5 Dash   (사용 MP 5)"
                ]
                for i, skill_info in enumerate(skills_data):
                    self.print_at(current_y + i, panel_x_start + 2, skill_info.ljust(panel_width - 3))
                current_y += len(skills_data) + 1
                
                self.print_at(current_y, panel_x_start + 2, "ITEMS".ljust(panel_width - 3))
                current_y += 1
                if player.inventory:
                    for i, item_slot in enumerate(player.inventory):
                        if i >= 5: break
                        item_def = data_manager.get_item_definition(item_slot['id'])
                        item_name = item_def.name if item_def else item_slot['id']
                        display_text = f"{i+6 if i < 4 else 0}: {item_name} x{item_slot['qty']}"
                        self.print_at(current_y + i, panel_x_start + 2, display_text.ljust(panel_width - 3))
                else:
                    self.print_at(current_y, panel_x_start + 2, "No items".ljust(panel_width - 3))
                
                for i in range(len(player.inventory), 5):
                    display_text = f"{i+6 if i < 4 else 0}: -"
                    self.print_at(current_y + i, panel_x_start + 2, display_text.ljust(panel_width - 3))
                
                current_y += 6
                
            else:
                self.print_at(current_y, panel_x_start + 2, f"Inventory : {len(player.inventory)} items".ljust(panel_width - 3))
                current_y += 2

        self.print_at(panel_y_start + panel_height - 2, panel_x_start + 2, "(Q : Quit)".ljust(panel_width - 3))
        self.print_at(panel_y_start + panel_height - 1, panel_x_start + 2, "(I : Toggle UI)".ljust(panel_width - 3))

    def draw_message_log(self):
        """메시지 로그 패널을 화면 버퍼에 렌더링합니다."""
        # 메시지 로그 영역 초기화 (버퍼에서 공백으로 지우기)
        for i in range(self.message_log_height):
            self.print_at(self.message_log_y_start + i, 1, " " * (self.terminal_width - 2))
            
        # 메시지 기록 렌더링
        for i, msg in enumerate(self.message_history):
            self.print_at(self.message_log_y_start + i, 1, msg)


    def draw_game_screen(self, player, dungeon_map, camera_x=0, camera_y=0):
        """게임 화면 전체를 버퍼에 그리고, 변경된 부분만 터미널에 출력합니다."""
        # 1. 현재 화면 버퍼를 초기화
        for y in range(self.terminal_height):
            for x in range(self.terminal_width):
                self._screen_buffer[y][x] = (' ', ANSI.RESET)

        # 2. 모든 UI 요소를 현재 화면 버퍼에 그립니다.
        # render_map과 render_info에 None이 전달될 수 있도록 처리
        if dungeon_map is not None and player is not None:
             self.render_map(dungeon_map, player.x, player.y, camera_x, camera_y)
        else: # 맵이나 플레이어 정보가 없을 경우 맵 패널 테두리만 그립니다.
            self.draw_border(0, 0, self.map_panel_width - 1, self.map_panel_height - 1)


        self.render_info(player) # player가 None일 수 있으므로 내부에서 처리
        self.draw_message_log()

        # 3. 이전 버퍼와 현재 버퍼를 비교하여 변경된 부분만 실제 터미널에 출력합니다.
        output_buffer = []
        for y in range(self.terminal_height):
            for x in range(self.terminal_width):
                current_char_tuple = self._screen_buffer[y][x]
                prev_char_tuple = self._prev_screen_buffer[y][x]

                if current_char_tuple != prev_char_tuple:
                    char, color = current_char_tuple
                    output_buffer.append(f"{ANSI.cursor_to(x, y)}{color}{char}{ANSI.RESET}")
        
        sys.stdout.write("".join(output_buffer))
        sys.stdout.flush()

        # 4. 현재 버퍼를 다음 프레임을 위한 이전 버퍼로 업데이트합니다.
        self._prev_screen_buffer = [row[:] for row in self._screen_buffer]

    def toggle_skill_inventory(self):
        """스킬/인벤토리 창 표시 여부를 토글합니다."""
        self.skill_inventory_visible = not self.skill_inventory_visible
    
    def clear_panel_area(self, x1, y1, x2, y2):
        """주어진 사각형 영역을 화면 버퍼에서 공백으로 채워 지웁니다."""
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if 0 <= y < self.terminal_height and 0 <= x < self.terminal_width:
                    self._screen_buffer[y][x] = (' ', ANSI.RESET)

