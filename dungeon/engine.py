# /home/dogsinatas/python_project/dungeon/dungeon/engine.py (수정된 전체 코드)

import sys
import time
import math
import random
import re
import readchar
import logging

# 로깅 설정
logging.basicConfig(filename='game_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- 필요한 모듈 및 클래스 임포트 (기존 코드 기반) ---
from .map_manager import DungeonMap, EXIT_NORMAL, EXIT_LOCKED, ITEM_TILE, ROOM_ENTRANCE
from .renderer import UI, ANSI
from . import data_manager
from .items import Item
from .monster import Monster
from .player import Player # Player 클래스 임포트
from .entity import EntityManager
from .component import PositionComponent, MovableComponent, MoveRequestComponent, InteractableComponent, ProjectileComponent, DamageRequestComponent, HealthComponent, NameComponent, AttackComponent, DefenseComponent, DeathComponent, GameOverComponent, InventoryComponent, EquipmentComponent, QuickSlotComponent, RenderComponent, ManaComponent 
from .system import MovementSystem, CollisionSystem, InteractionSystem, ProjectileSystem, CombatSystem, DungeonGenerationSystem, DeathSystem, GameOverSystem, InventorySystem, SaveLoadSystem, RenderingSystem 
from .trap import Trap # Trap 클래스 임포트
# ----------------------------------------------------

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
    logging.debug("run_game 함수 시작")

    monster_definitions = data_manager.load_monster_definitions(ui_instance)
    entity_manager = EntityManager()
    dungeon_map = None 

    save_load_system = SaveLoadSystem(entity_manager)
    
    game_state_data = data_manager.load_game_data()
    
    player_obj, all_dungeon_maps, current_dungeon_level = save_load_system.load_game(game_state_data, ui_instance)
    
    if current_dungeon_level is None:
        current_dungeon_level = (1, 0) # 기본값 설정

    if player_obj:
        player_entity_id = player_obj.entity_id
        logging.debug("기존 플레이어 로드됨: entity_id=%s", player_entity_id)
    else:
        # 새 게임이거나 저장된 게임이 없는 경우, 플레이어 엔티티 생성
        player_entity_id = entity_manager.create_entity()
        player_obj = Player("용사", hp=100, mp=50) # Player 객체 생성 및 엔티티 ID 할당 (기본값 사용)
        entity_manager.add_component(player_entity_id, PositionComponent(x=0, y=0, map_id=(1,0))) # 초기 위치 설정
        entity_manager.add_component(player_entity_id, MovableComponent())
        entity_manager.add_component(player_entity_id, HealthComponent(max_hp=100, current_hp=100))
        entity_manager.add_component(player_entity_id, NameComponent(name="용사"))
        entity_manager.add_component(player_entity_id, AttackComponent(power=10, critical_chance=0.05, critical_damage_multiplier=1.5))
        entity_manager.add_component(player_entity_id, DefenseComponent(value=3))
        entity_manager.add_component(player_entity_id, ManaComponent(max_mp=player_obj.max_mp, current_mp=player_obj.mp))
        entity_manager.add_component(player_entity_id, InventoryComponent())
        entity_manager.add_component(player_entity_id, EquipmentComponent())
        entity_manager.add_component(player_entity_id, QuickSlotComponent())
        entity_manager.add_component(player_entity_id, RenderComponent(symbol=player_obj.char, color='white'))
        logging.debug("새 플레이어 생성됨: entity_id=%s", player_entity_id)

    # 나머지 시스템 초기화
    movement_system = MovementSystem(entity_manager, dungeon_map)
    collision_system = CollisionSystem(entity_manager, dungeon_map)
    interaction_system = InteractionSystem(entity_manager, dungeon_map, player_entity_id, ui_instance)
    projectile_system = ProjectileSystem(entity_manager, dungeon_map, ui_instance)
    combat_system = CombatSystem(entity_manager, ui_instance, dungeon_map)
    dungeon_generation_system = DungeonGenerationSystem(entity_manager, dungeon_map, ui_instance, item_definitions, monster_definitions)
    death_system = DeathSystem(entity_manager, dungeon_map, ui_instance, player_entity_id)
    game_over_system = GameOverSystem(entity_manager, dungeon_map, ui_instance, player_entity_id)
    rendering_system = RenderingSystem(entity_manager, dungeon_map, ui_instance, player_entity_id)
    inventory_system = InventorySystem(entity_manager, ui_instance, item_definitions) 

    def get_or_create_map(level_tuple, all_maps, ui, items_def, monster_defs, is_boss_room=False):
        # level_tuple은 항상 (int, int) 형태의 튜플이어야 함.
        if level_tuple in all_maps:
            d_map = all_maps[level_tuple]
            d_map.ui_instance = ui
            d_map.entity_manager = entity_manager 
            
            # --- 몬스터 리젠 로직 (ECS 방식) ---
            entities_to_remove = []
            for entity_id, pos_comp in list(entity_manager.get_components_of_type(PositionComponent).items()):
                # 플레이어 엔티티 제외 및 현재 맵의 엔티티만 타겟팅
                if entity_id != player_entity_id and pos_comp.map_id == level_tuple and entity_manager.has_component(entity_id, NameComponent):
                    name_comp = entity_manager.get_component(entity_id, NameComponent)
                    # 몬스터로 추정되는 엔티티 제거 (아이템, 함정 등은 제외)
                    if name_comp.name not in ["Player", "Trap", "Item"]: 
                        entities_to_remove.append(entity_id)
            
            for entity_id in entities_to_remove:
                entity_manager.remove_entity(entity_id)

            # DungeonGenerationSystem을 사용하여 엔티티 생성 (재생성)
            dungeon_generation_system.dungeon_map = d_map 
            dungeon_generation_system.generate_dungeon_entities(level_tuple, is_boss_room=is_boss_room)

            return d_map
        else:
            # 새 맵 생성
            d_map = DungeonMap(level_tuple, ui, is_boss_room=is_boss_room, monster_definitions=monster_defs, entity_manager=entity_manager)
            # DungeonGenerationSystem을 사용하여 엔티티 생성
            dungeon_generation_system.dungeon_map = d_map 
            dungeon_generation_system.generate_dungeon_entities(level_tuple, is_boss_room=is_boss_room)

            all_maps[level_tuple] = d_map
            return d_map

    camera = {'x': 0, 'y': 0}
    last_entrance_position = {}
    
    inventory_open = False
    inventory_cursor_pos = 0
    inventory_active_tab = 'item'
    inventory_scroll_offset = 0

    log_viewer_open = False
    log_viewer_scroll_offset = 0
    
    # --- [수정] current_dungeon_level의 타입을 체크하여 (int, int) 튜플로 변환 ---
    map_level_tuple = (1, 0) # 기본값 (1층, 메인 룸)
    
    if current_dungeon_level is not None:
        if isinstance(current_dungeon_level, dict):
            floor_str = current_dungeon_level.get('floor') or current_dungeon_level.get('level_id') or "1F"
            room_index = current_dungeon_level.get('room_index', 0)
            match = re.search(r'(\d+)', str(floor_str))
            floor = int(match.group(1)) if match else 1
            map_level_tuple = (floor, room_index)
        elif isinstance(current_dungeon_level, str):
            match = re.search(r'(\d+)', current_dungeon_level)
            floor = int(match.group(1)) if match else 1
            map_level_tuple = (floor, 0)
        elif isinstance(current_dungeon_level, tuple) and len(current_dungeon_level) == 2:
            floor_val = current_dungeon_level[0]
            room_index_val = current_dungeon_level[1]
            if isinstance(floor_val, str):
                match = re.search(r'(\d+)', floor_val)
                floor = int(match.group(1)) if match else 1
            else:
                floor = int(floor_val) if isinstance(floor_val, (int, float)) else 1
            room_index = int(room_index_val) if isinstance(room_index_val, (int, float)) else 0
            map_level_tuple = (floor, room_index)
        else:
            ui_instance.add_message("경고: 로드된 맵 레벨 정보가 유효하지 않아 기본값(1, 0)을 사용합니다.")
    
    current_dungeon_level = map_level_tuple # 이제 current_dungeon_level은 항상 (int, int) 튜플
    # ---------------------------------------------------------------------------------------

    dungeon_map = get_or_create_map(current_dungeon_level, all_dungeon_maps, ui_instance, item_definitions, monster_definitions)
    
    # 모든 시스템에 현재 맵 전달
    movement_system.dungeon_map = dungeon_map
    collision_system.dungeon_map = dungeon_map
    interaction_system.dungeon_map = dungeon_map
    projectile_system.dungeon_map = dungeon_map
    combat_system.dungeon_map = dungeon_map
    dungeon_generation_system.dungeon_map = dungeon_map
    death_system.dungeon_map = dungeon_map
    game_over_system.dungeon_map = dungeon_map

    player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
    # player_x, player_y는 이제 dungeon_map.start_x, dungeon_map.start_y를 사용함
    if not player_pos:
         player_pos = PositionComponent(x=dungeon_map.start_x, y=dungeon_map.start_y, map_id=current_dungeon_level)
         entity_manager.add_component(player_entity_id, player_pos)
    else:
         player_pos.x, player_pos.y = dungeon_map.start_x, dungeon_map.start_y
         player_pos.map_id = current_dungeon_level 

    ui_instance.clear_screen()

    turn_count = 0
    rest_turn_count = 0

    game_state = 'NORMAL'
    aiming_skill = None
    
    # ECS 전환 후 컴포넌트 기반으로 수정된 use_projectile_skill 함수
    def use_projectile_skill(player_entity_id, dungeon, skill):
        player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
        if not player_pos: return False

        # HealthComponent를 가진 엔티티 (몬스터)를 찾음
        visible_monsters = []
        for entity_id, health_comp in entity_manager.get_components_of_type(HealthComponent).items():
            if entity_id != player_entity_id:
                 pos_comp = entity_manager.get_component(entity_id, PositionComponent)
                 # 맵 ID는 튜플로 비교
                 if pos_comp and pos_comp.map_id == dungeon.dungeon_level_tuple and (pos_comp.x, pos_comp.y) in dungeon.visited:
                    visible_monsters.append((entity_id, pos_comp))

        if not visible_monsters:
            ui_instance.add_message("주변에 보이는 몬스터가 없습니다.")
            return False

        # 가장 가까운 몬스터 엔티티 ID와 위치 컴포넌트 찾기
        closest_monster_data = min(visible_monsters, key=lambda m_data: math.sqrt((player_pos.x - m_data[1].x)**2 + (player_pos.y - m_data[1].y)**2))
        closest_monster_entity_id, closest_monster_pos = closest_monster_data
        
        distance = math.sqrt((player_pos.x - closest_monster_pos.x)**2 + (player_pos.y - closest_monster_pos.y)**2)
        if distance > skill.range_str:
            ui_instance.add_message(f"'{skill.name}' 스킬의 사거리가 닿지 않습니다. (사거리: {skill.range_str})")
            return False

        # 발사체 엔티티 생성
        projectile_entity_id = entity_manager.create_entity()
        entity_manager.add_component(projectile_entity_id, PositionComponent(x=player_pos.x, y=player_pos.y, map_id=player_pos.map_id))
        
        # 발사체 방향 계산
        dx, dy = 0, 0
        if closest_monster_pos.x > player_pos.x: dx = 1
        elif closest_monster_pos.x < player_pos.x: dx = -1
        if closest_monster_pos.y > player_pos.y: dy = 1
        elif closest_monster_pos.y < player_pos.y: dy = -1

        entity_manager.add_component(projectile_entity_id, ProjectileComponent(
            damage=skill.damage, 
            range=skill.range_str, 
            current_range=skill.range_str, 
            shooter_id=player_entity_id,
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
        
        # 플레이어 위치를 기반으로 카메라 설정
        if player_pos:
            camera['x'] = max(0, min(player_pos.x - map_viewport_width // 2, dungeon_map.width - map_viewport_width))
            camera['y'] = max(0, min(player_pos.y - map_viewport_height // 2, dungeon_map.height - map_viewport_height))
        else:
             running = False
             continue

        if game_state != 'ANIMATING':
            rendering_system.update(camera['x'], camera['y'],
                                    inventory_open, inventory_cursor_pos,
                                    inventory_active_tab, inventory_scroll_offset,
                                    log_viewer_open, log_viewer_scroll_offset)

        if entity_manager.has_component(player_entity_id, GameOverComponent):
            game_over_comp = entity_manager.get_component(player_entity_id, GameOverComponent)
            if not game_over_comp.win: 
                readchar.readkey()
            running = False
            continue

        player_action_taken = False
        
        key = readchar.readkey()
        
        current_floor, current_room_index = current_dungeon_level # 이제 안전하게 언패킹 가능
            
        inventory_comp = entity_manager.get_component(player_entity_id, InventoryComponent)
        quickslot_comp = entity_manager.get_component(player_entity_id, QuickSlotComponent)
        health_comp = entity_manager.get_component(player_entity_id, HealthComponent)
        mana_comp = entity_manager.get_component(player_entity_id, ManaComponent)

        if game_state == 'AIMING_SKILL':
            pass 
        
        elif log_viewer_open:
            if key == readchar.key.UP: log_viewer_scroll_offset += 1
            elif key == readchar.key.DOWN: log_viewer_scroll_offset = max(0, log_viewer_scroll_offset - 1)
            elif key == 'm': log_viewer_open = False

        elif inventory_open:
            if not inventory_comp: continue

            if key == 'i' or key == 'I': 
                inventory_open = False
            elif key == readchar.key.UP:
                items_in_tab = inventory_comp.get_items_by_tab(inventory_active_tab)
                if items_in_tab:
                    inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                    if inventory_cursor_pos < inventory_scroll_offset:
                        inventory_scroll_offset = inventory_cursor_pos
            elif key == readchar.key.DOWN:
                items_in_tab = inventory_comp.get_items_by_tab(inventory_active_tab)
                if items_in_tab:
                    inventory_cursor_pos = min(len(items_in_tab) - 1, inventory_cursor_pos + 1)
                    list_height = ui_instance.MAP_VIEWPORT_HEIGHT - 6
                    if inventory_cursor_pos >= inventory_scroll_offset + list_height: 
                        inventory_scroll_offset += 1
            elif key == 'a': inventory_active_tab = 'item'
            elif key == 'b': inventory_active_tab = 'equipment'
            elif key == 'c': inventory_active_tab = 'scroll'
            elif key == 'd': inventory_active_tab = 'skill_book'
            elif key == 'z': inventory_active_tab = 'all'
            elif key == 'e': 
                items_in_tab = inventory_comp.get_items_by_tab(inventory_active_tab)
                if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                    selected_item_data = items_in_tab[inventory_cursor_pos]
                    selected_item = selected_item_data['item']

                    if isinstance(selected_item, Item):
                        if selected_item.item_type == 'EQUIP':
                            message = inventory_system.equip_unequip_item(player_entity_id, selected_item)
                            ui_instance.add_message(message)
                            player_action_taken = True
                        elif selected_item.item_type == 'CONSUMABLE':
                            message, used = inventory_system.use_item(player_entity_id, selected_item.id)
                            ui_instance.add_message(message)
                            if used:
                                player_action_taken = True
                            if inventory_comp.get_item_quantity(selected_item.id) <= 0:
                                inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                        elif selected_item.item_type == 'SKILLBOOK':
                            message, acquired = inventory_system.acquire_skill_from_book(player_entity_id, selected_item)
                            ui_instance.add_message(message)
                            if acquired:
                                player_action_taken = True
                            if inventory_comp.get_item_quantity(selected_item.id) <= 0:
                                inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
                        else:
                            ui_instance.add_message("이 아이템은 장착하거나 사용할 수 없습니다.")
                    else:
                        ui_instance.add_message("선택된 항목이 아이템이 아닙니다.")
            elif key == 'R': 
                items_in_tab = inventory_comp.get_items_by_tab(inventory_active_tab)
                if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                    selected_item_data = items_in_tab[inventory_cursor_pos]
                    selected_item = selected_item_data['item']
                    message, dropped = inventory_system.drop_item(player_entity_id, selected_item.id)
                    ui_instance.add_message(message)
                    if dropped:
                        player_action_taken = True
                        inventory_cursor_pos = max(0, inventory_cursor_pos - 1)
            elif key in "1234567890": 
                if not quickslot_comp: continue
                slot_num = 10 if key == '0' else int(key)
                items_in_tab = inventory_comp.get_items_by_tab(inventory_active_tab)
                if items_in_tab and 0 <= inventory_cursor_pos < len(items_in_tab):
                    selected_item_data = items_in_tab[inventory_cursor_pos]
                    selected_item = selected_item_data['item']

                    if 1 <= slot_num <= 5: 
                        message = inventory_system.assign_item_to_quickslot(player_entity_id, selected_item.id, slot_num)
                        ui_instance.add_message(message)
                    elif 6 <= slot_num <= 10: 
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
                    if not quickslot_comp or not mana_comp: continue

                    slot_num = 10 if key == '0' else int(key)
                    
                    # 아이템 퀵슬롯 처리 (1-5)
                    if 1 <= slot_num <= 5:
                        item_id = quickslot_comp.item_slots.get(slot_num)
                        if not item_id:
                            ui_instance.add_message(f"퀵슬롯 {slot_num}번이 비어있습니다.")
                        else:
                            message, used = inventory_system.use_item(player_entity_id, item_id)
                            ui_instance.add_message(message)
                            if used:
                                player_action_taken = True
                                
                    # 스킬 퀵슬롯 처리 (6-0)
                    elif 6 <= slot_num <= 10:
                        skill_id = quickslot_comp.skill_slots.get(slot_num)
                        if not skill_id:
                            ui_instance.add_message(f"퀵슬롯 {0 if slot_num == 10 else slot_num}번이 비어있습니다.")
                        else:
                            skill_def = data_manager.get_skill_definition(skill_id)
                            if not skill_def:
                                ui_instance.add_message("알 수 없는 스킬입니다.")
                            elif mana_comp.current_mp < skill_def.cost_value:
                                ui_instance.add_message(f"MP가 부족하여 '{skill_def.name}'을(를) 사용할 수 없습니다.")
                            else:
                                mana_comp.current_mp -= skill_def.cost_value
                                ui_instance.add_message(f"'{skill_def.name}'을(를) 시전합니다!")
                                
                                if skill_def.skill_subtype == 'PROJECTILE':
                                    if use_projectile_skill(player_entity_id, dungeon_map, skill_def):
                                        pass
                                    else:
                                        mana_comp.current_mp += skill_def.cost_value
                                        player_action_taken = False 
                                else:
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
            
            # --- 시스템 업데이트 순서 (최적화) ---
            movement_system.update() 
            collision_result = collision_system.update() 
            interaction_system.update() 
            projectile_system.update() 
            combat_system.update() 
            death_system.update() 
            game_over_system.update() 
            # ------------------------------------

            # 시야 업데이트
            player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
            if player_pos:
                dungeon_map.reveal_tiles(player_pos.x, player_pos.y) 

            # 충돌 결과 처리
            if isinstance(collision_result, int): 
                monster_entity_id = collision_result
                
                player_attack_comp = entity_manager.get_component(player_entity_id, AttackComponent)
                if player_attack_comp:
                    entity_manager.add_component(monster_entity_id, DamageRequestComponent(target_id=monster_entity_id, amount=player_attack_comp.power, attacker_id=player_entity_id))

            elif isinstance(collision_result, Trap):
                trap_triggered = collision_result
                player_name_comp = entity_manager.get_component(player_entity_id, NameComponent)
                player_name = player_name_comp.name if player_name_comp else "플레이어"
                ui_instance.add_message(f"{player_name}이(가) {trap_triggered.name} 함정을 밟았습니다!")

            elif isinstance(collision_result, str):
                ui_instance.add_message(collision_result)

            # (몬스터 턴 처리)
            for entity_id, health_comp in entity_manager.get_components_of_type(HealthComponent).items():
                if entity_id == player_entity_id: continue 
                
                name_comp = entity_manager.get_component(entity_id, NameComponent)
                if not name_comp or name_comp.name in ["Item", "Trap"]: continue 

                monster_pos = entity_manager.get_component(entity_id, PositionComponent)
                monster_attack_comp = entity_manager.get_component(entity_id, AttackComponent)
                
                if not monster_pos or not monster_attack_comp or monster_pos.map_id != current_dungeon_level: continue
                if health_comp.current_hp <= 0: continue 

                player_pos = entity_manager.get_component(player_entity_id, PositionComponent)
                if not player_pos: continue

                # 공격 범위 체크 (1칸 이내)
                if abs(player_pos.x - monster_pos.x) <= 1 and abs(player_pos.y - monster_pos.y) <= 1:
                    entity_manager.add_component(player_entity_id, DamageRequestComponent(target_id=player_entity_id, amount=monster_attack_comp.power, attacker_id=entity_id))
                else:
                    # 몬스터 이동 AI (기존 로직 유지)
                    monster_data = data_manager.get_monster_definition_by_name(name_comp.name)
                    if not monster_data: continue
                    current_move_type = monster_data.move_type 

                    if current_move_type == 'STATIONARY':
                        continue 
                        
                    rel_x = player_pos.x - monster_pos.x
                    rel_y = player_pos.y - monster_pos.y

                    target_dx, target_dy = 0, 0
                    if current_move_type == 'AGGRESSIVE':
                        if rel_x > 0: target_dx = 1
                        elif rel_x < 0: target_dx = -1
                        if rel_y > 0: target_dy = 1
                        elif rel_y < 0: target_dy = -1
                    elif current_move_type == 'COWARDLY':
                        if rel_x > 0: target_dx = -1
                        elif rel_x < 0: target_dx = 1
                        if rel_y > 0: target_dy = -1
                        elif rel_y < 0: target_dy = 1

                    all_directions = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]
                    random.shuffle(all_directions) 

                    preferred_directions = []
                    
                    if current_move_type == 'AGGRESSIVE':
                        for adx, ady in all_directions:
                            if (adx == 0 or (adx > 0 and rel_x > 0) or (adx < 0 and rel_x < 0)) and \
                               (ady == 0 or (ady > 0 and rel_y > 0) or (ady < 0 and rel_y < 0)):
                                preferred_directions.append((adx, ady))
                    elif current_move_type == 'COWARDLY':
                        for adx, ady in all_directions:
                            if (adx == 0 or (adx > 0 and rel_x < 0) or (adx < 0 and rel_x > 0)) and \
                               (ady == 0 or (ady > 0 and rel_y < 0) or (ady < 0 and rel_y > 0)):
                                preferred_directions.append((adx, ady))

                    if not preferred_directions:
                        preferred_directions = all_directions

                    for dx, dy in preferred_directions:
                        monster_pos = entity_manager.get_component(entity_id, PositionComponent)
                        if monster_pos:
                            entity_manager.add_component(entity_id, MoveRequestComponent(entity_id=entity_id, dx=dx, dy=dy))
                            break 
        
    sys.stdout.write(ANSI.SHOW_CURSOR)
    save_load_system.save_game(player_entity_id, current_dungeon_level, all_dungeon_maps, ui_instance) 
    
    game_over_comp = entity_manager.get_component(player_entity_id, GameOverComponent)
    if game_over_comp:
        return "WIN" if game_over_comp.win else "DEATH"
    return "QUIT"
