# ui.py

import sys
import shutil
import re
from typing import List
from wcwidth import wcswidth
import data_manager # 아이템 정의를 가져오기 위해 추가

# 순환 참조 방지를 위해 타입 힌트를 문자열로 사용
# from monster import Monster
# from player import Player
# from dungeon_map import DungeonMap

class ANSI:
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET = tuple(f"\033[{i}m" for i in range(30, 38)) + ("\033[0m",)
    HIDE_CURSOR, SHOW_CURSOR = "\033[?25l", "\033[?25h"
    @staticmethod
    def cursor_to(y, x): return f"\033[{y + 1};{x + 1}H"

ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\-_]|[\[0-?]*[ -/]*[@-~])')

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

        self.quick_slot_x_start = self.message_log_x_start
        self.quick_slot_y_start = self.message_log_y_start + self.message_log_height + 1
        self.quick_slot_width = self.message_log_width
        
        sys.stdout.write(ANSI.HIDE_CURSOR)
        self.clear_screen()

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")

    def add_message(self, msg):
        self.message_log.append(msg)
        if len(self.message_log) > self.message_log_max_lines:
            self.message_log.pop(0)

    def draw_game_screen(self, player, dungeon_map, monsters, camera_x, camera_y, 
                         inventory_open=False, inventory_cursor_pos=0, inventory_active_tab='item'):
        self.clear_screen()
        
        self._draw_map_and_entities(player, dungeon_map, monsters, camera_x, camera_y)
        self._draw_player_status(player)
        self._draw_message_log()
        self._draw_quick_slots(player)

        if inventory_open:
            self._draw_inventory(player, inventory_cursor_pos, inventory_active_tab)

        sys.stdout.flush()

    def _draw_map_and_entities(self, player, dungeon_map, monsters, camera_x, camera_y):
        monster_positions = {(m.x, m.y): m.symbol for m in monsters if not m.dead}
        
        for y in range(self.MAP_VIEWPORT_HEIGHT):
            draw_y = self.map_viewport_y_start + y
            line_to_write = []
            
            for x_offset in range(self.MAP_VIEWPORT_WIDTH):
                map_x, map_y = camera_x + x_offset, camera_y + y
                
                char_to_draw = ' '
                
                if 0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height and \
                   (not dungeon_map.fog_enabled or (map_x, map_y) in dungeon_map.visited):
                    
                    char_to_draw = dungeon_map.get_tile_for_display(map_x, map_y)
                    
                    if (map_x, map_y) in monster_positions:
                        char_to_draw = f"{ANSI.RED}{monster_positions[(map_x, map_y)]}{ANSI.RESET}"
                        
                    if map_x == player.x and map_y == player.y:
                        char_to_draw = f"{ANSI.YELLOW}{player.char}{ANSI.RESET}"
                
                line_to_write.append(char_to_draw)

            sys.stdout.write(f"{ANSI.cursor_to(draw_y, self.map_viewport_x_start)}{''.join(line_to_write)}")

    def _draw_player_status(self, player):
        y_start = self.status_bar_y_start
        x_start = self.map_viewport_x_start
        
        # 이전 상태 표시줄을 지웁니다.
        for i in range(10): # 충분한 라인을 지웁니다.
             self.write_at(y_start + i, x_start, " " * self.MAP_VIEWPORT_WIDTH)

        bar_width = 20  # 막대 그래프의 너비

        def draw_bar(current, max_val, color):
            if max_val == 0:
                percent = 0
            else:
                percent = current / max_val
            filled_len = int(percent * bar_width)
            empty_len = bar_width - filled_len
            return f"{color}{'█' * filled_len}{ANSI.WHITE}{'█' * empty_len}{ANSI.RESET}"

        # HP, MP, Stamina
        hp_text = pad_str_to_width(f"HP: {player.hp}/{player.max_hp}", 18)
        hp_bar = draw_bar(player.hp, player.max_hp, ANSI.RED)
        self.write_at(y_start, x_start, f"{hp_text} {hp_bar}")

        mp_text = pad_str_to_width(f"MP: {player.mp}/{player.max_mp}", 18)
        mp_bar = draw_bar(player.mp, player.max_mp, ANSI.BLUE)
        self.write_at(y_start + 1, x_start, f"{mp_text} {mp_bar}")

        stamina_text = pad_str_to_width(f"Stamina: {player.stamina}/{player.max_stamina}", 18)
        stamina_bar = draw_bar(player.stamina, player.max_stamina, ANSI.YELLOW)
        self.write_at(y_start + 2, x_start, f"{stamina_text} {stamina_bar}")

        # Other stats
        other_stats = [
            f"ATT: {player.attack} ({player.base_att}+{player.att_bonus})",
            f"DEF: {player.defense} ({player.base_def}+{player.def_bonus})",
            f"Lv: {player.level}",
            f"EXP: {player.exp}/{player.exp_to_next_level}"
        ]
        for i, line in enumerate(other_stats):
            padded_line = pad_str_to_width(line, self.MAP_VIEWPORT_WIDTH)
            self.write_at(y_start + 3 + i, x_start, padded_line)

    def _draw_message_log(self):
        y, x, w = self.message_log_y_start, self.message_log_x_start, self.message_log_width
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{pad_str_to_width('--- 메시지 로그 ---', w, align='center')}")
        for i, msg in enumerate(self.message_log):
            if y + 1 + i < self.message_log_y_start + self.message_log_height:
                sys.stdout.write(f"{ANSI.cursor_to(y + 1 + i, x)}{pad_str_to_width(f' {msg}', w)}")

    def _draw_quick_slots(self, player):
        y, x, w = self.quick_slot_y_start, self.quick_slot_x_start, self.quick_slot_width
        
        self.write_at(y, x, pad_str_to_width('--- 아이템 퀵슬롯 ---', w, align='center'))
        for i in range(1, 6):
            slot_item = player.item_quick_slots.get(i)
            item_name = player.inventory.get(slot_item, {}).get('name', '비어있음') if slot_item else '비어있음'
            text = f"{i}: {item_name}"
            self.write_at(y + i, x, pad_str_to_width(text, w))

        skill_y_start = y + 7
        self.write_at(skill_y_start, x, pad_str_to_width('--- 스킬 퀵슬롯 ---', w, align='center'))
        skill_slots = list(range(6, 10)) + [0]
        for i, slot_num in enumerate(skill_slots):
            slot_skill = player.skill_quick_slots.get(slot_num)
            skill_name = player.skills.get(slot_skill, {}).get('name', '비어있음') if slot_skill else '비어있음'
            text = f"{slot_num}: {skill_name}"
            self.write_at(skill_y_start + 1 + i, x, pad_str_to_width(text, w))

    def _draw_inventory(self, player, cursor_pos=0):
        win_w, win_h = 54, 18
        win_x = self.map_viewport_x_start + (self.MAP_VIEWPORT_WIDTH - win_w) // 2
        win_y = self.map_viewport_y_start + (self.MAP_VIEWPORT_HEIGHT - win_h) // 2

        # Draw border and clear area
        self.write_at(win_y, win_x, "┌" + "─" * (win_w - 2) + "┐")
        for i in range(win_h - 2):
            self.write_at(win_y + 1 + i, win_x, "│" + " " * (win_w - 2) + "│")
        self.write_at(win_y + win_h - 1, win_x, "└" + "─" * (win_w - 2) + "┘")
        
        # Titles
        self.write_at(win_y, win_x + 2, " 인벤토리 ")
        self.write_at(win_y, win_x + 28, " 장비 ")

        # Equipment section
        equip_slots = ["WEAPON", "SHIELD", "HELMET", "ARMOR", "GLOVES", "BOOTS", "NECKLACE", "RING"]
        for i, slot in enumerate(equip_slots):
            item_id = player.equipment.get(slot)
            item_name = data_manager.get_item_definition(item_id).name if item_id else "---"
            self.write_at(win_y + 2 + i, win_x + 29, f"{slot:<8}: {item_name}")

        # Inventory section
        inventory_items = list(player.inventory.items())
        if not inventory_items:
            self.write_at(win_y + 2, win_x + 2, "비어 있음")
        else:
            for i, (item_id, item_data) in enumerate(inventory_items):
                if i < win_h - 4:
                    prefix = "> " if i == cursor_pos else "  "
                    item_text = f"{prefix}{item_data['name']}: {item_data['qty']}개"
                    self.write_at(win_y + 2 + i, win_x + 2, pad_str_to_width(item_text, 25))
        
        # Instructions
        instructions = "[↑↓] 이동 [e] 장착/해제 [i] 닫기"
        self.write_at(win_y + win_h - 2, win_x + (win_w - len(instructions)) // 2, instructions)

    def show_main_menu(self):
        self.clear_screen()
        options = ["새 게임", "이어하기", "게임 종료"]
        selected_index = 0
        while True:
            y, x = self.terminal_height // 2 - len(options) // 2, self.terminal_width // 2
            for i, option in enumerate(options):
                prefix = f"{ANSI.YELLOW}> " if i == selected_index else "  "
                self.write_at(y + i, x - len(option) // 2, f"{prefix}{option}{ANSI.RESET}")
            sys.stdout.flush()
            key = readchar.readkey()
            if key == readchar.key.UP: selected_index = (selected_index - 1) % len(options)
            elif key == readchar.key.DOWN: selected_index = (selected_index + 1) % len(options)
            elif key == readchar.key.ENTER: return selected_index
            elif key == 'q': return 2

    def get_player_name(self):
        self.clear_screen()
        self.write_at(self.terminal_height // 2 - 1, self.terminal_width // 2 - 10, "용사의 이름을 입력하세요: ")
        sys.stdout.flush()
        sys.stdout.write(ANSI.SHOW_CURSOR)
        name = input()
        sys.stdout.write(ANSI.HIDE_CURSOR)
        return name if name else "용사"

    def write_at(self, y, x, text):
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{text}")

    def show_game_over_screen(self):
        self.clear_screen()
        msg = "GAME OVER"
        self.write_at(self.terminal_height // 2, self.terminal_width // 2 - len(msg) // 2, msg)
        sys.stdout.flush()
        readchar.readkey()

    def __del__(self):
        sys.stdout.write(ANSI.SHOW_CURSOR)
        sys.stdout.write("\033[0m")
        self.clear_screen()
