# system.py
from .entity import EntityManager
from .component import *
from .map_manager import DungeonMap
from .player import Player # Player 클래스 임포트
from .monster import Monster # Monster 클래스 임포트
from . import data_manager # data_manager 임포트
from .items import Item # Item 클래스 임포트
import random # random 임포트

class MovementSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map

    def update(self):
        # 모든 MoveRequestComponent를 처리합니다.
        for entity_id, move_request in list(self.entity_manager.get_components_of_type(MoveRequestComponent).items()):
            position = self.entity_manager.get_component(entity_id, PositionComponent)
            if position and self.entity_manager.has_component(entity_id, MovableComponent):
                new_x, new_y = position.x + move_request.dx, position.y + move_request.dy

                # DesiredPositionComponent 추가 (이동 요청을 목표 위치 데이터로 변환)
                self.entity_manager.add_component(entity_id, DesiredPositionComponent(
                    x=new_x, 
                    y=new_y, 
                    original_x=position.x, 
                    original_y=position.y
                ))
                
            # MoveRequestComponent는 일회성 이벤트이므로 처리 후 제거합니다.
            self.entity_manager.remove_component(entity_id, MoveRequestComponent)

class CollisionSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map

    def update(self):
        for entity_id, desired_pos in list(self.entity_manager.get_components_of_type(DesiredPositionComponent).items()):
            current_pos = self.entity_manager.get_component(entity_id, PositionComponent)
            if not current_pos: # 현재 위치 컴포넌트가 없으면 처리 불가
                self.entity_manager.remove_component(entity_id, DesiredPositionComponent)
                continue

            new_x, new_y = desired_pos.x, desired_pos.y
            original_x, original_y = desired_pos.original_x, desired_pos.original_y

            can_move = True
            collision_result = None # 충돌 결과 (몬스터, 아이템, 함정 등)

            # 1. 맵 경계 및 벽 충돌 검사
            if not self.dungeon_map.is_valid_tile(new_x, new_y) or self.dungeon_map.is_wall(new_x, new_y):
                can_move = False
                collision_result = "벽으로 막혀있습니다."
            
            # 2. 몬스터 충돌 검사 (플레이어와 몬스터 모두)
            if can_move:
                target_monster = self.dungeon_map.get_monster_at(new_x, new_y)
                if target_monster:
                    can_move = False
                    collision_result = target_monster # 몬스터 객체 반환

            # 3. 다른 엔티티 (플레이어 또는 몬스터) 충돌 검사 (MovementSystem에서 처리하지 않았으므로 여기서 다시 확인)
            # 현재는 몬스터만 고려, 플레이어는 별도 처리
            # for other_entity_id, other_pos in self.entity_manager.get_components_of_type(PositionComponent).items():
            #     if other_entity_id != entity_id and other_pos.x == new_x and other_pos.y == new_y:
            #         can_move = False
            #         collision_result = "다른 엔티티와 충돌했습니다."
            #         break

            # 4. 함정 충돌 검사
            if can_move: # 몬스터나 벽에 막히지 않았을 경우에만 함정 검사
                for trap in self.dungeon_map.traps:
                    if not trap.triggered and trap.x == new_x and trap.y == new_y:
                        trap.trigger()
                        collision_result = trap # 함정 객체 반환
                        break

            if can_move:
                current_pos.x = new_x
                current_pos.y = new_y
                self.dungeon_map.reveal_tiles(current_pos.x, current_pos.y)

                # 이동 후 타일 상호작용을 위해 InteractionSystem에 전달할 정보 저장
                # (나중에 InteractionSystem에서 처리)
                # self.entity_manager.add_component(entity_id, InteractionRequestComponent(entity_id, new_x, new_y))

            # DesiredPositionComponent는 처리 후 제거합니다.
            self.entity_manager.remove_component(entity_id, DesiredPositionComponent)

            return collision_result # 충돌 결과를 반환하여 engine에서 처리할 수 있도록 함

class InteractionSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, player_entity_id: int, ui_instance):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.player_entity_id = player_entity_id
        self.ui_instance = ui_instance

    def update(self):
        player_pos = self.entity_manager.get_component(self.player_entity_id, PositionComponent)
        if not player_pos: return

        # 플레이어의 현재 위치에 있는 상호작용 가능한 엔티티를 찾습니다.
        for entity_id, interactable_comp in list(self.entity_manager.get_components_of_type(InteractableComponent).items()):
            entity_pos = self.entity_manager.get_component(entity_id, PositionComponent)
            if entity_pos and entity_pos.x == player_pos.x and entity_pos.y == player_pos.y:
                # 상호작용 수행
                if interactable_comp.interaction_type == 'ITEM_TILE':
                    # 아이템 루팅 로직 (engine.py에서 가져옴)
                    looted_something = False
                    if (player_pos.x, player_pos.y) in self.dungeon_map.items_on_map:
                        item_data_on_map = self.dungeon_map.items_on_map[(player_pos.x, player_pos.y)]
                        item_id_on_map = item_data_on_map['id']
                        item_qty_on_map = item_data_on_map['qty']
                        item_def_on_map = data_manager.get_item_definition(item_id_on_map)

                        if item_def_on_map:
                            looted_item_on_map = Item(item_def_on_map.id, item_def_on_map.name, item_def_on_map.item_type, 
                                                      item_def_on_map.equip_slot, item_def_on_map.effect_type, 
                                                      item_def_on_map.value, item_def_on_map.description, item_def_on_map.req_level)
                            
                            inventory_system = self.entity_manager.get_component(self.player_entity_id, InventorySystem) # InventorySystem 인스턴스 가져오기
                            if inventory_system and inventory_system.add_item(self.player_entity_id, looted_item_on_map, item_qty_on_map):
                                self.ui_instance.add_message(f"{looted_item_on_map.name} {item_qty_on_map}개를 획득했습니다.")
                                del self.dungeon_map.items_on_map[(player_pos.x, player_pos.y)] # 맵에서 아이템 제거
                                looted_something = True
                            else:
                                self.ui_instance.add_message(f"{looted_item_on_map.name}을(를) 획득할 수 없습니다.")
                        else:
                            self.ui_instance.add_message("맵에 있는 알 수 없는 아이템입니다.")
                    if not looted_something:
                        self.ui_instance.add_message("이동한 타일에 루팅할 아이템이 없습니다.")

                elif interactable_comp.interaction_type == 'ROOM_ENTRANCE':
                    # 방 이동 로직 (engine.py에서 가져옴)
                    current_floor, current_room_index = self.dungeon_map.floor, self.dungeon_map.room_index
                    room_info = self.dungeon_map.room_entrances.get((player_pos.x, player_pos.y))
                    if room_info:
                        next_room_index = room_info['id']
                        is_boss_room = room_info['is_boss']
                        # last_entrance_position[current_dungeon_level] = (player.x, player.y) # 현재 맵의 입구 위치 저장
                        # TODO: 이 부분은 engine에서 처리해야 함 (맵 변경)
                        self.ui_instance.add_message(f"{current_floor}층 {next_room_index}번 방으로 이동했습니다. (실제 이동은 engine에서)")
                    else:
                        self.ui_instance.add_message("알 수 없는 방 입구입니다.")

                # 상호작용 처리 후 InteractableComponent 제거 (일회성 상호작용의 경우)
                # self.entity_manager.remove_component(entity_id, InteractableComponent)

class ProjectileSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance

    def update(self):
        for entity_id, proj_comp in list(self.entity_manager.get_components_of_type(ProjectileComponent).items()):
            pos_comp = self.entity_manager.get_component(entity_id, PositionComponent)
            if not pos_comp: continue

            # 1. 발사체 이동
            new_x, new_y = pos_comp.x + proj_comp.dx, pos_comp.y + proj_comp.dy
            proj_comp.current_range -= 1

            # 2. 맵 경계 또는 벽 충돌 검사
            if not self.dungeon_map.is_valid_tile(new_x, new_y) or self.dungeon_map.is_wall(new_x, new_y):
                self._handle_impact(entity_id, pos_comp.x, pos_comp.y, proj_comp) # 현재 위치에서 충돌 처리
                self.entity_manager.remove_entity(entity_id) # 발사체 파괴
                continue

            # 3. 몬스터 충돌 검사
            target_monster = self.dungeon_map.get_monster_at(new_x, new_y)
            if target_monster:
                self._handle_impact(entity_id, new_x, new_y, proj_comp, target_monster) # 몬스터 위치에서 충돌 처리
                self.entity_manager.remove_entity(entity_id) # 발사체 파괴
                continue

            # 4. 수명 종료 (사거리 0)
            if proj_comp.current_range <= 0:
                self._handle_impact(entity_id, new_x, new_y, proj_comp) # 사거리 끝에서 충돌 처리
                self.entity_manager.remove_entity(entity_id) # 발사체 파괴
                continue

            # 5. 이동 성공
            pos_comp.x, pos_comp.y = new_x, new_y

    def _handle_impact(self, projectile_entity_id, impact_x, impact_y, proj_comp: ProjectileComponent, target_monster=None):
        # TODO: 애니메이션 시스템에 충돌 이펙트 요청
        # self.ui_instance.add_message(f"발사체 충돌! ({impact_x}, {impact_y})")

        if target_monster:
            # 데미지 계산 및 적용
            skill_def = data_manager.get_skill_definition(proj_comp.skill_def_id)
            if skill_def:
                # 기본 데미지에 스킬 레벨에 따른 보너스를 추가할 수 있음 (예시)
                # TODO: shooter_id를 통해 플레이어 객체를 가져와 스킬 레벨 확인
                # 현재는 스킬 정의의 기본 데미지 사용
                base_damage = skill_def.damage
                # damage, is_critical = combat.calculate_damage(shooter_obj, target_monster, base_damage=base_damage)
                # 임시로 데미지 직접 적용
                # target_monster.take_damage(base_damage) # CombatSystem으로 이전
                self.entity_manager.add_component(target_monster.entity_id, DamageRequestComponent(
                    target_id=target_monster.entity_id, 
                    amount=base_damage, 
                    attacker_id=proj_comp.shooter_id, 
                    skill_id=proj_comp.skill_def_id
                ))
                self.ui_instance.add_message(f"'{skill_def.name}'(이)가 {target_monster.name}에게 적중! {base_damage} 데미지.")
                # if target_monster.dead: # CombatSystem에서 처리
                #     self.ui_instance.add_message(f"{target_monster.name}을(를) 물리쳤습니다!")
                #     # TODO: 아이템 드랍 및 경험치 획득 로직 (engine에서 가져와야 함)
                #     # 임시로 여기에 경험치 획득 로직 추가
                #     player_obj = self.entity_manager.get_component(proj_comp.shooter_id, Player)
                #     if player_obj:
                #         exp_gained = target_monster.exp_given + (target_monster.level * 2)
                #         self.ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                #         leveled_up, level_up_message = player_obj.gain_exp(exp_gained, self.entity_manager)
                #         if leveled_up: self.ui_instance.add_message(level_up_message)

        # TODO: 충돌 이펙트 렌더링 (renderer에서 처리)

class CombatSystem:
    def __init__(self, entity_manager: EntityManager, ui_instance, dungeon_map: DungeonMap):
        self.entity_manager = entity_manager
        self.ui_instance = ui_instance
        self.dungeon_map = dungeon_map # 아이템 드랍을 위해 dungeon_map 추가

    def update(self):
        for entity_id, damage_request in list(self.entity_manager.get_components_of_type(DamageRequestComponent).items()):
            target_health = self.entity_manager.get_component(damage_request.target_id, HealthComponent)
            target_defense = self.entity_manager.get_component(damage_request.target_id, DefenseComponent)
            target_name = self.entity_manager.get_component(damage_request.target_id, NameComponent)

            if not target_health or not target_health.is_alive: # 대상이 없거나 이미 죽었으면 처리 안 함
                self.entity_manager.remove_component(entity_id, DamageRequestComponent)
                continue

            attacker_attack = self.entity_manager.get_component(damage_request.attacker_id, AttackComponent)
            attacker_name = self.entity_manager.get_component(damage_request.attacker_id, NameComponent)

            # 데미지 계산 (기존 combat.py의 로직을 참고하여 구현)
            base_damage = damage_request.amount # ProjectileSystem에서 넘어온 데미지 또는 기본 공격력
            if attacker_attack: # 공격자 정보가 있으면 치명타 계산
                is_critical = False
                if random.random() < attacker_attack.critical_chance:
                    is_critical = True

                damage = base_damage - (target_defense.value if target_defense else 0)

                if is_critical:
                    damage = int(damage * attacker_attack.critical_damage_multiplier)
                
                final_damage = max(1, damage)
                self.ui_instance.add_message(f"{attacker_name.name}의 공격!" + (" 💥치명타!💥" if is_critical else ""))
            else: # 공격자 정보가 없으면 순수 데미지 적용 (예: 함정)
                final_damage = base_damage

            target_health.current_hp -= final_damage
            self.ui_instance.add_message(f"{target_name.name}이(가) {final_damage}의 데미지를 입었습니다. 남은 HP: {target_health.current_hp}")

            if target_health.current_hp <= 0:
                target_health.current_hp = 0
                target_health.is_alive = False
                self.ui_instance.add_message(f"{target_name.name}이(가) 쓰러졌습니다!")
                
                # 사망 처리는 DeathSystem에서 담당
            self.entity_manager.remove_component(entity_id, DamageRequestComponent)

class DeathSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self):
        for entity_id, health_comp in list(self.entity_manager.get_components_of_type(HealthComponent).items()):
            if not health_comp.is_alive and not self.entity_manager.has_component(entity_id, DeathComponent): # 죽었고 아직 DeathComponent가 없으면
                self.entity_manager.add_component(entity_id, DeathComponent()) # DeathComponent 추가
                
                # 몬스터 사망 처리
                if entity_id != self.player_entity_id: # 플레이어가 아닌 경우
                    # 몬스터 객체 찾기 (entity_id로)
                    killed_monster = None
                    for m in self.dungeon_map.monsters:
                        if m.entity_id == entity_id:
                            killed_monster = m
                            break
                    
                    if killed_monster:
                        # 경험치 획득 (공격자가 플레이어인 경우에만)
                        # TODO: DamageRequestComponent에서 공격자 ID를 가져와야 함
                        # 현재는 임시로 플레이어가 죽인 것으로 가정
                        player_obj = self.entity_manager.get_component(self.player_entity_id, Player) # Player 객체 가져오기
                        if player_obj:
                            exp_gained = killed_monster.exp_given + (killed_monster.level * 2)
                            self.ui_instance.add_message(f"{exp_gained}의 경험치를 획득했습니다!")
                            leveled_up, level_up_message = player_obj.gain_exp(exp_gained, self.entity_manager)
                            if leveled_up: self.ui_instance.add_message(level_up_message)

                        # 아이템 드랍
                        if data_manager._item_definitions and random.random() < 0.5:
                            dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                            # 몬스터가 죽은 위치에 아이템을 맵에 추가
                            target_pos = self.entity_manager.get_component(entity_id, PositionComponent)
                            if target_pos:
                                self.dungeon_map.items_on_map[(target_pos.x, target_pos.y)] = {'id': dropped_item_id, 'qty': 1}
                                item_def = data_manager.get_item_definition(dropped_item_id)
                                if item_def:
                                    self.ui_instance.add_message(f"{killed_monster.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다.")

                    # 엔티티 제거
                    self.entity_manager.remove_entity(entity_id)
                    # 몬스터 객체 목록에서도 제거
                    self.dungeon_map.monsters = [m for m in self.dungeon_map.monsters if m.entity_id != entity_id]

                else: # 플레이어 사망 처리
                    self.ui_instance.add_message("당신은 쓰러졌습니다...")
                    # TODO: 게임 오버 화면 전환 등 (engine에서 처리)

class GameOverSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self):
        # 1. 플레이어 사망 조건
        player_health = self.entity_manager.get_component(self.player_entity_id, HealthComponent)
        if player_health and not player_health.is_alive:
            if not self.entity_manager.has_component(self.player_entity_id, GameOverComponent):
                self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=False))
                self.ui_instance.add_message("게임 오버! 당신은 죽었습니다.")
                return # 게임 종료

        # 2. 승리 조건 (예: 보스 몬스터 사망 또는 최종 층 도달)
        # TODO: 보스 몬스터 엔티티 ID를 DungeonGenerationSystem에서 관리하도록 변경
        # 현재는 임시로 보스 몬스터가 없으면 승리하는 것으로 가정
        if self.dungeon_map.floor == 10 and not self.dungeon_map.monsters: # 10층에 몬스터가 없으면 승리 (임시)
            if not self.entity_manager.has_component(self.player_entity_id, GameOverComponent):
                self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=True))
                self.ui_instance.add_message("게임 승리! 던전을 탈출했습니다.")
                return # 게임 종료


class GameOverSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self):
        # 1. 플레이어 사망 조건
        player_health = self.entity_manager.get_component(self.player_entity_id, HealthComponent)
        if player_health and not player_health.is_alive:
            if not self.entity_manager.has_component(self.player_entity_id, GameOverComponent):
                self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=False))
                self.ui_instance.add_message("게임 오버! 당신은 죽었습니다.")
                return # 게임 종료

        # 2. 승리 조건 (예: 보스 몬스터 사망 또는 최종 층 도달)
        # TODO: 보스 몬스터 엔티티 ID를 DungeonGenerationSystem에서 관리하도록 변경
        # 현재는 임시로 보스 몬스터가 없으면 승리하는 것으로 가정
        if self.dungeon_map.floor == 10 and not self.dungeon_map.monsters: # 10층에 몬스터가 없으면 승리 (임시)
            if not self.entity_manager.has_component(self.player_entity_id, GameOverComponent):
                self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=True))
                self.ui_instance.add_message("게임 승리! 던전을 탈출했습니다.")
                return # 게임 종료


class RenderingSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self, camera_x: int, camera_y: int,
               inventory_open: bool, inventory_cursor_pos: int,
               inventory_active_tab: str, inventory_scroll_offset: int,
               log_viewer_open: bool, log_viewer_scroll_offset: int):
        
        player_obj = self.entity_manager.get_component(self.player_entity_id, Player) # Player 객체 가져오기
        if not player_obj: return

        monsters_to_render = []
        for entity_id, pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
            if entity_id != self.player_entity_id: # 플레이어는 별도로 처리
                # 해당 엔티티가 몬스터인지 확인 (예: Monster 객체에 entity_id가 저장되어 있다고 가정)
                for monster_obj in self.dungeon_map.monsters:
                    if monster_obj.entity_id == entity_id and not monster_obj.dead:
                        monsters_to_render.append(monster_obj)
                        break

        self.ui_instance.draw_game_screen(player_obj, self.dungeon_map, monsters_to_render, camera_x, camera_y,
                                         inventory_open, inventory_cursor_pos,
                                         inventory_active_tab, inventory_scroll_offset,
                                         log_viewer_open, log_viewer_scroll_offset)


class RenderingSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self, camera_x: int, camera_y: int,
               inventory_open: bool, inventory_cursor_pos: int,
               inventory_active_tab: str, inventory_scroll_offset: int,
               log_viewer_open: bool, log_viewer_scroll_offset: int):
        
        player_obj = self.entity_manager.get_component(self.player_entity_id, Player) # Player 객체 가져오기
        if not player_obj: return

        monsters_to_render = []
        for entity_id, pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
            if entity_id != self.player_entity_id: # 플레이어는 별도로 처리
                # 해당 엔티티가 몬스터인지 확인 (예: Monster 객체에 entity_id가 저장되어 있다고 가정)
                for monster_obj in self.dungeon_map.monsters:
                    if monster_obj.entity_id == entity_id and not monster_obj.dead:
                        monsters_to_render.append(monster_obj)
                        break

        self.ui_instance.draw_game_screen(player_obj, self.dungeon_map, monsters_to_render, camera_x, camera_y,
                                         inventory_open, inventory_cursor_pos,
                                         inventory_active_tab, inventory_scroll_offset,
                                         log_viewer_open, log_viewer_scroll_offset)


class InventorySystem:
    def __init__(self, entity_manager: EntityManager, ui_instance, item_definitions):
        self.entity_manager = entity_manager
        self.ui_instance = ui_instance
        self.item_definitions = item_definitions

    def add_item(self, entity_id: int, item_to_add: Item, qty: int = 1):
        inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
        if not inventory_comp: return False

        if item_to_add.id in inventory_comp.items:
            inventory_comp.items[item_to_add.id]['qty'] += qty
        else:
            inventory_comp.items[item_to_add.id] = {'item': item_to_add, 'qty': qty}
        return True

    def equip_unequip_item(self, entity_id: int, item_to_equip: Item):
        inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
        equipment_comp = self.entity_manager.get_component(entity_id, EquipmentComponent)
        if not inventory_comp or not equipment_comp: return ""

        if item_to_equip.item_type != 'EQUIP':
            return "장비 아이템만 장착/해제할 수 있습니다."

        # 이미 장착된 아이템인지 확인
        is_equipped = False
        for slot, equipped_item_id in equipment_comp.equipped_items.items():
            if equipped_item_id == item_to_equip.id:
                is_equipped = True
                break
        
        if is_equipped:
            # 장착 해제
            unequipped_slot = None
            for slot_name, eq_item_id in equipment_comp.equipped_items.items():
                if eq_item_id == item_to_equip.id:
                    unequipped_slot = slot_name
                    break
            if unequipped_slot:
                del equipment_comp.equipped_items[unequipped_slot]
                # TODO: 스탯 업데이트 로직 (나중에 별도 시스템으로 분리)
                return f"{item_to_equip.name}을(를) 해제했습니다."
            return "해당 부위에 장착한 아이템이 없습니다."
        else:
            # 장착
            if item_to_equip.equip_slot in equipment_comp.equipped_items:
                # 기존 장비 해제
                old_item_id = equipment_comp.equipped_items[item_to_equip.equip_slot]
                old_item_def = data_manager.get_item_definition(old_item_id)
                old_item = Item.from_definition(old_item_def) if old_item_def else None
                if old_item:
                    self.ui_instance.add_message(f"{old_item.name}을(를) 해제했습니다.")

            equipment_comp.equipped_items[item_to_equip.equip_slot] = item_to_equip.id
            # TODO: 스탯 업데이트 로직 (나중에 별도 시스템으로 분리)
            return f"{item_to_equip.name}을(를) 장착했습니다."

    def drop_item(self, entity_id: int, item_id: str, qty: int = 1):
        inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
        if not inventory_comp: return "아이템을 버리는 데 실패했습니다.", False

        if item_id not in inventory_comp.items or inventory_comp.items[item_id]['qty'] < qty:
            return "인벤토리에 해당 아이템이 충분하지 않습니다.", False

        inventory_comp.items[item_id]['qty'] -= qty
        if inventory_comp.items[item_id]['qty'] <= 0:
            del inventory_comp.items[item_id]
            # 퀵슬롯에서도 제거 (player 객체에 접근)
            player_obj = self.entity_manager.get_component(entity_id, Player)
            if player_obj:
                for slot, q_item_id in list(player_obj.item_quick_slots.items()):
                    if q_item_id == item_id:
                        player_obj.item_quick_slots[slot] = None
                for slot, q_skill_id in list(player_obj.skill_quick_slots.items()):
                    if q_skill_id == item_id: # 스킬북 ID와 스킬 ID가 같다고 가정
                        player_obj.skill_quick_slots[slot] = None

        item_def = data_manager.get_item_definition(item_id)
        item_name = item_def.name if item_def else "알 수 없는 아이템"
        return f"{item_name}을(를) 버렸습니다.", True

    def use_item(self, entity_id: int, item_id: str):
        inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
        health_comp = self.entity_manager.get_component(entity_id, HealthComponent)
        mana_comp = self.entity_manager.get_component(entity_id, ManaComponent)
        player_obj = self.entity_manager.get_component(entity_id, Player) # Player 객체 (스킬, 퀵슬롯 등)

        if not inventory_comp or not player_obj: return "", False

        item_data = inventory_comp.items.get(item_id)
        if not item_data or item_data['qty'] <= 0:
            return f"인벤토리에 {item_id}이(가) 없습니다.", False

        item = item_data['item']
        effect_applied = False
        message = ""

        if item.item_type == 'CONSUMABLE':
            if item.effect_type == 'HP_RECOVER' and health_comp:
                health_comp.current_hp = min(health_comp.current_hp + item.value, health_comp.max_hp)
                message = f"{item.name}을(를) 사용하여 HP를 {item.value}만큼 회복했습니다."
                effect_applied = True
            elif item.effect_type == 'MP_RECOVER' and mana_comp:
                mana_comp.current_mp = min(mana_comp.current_mp + item.value, mana_comp.max_mp)
                message = f"{item.name}을(를) 사용하여 MP를 {item.value}만큼 회복했습니다."
                effect_applied = True
            # TODO: STAMINA_RECOVER 등 다른 효과 추가
        elif item.item_type == 'SKILLBOOK':
            # 스킬북 사용 로직 (player.py에서 가져옴)
            skill_id = item.id
            if player_obj.level < item.req_level:
                message = f"레벨 {item.req_level}이 되지 않아 '{item.name}' 스킬북을 읽을 수 없습니다."
            elif skill_id in player_obj.skills:
                player_obj.skills[skill_id]['level'] += 1
                new_level = player_obj.skills[skill_id]['level']
                message = f"'{item.name}' 스킬의 레벨이 올랐습니다! (Lv.{new_level - 1} -> Lv.{new_level})"
            else:
                player_obj.skills[skill_id] = {'level': 1, 'exp': 0}
                message = f"새로운 스킬 '{item.name}'을(를) 배웠습니다!"
            effect_applied = True

        if effect_applied:
            item_data['qty'] -= 1
            if item_data['qty'] <= 0:
                del inventory_comp.items[item_id]
                # 퀵슬롯에서도 제거 (player 객체에 접근)
                for slot, q_item_id in list(player_obj.item_quick_slots.items()):
                    if q_item_id == item_id:
                        player_obj.item_quick_slots[slot] = None
                for slot, q_skill_id in list(player_obj.skill_quick_slots.items()):
                    if q_skill_id == item_id: # 스킬북 ID와 스킬 ID가 같다고 가정
                        player_obj.skill_quick_slots[slot] = None
            return message, True
        
        return f"{item.name}은(는) 아직 사용할 수 없습니다.", False

    def assign_item_to_quickslot(self, entity_id: int, item_id: str, slot: int):
        player_obj = self.entity_manager.get_component(entity_id, Player)
        inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
        if not player_obj or not inventory_comp: return "", False

        if not (1 <= slot <= 5):
            return "아이템 퀵슬롯은 1-5번만 가능합니다.", False
        
        item_data = inventory_comp.items.get(item_id)
        if not item_data: return "인벤토리에 해당 아이템이 없습니다.", False
        item = item_data['item']

        if item.item_type != 'CONSUMABLE' and item.item_type != 'SCROLL':
            return "소모품 또는 스크롤만 아이템 퀵슬롯에 등록할 수 있습니다.", False

        # 중복 등록 방지
        if item_id in player_obj.item_quick_slots.values():
            return "이미 다른 퀵슬롯에 등록된 아이템입니다.", False

        player_obj.item_quick_slots[slot] = item_id
        return f"퀵슬롯 {slot}번에 {item.name}을(를) 등록했습니다.", True

    def assign_skill_to_quickslot(self, entity_id: int, skill_id: str, slot: int):
        player_obj = self.entity_manager.get_component(entity_id, Player)
        if not player_obj: return "", False

        slot_key = slot if slot != 0 else 10 # 0번 키는 10번 인덱스로 처리
        if not (6 <= slot_key <= 10):
            return "스킬 퀵슬롯은 6-0번만 가능합니다.", False
        
        if skill_id not in player_obj.skills:
            return f"'{skill_id}' 스킬을 아직 배우지 않았습니다. 먼저 스킬북을 사용하세요.", False
            
        player_obj.skill_quick_slots[slot_key] = skill_id
        return f"퀵슬롯 {slot}번에 {skill_id}을(를) 등록했습니다.", True # TODO: 스킬 이름으로 변경

    def loot_items(self, entity_id: int, dungeon_map: DungeonMap):
        player_pos = self.entity_manager.get_component(entity_id, PositionComponent)
        if not player_pos: return "", False

        looted_something = False
        message = ""

        # 1. 몬스터 시체에서 아이템 루팅 시도
        monster_at_player_pos = None
        for m in dungeon_map.monsters:
            if m.dead and m.x == player_pos.x and m.y == player_pos.y:
                monster_at_player_pos = m
                break

        if monster_at_player_pos and monster_at_player_pos.loot:
            item_id_to_loot = monster_at_player_pos.loot
            item_def = data_manager.get_item_definition(item_id_to_loot)
            if item_def:
                looted_item = Item.from_definition(item_def)
                if self.add_item(entity_id, looted_item):
                    message += f"{looted_item.name}을(를) 획득했습니다.\n"
                    monster_at_player_pos.loot = None # 루팅 후 아이템 제거
                    looted_something = True
                else:
                    message += f"{looted_item.name}을(를) 획득할 수 없습니다.\n"
            else:
                message += "알 수 없는 아이템입니다.\n"
        
        # 2. 맵에 직접 떨어진 아이템 루팅 시도 (몬스터 루팅 후 또는 몬스터 루팅할 것이 없을 때)
        if (player_pos.x, player_pos.y) in dungeon_map.items_on_map:
            item_data_on_map = dungeon_map.items_on_map[(player_pos.x, player_pos.y)]
            item_id_on_map = item_data_on_map['id']
            item_qty_on_map = item_data_on_map['qty']
            item_def_on_map = data_manager.get_item_definition(item_id_on_map)

            if item_def_on_map:
                looted_item_on_map = Item(item_def_on_map.id, item_def_on_map.name, item_def_on_map.item_type, 
                                          item_def_on_map.equip_slot, item_def_on_map.effect_type, 
                                          item_def_on_map.value, item_def_on_map.description, item_def_on_map.req_level)
                
                if self.add_item(entity_id, looted_item_on_map, item_qty_on_map):
                    message += f"{looted_item_on_map.name} {item_qty_on_map}개를 획득했습니다.\n"
                    del dungeon_map.items_on_map[(player_pos.x, player_pos.y)] # 맵에서 아이템 제거
                    looted_something = True
                else:
                    message += f"{looted_item_on_map.name}을(를) 획득할 수 없습니다.\n"
            else:
                message += "맵에 있는 알 수 없는 아이템입니다.\n"

        if not looted_something:
            message = "주변에 루팅할 아이템이 없습니다."

        return message.strip(), looted_something

    def update(self):
        # ItemUseRequestComponent 처리
        for entity_id, use_request in list(self.entity_manager.get_components_of_type(ItemUseRequestComponent).items()):
            inventory_comp = self.entity_manager.get_component(entity_id, InventoryComponent)
            health_comp = self.entity_manager.get_component(entity_id, HealthComponent)
            mana_comp = self.entity_manager.get_component(entity_id, ManaComponent)
            player_obj = self.entity_manager.get_component(entity_id, Player) # Player 객체 (스킬, 퀵슬롯 등)

            if not inventory_comp or not player_obj: # Player 객체도 필요
                self.entity_manager.remove_component(entity_id, ItemUseRequestComponent)
                continue

            item_data = inventory_comp.items.get(use_request.item_id)
            if not item_data or item_data['qty'] <= 0:
                self.ui_instance.add_message(f"인벤토리에 {use_request.item_id}이(가) 없습니다.")
                self.entity_manager.remove_component(entity_id, ItemUseRequestComponent)
                continue

            item = item_data['item']
            effect_applied = False
            message = ""

            if item.item_type == 'CONSUMABLE':
                if item.effect_type == 'HP_RECOVER' and health_comp:
                    health_comp.current_hp = min(health_comp.current_hp + item.value, health_comp.max_hp)
                    message = f"{item.name}을(를) 사용하여 HP를 {item.value}만큼 회복했습니다."
                    effect_applied = True
                elif item.effect_type == 'MP_RECOVER' and mana_comp:
                    mana_comp.current_mp = min(mana_comp.current_mp + item.value, mana_comp.max_mp)
                    message = f"{item.name}을(를) 사용하여 MP를 {item.value}만큼 회복했습니다."
                    effect_applied = True
                # TODO: STAMINA_RECOVER 등 다른 효과 추가
            elif item.item_type == 'SKILLBOOK':
                # 스킬북 사용 로직 (player.py에서 가져옴)
                skill_id = item.id
                if player_obj.level < item.req_level:
                    message = f"레벨 {item.req_level}이 되지 않아 '{item.name}' 스킬북을 읽을 수 없습니다."
                elif skill_id in player_obj.skills:
                    player_obj.skills[skill_id]['level'] += 1
                    new_level = player_obj.skills[skill_id]['level']
                    message = f"'{item.name}' 스킬의 레벨이 올랐습니다! (Lv.{new_level - 1} -> Lv.{new_level})"
                else:
                    player_obj.skills[skill_id] = {'level': 1, 'exp': 0}
                    message = f"새로운 스킬 '{item.name}'을(를) 배웠습니다!"
                effect_applied = True

            if effect_applied:
                item_data['qty'] -= 1
                self.ui_instance.add_message(message)
                if item_data['qty'] <= 0:
                    del inventory_comp.items[use_request.item_id]
                    # 퀵슬롯에서도 제거 (player 객체에 접근)
                    for slot, q_item_id in list(player_obj.item_quick_slots.items()):
                        if q_item_id == use_request.item_id:
                            player_obj.item_quick_slots[slot] = None
                    for slot, q_skill_id in list(player_obj.skill_quick_slots.items()):
                        if q_skill_id == use_request.item_id: # 스킬북 ID와 스킬 ID가 같다고 가정
                            player_obj.skill_quick_slots[slot] = None
            else:
                self.ui_instance.add_message(f"{item.name}은(는) 아직 사용할 수 없습니다.")

            self.entity_manager.remove_component(entity_id, ItemUseRequestComponent)


class SaveLoadSystem:
    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def save_game(self, player_entity_id: int, all_dungeon_maps, ui_instance):
        # 모든 엔티티와 컴포넌트를 직렬화
        game_state_data = {
            "entities": {},
            "dungeon_maps": {str(level): d_map.to_dict() for level, d_map in all_dungeon_maps.items()}
        }

        for entity_id, components in self.entity_manager.entities.items():
            serialized_components = {}
            for comp_type, component in components.items():
                # dataclass를 딕셔너리로 변환 (필요에 따라 커스텀 직렬화 로직 추가)
                if hasattr(component, 'to_dict'): # 커스텀 to_dict가 있는 경우
                    serialized_components[comp_type.__name__] = component.to_dict()
                else:
                    serialized_components[comp_type.__name__] = component.__dict__
            game_state_data["entities"][entity_id] = serialized_components
        
        # Player 객체의 특정 속성 (인벤토리, 스킬, 퀵슬롯 등)은 Player 객체 자체에 남아있으므로 별도로 저장
        player_obj = self.entity_manager.get_component(player_entity_id, Player)
        if player_obj:
            game_state_data["player_specific_data"] = player_obj.to_dict()

        data_manager.save_game_data(player_entity_id, all_dungeon_maps, ui_instance, game_state_data) # game_state_data 전달

    def load_game(self, game_state_data, ui_instance):
        # entity_manager 초기화 (기존 엔티티 제거)
        self.entity_manager.entities.clear()
        self.entity_manager.next_entity_id = 0

        player_obj = None
        all_dungeon_maps = {}

        if game_state_data:
            # Player 객체 데이터 로드
            player_specific_data = game_state_data.get("player_specific_data")
            if player_specific_data:
                player_obj = Player.from_dict(player_specific_data)

            # 맵 데이터 로드
            dungeon_maps_data = game_state_data.get("dungeon_maps", {})
            for level_str, map_dict in dungeon_maps_data.items():
                floor, room_index = map(int, level_str.split(','))
                all_dungeon_maps[(floor, room_index)] = DungeonMap.from_dict(map_dict)

            # 엔티티 및 컴포넌트 로드
            entities_data = game_state_data.get("entities", {})
            for entity_id_str, components_data in entities_data.items():
                entity_id = int(entity_id_str)
                self.entity_manager.create_entity(entity_id) # 특정 ID로 엔티티 생성
                for comp_name, comp_data in components_data.items():
                    # 컴포넌트 타입 매핑 (예시)
                    comp_class = globals().get(comp_name) # 전역 스코프에서 컴포넌트 클래스 찾기
                    if comp_class:
                        # dataclass의 from_dict 또는 __init__을 사용하여 컴포넌트 객체 생성
                        if hasattr(comp_class, 'from_dict'):
                            component = comp_class.from_dict(comp_data)
                        else:
                            component = comp_class(**comp_data)
                        self.entity_manager.add_component(entity_id, component)

        return player_obj, all_dungeon_maps


class DungeonGenerationSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, item_definitions, monster_definitions):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.item_definitions = item_definitions
        self.monster_definitions = monster_definitions

    def generate_dungeon_entities(self, level, is_boss_room=False):
        # 기존 engine.py의 몬스터 생성 로직을 가져옴
        if level[1] > 0: # 방인 경우
            if not is_boss_room:
                placed_monster_data = self.dungeon_map.place_monsters(self.monster_definitions, num_monsters=random.randint(1, 3))
                self.dungeon_map.place_random_items(self.item_definitions, num_items=random.randint(0, 2))
            else:
                placed_monster_data = self.dungeon_map._populate_boss_room()
        else: # 메인 맵인 경우
            placed_monster_data = self.dungeon_map.place_monsters(self.monster_definitions)
            self.dungeon_map.place_random_items(self.item_definitions)
        
        # 몬스터 엔티티 생성 및 컴포넌트 추가
        for m_data in placed_monster_data:
            monster_obj = Monster(m_data['x'], m_data['y'], self.ui_instance, monster_id=m_data['monster_id'])
            monster_entity_id = self.entity_manager.create_entity()
            self.entity_manager.add_component(monster_entity_id, PositionComponent(x=monster_obj.x, y=monster_obj.y))
            self.entity_manager.add_component(monster_entity_id, MovableComponent())
            self.entity_manager.add_component(monster_entity_id, HealthComponent(max_hp=monster_obj.max_hp, current_hp=monster_obj.hp))
            self.entity_manager.add_component(monster_entity_id, NameComponent(name=monster_obj.name))
            self.entity_manager.add_component(monster_entity_id, AttackComponent(power=monster_obj.attack, critical_chance=monster_obj.critical_chance, critical_damage_multiplier=monster_obj.critical_damage_multiplier))
            self.entity_manager.add_component(monster_entity_id, DefenseComponent(value=monster_obj.defense))
            monster_obj.entity_id = monster_entity_id
            self.dungeon_map.monsters.append(monster_obj) # 맵의 몬스터 목록에도 추가

        # TODO: 아이템, 함정, 방 입구 등 다른 엔티티 생성 로직도 여기에 통합

