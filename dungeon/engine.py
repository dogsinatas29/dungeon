# game.py

import sys
import time
import math
from .player import Player
from .map_manager import DungeonMap, EXIT_NORMAL, EXIT_LOCKED, ITEM_TILE, ROOM_ENTRANCE
from .renderer import UI, ANSI
import readchar
from . import data_manager
from . import combat
import random
from .items import Item
from .monster import Monster

def calculate_line_path(x1, y1, x2, y2):
    """Bresenham's line algorithm을 사용하여 두 점 사이의 경로를 계산합니다."""
    path = []
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    
    x, y = x1, y1
    
    while True:
        path.append((x, y))
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
            
    # 시작점은 제외하고 경로 반환
    return path[1:]

def run_game(player_data_from_save, all_dungeon_maps_data_from_save_raw, item_definitions, ui_instance):
    
    monster_definitions = data_manager.load_monster_definitions(ui_instance)

    def get_or_create_map(level, all_maps, ui, items_def, monster_defs, is_boss_room=False):
        if level in all_maps:
            d_map = all_maps[level]
            d_map.ui_instance = ui
            
            # --- 몬스터 리젠 로직 ---
            # 기존 몬스터 목록을 초기화하고 새로 배치합니다.
            d_map.monsters.clear()
            if level[1] > 0: # 방인 경우
                if not is_boss_room:
                    d_map.place_monsters(monster_defs, num_monsters=random.randint(1, 3))
            else: # 메인 맵인 경우
                d_map.place_monsters(monster_defs)
            
            return d_map
        else:
            d_map = DungeonMap(level, ui, is_boss_room=is_boss_room, monster_definitions=monster_defs)
            if level[1] > 0: # 방인 경우
                if not is_boss_room:
                    d_map.place_monsters(monster_defs, num_monsters=random.randint(1, 3))
                    d_map.place_random_items(items_def, num_items=random.randint(0, 2))
            else: # 메인 맵인 경우
                d_map.place_monsters(monster_defs)
                d_map.place_random_items(items_def)
            all_maps[level] = d_map
            return d_map

    player = Player.from_dict(player_data_from_save)
    camera = {'x': 0, 'y': 0}
    last_entrance_position = {}
    
    inventory_open = False
    inventory_cursor_pos = 0
    inventory_active_tab = 'item'
    inventory_scroll_offset = 0

    log_viewer_open = False
    log_viewer_scroll_offset = 0

    all_dungeon_maps = {}
    if all_dungeon_maps_data_from_save_raw:
        for level_str, map_dict in all_dungeon_maps_data_from_save_raw.items():
            floor, room_index = map(int, level_str.split(','))
            all_dungeon_maps[(floor, room_index)] = DungeonMap.from_dict(map_dict)

    current_dungeon_level = player.dungeon_level
    dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions)

    player.x, player.y = dungeon_map.player_x, dungeon_map.player_y

    game_over_flag = False
    ui_instance.clear_screen()

    turn_count = 0
    rest_turn_count = 0

    game_state = 'NORMAL'
    aiming_skill = None
    
    # --- 애니메이션 관련 변수 ---
    animation_data = None

    def handle_animation():
        nonlocal animation_data, game_state, player_action_taken
        
        if not animation_data:
            game_state = 'NORMAL'
            return

        path = animation_data.get('path', [])
        skill_def = animation_data.get('skill_def') # 스킬 정보 가져오기

        # 애니메이션 재생
        if path:
            current_pos = path.pop(0)
            animation_data['current_pos'] = [current_pos]
        # 애니메이션 종료 (충돌)
        else:
            impact_pos = animation_data.get('impact_pos')
            
            # 스킬 속성에 따른 시각 효과 결정
            impact_symbol = '💥'
            impact_color = ANSI.RED
            if skill_def:
                if skill_def.attribute == '물':
                    impact_symbol = '❄️'
                    impact_color = ANSI.CYAN
                elif skill_def.attribute == '불':
                    impact_symbol = '🔥'
                    impact_color = ANSI.YELLOW

            animation_data['impact_effect'] = {
                'x': impact_pos[0], 'y': impact_pos[1],
                'symbol': impact_symbol, 'color': impact_color
            }
            animation_data['current_pos'] = []

        # 화면 다시 그리기
        ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'],
                                     projectile_path=animation_data.get('current_pos', []),
                                     impact_effect=animation_data.get('impact_effect'))
        time.sleep(0.05)

        # 충돌 효과 후 정리
        if 'impact_effect' in animation_data:
            target_monster = animation_data.get('target')
            if target_monster and skill_def: # skill_def가 있는지 확인
                # 데미지 계산 및 적용 (스킬 데미지 사용)
                # 기본 데미지에 스킬 레벨에 따른 보너스를 추가할 수 있음 (예시)
                skill_level = player.skills.get(skill_def.id, {}).get('level', 1)
                base_damage = skill_def.damage
                final_damage = base_damage + (skill_level - 1) * int(base_damage * 0.1) # 레벨당 10% 추가 데미지

                # combat 모듈을 사용하되, 플레이어의 공격력이 아닌 스킬 데미지를 기반으로 계산
                damage, is_critical = combat.calculate_damage(player, target_monster, base_damage=final_damage)

                ui_instance.add_message(f"'{skill_def.name}'(이)가 {target_monster.name}에게 적중!" + (" 💥치명타!💥" if is_critical else ""))
                target_monster.take_damage(damage)
                ui_instance.add_message(f"{target_monster.name}에게 {damage}의 데미지를 입혔습니다.")
                if target_monster.dead:
                    ui_instance.add_message(f"{target_monster.name}을(를) 물리쳤습니다!")
                    if data_manager._item_definitions and random.random() < 0.5:
                        dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                        target_monster.loot = dropped_item_id
                        item_def = data_manager.get_item_definition(dropped_item_id)
                        if item_def:
                            ui_instance.add_message(f"{target_monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")
                    exp_gained = target_monster.exp_given + (target_monster.level * 2)
                    ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                    leveled_up, level_up_message = player.gain_exp(exp_gained)
                    if leveled_up: ui_instance.add_message(level_up_message)

            animation_data = None
            game_state = 'NORMAL'
            player_action_taken = True # 애니메이션 종료 후 턴이 진행되도록 설정

    def use_projectile_skill(player_char, dungeon, skill):
        nonlocal game_state, animation_data
        visible_monsters = [m for m in dungeon.monsters if not m.dead and (m.x, m.y) in dungeon.visited]
        if not visible_monsters:
            ui_instance.add_message("주변에 보이는 몬스터가 없습니다.")
            return False

        closest_monster = min(visible_monsters, key=lambda m: math.sqrt((player_char.x - m.x)**2 + (player_char.y - m.y)**2))
        
        # 스킬 사거리 체크
        distance = math.sqrt((player_char.x - closest_monster.x)**2 + (player_char.y - closest_monster.y)**2)
        if distance > skill.range_str:
            ui_instance.add_message(f"'{skill.name}' 스킬의 사거리가 닿지 않습니다. (사거리: {skill.range_str})")
            return False

        path = calculate_line_path(player_char.x, player_char.y, closest_monster.x, closest_monster.y)
        
        if path:
            game_state = 'ANIMATING'
            animation_data = {
                'path': path,
                'impact_pos': (closest_monster.x, closest_monster.y),
                'target': closest_monster,
                'skill_def': skill,  # 사용된 스킬 정보 전달
                'current_pos': []
            }
            return True
        else:
            ui_instance.add_message("몬스터에게 가는 경로가 없습니다.")
            return False

    running = True
    while running:
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        camera['x'] = max(0, min(player.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))
        
        if game_state != 'ANIMATING':
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'],
                                         inventory_open, inventory_cursor_pos, 
                                         inventory_active_tab, inventory_scroll_offset,
                                         log_viewer_open, log_viewer_scroll_offset)

        if not player.is_alive():
            readchar.readkey()
            running = False
            continue

        player_action_taken = False
        
        if game_state == 'ANIMATING':
            handle_animation()
        else:
            key = readchar.readkey()
            current_floor, current_room_index = current_dungeon_level
            is_in_menu = inventory_open or log_viewer_open

            if game_state == 'AIMING_SKILL':
                pass 

            elif log_viewer_open:
                if key == readchar.key.UP: log_viewer_scroll_offset += 1
                elif key == readchar.key.DOWN: log_viewer_scroll_offset = max(0, log_viewer_scroll_offset - 1)
                elif key == 'm': log_viewer_open = False

            elif inventory_open:
                if key == 'i' or key == 'I': # 'i' 또는 'I' 키로 인벤토리 닫기
                    inventory_open = False
                elif key == readchar.key.UP:
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab:
                        inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                        if inventory_cursor_pos < inventory_scroll_offset:
                            inventory_scroll_offset = inventory_cursor_pos
                elif key == readchar.key.DOWN:
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab:
                        inventory_cursor_pos = min(len(items_in_tab) - 1, inventory_cursor_pos + 1)
                        if inventory_cursor_pos >= inventory_scroll_offset + ui_instance.MAP_VIEWPORT_HEIGHT - 6: # list_height
                            inventory_scroll_offset += 1
                elif key == 'a': inventory_active_tab = 'item'
                elif key == 'b': inventory_active_tab = 'equipment'
                elif key == 'c': inventory_active_tab = 'scroll'
                elif key == 'd': inventory_active_tab = 'skill_book'
                elif key == 'z': inventory_active_tab = 'all'
                elif key == 'e': # 장착/해제 또는 사용
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                        selected_item_data = items_in_tab[inventory_cursor_pos]
                        selected_item = selected_item_data['item']

                        if isinstance(selected_item, Item):
                            if selected_item.item_type == 'EQUIP':
                                # 이미 장착된 아이템이면 해제, 아니면 장착
                                is_equipped = False
                                for slot, equipped_item in player.equipment.items():
                                    if equipped_item and equipped_item.id == selected_item.id:
                                        is_equipped = True
                                        break
                                
                                if is_equipped:
                                    # 장착 해제 (어떤 슬롯에 장착되어 있는지 찾아야 함)
                                    unequipped_slot = None
                                    for slot_name, eq_item in player.equipment.items():
                                        if eq_item and eq_item.id == selected_item.id:
                                            unequipped_slot = slot_name
                                            break
                                    if unequipped_slot:
                                        message = player.unequip(unequipped_slot)
                                        ui_instance.add_message(message)
                                        player_action_taken = True
                                else:
                                    message = player.equip(selected_item)
                                    ui_instance.add_message(message)
                                    player_action_taken = True
                            elif selected_item.item_type == 'CONSUMABLE':
                                used, message = player.use_item(selected_item)
                                ui_instance.add_message(message)
                                if used:
                                    player_action_taken = True
                                    if player.inventory.get_item_quantity(selected_item.id) <= 0:
                                        inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                            elif selected_item.item_type == 'SKILLBOOK':
                                message = player.acquire_skill_from_book(selected_item)
                                ui_instance.add_message(message)
                                player_action_taken = True
                                player.remove_item(selected_item, 1)
                                if player.inventory.get_item_quantity(selected_item.id) <= 0:
                                    inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                            else:
                                ui_instance.add_message("이 아이템은 장착하거나 사용할 수 없습니다.")
                        else:
                            ui_instance.add_message("선택된 항목이 아이템이 아닙니다.")
                elif key == 'R': # 버리기
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                        selected_item_data = items_in_tab[inventory_cursor_pos]
                        selected_item = selected_item_data['item']
                        if player.drop_item(selected_item):
                            ui_instance.add_message(f"{selected_item.name}을(를) 버렸습니다.")
                            player_action_taken = True
                            inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                        else:
                            ui_instance.add_message("아이템을 버리는 데 실패했습니다.")
                elif key in "1234567890": # 퀵슬롯 등록
                    slot_num = 10 if key == '0' else int(key)
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                        selected_item_data = items_in_tab[inventory_cursor_pos]
                        selected_item = selected_item_data['item']

                        if 1 <= slot_num <= 5: # 아이템 퀵슬롯
                            if selected_item.item_type == 'CONSUMABLE' or selected_item.item_type == 'SCROLL': # SCROLL 타입은 아직 없지만 미리 추가
                                message = player.assign_item_to_quickslot(selected_item, slot_num)
                                ui_instance.add_message(message)
                            else:
                                ui_instance.add_message("소모품 또는 스크롤만 아이템 퀵슬롯에 등록할 수 있습니다.")
                        elif 6 <= slot_num <= 10: # 스킬 퀵슬롯
                            if selected_item.item_type == 'SKILLBOOK':
                                # 스킬북 자체를 등록하는 것이 아니라, 배운 스킬을 등록해야 함
                                # 여기서는 스킬북 ID를 사용하여 스킬 ID를 찾고 등록
                                if selected_item.id in player.skills:
                                    message = player.assign_skill_to_quickslot(selected_item, slot_num)
                                    ui_instance.add_message(message)
                                else:
                                    ui_instance.add_message("먼저 스킬북을 사용하여 스킬을 배워야 합니다.")
                            else:
                                ui_instance.add_message("스킬북만 스킬 퀵슬롯에 등록할 수 있습니다.")
                    else:
                        ui_instance.add_message("선택된 아이템이 없습니다.")

            elif game_state == 'NORMAL':
                if key == 'i':
                    inventory_open = True
                elif key == 'm':
                    log_viewer_open = True
                else:
                    dx, dy = 0, 0
                    move_keys = {
                        readchar.key.UP: (0, -1), readchar.key.DOWN: (0, 1),
                        readchar.key.LEFT: (-1, 0), readchar.key.RIGHT: (1, 0),
                        'k': (0, -1), 'j': (0, 1), 'h': (-1, 0), 'l': (1, 0),
                        'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1)
                    }
                    if key in move_keys:
                        dx, dy = move_keys[key]

                    if dx != 0 or dy != 0:
                        moved, result = dungeon_map.move_player(dx, dy)
                        
                        if isinstance(result, Monster):
                            monster = result
                            player_action_taken = True
                            ui_instance.add_message(f"{monster.name}과(와) 전투 시작!")
                            damage, is_critical = combat.calculate_damage(player, monster)
                            ui_instance.add_message(f"{player.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                            monster.take_damage(damage)
                            ui_instance.add_message(f"{monster.name}에게 {damage}의 데미지를 입혔습니다.")
                            if monster.dead:
                                ui_instance.add_message(f"{monster.name}을(를) 물리쳤습니다!")
                                if data_manager._item_definitions and random.random() < 0.5:
                                    dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                                    monster.loot = dropped_item_id
                                    item_def = data_manager.get_item_definition(dropped_item_id)
                                    if item_def:
                                        ui_instance.add_message(f"{monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")
                                exp_gained = monster.exp_given + (monster.level * 2)
                                ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                                leveled_up, level_up_message = player.gain_exp(exp_gained)
                                if leveled_up: ui_instance.add_message(level_up_message)

                        elif result == ITEM_TILE:
                            player_action_taken = True
                            player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                            # 아이템 루팅 로직 (r 키 로직 재사용)
                            looted_something = False
                            if (player.x, player.y) in dungeon_map.items_on_map:
                                item_data_on_map = dungeon_map.items_on_map[(player.x, player.y)]
                                item_id_on_map = item_data_on_map['id']
                                item_qty_on_map = item_data_on_map['qty']
                                item_def_on_map = data_manager.get_item_definition(item_id_on_map)

                                if item_def_on_map:
                                    looted_item_on_map = Item.from_definition(item_def_on_map)
                                    
                                    if player.add_item(looted_item_on_map, item_qty_on_map):
                                        ui_instance.add_message(f"{looted_item_on_map.name} {item_qty_on_map}개를 획득했습니다.")
                                        del dungeon_map.items_on_map[(player.x, player.y)] # 맵에서 아이템 제거
                                        looted_something = True
                                    else:
                                        ui_instance.add_message(f"{looted_item_on_map.name}을(를) 획득할 수 없습니다.")
                                else:
                                    ui_instance.add_message("맵에 있는 알 수 없는 아이템입니다.")
                            if not looted_something:
                                ui_instance.add_message("이동한 타일에 루팅할 아이템이 없습니다.")

                        elif result == ROOM_ENTRANCE:
                            player_action_taken = True
                            player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                            # 방 이동 로직
                            current_floor, current_room_index = current_dungeon_level
                            room_info = dungeon_map.room_entrances.get((player.x, player.y))
                            if room_info:
                                next_room_index = room_info['id']
                                is_boss_room = room_info['is_boss']
                                last_entrance_position[current_dungeon_level] = (player.x, player.y) # 현재 맵의 입구 위치 저장
                                current_dungeon_level = (current_floor, next_room_index)
                                dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions, is_boss_room=is_boss_room)
                                player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                                ui_instance.add_message(f"{current_floor}층 {next_room_index}번 방으로 이동했습니다.")
                            else:
                                ui_instance.add_message("알 수 없는 방 입구입니다.")

                        elif moved:
                            player_action_taken = True
                            player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                            
                        elif isinstance(result, str):
                             ui_instance.add_message(result)
                    
                    elif key in "1234567890":
                        slot_num = 10 if key == '0' else int(key)
                        
                        # 아이템 퀵슬롯 처리 (1-5)
                        if 1 <= slot_num <= 5:
                            item_id = player.item_quick_slots.get(slot_num)
                            if not item_id:
                                ui_instance.add_message(f"퀵슬롯 {slot_num}번이 비어있습니다.")
                            else:
                                item_in_inventory = player.inventory.find_item(item_id)
                                if not item_in_inventory:
                                    ui_instance.add_message(f"'{item_id}' 아이템이 인벤토리에 없습니다.")
                                    player.item_quick_slots[slot_num] = None # 퀵슬롯 정리
                                else:
                                    used, message = player.use_item(item_in_inventory)
                                    ui_instance.add_message(message)
                                    if used:
                                        player_action_taken = True
                        
                        # 스킬 퀵슬롯 처리 (6-0)
                        elif 6 <= slot_num <= 10:
                            skill_id = player.skill_quick_slots.get(slot_num)
                            if not skill_id:
                                ui_instance.add_message(f"퀵슬롯 {0 if slot_num == 10 else slot_num}번이 비어있습니다.")
                            else:
                                skill_def = data_manager.get_skill_definition(skill_id)
                                if not skill_def:
                                    ui_instance.add_message("알 수 없는 스킬입니다.")
                                elif player.mp < skill_def.cost_value:
                                    ui_instance.add_message(f"MP가 부족하여 '{skill_def.name}'을(를) 사용할 수 없습니다.")
                                else:
                                    # 스킬 사용
                                    player.mp -= skill_def.cost_value
                                    ui_instance.add_message(f"'{skill_def.name}'을(를) 시전합니다!")
                                    
                                    if skill_def.skill_subtype == 'PROJECTILE':
                                        if use_projectile_skill(player, dungeon_map, skill_def):
                                            # 성공적으로 시전하면 애니메이션이 시작되므로,
                                            # 여기서는 player_action_taken을 True로 설정하지 않음.
                                            # 애니메이션이 끝난 후 handle_animation에서 설정됨.
                                            pass
                                        else:
                                            # 몬스터가 없거나 경로가 없는 등 시전 실패 시 MP를 돌려주고 턴을 소모하지 않음
                                            player.mp += skill_def.cost_value
                                    else:
                                        # 다른 타입 스킬 (즉시 발동)
                                        ui_instance.add_message(f"'{skill_def.name}'은(는) 아직 구현되지 않았습니다.")
                                        player_action_taken = True

                    elif key in ['v', 't']:
                        status_text = "ON" if dungeon_map.toggle_fog() else "OFF"
                        ui_instance.add_message(f"전장의 안개(Fog of War) 토글: {status_text}")
                    
                    elif key == 'r':
                        player_action_taken = False
                        looted_something = False

                        # 1. 몬스터 시체에서 아이템 루팅 시도
                        monster_at_player_pos = None
                        for m in dungeon_map.monsters:
                            if m.dead and m.x == player.x and m.y == player.y:
                                monster_at_player_pos = m
                                break

                        if monster_at_player_pos and monster_at_player_pos.loot:
                            item_id_to_loot = monster_at_player_pos.loot
                            item_def = data_manager.get_item_definition(item_id_to_loot)
                            if item_def:
                                looted_item = Item.from_definition(item_def)
                                
                                if player.add_item(looted_item):
                                    ui_instance.add_message(f"{looted_item.name}을(를) 획득했습니다.")
                                    monster_at_player_pos.loot = None # 루팅 후 아이템 제거
                                    looted_something = True
                                    player_action_taken = True
                                else:
                                    ui_instance.add_message(f"{looted_item.name}을(를) 획득할 수 없습니다.")
                            else:
                                ui_instance.add_message("알 수 없는 아이템입니다.")
                        
                        # 2. 맵에 직접 떨어진 아이템 루팅 시도 (몬스터 루팅 후 또는 몬스터 루팅할 것이 없을 때)
                        if (player.x, player.y) in dungeon_map.items_on_map and not looted_something:
                            item_data_on_map = dungeon_map.items_on_map[(player.x, player.y)]
                            item_id_on_map = item_data_on_map['id']
                            item_qty_on_map = item_data_on_map['qty']
                            item_def_on_map = data_manager.get_item_definition(item_id_on_map)

                            if item_def_on_map:
                                looted_item_on_map = Item(item_def_on_map.id, item_def_on_map.name, item_def_on_map.item_type, 
                                                          item_def_on_map.equip_slot, item_def_on_map.effect_type, 
                                                          item_def_on_map.value, item_def_on_map.description, item_def_on_map.req_level)
                                
                                if player.add_item(looted_item_on_map, item_qty_on_map):
                                    ui_instance.add_message(f"{looted_item_on_map.name} {item_qty_on_map}개를 획득했습니다.")
                                    del dungeon_map.items_on_map[(player.x, player.y)] # 맵에서 아이템 제거
                                    looted_something = True
                                    player_action_taken = True
                                else:
                                    ui_instance.add_message(f"{looted_item_on_map.name}을(를) 획득할 수 없습니다.")
                            else:
                                ui_instance.add_message("맵에 있는 알 수 없는 아이템입니다.")

                        if not looted_something:
                            ui_instance.add_message("주변에 루팅할 아이템이 없습니다.")

                    elif key == 'q':
                        running = False
                        ui_instance.add_message("게임을 저장하고 메인 메뉴로 돌아갑니다.")

        if player_action_taken:
            turn_count += 1
            # (기존 턴 종료 처리 로직)
            for monster in dungeon_map.monsters:
                if monster.dead: continue
                if abs(player.x - monster.x) <= 1 and abs(player.y - monster.y) <= 1:
                    damage, is_critical = combat.calculate_damage(monster, player)
                    ui_instance.add_message(f"{monster.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                    player.take_damage(damage)
                    ui_instance.add_message(f"{player.name}에게 {damage}의 데미지를 입혔습니다.")
                else:
                    # 몬스터 이동 AI
                    # 플레이어와 몬스터 사이의 최단 경로를 찾기 위한 간단한 BFS (너비 우선 탐색)
                    # 여기서는 간단하게 플레이어 방향으로 한 칸 이동하는 로직을 구현합니다.
                    
                    # 몬스터가 도발 상태가 아니면 원래 move_type을 따르고, 도발 상태면 AGGRESSIVE로 변경
                    current_move_type = monster.move_type
                    if monster.is_provoked:
                        current_move_type = 'AGGRESSIVE'

                    if current_move_type == 'STATIONARY':
                        continue # 움직이지 않는 몬스터
                    
                    target_dx, target_dy = 0, 0
                    
                    # 플레이어와의 상대적인 위치 계산
                    rel_x = player.x - monster.x
                    rel_y = player.y - monster.y

                    # AGGRESSIVE: 플레이어에게 가까워지는 방향
                    if current_move_type == 'AGGRESSIVE':
                        if rel_x > 0: target_dx = 1
                        elif rel_x < 0: target_dx = -1
                        if rel_y > 0: target_dy = 1
                        elif rel_y < 0: target_dy = -1
                    # COWARDLY: 플레이어로부터 멀어지는 방향
                    elif current_move_type == 'COWARDLY':
                        if rel_x > 0: target_dx = -1
                        elif rel_x < 0: target_dx = 1
                        if rel_y > 0: target_dy = -1
                        elif rel_y < 0: target_dy = 1

                    # 이동 시도 (대각선, 수평/수직 순서로)
                    possible_moves = []
                    if target_dx != 0 and target_dy != 0: # 대각선 이동
                        possible_moves.append((target_dx, target_dy))
                    if target_dx != 0: # 수평 이동
                        possible_moves.append((target_dx, 0))
                    if target_dy != 0: # 수직 이동
                        possible_moves.append((0, target_dy))
                    
                    # 이동할 수 있는 모든 8방향 (STATIONARY 제외)
                    all_directions = [
                        (0, -1), (0, 1), (-1, 0), (1, 0), # 상하좌우
                        (-1, -1), (1, -1), (-1, 1), (1, 1) # 대각선
                    ]
                    random.shuffle(all_directions) # 무작위성 추가

                    # AGGRESSIVE/COWARDLY에 따라 우선순위가 높은 방향부터 시도
                    if current_move_type == 'AGGRESSIVE':
                        # 플레이어에게 가까워지는 방향을 우선
                        # (dx, dy)가 플레이어 방향과 일치하는지 확인
                        preferred_directions = []
                        for adx, ady in all_directions:
                            if (adx == 0 or (adx > 0 and rel_x > 0) or (adx < 0 and rel_x < 0)) and \
                               (ady == 0 or (ady > 0 and rel_y > 0) or (ady < 0 and rel_y < 0)):
                                preferred_directions.append((adx, ady))
                        # 선호 방향이 없으면 모든 방향 시도
                        if not preferred_directions:
                            preferred_directions = all_directions
                        
                        for dx, dy in preferred_directions:
                            moved, trap_triggered = dungeon_map.move_monster(monster, dx, dy)
                            if moved:
                                if trap_triggered:
                                    ui_instance.add_message(f"{monster.name}이(가) {trap_triggered.name} 함정을 밟았습니다! {trap_triggered.damage} 데미지!")
                                    monster.take_damage(trap_triggered.damage)
                                    if monster.dead:
                                        ui_instance.add_message(f"{monster.name}이(가) 함정에 의해 죽었습니다!")
                                        # 몬스터 사망 시 아이템 드랍 로직은 플레이어 전투 시와 동일하게 처리
                                        if data_manager._item_definitions and random.random() < 0.5:
                                            dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                                            monster.loot = dropped_item_id
                                            item_def = data_manager.get_item_definition(dropped_item_id)
                                            if item_def:
                                                ui_instance.add_message(f"{monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")
                                        exp_gained = monster.exp_given + (monster.level * 2)
                                        ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                                        leveled_up, level_up_message = player.gain_exp(exp_gained)
                                        if leveled_up: ui_instance.add_message(level_up_message)
                                break # 이동 성공 시 다음 몬스터로
                    
                    elif current_move_type == 'COWARDLY':
                        # 플레이어로부터 멀어지는 방향을 우선
                        # (dx, dy)가 플레이어 반대 방향과 일치하는지 확인
                        preferred_directions = []
                        for adx, ady in all_directions:
                            if (adx == 0 or (adx > 0 and rel_x < 0) or (adx < 0 and rel_x > 0)) and \
                               (ady == 0 or (ady > 0 and rel_y < 0) or (ady < 0 and rel_y > 0)):
                                preferred_directions.append((adx, ady))
                        # 선호 방향이 없으면 모든 방향 시도
                        if not preferred_directions:
                            preferred_directions = all_directions

                        for dx, dy in preferred_directions:
                            moved, trap_triggered = dungeon_map.move_monster(monster, dx, dy)
                            if moved:
                                if trap_triggered:
                                    ui_instance.add_message(f"{monster.name}이(가) {trap_triggered.name} 함정을 밟았습니다! {trap_triggered.damage} 데미지!")
                                    monster.take_damage(trap_triggered.damage)
                                    if monster.dead:
                                        ui_instance.add_message(f"{monster.name}이(가) 함정에 의해 죽었습니다!")
                                        # 몬스터 사망 시 아이템 드랍 로직은 플레이어 전투 시와 동일하게 처리
                                        if data_manager._item_definitions and random.random() < 0.5:
                                            dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                                            monster.loot = dropped_item_id
                                            item_def = data_manager.get_item_definition(dropped_item_id)
                                            if item_def:
                                                ui_instance.add_message(f"{monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")
                                        exp_gained = monster.exp_given + (monster.level * 2)
                                        ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                                        leveled_up, level_up_message = player.gain_exp(exp_gained)
                                        if leveled_up: ui_instance.add_message(level_up_message)
                                break # 이동 성공 시 다음 몬스터로
        
        if not player.is_alive():
            game_over_flag = True
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'])
            readchar.readkey()
            running = False

        
        if not player.is_alive():
            game_over_flag = True
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'])
            readchar.readkey()
            running = False

    sys.stdout.write(ANSI.SHOW_CURSOR)
    player.dungeon_level = current_dungeon_level
    data_manager.save_game_data(player, all_dungeon_maps, ui_instance)
    
    return "DEATH" if not player.is_alive() else "QUIT"
