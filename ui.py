# ui.py

import sys
import shutil
import re
from typing import List
from wcwidth import wcswidth

# 순환 참조 방지를 위해 타입 힌트를 문자열로 사용
# from monster import Monster
# from player import Player
# from dungeon_map import DungeonMap

class ANSI:
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET = tuple(f"\033[{i}m" for i in range(30, 38)) + ("\033[0m",)
    HIDE_CURSOR, SHOW_CURSOR = "\033[?25l", "\033[?25h"
    @staticmethod
    def cursor_to(y, x): return f"\033[{y + 1};{x + 1}H"

ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[0-?]*[ -/]*[@-~])')

def get_str_width(s):
    return wcswidth(ansi_escape_pattern.sub('', s))

def pad_str_to_width(s, width, align='left'):
    s_width = get_str_width(s)
    if s_width >= width: return s
    padding_size = width - s_width
    if align == 'right': return ' ' * padding_size + s
    if align == 'center':
        left = padding_size // 2
        return ' ' * left + s + ' ' * (padding_size - left)
    return s + ' ' * padding_size

class UI:
    def __init__(self):
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()
        self.message_log = []
        self.message_log_max_lines = 5
        
        self.MAP_VIEWPORT_WIDTH = 60
        self.MAP_VIEWPORT_HEIGHT = 20
        self.map_viewport_x_start = 1
        self.map_viewport_y_start = 1

        self.status_bar_y_start = self.map_viewport_y_start + self.MAP_VIEWPORT_HEIGHT
        
        self.message_log_x_start = self.map_viewport_x_start + self.MAP_VIEWPORT_WIDTH + 2
        self.message_log_y_start = self.map_viewport_y_start
        self.message_log_width = self.terminal_width - self.message_log_x_start - 2
        self.message_log_height = 10

        self.skill_inventory_x_start = self.message_log_x_start
        self.skill_inventory_y_start = self.message_log_y_start + self.message_log_height + 1
        self.skill_inventory_width = self.message_log_width
        
        sys.stdout.write(ANSI.HIDE_CURSOR)
        self.clear_screen()

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")

    def add_message(self, msg):
        self.message_log.append(msg)
        if len(self.message_log) > self.message_log_max_lines:
            self.message_log.pop(0)

    def draw_game_screen(self, player, dungeon_map, monsters, camera_x, camera_y):
        self.clear_screen()
        
        self._draw_map_and_entities(player, dungeon_map, monsters, camera_x, camera_y)
        self._draw_player_status(player)
        self._draw_message_log()
        self._draw_skill_inventory(player)

        sys.stdout.flush()

    def _draw_map_and_entities(self, player, dungeon_map, monsters, camera_x, camera_y):
        monster_positions = {(m.x, m.y): m.symbol for m in monsters if not m.dead}
        
        for y in range(self.MAP_VIEWPORT_HEIGHT):
            draw_y = self.map_viewport_y_start + y
            line_to_write = []
            
            for x_offset in range(self.MAP_VIEWPORT_WIDTH):
                map_x, map_y = camera_x + x_offset, camera_y + y
                
                char_to_draw = ' ' # 기본값은 빈 공간
                
                # 맵 범위 안이고, 안개가 비활성화되었거나 방문한 타일인 경우
                if 0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height and \
                   (not dungeon_map.fog_enabled or (map_x, map_y) in dungeon_map.visited):
                    
                    # 1. 몬스터 또는 플레이어보다 타일을 먼저 가져옴
                    char_to_draw = dungeon_map.get_tile_for_display(map_x, map_y)
                    
                    # 2. 해당 위치에 몬스터가 있으면 몬스터로 덮어씀
                    if (map_x, map_y) in monster_positions:
                        char_to_draw = f"{ANSI.RED}{monster_positions[(map_x, map_y)]}{ANSI.RESET}"
                        
                    # 3. 해당 위치에 플레이어가 있으면 플레이어로 덮어씀 (최우선)
                    if map_x == player.x and map_y == player.y:
                        char_to_draw = f"{ANSI.YELLOW}{player.char}{ANSI.RESET}"
                
                line_to_write.append(char_to_draw)

            # 패딩 로직 없이 바로 출력
            sys.stdout.write(f"{ANSI.cursor_to(draw_y, self.map_viewport_x_start)}{''.join(line_to_write)}")

    def _draw_player_status(self, player):
        status_text = f"HP: {player.hp}/{player.max_hp} | MP: {player.mp}/{player.max_mp} | Lv: {player.level} | EXP: {player.exp}/{player.exp_to_next_level}"
        padded_status = pad_str_to_width(status_text, self.MAP_VIEWPORT_WIDTH)
        sys.stdout.write(f"{ANSI.cursor_to(self.status_bar_y_start, self.map_viewport_x_start)}{padded_status}")

    def _draw_message_log(self):
        y, x, w = self.message_log_y_start, self.message_log_x_start, self.message_log_width
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{pad_str_to_width('--- 메시지 로그 ---', w)}")
        for i, msg in enumerate(self.message_log):
            if y + 1 + i < self.message_log_y_start + self.message_log_height:
                sys.stdout.write(f"{ANSI.cursor_to(y + 1 + i, x)}{pad_str_to_width(f' {msg}', w)}")

    def _draw_skill_inventory(self, player):
        y, x, w = self.skill_inventory_y_start, self.skill_inventory_x_start, self.skill_inventory_width
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{pad_str_to_width('--- 스킬 ---', w)}")
        inv_y = y + 5
        sys.stdout.write(f"{ANSI.cursor_to(inv_y, x)}{pad_str_to_width('--- 인벤토리 ---', w)}")
        for i, (item_id, item_data) in enumerate(player.inventory.items()):
            if inv_y + 1 + i < self.terminal_height:
                item_text = f" {item_data['name']}: {item_data['qty']}개"
                sys.stdout.write(f"{ANSI.cursor_to(inv_y + 1 + i, x)}{pad_str_to_width(item_text, w)}")