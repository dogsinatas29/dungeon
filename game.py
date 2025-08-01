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
    # readchar.readkey()
    ui_instance.clear_screen() 

    # --- Main Game Loop ---
    while player.is_alive() and not game_over_flag:
        # --- Update & Draw ---
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        camera['x'] = max(0, min(player.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))

        ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'])

        # --- Input & Action ---
        action = readchar.readkey()
        player_action_taken = False

        # Unpack current level for use in this loop iteration
        current_floor, current_room_index = current_dungeon_level

        dx, dy = 0, 0
        if action == readchar.key.UP or action == 'k': dx, dy = 0, -1
        elif action == readchar.key.DOWN or action == 'j': dx, dy = 0, 1
        elif action == readchar.key.LEFT or action == 'h': dx, dy = -1, 0
        elif action == readchar.key.RIGHT or action == 'l': dx, dy = 1, 0
        # 대각선 이동 추가
        elif action == 'y': dx, dy = -1, -1
        elif action == 'u': dx, dy = 1, -1
        elif action == 'b': dx, dy = -1, 1
        elif action == 'n': dx, dy = 1, 1

        if dx != 0 or dy != 0:
            moved, result = dungeon_map.move_player(dx, dy) # result can be a message or a monster
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

            if isinstance(result, str): # It's a message
                 ui_instance.add_message(result)
                 # 메시지 출력 후 즉시 화면을 다시 그려서 렌더링 깨짐 방지
                 ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'])
            elif result is not None: # It's a monster, initiate combat
                monster = result
                player_action_taken = True
                ui_instance.add_message(f"{monster.name}과(와) 전투 시작!")

                damage, is_critical = combat.calculate_damage(player, monster)
                ui_instance.add_message(f"{player.name}의 공격!")
                if is_critical:
                    ui_instance.add_message("💥치명타!💥")
                
                monster.take_damage(damage)
                ui_instance.add_message(f"{monster.name}에게 {damage}의 데미지를 입혔습니다.")

                if monster.dead:
                    ui_instance.add_message(f"{monster.name}을(를) 물리쳤습니다!")
                    
                    # 아이템 드랍 로직
                    if item_definitions:
                        # 50% 확률로 아이템 드랍
                        if random.random() < 0.5:
                            dropped_item_id = random.choice(list(item_definitions.keys()))
                            monster.loot = dropped_item_id
                            item_name = item_definitions[dropped_item_id].name
                            ui_instance.add_message(f"{monster.name}이(가) {item_name}을(를) 떨어뜨렸습니다.")

                    # 경험치 획득
                    exp_gained = monster.exp_given + (monster.level * 2)
                    ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                    
                    leveled_up, level_up_message = player.gain_exp(exp_gained)
                    if leveled_up:
                        ui_instance.add_message(level_up_message)
                else:
                    damage, is_critical = combat.calculate_damage(monster, player)
                    ui_instance.add_message(f"{monster.name}의 공격!")
                    if is_critical:
                        ui_instance.add_message("💥치명타!💥")

                    player.take_damage(damage)
                    ui_instance.add_message(f"{player.name}에게 {damage}의 데미지를 입혔습니다.")
        
        elif action in ['v', 't']:
            # 안개 토글 키
            fog_status = dungeon_map.toggle_fog()
            status_text = "ON" if fog_status else "OFF"
            ui_instance.add_message(f"전장의 안개(Fog of War) 토글: {status_text}")
            # 턴을 소모하지 않는 행동이므로, 즉시 루프를 다시 시작하여 화면을 갱신합니다.
            continue
        
        elif action == 'r':
            # 아이템 루팅 로직
            looted_item = False
            for monster in dungeon_map.monsters:
                if monster.dead and monster.x == player.x and monster.y == player.y and monster.loot:
                    item_id = monster.loot
                    item_def = item_definitions.get(item_id)
                    if item_def:
                        player.add_item(item_id, item_def.name)
                        ui_instance.add_message(f"{item_def.name}을(를) 주웠습니다.")
                        monster.loot = None # 아이템을 줍고 나면 비움
                        looted_item = True
                        player_action_taken = True # 턴 소모
                        break # 한 번에 하나의 시체만 루팅
            if not looted_item:
                ui_instance.add_message("주울 아이템이 없습니다.")

        elif action == 'q':
            game_over_flag = True
            ui_instance.add_message("게임을 저장하고 메인 메뉴로 돌아갑니다.")
        # (Other actions like skills, inventory...)

        # --- Monster Turn ---
        if player_action_taken and player.is_alive():
            for monster in dungeon_map.monsters:
                if monster.dead:
                    continue

                action_taken_by_monster = False
                distance_to_player = abs(monster.x - player.x) + abs(monster.y - player.y)

                # 몬스터 행동 결정 (도망, 추격)
                should_flee = monster.move_type == 'COWARD' and monster.hp < monster.max_hp / 3
                should_chase = (monster.move_type == 'AGGRESSIVE' or monster.is_provoked) and distance_to_player <= 8

                if should_flee or should_chase:
                    # 목표 방향 설정 (추격이면 플레이어 쪽, 도망이면 반대쪽)
                    mdx, mdy = 0, 0
                    if player.x < monster.x: mdx = -1
                    elif player.x > monster.x: mdx = 1
                    if player.y < monster.y: mdy = -1
                    elif player.y > monster.y: mdy = 1
                    
                    if should_flee:
                        mdx, mdy = -mdx, -mdy # 도망은 방향 반전

                    # 지능적인 이동: 대각선 -> 수평/수직 순으로 시도
                    potential_moves = []
                    # 1. 대각선 이동 (가장 선호)
                    if mdx != 0 and mdy != 0:
                        potential_moves.append((mdx, mdy))
                    # 2. 축 방향 이동 (우선순위 무작위)
                    if random.random() < 0.5:
                        if mdx != 0: potential_moves.append((mdx, 0))
                        if mdy != 0: potential_moves.append((0, mdy))
                    else:
                        if mdy != 0: potential_moves.append((0, mdy))
                        if mdx != 0: potential_moves.append((mdx, 0))

                    # 가능한 첫 번째 이동 실행
                    for move_dx, move_dy in potential_moves:
                        new_mx, new_my = monster.x + move_dx, monster.y + move_dy
                        
                        # 대각선 이동 시, 코너를 통과하는지 확인
                        if move_dx != 0 and move_dy != 0:
                            if not dungeon_map.is_walkable_for_monster(monster.x + move_dx, monster.y) or \
                               not dungeon_map.is_walkable_for_monster(monster.x, monster.y + move_dy):
                                continue # 코너 통과 불가, 다음 이동 시도

                        if dungeon_map.is_walkable_for_monster(new_mx, new_my):
                            monster.x = new_mx
                            monster.y = new_my
                            action_taken_by_monster = True
                            break # 이동에 성공했으므로 루프 탈출
                
                if action_taken_by_monster:
                    continue

                # 3. 배회 로직 (위 조건에 해당하지 않을 경우)
                if monster.move_type in ['PASSIVE', 'AGGRESSIVE']:
                    if random.random() < 0.5: # 50% 확률로 이동
                        mdx, mdy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                        new_mx, new_my = monster.x + mdx, monster.y + mdy
                        if dungeon_map.is_walkable_for_monster(new_mx, new_my):
                            monster.x = new_mx
                            monster.y = new_my
        
        if not player.is_alive():
            game_over_flag = True
            dungeon_map.player_tombstone = (player.x, player.y)
            ui_instance.add_message("당신은 패배했습니다... 아무 키나 눌러 계속하세요.")
            
            # 마지막 화면(무덤)을 다시 그림
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'])
            
            # 사용자가 마지막 화면을 볼 수 있도록 키 입력 대기
            readchar.readkey()
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
