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

class UI:
    def __init__(self):
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()
        # 터미널 크기 보정 (최소값 보장)
        self.terminal_width = max(self.terminal_width, 80)  # 최소 너비 80
        self.terminal_height = max(self.terminal_height, 25) # 최소 높이 25
        logging.debug("UI 초기화: 터미널 크기 - 너비: %d, 높이: %d", self.terminal_width, self.terminal_height)
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
        self.add_message("디버그: draw_game_screen 호출됨")
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
        self.add_message("디버그: _draw_map_and_entities 호출됨")
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
                logging.debug(f"_draw_map_and_entities: ({map_x}, {map_y})에 렌더링될 문자: '{final_char_to_draw}'")
            
            final_line = ''.join(line_to_write)
            sys.stdout.write(f"{ANSI.cursor_to(draw_y, self.map_viewport_x_start)}{final_line}")
            sys.stdout.flush() # 각 줄을 그린 후 즉시 화면에 반영
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
        sys.stdout.write(f"{ANSI.cursor_to(y, x)}{text}")

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
        # unset_raw_mode() # readchar 사용으로 불필요
        # sys.stdout.write(ANSI.SHOW_CURSOR) # readchar가 커서 관리를 담당
        sys.stdout.write("\033[0m")
        self.clear_screen()
        logging.debug("UI 객체 소멸")


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
        # unset_raw_mode() # readchar 사용으로 불필요
        # sys.stdout.write(ANSI.SHOW_CURSOR) # readchar가 커서 관리를 담당
        sys.stdout.write("\033[0m")
        self.clear_screen()
        logging.debug("UI 객체 소멸")
