# dungeon/systems.py - 게임 로직을 실행하는 모듈

from typing import Set, Tuple, List, Any
from .ecs import System, Entity, Event, EventManager # EventManager는 필요 없음
from .components import PositionComponent, DesiredPositionComponent, MapComponent, MonsterComponent, MessageComponent, StatsComponent, AIComponent
import readchar

# --- Event 정의 (시스템 통신 표준) ---
class MoveSuccessEvent(Event):
    """엔티티가 성공적으로 새 위치로 이동했을 때 발생"""
    def __init__(self, entity_id: int, old_x: int, old_y: int, new_x: int, new_y: int):
        self.entity_id = entity_id
        self.old_x = old_x
        self.old_y = old_y
        self.new_x = new_x
        self.new_y = new_y

class CollisionEvent(Event):
    """이동 중 맵 타일이나 다른 엔티티와 충돌했을 때 발생"""
    def __init__(self, entity_id: int, target_entity_id: int | None, target_x: int, target_y: int, collision_type: str):
        self.entity_id = entity_id
        self.target_entity_id = target_entity_id # 충돌 대상 Entity ID (벽 충돌 시 None)
        self.target_x = target_x
        self.target_y = target_y
        self.collision_type = collision_type # 'WALL', 'MONSTER', 'ITEM' 등

class MessageEvent(Event):
    """일반 메시지 로그에 표시될 텍스트"""
    def __init__(self, text: str):
        self.text = text


# --- 1.3 주요 시스템 클래스 (로직 구현) ---

class InputSystem(System):
    """사용자 입력 -> DesiredPositionComponent를 엔티티에 추가."""
    def process(self):
        pass # InputSystem의 로직은 handle_input에서 처리됨
    
    def handle_input(self, action: str) -> bool:
        """Engine에서 직접 호출되어 목표 위치 컴포넌트 생성"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return False

        move_map = {
            'w': (0, -1),
            's': (0, 1),
            'a': (-1, 0),
            'd': (1, 0),
            readchar.key.UP: (0, -1),
            readchar.key.DOWN: (0, 1),
            readchar.key.LEFT: (-1, 0),
            readchar.key.RIGHT: (1, 0),
            # Explicit ANSI support for safety
            '\x1b[A': (0, -1),
            '\x1b[B': (0, 1),
            '\x1b[D': (-1, 0),
            '\x1b[C': (1, 0),
            # Application cursor keys (sometimes sent by terminals)
            '\x1bOA': (0, -1),
            '\x1bOB': (0, 1),
            '\x1bOD': (-1, 0),
            '\x1bOC': (1, 0),
        }

        if action in move_map:
            dx, dy = move_map[action]
            
            # 이전 DesiredPositionComponent 제거 및 새로 추가
            if player_entity.has_component(DesiredPositionComponent):
                player_entity.remove_component(DesiredPositionComponent)
                
            player_entity.add_component(DesiredPositionComponent(dx=dx, dy=dy))
            
            return True # 턴 소모

        if action == 'q':
            self.world.engine.is_running = False
            return True
        
        self.world.event_manager.push(MessageEvent(f"알 수 없는 명령: {action}"))
        return False


class MovementSystem(System):
    """이동 요청 처리, 맵 충돌 및 상호작용 후 위치 업데이트."""
    _required_components: Set = {PositionComponent, DesiredPositionComponent}

    def process(self):
        """매 턴(프레임)마다 모든 이동 요청을 처리"""
        # 리스트를 명시적으로 복사하여 사용 (ECS 참조 오류 방지)
        entities_to_move = list(self.world.get_entities_with_components(self._required_components))
        
        # 맵 컴포넌트 정보 가져오기
        map_entity_list = self.world.get_entities_with_components({MapComponent})
        if not map_entity_list: return
        map_component = map_entity_list[0].get_component(MapComponent)

        for entity in entities_to_move:
            position = entity.get_component(PositionComponent)
            desired_pos = entity.get_component(DesiredPositionComponent) 

            # 핵심 방어: position이 없거나, desired_pos가 None인 경우 (중복 제거 후 최종 방어)
            if not position or not desired_pos:
                if desired_pos:
                    entity.remove_component(DesiredPositionComponent)
                continue # 다음 엔티티로 넘어갑니다.

            # 새 목표 위치 계산
            new_x = position.x + desired_pos.dx
            new_y = position.y + desired_pos.dy

            is_collision = False
            
            # 1. 맵 경계/벽 충돌 확인
            if not self._is_valid_tile(map_component, new_x, new_y):
                self.event_manager.push(CollisionEvent(entity.entity_id, None, new_x, new_y, "WALL"))
                is_collision = True
            
            # 2. 다른 엔티티 충돌 확인 (벽 충돌이 아닌 경우에만 확인)
            if not is_collision:
                collision_data = self._check_entity_collision(entity, new_x, new_y)
                if collision_data:
                    collided_id, collision_type = collision_data
                    self.event_manager.push(CollisionEvent(entity.entity_id, collided_id, new_x, new_y, collision_type))
                    is_collision = True
            
            # 3. 이동 성공 (어떤 충돌도 없었을 때만 실행)
            if not is_collision:
                old_x, old_y = position.x, position.y
                position.x, position.y = new_x, new_y
                self.event_manager.push(MoveSuccessEvent(entity.entity_id, old_x, old_y, new_x, new_y))
                
                # 스태미너 소모 (20이동당 1소모 = 1이동당 0.05소모)
                stats = entity.get_component(StatsComponent)
                if stats:
                    stats.current_stamina -= 0.05
                    if stats.current_stamina <= 0:
                        stats.current_stamina = 0
                        stats.current_hp = 0
                        self.event_manager.push(MessageEvent("탈진하여 쓰러졌습니다! (Stamina 0)"))

            # DesiredPositionComponent 제거 (처리 완료)
            entity.remove_component(DesiredPositionComponent)


    # --- 충돌 헬퍼 함수 ---
    def _is_valid_tile(self, map_comp: MapComponent, x: int, y: int) -> bool:
        """맵 경계 및 벽 타일 확인"""
        if not (0 <= x < map_comp.width and 0 <= y < map_comp.height):
            return False # 맵 경계 초과
        if map_comp.tiles[y][x] == '#': 
             return False # 벽 타일
        return True

    def _check_entity_collision(self, moving_entity: Entity, x: int, y: int) -> Tuple[int, str] | None:
        """이동할 위치에 다른 엔티티가 있는지 확인"""
        
        # 맵 관련 엔티티는 무시 (MapComponent, MessageComponent 등)
        entities_at_position = [
            e for e in self.world.get_entities_with_components({PositionComponent}) 
            if e.get_component(PositionComponent).x == x 
            and e.get_component(PositionComponent).y == y
            and e.entity_id != moving_entity.entity_id
            and e.get_component(MapComponent) is None  # 맵 엔티티 제외
            and e.get_component(MessageComponent) is None # 메시지 엔티티 제외
        ]
        
        if not entities_at_position:
            return None
            
        collided_entity = entities_at_position[0]
        
        # 충돌 유형 결정
        if collided_entity.get_component(MonsterComponent):
            return collided_entity.entity_id, "MONSTER"
            
        return collided_entity.entity_id, "OTHER"


class MonsterAISystem(System):
    """몬스터의 행동 패턴에 따라 DesiredPositionComponent를 추가합니다."""
    _required_components: Set = {MonsterComponent, PositionComponent, AIComponent}

    def process(self):
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        player_pos = player_entity.get_component(PositionComponent)
        if not player_pos: return

        monsters = self.world.get_entities_with_components(self._required_components)
        
        for monster in monsters:
            # 안전장치: 플레이어는 제외
            if monster.entity_id == player_entity.entity_id: continue
            
            ai = monster.get_component(AIComponent)
            pos = monster.get_component(PositionComponent)
            if not ai or not pos: continue
            
            # 맨해튼 거리 계산
            dist = abs(player_pos.x - pos.x) + abs(player_pos.y - pos.y)
            
            # 탐지 범위 밖이면 무시
            if dist > ai.detection_range:
                continue
            
            dx, dy = 0, 0
            
            if ai.behavior == AIComponent.CHASE:
                # 플레이어 방향으로 이동 결정
                if player_pos.x > pos.x: dx = 1
                elif player_pos.x < pos.x: dx = -1
                elif player_pos.y > pos.y: dy = 1
                elif player_pos.y < pos.y: dy = -1
                
            elif ai.behavior == AIComponent.FLEE:
                # 플레이어 반대 방향으로 이동 결정
                if player_pos.x > pos.x: dx = -1
                elif player_pos.x < pos.x: dx = 1
                elif player_pos.y > pos.y: dy = -1
                elif player_pos.y < pos.y: dy = 1
            
            if dx != 0 or dy != 0:
                if monster.has_component(DesiredPositionComponent):
                    monster.remove_component(DesiredPositionComponent)
                monster.add_component(DesiredPositionComponent(dx=dx, dy=dy))


class RenderSystem(System):
    """
    ConsoleUI 모듈과 연동하여 최종 렌더링을 준비하고 이벤트를 처리합니다.
    """
    def process(self):
        # ConsoleUI 갱신 로직은 Engine에서 직접 처리
        pass

    # --- 이벤트 핸들러 ---
    
    def handle_message_event(self, event: MessageEvent):
        """MessageEvent를 받아 메시지 로그에 추가"""
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            message_comp.add_message(event.text)

    def handle_collision_event(self, event: CollisionEvent):
        """충돌 이벤트 발생 시 메시지 로그 업데이트"""
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            
            if event.collision_type == "WALL":
                 message_comp.add_message("벽에 막혔습니다.")
            elif event.collision_type == "MONSTER":
                 entity_id = event.target_entity_id
                 target_entity = self.world.get_entity(entity_id)
                 if target_entity:
                     monster_comp = target_entity.get_component(MonsterComponent)
                     if monster_comp:
                         message_comp.add_message(f"{monster_comp.type_name}와 충돌했습니다. 전투가 시작됩니다.")
                     else:
                         message_comp.add_message(f"알 수 없는 엔티티와 충돌했습니다.")
            else:
                 message_comp.add_message(f"충돌 발생: {event.collision_type}")

    # handle_move_success_event는 현재 특별한 메시지가 필요 없으므로 생략
