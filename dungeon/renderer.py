# ui.py

import sys
import shutil
import re
import readchar
from typing import List
from wcwidth import wcswidth
from . import data_manager # 아이템 정의를 가져오기 위해 추가
from .items import Equipment, SkillBook # 상태 표시를 위해 클래스 임포트
import logging # 로깅 모듈 임포트

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
        self.full_message_log = [] # 전체 메시지 기록
        self.message_log_max_lines = 3 # 화면에 표시될 최대 줄 수
        
        self.MAP_VIEWPORT_WIDTH = 60
        self.MAP_VIEWPORT_HEIGHT = 20
        self.map_viewport_x_start = 1
        self.map_viewport_y_start = 1

        self.status_bar_y_start = self.map_viewport_y_start + self.MAP_VIEWPORT_HEIGHT
        
        # --- 오른쪽 사이드바 레이아웃 ---
        self.sidebar_x_start = self.map_viewport_x_start + self.MAP_VIEWPORT_WIDTH + 2
        self.sidebar_width = self.terminal_width - self.sidebar_x_start - 2
        
        self.message_log_y_start = self.map_viewport_y_start
        self.equipment_y_start = self.message_log_y_start + 5 # 메시지 로그(제목+3줄) 다음
        self.inventory_y_start = self.equipment_y_start + 10 # 장비(제목+8줄) 다음
        self.skills_y_start = self.inventory_y_start + 7 # 인벤토리(제목+5줄) 다음

        sys.stdout.write(ANSI.HIDE_CURSOR)
        self.clear_screen()
        logging.debug("UI 초기화 완료")

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")
        logging.debug("화면 지우기")

    def add_message(self, msg):
        self.full_message_log.append(msg) # 전체 로그에는 원본 메시지 추가
        logging.debug("메시지 추가: %s", msg)
        
        # 메시지 줄 바꿈 로직
        max_width = self.sidebar_width - 2 # 양쪽 여백 고려
        
        words = msg.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            # 단어 자체의 길이가 최대 너비를 초과하는 경우 (예: 긴 아이템 이름)
            while get_str_width(word) > max_width:
                # 앞에서부터 max_width만큼 자름
                part = ""
                part_len = 0
                for char in word:
                    char_len = get_str_width(char)
                    if part_len + char_len > max_width:
                        break
                    part += char
                    part_len += char_len
                
                if current_line: # 현재 줄에 내용이 있으면 먼저 추가
                    lines.append(current_line)
                    current_line = ""

                lines.append(part)
                word = word[len(part):]

            if get_str_width(current_line + ' ' + word) > max_width:
                lines.append(current_line)
                current_line = word
            else:
                if current_line:
                    current_line += ' ' + word
                else:
                    current_line = word
        
        if current_line:
            lines.append(current_line)

        # 화면 표시용 로그에 추가
        for line in lines:
            self.message_log.append(line)
            if len(self.message_log) > self.message_log_max_lines:
                self.message_log.pop(0)

    def draw_game_screen(self, player, dungeon_map, monsters, camera_x, camera_y,
                         inventory_open=False, inventory_cursor_pos=0,
                         inventory_active_tab='item', inventory_scroll_offset=0,
                         log_viewer_open=False, log_viewer_scroll_offset=0,
                         game_state='NORMAL', projectile_path=None, impact_effect=None, splash_positions=None):
        logging.debug("draw_game_screen 호출됨")
        if projectile_path is None:
            projectile_path = []
        if splash_positions is None:
            splash_positions = []
        self.clear_screen()

        self._draw_map_and_entities(player, dungeon_map, monsters, camera_x, camera_y, projectile_path, impact_effect, splash_positions)
        self._draw_player_status(player)
        self._draw_sidebar(player)

        if inventory_open:
            self._draw_inventory(player, inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset)
        elif log_viewer_open:
            self._draw_full_log_viewer(log_viewer_scroll_offset)

        sys.stdout.flush()
        logging.debug("draw_game_screen 완료")

    def _draw_map_and_entities(self, player, dungeon_map, monsters, camera_x, camera_y, projectile_path=None, impact_effect=None, splash_positions=None):
        logging.debug("_draw_map_and_entities 호출됨")
        if projectile_path is None:
            projectile_path = []
        if splash_positions is None:
            splash_positions = []
        
        # 몬스터 위치를 entity_manager에서 가져오도록 변경
        monster_positions = {}
        if dungeon_map.entity_manager:
            for monster_obj in monsters:
                pos_comp = dungeon_map.entity_manager.get_component(monster_obj.entity_id, PositionComponent)
                if pos_comp:
                    monster_positions[(pos_comp.x, pos_comp.y)] = monster_obj.symbol

        player_pos = dungeon_map.entity_manager.get_component(player.entity_id, PositionComponent)
        if not player_pos: 
            logging.warning("플레이어 위치 컴포넌트를 찾을 수 없습니다.")
            return # 플레이어 위치 없으면 그리지 않음

        # 발사체 위치를 entity_manager에서 가져오도록 변경
        projectile_positions = {}
        if dungeon_map.entity_manager:
            for entity_id, proj_comp in dungeon_map.entity_manager.get_components_of_type(ProjectileComponent).items():
                pos_comp = dungeon_map.entity_manager.get_component(entity_id, PositionComponent)
                if pos_comp:
                    projectile_positions[(pos_comp.x, pos_comp.y)] = '*' # 발사체 심볼 (임시)

        for y in range(self.MAP_VIEWPORT_HEIGHT):
            draw_y = self.map_viewport_y_start + y
            line_to_write = []

            for x_offset in range(self.MAP_VIEWPORT_WIDTH):
                map_x, map_y = camera_x + x_offset, camera_y + y

                char_to_draw = ' '

                if 0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height and \
                   (not dungeon_map.fog_enabled or (map_x, map_y) in dungeon_map.visited):

                    char_to_draw = dungeon_map.get_tile_for_display(map_x, map_y)

                    # 스플래시 효과 렌더링 (몬스터보다 높은 우선순위)
                    if (map_x, map_y) in splash_positions:
                        char_to_draw = f"{ANSI.RED}@{ANSI.RESET}"

                    if (map_x, map_y) in monster_positions:
                        char_to_draw = f"{ANSI.RED}{monster_positions[(map_x, map_y)]}{ANSI.RESET}"
                    
                    if impact_effect and map_x == impact_effect['x'] and map_y == impact_effect['y']:
                        char_to_draw = f"{impact_effect['color']}{impact_effect['symbol']}{ANSI.RESET}"
                    elif (map_x, map_y) in projectile_positions: # 발사체 렌더링
                        char_to_draw = f"{ANSI.YELLOW}{projectile_positions[(map_x, map_y)]}{ANSI.RESET}"


                    if map_x == player_pos.x and map_y == player_pos.y:
                        char_to_draw = f"{ANSI.YELLOW}{player.char}{ANSI.RESET}"

                line_to_write.append(char_to_draw)

            sys.stdout.write(f"{ANSI.cursor_to(draw_y, self.map_viewport_x_start)}{''.join(line_to_write)}")
        logging.debug("_draw_map_and_entities 완료")

    def _draw_player_status(self, player):
        logging.debug("_draw_player_status 호출됨")
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

        # HP, MP, Stamina, EXP
        hp_text = pad_str_to_width(f"HP: {player.hp}/{player.max_hp}", 18)
        hp_bar = draw_bar(player.hp, player.max_hp, ANSI.RED)
        self.write_at(y_start, x_start, f"{hp_text} {hp_bar}")

        mp_text = pad_str_to_width(f"MP: {player.mp}/{player.max_mp}", 18)
        mp_bar = draw_bar(player.mp, player.max_mp, ANSI.BLUE)
        self.write_at(y_start + 1, x_start, f"{mp_text} {mp_bar}")

        stamina_text = pad_str_to_width(f"Stamina: {int(player.stamina)}/{int(player.max_stamina)}", 18)
        stamina_bar = draw_bar(player.stamina, player.max_stamina, ANSI.YELLOW)
        self.write_at(y_start + 2, x_start, f"{stamina_text} {stamina_bar}")
        
        exp_text = pad_str_to_width(f"EXP: {player.exp}/{player.exp_to_next_level}", 18)
        exp_bar = draw_bar(player.exp, player.exp_to_next_level, ANSI.GREEN)
        self.write_at(y_start + 3, x_start, f"{exp_text} {exp_bar}")

        # Other stats
        other_stats_line1 = f"ATT: {player.attack} ({player.base_att}+{player.att_bonus})   DEF: {player.defense} ({player.base_def}+{player.def_bonus})"
        other_stats_line2 = f"Lv: {player.level}"
        
        self.write_at(y_start + 4, x_start, pad_str_to_width(other_stats_line1, self.MAP_VIEWPORT_WIDTH))
        self.write_at(y_start + 5, x_start, pad_str_to_width(other_stats_line2, self.MAP_VIEWPORT_WIDTH))
        logging.debug("_draw_player_status 완료")

    def _draw_sidebar(self, player):
        logging.debug("_draw_sidebar 호출됨")
        x = self.sidebar_x_start
        w = self.sidebar_width

        # --- 1. Message Log ---
        msg_y = self.message_log_y_start
        self.write_at(msg_y, x, pad_str_to_width('--- 메시지 로그 ---', w, align='center'))
        # 메시지 로그 영역을 먼저 지웁니다.
        for i in range(self.message_log_max_lines):
            self.write_at(msg_y + 1 + i, x, " " * w)
        # 메시지를 표시합니다.
        for i, message in enumerate(self.message_log):
            self.write_at(msg_y + 1 + i, x, pad_str_to_width(f' {message}', w))

        # --- 2. Equipment ---
        eq_y = self.equipment_y_start
        self.write_at(eq_y, x, pad_str_to_width('--- 장비 ---', w, align='center'))
        
        equipment_slots = {
            "머리": "투구", "몸통": "갑옷", "장갑": "장갑", "신발": "신발",
            "손1": "무기", "손2방패": "방패", 
            "액세서리1": "목걸이", "액세서리2": "반지1"
        }
        
        for i, (display_name, slot_key) in enumerate(equipment_slots.items()):
            item = player.equipment.get(slot_key)
            item_name = item.name if item else "비어있음"
            text = f"{display_name}: {item_name}"
            self.write_at(eq_y + 1 + i, x, pad_str_to_width(text, w))

        # --- 3. Inventory (Item Quick Slots) ---
        inv_y = self.inventory_y_start
        self.write_at(inv_y, x, pad_str_to_width('--- 퀵 슬롯 ---', w, align='center'))
        for i in range(1, 6):
            item_id = player.item_quick_slots.get(i)
            text = f"{i}: 비어있음"
            if item_id:
                item_def = data_manager.get_item_definition(item_id)
                if item_def:
                    item_qty = player.get_item_quantity(item_id)
                    text = f"{i}: {item_def.name} x{item_qty}"
            
            self.write_at(inv_y + 1 + (i-1), x, pad_str_to_width(text, w))

        # --- 4. Skills ---
        skill_y = self.skills_y_start
        self.write_at(skill_y, x, pad_str_to_width('--- 스킬 ---', w, align='center'))
        skill_slots = list(range(6, 10)) + [0]
        for i, slot_num in enumerate(skill_slots):
            actual_slot_num = 10 if slot_num == 0 else slot_num
            skill_id = player.skill_quick_slots.get(actual_slot_num)
            
            text_to_display = f"{slot_num}: 비어있음"
            if skill_id:
                skill_def = data_manager.get_skill_definition(skill_id)
                if skill_def:
                    skill_info = player.skills.get(skill_id, {'level': 1, 'exp': 0})
                    skill_level = skill_info['level']
                    skill_exp = skill_info['exp']
                    exp_to_next_skill_level = skill_level * 100 # 다음 레벨 필요 경험치 (임시)
                    
                    # Ex) 6 : 휠 윈드 : Lv2 : 10/200
                    text_to_display = f"{slot_num}: {skill_def.name}:Lv{skill_level}:{skill_exp}/{exp_to_next_skill_level}"

            self.write_at(skill_y + 1 + i, x, pad_str_to_width(text_to_display, w))
        logging.debug("_draw_sidebar 완료")

    def _draw_inventory(self, player, active_tab='item', cursor_pos=0, scroll_offset=0):
        logging.debug("_draw_inventory 호출됨 (탭: %s, 커서: %d)", active_tab, cursor_pos)
        win_w, win_h = 60, 20
        win_x = self.map_viewport_x_start + (self.MAP_VIEWPORT_WIDTH - win_w) // 2
        win_y = self.map_viewport_y_start + (self.MAP_VIEWPORT_HEIGHT - win_h) // 2
        
        # --- 창 그리기 ---
        border = "┌" + "─" * (win_w - 2) + "┐"
        middle = "│" + " " * (win_w - 2) + "│"
        self.write_at(win_y, win_x, border)
        for i in range(win_h - 2):
            self.write_at(win_y + 1 + i, win_x, middle)
        self.write_at(win_y + win_h - 1, win_x, "└" + "─" * (win_w - 2) + "┘")

        # --- 탭 그리기 ---
        tabs = {'item': 'a:Item', 'equipment': 'b:Equip', 'scroll': 'c:Scroll', 'skill_book': 'd:Skill', 'all': 'z:All'}
        tab_x_start = win_x + 2
        for tab_key, tab_text in tabs.items():
            display_text = f" {tab_text} "
            if tab_key == active_tab:
                display_text = f"[{tab_text}]"
            self.write_at(win_y + 1, tab_x_start, display_text)
            tab_x_start += get_str_width(display_text) + 1 # 탭 간격 추가

        # --- 아이템 목록 그리기 ---
        list_y_start = win_y + 3
        list_height = win_h - 6
        
        items_to_display = player.inventory.get_items_by_tab(active_tab)

        if not items_to_display:
            self.write_at(list_y_start, win_x + 2, "해당 아이템이 없습니다.")
        else:
            for i in range(list_height):
                item_index = scroll_offset + i
                if item_index >= len(items_to_display):
                    break

                item_data = items_to_display[item_index]
                item_obj = item_data['item']
                
                prefix = "> " if item_index == cursor_pos else "  "
                
                # --- 상태 표시 로직 ---
                status_indicator = ""
                # 1. 장비 아이템이 장착되었는지 확인
                if isinstance(item_obj, Equipment):
                    if item_obj in player.equipment.values():
                        status_indicator = "(E)"
                # 2. 퀵슬롯에 등록되었는지 확인
                else:
                    if isinstance(item_obj, SkillBook):
                        if item_obj.id in player.skill_quick_slots.values():
                            status_indicator = "(Q)"
                    elif item_obj.id in player.item_quick_slots.values():
                        status_indicator = "(Q)"

                # 형식: (상태) 아이템 이름x개수 : 효과
                indicator_space = f"{status_indicator} " if status_indicator else ""
                item_text = f"{prefix}{indicator_space}{item_obj.name} x{item_data['qty']}"
                desc_text = f": {item_obj.description}"
                
                # 너비를 고려하여 텍스트 자르기
                available_width = win_w - 4
                full_text = item_text + desc_text
                if get_str_width(full_text) > available_width:
                    full_text = pad_str_to_width(full_text, available_width)[:available_width]

                self.write_at(list_y_start + i, win_x + 2, pad_str_to_width(full_text, available_width))

        # --- 스크롤바 (선택적) ---
        if len(items_to_display) > list_height:
            scrollbar_height = list_height
            thumb_size = max(1, int(scrollbar_height * list_height / len(items_to_display)))
            thumb_pos = int(scrollbar_height * scroll_offset / len(items_to_display))
            for i in range(scrollbar_height):
                char = "█" if thumb_pos <= i < thumb_pos + thumb_size else "░"
                self.write_at(list_y_start + i, win_x + win_w - 2, char)

        # --- 안내문 ---
        instructions = "[↑↓]이동 [e]장착/퀵슬롯 [u]사용(소모품/스킬북) [R]버리기 [i]닫기"
        self.write_at(win_y + win_h - 2, win_x + (win_w - get_str_width(instructions)) // 2, instructions)
        logging.debug("_draw_inventory 완료")

    def _draw_full_log_viewer(self, scroll_offset=0):
        logging.debug("_draw_full_log_viewer 호출됨 (스크롤: %d)", scroll_offset)
        win_w, win_h = 70, 22
        win_x = (self.terminal_width - win_w) // 2
        win_y = (self.terminal_height - win_h) // 2
        
        # --- 창 그리기 ---
        border = "┌" + "─" * (win_w - 2) + "┐"
        middle = "│" + " " * (win_w - 2) + "│"
        self.write_at(win_y, win_x, border)
        for i in range(win_h - 2):
            self.write_at(win_y + 1 + i, win_x, middle)
        self.write_at(win_y + win_h - 1, win_x, "└" + "─" * (win_w - 2) + "┘")

        # --- 제목 ---
        title = "전체 메시지 로그"
        self.write_at(win_y, win_x + (win_w - len(title)) // 2, title)

        # --- 로그 내용 그리기 ---
        list_y_start = win_y + 2
        list_height = win_h - 4
        
        # 최신 메시지가 아래에 오도록 로그를 역순으로 표시
        logs_to_display = self.full_message_log
        
        if not logs_to_display:
            self.write_at(list_y_start, win_x + 2, "표시할 메시지가 없습니다.")
        else:
            # 스크롤 오프셋에 맞춰 표시할 로그 선택
            start_index = max(0, len(logs_to_display) - list_height - scroll_offset)
            end_index = max(0, len(logs_to_display) - scroll_offset)
            
            visible_logs = logs_to_display[start_index:end_index]

            for i, log_msg in enumerate(visible_logs):
                self.write_at(list_y_start + i, win_x + 2, pad_str_to_width(log_msg, win_w - 4))

        # --- 스크롤바 (선택적) ---
        if len(logs_to_display) > list_height:
            scrollbar_height = list_height
            thumb_size = max(1, int(scrollbar_height * list_height / len(logs_to_display)))
            
            # 스크롤 위치 계산 (최신 항목이 맨 아래에 오므로 역으로 계산)
            thumb_pos = int(scrollbar_height * (len(logs_to_display) - list_height - scroll_offset) / len(logs_to_display))
            thumb_pos = scrollbar_height - thumb_size - thumb_pos # 역방향

            for i in range(scrollbar_height):
                char = "█" if thumb_pos <= i < thumb_pos + thumb_size else "░"
                self.write_at(list_y_start + i, win_x + win_w - 2, char)

        # --- 안내문 ---
        instructions = "[↑↓]스크롤 [m]닫기"
        self.write_at(win_y + win_h - 2, win_x + (win_w - get_str_width(instructions)) // 2, instructions)
        logging.debug("_draw_full_log_viewer 완료")

    def show_main_menu(self):
        logging.debug("show_main_menu 호출됨")
        self.clear_screen()
        options = ["새 게임", "이어하기", "게임 종료"]
        selected_index = 0
        while True:
            y, x = self.terminal_height // 2 - len(options) // 2, self.terminal_width // 2
            for i, option in enumerate(options):
                prefix = f"{ANSI.YELLOW}> " if i == selected_index else "  "
                self.write_at(y + i, x - len(option) // 2, f"{prefix}{option}{ANSI.RESET}")
            sys.stdout.flush()
            logging.debug("메인 메뉴 렌더링 완료, 입력 대기 중...")
            key = readchar.readkey()
            logging.debug("메인 메뉴 입력 감지: %s", key)
            if key == readchar.key.UP: selected_index = (selected_index - 1) % len(options)
            elif key == readchar.key.DOWN: selected_index = (selected_index + 1) % len(options)
            elif key == readchar.key.ENTER: 
                logging.debug("메인 메뉴 선택: %d", selected_index)
                return selected_index
            elif key == 'q': 
                logging.debug("메인 메뉴에서 'q' 입력, 게임 종료 선택")
                return 2

    def get_player_name(self):
        logging.debug("get_player_name 호출됨")
        self.clear_screen()
        prompt = "용사의 이름을 입력하세요: "
        self.write_at(self.terminal_height // 2 - 1, self.terminal_width // 2 - len(prompt) // 2, prompt)
        sys.stdout.flush()
        sys.stdout.write(ANSI.SHOW_CURSOR)

        name = []
        input_x = self.terminal_width // 2 - len(prompt) // 2 + len(prompt)
        input_y = self.terminal_height // 2 - 1

        while True:
            current_name_str = "".join(name)
            self.write_at(input_y, input_x, pad_str_to_width(current_name_str, 20)) # 최대 20글자 표시
            sys.stdout.flush()
            logging.debug("이름 입력 대기 중 (현재: '%s')", current_name_str)
            key = readchar.readkey()
            logging.debug("이름 입력 감지: %s", key)

            if key == readchar.key.ENTER:
                logging.debug("이름 입력 완료: '%s'", current_name_str)
                break
            elif key == readchar.key.BACKSPACE:
                if name: 
                    name.pop()
                    logging.debug("백스페이스 입력, 현재 이름: '%s'", "".join(name))
            elif len(name) < 20 and key.isprintable(): # 최대 20글자, 출력 가능한 문자만
                name.append(key)
                logging.debug("문자 입력: '%s', 현재 이름: '%s'", key, "".join(name))
        
        sys.stdout.write(ANSI.HIDE_CURSOR)
        final_name = "".join(name) if name else "용사"
        logging.debug("최종 플레이어 이름: '%s'", final_name)
        return final_name

    def write_at(self, y, x, text):
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{text}")

    def show_game_over_screen(self):
        logging.debug("show_game_over_screen 호출됨")
        self.clear_screen()
        msg = "GAME OVER"
        self.write_at(self.terminal_height // 2, self.terminal_width // 2 - len(msg) // 2, msg)
        sys.stdout.flush()
        logging.debug("게임 오버 화면 렌더링 완료, 입력 대기 중...")
        readchar.readkey()
        logging.debug("게임 오버 화면 입력 감지")

    def __del__(self):
        sys.stdout.write(ANSI.SHOW_CURSOR)
        sys.stdout.write("\033[0m")
        self.clear_screen()
        logging.debug("UI 객체 소멸")
