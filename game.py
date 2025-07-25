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

def run_game(player_data_from_save, all_dungeon_maps_data_from_save_raw, item_definitions, ui_instance):
    
    # 몬스터 정의 로드
    monster_definitions = data_manager.load_monster_definitions(ui_instance)

    # --- Helper function for map management ---
    def get_or_create_map(level, all_maps, ui, items_def, monster_defs): # monster_defs 인자 추가
        if level in all_maps:
            d_map = all_maps[level]
            d_map.ui_instance = ui
            ui.add_message(f"DEBUG: 레벨 {level[0]}층 - {level[1]}번 맵 로드됨.")
            return d_map
        else:
            d_map = DungeonMap(level, ui)
            # 메인 맵이 아니면 몬스터/아이템을 더 적게 스폰하거나 다른 규칙 적용 가능
            if level[1] > 0: # 서브 룸일 경우
                d_map.place_monsters(monster_defs, num_monsters=random.randint(1, 3)) # monster_defs 전달
                d_map.place_random_items(items_def, num_items=random.randint(0, 2))
            else: # 메인 맵일 경우
                d_map.place_monsters(monster_defs) # monster_defs 전달
                d_map.place_random_items(items_def)
            
            all_maps[level] = d_map
            ui.add_message(f"DEBUG: 레벨 {level[0]}층 - {level[1]}번 맵 새로 생성됨.")
            return d_map

    # --- Initialization ---
    player = Player.from_dict(player_data_from_save)
    camera = {'x': 0, 'y': 0}
    last_entrance_position = {} # {floor: (x, y)}

    all_dungeon_maps = {}
    if all_dungeon_maps_data_from_save_raw:
        for level_str, map_dict in all_dungeon_maps_data_from_save_raw.items():
            floor, room_index = map(int, level_str.split(','))
            all_dungeon_maps[(floor, room_index)] = DungeonMap.from_dict(map_dict)

    current_dungeon_level = player.dungeon_level
    dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions) # monster_definitions 전달

    player.x, player.y = dungeon_map.player_x, dungeon_map.player_y

    game_over_flag = False
    ui_instance.clear_screen()
    # (Initial UI setup)
    readchar.readkey()
    ui_instance.clear_screen() 

    # --- Main Game Loop ---
    while player.is_alive() and not game_over_flag:
        # --- Update & Draw ---
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        camera['x'] = max(0, min(player.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))

        ui_instance.draw_game_screen(player, dungeon_map, camera['x'], camera['y'])

        # --- Input & Action ---
        action = readchar.readkey()
        player_action_taken = False

        # Unpack current level for use in this loop iteration
        current_floor, current_room_index = current_dungeon_level

        dx, dy = 0, 0
        if action == readchar.key.UP: dx, dy = 0, -1
        elif action == readchar.key.DOWN: dx, dy = 0, 1
        elif action == readchar.key.LEFT: dx, dy = -1, 0
        elif action == readchar.key.RIGHT: dx, dy = 1, 0

        if dx != 0 or dy != 0:
            moved, message = dungeon_map.move_player(dx, dy)
            if moved:
                player_action_taken = True
                # 이동에 성공했을 때만 player 객체의 좌표를 동기화합니다.
                player.x = dungeon_map.player_x
                player.y = dungeon_map.player_y

                # 몬스터 접근 메시지 확인
                for monster in dungeon_map.monsters:
                    if not monster.dead:
                        distance = abs(player.x - monster.x) + abs(player.y - monster.y)
                        if distance <= 3:
                            ui_instance.add_message(f"{monster.name}(LV:{monster.level})을(를) 만났습니다.")

            ui_instance.add_message(message)
        
        elif action == 'f':
            # 디버그용 안개 토글 키
            fog_status = dungeon_map.toggle_fog()
            status_text = "ON" if fog_status else "OFF"
            ui_instance.add_message(f"전장의 안개(Fog of War) 토글: {status_text}")
            # 턴을 소모하지 않는 행동이므로 player_action_taken을 True로 설정하지 않음
        
        elif action == 'q':
            game_over_flag = True
            ui_instance.add_message("게임을 종료합니다.")
        # (Other actions like skills, inventory...)

        # --- Monster Turn ---
        if player_action_taken and player.is_alive():
            # (Monster AI logic)
            pass

        if not player.is_alive():
            game_over_flag = True
            ui_instance.add_message("당신은 패배했습니다...")
            continue

        # --- Tile Interaction ---
        # player.x, player.y = dungeon_map.player_x, dungeon_map.player_y # 이 라인을 이동 로직 안으로 옮겼습니다.
        
        # Item pickup
        item_data = dungeon_map.items_on_map.pop((player.x, player.y), None)
        if item_data:
            item_id = item_data['id']
            item_def = item_definitions.get(item_id)
            if item_def:
                player.add_item(item_id, item_def.name, item_data['qty'])
                ui_instance.add_message(f"{item_def.name}을(를) 획득했습니다!")
            else:
                # 아이템 정의가 없는 경우, ID를 이름으로 사용
                player.add_item(item_id, item_id, item_data['qty'])
                ui_instance.add_message(f"알 수 없는 아이템({item_id})을(를) 획득했습니다!")

        # Check for level transition
        tile_changed_level = False

        # 1. Room Entrances
        if (player.x, player.y) in dungeon_map.room_entrances:
            target_room_index = dungeon_map.room_entrances[(player.x, player.y)]
            
            all_dungeon_maps[current_dungeon_level] = dungeon_map # Save current map
            last_entrance_position[current_floor] = (player.x, player.y) # Remember entrance position

            new_level = (current_floor, target_room_index)
            transition_message = f"{current_floor}층의 {target_room_index}번 방으로 들어갑니다."
            
            current_dungeon_level = new_level
            dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions)
            
            player.x, player.y = dungeon_map.start_x, dungeon_map.start_y
            tile_changed_level = True

        # 2. Exits
        elif (player.x, player.y) == (dungeon_map.exit_x, dungeon_map.exit_y):
            # (Handle locked doors logic if necessary)
            all_dungeon_maps[current_dungeon_level] = dungeon_map # Save current map

            if current_room_index == 0:  # Exit from Main Map -> Go to next floor
                new_level = (current_floor + 1, 0)
                transition_message = f"던전 {new_level[0]}층으로 이동합니다."
                player_pos_in_new_map = None # None will default to start_x, start_y
            else:  # Exit from Sub-Room -> Go back to Main Map
                new_level = (current_floor, 0)
                transition_message = f"{current_floor}층의 메인 맵으로 돌아왔습니다."
                # Return player to the entrance they came from
                player_pos_in_new_map = last_entrance_position.get(current_floor, None)

            current_dungeon_level = new_level
            dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions)
            
            if player_pos_in_new_map:
                player.x, player.y = player_pos_in_new_map
            else:
                player.x, player.y = dungeon_map.start_x, dungeon_map.start_y
            tile_changed_level = True

        # 3. Start Point (Previous floor)
        elif (player.x, player.y) == (dungeon_map.start_x, dungeon_map.start_y) and current_room_index == 0 and current_floor > 1:
            all_dungeon_maps[current_dungeon_level] = dungeon_map # Save current map
            
            new_level = (current_floor - 1, 0)
            transition_message = f"이전 층({new_level[0]}층)으로 돌아갑니다."
            
            current_dungeon_level = new_level
            dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions)
            
            player.x, player.y = dungeon_map.exit_x, dungeon_map.exit_y
            tile_changed_level = True

        # If level changed, update player state and UI
        if tile_changed_level:
            player.dungeon_level = current_dungeon_level
            dungeon_map.player_x, dungeon_map.player_y = player.x, player.y
            dungeon_map.visited.add((player.x, player.y))
            
            ui_instance.clear_screen()
            ui_instance.add_message(transition_message)
            # The loop will restart and redraw the new map

    # --- Game Over / Quit ---
    sys.stdout.write(ANSI.SHOW_CURSOR)
    player.dungeon_level = current_dungeon_level
    Start.save_game_data(player, all_dungeon_maps, ui_instance)
    
    return "DEATH" if not player.is_alive() else "QUIT"
