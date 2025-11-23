# ui.py

import sys
import shutil
import re
from typing import List
from wcwidth import wcswidth
import readchar # termios, tty 대체
from . import data_manager # 아이템 정의를 가져오기 위해 추가
from .items import Equipment, SkillBook # 상태 표시를 위해 클래스 임포트
import logging # 로깅 모듈 임포트

# 순환 참조 방지를 위해 타입 힌트를 문자열로 사용
from .component import HealthComponent, ManaComponent, StaminaComponent, ExperienceComponent, AttackComponent, DefenseComponent, LevelComponent, EquipmentComponent, InventoryComponent, SkillComponent, PositionComponent, RenderComponent, NameComponent, ProjectileComponent

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

# 터미널 원시 모드 설정 및 해제 함수
# _original_stty = None # readchar 사용으로 불필요
# def set_raw_mode(): # readchar 사용으로 불필요
#     global _original_stty
#     if sys.stdin.isatty():
#         _original_stty = termios.tcgetattr(sys.stdin)
#         tty.setraw(sys.stdin)
#         logging.debug("터미널 원시 모드 설정됨")
# def unset_raw_mode(): # readchar 사용으로 불필요
#     global _original_stty
#     if sys.stdin.isatty() and _original_stty:
#         termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _original_stty)
#         logging.debug("터미널 원시 모드 해제됨")

class Renderer:
    def __init__(self, map_display_width: int, map_display_height: int):
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()
        # 터미널 크기 보정 (최소값 보장)
        self.terminal_width = max(self.terminal_width, 80)  # 최소 너비 80
        self.terminal_height = max(self.terminal_height, 25) # 최소 높이 25
        logging.debug("UI 초기화: 터미널 크기 - 너비: %d, 높이: %d", self.terminal_width, self.terminal_height)
        self.message_log = []
        self.full_message_log = [] # 전체 메시지 기록
        self.message_log_max_lines = 3 # 화면에 표시될 최대 줄 수
        
        self.MAP_VIEWPORT_WIDTH = map_display_width
        self.MAP_VIEWPORT_HEIGHT = map_display_height
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

        self._buffer = [' ' * self.terminal_width for _ in range(self.terminal_height)] # 더블 버퍼링을 위한 버퍼

        # sys.stdout.write(ANSI.HIDE_CURSOR) # readchar가 커서 관리를 담당
        self.clear_screen()
        # set_raw_mode() # readchar 사용으로 불필요
        logging.debug("UI 초기화 완료")

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")
        self._buffer = [' ' * self.terminal_width for _ in range(self.terminal_height)] # 버퍼 초기화
        logging.debug("화면 지우기")
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

    def draw_game_screen(self, player_entity_id, dungeon_map, monsters, camera_x, camera_y,
                         inventory_open=False, inventory_cursor_pos=0,
                         inventory_active_tab='item', inventory_scroll_offset=0,
                         log_viewer_open=False, log_viewer_scroll_offset=0,
                         game_state='NORMAL', projectile_path=None, impact_effect=None, splash_positions=None):
        logging.debug(f"draw_game_screen 호출됨: player_entity_id={player_entity_id}, camera_x={camera_x}, camera_y={camera_y}")

        logging.debug("draw_game_screen 호출됨")
        if projectile_path is None:
            projectile_path = []
        if splash_positions is None:
            splash_positions = []

        logging.debug("draw_game_screen: _draw_map_and_entities 호출 전.")
        logging.debug(f"draw_game_screen: _draw_map_and_entities 호출 전 - dungeon_map 유효성: {dungeon_map is not None}, 타입: {type(dungeon_map)}")
        if dungeon_map:
            logging.debug(f"draw_game_screen: _draw_map_and_entities 호출 전 - dungeon_map.entity_manager 유효성: {dungeon_map.entity_manager is not None}")
        else:
            logging.debug("draw_game_screen: _draw_map_and_entities 호출 전 - dungeon_map이 None입니다.")
        self._draw_map_and_entities(player_entity_id, dungeon_map, monsters, camera_x, camera_y, projectile_path, impact_effect, splash_positions)
        logging.debug("_draw_map_and_entities 호출 후.")

        # 플레이어 엔티티 ID와 entity_manager를 _draw_player_status에 전달
        if dungeon_map and dungeon_map.entity_manager:
            self._draw_player_status(player_entity_id, dungeon_map.entity_manager)
            self._draw_sidebar(player_entity_id, dungeon_map.entity_manager)
        else:
            logging.warning("draw_game_screen: dungeon_map 또는 entity_manager를 찾을 수 없습니다.")

        if inventory_open:
            self._draw_inventory(player_entity_id, dungeon_map.entity_manager, inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset)
        elif log_viewer_open:
            self._draw_full_log_viewer(log_viewer_scroll_offset)

        sys.stdout.flush()
        logging.debug("draw_game_screen 완료")

    def _draw_map_and_entities(self, player_entity_id, dungeon_map, monsters, camera_x, camera_y, projectile_path=None, impact_effect=None, splash_positions=None):

        logging.debug("_draw_map_and_entities: 함수 시작")
        logging.debug(f"_draw_map_and_entities: dungeon_map 유효성: {dungeon_map is not None}, 타입: {type(dungeon_map)}")
        logging.debug(f"_draw_map_and_entities: dungeon_map.entity_manager 유효성: {dungeon_map.entity_manager is not None}")
        
        player_pos = dungeon_map.entity_manager.get_component(player_entity_id, PositionComponent)
        player_render_comp = dungeon_map.entity_manager.get_component(player_entity_id, RenderComponent)
        
        logging.debug(f"_draw_map_and_entities: player_pos 유효성: {player_pos is not None}, player_render_comp 유효성: {player_render_comp is not None}")

        if not player_pos or not player_render_comp: 
            logging.warning("플레이어 위치 또는 렌더 컴포넌트를 찾을 수 없습니다.")
            return # 플레이어 위치 없으면 그리지 않음
        logging.debug("플레이어 위치: (%d, %d) on map %s", player_pos.x, player_pos.y, player_pos.map_id)
        logging.debug("플레이어 렌더 컴포넌트: symbol='%s', color='%s'", player_render_comp.symbol, player_render_comp.color)

        if projectile_path is None:
            projectile_path = []
        if splash_positions is None:
            splash_positions = []

        # 몬스터 위치를 entity_manager에서 가져오도록 변경
        monster_positions = {}
        logging.debug("_draw_map_and_entities: 몬스터 위치 가져오기 시작")
        if dungeon_map.entity_manager:
            for entity_id, name_comp in dungeon_map.entity_manager.get_components_of_type(NameComponent).items():
                if name_comp.name not in ["Player", "Trap", "Item"] and entity_id != player_entity_id: # 플레이어, 함정, 아이템 제외
                    pos_comp = dungeon_map.entity_manager.get_component(entity_id, PositionComponent)
                    render_comp = dungeon_map.entity_manager.get_component(entity_id, RenderComponent)
                    health_comp = dungeon_map.entity_manager.get_component(entity_id, HealthComponent)
                    if pos_comp and render_comp and health_comp and health_comp.current_hp > 0:
                        monster_positions[(pos_comp.x, pos_comp.y)] = f"{getattr(ANSI, render_comp.color.upper(), ANSI.WHITE)}{render_comp.symbol}{ANSI.RESET}"
                        logging.debug(f"_draw_map_and_entities: 몬스터 발견 - ID: {entity_id}, 이름: {name_comp.name}, 위치: ({pos_comp.x}, {pos_comp.y}), 심볼: {render_comp.symbol}, 색상: {render_comp.color}")
        logging.debug("_draw_map_and_entities: 몬스터 위치 가져오기 완료. 총 {len(monster_positions)}마리.")

        # 발사체 위치를 entity_manager에서 가져오도록 변경
        projectile_positions = {}
        logging.debug("_draw_map_and_entities: 발사체 위치 가져오기 시작")
        if dungeon_map.entity_manager:
            for entity_id, proj_comp in dungeon_map.entity_manager.get_components_of_type(ProjectileComponent).items():
                pos_comp = dungeon_map.entity_manager.get_component(entity_id, PositionComponent)
                render_comp = dungeon_map.entity_manager.get_component(entity_id, RenderComponent)
                if pos_comp and render_comp:
                    projectile_positions[(pos_comp.x, pos_comp.y)] = f"{getattr(ANSI, render_comp.color.upper(), ANSI.YELLOW)}{render_comp.symbol}{ANSI.RESET}"
                    logging.debug(f"_draw_map_and_entities: 발사체 발견 - ID: {entity_id}, 위치: ({pos_comp.x}, {pos_comp.y}), 심볼: {render_comp.symbol}, 색상: {render_comp.color}")
        logging.debug("_draw_map_and_entities: 발사체 위치 가져오기 완료. 총 {len(projectile_positions)}개.")

        logging.debug("_draw_map_and_entities: 맵 렌더링 루프 진입 전.")
        for y_offset in range(self.MAP_VIEWPORT_HEIGHT):
            draw_y = self.map_viewport_y_start + y_offset
            line_to_write = []

            for x_offset in range(self.MAP_VIEWPORT_WIDTH):
                map_x, map_y = camera_x + x_offset, camera_y + y_offset

                final_char_to_draw = ' ' # 기본값
                
                is_visible = (0 <= map_x < dungeon_map.width and 0 <= map_y < dungeon_map.height and \
                              (not dungeon_map.fog_enabled or (map_x, map_y) in dungeon_map.visited))
                logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - is_visible: {is_visible}")
                
                if is_visible:
                    # 맵 타일 그리기 (색상 포함)
                    tile_display_char = dungeon_map.get_tile_for_display(map_x, map_y)
                    final_char_to_draw = tile_display_char
                    logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - get_tile_for_display 반환: '{tile_display_char}'")
                    logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 기본 타일: '{final_char_to_draw}'")

                    # 오버레이 (우선순위: 플레이어 > 발사체 > 임팩트 > 스플래시 > 몬스터 > 아이템/함정)
                    if map_x == player_pos.x and map_y == player_pos.y:
                        final_char_to_draw = f"{getattr(ANSI, player_render_comp.color.upper(), ANSI.WHITE)}{player_render_comp.symbol}{ANSI.RESET}"
                        logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 플레이어 오버레이: '{final_char_to_draw}'")
                    elif (map_x, map_y) in projectile_positions:
                        final_char_to_draw = projectile_positions[(map_x, map_y)]
                        logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 발사체 오버레이: '{final_char_to_draw}'")
                    elif impact_effect and map_x == impact_effect['x'] and map_y == impact_effect['y']:
                        final_char_to_draw = f"{ANSI.RED}X{ANSI.RESET}" # 임팩트 효과
                        logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 임팩트 오버레이: '{final_char_to_draw}'")
                    elif (map_x, map_y) in splash_positions:
                        final_char_to_draw = f"{ANSI.CYAN}*{ANSI.RESET}" # 스플래시 효과
                        logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 스플래시 오버레이: '{final_char_to_draw}'")
                    elif (map_x, map_y) in monster_positions:
                        final_char_to_draw = monster_positions[(map_x, map_y)]
                        logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 몬스터 오버레이: '{final_char_to_draw}'")
                    # 아이템 및 함정은 get_tile_for_display에서 이미 처리되므로 여기서는 생략
                else:
                    final_char_to_draw = f"{ANSI.BLACK}{' '}{ANSI.RESET}" # 안개 또는 맵 밖은 검은색 공백
                    logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y}) - 안개/맵 밖: '{final_char_to_draw}'")

                line_to_write.append(final_char_to_draw)
            
            self._buffer[draw_y] = ''.join(line_to_write)
        logging.debug("_draw_map_and_entities 완료")
        logging.debug("_draw_map_and_entities 완료")

    def _draw_player_status(self, player_entity_id, entity_manager):
        self.add_message("디버그: _draw_player_status 호출됨")
        logging.debug("_draw_player_status 호출됨")
        y_start = self.status_bar_y_start
        x_start = self.map_viewport_x_start
        
        # 이전 상태 표시줄을 지웁니다.
        for i in range(10): # 충분한 라인을 지웁니다.
             self.write_at(y_start + i, x_start, " " * self.MAP_VIEWPORT_WIDTH)

        # 필요한 컴포넌트 가져오기
        health_comp = entity_manager.get_component(player_entity_id, HealthComponent)
        mana_comp = entity_manager.get_component(player_entity_id, ManaComponent)
        stamina_comp = entity_manager.get_component(player_entity_id, StaminaComponent)
        exp_comp = entity_manager.get_component(player_entity_id, ExperienceComponent)
        attack_comp = entity_manager.get_component(player_entity_id, AttackComponent)
        defense_comp = entity_manager.get_component(player_entity_id, DefenseComponent)
        level_comp = entity_manager.get_component(player_entity_id, LevelComponent)

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
        if health_comp:
            hp_text = pad_str_to_width(f"HP: {health_comp.current_hp}/{health_comp.max_hp}", 18)
            hp_bar = draw_bar(health_comp.current_hp, health_comp.max_hp, ANSI.RED)
            self.write_at(y_start, x_start, f"{hp_text} {hp_bar}")

        if mana_comp:
            mp_text = pad_str_to_width(f"MP: {mana_comp.current_mp}/{mana_comp.max_mp}", 18)
            mp_bar = draw_bar(mana_comp.current_mp, mana_comp.max_mp, ANSI.BLUE)
            self.write_at(y_start + 1, x_start, f"{mp_text} {mp_bar}")

        if stamina_comp:
            stamina_text = pad_str_to_width(f"Stamina: {int(stamina_comp.current_stamina)}/{int(stamina_comp.max_stamina)}", 18)
            stamina_bar = draw_bar(stamina_comp.current_stamina, stamina_comp.max_stamina, ANSI.YELLOW)
            self.write_at(y_start + 2, x_start, f"{stamina_text} {stamina_bar}")
        
        if exp_comp and level_comp:
            exp_text = pad_str_to_width(f"EXP: {exp_comp.current_exp}/{exp_comp.exp_to_next_level}", 18)
            exp_bar = draw_bar(exp_comp.current_exp, exp_comp.exp_to_next_level, ANSI.GREEN)
            self.write_at(y_start + 3, x_start, f"{exp_text} {exp_bar}")

        # Other stats
        att_val = attack_comp.power if attack_comp else 0
        def_val = defense_comp.value if defense_comp else 0
        level_val = level_comp.level if level_comp else 1

        other_stats_line1 = f"ATT: {att_val}   DEF: {def_val}"
        other_stats_line2 = f"Lv: {level_val}"
        
        self.write_at(y_start + 4, x_start, pad_str_to_width(other_stats_line1, self.MAP_VIEWPORT_WIDTH))
        self.write_at(y_start + 5, x_start, pad_str_to_width(other_stats_line2, self.MAP_VIEWPORT_WIDTH))
        logging.debug("_draw_player_status 완료")

    def _draw_sidebar(self, player_entity_id, entity_manager):
        self.add_message("디버그: _draw_sidebar 호출됨")
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
        
        equipment_comp = entity_manager.get_component(player_entity_id, EquipmentComponent)

        equipment_slots = {
            "머리": "head", "몸통": "body", "장갑": "hands", "신발": "feet",
            "손1": "main_hand", "손2방패": "off_hand", 
            "액세서리1": "accessory1", "액세서리2": "accessory2"
        }
        
        for i, (display_name, slot_key) in enumerate(equipment_slots.items()):
            item = getattr(equipment_comp, slot_key, None) if equipment_comp else None
            item_name = item.name if item else "비어있음"
            text = f"{display_name}: {item_name}"
            self.write_at(eq_y + 1 + i, x, pad_str_to_width(text, w))

        # --- 3. Inventory (Item Quick Slots) ---
        inv_y = self.inventory_y_start
        self.write_at(inv_y, x, pad_str_to_width('--- 퀵 슬롯 ---', w, align='center'))
        inventory_comp = entity_manager.get_component(player_entity_id, InventoryComponent)
        if inventory_comp:
            for i in range(1, 6):
                item_id = inventory_comp.item_quick_slots.get(i)
                text = f"{i}: 비어있음"
                if item_id:
                    item_def = data_manager.get_item_definition(item_id)
                    if item_def:
                        item_qty = inventory_comp.items.get(item_id, 0)
                        text = f"{i}: {item_def.name} x{item_qty}"
                
                self.write_at(inv_y + 1 + (i-1), x, pad_str_to_width(text, w))

        # --- 4. Skills ---
        skill_y = self.skills_y_start
        self.write_at(skill_y, x, pad_str_to_width('--- 스킬 ---', w, align='center'))
        skill_comp = entity_manager.get_component(player_entity_id, SkillComponent)
        level_comp = entity_manager.get_component(player_entity_id, LevelComponent)
        skill_slots = list(range(6, 10)) + [0]
        if skill_comp and level_comp:
            for i, slot_num in enumerate(skill_slots):
                actual_slot_num = 10 if slot_num == 0 else slot_num
                skill_id = skill_comp.skill_quick_slots.get(actual_slot_num)
                
                text_to_display = f"{slot_num}: 비어있음"
                if skill_id:
                    skill_def = data_manager.get_skill_definition(skill_id)
                    if skill_def:
                        skill_info = skill_comp.skills.get(skill_id, {'level': 1, 'exp': 0})
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
            logging.debug("렌더링될 메인 메뉴 옵션: %s, 선택됨: %d", options, selected_index)
            sys.stdout.flush()
            import time
            time.sleep(0.1) # 디버깅을 위해 짧은 지연 추가
            logging.debug("메인 메뉴 렌더링 완료, 입력 대기 중...")
            key = self.get_full_key_input() # 단일 문자 입력 받기
            logging.debug("메인 메뉴 입력 감지: %s", key)
            if key == readchar.key.UP: selected_index = (selected_index - 1) % len(options) # UP
            elif key == readchar.key.DOWN: selected_index = (selected_index + 1) % len(options) # DOWN
            elif key == readchar.key.ENTER: # ENTER
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
        input_x = self.terminal_width // 2 - get_str_width(prompt) // 2 + get_str_width(prompt)
        input_y = self.terminal_height // 2 - 1

        while True:
            current_name_str = "".join(name)
            logging.debug("이름 입력 필드: input_x=%d, input_y=%d, 현재 이름='%s' (너비: %d)", input_x, input_y, current_name_str, get_str_width(current_name_str))
            self.write_at(input_y, input_x, pad_str_to_width(current_name_str, 20)) # 최대 20글자 표시
            sys.stdout.flush()
            logging.debug("이름 입력 대기 중 (현재: '%s')", current_name_str)
            key = self.get_full_key_input() # 단일 문자 입력 받기
            logging.debug("이름 입력 감지: %s", key)

            if key == readchar.key.ENTER: # ENTER
                if not name: # 이름이 비어있으면 엔터 무시 (최소 한 글자 입력 강제)
                    continue
                logging.debug("이름 입력 완료: '%s'", current_name_str)
                break
            elif key == readchar.key.BACKSPACE: # BACKSPACE
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
        # 버퍼에 텍스트를 씁니다.
        if 0 <= y < self.terminal_height and 0 <= x < self.terminal_width:
            current_line = list(self._buffer[y])
            # ANSI 이스케이프 코드를 고려하여 텍스트를 버퍼에 병합
            clean_text = ansi_escape_pattern.sub('', text)
            text_width = wcswidth(clean_text)

            # 현재 줄의 특정 위치에 새 텍스트를 덮어씁니다.
            # ANSI 코드를 포함한 문자열을 직접 할당하지 않고, 기존 버퍼에 덮어씌우는 방식.
            # 더블 버퍼링은 항상 전체 라인을 다시 그리는 방식으로 동작한다고 가정합니다.
            # 따라서 여기서는 특정 위치에 텍스트를 "쓰는" 것이 아니라,
            # 단순히 해당 라인의 텍스트를 업데이트하는 것으로 충분합니다.
            # 그러나 기존 `write_at`의 의도가 특정 x, y 위치에 문자열을 쓰는 것이므로,
            # `pad_str_to_width`를 이용하여 기존 라인과 새 텍스트를 병합합니다.

            # 가장 간단한 접근: 전체 라인을 지우고 다시 쓰는 방식 (성능은 좋지 않지만 구현 용이)
            # 여기서는 `self._buffer[y]`의 `x` 위치부터 `text`를 덮어씁니다.
            # 이스케이프 시퀀스를 유지하면서 버퍼에 쓰는 것은 복잡하므로, 일단은 `clean_text`와 길이만 고려.

            # 실제 출력될 줄을 만들기 위해, 현재 버퍼 줄의 x 위치부터 text를 삽입
            # 단, ANSI 코드가 있을 수 있으므로 wcswidth를 정확히 사용하는 것이 중요
            # 여기서는 단순히 버퍼의 해당 부분을 업데이트한다고 가정
            # 더블 버퍼링의 '버퍼'는 최종 출력될 ANSI 컬러 코드가 포함된 문자열이라고 가정합니다.
            # 즉, _buffer[y]는 이미 최종 렌더링될 문자열 형태여야 합니다.

            # 먼저 해당 라인을 'clean'하게 만듭니다. (덮어씌울 영역만)
            # 그리고 그 위에 새로운 텍스트를 병합합니다.

            # 이중 버퍼링의 목표는 최종 렌더링될 상태를 버퍼에 완벽하게 만드는 것
            # 따라서, write_at은 해당 (y,x)에 text를 정확히 반영해야 함

            # 가장 단순한 구현 (전체 라인을 다시 구성하지 않고 부분적으로 수정)
            current_line_str = self._buffer[y]
            # 기존 ANSI 코드를 유지하며 덮어씌우는 것은 매우 복잡 -> 간단하게 처리
            # 여기서는 write_at이 호출될 때마다 해당 라인의 텍스트를 새로 구성한다고 가정
            # 이 구현은 이전 write_at과 동일하게 버퍼를 직접 수정하지 않고,
            # refresh()에서 한번에 처리될 수 있도록 문자열을 반환하는 방식이 더 적합할 수 있음
            # 하지만 현재 _draw_xxx 함수들은 write_at을 호출하므로, write_at이 버퍼를 수정해야 함.

            # 단순화를 위해, 버퍼는 이미 렌더링된 형태의 문자열을 가지고 있다고 가정하고,
            # 그 위에 새로운 텍스트를 덮어씌웁니다.
            # 이 경우, 텍스트의 실제 너비를 고려하여 덮어씌워야 합니다.

            # Option 1: 이전 라인을 먼저 지우고 다시 쓰는 방식 (효율은 떨어지나 정확)
            # current_line = [' ' for _ in range(self.terminal_width)] # 빈 줄 생성
            # self._buffer[y] = ''.join(current_line)

            # Option 2: 기존 라인에서 변경 부분만 덮어쓰기 (복잡)
            # 현재는 Option 1에 가까운 방식으로, write_at이 호출될 때마다 해당 버퍼 라인을 새로 구성

            # 이스케이프 코드를 가진 문자열을 안전하게 덮어쓰기 위해, 먼저 해당 영역을 공백으로 채웁니다.
            # 단, ANSI 이스케이프 코드를 인식해야 함.
            # 임시로, 단순 문자열 길이로 처리 (불완전)

            # 가장 간단하고 안전한 방법: _buffer는 렌더링될 최종 문자열을 저장한다.
            # write_at은 해당 위치에 텍스트를 '병합'한다.
            # 이스케이프 시퀀스를 가진 문자열을 병합할 때는 WCWIDTH를 고려해야 함.
            # 현재 _buffer[y]는 이미 ANSI 코드를 포함한 문자열일 수 있습니다.

            # `pad_str_to_width`를 사용하여 `text`의 실제 너비를 얻고,
            # `current_line`을 업데이트합니다.

            # 새로운 접근: _buffer는 최종적으로 터미널에 쓰여질 문자열 배열. 
            # write_at은 이 버퍼의 특정 y, x 위치에 text를 삽입. 
            # ANSI 코드 처리: text에 ANSI 코드가 포함될 경우, wcswidth로 실제 너비를 계산하여 삽입. 
            
            # 1. 현재 버퍼 라인의 클린 텍스트와 ANSI 코드 파트를 분리하는 함수 필요 (복잡)
            # 2. 아니면, write_at을 호출하기 전에 항상 전체 라인을 새로 구성하도록 각 _draw_xxx 함수 수정 (더 나은 방식)

            # 현재 `write_at`은 `sys.stdout.write`를 직접 호출하므로, 버퍼링되지 않습니다.
            # 이것을 버퍼에 쓰는 방식으로 변경해야 합니다.

            # 현재 `write_at`을 사용하는 모든 곳에서 `sys.stdout.flush()` 호출이 없으므로,
            # `_buffer`에만 쓰는 것으로 변경해도 됩니다.
            # `refresh` 함수가 최종적으로 `sys.stdout.write`를 호출합니다.

            # 버퍼에 직접 쓰고, `refresh` 시 모든 버퍼를 렌더링
            # `final_line`의 길이를 계산하여 `current_line`에 덮어쓰기

            # `_buffer`를 직접 수정하는 방식으로 변경
            current_line_list = list(self._buffer[y])
            # x 위치부터 텍스트를 덮어씁니다.
            # ANSI 코드가 있는 경우 처리가 복잡해지므로, 현재는 텍스트의 '보이는' 길이를 기준으로 처리.
            # 이스케이프 시퀀스를 무시하고 보이는 문자열 길이만큼 덮어씌웁니다.
            clean_new_text = ansi_escape_pattern.sub('', text)
            actual_new_text_width = wcswidth(clean_new_text)

            # 텍스트를 버퍼에 직접 삽입
            # ANSI 코드를 포함한 문자열을 직접 버퍼에 저장하고,
            # wcswidth를 사용하여 길이를 계산하고, 이 길이만큼 기존 버퍼 내용을 교체해야 합니다.

            # 가장 단순한 구현으로, 버퍼의 해당 y, x 위치에 'text'를 덮어씁니다.
            # 이때, 'text'는 ANSI 코드를 포함한 최종 출력 문자열이어야 합니다.

            # Option 1: 현재 라인을 완전히 지우고 다시 쓰는 방식 (확실하지만 비효율적)
            # self._buffer[y] = ' ' * self.terminal_width
            # self._buffer[y] = self._buffer[y][:x] + text + self._buffer[y][x + get_str_width(text):]

            # Option 2 (선택): 라인 전체를 새롭게 구성 (현재 _draw_map_and_entities에서 사용)
            # 이 경우에는 `write_at`을 사용하는 대신, 각 `_draw_xxx` 함수에서 `line_to_write`를 만들고,
            # 마지막에 `_buffer[y] = ''.join(line_to_write)` 하는 방식이 더 일관될 수 있습니다.

            # 현재 `write_at`이 `_draw_player_status` 등에서 호출되므로,
            # `_buffer[y]`의 특정 `x` 위치에 `text`를 `text`의 실제 너비만큼 덮어씌우는 것이 필요합니다.

            # 이스케이프 시퀀스를 유지하면서 버퍼에 덮어쓰는 것은 까다롭습니다.
            # 가장 현실적인 구현은, `_buffer`를 `List[List[str]]`로 만들어서 각 문자를 저장하고,
            # 렌더링 시점에 ANSI 코드를 붙여서 문자열로 합치는 것입니다.
            # 하지만 현재 `_buffer`는 `List[str]`입니다. 이 구조를 유지하려면,
            # `write_at`은 `_buffer[y]`의 `x` 위치에 `text`를 병합해야 합니다.

            # 여기서는 `_buffer[y]`의 해당 `x` 위치에 `text`를 삽입하고,
            # `text`의 `wcswidth` 길이를 고려하여 기존 내용을 대체하는 방식으로 구현합니다.

            # 현재 `_buffer[y]`는 이미 `ANSI` 코드를 포함한 문자열일 수 있습니다.
            # 따라서 `ansi_escape_pattern.sub('', self._buffer[y])`를 사용하여 클린 텍스트를 얻고
            # `wcswidth`로 길이를 계산해야 합니다.

            # 이는 `_draw_map_and_entities`의 `final_line` 생성 방식과 일치하도록 변경하는 것이 목표입니다.
            # 따라서, `write_at`도 버퍼의 특정 라인(y)에 `final_line`과 유사하게 쓰도록 변경해야 합니다.

            # 기존 `_buffer[y]`의 내용을 가져와서,
            # `x` 위치에 `text`를 삽입하고, 남은 부분을 다시 붙이는 방식
            # 이 때, `text`의 실제 너비만큼 기존 문자를 덮어씌워야 합니다.

            # Step 1: 현재 라인에서 x 위치 이전의 부분
            before_x = self._buffer[y][:x]
            # Step 2: 삽입할 텍스트 (ansi 코드 포함)
            # Step 3: 삽입할 텍스트 이후의 부분
            #   - 기존 라인에서 x + text_width 이후부터 가져와야 함
            #   - 이때 text_width는 ansi 코드를 제거한 실제 너비여야 함

            # 이 복잡성을 피하기 위해 `write_at`을 사용하는 모든 곳에서
            # `line_to_write` 패턴을 사용하도록 변경하는 것이 더 합리적일 수 있습니다.

            # 임시로 `write_at`이 `_buffer[y]` 전체를 덮어쓰지 않고,
            # `x` 위치부터 `text`를 삽입하는 것으로 변경.

            current_line_content = self._buffer[y]
            # 텍스트가 시작될 위치부터 덮어쓰기 위해, 기존 문자열을 잘라내고 새 문자열을 삽입
            # 단, ANSI 이스케이프 코드는 문자열 길이에 포함되지 않으므로, wcswidth 사용
            
            # `text`의 실제 너비
            text_display_width = get_str_width(text)
            
            # `x` 위치에서 `text_display_width`만큼의 공간을 확보한 후 `text`를 삽입
            # 기존 버퍼에서 `x` 이전 부분 + `text` + `x + text_display_width` 이후 부분
            
            # `current_line_content`를 리스트로 변환하여 인덱싱 문제 해결
            line_chars = list(current_line_content)
            
            # `text`가 ANSI 코드를 포함하고 있을 수 있으므로, 직접 삽입하는 방식은 어려움.
            # 가장 좋은 방법은 `_buffer`가 `List[List[Tuple[str, str]]]` 형태로 (char, color)를 저장하고,
            # `_render_buffer_to_screen`에서 최종 문자열을 구성하는 것입니다.
            # 그러나 현재 `_buffer`는 `List[str]`이므로, 이를 유지해야 합니다.

            # `write_at`이 호출될 때마다 해당 라인(`self._buffer[y]`)을 수정해야 합니다.
            # `ANSI.cursor_to`는 화면에 직접 쓰는 것이 아니라 커서 위치를 지정하는 코드이므로,
            # `self._buffer[y]`에 `f"{ANSI.cursor_to(y, x)}{text}"`와 같은 형식으로 저장하는 것은 맞지 않습니다.

            # 대신, `self._buffer[y]`는 화면에 그려질 최종 문자열이어야 합니다.
            # `write_at`은 `self._buffer[y]`의 특정 부분을 `text`로 업데이트해야 합니다.

            # `self._buffer[y]`를 수정하는 방식으로 변경
            # `text`는 이미 색상 코드를 포함한 문자열이라고 가정합니다.

            # `pad_str_to_width`를 사용하여 `text`의 길이에 맞춰 기존 내용을 덮어씁니다.
            # 이 함수는 주로 빈 공간을 채우는 데 사용되지만, 여기서는 `text` 길이만큼의 공간을 확보합니다.
            # 이스케이프 시퀀스를 포함한 `text`를 정확히 덮어쓰기 위해선 더 정교한 로직이 필요합니다.

            # 현재 `write_at` 구현은 `sys.stdout.write`를 직접 사용하고 있습니다.
            # 이 부분을 `self._buffer`에 쓰는 것으로 변경해야 합니다.

            # `_buffer`에 쓸 때는 ANSI 코드를 포함한 문자열을 그대로 저장합니다.
            # `get_str_width`를 사용하여 `text`의 실제 길이만큼 기존 버퍼 내용을 덮어씌웁니다.

            # 새로운 버퍼 라인 생성: 기존 라인 + 새 텍스트 + 기존 라인 나머지
            # 현재 버퍼 라인 (`self._buffer[y]`)을 가져와서 리스트로 변환
            line_list = list(self._buffer[y])

            # 삽입할 텍스트의 실제 너비 계산 (ANSI 코드 제외)
            clean_text_width = get_str_width(text)

            # 기존 라인에서 텍스트가 들어갈 위치까지 잘라내기
            prefix = "".join(line_list[:x])

            # 텍스트가 삽입된 후 남은 부분 (기존 라인에서 텍스트 길이만큼 제외)
            suffix_start_index = x + clean_text_width
            suffix = "".join(line_list[suffix_start_index:])

            # 새로운 라인 조립
            new_line = prefix + text + suffix
            self._buffer[y] = new_line


    def refresh(self):
        """버퍼의 내용을 화면에 렌더링하고 버퍼를 지웁니다."""
        self._render_buffer_to_screen()
        self._buffer = [' ' * self.terminal_width for _ in range(self.terminal_height)] # 버퍼 초기화

    def _render_buffer_to_screen(self):
        sys.stdout.write(ANSI.cursor_to(0, 0)) # 커서를 화면 맨 위로 이동
        for y in range(self.terminal_height):
            sys.stdout.write(self._buffer[y])
        sys.stdout.flush()

    def get_full_key_input(self):
        logging.debug("get_full_key_input: 입력 대기 중...")
        try:
            char = readchar.readkey()
            logging.debug("get_full_key_input: 키 감지됨 - '%s'", repr(char))
            return char
        except KeyboardInterrupt:
            logging.debug("KeyboardInterrupt 감지됨. None 반환.")
            return None

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
            logging.debug("렌더링될 메인 메뉴 옵션: %s, 선택됨: %d", options, selected_index)
            sys.stdout.flush()
            import time
            time.sleep(0.1) # 디버깅을 위해 짧은 지연 추가
            logging.debug("메인 메뉴 렌더링 완료, 입력 대기 중...")
            key = self.get_full_key_input() # 단일 문자 입력 받기
            if key is None: # KeyboardInterrupt 발생 시
                logging.debug("메인 메뉴에서 KeyboardInterrupt 감지, 게임 종료")
                return 2 # "게임 종료" 선택으로 간주
            logging.debug("메인 메뉴 입력 감지: %s", key)
            if key == readchar.key.UP: selected_index = (selected_index - 1) % len(options) # UP
            elif key == readchar.key.DOWN: selected_index = (selected_index + 1) % len(options) # DOWN
            elif key == readchar.key.ENTER: # ENTER
                logging.debug("메인 메뉴 선택: %d", selected_index)
                return selected_index
            elif key == 'q': 
                logging.debug("메인 메뉴에서 'q' 입력, 게임 종료 선택")
                return 2

    def get_player_name(self):
        logging.debug("get_player_name 호출됨")
        self.clear_screen()
        prompt = "용사의 이름을 입력하세요: "
        
        # 프롬프트의 시작 X 위치 계산 (중앙 정렬)
        prompt_x_start = self.terminal_width // 2 - get_str_width(prompt) // 2
        prompt_y = self.terminal_height // 2 - 1
        self.write_at(prompt_y, prompt_x_start, prompt)
        sys.stdout.flush()
        sys.stdout.write(ANSI.SHOW_CURSOR)

        name = []
        # 입력 필드의 시작 X 위치는 프롬프트의 끝 바로 다음
        input_x = prompt_x_start + get_str_width(prompt)
        input_y = prompt_y
        max_input_width = 20 # 최대 입력 길이 (표시용)

        while True:
            current_name_str = "".join(name)
            logging.debug("이름 입력 필드: input_x=%d, input_y=%d, 현재 이름='%s' (너비: %d)", input_x, input_y, current_name_str, get_str_width(current_name_str))
            
            # 입력 필드 영역을 먼저 지웁니다.
            self.write_at(input_y, input_x, " " * max_input_width)
            # 현재 이름을 출력합니다.
            self.write_at(input_y, input_x, pad_str_to_width(current_name_str, max_input_width))
            sys.stdout.flush()
            logging.debug("이름 입력 대기 중 (현재: '%s')", current_name_str)
            key = self.get_full_key_input() # 단일 문자 입력 받기

            if key == readchar.key.ENTER: # ENTER
                if not name: # 이름이 비어있으면 엔터 무시 (최소 한 글자 입력 강제)
                    continue
                logging.debug("이름 입력 완료: '%s'", current_name_str)
                break
            elif key == readchar.key.BACKSPACE: # BACKSPACE
                if name: 
                    name.pop()
                    logging.debug("백스페이스 입력, 현재 이름: '%s'", "".join(name))
            elif len(name) < 20 and key and isinstance(key, str) and key.isprintable(): # 최대 20글자, 출력 가능한 문자만
                name.append(key)
                logging.debug("문자 입력: '%s', 현재 이름: '%s'", key, "".join(name))
            
        sys.stdout.write(ANSI.HIDE_CURSOR)
        final_name = "".join(name) if name else "용사"
        logging.debug("최종 플레이어 이름: '%s'", final_name)
        return final_name

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
        sys.stdout.write("\033[0m")
        self.clear_screen()
        logging.debug("UI 객체 소멸")
