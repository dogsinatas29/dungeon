# game.py

import sys
from player import Player
from dungeon_map import DungeonMap, EXIT_NORMAL, EXIT_LOCKED, ITEM_TILE, ROOM_ENTRANCE
from ui import UI, ANSI
import readchar
import Start
import data_manager
import combat
import random
from items import Item
from monster import Monster

def run_game(player_data_from_save, all_dungeon_maps_data_from_save_raw, item_definitions, ui_instance):
    
    monster_definitions = data_manager.load_monster_definitions(ui_instance)

    def get_or_create_map(level, all_maps, ui, items_def, monster_defs):
        if level in all_maps:
            d_map = all_maps[level]
            d_map.ui_instance = ui
            return d_map
        else:
            d_map = DungeonMap(level, ui)
            if level[1] > 0:
                d_map.place_monsters(monster_defs, num_monsters=random.randint(1, 3))
                d_map.place_random_items(items_def, num_items=random.randint(0, 2))
            else:
                d_map.place_monsters(monster_defs)
                d_map.place_random_items(items_def)
            all_maps[level] = d_map
            return d_map

    player = Player.from_dict(player_data_from_save)
    camera = {'x': 0, 'y': 0}
    last_entrance_position = {}
    
    # 인벤토리 상태 변수
    inventory_open = False
    inventory_cursor_pos = 0
    inventory_active_tab = 'item'
    inventory_scroll_offset = 0

    # 전체 로그 뷰어 상태 변수
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

    # 게임 루프
    running = True
    while running:
        # 화면 그리기
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        camera['x'] = max(0, min(player.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))
        
        ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'],
                                     inventory_open, inventory_cursor_pos, 
                                     inventory_active_tab, inventory_scroll_offset,
                                     log_viewer_open, log_viewer_scroll_offset)

        # 사용자 입력 처리
        if not player.is_alive():
            key = readchar.readkey() # 아무 키나 입력받아 루프 종료
            running = False
            continue

        key = readchar.readkey()
        player_action_taken = False
        current_floor, current_room_index = current_dungeon_level
        is_in_menu = inventory_open or log_viewer_open

        # --- 전체 로그 뷰어 활성화 시 입력 처리 ---
        if log_viewer_open:
            if key == readchar.key.UP:
                log_viewer_scroll_offset += 1
            elif key == readchar.key.DOWN:
                log_viewer_scroll_offset = max(0, log_viewer_scroll_offset - 1)
            elif key == 'm':
                log_viewer_open = False
            # 메뉴 조작 시에는 턴이 진행되도록 continue를 사용하지 않음

        # --- 인벤토리 창 활성화 시 입력 처리 ---
        elif inventory_open:
            current_item_list = player.inventory.get_items_by_tab(inventory_active_tab)
            list_height = 14 # ui._draw_inventory의 list_height와 맞춤

            if key == readchar.key.UP:
                inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                if inventory_cursor_pos < inventory_scroll_offset:
                    inventory_scroll_offset = inventory_cursor_pos
            elif key == readchar.key.DOWN:
                if current_item_list:
                    inventory_cursor_pos = min(len(current_item_list) - 1, inventory_cursor_pos + 1)
                    if inventory_cursor_pos >= inventory_scroll_offset + list_height:
                        inventory_scroll_offset = max(0, inventory_cursor_pos - list_height + 1)
            
            # 탭 전환
            elif key == 'a': inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset = 'item', 0, 0
            elif key == 'b': inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset = 'equipment', 0, 0
            elif key == 'c': inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset = 'scroll', 0, 0
            elif key == 'd': inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset = 'skill_book', 0, 0
            elif key == 'z': inventory_active_tab, inventory_cursor_pos, inventory_scroll_offset = 'all', 0, 0

            # 선택된 아이템 관련 로직
            selected_item_obj = None
            if current_item_list and 0 <= inventory_cursor_pos < len(current_item_list):
                selected_item_obj = current_item_list[inventory_cursor_pos]['item']

            if selected_item_obj:
                if key in ('e', 'E'):
                    message = player.equip(selected_item_obj)
                    ui_instance.add_message(message)
                elif key in ('r', 'R'):
                    if player.drop_item(selected_item_obj, 1):
                         ui_instance.add_message(f"{selected_item_obj.name}을(를) 버렸습니다.")
                         inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                    else:
                         ui_instance.add_message("아이템을 버릴 수 없습니다.")
                # 퀵슬롯 로직 (생략)

            if key == 'i':
                inventory_open = False
            # 메뉴 조작 시에는 턴이 진행되도록 continue를 사용하지 않음

        # --- 일반 게임 플레이 입력 처리 ---
        elif key == 'i':
            inventory_open = True
            inventory_cursor_pos = 0
            inventory_active_tab = 'item'
            inventory_scroll_offset = 0
        
        elif key == 'm':
            log_viewer_open = True
            log_viewer_scroll_offset = 0

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
                    
                    # --- 전투 로직 시작 ---
                    ui_instance.add_message(f"{monster.name}과(와) 전투 시작!")
                    damage, is_critical = combat.calculate_damage(player, monster)
                    ui_instance.add_message(f"{player.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                    monster.take_damage(damage)
                    ui_instance.add_message(f"{monster.name}에게 {damage}의 데미지를 입혔습니다.")

                    if monster.dead:
                        ui_instance.add_message(f"{monster.name}을(를) 물리쳤습니다!")
                        # 아이템 드랍 로직
                        if data_manager._item_definitions and random.random() < 0.5:
                            dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                            monster.loot = dropped_item_id
                            item_def = data_manager.get_item_definition(dropped_item_id)
                            if item_def:
                                ui_instance.add_message(f"{monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")
                        # 경험치 획득 로직
                        exp_gained = monster.exp_given + (monster.level * 2)
                        ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                        leveled_up, level_up_message = player.gain_exp(exp_gained)
                        if leveled_up: ui_instance.add_message(level_up_message)
                elif moved:
                    player.stamina -= 1
                    player_action_taken = True
                    player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                    
                    # 몬스터 발견 메시지
                    for m in dungeon_map.monsters:
                        if not m.dead and abs(player.x - m.x) + abs(player.y - m.y) <= 3:
                            ui_instance.add_message(f"{m.name}(LV:{m.level})을(를) 만났습니다.")
                    
                    # 아이템 줍기 로직
                    item_data_on_map = dungeon_map.items_on_map.pop((player.x, player.y), None)
                    if item_data_on_map:
                        item_def = data_manager.get_item_definition(item_data_on_map['id'])
                        if item_def:
                            item_obj = Item.from_definition(item_def)
                            player.add_item(item_obj, item_data_on_map['qty'])
                            ui_instance.add_message(f"{item_def.name}을(를) 획득했습니다!")
                elif isinstance(result, str):
                     ui_instance.add_message(result)
            
            elif key in ['v', 't']:
                status_text = "ON" if dungeon_map.toggle_fog() else "OFF"
                ui_instance.add_message(f"전장의 안개(Fog of War) 토글: {status_text}")
            
            elif key == 'r':
                # 루팅 로직 (생략)
                pass

            elif key == 'q':
                running = False
                ui_instance.add_message("게임을 저장하고 메인 메뉴로 돌아갑니다.")

        # --- 턴 종료 후 처리 (몬스터 AI, 플레이어 상태 등) ---
        # 플레이어가 행동했거나, 메뉴를 조작했다면 몬스터 턴 진행
        if (player_action_taken or is_in_menu) and player.is_alive():
            for monster in dungeon_map.monsters:
                if monster.dead: continue
                
                # 플레이어가 메뉴 안에 있을 때도 몬스터는 공격할 수 있음
                if abs(player.x - monster.x) <= 1 and abs(player.y - monster.y) <= 1:
                    damage, is_critical = combat.calculate_damage(monster, player)
                    ui_instance.add_message(f"{monster.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                    player.take_damage(damage)
                    ui_instance.add_message(f"{player.name}에게 {damage}의 데미지를 입혔습니다.")
                else: # 플레이어가 멀리 있으면 이동
                    if monster.move_type == 'STATIONARY':
                        continue # 이동하지 않음

                    dx, dy = 0, 0
                    # AGGRESSIVE: 플레이어 추격
                    if monster.move_type == 'AGGRESSIVE':
                        if player.x > monster.x: dx = 1
                        elif player.x < monster.x: dx = -1
                        if player.y > monster.y: dy = 1
                        elif player.y < monster.y: dy = -1
                    
                    # COWARD: 플레이어로부터 도망
                    elif monster.move_type == 'COWARD':
                        if player.x > monster.x: dx = -1
                        elif player.x < monster.x: dx = 1
                        if player.y > monster.y: dy = -1
                        elif player.y < monster.y: dy = 1

                    # 이동 시도
                    if dx != 0 or dy != 0:
                        # 대각선 이동 먼저 시도
                        if not dungeon_map.move_monster(monster, dx, dy):
                            # 대각선이 막혔으면 직선 이동 시도
                            if dx != 0 and dungeon_map.move_monster(monster, dx, 0):
                                pass # x축으로 이동 성공
                            elif dy != 0 and dungeon_map.move_monster(monster, 0, dy):
                                pass # y축으로 이동 성공

        # 플레이어가 아무 행동도 안 하고 메뉴도 닫혀있을 때만 스태미너 회복
        elif not player_action_taken and not is_in_menu:
            if player.stamina < player.max_stamina:
                player.stamina += 1
        
        if not player.is_alive():
            game_over_flag = True
            # 게임 오버 로직 (생략)
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'],
                                         False, 0, 'item', 0, False, 0)
            key = readchar.readkey()
            running = False

        # 레벨 전환 등 (생략)
        # ...

    sys.stdout.write(ANSI.SHOW_CURSOR)
    player.dungeon_level = current_dungeon_level
    Start.save_game_data(player, all_dungeon_maps, ui_instance)
    
    return "DEATH" if not player.is_alive() else "QUIT"
