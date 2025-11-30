import sys # input() 사용을 위해 필요
import readchar # readchar 임포트 추가
import logging # logging 임포트 추가
from events.event_manager import event_manager
from events.game_events import PlayerMovedEvent, GameMessageEvent, DoorOpenedEvent, DoorClosedEvent, KeyUsedEvent, InputReceivedEvent # 추가된 이벤트 임포트
from dungeon.utils.collision import calculate_bounding_box, is_aabb_colliding, check_entity_collision, get_colliding_tile_coords
from .ui import ConsoleUI # ConsoleUI 임포트
from .component import PositionComponent, MovableComponent, MoveRequestComponent, InteractableComponent, ProjectileComponent, DamageRequestComponent, HealthComponent, NameComponent, AttackComponent, DefenseComponent, DeathComponent, GameOverComponent, InventoryComponent, EquipmentComponent, QuickSlotComponent, RenderComponent, ManaComponent, ColliderComponent, AIComponent, ItemUseRequestComponent, DesiredPositionComponent, DoorComponent, KeyComponent # 모든 컴포넌트 임포트
from .entity import EntityManager
from .map import DungeonMap # DungeonMap 임포트 추가
from .items import Item # Item 클래스 임포트 추가
from .player import Player # Player 클래스 임포트 추가

# TODO: DOOR_CLOSED_CHAR, DOOR_OPEN_CHAR는 constants.py로 이동
DOOR_CLOSED_CHAR = '+'

class System:
    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def update(self):
        pass

class InputSystem(System): # System 상속
    """
    사용자의 입력을 감지하고 InputReceivedEvent를 발행하는 시스템입니다.
    """
    def __init__(self, entity_manager: EntityManager):
        super().__init__(entity_manager)

    def update(self):
        # 렌더링 시스템이 화면을 그린 후, 사용자 입력을 대기합니다.
        # 이 방식은 게임을 턴 기반으로 만듭니다.
        key = readchar.readchar() # 사용자 입력 대기 (블로킹 호출)
        if key: # 키 입력이 있으면 이벤트를 발행합니다.
            logging.debug(f"InputSystem: Key detected - {key}")
            event_manager.publish(InputReceivedEvent(key=key))

class MovementSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, inventory_system: 'InventorySystem'):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.inventory_system = inventory_system

    def update(self):
        player_entity_id = None
        for p_id, _ in self.entity_manager.get_components_of_type(Player).items(): # Player 컴포넌트를 가진 엔티티 찾기
            player_entity_id = p_id
            break

        for entity_id, move_request in list(self.entity_manager.get_components_of_type(MoveRequestComponent).items()):
            position = self.entity_manager.get_component(entity_id, PositionComponent)
            if position and self.entity_manager.has_component(entity_id, MovableComponent):
                new_x, new_y = position.x + move_request.dx, position.y + move_request.dy
                
                can_move = True
                collision_result = None

                # 1. 맵 경계 및 타일(벽) 충돌 검사
                if not self.dungeon_map.is_valid_tile(new_x, new_y) or self.dungeon_map.is_wall(new_x, new_y):
                    can_move = False
                    collision_result = "벽으로 막혀있습니다."
                
                # 2. 문과의 상호작용 (플레이어 엔티티만 문과 상호작용 가능)
                if can_move and entity_id == player_entity_id:
                    door_entity_id = None
                    for other_entity_id, other_pos in self.entity_manager.get_components_of_type(PositionComponent).items():
                        if other_pos.x == new_x and other_pos.y == new_y and self.entity_manager.has_component(other_entity_id, DoorComponent):
                            door_entity_id = other_entity_id
                            break
                    
                    if door_entity_id: 
                        door_comp = self.entity_manager.get_component(door_entity_id, DoorComponent)
                        door_render_comp = self.entity_manager.get_component(door_entity_id, RenderComponent)
                        door_collider_comp = self.entity_manager.get_component(door_entity_id, ColliderComponent)

                        if door_comp.is_locked: 
                            key_item_id = f"key_{door_comp.key_id}"
                            if self.inventory_system.has_item(entity_id, key_item_id):
                                self.inventory_system.remove_item(entity_id, key_item_id)
                                door_comp.is_locked = False
                                door_comp.is_open = True
                                door_render_comp.symbol = DOOR_OPEN_CHAR 
                                door_collider_comp.is_solid = False 
                                event_manager.publish(GameMessageEvent(message=f"문이 '{door_comp.key_id}' 열쇠로 열렸습니다!"))
                                event_manager.publish(KeyUsedEvent(entity_id=entity_id, key_id=key_item_id, door_entity_id=door_entity_id))
                                event_manager.publish(DoorOpenedEvent(entity_id=door_entity_id, opener_entity_id=entity_id, door_id=door_comp.key_id, x=new_x, y=new_y))
                            else:
                                event_manager.publish(GameMessageEvent(message=f"문이 잠겨 있습니다. '{door_comp.key_id}' 열쇠가 필요합니다."))
                            can_move = False 
                        elif not door_comp.is_open: 
                            door_comp.is_open = True
                            door_render_comp.symbol = DOOR_OPEN_CHAR
                            door_collider_comp.is_solid = False
                            event_manager.publish(GameMessageEvent(message="문이 열렸습니다."))
                            event_manager.publish(DoorOpenedEvent(entity_id=door_entity_id, opener_entity_id=entity_id, door_id=door_comp.key_id if door_comp.key_id else "unlocked_door", x=new_x, y=new_y))
                            can_move = False 
                        else: 
                            door_comp.is_open = False
                            door_render_comp.symbol = DOOR_CLOSED_CHAR
                            door_collider_comp.is_solid = True 
                            event_manager.publish(GameMessageEvent(message="문이 닫혔습니다."))
                            event_manager.publish(DoorClosedEvent(entity_id=door_entity_id, closer_entity_id=entity_id, door_id=door_comp.key_id if door_comp.key_id else "unlocked_door", x=new_x, y=new_y))
                            can_move = False 

                # 3. 엔티티 간 충돌 검사 (Solid 엔티티)
                if can_move:
                    for other_entity_id, other_pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
                        if other_entity_id == entity_id or other_pos_comp.map_id != position.map_id:
                            continue

                        other_collider = self.entity_manager.get_component(other_entity_id, ColliderComponent)
                        if not other_collider or not other_collider.is_solid:
                            continue

                        # 이동하려는 엔티티의 ColliderComponent 가져오기 (없으면 1x1 엔티티로 가정)
                        moving_collider = self.entity_manager.get_component(entity_id, ColliderComponent)
                        default_collider = ColliderComponent(width=1, height=1)
                        actual_moving_collider = moving_collider if moving_collider else default_collider

                        if check_entity_collision(position, DesiredPositionComponent(x=new_x, y=new_y), actual_moving_collider, other_pos_comp, other_collider):
                            can_move = False
                            if self.entity_manager.has_component(other_entity_id, NameComponent) and \
                               self.entity_manager.get_component(other_entity_id, NameComponent).name not in ["Player", "Item", "Trap", "열쇠(default_key)"]:
                                attacker_attack_comp = self.entity_manager.get_component(entity_id, AttackComponent)
                                if attacker_attack_comp:
                                    self.entity_manager.add_component(other_entity_id, DamageRequestComponent(
                                        target_id=other_entity_id, 
                                        amount=attacker_attack_comp.power, 
                                        attacker_id=entity_id
                                    ))
                                    collision_result = other_entity_id
                                else:
                                    collision_result = "다른 엔티티와 충돌했습니다."
                            else:
                                collision_result = "다른 엔티티와 충돌했습니다."
                            break

                if can_move:
                    position.x = new_x
                    position.y = new_y
                    self.dungeon_map.reveal_tiles(position.x, position.y)

                    if entity_id == player_entity_id:
                        encountered_monster_ids = []
                        # TODO: 맵의 몬스터 목록 대신 entity_manager에서 몬스터 엔티티를 찾아야 함
                        # 현재는 self.dungeon_map.monsters를 사용하므로 이 부분은 유지
                        # for monster_obj in self.dungeon_map.monsters: # 이 부분은 변경 필요
                        #     monster_pos = self.entity_manager.get_component(monster_obj.entity_id, PositionComponent)
                        #     if monster_pos and monster_pos.x == new_x and monster_pos.y == new_y and not monster_obj.dead:
                        #         name_comp = self.entity_manager.get_component(monster_obj.entity_id, NameComponent)
                        #         if name_comp:
                        #             encountered_monster_ids.append(name_comp.name)

                        event_manager.publish(PlayerMovedEvent(
                            entity_id=entity_id, 
                            old_pos=(position.x - move_request.dx, position.y - move_request.dy), 
                            new_pos=(new_x, new_y), 
                            encountered_monster_ids=encountered_monster_ids
                        ))
            
            self.entity_manager.remove_component(entity_id, MoveRequestComponent)

class CollisionSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, player_entity_id: int): # player_entity_id 추가
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.player_entity_id = player_entity_id # player_entity_id 저장

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

            # 이동하려는 엔티티의 ColliderComponent 가져오기 (없으면 1x1 엔티티로 가정)
            moving_collider = self.entity_manager.get_component(entity_id, ColliderComponent)
            default_collider = ColliderComponent(width=1, height=1) # 기본 1x1 충돌체
            actual_moving_collider = moving_collider if moving_collider else default_collider

            # 1. 맵 경계 및 타일(벽) 충돌 검사 (ColliderComponent 활용)
            colliding_tile_coords = get_colliding_tile_coords(new_x, new_y, actual_moving_collider)
            for tx, ty in colliding_tile_coords:
                if not self.dungeon_map.is_valid_tile(tx, ty) or self.dungeon_map.map_data[ty][tx] == WALL_CHAR: # is_wall 대신 map_data 참조
                    can_move = False
                    collision_result = "벽으로 막혀있습니다."
                    break

            # 2. 엔티티 간 충돌 검사 (Solid 엔티티)
            if can_move: # 맵 충돌이 없으면 엔티티 충돌 검사
                for other_entity_id, other_pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
                    if other_entity_id == entity_id or other_pos_comp.map_id != current_pos.map_id:
                        continue # 자기 자신 또는 다른 맵의 엔티티는 무시

                    other_collider = self.entity_manager.get_component(other_entity_id, ColliderComponent)
                    if not other_collider or not other_collider.is_solid: # ColliderComponent가 없거나 통과 가능한 엔티티는 무시
                        continue 

                    # 충돌 유틸리티 함수를 사용하여 목표 위치에서의 충돌을 검사합니다.
                    if check_entity_collision(current_pos, desired_pos, actual_moving_collider, other_pos_comp, other_collider):
                        can_move = False
                        # 충돌한 엔티티가 몬스터인지 확인
                        if self.entity_manager.has_component(other_entity_id, NameComponent) and \
                           self.entity_manager.get_component(other_entity_id, NameComponent).name not in ["Player", "Item", "Trap"]:
                            # 몬스터와 충돌한 경우, DamageRequestComponent를 발행하여 전투를 요청
                            attacker_attack_comp = self.entity_manager.get_component(entity_id, AttackComponent)
                            if attacker_attack_comp:
                                self.entity_manager.add_component(other_entity_id, DamageRequestComponent(
                                    target_id=other_entity_id, 
                                    amount=attacker_attack_comp.power, # 공격하는 엔티티의 공격력 사용
                                    attacker_id=entity_id
                                ))
                                collision_result = other_entity_id # 충돌 결과를 몬스터 ID로 반환하여 engine에서 추가 처리 가능
                            else:
                                collision_result = "다른 엔티티와 충돌했습니다." # 공격력이 없는 엔티티와의 충돌
                        else:
                            collision_result = "다른 엔티티와 충돌했습니다."
                        break # 충돌했으므로 다른 엔티티 검사 중단

            # 3. 함정 충돌 검사 (ColliderComponent 고려)
            if can_move: # 몬스터나 벽에 막히지 않았을 경우에만 함정 검사
                # 이동하려는 엔티티의 ColliderComponent를 사용하여 겹치는 타일 확인
                # 여기서는 SimplifiedCollisionCheck 함수를 사용하여 타일 중심 충돌을 검사할 수 있습니다.
                # 현재는 단순히 목표 타일에 함정이 있는지 확인하는 기존 로직을 유지
                for trap in self.dungeon_map.traps: # self.dungeon_map.traps는 DungeonMap에서 제거되었으므로 수정 필요
                    # 함정도 PositionComponent와 ColliderComponent를 가질 수 있다면 AABB 충돌 검사로 변경 가능
                    # 현재는 함정의 (x, y)가 단일 타일 위치를 나타낸다고 가정
                    if not trap.triggered and trap.x == new_x and trap.y == new_y:
                        trap.trigger()
                        collision_result = trap # 함정 객체 반환
                        break

            if can_move:
                current_pos.x = new_x
                current_pos.y = new_y
                self.dungeon_map.reveal_tiles(current_pos.x, current_pos.y)

                # 이동한 엔티티가 플레이어인 경우 PlayerMovedEvent 발행
                if entity_id == self.player_entity_id:
                    encountered_monster_ids = []
                    # 새 위치에서 몬스터 확인
                    # self.dungeon_map.monsters는 DungeonMap에서 제거되었으므로 수정 필요
                    # for monster_obj in self.dungeon_map.monsters:
                    #     monster_pos = self.entity_manager.get_component(monster_obj.entity_id, PositionComponent)
                    #     if monster_pos and monster_pos.x == new_x and monster_pos.y == new_y and not monster_obj.dead:
                    #         name_comp = self.entity_manager.get_component(monster_obj.entity_id, NameComponent)
                    #         if name_comp:
                    #             encountered_monster_ids.append(name_comp.name)

                    event_manager.publish(PlayerMovedEvent(
                        entity_id=entity_id, # 플레이어 엔티티 ID 추가
                        old_pos=(original_x, original_y), # 필드명 변경
                        new_pos=(new_x, new_y), # 필드명 변경
                        encountered_monster_ids=encountered_monster_ids
                    ))

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
                    # 아이템 루팅 로직
                    looted_something = False
                    item_id_on_map = interactable_comp.data['item_id']
                    item_qty_on_map = interactable_comp.data.get('qty', 1)
                    item_def_on_map = data_manager.get_item_definition(item_id_on_map)

                    if item_def_on_map:
                        looted_item_on_map = Item.from_definition(item_def_on_map) # Item.from_definition 사용
                        
                        inventory_system = self.entity_manager.get_component(self.player_entity_id, InventorySystem) # InventorySystem 인스턴스 가져오기
                        if inventory_system and inventory_system.add_item(self.player_entity_id, looted_item_on_map, item_qty_on_map):
                            event_manager.publish(GameMessageEvent(message=f"{looted_item_on_map.name} {item_qty_on_map}개를 획득했습니다."))
                            self.entity_manager.remove_entity(entity_id) # 맵에서 아이템 엔티티 제거
                            looted_something = True
                        else:
                            event_manager.publish(GameMessageEvent(message=f"{looted_item_on_map.name}을(를) 획득할 수 없습니다."))
                    else:
                        event_manager.publish(GameMessageEvent(message="맵에 있는 알 수 없는 아이템입니다."))
                    
                    if not looted_something:
                        event_manager.publish(GameMessageEvent(message="이동한 타일에 루팅할 아이템이 없습니다."))

                elif interactable_comp.interaction_type == 'ROOM_ENTRANCE':
                    # 방 이동 로직 (engine.py에서 가져옴)
                    # self.dungeon_map.floor, self.dungeon_map.room_index는 DungeonMap에서 제거되었으므로 수정 필요
                    # self.dungeon_map.room_entrances는 DungeonMap에서 제거되었으므로 수정 필요
                    event_manager.publish(GameMessageEvent(message=f"방 입구와 상호작용했습니다. (실제 이동은 engine에서)"))

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
            if not self.dungeon_map.is_valid_tile(new_x, new_y) or self.dungeon_map.map_data[new_y][new_x] == WALL_CHAR: # is_wall 대신 map_data 참조
                self._handle_impact(entity_id, pos_comp.x, pos_comp.y, proj_comp) # 현재 위치에서 충돌 처리
                self.entity_manager.remove_entity(entity_id) # 발사체 파괴
                continue

            # 3. 몬스터 충돌 검사
            # target_monster = self.dungeon_map.get_monster_at(new_x, new_y)는 DungeonMap에서 제거되었으므로 수정 필요
            target_monster = None
            for other_entity_id, other_pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
                if other_entity_id == proj_comp.shooter_id: continue # 발사체 발사자와는 충돌하지 않음
                if other_pos_comp.x == new_x and other_pos_comp.y == new_y and self.entity_manager.has_component(other_entity_id, HealthComponent) and self.entity_manager.has_component(other_entity_id, AIComponent):
                    target_monster = self.entity_manager.get_component(other_entity_id, NameComponent) # 몬스터 NameComponent 반환
                    target_monster.entity_id = other_entity_id # 임시로 엔티티 ID 추가
                    break

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
                base_damage = skill_def.damage
                self.entity_manager.add_component(target_monster.entity_id, DamageRequestComponent(
                    target_id=target_monster.entity_id, 
                    amount=base_damage, 
                    attacker_id=proj_comp.shooter_id, 
                    skill_id=proj_comp.skill_def_id
                ))
                event_manager.publish(GameMessageEvent(message=f"'{skill_def.name}'(이)가 {target_monster.name}에게 적중! {base_damage} 데미지."))

class CombatSystem:
    def __init__(self, entity_manager: EntityManager, ui_instance): # dungeon_map 인자 제거
        self.entity_manager = entity_manager
        self.ui_instance = ui_instance

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
                event_manager.publish(GameMessageEvent(message=f"{attacker_name.name}의 공격!" + (" 💥치명타!💥" if is_critical else "")))
            else: # 공격자 정보가 없으면 순수 데미지 적용 (예: 함정)
                final_damage = base_damage

            target_health.current_hp -= final_damage
            event_manager.publish(GameMessageEvent(message=f"{target_name.name}이(가) {final_damage}의 데미지를 입었습니다. 남은 HP: {target_health.current_hp}"))

            if target_health.current_hp <= 0:
                target_health.current_hp = 0
                target_health.is_alive = False
                event_manager.publish(GameMessageEvent(message=f"{target_name.name}이(가) 쓰러졌습니다!"))
                
                # 사망 처리는 DeathSystem에서 담당
            self.entity_manager.remove_component(entity_id, DamageRequestComponent)


class DungeonGenerationSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance: ConsoleUI, item_definitions, monster_definitions):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.item_definitions = item_definitions
        self.monster_definitions = monster_definitions

    def generate_dungeon_entities(self, dungeon_level_tuple: tuple):
        # TODO: 실제 던전 엔티티 생성 로직 구현 (몬스터, 아이템, 함정, 출구 등)
        pass

    def update(self):
        pass # DungeonGenerationSystem은 주로 초기 맵 생성 시에만 사용되므로 update 메서드는 비워둡니다.

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
                    # self.dungeon_map.monsters는 DungeonMap에서 제거되었으므로 수정 필요
                    killed_monster_name_comp = self.entity_manager.get_component(entity_id, NameComponent)
                    killed_monster_pos_comp = self.entity_manager.get_component(entity_id, PositionComponent)
                    killed_monster_ai_comp = self.entity_manager.get_component(entity_id, AIComponent) # 경험치 정보는 AIComponent에 있다고 가정
                    
                    if killed_monster_name_comp and killed_monster_pos_comp and killed_monster_ai_comp:
                        # 경험치 획득 (공격자가 플레이어인 경우에만)
                        player_exp_comp = self.entity_manager.get_component(self.player_entity_id, ExperienceComponent) # ExperienceComponent가 있다고 가정
                        if player_exp_comp:
                            exp_gained = killed_monster_ai_comp.exp_given + (killed_monster_ai_comp.level * 2) # AIComponent에 level, exp_given이 있다고 가정
                            event_manager.publish(GameMessageEvent(message=f"{exp_gained}의 경험치를 획득했습니다!"))
                            # TODO: player_obj.gain_exp 대신 ExperienceSystem에서 처리하도록 변경
                            # leveled_up, level_up_message = player_obj.gain_exp(exp_gained, self.entity_manager)
                            # if leveled_up: event_manager.publish(GameMessageEvent(message=level_up_message))

                        # 아이템 드랍
                        if data_manager._item_definitions and random.random() < 0.5:
                            dropped_item_id = random.choice(list(data_manager._item_definitions.keys()))
                            # 몬스터가 죽은 위치에 아이템을 맵에 추가
                            item_entity_id = self.entity_manager.create_entity()
                            self.entity_manager.add_component(item_entity_id, PositionComponent(x=killed_monster_pos_comp.x, y=killed_monster_pos_comp.y, map_id=killed_monster_pos_comp.map_id))
                            self.entity_manager.add_component(item_entity_id, RenderComponent(symbol=Item.from_definition(data_manager.get_item_definition(dropped_item_id)).char, color="yellow"))
                            self.entity_manager.add_component(item_entity_id, InteractableComponent(interaction_type='ITEM_TILE', data={'item_id': dropped_item_id, 'qty': 1}))
                            self.entity_manager.add_component(item_entity_id, NameComponent(name=data_manager.get_item_definition(dropped_item_id).name))
                            
                            item_def = data_manager.get_item_definition(dropped_item_id)
                            if item_def:
                                event_manager.publish(GameMessageEvent(message=f"{killed_monster_name_comp.name}이(가) {item_def.name}을(를) 떨어뜨렸습니다."))

                    # 엔티티 제거 (DeathComponent가 있는 엔티티는 DeletionSystem에서 제거)
                    # self.entity_manager.remove_entity(entity_id) # DeletionSystem에서 처리
                    # 몬스터 객체 목록에서도 제거 (dungeon_map.monsters는 제거되었음)

                else: # 플레이어 사망 처리
                    event_manager.publish(GameMessageEvent(message="당신은 쓰러졌습니다..."))
                    # 게임 오버 상태를 알리는 컴포넌트 추가
                    self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=False))


class GameOverSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance, player_entity_id: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id

    def update(self):
        # 1. 플레이어 사망 조건은 DeathSystem에서 GameOverComponent를 추가하여 처리됨
        # 2. 승리 조건 (예: 보스 몬스터 사망 또는 최종 층 도달)
        # TODO: 보스 몬스터 엔티티 ID를 DungeonGenerationSystem에서 관리하도록 변경
        # 현재는 임시로 보스 몬스터가 없으면 승리하는 것으로 가정
        # self.dungeon_map.floor, self.dungeon_map.monsters는 DungeonMap에서 제거되었으므로 수정 필요
        # if self.dungeon_map.floor == 10 and not self.dungeon_map.monsters: # 10층에 몬스터가 없으면 승리 (임시)
        #     if not self.entity_manager.has_component(self.player_entity_id, GameOverComponent):
        #         self.entity_manager.add_component(self.player_entity_id, GameOverComponent(win=True))
        #         event_manager.publish(GameMessageEvent(message="게임 승리! 던전을 탈출했습니다."))
        #         return # 게임 종료

        # 게임 오버 상태가 되면 Engine의 루프를 종료
        game_over_comp = self.entity_manager.get_component(self.player_entity_id, GameOverComponent)
        if game_over_comp:
            # Engine 인스턴스에 접근하여 is_running 상태를 변경
            # Engine은 RenderingSystem의 생성자를 통해 전달되므로, RenderingSystem에서 접근 가능하도록 함
            # 또는 GameStateComponent를 추가하여 엔진에서 읽도록 할 수 있음
            event_manager.publish(GameMessageEvent(message=f"게임 종료: {'승리' if game_over_comp.win else '패배'}"))


class AISystem(System): # System 상속
    """
    몬스터의 AI를 처리하고 이동 요청(MoveRequestComponent)을 발행하는 시스템입니다.
    """
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, player_entity_id: int):
        super().__init__(entity_manager)
        self.dungeon_map = dungeon_map
        self.player_entity_id = player_entity_id

    def update(self, dt: float): # dt 인자 추가
        player_pos = self.entity_manager.get_component(self.player_entity_id, PositionComponent)
        if not player_pos:
            return

        for entity_id, ai_comp in list(self.entity_manager.get_components_of_type(AIComponent).items()):
            ai_comp.action_cooldown -= dt # 쿨다운 감소

            if ai_comp.action_cooldown > 0: # 쿨다운 중이면 행동하지 않음
                continue

            monster_pos = self.entity_manager.get_component(entity_id, PositionComponent)
            if not monster_pos or monster_pos.map_id != self.dungeon_map.dungeon_level_tuple:
                continue
            
            # 플레이어가 시야 내에 있는지 확인 (간단한 예시)
            distance = math.sqrt((player_pos.x - monster_pos.x)**2 + (player_pos.y - monster_pos.y)**2)
            
            if distance < 5: # 플레이어가 5타일 이내에 있으면 추적
                ai_comp.state = 'CHASE'
                ai_comp.target_entity_id = self.player_entity_id
                ai_comp.last_known_player_pos = (player_pos.x, player_pos.y)
            elif ai_comp.state == 'CHASE' and ai_comp.last_known_player_pos:
                # 플레이어를 놓쳤지만 마지막으로 본 위치로 이동
                target_x, target_y = ai_comp.last_known_player_pos
                if monster_pos.x == target_x and monster_pos.y == target_y:
                    ai_comp.state = 'IDLE' # 목표 지점에 도달하면 IDLE
            else:
                ai_comp.state = 'IDLE' # 기본적으로 IDLE

            if ai_comp.state == 'CHASE' and ai_comp.target_entity_id:
                # 플레이어에게 다가가는 방향 계산
                dx, dy = 0, 0
                if player_pos.x > monster_pos.x: dx = 1
                elif player_pos.x < monster_pos.x: dx = -1
                if player_pos.y > monster_pos.y: dy = 1
                elif player_pos.y < monster_pos.y: dy = -1
                
                # MoveRequestComponent 발행
                if dx != 0 or dy != 0:
                    self.entity_manager.add_component(entity_id, MoveRequestComponent(entity_id=entity_id, dx=dx, dy=dy))
                    ai_comp.action_cooldown = ai_comp.action_delay # 행동 후 쿨다운 설정
            elif ai_comp.state == 'IDLE':
                # IDLE 상태일 때는 무작위 이동 요청을 발행할 수 있습니다 (선택 사항)
                pass # 지금은 아무것도 하지 않음


class SaveLoadSystem:
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance: ConsoleUI, player_entity_id: int, all_dungeon_maps: dict, rng_seed: int):
        self.entity_manager = entity_manager
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id
        self.all_dungeon_maps = all_dungeon_maps
        self.rng_seed = rng_seed

    def update(self):
        pass # 저장/로드 기능은 주로 특정 입력(예: 메뉴)에 의해 트리거되므로 update는 비워둡니다.


class InventorySystem:
    def __init__(self, entity_manager: EntityManager, ui_instance: ConsoleUI, item_definitions):
        self.entity_manager = entity_manager
        self.ui_instance = ui_instance
        self.item_definitions = item_definitions

    def add_item(self, entity_id: int, item: Item, quantity: int = 1) -> bool:
        # TODO: 실제 아이템 추가 로직 구현
        return True

    def has_item(self, entity_id: int, item_id: str) -> bool:
        # TODO: 실제 아이템 보유 여부 확인 로직 구현
        return True

    def remove_item(self, entity_id: int, item_id: str, quantity: int = 1) -> bool:
        # TODO: 실제 아이템 제거 로직 구현
        return True

    def loot_items(self, player_entity_id: int, dungeon_map: DungeonMap) -> tuple[str, bool]:
        # TODO: 실제 아이템 루팅 로직 구현
        return "", False

    def update(self):
        pass


class RenderingSystem(System):
    def __init__(self, entity_manager: EntityManager, dungeon_map: DungeonMap, ui_instance: ConsoleUI, player_entity_id: int, engine: 'Engine'):
        super().__init__(entity_manager)
        self.dungeon_map = dungeon_map
        self.ui_instance = ui_instance
        self.player_entity_id = player_entity_id
        self.engine = engine # Engine 인스턴스

    def update(self):
        player_pos = self.entity_manager.get_component(self.player_entity_id, PositionComponent)
        if not player_pos: return

        # UI를 통해 맵 렌더링을 요청합니다.
        map_display_data = []
        for y in range(self.dungeon_map.height):
            row = []
            for x in range(self.dungeon_map.width):
                # 맵 타일 그리기
                tile_char = self.dungeon_map.get_tile_for_display(x, y)
                tile_color = "white" # 기본 색상
                
                # 엔티티 그리기 (플레이어, 몬스터, 아이템 등)
                entity_at_pos = False
                for eid, pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
                    if pos_comp.x == x and pos_comp.y == y and pos_comp.map_id == player_pos.map_id: # 현재 맵에 있는 엔티티만
                        render_comp = self.entity_manager.get_component(eid, RenderComponent)
                        if render_comp:
                            if eid == self.player_entity_id: # 플레이어는 항상 맨 위에 렌더링
                                tile_char = render_comp.symbol
                                tile_color = render_comp.color
                                entity_at_pos = True
                                break # 플레이어가 있으면 다른 엔티티는 무시
                            elif self.entity_manager.has_component(eid, AIComponent): # 몬스터
                                if not entity_at_pos: # 아직 다른 엔티티가 없으면 몬스터 그리기
                                    tile_char = render_comp.symbol
                                    tile_color = render_comp.color
                                    entity_at_pos = True
                            elif self.entity_manager.has_component(eid, InteractableComponent) and not entity_at_pos: # 아이템
                                tile_char = render_comp.symbol
                                tile_color = render_comp.color
                                entity_at_pos = True

                row.append((tile_char, tile_color))
            map_display_data.append(row)

        # 플레이어 스탯 정보
        player_health_comp = self.entity_manager.get_component(self.player_entity_id, HealthComponent)
        player_mana_comp = self.entity_manager.get_component(self.player_entity_id, ManaComponent)
        player_name_comp = self.entity_manager.get_component(self.player_entity_id, NameComponent)
        player_att_comp = self.entity_manager.get_component(self.player_entity_id, AttackComponent)
        player_def_comp = self.entity_manager.get_component(self.player_entity_id, DefenseComponent)
        player_inventory_comp = self.entity_manager.get_component(self.player_entity_id, InventoryComponent)

        player_stats = {
            'name': player_name_comp.name if player_name_comp else 'Unknown',
            'hp': player_health_comp.current_hp if player_health_comp else 0,
            'max_hp': player_health_comp.max_hp if player_health_comp else 0,
            'mp': player_mana_comp.current_mp if player_mana_comp else 0,
            'max_mp': player_mana_comp.max_mp if player_mana_comp else 0,
            'attack': player_att_comp.power if player_att_comp else 0,
            'defense': player_def_comp.value if player_def_comp else 0,
            'inventory': [item.name for item in player_inventory_comp.items] if player_inventory_comp and player_inventory_comp.items else []
        }

        self.ui_instance.render_all(map_display_data, player_stats)



class DeletionSystem(System):
    def __init__(self, entity_manager: EntityManager):
        super().__init__(entity_manager)

    def update(self):
        # DeathComponent가 있는 엔티티들을 제거하는 로직을 여기에 구현
        entities_to_delete = []
        for entity_id, death_comp in self.entity_manager.get_components_of_type(DeathComponent).items():
            entities_to_delete.append(entity_id)

        for entity_id in entities_to_delete:
            self.entity_manager.remove_entity(entity_id)


class LoggingSystem(System): # System 상속
    """
    PlayerMovedEvent를 구독하여 게임 메시지(로그)를 출력하는 시스템입니다.
    """
    def __init__(self, entity_manager: EntityManager, ui_instance):
        super().__init__(entity_manager)
        self.ui_instance = ui_instance # renderer 대신 ui_instance 사용
        
        # CRITICAL: 시스템이 시작될 때 이벤트를 구독합니다.
        event_manager.subscribe(PlayerMovedEvent, self.handle_player_moved_event) # 메서드 이름 유지
        event_manager.subscribe(GameMessageEvent, self.handle_game_message_event)
        event_manager.subscribe(DoorOpenedEvent, self.handle_door_opened_event)
        event_manager.subscribe(DoorClosedEvent, self.handle_door_closed_event)
        event_manager.subscribe(KeyUsedEvent, self.handle_key_used_event)
        event_manager.publish(GameMessageEvent(message="LoggingSystem: 모든 이벤트 구독 완료."))

    def handle_player_moved_event(self, event: PlayerMovedEvent):
        """PlayerMovedEvent를 처리하는 핸들러 함수입니다."""
        
        # 1. 플레이어 위치를 로그로 출력 (디버그용)
        x, y = event.new_pos # event.new_pos 사용
        log_message = f"플레이어가 이동했습니다: ({x}, {y})"
        
        # 2. 메시지 로그에 메시지 추가 (UI 직접 호출은 불가피)
        self.ui_instance.add_message(log_message)
        
        # 3. (임시) 몬스터 근접 메시지 출력 로직은 추후 CombatSystem 이벤트로 분리 예정
        #    현재는 단순 이동 로그만 출력합니다.
        #    encountered_monster_ids 로깅은 필요에 따라 남길 수 있음 (디버그용)
        if event.encountered_monster_ids:
            self.ui_instance.add_message(f"DEBUG: Player encountered monsters: {', '.join(event.encountered_monster_ids)}")

    def handle_game_message_event(self, event: GameMessageEvent):
        self.ui_instance.add_message(event.message)

    def handle_door_opened_event(self, event: DoorOpenedEvent):
        door_name = f"문 (ID: {event.door_id})" if event.door_id else "문"
        self.ui_instance.add_message(f"{door_name}이(가) 열렸습니다. (X: {event.x}, Y: {event.y})")

    def handle_door_closed_event(self, event: DoorClosedEvent):
        door_name = f"문 (ID: {event.door_id})" if event.door_id else "문"
        self.ui_instance.add_message(f"{door_name}이(가) 닫혔습니다. (X: {event.x}, Y: {event.y})")

    def handle_key_used_event(self, event: KeyUsedEvent):
        self.ui_instance.add_message(f"열쇠를 사용하여 문을 열었습니다. (X: {event.x}, Y: {event.y})")