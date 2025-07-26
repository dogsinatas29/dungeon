# ui.py

import sys
import shutil
import re
from wcwidth import wcswidth # 한글 너비 계산을 위해 추가

class ANSI:
    # (ANSI 코드 정의는 기존과 동일)
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"
    
    # 커서 숨기기/보이기
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

    @staticmethod
    def cursor_to(y, x):
        # 터미널 좌표는 1-based이므로 1을 더해준다.
        return f"\033[{y + 1};{x + 1}H"

# ANSI 이스케이프 시퀀스를 제거하기 위한 정규식
ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[0-?]*[ -/]*[@-~])')

def get_str_width(s):
    """ANSI 코드를 제외한 문자열의 실제 터미널 너비를 반환합니다."""
    clean_s = ansi_escape_pattern.sub('', s)
    return wcswidth(clean_s)

def pad_str_to_width(s, width, align='left'):
    """문자열을 주어진 너비에 맞게 공백으로 채웁니다. (한글 등 넓은 문자 지원)"""
    current_width = get_str_width(s)
    padding_size = width - current_width
    if padding_size <= 0:
        return s

    padding = ' ' * padding_size
    if align == 'left':
        return s + padding
    elif align == 'right':
        return padding + s
    elif align == 'center':
        left_padding = ' ' * (padding_size // 2)
        right_padding = ' ' * (padding_size - len(left_padding))
        return left_padding + s + right_padding
    return s # 기본값

class UI:
    def __init__(self):
        self.terminal_width, self.terminal_height = self._get_terminal_size()
        self.buffer = [[' ' for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]
        self.message_log = []
        self.message_log_max_lines = 5
        
        # UI 레이아웃 정의
        self.MAP_VIEWPORT_WIDTH = 60
        self.MAP_VIEWPORT_HEIGHT = 20
        self.map_viewport_x_start = 1
        self.map_viewport_y_start = 1

        self.status_bar_y_start = self.map_viewport_y_start + self.MAP_VIEWPORT_HEIGHT
        
        self.message_log_x_start = self.map_viewport_x_start + self.MAP_VIEWPORT_WIDTH + 2
        self.message_log_y_start = self.map_viewport_y_start
        self.message_log_width = self.terminal_width - self.message_log_x_start -1
        self.message_log_height = 10

        self.skill_inventory_x_start = self.message_log_x_start
        self.skill_inventory_y_start = self.message_log_y_start + self.message_log_height + 1
        self.skill_inventory_width = self.message_log_width
        self.skill_inventory_height = self.terminal_height - self.skill_inventory_y_start -1
        
        self.show_skill_inventory = True

        sys.stdout.write(ANSI.HIDE_CURSOR)
        self.clear_screen()

    def _get_terminal_size(self):
        return shutil.get_terminal_size()

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")
        self.buffer = [[' ' for _ in range(self.terminal_width)] for _ in range(self.terminal_height)]

    def print_at(self, y, x, text, end='\n'):
        """
        버퍼의 특정 위치에 텍스트를 씁니다.
        """
        if y < 0 or y >= self.terminal_height or x < 0:
            return

        # ANSI 코드를 제외한 실제 너비 계산
        text_width = get_str_width(text)
        
        # 버퍼에 쓸 때, 한 문자가 여러 칸을 차지하는 것을 고려하지 않고 그대로 저장
        # 렌더링 시점에 너비를 계산하여 위치를 조정
        col = x
        for char in text:
            if col < self.terminal_width:
                # 버퍼에는 char 단위로 저장
                # 실제 렌더링은 draw_game_screen에서 처리
                pass # 이 함수는 이제 버퍼링에 직접 관여하지 않음

        # 직접 화면에 출력하는 대신, 버퍼에 저장
        # 이 함수는 이제 draw_game_screen을 위한 준비 작업만 함
        # 실제 버퍼링은 draw_game_screen에서 이루어짐
        # 여기서는 간단하게 텍스트를 버퍼의 해당 라인에만 임시로 넣어두는 개념으로 변경
        # 주의: 이 방식은 한 줄에 여러 print_at 호출 시 덮어쓰기 문제가 생길 수 있음
        # -> draw_game_screen에서 모든 그리기를 처리하도록 로직을 중앙화해야 함
        
        # 임시로 기존 버퍼링 방식 유지, 단 draw_game_screen에서 최종 처리
        row = self.buffer[y]
        # 기존 내용을 지우고 새 텍스트 삽입 (단순화된 방식)
        # pad_str_to_width를 사용하여 정렬된 문자열을 얻음
        # 이 함수는 이제 draw_game_screen에서 직접 호출되어야 함.
        # print_at은 메시지 추가 등 다른 용도로 사용될 수 있음.
        pass # draw_game_screen으로 로직 이전

    def add_message(self, msg):
        self.message_log.append(msg)
        if len(self.message_log) > self.message_log_max_lines:
            self.message_log.pop(0)

    def toggle_skill_inventory(self):
        self.show_skill_inventory = not self.show_skill_inventory

    def _draw_borders(self):
        # (기존과 동일)
        pass

    def _draw_map(self, player, dungeon_map, camera_x, camera_y):
        if not dungeon_map: return
        for y in range(self.MAP_VIEWPORT_HEIGHT):
            for x in range(self.MAP_VIEWPORT_WIDTH):
                map_x, map_y = camera_x + x, camera_y + y
                
                char_to_draw = ' '
                if 0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height:
                    char_to_draw = dungeon_map.get_tile_for_display(map_x, map_y, player.x, player.y)
                
                # 버퍼에 직접 쓰기
                # 이 부분은 한글 등 넓은 문자를 고려해야 함
                # get_tile_for_display가 반환하는 문자열은 ANSI 코드를 포함할 수 있음
                # 여기서는 일단 첫 글자만 표시 (임시)
                # TODO: 넓은 문자 처리 로직 개선
                self.buffer[self.map_viewport_y_start + y][self.map_viewport_x_start + x] = char_to_draw

    def _draw_player_status(self, player):
        if not player: return
        
        hp_bar = f"HP: {player.hp}/{player.max_hp}"
        mp_bar = f"MP: {player.mp}/{player.max_mp}"
        level_info = f"Lv: {player.level}"
        
        status_text = f"{hp_bar} | {mp_bar} | {level_info}"
        padded_status = pad_str_to_width(status_text, self.MAP_VIEWPORT_WIDTH)
        
        y = self.status_bar_y_start
        x = self.map_viewport_x_start
        
        # 버퍼에 쓰기
        col = x
        for char in padded_status:
            if col < x + self.MAP_VIEWPORT_WIDTH:
                self.buffer[y][col] = char
                col += 1

    def _draw_message_log(self):
        y = self.message_log_y_start
        x = self.message_log_x_start
        
        title = "--- 메시지 로그 ---"
        self.buffer[y][x:x+len(title)] = list(title)
        
        for i, msg in enumerate(self.message_log):
            padded_msg = pad_str_to_width(msg, self.message_log_width)
            row = y + i + 1
            if row < self.message_log_y_start + self.message_log_height:
                # 버퍼에 쓰기
                col = x
                # 문자열을 버퍼에 쓸 때 ANSI 코드는 자리를 차지하지 않음을 고려해야 함
                # 이 부분은 복잡하므로, 렌더링 시점에 직접 출력하는 방식으로 변경하는 것이 나을 수 있음
                # 여기서는 단순하게 버퍼에 저장
                # self.buffer[row][x:x+len(padded_msg)] = list(padded_msg) # 이 방식은 넓은 문자에 문제 발생
                
                # 임시 해결: 직접 sys.stdout.write 사용
                sys.stdout.write(f"\033[{row+1};{x+1}H{padded_msg}")


    def _draw_skill_inventory(self, player):
        # (기존과 동일, 단, 문자열 정렬에 pad_str_to_width 사용)
        pass

    def draw_game_screen(self, player, dungeon_map, camera_x=0, camera_y=0):
        """게임의 모든 ��소를 한 번에 화면에 출력합니다."""
        # ANSI 코드를 포함할 최종 문자열 리스트
        output_buffer = []
        
        # 화면 지우기 코드 추가
        output_buffer.append("\033[2J\033[H")

        # 1. 맵 그리기
        if player and dungeon_map:
            for y_vp in range(self.MAP_VIEWPORT_HEIGHT):
                line_buffer = []
                current_width = 0
                x_vp = 0
                while current_width < self.MAP_VIEWPORT_WIDTH and x_vp < self.MAP_VIEWPORT_WIDTH:
                    map_x, map_y = camera_x + x_vp, camera_y + y_vp
                    
                    char_code = ' '
                    if 0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height:
                        char_code = dungeon_map.get_tile_for_display(map_x, map_y, player.x, player.y)
                    
                    char_width = get_str_width(char_code)
                    
                    # 뷰포트 너비를 초과하면 나머지 공간을 공백으로 채움
                    if current_width + char_width > self.MAP_VIEWPORT_WIDTH:
                        line_buffer.append(' ' * (self.MAP_VIEWPORT_WIDTH - current_width))
                        current_width = self.MAP_VIEWPORT_WIDTH
                        continue

                    # UI 모듈에서 색상 결정
                    color = ANSI.WHITE
                    if char_code == '@': color = ANSI.CYAN
                    elif char_code in ['고', '슬']: color = ANSI.YELLOW # 몬스터 이름 첫 글자
                    elif char_code == 'S': color = ANSI.CYAN
                    elif char_code == 'E' or char_code == 'X': color = ANSI.MAGENTA
                    elif char_code == 'R': color = ANSI.GREEN
                    elif char_code == 'I': color = ANSI.RED
                    
                    line_buffer.append(f"{color}{char_code}{ANSI.RESET}")
                    current_width += char_width
                    x_vp += 1
                
                # 남은 공간이 있다면 공백으로 채움
                if current_width < self.MAP_VIEWPORT_WIDTH:
                    line_buffer.append(' ' * (self.MAP_VIEWPORT_WIDTH - current_width))

                # 각 줄의 시작 위치로 커서 이동 후 한 줄 출력
                output_buffer.append(f"\033[{self.map_viewport_y_start + y_vp + 1};{self.map_viewport_x_start + 1}H")
                output_buffer.append("".join(line_buffer))

        # 2. 상태바 그리기
        if player:
            # 단축키 정보 추가
            key_info_text = pad_str_to_width("[q: 저장 후 종료]", self.MAP_VIEWPORT_WIDTH)
            output_buffer.append(f"\033[{self.status_bar_y_start};{self.map_viewport_x_start + 1}H{key_info_text}")

            hp_bar = f"HP: {player.hp}/{player.max_hp}"
            mp_bar = f"MP: {player.mp}/{player.max_mp}"
            level_info = f"Lv: {player.level}"
            status_text = pad_str_to_width(f"{hp_bar} | {mp_bar} | {level_info}", self.MAP_VIEWPORT_WIDTH)
            output_buffer.append(f"\033[{self.status_bar_y_start + 1};{self.map_viewport_x_start + 1}H{status_text}")

            current_floor, current_room_index = player.dungeon_level
            map_type_str = "메인 맵" if current_room_index == 0 else f"서브 룸 {current_room_index}"
            location_text = pad_str_to_width(f"위치: {current_floor}층 - {map_type_str}", self.MAP_VIEWPORT_WIDTH)
            output_buffer.append(f"\033[{self.status_bar_y_start + 2};{self.map_viewport_x_start + 1}H{location_text}")

        # 3. 메시지 로그 그리기
        title = pad_str_to_width("--- 메시지 로그 ---", self.message_log_width, align='center')
        output_buffer.append(f"\033[{self.message_log_y_start + 1};{self.message_log_x_start + 1}H{title}")
        for i, msg in enumerate(self.message_log):
            padded_msg = pad_str_to_width(f" - {msg}", self.message_log_width)
            output_buffer.append(f"\033[{self.message_log_y_start + i + 2};{self.message_log_x_start + 1}H{padded_msg}")

        # 4. 인벤토리 창 그리기
        if self.show_skill_inventory and player:
            y_offset = self.skill_inventory_y_start
            title = pad_str_to_width("--- 인벤토리 ---", self.skill_inventory_width, align='center')
            output_buffer.append(f"\033[{y_offset + 1};{self.skill_inventory_x_start + 1}H{title}")
            
            i = 0
            for item_id, data in player.inventory.items():
                item_name = data.get('name', item_id)
                qty = data.get('qty', 0)
                item_line = pad_str_to_width(f" {i+1}. {item_name} ({qty}개)", self.skill_inventory_width)
                output_buffer.append(f"\033[{y_offset + i + 2};{self.skill_inventory_x_start + 1}H{item_line}")
                i += 1

        # 모든 내용을 한 번에 출력
        sys.stdout.write("".join(output_buffer))
        sys.stdout.flush()