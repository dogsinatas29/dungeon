# game.py

import sys
from player import Player
from dungeon_map import DungeonMap, EXIT_NORMAL, EXIT_LOCKED, ITEM_TILE
from ui import UI, ANSI
import readchar
import Start
import data_manager
import combat
import random

ROOMS_PER_FLOOR = 3 # 각 층당 방의 개수

# run_game 함수에 ui_instance 인자 추가
def run_game(player_data_from_save, all_dungeon_maps_data_from_save_raw, item_definitions, ui_instance):
    # 플레이어 데이터 로드
    player = Player.from_dict(player_data_from_save)

    camera = {
        'x': 0,
        'y': 0
    }
    
    # 기존에 여기서 UI()를 생성하던 것을 삭제하고 인자로 받은 ui_instance를 사용합니다.
    # ui = UI()

    # 모든 던전 맵 데이터를 DungeonMap 객체들로 변환
    all_dungeon_maps = {}
    if all_dungeon_maps_data_from_save_raw:
        for level_str, map_dict in all_dungeon_maps_data_from_save_raw.items():
            # "floor,room" 문자열 키를 (floor, room) 튜플로 변환
            floor, room = map(int, level_str.split(','))
            all_dungeon_maps[(floor, room)] = DungeonMap.from_dict(map_dict)

    current_dungeon_level = player.dungeon_level # 플레이어의 현재 던전 레벨 (튜플)

    dungeon_map = None

    # 현재 던전 레벨에 해당하는 맵이 없으면 새로 생성
    if current_dungeon_level not in all_dungeon_maps:
        dungeon_map = DungeonMap(current_dungeon_level, ui_instance) # 튜플 전달
        dungeon_map._generate_random_map()
        dungeon_map._place_start_and_exit()
        dungeon_map.place_random_items(item_definitions)
        dungeon_map.place_monsters()
        dungeon_map.is_generated = True
        all_dungeon_maps[current_dungeon_level] = dungeon_map
        ui_instance.add_message(f"DEBUG: 레벨 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 새 맵 생성됨 (크기: {dungeon_map.width}x{dungeon_map.height})")
    else:
        # 이미 DungeonMap 객체로 변환된 맵을 사용
        dungeon_map = all_dungeon_maps[current_dungeon_level]
        # 로드된 맵에 ui_instance 설정 (from_dict에서는 None으로 초기화됨)
        dungeon_map.ui_instance = ui_instance
        ui_instance.add_message(f"DEBUG: 레벨 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 맵 로드됨 (크기: {dungeon_map.width}x{dungeon_map.height})")

    # 플레이어 위치를 현재 활성화된 던전 맵의 시작 위치와 동기화
    player.x = dungeon_map.player_x
    player.y = dungeon_map.player_y


    game_over_flag = False

    ui_instance.clear_screen() # 화면을 깨끗하게 지웁니다.
    ui_instance.print_at(1, 1, f"--- {player.name} 님의 모험 시작 ---")
    ui_instance.print_at(2, 1, f"현재 HP: {player.hp}/{player.max_hp}, MP: {player.mp}/{player.max_mp}")
    ui_instance.print_at(3, 1, "던전을 탐험하고 있습니다...")

    ui_instance.add_message(f"DEBUG (초기 상태): 현재 던전 레벨: {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방")
    ui_instance.add_message(f"DEBUG (초기 상태): 플레이어 시작 위치: ({player.x},{player.y})")
    ui_instance.add_message(f"DEBUG (초기 상태): 출구 위치: ({dungeon_map.exit_x},{dungeon_map.exit_y}), 타입: {dungeon_map.exit_type}")
    if dungeon_map.exit_type == EXIT_LOCKED:
        ui_instance.add_message(f"DEBUG (초기 상태): 필요 열쇠: {dungeon_map.required_key_id}, 개수: {dungeon_map.required_key_count}")

    # 이 디버그 print 문을 ui_instance.add_message로 변경
    ui_instance.add_message(f"DEBUG (Initial Game State - Message Log): Items on map: {dungeon_map.items_on_map}")


    # 초기 화면 렌더링을 명시적으로 호출하여 버퍼 내용을 터미널에 출력
    ui_instance.draw_game_screen(player, dungeon_map, camera['x'], camera['y'])

    # 이 메시지는 draw_game_screen 이후에 나와야 보이므로, 다음 draw_game_screen 전에 입력 대기를 시킵니다.
    ui_instance.print_at(ui_instance.terminal_height - 1, 1, "아무 키나 눌러 게임 시작...".ljust(ui_instance.terminal_width - 1))
    sys.stdout.flush() # 이 메시지를 바로 출력하기 위함.
    readchar.readkey()
    
    # 게임 시작 직전 마지막으로 화면을 지우고 게임 루프로 진입합니다.
    ui_instance.clear_screen() 

    while player.is_alive() and not game_over_flag:
        # --- 카메라 위치 업데이트 ---
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT

        # 1. 플레이어를 뷰포트 중앙에 위치시키도록 카메라 목표 위치 설정
        camera['x'] = player.x - map_viewport_width // 2
        camera['y'] = player.y - map_viewport_height // 2

        # 2. 카메라가 맵 경계를 벗어나지 않도록 위치 보정 (Clamping)
        camera['x'] = max(0, min(camera['x'], dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(camera['y'], dungeon_map.height - map_viewport_height))
        # --- 카메라 위치 업데이트 끝 ---

        # 매 루프마다 게임 화면을 다시 그립니다.
        ui_instance.draw_game_screen(player, dungeon_map, camera['x'], camera['y'])

        ui_instance.print_at(0, 0, f"현재 층: {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방")

        command_prompt_y = ui_instance.message_log_y_start + ui_instance.message_log_height
        command_prompt_x = 1

        ui_instance.print_at(command_prompt_y, command_prompt_x,
                     "Command (↑↓←→:Move / i:Toggle UI / q:Quit / 1-0:Skill/Item): " + " " * (ui_instance.terminal_width - 70))
        # 명령 프롬프트도 버퍼에 그려진 후 draw_game_screen에서 실제 터미널에 반영되므로 flush 필요 없음.

        action = readchar.readkey()
        
        player_action_taken = False # 플레이어가 턴을 소모하는 행동을 했는지 여부

        # 이동 처리
        dx, dy = 0, 0
        if action == readchar.key.UP: dx, dy = 0, -1
        elif action == readchar.key.DOWN: dx, dy = 0, 1
        elif action == readchar.key.LEFT: dx, dy = -1, 0
        elif action == readchar.key.RIGHT: dx, dy = 1, 0

        if dx != 0 or dy != 0:
            target_x, target_y = player.x + dx, player.y + dy
            
            # 목표 지점에 몬스터가 있는지 확인
            monster_at_target = None
            for m in dungeon_map.monsters:
                if m.x == target_x and m.y == target_y and not m.dead:
                    monster_at_target = m
                    break
            
            if monster_at_target:
                # 몬스터가 있으면 공격 (기본 공격)
                ui_instance.add_message(f"플레이어가 {monster_at_target.char}을(를) 공격!")
                monster_at_target.take_damage(10) # 임시 기본 공격 데미지
                if monster_at_target.dead:
                    ui_instance.add_message(f"{monster_at_target.char}을(를) 쓰러뜨렸다!")
                player_action_taken = True
            # 목표 지점이 잠긴 문인지 확인
            elif (target_x, target_y) == (dungeon_map.exit_x, dungeon_map.exit_y) and dungeon_map.exit_type == EXIT_LOCKED:
                # (이전 로직과 동일)
                required_key_id = dungeon_map.required_key_id
                required_key_count = dungeon_map.required_key_count
                if player.get_item_quantity(required_key_id) >= required_key_count:
                    moved, message = dungeon_map.move_player(dx, dy)
                    ui_instance.add_message(message)
                    player_action_taken = True
                else:
                    player_key_count = player.get_item_quantity(required_key_id)
                    if player_key_count == 0: ui_instance.add_message("문이 잠겨 있습니다. 열쇠가 없습니다.")
                    else: ui_instance.add_message(f"문이 잠겨 있습니다. 열쇠가 {required_key_count - player_key_count}개 부족합니다.")
            else:
                # 일반 이동
                moved, message = dungeon_map.move_player(dx, dy)
                if moved:
                    player_action_taken = True
                ui_instance.add_message(message)

        elif action.isdigit():
            # 스킬 사용 로직
            skill_to_use = None
            if action == '1': skill_to_use = 'Fireball'
            elif action == '2': skill_to_use = 'Heal'
            
            if skill_to_use:
                if skill_to_use == 'Fireball':
                    # 가장 가까운 몬스터 찾기 (간단한 타겟팅)
                    target_monster = None
                    closest_dist = float('inf')
                    for m in dungeon_map.monsters:
                        if not m.dead:
                            dist = abs(player.x - m.x) + abs(player.y - m.y)
                            if dist < closest_dist:
                                closest_dist = dist
                                target_monster = m
                    
                    if combat.use_skill_in_combat(player, skill_to_use, target_monster, ui_instance):
                        if target_monster and target_monster.dead:
                            ui_instance.add_message(f"{target_monster.char}을(를) 쓰러뜨렸다!")
                        player_action_taken = True
                
                elif skill_to_use == 'Heal':
                    if combat.use_skill_in_combat(player, skill_to_use, ui_instance=ui_instance):
                        player_action_taken = True
        
        elif action == 'i':
            ui_instance.toggle_skill_inventory()
            ui_instance.add_message("UI 토글")
            ui_instance.draw_game_screen(player, dungeon_map, camera['x'], camera['y'])
            continue
        elif action == 'q':
            # (기존과 동일)
            ui_instance.add_message("게임을 종료합니다.")
            game_over_flag = True
            player.dungeon_level = current_dungeon_level
            Start.save_game_data(player, all_dungeon_maps, ui_instance)
        elif action == '\x03': # Ctrl+C
            # (기존과 동일)
            ui_instance.add_message("게임을 강제 종료합니다.")
            game_over_flag = True
        else:
            ui_instance.add_message(f"알 수 없는 입력: '{action}'")

        # 몬스터 턴 처리
        if player_action_taken and player.is_alive():
            for monster in dungeon_map.monsters:
                if not monster.dead:
                    # 간단한 AI: 플레이어가 근처에 있으면 공격, 아니면 플레이어 쪽으로 이동
                    dist_x = abs(player.x - monster.x)
                    dist_y = abs(player.y - monster.y)

                    if dist_x <= 1 and dist_y <= 1:
                        monster.attack(player)
                    else:
                        # 플레이어 방향으로 한 칸 이동
                        move_dx, move_dy = 0, 0
                        if player.x > monster.x: move_dx = 1
                        elif player.x < monster.x: move_dx = -1
                        
                        if player.y > monster.y: move_dy = 1
                        elif player.y < monster.y: move_dy = -1
                        
                        # 대각선 이동 방지 (하나의 축으로만 이동)
                        if move_dx != 0 and move_dy != 0:
                            if random.random() < 0.5: move_dx = 0
                            else: move_dy = 0

                        new_monster_x, new_monster_y = monster.x + move_dx, monster.y + move_dy
                        
                        # 이동할 위치가 벽이 아니고 다른 몬스터가 없는지 확인
                        can_move = True
                        if dungeon_map.map_data[new_monster_y][new_monster_x] in ['▒', '▓']:
                            can_move = False
                        for other_m in dungeon_map.monsters:
                            if other_m is not monster and other_m.x == new_monster_x and other_m.y == new_monster_y:
                                can_move = False
                                break
                        
                        if can_move:
                            monster.x = new_monster_x
                            monster.y = new_monster_y

        # 플레이어 사망 체크
        if not player.is_alive():
            game_over_flag = True
            ui_instance.add_message("당신은 패배했습니다...")

        # --- 루프의 나머지 부분 (아이템 줍기, 출구/입구 도착 등) ---
        # 이동이 성공했거나 아이템을 획득, 출구에 도달 등 상태 변화가 있는 경우
        # 플레이어 객체의 좌표를 dungeon_map의 좌표와 동기화
        player.x = dungeon_map.player_x
        player.y = dungeon_map.player_y

        current_player_x, current_player_y = player.x, player.y
        ui_instance.add_message(f"DEBUG (이동 후): 플레이어 위치: ({current_player_x},{current_player_y})")
        tile_at_player_pos = dungeon_map.get_tile(current_player_x, current_player_y)
        ui_instance.add_message(f"DEBUG (이동 후): 현재 타일 유형: '{tile_at_player_pos}'")
        item_data_at_pos = dungeon_map.items_on_map.get((current_player_x, current_player_y))
        ui_instance.add_message(f"DEBUG (이동 후): 아이템 데이터 (dungeon_map.items_on_map): {item_data_at_pos}")
        ui_instance.add_message(f"DEBUG (이동 후): 맵에 남은 모든 아이템: {dungeon_map.items_on_map}")


        # 이전 맵으로 돌아가는 로직
        if (current_player_x, current_player_y) == (dungeon_map.start_x, dungeon_map.start_y) and (current_dungeon_level[0] > 0 or current_dungeon_level[1] > 0):
            all_dungeon_maps[current_dungeon_level] = dungeon_map # 현재 맵 상태 저장
            
            # 이전 방으로 이동
            new_floor, new_room = current_dungeon_level[0], current_dungeon_level[1] - 1
            if new_room < 0: # 현재 층의 첫 번째 방에서 뒤로 가면 이전 층의 마지막 방으로 이동
                new_floor -= 1
                new_room = ROOMS_PER_FLOOR - 1
            
            current_dungeon_level = (new_floor, new_room)
            player.dungeon_level = current_dungeon_level
            
            dungeon_map = all_dungeon_maps[current_dungeon_level] # 이전 맵 로드
            dungeon_map.ui_instance = ui_instance # 로드된 맵에 ui_instance 설정
            
            # 이전 맵의 출구 위치로 플레이어 이동
            player.x = dungeon_map.exit_x
            player.y = dungeon_map.exit_y
            dungeon_map.player_x = player.x
            dungeon_map.player_y = player.y

            ui_instance.clear_screen()
            ui_instance.add_message(f"던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방으로 돌아왔습니다.")
            # 다음 루프에서 화면이 다시 그려지므로 여기서 별도 렌더링 불필요


        if item_data_at_pos:
            item_id_to_add = item_data_at_pos['id']
            item_qty_to_add = item_data_at_pos['qty']

            del dungeon_map.items_on_map[(current_player_x, current_player_y)] # 맵에서 아이템 제거

            player.add_item(item_id_to_add, item_qty_to_add) # 플레이어 인벤토리에 추가

            item_def = item_definitions.get(item_id_to_add)
            if item_def:
                ui_instance.add_message(f"{item_def.name}을(를) 획득했습니다!")
                ui_instance.add_message(f"DEBUG (아이템 획득): '{item_def.name}' 획득됨. 플레이어 인벤토리: {player.inventory}")
            else:
                ui_instance.add_message(f"알 수 없는 아이템 ({item_id_to_add})을(를) 획득했습니다!")

        # 출구에 도달했는지 확인
        if current_player_x == dungeon_map.exit_x and \
           current_player_y == dungeon_map.exit_y:

            ui_instance.add_message(f"DEBUG (출구 확인): 출구에 도착. 출구 타입: {dungeon_map.exit_type}")
            if dungeon_map.exit_type == EXIT_LOCKED:
                ui_instance.add_message(f"DEBUG (출구 확인): 필요 열쇠 ID: {dungeon_map.required_key_id}, 개수: {dungeon_map.required_key_count}")
                ui_instance.add_message(f"DEBUG (출구 확인): 플레이어 보유 열쇠: {player.get_item_quantity(dungeon_map.required_key_id)}개")
                ui_instance.add_message(f"DEBUG (출구 확인): 플레이어 인벤토리: {player.inventory}")


            if dungeon_map.exit_type == EXIT_LOCKED:
                required_key_id = dungeon_map.required_key_id
                required_key_count = dungeon_map.required_key_count

                if player.get_item_quantity(required_key_id) >= required_key_count:
                    # player.remove_item(required_key_id, required_key_count) # 열쇠를 소모하지 않음
                    ui_instance.add_message(f"올바른 열쇠를 가지고 있어 문을 열었습니다!")

                    all_dungeon_maps[current_dungeon_level] = dungeon_map # 현재 던전 맵 상태 저장

                    ui_instance.clear_screen() # 화면과 버퍼 초기화
                    
                    # 메시지를 버퍼에 그립니다.
                    ui_instance.print_at(ui_instance.terminal_height // 2 - 2, ui_instance.terminal_width // 2 - 15, "==================================")
                    ui_instance.print_at(ui_instance.terminal_height // 2 - 1, ui_instance.terminal_width // 2 - 15, f"        던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 클리어!        ")
                    ui_instance.print_at(ui_instance.terminal_height // 2, ui_instance.terminal_width // 2 - 15, "        다음 던전으로 이동합니다...        ")
                    ui_instance.print_at(ui_instance.terminal_height // 2 + 1, ui_instance.terminal_width // 2 - 15, "==================================")
                    ui_instance.print_at(ui_instance.terminal_height // 2 + 3, ui_instance.terminal_width // 2 - 15, "아무 키나 눌러 계속하세요...".ljust(30))

                    ui_instance.draw_game_screen(None, None) # 버퍼의 내용을 화면에 출력
                    readchar.readkey()

                    # 다음 방 또는 다음 층으로 이동
                    new_floor, new_room = current_dungeon_level[0], current_dungeon_level[1] + 1
                    if new_room >= ROOMS_PER_FLOOR: # 현재 층의 마지막 방이면 다음 층으로 이동
                        new_floor += 1
                        new_room = 0
                    
                    current_dungeon_level = (new_floor, new_room)
                    player.dungeon_level = current_dungeon_level # 플레이어 객체의 던전 레벨 업데이트

                    # 다음 던전 맵 로드 또는 생성
                    if current_dungeon_level in all_dungeon_maps:
                        dungeon_map = all_dungeon_maps[current_dungeon_level] # 기존 맵 로드
                        message_to_display = f"던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 (이전 방문)으로 이동했습니다."
                    else:
                        new_dungeon_map = DungeonMap(current_dungeon_level, ui_instance) # 새 맵 생성
                        new_dungeon_map._generate_random_map()
                        new_dungeon_map._place_start_and_exit()
                        new_dungeon_map.place_random_items(item_definitions)
                        new_dungeon_map.place_monsters()
                        new_dungeon_map.is_generated = True
                        all_dungeon_maps[current_dungeon_level] = new_dungeon_map
                        dungeon_map = new_dungeon_map
                        message_to_display = f"던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 (새로운 던전)으로 이동했습니다."

                    player.x = dungeon_map.player_x # 새 맵의 시작 위치로 플레이어 이동
                    player.y = dungeon_map.player_y

                    ui_instance.clear_screen()
                    ui_instance.add_message(message_to_display)

                else:
                    player_key_count = player.get_item_quantity(required_key_id)
                    if player_key_count == 0:
                        ui_instance.add_message("문이 잠겨 있습니다. 열쇠가 없습니다.")
                    else:
                        missing_keys = required_key_count - player_key_count
                        ui_instance.add_message(f"문이 잠겨 있습니다. 열쇠가 {missing_keys}개 부족합니다.")

            elif dungeon_map.exit_type == EXIT_NORMAL: # 잠기지 않은 출구인 경우
                all_dungeon_maps[current_dungeon_level] = dungeon_map # 현재 던전 맵 상태 저장

                ui_instance.clear_screen() # 화면과 버퍼 초기화

                # 메시지를 버퍼에 그립니다.
                ui_instance.print_at(ui_instance.terminal_height // 2 - 2, ui_instance.terminal_width // 2 - 15, "==================================")
                ui_instance.print_at(ui_instance.terminal_height // 2 - 1, ui_instance.terminal_width // 2 - 15, f"        던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 클리어!        ")
                ui_instance.print_at(ui_instance.terminal_height // 2, ui_instance.terminal_width // 2 - 15, "        다음 던전으로 이동합니다...        ")
                ui_instance.print_at(ui_instance.terminal_height // 2 + 1, ui_instance.terminal_width // 2 - 15, "==================================")
                ui_instance.print_at(ui_instance.terminal_height // 2 + 3, ui_instance.terminal_width // 2 - 15, "아무 키나 눌러 계속하세요...".ljust(30))

                ui_instance.draw_game_screen(None, None) # 버퍼의 내용을 화면에 출력
                readchar.readkey()

                # 다음 방 또는 다음 층으로 이동
                new_floor, new_room = current_dungeon_level[0], current_dungeon_level[1] + 1
                if new_room >= ROOMS_PER_FLOOR: # 현재 층의 마지막 방이면 다음 층으로 이동
                    new_floor += 1
                    new_room = 0
                
                current_dungeon_level = (new_floor, new_room)
                player.dungeon_level = current_dungeon_level # 플레이어 객체의 던전 레벨 업데이트

                # 다음 던전 맵 로드 또는 생성
                if current_dungeon_level in all_dungeon_maps:
                    dungeon_map = all_dungeon_maps[current_dungeon_level] # 기존 맵 로드
                    message_to_display = f"던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 (이전 방문)으로 이동했습니다."
                else:
                    new_dungeon_map = DungeonMap(current_dungeon_level, ui_instance) # 새 맵 생성
                    new_dungeon_map._generate_random_map()
                    new_dungeon_map._place_start_and_exit()
                    new_dungeon_map.place_random_items(item_definitions)
                    new_dungeon_map.place_monsters()
                    new_dungeon_map.is_generated = True
                    all_dungeon_maps[current_dungeon_level] = new_dungeon_map
                    dungeon_map = new_dungeon_map
                    message_to_display = f"던전 {current_dungeon_level[0]}층 - {current_dungeon_level[1]}방 (새로운 던전)으로 이동했습니다."

                player.x = dungeon_map.player_x # 새 맵의 시작 위치로 플레이어 이동
                player.y = dungeon_map.player_y

                ui_instance.clear_screen()
                ui_instance.add_message(message_to_display)

    sys.stdout.write(ANSI.SHOW_CURSOR) # 게임 종료 시 커서를 다시 보이게 합니다.
    sys.stdout.flush()

    if not player.is_alive():
        player.dungeon_level = current_dungeon_level
        Start.save_game_data(player, all_dungeon_maps, ui_instance) # 사망 시에도 게임 상태 저장
        return "DEATH"
    else:
        player.dungeon_level = current_dungeon_level
        Start.save_game_data(player, all_dungeon_maps, ui_instance) # 정상 종료 시 게임 상태 저장
        return "QUIT"
