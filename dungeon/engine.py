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
from .entity import EntityManager
from .component import PositionComponent, MovableComponent, MoveRequestComponent, InteractableComponent, ProjectileComponent, DamageRequestComponent, HealthComponent, NameComponent, AttackComponent, DefenseComponent, DeathComponent, GameOverComponent # GameOverComponent 추가
from .system import MovementSystem, CollisionSystem, InteractionSystem, ProjectileSystem, CombatSystem, DungeonGenerationSystem, DeathSystem, GameOverSystem # GameOverSystem 추가
from .trap import Trap # Trap 클래스 임포트

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

def run_game(item_definitions, ui_instance):

    monster_definitions = data_manager.load_monster_definitions(ui_instance)
    entity_manager = EntityManager()
    dungeon_map = None # dungeon_map 변수 미리 선언

    save_load_system = SaveLoadSystem(entity_manager) # SaveLoadSystem 초기화
    
    # 게임 로드 (SaveLoadSystem 사용)
    game_state_data = data_manager.load_game_data()
    player, all_dungeon_maps = save_load_system.load_game(game_state_data, ui_instance)
    player_entity_id = player.entity_id # 로드된 플레이어 엔티티 ID 사용

    # 로드된 데이터로 컴포넌트 업데이트 (필요시)
    # 예: PositionComponent 업데이트
    player_pos_comp = entity_manager.get_component(player_entity_id, PositionComponent)
    if player_pos_comp:
        player_pos_comp.x = player_data_from_save.get('x', 0)
        player_pos_comp.y = player_data_from_save.get('y', 0)
        player_pos_comp.map_id = player.dungeon_level # Player 객체의 dungeon_level을 map_id로 사용

    # 나머지 시스템 초기화
    movement_system = MovementSystem(entity_manager, dungeon_map)
    collision_system = CollisionSystem(entity_manager, dungeon_map)
    interaction_system = InteractionSystem(entity_manager, dungeon_map, player_entity_id, ui_instance) # InteractionSystem 초기화
    projectile_system = ProjectileSystem(entity_manager, dungeon_map, ui_instance) # ProjectileSystem 초기화
    combat_system = CombatSystem(entity_manager, ui_instance, dungeon_map) # CombatSystem 초기화 시 dungeon_map 전달
    dungeon_generation_system = DungeonGenerationSystem(entity_manager, dungeon_map, ui_instance, item_definitions, monster_definitions) # DungeonGenerationSystem 초기화
    death_system = DeathSystem(entity_manager, dungeon_map, ui_instance, player_entity_id) # DeathSystem 초기화
    game_over_system = GameOverSystem(entity_manager, dungeon_map, ui_instance, player_entity_id) # GameOverSystem 초기화
    rendering_system = RenderingSystem(entity_manager, dungeon_map, ui_instance, player_entity_id) # RenderingSystem 초기화
    inventory_system = InventorySystem(entity_manager, ui_instance, item_definitions) # InventorySystem 초기화

    def get_or_create_map(level, all_maps, ui, items_def, monster_defs, is_boss_room=False):
        if level in all_maps:
            d_map = all_maps[level]
            d_map.ui_instance = ui
            d_map.entity_manager = entity_manager # entity_manager 전달
            
            # --- 몬스터 리젠 로직 ---
            # 기존 몬스터 목록을 초기화하고 새로 배치합니다.
            # ECS로 전환됨에 따라 몬스터 엔티티를 제거하고 다시 생성해야 함
            # (나중에 몬스터 엔티티 관리 로직을 더 정교하게 만들 수 있음)
            for monster_entity_id in list(entity_manager.get_components_of_type(PositionComponent).keys()):
                if monster_entity_id != player_entity_id: # 플레이어 엔티티는 제외
                    entity_manager.remove_entity(monster_entity_id)
            d_map.monsters.clear() # 기존 몬스터 객체 목록도 비움

            # DungeonGenerationSystem을 사용하여 엔티티 생성
            dungeon_generation_system.dungeon_map = d_map # 현재 맵을 시스템에 전달
            dungeon_generation_system.generate_dungeon_entities(level, is_boss_room=is_boss_room)

            return d_map
        else:
            d_map = DungeonMap(level, ui, is_boss_room=is_boss_room, monster_definitions=monster_defs, entity_manager=entity_manager)
            # DungeonGenerationSystem을 사용하여 엔티티 생성
            dungeon_generation_system.dungeon_map = d_map # 현재 맵을 시스템에 전달
            dungeon_generation_system.generate_dungeon_entities(level, is_boss_room=is_boss_room)

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
    movement_system.dungeon_map = dungeon_map # MovementSystem에 현재 맵 전달
    collision_system.dungeon_map = dungeon_map # CollisionSystem에 현재 맵 전달
    interaction_system.dungeon_map = dungeon_map # InteractionSystem에 현재 맵 전달
    projectile_system.dungeon_map = dungeon_map # ProjectileSystem에 현재 맵 전달
    combat_system.dungeon_map = dungeon_map # CombatSystem에 현재 맵 전달
    dungeon_generation_system.dungeon_map = dungeon_map # DungeonGenerationSystem에 현재 맵 전달
    death_system.dungeon_map = dungeon_map # DeathSystem에 현재 맵 전달
    game_over_system.dungeon_map = dungeon_map # GameOverSystem에 현재 맵 전달

    player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
    player_pos.x, player_pos.y = dungeon_map.player_x, dungeon_map.player_y

    ui_instance.clear_screen()

    turn_count = 0
    rest_turn_count = 0

    game_state = 'NORMAL'
    aiming_skill = None
    
    # --- 애니메이션 관련 변수 ---
    # animation_data = None # ProjectileSystem으로 대체

    # def handle_animation(): # ProjectileSystem으로 대체
    #     pass # 기존 로직 제거

    def use_projectile_skill(player_char, dungeon, skill):
        nonlocal game_state
        player_pos = entity_manager.get_component(player_char.entity_id, PositionComponent)
        if not player_pos: return False

        visible_monsters = []
        for monster_obj in dungeon.monsters:
            if not monster_obj.dead:
                monster_pos = entity_manager.get_component(monster_obj.entity_id, PositionComponent)
                if monster_pos and (monster_pos.x, monster_pos.y) in dungeon.visited:
                    visible_monsters.append((monster_obj, monster_pos))

        if not visible_monsters:
            ui_instance.add_message("주변에 보이는 몬스터가 없습니다.")
            return False

        closest_monster_data = min(visible_monsters, key=lambda m_data: math.sqrt((player_pos.x - m_data[1].x)**2 + (player_pos.y - m_data[1].y)**2))
        closest_monster_obj, closest_monster_pos = closest_monster_data
        
        # 스킬 사거리 체크
        distance = math.sqrt((player_pos.x - closest_monster_pos.x)**2 + (player_pos.y - closest_monster_pos.y)**2)
        if distance > skill.range_str:
            ui_instance.add_message(f"'{skill.name}' 스킬의 사거리가 닿지 않습니다. (사거리: {skill.range_str})")
            return False

        # 발사체 엔티티 생성
        projectile_entity_id = entity_manager.create_entity()
        entity_manager.add_component(projectile_entity_id, PositionComponent(x=player_pos.x, y=player_pos.y))
        
        # 발사체 방향 계산
        dx = 0
        dy = 0
        if closest_monster_pos.x > player_pos.x: dx = 1
        elif closest_monster_pos.x < player_pos.x: dx = -1
        if closest_monster_pos.y > player_pos.y: dy = 1
        elif closest_monster_pos.y < player_pos.y: dy = -1

        entity_manager.add_component(projectile_entity_id, ProjectileComponent(
            damage=skill.damage, 
            range=skill.range_str, 
            current_range=skill.range_str, 
            shooter_id=player_char.entity_id,
            dx=dx, dy=dy,
            skill_def_id=skill.id
        ))
        entity_manager.add_component(projectile_entity_id, RenderComponent(symbol='*', color='yellow')) # 발사체 심볼 및 색상 추가

        ui_instance.add_message(f"'{skill.name}'을(를) 발사했습니다!")
        return True

    running = True
    while running:
        map_viewport_width = ui_instance.MAP_VIEWPORT_WIDTH
        map_viewport_height = ui_instance.MAP_VIEWPORT_HEIGHT
        player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
        camera['x'] = max(0, min(player_pos.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
        camera['y'] = max(0, min(player_pos.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))
        
        if game_state != 'ANIMATING':


            rendering_system.update(camera['x'], camera['y'],
                                    inventory_open, inventory_cursor_pos,
                                    inventory_active_tab, inventory_scroll_offset,
                                    log_viewer_open, log_viewer_scroll_offset)

        if entity_manager.has_component(player_entity_id, GameOverComponent):
            game_over_comp = entity_manager.get_component(player_entity_id, GameOverComponent)
            if not game_over_comp.win: # If it's a loss
                readchar.readkey()
            running = False
            continue

        player_action_taken = False
        
        # if game_state == 'ANIMATING': # ProjectileSystem으로 대체
        #     handle_animation()
        # else:
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
                                # InventorySystem에 장착/해제 요청
                                message = inventory_system.equip_unequip_item(player_entity_id, selected_item)
                                ui_instance.add_message(message)
                                player_action_taken = True
                            elif selected_item.item_type == 'CONSUMABLE':
                                # InventorySystem에 아이템 사용 요청
                                message = inventory_system.use_item(player_entity_id, selected_item.id)
                                ui_instance.add_message(message)
                                player_action_taken = True
                                if player.inventory.get_item_quantity(selected_item.id) <= 0:
                                    inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                            elif selected_item.item_type == 'SKILLBOOK':
                                # InventorySystem에 스킬북 사용 요청
                                message = inventory_system.acquire_skill_from_book(player_entity_id, selected_item)
                                ui_instance.add_message(message)
                                player_action_taken = True
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
                        message, dropped = inventory_system.drop_item(player_entity_id, selected_item.id)
                        ui_instance.add_message(message)
                        if dropped:
                            player_action_taken = True
                            inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                elif key in "1234567890": # 퀵슬롯 등록
                    slot_num = 10 if key == '0' else int(key)
                    items_in_tab = player.inventory.get_items_by_tab(inventory_active_tab)
                    if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                        selected_item_data = items_in_tab[inventory_cursor_pos]
                        selected_item = selected_item_data['item']

                        if 1 <= slot_num <= 5: # 아이템 퀵슬롯
                            message = inventory_system.assign_item_to_quickslot(player_entity_id, selected_item.id, slot_num)
                            ui_instance.add_message(message)
                        elif 6 <= slot_num <= 10: # 스킬 퀵슬롯
                            message = inventory_system.assign_skill_to_quickslot(player_entity_id, selected_item.id, slot_num)
                            ui_instance.add_message(message)
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
                        entity_manager.add_component(player_entity_id, MoveRequestComponent(entity_id=player_entity_id, dx=dx, dy=dy))
                        player_action_taken = True
                    
                    elif key in "1234567890":
                        slot_num = 10 if key == '0' else int(key)
                        
                        # 아이템 퀵슬롯 처리 (1-5)
                        if 1 <= slot_num <= 5:
                            item_id = player.item_quick_slots.get(slot_num)
                            if not item_id:
                                ui_instance.add_message(f"퀵슬롯 {slot_num}번이 비어있습니다.")
                            else:
                                message, used = inventory_system.use_item(player_entity_id, item_id)
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
                        message, looted = inventory_system.loot_items(player_entity_id, dungeon_map)
                        ui_instance.add_message(message)
                        if looted:
                            player_action_taken = True

                    elif key == 'q':
                        running = False
                        ui_instance.add_message("게임을 저장하고 메인 메뉴로 돌아갑니다.")

        if player_action_taken:
            turn_count += 1
            movement_system.update() # 모든 이동 요청 처리
            collision_result = collision_system.update() # 충돌 처리 및 위치 업데이트
            interaction_system.update() # 상호작용 처리
            projectile_system.update() # 발사체 시스템 업데이트
            combat_system.update() # 전투 시스템 업데이트

            player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
            dungeon_map.reveal_tiles(player_pos.x, player_pos.y) # 시야 업데이트

            # 충돌 결과 처리
            if isinstance(collision_result, Monster):
                monster = collision_result
                ui_instance.add_message(f"{monster.name}과(와) 전투 시작!")
                # CombatSystem으로 전투 로직 이전
                player_attack_comp = entity_manager.get_component(player_entity_id, AttackComponent)
                if player_attack_comp:
                    entity_manager.add_component(monster.entity_id, DamageRequestComponent(target_id=monster.entity_id, amount=player_attack_comp.power, attacker_id=player_entity_id))

            elif isinstance(collision_result, Trap):
                trap_triggered = collision_result
                ui_instance.add_message(f"{player.name}이(가) {trap_triggered.name} 함정을 밟았습니다!")
                # TODO: 함정 효과 적용 (나중에 TrapSystem에서 처리)

            elif isinstance(collision_result, str):
                ui_instance.add_message(collision_result)

            # (기존 턴 종료 처리 로직)
            for monster in dungeon_map.monsters:
                if monster.dead: continue
                monster_pos = entity_manager.get_component(monster.entity_id, PositionComponent)
                if not monster_pos: continue

                if abs(player_pos.x - monster_pos.x) <= 1 and abs(player_pos.y - monster_pos.y) <= 1:
                    # CombatSystem으로 전투 로직 이전
                    entity_manager.add_component(player_entity_id, DamageRequestComponent(target_id=player_entity_id, amount=monster.attack, attacker_id=monster.entity_id))
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
                    rel_x = player_pos.x - monster_pos.x
                    rel_y = player_pos.y - monster_pos.y

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
                            monster_pos = entity_manager.get_component(monster.entity_id, PositionComponent)
                            if monster_pos:
                                # MovementSystem에서 충돌 처리 및 실제 이동을 담당
                                entity_manager.add_component(monster.entity_id, MoveRequestComponent(entity_id=monster.entity_id, dx=dx, dy=dy))
                                break # 이동 요청 성공 시 다음 몬스터로
                    
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
                            monster_pos = entity_manager.get_component(monster.entity_id, PositionComponent)
                            if monster_pos:
                                # MovementSystem에서 충돌 처리 및 실제 이동을 담당
                                entity_manager.add_component(monster.entity_id, MoveRequestComponent(entity_id=monster.entity_id, dx=dx, dy=dy))
                                break # 이동 요청 성공 시 다음 몬스터로
        
        
    sys.stdout.write(ANSI.SHOW_CURSOR)
    save_load_system.save_game(player, all_dungeon_maps, ui_instance)
    
    game_over_comp = entity_manager.get_component(player_entity_id, GameOverComponent)
    if game_over_comp:
        return "WIN" if game_over_comp.win else "DEATH"
    return "QUIT"
