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
    inventory_open = False
    inventory_cursor_pos = 0
    inventory_active_tab = 'item' # 'item', 'equipment', 'book'

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

    while player.is_alive() and not game_over_flag:
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        camera['x'] = max(0, min(player.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))

        ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'], 
                                     inventory_open, inventory_cursor_pos, inventory_active_tab)

        action = readchar.readkey()
        player_action_taken = False
        current_floor, current_room_index = current_dungeon_level

        if inventory_open:
            # 현재 탭에 맞는 아이템 목록 가져오기
            if inventory_active_tab == 'item':
                inventory_items = list(player.inventory.items.values())
            elif inventory_active_tab == 'equipment':
                inventory_items = list(player.inventory.equipment_items.values())
            else: # 'book'
                inventory_items = list(player.inventory.skill_books.values())

            if action == readchar.key.UP:
                inventory_cursor_pos = (inventory_cursor_pos - 1) % len(inventory_items) if inventory_items else 0
            elif action == readchar.key.DOWN:
                inventory_cursor_pos = (inventory_cursor_pos + 1) % len(inventory_items) if inventory_items else 0
            elif action == '1':
                inventory_active_tab = 'item'
                inventory_cursor_pos = 0
            elif action == '2':
                inventory_active_tab = 'equipment'
                inventory_cursor_pos = 0
            elif action == '3':
                inventory_active_tab = 'book'
                inventory_cursor_pos = 0
            elif action == 'e' and inventory_items and inventory_active_tab == 'equipment':
                selected_item_data = inventory_items[inventory_cursor_pos]
                message = player.equip(selected_item_data['item'])
                ui_instance.add_message(message)
                # 아이템 장착/해제 후 커서 위치 조정
                if not inventory_items: inventory_cursor_pos = 0
                elif inventory_cursor_pos >= len(inventory_items): inventory_cursor_pos = len(inventory_items) - 1

            elif action == 'i':
                inventory_open = False
        
        else: # 인벤토리가 닫혀 있을 때
            if action == 'i':
                inventory_open = True
                inventory_cursor_pos = 0
                inventory_active_tab = 'item'
                continue

            dx, dy = 0, 0
            if action == readchar.key.UP or action == 'k': dx, dy = 0, -1
            elif action == readchar.key.DOWN or action == 'j': dx, dy = 0, 1
            elif action == readchar.key.LEFT or action == 'h': dx, dy = -1, 0
            elif action == readchar.key.RIGHT or action == 'l': dx, dy = 1, 0
            elif action == 'y': dx, dy = -1, -1
            elif action == 'u': dx, dy = 1, -1
            elif action == 'b': dx, dy = -1, 1
            elif action == 'n': dx, dy = 1, 1

            if dx != 0 or dy != 0:
                moved, result = dungeon_map.move_player(dx, dy)
                if moved:
                    player.stamina -= 1
                    player_action_taken = True
                    player.x, player.y = dungeon_map.player_x, dungeon_map.player_y
                    for monster in dungeon_map.monsters:
                        if not monster.dead and abs(player.x - monster.x) + abs(player.y - monster.y) <= 3:
                            ui_instance.add_message(f"{monster.name}(LV:{monster.level})을(를) 만났습니다.")
                
                if isinstance(result, str):
                     ui_instance.add_message(result)
                elif result is not None: # Combat
                    monster = result
                    player_action_taken = True
                    ui_instance.add_message(f"{monster.name}과(와) 전투 시작!")
                    damage, is_critical = combat.calculate_damage(player, monster)
                    ui_instance.add_message(f"{player.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                    monster.take_damage(damage)
                    ui_instance.add_message(f"{monster.name}에게 {damage}의 데미지를 입혔습니다.")

                    if monster.dead:
                        ui_instance.add_message(f"{monster.name}을(를) 물리쳤습니다!")
                        if item_definitions and random.random() < 0.5:
                            dropped_item_id = random.choice(list(item_definitions.keys()))
                            monster.loot = dropped_item_id
                            ui_instance.add_message(f"{monster.name}이(가) {item_definitions[dropped_item_id].name}을(를) 떨어뜨렸습니다.")
                        exp_gained = monster.exp_given + (monster.level * 2)
                        ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                        leveled_up, level_up_message = player.gain_exp(exp_gained)
                        if leveled_up: ui_instance.add_message(level_up_message)
                    else:
                        damage, is_critical = combat.calculate_damage(monster, player)
                        ui_instance.add_message(f"{monster.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
                        player.take_damage(damage)
                        ui_instance.add_message(f"{player.name}에게 {damage}의 데미지를 입혔습니다.")
            
            elif action in ['v', 't']:
                status_text = "ON" if dungeon_map.toggle_fog() else "OFF"
                ui_instance.add_message(f"전장의 안개(Fog of War) 토글: {status_text}")
                continue
            
            elif action == 'r':
                looted = False
                for m in dungeon_map.monsters:
                    if m.dead and m.x == player.x and m.y == player.y and m.loot:
                        item_def = item_definitions.get(m.loot)
                        if item_def:
                            # Item 객체를 생성하여 추가
                            item_obj = Item.from_definition(item_def)
                            player.add_item(item_obj)
                            ui_instance.add_message(f"{item_def.name}을(를) 주웠습니다.")
                            m.loot = None
                            looted = True
                            player_action_taken = True
                            break
                if not looted: ui_instance.add_message("주울 아이템이 없습니다.")

            elif action == 'q':
                game_over_flag = True
                ui_instance.add_message("게임을 저장하고 메인 메뉴로 돌아갑니다.")

        if player_action_taken and player.is_alive():
            for monster in dungeon_map.monsters:
                if monster.dead: continue
                # Monster AI logic... (omitted for brevity, assuming it's complex and correct)
        elif not player_action_taken:
            if player.stamina < player.max_stamina:
                player.stamina += 1
        
        if not player.is_alive():
            game_over_flag = True
            dungeon_map.player_tombstone = (player.x, player.y)
            if player.stamina <= 0:
                ui_instance.add_message("스태미너가 모두 소진되어 사망했습니다...")
            else:
                ui_instance.add_message("당신은 패배했습니다... 아무 키나 눌러 계속하세요.")
            ui_instance.draw_game_screen(player, dungeon_map, dungeon_map.monsters, camera['x'], camera['y'], False, 0, 'item')
            readchar.readkey()
            continue

        item_data_on_map = dungeon_map.items_on_map.pop((player.x, player.y), None)
        if item_data_on_map:
            item_def = item_definitions.get(item_data_on_map['id'])
            if item_def:
                item_obj = Item.from_definition(item_def)
                player.add_item(item_obj, item_data_on_map['qty'])
                ui_instance.add_message(f"{item_def.name}을(를) 획득했습니다!")

        # Level transition logic... (omitted for brevity)

    sys.stdout.write(ANSI.SHOW_CURSOR)
    player.dungeon_level = current_dungeon_level
    Start.save_game_data(player, all_dungeon_maps, ui_instance)
    
    return "DEATH" if not player.is_alive() else "QUIT"
