# dungeon/systems.py - 게임 로직을 실행하는 모듈

from typing import Set, Tuple, List, Any
from .ecs import System, Entity, Event, EventManager # EventManager는 필요 없음
from .components import (
    PositionComponent, DesiredPositionComponent, MapComponent, MonsterComponent, 
    MessageComponent, StatsComponent, AIComponent, LootComponent, CorpseComponent,
    RenderComponent, InventoryComponent, ChestComponent, ShopComponent, StunComponent,
    EffectComponent, SkillEffectComponent, HitFlashComponent, LevelComponent,
    HiddenComponent, MimicComponent, TrapComponent, SleepComponent, PoisonComponent,
    StatModifierComponent, ShrineComponent
)
import readchar
import random
import time
from .events import (
    MoveSuccessEvent, CollisionEvent, MessageEvent, MapTransitionEvent,
    ShopOpenEvent, DirectionalAttackEvent, SkillUseEvent, SoundEvent
)


# --- 1.3 주요 시스템 클래스 (로직 구현) ---

class InputSystem(System):
    """사용자 입력 -> DesiredPositionComponent를 엔티티에 추가."""
    def process(self):
        pass # InputSystem의 로직은 handle_input에서 처리됨
    
    def handle_input(self, action: str) -> bool:
        """Engine에서 직접 호출되어 목표 위치 컴포넌트 생성"""
        effect_entities = self.world.get_entities_with_components({EffectComponent})
        for effect in effect_entities:
            self.world.delete_entity(effect.entity_id)

        player_entity = self.world.get_player_entity()
        if not player_entity: return False

        stats = player_entity.get_component(StatsComponent)
        if not stats: return False

        # 1. 쿨다운 확인 (실시간 이동/공격 제한)
        current_time = time.time()
        if current_time - stats.last_action_time < stats.action_delay:
            if action.lower() != 'q':
                return False

        # 스턴 상태 확인
        stun = player_entity.get_component(StunComponent)
        if stun:
            if action == 'q':
                self.world.engine.is_running = False
                return True
            self.event_manager.push(MessageEvent("몸이 움직이지 않습니다... (기절 중)"))
            return False

        # 수면 상태 확인
        sleep = player_entity.get_component(SleepComponent)
        if sleep:
            if action == 'q':
                self.world.engine.is_running = False
                return True
            self.event_manager.push(MessageEvent("깊은 잠에 빠져 움직일 수 없습니다... (수면 중)"))
            return False

        # 액션 허용됨 -> 시간 갱신 (실제 이동/공격 로직에서 한 번 더 갱신할 수 있음)
        stats.last_action_time = current_time

        # 공격 모드 전환 (Space 키)
        if action == ' ':
            # Engine의 is_attack_mode 토글
            self.world.engine.is_attack_mode = not self.world.engine.is_attack_mode
            if self.world.engine.is_attack_mode:
                self.event_manager.push(MessageEvent("공격 방향을 선택하세요... [Space] 취소"))
            else:
                self.event_manager.push(MessageEvent("공격 모드 해제."))
            return False # 턴을 소모하지 않음

        # 입력값 정규화 (소문자 및 좌우 공백 제거)
        action_clean = action.strip()
        action_lower = action_clean.lower()

        move_map = {
            # Standard ANSI
            '\x1b[A': (0, -1),
            '\x1b[B': (0, 1),
            '\x1b[D': (-1, 0),
            '\x1b[C': (1, 0),
            # Application cursor keys
            '\x1bOA': (0, -1),
            '\x1bOB': (0, 1),
            '\x1bOD': (-1, 0),
            '\x1bOC': (1, 0),
            # WASD (Wait/Up/Left/Down/Right)
            'w': (0, -1), 'W': (0, -1),
            'a': (-1, 0), 'A': (-1, 0),
            's': (0, 1),  'S': (0, 1),
            'd': (1, 0),  'D': (1, 0),
        }

        # readchar가 설치되어 있다면 해당 키 상수들도 매핑에 포함 (하위 호환성)
        try:
            import readchar
            move_map.update({
                readchar.key.UP: (0, -1),
                readchar.key.DOWN: (0, 1),
                readchar.key.LEFT: (-1, 0),
                readchar.key.RIGHT: (1, 0),
            })
        except:
            pass

        if action_clean in move_map:
            dx, dy = move_map[action_clean]
            
            # 공격 모드인 경우 (Space 또는 스킬 입력 후 방향키 입력 시)
            if self.world.engine.is_attack_mode:
                self.world.engine.is_attack_mode = False # 공격 후 모드 해제
                
                # 활성화된 스킬이 있는 경우
                active_skill = getattr(self.world.engine, 'active_skill_name', None)
                if active_skill:
                    self.world.engine.active_skill_name = None
                    self.event_manager.push(SkillUseEvent(
                        attacker_id=player_entity.entity_id,
                        skill_name=active_skill,
                        dx=dx,
                        dy=dy
                    ))
                else:
                    # 일반 무기 공격
                    # 원거리 공격 사거리 (장비 스탯 반영)
                    attack_range = 1
                    stats = player_entity.get_component(StatsComponent)
                    if stats:
                        attack_range = stats.weapon_range
                    
                    self.event_manager.push(DirectionalAttackEvent(
                        attacker_id=player_entity.entity_id,
                        dx=dx,
                        dy=dy,
                        range_dist=attack_range
                    ))
                return True # 턴 소모
                
            # 일반 이동 모드
            if player_entity.has_component(DesiredPositionComponent):
                player_entity.remove_component(DesiredPositionComponent)
                
            player_entity.add_component(DesiredPositionComponent(dx=dx, dy=dy))
            return True # 턴 소모
        
        # 퀵슬롯 (1~0)
        if action_clean and action_clean in "1234567890":
            return self.world.engine._trigger_quick_slot(action_clean)
        
        # 상호작용/줍기 (Enter)
        if action in ['\r', '\n']:
            # 제자리 대기 효과 부여 (턴 소모)
            self.event_manager.push(MessageEvent("주변을 살펴봅니다."))
            player_pos = player_entity.get_component(PositionComponent)
            if player_pos:
                # 1. 시체 확인
                corpses = self.world.get_entities_with_components({CorpseComponent, PositionComponent})
                found_corpse = False
                for c in corpses:
                    c_pos = c.get_component(PositionComponent)
                    if c_pos.x == player_pos.x and c_pos.y == player_pos.y:
                        corpse_comp = c.get_component(CorpseComponent)
                        self.event_manager.push(MessageEvent(f"{corpse_comp.original_name}의 시체를 살펴봅니다..."))
                        found_corpse = True
                        break
                
                # 2. 계단 확인 (시체가 없거나 시체 확인 후에도 계단 확인 가능)
                from .constants import EXIT_NORMAL
                map_entities = self.world.get_entities_with_components({MapComponent})
                if map_entities:
                    map_comp = map_entities[0].get_component(MapComponent)
                    if map_comp.tiles[player_pos.y][player_pos.x] == EXIT_NORMAL:
                        target_level = getattr(self.world.engine, 'current_level', 1) + 1
                        self.event_manager.push(MapTransitionEvent(target_level=target_level))
                        return True # 맵 이동 시 턴 소모 (또는 즉시 이동 처리)
                        
                if found_corpse: return True
            return True
        
        # 제자리 대기 (Wait)
        if action_lower in ['.', '5', 'x', 'z']: # 대기 키 확장
            self.event_manager.push(MessageEvent("제자리에서 대기합니다."))
            return True # 턴 소모

        if action_lower == 'q':
            self.world.engine.is_running = False
            return True
        
        # [DEBUG] 알 수 없는 명령 로그
        # self.world.event_manager.push(MessageEvent(f"알 수 없는 명령: {repr(action_clean)}"))
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
                
                # 플레이어 이동 소리
                player = self.world.get_player_entity()
                if player and entity.entity_id == player.entity_id:
                    self.event_manager.push(SoundEvent("STEP"))
                
                # 스태미너 소모 (5이동당 1소모 = 1이동당 0.2소모)
                stats = entity.get_component(StatsComponent)
                if stats:
                    stats.current_stamina -= 0.2
                    if stats.current_stamina <= 0:
                        stats.current_stamina = 0
                        stats.current_hp = 0
                        self.event_manager.push(MessageEvent("탈진하여 쓰러졌습니다! (Stamina 0)"))

                # 4. 계단 확인 (플레이어만)
                if entity.entity_id == self.world.get_player_entity().entity_id:
                    from .constants import EXIT_NORMAL
                    if map_component.tiles[new_y][new_x] == EXIT_NORMAL:
                        self.event_manager.push(MessageEvent("다음 층으로 연결되는 계단입니다. [ENTER] 키를 눌러 내려가시겠습니까?"))

            # 5. 숨겨진 아이템 발견 시 메시지
            if not is_collision:
                hidden_entities = self.world.get_entities_with_components({PositionComponent, HiddenComponent})
                for h_ent in hidden_entities:
                    h_pos = h_ent.get_component(PositionComponent)
                    if h_pos.x == new_x and h_pos.y == new_y:
                        player = self.world.get_player_entity()
                        if player:
                            p_stats = player.get_component(StatsComponent)
                            if p_stats and p_stats.sees_hidden:
                                 self.event_manager.push(MessageEvent("숨겨진 무언가를 발견했습니다!"))

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
            and e.get_component(LootComponent) is None # 루팅 가능한 엔티티(시체, 상자)는 통과 가능
        ]
        
        if not entities_at_position:
            return None
            
        collided_entity = entities_at_position[0]
        
        # 충돌 유형 결정
        if collided_entity.get_component(MonsterComponent):
            return collided_entity.entity_id, "MONSTER"
        
        # 플레이어 체크 (ID=1 가정 또는 컴포넌트 유무)
        if collided_entity.entity_id == self.world.get_player_entity().entity_id:
            return collided_entity.entity_id, "PLAYER"
            
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

            # 스턴/수면 상태 확인 (TimeSystem에서 시간 감액 처리함)
            if monster.has_component(StunComponent) or monster.has_component(SleepComponent):
                continue
 # 스턴 중에는 행동 불가
            
            ai = monster.get_component(AIComponent)
            pos = monster.get_component(PositionComponent)
            stats = monster.get_component(StatsComponent)
            if not ai or not pos or not stats: continue

            # 실시간 행동 지연(Cooldown) 확인
            current_time = time.time()
            # 몬스터는 플레이어보다 약간 느리게 설정 (기본 0.6초 지연)
            monster_delay = getattr(stats, 'action_delay', 0.6)
            if current_time - stats.last_action_time < monster_delay:
                continue
            
            # 맨해튼 거리 계산
            dist = abs(player_pos.x - pos.x) + abs(player_pos.y - pos.y)
            
            # 5. 행동 결정 (플래그 기반 확장)
            if "TELEPORT" in stats.flags and random.random() < 0.2:
                # 30% 확률로 플레이어 근처로 순간이동
                map_ent = self.world.get_entities_with_components({MapComponent})
                if map_ent:
                    mc = map_ent[0].get_component(MapComponent)
                    tx, ty = player_pos.x + random.randint(-2, 2), player_pos.y + random.randint(-2, 2)
                    if 0 <= tx < mc.width and 0 <= ty < mc.height and mc.tiles[ty][tx] == '.':
                        pos.x, pos.y = tx, ty
                        self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(monster)}가 갑자기 뒤로 나타났습니다!"))
                        stats.last_action_time = current_time
                        continue

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
                # 행동 수행 시간 기록
                stats.last_action_time = current_time

            # [BOSS 전용] 보스 소환 및 특수 패턴 (체력 50% 이하 시 1회 소환)
            if "BOSS" in stats.flags and stats.current_hp < stats.max_hp * 0.5:
                if not hasattr(ai, 'has_summoned') or not ai.has_summoned:
                    ai.has_summoned = True
                    self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(monster)}가 지원군을 부릅니다!"))
                    # 주변에 미니언 소환 (2-3마리)
                    for _ in range(random.randint(2, 3)):
                        mx, my = pos.x + random.randint(-1, 1), pos.y + random.randint(-1, 1)
                        # 단순화: 엔진의 몬스터 생성 로직 일부 재사용 또는 소환 비호출
                        # 여기서는 엔진에 소환 요청을 보내는 이벤트를 만들거나 직접 엔진 메서드 호출
                        if hasattr(self.world.engine, '_spawn_minion'):
                            self.world.engine._spawn_minion(mx, my, "GOBLIN")


class CombatSystem(System):
    """엔티티 간 충돌 시 전투(데미지 계산)를 처리합니다."""
    def process(self):
        """매 턴 지속형 스킬 효과(오라) 처리"""
        aura_entities = self.world.get_entities_with_components({SkillEffectComponent, PositionComponent})
        for entity in aura_entities:
            self._handle_skill_aura(entity)

    def _handle_skill_aura(self, entity: Entity):
        """지속 스킬(예: 휠 윈드)의 실시간 효과 처리"""
        effect = entity.get_component(SkillEffectComponent)
        pos = entity.get_component(PositionComponent)
        if not effect or not pos: return

        # 시각 효과 및 로직 틱 증가
        effect.tick_count += 1
        
        # 데미지 및 넉백은 약 0.3초마다(6프레임마다) 1번씩만 적용
        if effect.tick_count % 6 != 0:
            return

        # 주변 적 탐색 (8방향)
        for dy in range(-effect.radius, effect.radius + 1):
            for dx in range(-effect.radius, effect.radius + 1):
                if dx == 0 and dy == 0: continue
                
                tx, ty = pos.x + dx, pos.y + dy
                targets = [
                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                    if e.get_component(PositionComponent).x == tx 
                    and e.get_component(PositionComponent).y == ty
                    and e.entity_id != entity.entity_id
                ]
                
                for target in targets:
                    # 1. 데미지 적용
                    self._apply_damage(entity, target, distance=1)
                    
                    # 2. 스턴 효과 (0.5초 부여 + 연출)
                    if not target.has_component(StunComponent):
                        target.add_component(StunComponent(duration=0.5))
                        # 시각 효과 추가
                        e_id = self.world.create_entity().entity_id
                        self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
                        self.world.add_component(e_id, RenderComponent(char='?', color='yellow'))
                        self.world.add_component(e_id, EffectComponent(duration=0.2))
                    
                    # 3. 넉백 효과 (플레이어 반대 방향으로 1칸)
                    self._apply_knockback(entity, target)

    def _apply_knockback(self, attacker: Entity, target: Entity):
        """대상을 공격자 반대 방향으로 밀어냄"""
        a_pos = attacker.get_component(PositionComponent)
        t_pos = target.get_component(PositionComponent)
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not a_pos or not t_pos or not map_ent: return
        map_comp = map_ent[0].get_component(MapComponent)

        # 밀려날 방향 (공격자 -> 대상 방향 그대로)
        dx = 1 if t_pos.x > a_pos.x else (-1 if t_pos.x < a_pos.x else 0)
        dy = 1 if t_pos.y > a_pos.y else (-1 if t_pos.y < a_pos.y else 0)
        
        nx, ny = t_pos.x + dx, t_pos.y + dy
        
        # 이동 가능한 공간(바닥)이고 다른 엔티티가 없는지 확인
        if 0 <= nx < map_comp.width and 0 <= ny < map_comp.height and map_comp.tiles[ny][nx] == '.':
            # 다른 엔티티 체크
            others = [e for e in self.world.get_entities_with_components({PositionComponent}) 
                     if e.get_component(PositionComponent).x == nx and e.get_component(PositionComponent).y == ny]
            if not others:
                t_pos.x, t_pos.y = nx, ny
                self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}이(가) 뒤로 밀려났습니다!"))

    def handle_directional_attack_event(self, event: DirectionalAttackEvent):
        """특정 방향으로 사거리 내의 모든 적을 공격"""
        attacker = self.world.get_entity(event.attacker_id)
        if not attacker: return

        a_stats = attacker.get_component(StatsComponent)
        if not a_stats: return

        a_pos = attacker.get_component(PositionComponent)
        if not a_pos: return

        # 맵 정보 가져오기
        map_entities = self.world.get_entities_with_components({MapComponent})
        if not map_entities: return
        map_comp = map_entities[0].get_component(MapComponent)

        attacker_name = self._get_entity_name(attacker)
        self.event_manager.push(MessageEvent(f'"{attacker_name}"의 원거리 공격!'))

        # 사거리만큼 일직선상 조사 (애니메이션 효과 포함)
        for dist in range(1, event.range_dist + 1):
            target_x = a_pos.x + (event.dx * dist)
            target_y = a_pos.y + (event.dy * dist)

            # 맵 경계/벽 체크 (공격 차단)
            if not (0 <= target_x < map_comp.width and 0 <= target_y < map_comp.height):
                break
            
            effect_entity = self.world.create_entity()
            self.world.add_component(effect_entity.entity_id, PositionComponent(x=target_x, y=target_y))
            effect_char = '-' if event.dx != 0 else '|'
            self.world.add_component(effect_entity.entity_id, RenderComponent(char=effect_char, color='yellow'))
            self.world.add_component(effect_entity.entity_id, EffectComponent(duration=0.2))

            # 즉시 렌더링 호출 (애니메이션 느낌 유도)
            if hasattr(self.world, 'engine'):
                self.world.engine._render()
                time.sleep(0.03) # 30ms 대기

            if map_comp.tiles[target_y][target_x] == '#':
                self.event_manager.push(MessageEvent("공격이 벽에 막혔습니다."))
                self.world.delete_entity(effect_entity.entity_id) # 잔상 삭제
                break

            # 잔상 삭제 (날아가는 표현을 위해 현재 타일 이펙트 제거)
            self.world.delete_entity(effect_entity.entity_id)

            # 해당 위치의 엔티티 찾기 (관통 공격이므로 매 칸 체크)
            targets_at_pos = [
                e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                if e.get_component(PositionComponent).x == target_x
                and e.get_component(PositionComponent).y == target_y
                and e.entity_id != event.attacker_id
            ]

            hit_any_target = False
            for target in targets_at_pos:
                self._apply_damage(attacker, target, dist)
                hit_any_target = True
            
            # [Piercing] 관통 플래그가 없으면 첫 타격 적중 시 중단
            if hit_any_target and "PIERCING" not in a_stats.flags:
                break

    def handle_move_success_event(self, event: MoveSuccessEvent):
        """플레이어가 이동 성공 시 해당 위치에 루팅 가능한 아이템이 있는지 확인"""
        player_entity = self.world.get_player_entity()
        if not player_entity or event.entity_id != player_entity.entity_id:
            return

        # 해당 위치의 엔티티들 검색 (LootComponent를 가진 것)
        lootables = [
            e for e in self.world.get_entities_with_components({PositionComponent, LootComponent})
            if e.get_component(PositionComponent).x == event.new_x
            and e.get_component(PositionComponent).y == event.new_y
        ]

        for loot_entity in lootables:
            self._handle_loot(player_entity, loot_entity)

    def _handle_loot(self, player: Entity, loot_entity: Entity):
        """아이템 및 골드 루팅 처리"""
        loot = loot_entity.get_component(LootComponent)
        inv = player.get_component(InventoryComponent)
        stats = player.get_component(StatsComponent)
        
        if not loot or not inv or not stats: return

        loot_msg = []
        
        # 골드 루팅
        if loot.gold > 0:
            stats.gold += loot.gold
            loot_msg.append(f"{loot.gold} Gold")
            self.event_manager.push(SoundEvent("COIN"))

        # 아이템 루팅
        for item_data in loot.items:
            item = item_data['item']
            qty = item_data['qty']
            
            if item.name in inv.items:
                inv.items[item.name]['qty'] += qty
            else:
                inv.items[item.name] = {'item': item, 'qty': qty}
            loot_msg.append(f"{item.name} x{qty}")

        if loot_msg:
            msg = ", ".join(loot_msg)
            corpse = loot_entity.get_component(CorpseComponent)
            chest = loot_entity.get_component(ChestComponent)
            
            source = "시체"
            if chest: source = "보물상자"
            elif not corpse: source = "아이템"
            elif corpse and corpse.original_name: source = f"{corpse.original_name}의 시체"
            
            self.event_manager.push(MessageEvent(f"{source}에서 {msg}을(를) 획득했습니다!"))
            
            # 루팅 후 처리 (내용물 비우기)
            loot.items = []
            loot.gold = 0
            
            # 시체인 경우 색상을 하얀색(루팅됨)으로 변경하고 엔티티 유지
            if corpse:
                render = loot_entity.get_component(RenderComponent)
                if render:
                    render.color = 'white'
            
            # 보물상자나 일반 아이템인 경우 삭제
            else:
                self.world.delete_entity(loot_entity.entity_id)
        else:
            # 보상이 없는 경우 (이미 루팅된 시체 등)
            corpse = loot_entity.get_component(CorpseComponent)
            chest = loot_entity.get_component(ChestComponent)
            
            source = "시체"
            if chest: source = "보물상자"
            elif not corpse: source = "아이템"
            elif corpse and corpse.original_name: source = f"{corpse.original_name}의 시체"
            
            # 사용자의 요청에 따른 메시지 형식: "[대상]을(를) 살펴봅니다... 아무것도 발견하지 못했습니다."
            self.event_manager.push(MessageEvent(f"{source}를 살펴봅니다... 아무것도 발견하지 못했습니다."))

    def _get_element_from_flags(self, flags):
        """플래그 집합에서 속성 찾기"""
        from .constants import ELEMENT_FIRE, ELEMENT_WATER, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_NONE
        if "ELEMENT_FIRE" in flags: return ELEMENT_FIRE
        if "ELEMENT_WATER" in flags: return ELEMENT_WATER
        if "ELEMENT_WOOD" in flags: return ELEMENT_WOOD
        if "ELEMENT_EARTH" in flags: return ELEMENT_EARTH
        return ELEMENT_NONE

    def _get_level(self, entity: Entity):
        """엔티티의 레벨을 반환합니다."""
        level_comp = entity.get_component(LevelComponent)
        if level_comp:
            return level_comp.level
        monster_comp = entity.get_component(MonsterComponent)
        if monster_comp:
            return monster_comp.level
        return 1

    def _apply_damage(self, attacker: Entity, target: Entity, distance: int, skill=None, damage_factor=1.0, allow_splash=True):
        """실제 데미지 적용 로직 (상성 및 거리 보정 포함)"""
        from .components import StunComponent, HitFlashComponent
        a_stats = attacker.get_component(StatsComponent)
        t_stats = target.get_component(StatsComponent)
        
        if not a_stats or not t_stats:
            return

        # 1. 속성 결정
        from .constants import ELEMENT_ADVANTAGE, ELEMENT_NONE
        
        # 공격 속성: 스킬 속성 우선 -> 무기 속성 -> 본체 속성(기본)
        attack_element = a_stats.element # 기본값: 본체 속성
        
        # 기본 데미지 범위 결정
        if skill:
            d_min = getattr(skill, 'damage_min', getattr(skill, 'damage', 10))
            d_max = getattr(skill, 'damage_max', getattr(skill, 'damage', 10))
            base_damage = random.randint(max(1, d_min), max(1, d_max))
            attack_element = getattr(skill, 'element', ELEMENT_NONE)
        else:
            d_min = getattr(a_stats, 'attack_min', a_stats.attack)
            d_max = getattr(a_stats, 'attack_max', a_stats.attack)
            base_damage = random.randint(max(1, d_min), max(1, d_max))
            # 무기 속성 확인
            inv = attacker.get_component(InventoryComponent)
            if inv and inv.equipped.get('weapon'):
                 weapon = inv.equipped['weapon']
                 if hasattr(weapon, 'flags'):
                     wpn_element = self._get_element_from_flags(weapon.flags)
                     if wpn_element != ELEMENT_NONE:
                         attack_element = wpn_element
        
        # 방어 속성: 방어구 속성 우선 -> 본체 속성(몬스터) -> 기본(NONE)
        defense_element = t_stats.element 
        t_inv = target.get_component(InventoryComponent)
        if t_inv and t_inv.equipped.get('armor'):
             armor = t_inv.equipped['armor']
             if hasattr(armor, 'flags'):
                 armor_element = self._get_element_from_flags(armor.flags)
                 if armor_element != ELEMENT_NONE:
                     defense_element = armor_element
        
        
        # 2. 데미지 및 크리티컬 계산
        base_damage = int(base_damage * damage_factor)
        is_critical = False
        crit_chance = 0.1 # 기본 크리 10%
        damage_multiplier = 1.0
        advantage_msg = ""
        
        # 상성 체크
        if ELEMENT_ADVANTAGE.get(attack_element) == defense_element:
            # 상성 우위: 데미지 +1~5%, 크리티컬 +10%
            bonus = random.uniform(0.01, 0.05)
            damage_multiplier = 1.0 + bonus
            crit_chance += 0.1
            advantage_msg = f" (상성 우위! +{int(bonus*100)}%)"
        elif ELEMENT_ADVANTAGE.get(defense_element) == attack_element:
            # 상성 열위: 데미지 -1~5%, 크리티컬 -10%
            malus = random.uniform(0.01, 0.05)
            damage_multiplier = 1.0 - malus
            crit_chance -= 0.1
            advantage_msg = f" (상성 열위.. -{int(malus*100)}%)"

        # 크리티컬 판정
        if random.random() < crit_chance:
            is_critical = True
            damage_multiplier *= 1.5
            advantage_msg += " (CRITICAL!)"
            
        # 2. 거리 보정 (스킬이 아닐 경우에만)
        # 2. 거리 보정 (스킬이 아닐 경우에만)
        if not skill and distance > 1:
            dist_multiplier = max(0.5, 1.0 - (distance - 1) * 0.1)
            damage_multiplier *= dist_multiplier
            

        # 2. 명중/실패 판정 (Diablo 1 Formula)
        # Chance to Hit = 50 + (Dex / 2) + ToHit_Bonus + (Attacker_Lv - Target_Lv) - Target_AC
        attacker_name = self._get_entity_name(attacker)
        target_name = self._get_entity_name(target)
        a_lv = self._get_level(attacker)
        t_lv = self._get_level(target)
        
        # 스킬 타입이 마법(MAGIC)인지 확인
        is_magic = False
        if skill:
            s_type = getattr(skill, 'skill_type', "")
            if s_type == "MAGIC":
                is_magic = True
        
        if not is_magic:
            target_ac = random.randint(getattr(t_stats, 'defense_min', t_stats.defense), getattr(t_stats, 'defense_max', t_stats.defense))
            to_hit = 50 + (a_stats.dex / 2) + (a_lv - t_lv) - target_ac
            # boundaries: 5% ~ 95%
            to_hit = max(5, min(95, to_hit))
            
            if random.random() * 100 > to_hit:
                msg = f"'{attacker_name}'의 공격이 '{target_name}'에게 빗나갔습니다! (확률: {int(to_hit)}%)"
                self.event_manager.push(MessageEvent(msg))
                self.event_manager.push(SoundEvent("MISS"))
                return

        # 3. 데미지 계산
        final_damage = 0
        if is_magic:
            # 마법 데미지 (저항력 적용)
            from .constants import ELEMENT_FIRE, ELEMENT_WATER, ELEMENT_WOOD, ELEMENT_POISON
            resist = 0
            if attack_element == ELEMENT_FIRE: resist = t_stats.res_fire
            elif attack_element == ELEMENT_WATER: resist = t_stats.res_ice
            elif attack_element == ELEMENT_WOOD: resist = t_stats.res_lightning
            elif attack_element == ELEMENT_POISON: resist = t_stats.res_poison
            
            resist = min(75, resist) # 최대 저항 75%
            final_damage = int((base_damage * damage_factor * damage_multiplier) * (1 - resist / 100))
        else:
            # 물리 데미지 (STR 보너스)
            # Final Damage = (Weapon_Damage * (1 + Str / 100)) + Bonus_Damage
            # base_damage는 무기/스킬 기본 공격력을 의미함
            final_damage = int((base_damage * damage_factor * (1 + a_stats.str / 100)) * damage_multiplier)

        # 4. 데미지 적용 및 메시지
        if final_damage <= 0 and not is_magic:
            # 물리 공격인데 데미지가 0 이하인 경우 (거의 없겠지만 방어 판정 느낌으로)
            msg = f"'{target_name}'이(가) '{attacker_name}'의 공격을 가뿐히 받아냈습니다!"
            self.event_manager.push(MessageEvent(msg))
            self.event_manager.push(SoundEvent("BLOCK"))
        else:
            final_damage = max(1, final_damage) if final_damage > 0 or is_magic else 0
            if skill:
                msg = f"'{attacker_name}'의 {skill.name}! '{target_name}'에게 {final_damage} 데미지!{advantage_msg}"
            else:
                msg = f"'{attacker_name}'의 공격! '{target_name}'에게 {final_damage} 데미지!{advantage_msg}"
            self.event_manager.push(MessageEvent(msg))
            
            t_stats.current_hp -= final_damage
            
            # [Boss Overhaul] 지원군 소환 트리거 (체력 50% 이하)
            if target.has_component(MonsterComponent):
                m_comp = target.get_component(MonsterComponent)
                if "BOSS" in t_stats.flags and not getattr(m_comp, 'is_summoned', False) and not getattr(t_stats, 'has_summoned_help', False):
                    if t_stats.current_hp > 0 and t_stats.current_hp <= t_stats.max_hp / 2:
                        # 소환 로직 실행
                        self._trigger_boss_summon(attacker, target)

            # [Affix] Life Leech (생명력 흡수)
            if hasattr(a_stats, 'life_leech') and a_stats.life_leech > 0 and final_damage > 0:
                leech_amount = int(final_damage * a_stats.life_leech / 100)
                if leech_amount > 0:
                    old_hp = a_stats.current_hp
                    a_stats.current_hp = min(a_stats.max_hp, a_stats.current_hp + leech_amount)
                    healed = a_stats.current_hp - old_hp
                    if healed > 0:
                        # 흡수 이펙트/메시지는 전투 흐름을 끊지 않도록 간략하게 로그만
                        pass

            # 5. 경직(Hit Recovery) 판정: 데미지 > 최대체력/8
            if final_damage > t_stats.max_hp / 8:
                if not target.has_component(StunComponent):
                    # 0.5초간 경직
                    target.add_component(StunComponent(duration=0.5))
                    self.event_manager.push(MessageEvent(f"'{target_name}'이(가) 강력한 충격으로 경직되었습니다!"))
            
            # A. Attacker Weapon Durability
            a_inv = attacker.get_component(InventoryComponent)
            if a_inv and final_damage > 0:
                # Check Main Hand and Off Hand (if weapon)
                weapons = []
                mh = a_inv.equipped.get("손1")
                oh = a_inv.equipped.get("손2")
                if mh and getattr(mh, 'type', '') == 'WEAPON': weapons.append(mh)
                if oh and getattr(oh, 'type', '') == 'WEAPON': weapons.append(oh)
                
                if weapons and random.random() < 0.1: # 10% chance
                    w_item = random.choice(weapons)
                    if getattr(w_item, 'max_durability', 0) > 0 and w_item.current_durability > 0:
                        w_item.current_durability -= 1
                        if w_item.current_durability <= 0:
                             self.event_manager.push(MessageEvent(f"[경고] {attacker_name}의 {w_item.name}이(가) 파손되었습니다!"))
                             self.event_manager.push(SoundEvent("BREAK"))

            # B. Target Armor Durability
            t_inv = target.get_component(InventoryComponent)
            if t_inv and final_damage > 0:
                # Check Armor Slots
                armors = []
                for slot in ["몸통", "머리", "장갑", "신발", "손2"]: # 손2 could be Shield
                    item = t_inv.equipped.get(slot)
                    # Shield is technically armor for durability purposes
                    if item and getattr(item, 'max_durability', 0) > 0: 
                        armors.append(item)
                
                if armors and random.random() < 0.1: # 10% chance
                    a_item = random.choice(armors)
                    if a_item.current_durability > 0:
                        a_item.current_durability -= 1
                        if a_item.current_durability <= 0:
                             self.event_manager.push(MessageEvent(f"[경고] {target_name}의 {a_item.name}이(가) 파손되었습니다!"))
                             self.event_manager.push(SoundEvent("BREAK"))


        # 6. 효과음 발생
        if final_damage > 0:
            if is_critical:
                self.event_manager.push(SoundEvent("CRITICAL"))
            else:
                self.event_manager.push(SoundEvent("HIT"))

        # 7. 피격 피드백 (Hit Flash)
        if not target.has_component(HitFlashComponent):
            target.add_component(HitFlashComponent(duration=0.15))

        # 5. 적중 효과 (플래그 기반) 어빌리티
        if hasattr(attacker, 'get_component'):
            a_flags = a_stats.flags # 무기나 몬스터 본체의 플래그
            if "STUN_ON_HIT" in a_flags:
                if not target.has_component(StunComponent):
                   target.add_component(StunComponent(duration=1.0))
                   self.event_manager.push(MessageEvent(f"{target_name}이(가) 충격으로 기절했습니다!"))
            
            # 타격 시 스턴 플래그가 있는 스킬인 경우
            if skill:
                if "STUN" in getattr(skill, 'flags', set()):
                    if not target.has_component(StunComponent):
                       target.add_component(StunComponent(duration=2.0))
                if "KNOCKBACK" in getattr(skill, 'flags', set()):
                    self._apply_knockback(attacker, target)
        
        # 5.5 스플래쉬(SPLASH) 데미지 처리
        # allow_splash=True 인 경우에만 발동 (무한 재귀 방지)
        if allow_splash:
            a_flags = getattr(a_stats, 'flags', set())
            s_flags = getattr(skill, 'flags', set()) if skill else set()
            
            # 공격자 플래그 또는 스킬 플래그에 SPLASH가 있으면 발동
            if "SPLASH" in a_flags or "SPLASH" in s_flags:
                t_pos = target.get_component(PositionComponent)
                if t_pos:
                    # 주변 8칸
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0: continue
                            
                            # 타겟 탐색
                            splash_targets = [
                                e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                                if e.get_component(PositionComponent).x == t_pos.x + dx 
                                and e.get_component(PositionComponent).y == t_pos.y + dy
                                and e.entity_id != attacker.entity_id # 자해 방지
                                and e.entity_id != target.entity_id   # 원본 타겟 중복 방지
                            ]
                            
                            for s_target in splash_targets:
                                # 스플래쉬 데미지는 50% (0.5), range=1, 스플래쉬 전파 X
                                self._apply_damage(attacker, s_target, distance=1, skill=skill, damage_factor=0.5, allow_splash=False)
        

        # 3.5 주변 동료 분노 (Angry AI)
        # 플레이어가 몬스터를 공격한 경우에만 발동
        player_entity = self.world.get_player_entity()
        if player_entity and attacker.entity_id == player_entity.entity_id and target.has_component(MonsterComponent):
            t_pos = target.get_component(PositionComponent)
            if t_pos:
                # 주변 5칸 내의 다른 몬스터들 탐색
                all_monsters = self.world.get_entities_with_components([MonsterComponent, AIComponent, PositionComponent])
                for ally in all_monsters:
                    if ally.entity_id == target.entity_id: continue
                    a_pos = ally.get_component(PositionComponent)
                    dist = abs(a_pos.x - t_pos.x) + abs(a_pos.y - t_pos.y) # Manhattan distance
                    if dist <= 5:
                        ai_comp = ally.get_component(AIComponent)
                        if ai_comp.behavior != AIComponent.CHASE:
                            ai_comp.behavior = AIComponent.CHASE
                            # (선택) 분노 메시지는 너무 많아질 수 있으므로 로그에 1번만 출력하거나 생략

        # 3.5 수면(Sleep) 해제 처리: 공격을 받으면 깨어남
        if target.has_component(SleepComponent):
            target.remove_component(SleepComponent)
            self.event_manager.push(MessageEvent(f"{target_name}이(가) 공격을 받아 잠에서 깨어났습니다!"))

        # 4. 사망 처리
        if t_stats.current_hp <= 0:
            t_stats.current_hp = 0
            self.event_manager.push(MessageEvent(f"{target_name}이(가) 쓰러졌습니다!"))
            
            if target.has_component(MonsterComponent):
                m_comp = target.get_component(MonsterComponent)
                m_type = m_comp.type_name
                
                # 몬스터 사망 시 시체로 변환 (영구적 죽음)
                pos = target.get_component(PositionComponent)
                if pos:
                    # 1. 전리품 및 경험치 계산을 위해 몬스터 정의 가져오기
                    m_defs = self.world.engine.monster_defs if hasattr(self.world.engine, 'monster_defs') else {}
                    m_def = m_defs.get(m_type)
                    
                    # 2. 경험치 보상 (플레이어에게)
                    player_entity = self.world.get_player_entity()
                    if player_entity and attacker.entity_id == player_entity.entity_id:
                        if m_def:
                            # LevelSystem을 통해 경험치 획득
                            level_sys = self.world.get_system(LevelSystem)
                            if level_sys:
                                level_sys.gain_exp(player_entity, m_def.xp_value)
                    
                    # 3. 컴포넌트 정리
                    target.remove_component(AIComponent)
                    target.remove_component(MonsterComponent)
                    target.remove_component(StatsComponent)
                    
                    # 4. 시각 효과 변경
                    render = target.get_component(RenderComponent)
                    if render:
                        render.char = '%'
                        render.color = 'blue'
                    
                    # 5. 시체 컴포넌트 추가
                    target.add_component(CorpseComponent(original_name=m_type))
                    
                    # 6. 전리품 설정
                    if not target.has_component(LootComponent):
                        loot_items = []
                        item_defs = self.world.engine.item_defs if hasattr(self.world.engine, 'item_defs') else None
                        # 층수에 맞는 아이템 후보군 가져오기
                        eligible = self.world.engine._get_eligible_items(floor)
                        if eligible and random.random() < 0.2:
                            item = random.choice(eligible)
                            
                            # [Rarity & Affix System] (Monster Drop)
                            # 1. Get Floor
                            dungeon = getattr(self.world.engine, 'dungeon', None)
                            floor = dungeon.dungeon_level_tuple[0] if dungeon else 1
                            
                            # 2. Determine Rarity
                            rarity = self.world.engine._get_rarity(floor)
                            
                            if rarity == "MAGIC" or rarity == "UNIQUE":
                                prefix_id, suffix_id = self.world.engine._roll_magic_affixes(item.type, floor)
                                if prefix_id or suffix_id:
                                    affixed = self.world.engine._create_item_with_affix(item.name, prefix_id, suffix_id)
                                    if affixed:
                                        item = affixed
                                        
                            loot_items.append({'item': item, 'qty': 1})
                        
                        target.add_component(LootComponent(items=loot_items, gold=random.randint(5, 20)))
                # 더 이상 delete_entity를 하지 않음

    def _trigger_boss_summon(self, attacker: Entity, target: Entity):
        """보스의 체력이 낮아지면 지원군을 소환합니다."""
        t_stats = target.get_component(StatsComponent)
        m_comp = target.get_component(MonsterComponent)
        if not t_stats or not m_comp: return
        
        t_stats.has_summoned_help = True
        t_pos = target.get_component(PositionComponent)
        if not t_pos: return
        
        from .constants import BOSS_SEQUENCE
        boss_id = getattr(m_comp, 'monster_id', None)
        if not boss_id or boss_id not in BOSS_SEQUENCE: return
        
        target_name = self._get_entity_name(target)
        self.event_manager.push(MessageEvent(f"'{target_name}'이(가) 강력한 포효와 함께 지원군을 부릅니다!"))
        self.event_manager.push(SoundEvent("BOSS_ROAR"))
        
        engine = self.world.engine
        
        if boss_id == "DIABLO":
            # 모든 이전 보스 소환
            predecessors = BOSS_SEQUENCE[:-1]
            for p_id in predecessors:
                tx, ty = self._find_spawn_pos(t_pos.x, t_pos.y)
                engine._spawn_boss(tx, ty, boss_name=p_id, is_summoned=True)
        else:
            # 이전 보스 1마리 소환
            idx = BOSS_SEQUENCE.index(boss_id)
            if idx > 0:
                p_id = BOSS_SEQUENCE[idx - 1]
                tx, ty = self._find_spawn_pos(t_pos.x, t_pos.y)
                engine._spawn_boss(tx, ty, boss_name=p_id, is_summoned=True)

    def _find_spawn_pos(self, x, y):
        """주변 빈 공간을 찾습니다."""
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not map_ent: return x, y
        mc = map_ent[0].get_component(MapComponent)
        
        for _ in range(15): # 15번 시도
            tx, ty = x + random.randint(-3, 3), y + random.randint(-3, 3)
            if 0 <= tx < mc.width and 0 <= ty < mc.height and mc.tiles[ty][tx] == '.':
                return tx, ty
        return x, y


    def handle_collision_event(self, event: CollisionEvent):
        """충돌 이벤트 발생 시 공격자와 대상이 있으면 전투 처리"""
        if event.collision_type not in ["MONSTER", "PLAYER"] and event.target_entity_id is None:
            return

        attacker = self.world.get_entity(event.entity_id)
        target = self.world.get_entity(event.target_entity_id)
        
        if not attacker or not target:
            return

        # 만약 대상이 상점 컴포넌트를 가지고 있다면 상점 오픈 이벤트 발생
        if target.has_component(ShopComponent) and attacker.entity_id == self.world.get_player_entity().entity_id:
            self.event_manager.push(ShopOpenEvent(shopkeeper_id=target.entity_id))
            return
        
        # [Shrine] 신전 상호작용
        if target.has_component(ShrineComponent) and attacker.entity_id == self.world.get_player_entity().entity_id:
            shrine_comp = target.get_component(ShrineComponent)
            if not shrine_comp.is_used:
                from .events import ShrineOpenEvent
                self.event_manager.push(ShrineOpenEvent(shrine_id=target.entity_id))
            return

        if not target.has_component(ShopComponent):
            # 상인이 아니면 공격 소리 발생
            self.event_manager.push(SoundEvent("ATTACK"))
            
        self._apply_damage(attacker, target, distance=1)

    def handle_skill_use_event(self, event: SkillUseEvent):
        """스킬 사용 로직 처리"""
        attacker = self.world.get_entity(event.attacker_id)
        if not attacker: return

        a_stats = attacker.get_component(StatsComponent)
        if not a_stats: return

        # 스킬 데이터 가져오기 (Engine에 저장된 데이터를 사용)
        skill_defs = getattr(self.world.engine, 'skill_defs', {})
        skill = skill_defs.get(event.skill_name)
        
        # 만약 DB에 없다면 (샌드박스 등의 하드코딩된 이름일 경우 임시 생성)
        if not skill:
            # 샌드박스 등에서 직접 넘긴 이름일 경우를 위한 예외 처리
            if "화염구" in event.skill_name:
                skill = type('obj', (object,), {
                    'name': event.skill_name, 'cost_value': 10, 'damage': 30, 
                    'subtype': 'PROJECTILE', 'range': 6, 'type': 'ATTACK', 'element': '불', 'cost_type': 'MP'
                })
            else:
                self.event_manager.push(MessageEvent(f"알 수 없는 스킬입니다: {event.skill_name}"))
                return

        if not skill:
            return

        # 레벨 제한 확인
        level_comp = attacker.get_component(LevelComponent)
        req_level = getattr(skill, 'required_level', 1)
        if level_comp and req_level > level_comp.level:
            self.event_manager.push(MessageEvent(f"아직 이 기술을 사용할 수 없습니다. (필요: Lv.{req_level})"))
            return

        # 스킬 플래그 가져오기
        s_flags = getattr(skill, 'flags', set())

        # [Class Bonus] Sorcerer Staff Charge System
        # 소서러가 지팡이를 장착하고 있고, 해당 지팡이에 차지가 남아있다면 자원 소모 대신 차지 소모
        used_charge = False
        if level_comp and level_comp.job in ["소서러", "SORCERER"]:
            inv = attacker.get_component(InventoryComponent)
            if inv and "손1" in inv.equipped:
                staff = inv.equipped["손1"]
                from .data_manager import ItemDefinition
                if isinstance(staff, ItemDefinition) and getattr(staff, 'current_charges', 0) > 0:
                    # 지팡이 자체 스킬이거나, 마법 계열 스킬인 경우 차지 사용 (여기서는 단순화하여 모든 MP 소모 스킬에 적용)
                    if skill.cost_type == "MP" or "COST_MP" in s_flags:
                        staff.current_charges -= 1
                        used_charge = True
                        resource_used = f"STAFF CHARGE -1 ({staff.current_charges}/{staff.max_charges})"
                        self.event_manager.push(MessageEvent(f"지팡이의 마력을 사용하여 정신력을 보존했습니다! (남은 충전: {staff.current_charges})"))

        # 자원 소모 로직 (플래그 우선 -> 기존 cost_type 폴백)
        cost_val = skill.cost_value
        resource_used = ""
        
        if not used_charge:
            if "COST_HP" in s_flags:
                if a_stats.current_hp <= cost_val:
                    self.event_manager.push(MessageEvent("체력이 부족합니다!"))
                    return
                a_stats.current_hp -= cost_val
                resource_used = f"HP -{cost_val}"
            elif "COST_STM" in s_flags:
                if a_stats.current_stamina < cost_val:
                    self.event_manager.push(MessageEvent("스태미나가 부족합니다!"))
                    return
                a_stats.current_stamina -= cost_val
                resource_used = f"STM -{cost_val}"
            elif "COST_MP" in s_flags or (hasattr(skill, 'cost_type') and skill.cost_type == "MP"):
                if a_stats.current_mp < cost_val:
                    self.event_manager.push(MessageEvent("마력이 부족합니다!"))
                    return
                a_stats.current_mp -= cost_val
                resource_used = f"MP -{cost_val}"
            elif hasattr(skill, 'cost_type') and skill.cost_type == "STAMINA":
                if a_stats.current_stamina < cost_val:
                    self.event_manager.push(MessageEvent("스태미나가 부족합니다!"))
                    return
                a_stats.current_stamina -= cost_val
                resource_used = f"STM -{cost_val}"

        # [Buff] 능력치 버프 스킬 처리
        if any(v != 0 for v in [getattr(skill, 'str_bonus', 0), getattr(skill, 'mag_bonus', 0), 
                                getattr(skill, 'dex_bonus', 0), getattr(skill, 'vit_bonus', 0)]) and getattr(skill, 'duration', 0) > 0:
            modifiers = attacker.get_components(StatModifierComponent)
            buff_source = f"SKILL_{skill.name}"
            existing = next((m for m in modifiers if m.source == buff_source), None)
            if existing:
                existing.expires_at = time.time() + skill.duration
            else:
                new_mod = StatModifierComponent(
                    str_mod=skill.str_bonus, mag_mod=skill.mag_bonus, 
                    dex_mod=skill.dex_bonus, vit_bonus=skill.vit_bonus, 
                    duration=skill.duration, source=buff_source
                )
                new_mod.expires_at = time.time() + skill.duration
                attacker.add_component(new_mod)
            
            if hasattr(self.world.engine, '_recalculate_stats'):
                self.world.engine._recalculate_stats()
            self.event_manager.push(MessageEvent(f"{skill.name}의 효과로 능력이 향상되었습니다!"))

        # 스킬 레벨 가져오기
        inv = attacker.get_component(InventoryComponent)
        skill_level = 1
        if inv and skill.name in inv.skill_levels:
            skill_level = inv.skill_levels[skill.name]
        elif inv:
            # 베이스 네임으로 재시도 (LvX 제거된 이름)
            import re
            base_name = re.sub(r' Lv\d+', '', skill.name)
            skill_level = inv.skill_levels.get(base_name, 1)

        # 레벨 기반 스케일링 (SCALABLE 플래그가 있는 경우에만 적용)
        if "SCALABLE" in getattr(skill, 'flags', set()):
            # 1. 데미지: 레벨당 +50% 복리 또는 합산 (여기선 합산)
            scaled_damage = int(skill.damage * (1 + 0.5 * (skill_level - 1)))
            # 2. 사거리: 레벨당 +1
            scaled_range = skill.range + (skill_level - 1)
            # 3. 지속시간: 레벨당 +1초 (속성에 따라 다를 수 있음)
            scaled_duration = getattr(skill, 'duration', 5.0) + (skill_level - 1)
        else:
            scaled_damage = skill.damage
            scaled_range = skill.range
            scaled_duration = getattr(skill, 'duration', 5.0)

        # 시스템 전역 사용을 위해 스킬 객체 복사본 생성하여 스케일링 값 저장
        from copy import copy
        effective_skill = copy(skill)
        effective_skill.damage = scaled_damage
        effective_skill.range = scaled_range
        
        # [Class Bonus] Rogue Bow Bonus for Skills
        if level_comp and level_comp.job in ["로그", "ROGUE"]:
            # 장착된 무기가 활인지 확인
            inv = attacker.get_component(InventoryComponent)
            if inv and "손1" in inv.equipped:
                weapon = inv.equipped["손1"]
                from .data_manager import ItemDefinition
                if isinstance(weapon, ItemDefinition) and "RANGED" in getattr(weapon, 'flags', []):
                    effective_skill.range += 3
        effective_skill.duration = scaled_duration
        
        self.event_manager.push(MessageEvent(f"'{effective_skill.name}' 발동! (Lv.{skill_level}, {resource_used})"))

        # 스킬 타입별 처리 (플래그 기반)
        if "PROJECTILE" in effective_skill.flags or effective_skill.subtype == "PROJECTILE":
            self._handle_projectile_skill(attacker, effective_skill, event.dx, event.dy)
        elif "AREA" in effective_skill.flags or effective_skill.subtype == "AREA":
            self._handle_area_skill(attacker, effective_skill)
        elif "AURA" in effective_skill.flags or effective_skill.subtype == "SELF" and "STUN" in effective_skill.flags:
            # 지속형 오라 효과 (예: 휠 윈드)
            attacker.add_component(SkillEffectComponent(
                name=effective_skill.name,
                duration=effective_skill.duration,
                damage=effective_skill.damage,
                radius=effective_skill.range,
                flags=effective_skill.flags
            ))
        else:
            self._handle_self_skill(attacker, effective_skill)


        # 마지막 렌더링 (잔상 제거용)
        if hasattr(self.world, 'engine'):
            self.world.engine._render()

    def _handle_projectile_skill(self, attacker, skill, dx, dy):
        """직선 발사형 스킬: 레벨별 특수 연출 처리"""
        a_pos = attacker.get_component(PositionComponent)
        map_entities = self.world.get_entities_with_components({MapComponent})
        if not map_entities: return
        map_comp = map_entities[0].get_component(MapComponent)
        
        # 시각적 이펙트를 표시할 위치 리스트
        for dist in range(1, skill.range + 1):
            tx, ty = a_pos.x + (dx * dist), a_pos.y + (dy * dist)
            
            # 발사 패턴 (플래그 기반)
            positions = []
            if "SPLIT" in skill.flags: # 갈라지는 탄환
                if dist < skill.range:
                    if dx != 0: positions = [(tx, ty - 1), (tx, ty + 1)]
                    else: positions = [(tx - 1, ty), (tx + 1, ty)]
                else: positions = [(tx, ty)]
            elif "CONVERGE" in skill.flags: # 모여드는 탄환
                # (생략: 갈래 로직은 동일하게 구현하거나 각기 다르게 처리 가능)
                if dist < skill.range:
                    if dx != 0: positions = [(tx, ty - 2), (tx, ty + 2)]
                    else: positions = [(tx - 2, ty), (tx + 2, ty)]
                else: positions = [(tx, ty)]
            else: # 일반
                positions = [(tx, ty)]

            # 유효한 위치만 필터링 (벽 체크 등)
            valid_positions = []
            for px, py in positions:
                if (0 <= px < map_comp.width and 0 <= py < map_comp.height) and map_comp.tiles[py][px] != '#':
                    valid_positions.append((px, py))
            
            if not valid_positions and dist == 1: # 시작부터 막히면 종료
                break
            
            # 이펙트 생성
            effect_ids = []
            char = '#' if "Lv1" in skill.name or "Lv2" in skill.name or "Lv3" in skill.name else '*'
            color = 'red' if getattr(skill, 'element', '') == '불' else 'blue'
            
            for px, py in valid_positions:
                effect = self.world.create_entity()
                e_id = effect.entity_id
                self.world.add_component(e_id, PositionComponent(x=px, y=py))
                self.world.add_component(e_id, RenderComponent(char=char, color=color))
                self.world.add_component(e_id, EffectComponent(duration=0.2))
                effect_ids.append(e_id)

            # 애니메이션 렌더링
            if hasattr(self.world, 'engine'):
                self.world.engine._render()
                time.sleep(0.04)

            # 적 충돌 체크 (모든 발사 위치에서 체크)
            hit_target = False
            
            # 관통 플래그 확인
            is_piercing = "PIERCING" in skill.flags or "PIERCING" in attacker.get_component(StatsComponent).flags
            
            for px, py in valid_positions:
                targets = [
                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                    if e.get_component(PositionComponent).x == px 
                    and e.get_component(PositionComponent).y == py
                    and e.entity_id != attacker.entity_id
                ]
                
                if targets:
                    on_hit = getattr(skill, 'on_hit_effect', "없음")
                    if on_hit == "EXPLOSION":
                        # 폭발은 관통 불가
                        self._handle_explosion(attacker, px, py, skill)
                        hit_target = True
                        break # 폭발 후 소멸
                    else:
                        for target in targets:
                            # 관통이면 데미지 감소 (히트 수에 따라? 여기선 단순화하여 100%->80%->64% 등 구현은 복잡하므로 고정 20% 감쇄 로직 대신 factor 전달)
                            # 현재 구조상 히트 카운트를 추적하기 어려우므로, 관통 무조건 100% 데미지 혹은 거리별 감쇄 등을 적용해야 함.
                            # 여기서는 관통 시 데미지 유지하고 계속 진행하도록 함.
                            self._apply_skill_damage(attacker, target, skill, dx, dy, damage_factor=1.0)
                            hit_target = True
                    
                    if not is_piercing: # 관통이 아니면 첫 타격 후 소멸
                        break
            
            # 관통이면 계속 진행 (단, hit_target이 True여도 break 안함)
            # 만약 관통이 아니고 hit_target이면 투사체 소멸
            if hit_target and not is_piercing:
                # 이펙트 엔티티 삭제
                for e_id in effect_ids:
                    self.world.delete_entity(e_id)
                if hasattr(self.world, 'engine'):
                     self.world.engine._render()
                return

            # 이펙트 엔티티 삭제 (다음 프레임 이동을 위해 현재 잔상 삭제)
            for e_id in effect_ids:
                self.world.delete_entity(e_id)

        # 사거리 끝에서 종료 시 렌더링 (잔상 제거)
        if hasattr(self.world, 'engine'):
            self.world.engine._render()

    def _handle_explosion(self, attacker, cx, cy, skill):
        """폭발 효과: 지정된 좌표 주변 8방향(3x3)에 피해 및 이펙트 생성"""
        
        self.event_manager.push(MessageEvent(f"!!! '{skill.name}' 폭발 !!!"))
        
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx, ty = cx + dx, cy + dy
                
                # 시각적 이펙트 (폭발 느낌)
                e_id = self.world.create_entity().entity_id
                self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
                self.world.add_component(e_id, RenderComponent(char='#', color='yellow'))
                self.world.add_component(e_id, EffectComponent(duration=0.2))
                
                # 범위 내 모든 엔티티 피해 적용
                targets = [
                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                    if e.get_component(PositionComponent).x == tx 
                    and e.get_component(PositionComponent).y == ty
                ]
                for target in targets:
                    self._apply_skill_damage(attacker, target, skill, dx, dy)
        
        # 폭발 애니메이션 표시
        if hasattr(self.world, 'engine'):
            self.world.engine._render()
            time.sleep(0.15) # 폭발 연출을 위해 잠시 대기
            
            # 폭발 이펙트 엔티티 정리
            effect_entities = self.world.get_entities_with_components({EffectComponent})
            for effect in effect_entities:
                # 폭발 이펙트만 골라서 삭제 (노란색 '#' 문자)
                render = effect.get_component(RenderComponent)
                if render and render.char == '#' and render.color == 'yellow':
                    self.world.delete_entity(effect.entity_id)
            
            # 최종 렌더링 (잔상 제거)
            self.world.engine._render()

    def _handle_area_skill(self, attacker, skill):
        """주변 4방향 공격"""
        a_pos = attacker.get_component(PositionComponent)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dx, dy in directions:
            for dist in range(1, skill.range + 1):
                tx, ty = a_pos.x + (dx * dist), a_pos.y + (dy * dist)
                
                effect = self.world.create_entity()
                self.world.add_component(effect.id if hasattr(effect, 'id') else effect.entity_id, PositionComponent(x=tx, y=ty))
                self.world.add_component(effect.id if hasattr(effect, 'id') else effect.entity_id, RenderComponent(char='x', color='purple'))
                self.world.add_component(effect.id if hasattr(effect, 'id') else effect.entity_id, EffectComponent(duration=0.2))

                targets = [
                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                    if e.get_component(PositionComponent).x == tx 
                    and e.get_component(PositionComponent).y == ty
                    and e.entity_id != attacker.entity_id
                ]
                for target in targets:
                    self._apply_skill_damage(attacker, target, skill, dx, dy)

    def _handle_self_skill(self, attacker, skill):
        """회복 등 자신에게 거는 스킬"""
        if skill.type == "RECOVERY":
            stats = attacker.get_component(StatsComponent)
            old_hp = stats.current_hp
            heal_amount = getattr(skill, 'damage', 10)
            stats.current_hp = min(stats.max_hp, stats.current_hp + heal_amount)
            recovered = stats.current_hp - old_hp
            self.event_manager.push(MessageEvent(f"체력을 {recovered} 회복했습니다!"))
            
            # 시각 효과 (초록색 반짝임)
            pos = attacker.get_component(PositionComponent)
            if pos:
                e_id = self.world.create_entity().entity_id
                self.world.add_component(e_id, PositionComponent(x=pos.x, y=pos.y))
                self.world.add_component(e_id, RenderComponent(char='*', color='green'))
                self.world.add_component(e_id, EffectComponent(duration=0.2))

    def _apply_skill_damage(self, attacker, target, skill, dx=0, dy=0, damage_factor=1.0):
        """스킬 데미지 및 부가 효과 적용"""
        # _apply_damage로 통합 (속성, 크리티컬, 거리 보정 등 일괄 적용)
        self._apply_damage(attacker, target, distance=1, skill=skill, damage_factor=damage_factor)

        # 부가 효과 처리
        on_hit = getattr(skill, 'on_hit_effect', "없음")
        if on_hit == "STUN":
            self._handle_stun_effect(target)
        elif on_hit == "SLEEP":
            self._handle_sleep_effect(target)
        elif on_hit == "POISON":
            self._handle_poison_effect(target)
        elif on_hit == "KNOCKBACK":
            self._handle_knockback(target, dx, dy)

    def _handle_stun_effect(self, target):
        """스턴 효과 부여 및 시각 효과 (흔들림 + 캐릭터 위에 ?)"""
        if not target.has_component(StunComponent):
            target.add_component(StunComponent(duration=2))
            
    def _handle_sleep_effect(self, target):
        """수면 효과 부여"""
        if not target.has_component(SleepComponent):
            target.add_component(SleepComponent(duration=5.0))
            self.event_manager.push(MessageEvent(f"{target.world.engine._get_entity_name(target)}이(가) 깊은 잠에 빠졌습니다."))

    def _handle_poison_effect(self, target):
        """중독 효과 부여"""
        if not target.has_component(PoisonComponent):
            target.add_component(PoisonComponent(damage=5, duration=10.0))
            self.event_manager.push(MessageEvent(f"{target.world.engine._get_entity_name(target)}이(가) 독에 중독되었습니다!"))
            
            # 1. 흔들림 애니메이션 (좌우로 떨리는 느낌)
            pos = target.get_component(PositionComponent)
            if pos and hasattr(self.world, 'engine'):
                old_x = pos.x
                for _ in range(3): # 3번 흔들림
                    pos.x = old_x + 1
                    self.world.engine._render()
                    time.sleep(0.03)
                    pos.x = old_x - 1
                    self.world.engine._render()
                    time.sleep(0.03)
                pos.x = old_x # 원래 위치 복구
            
            # 2. 시각 효과 (머리 위 '?' 마크)
            if pos:
                # 머리 위 위치 (맵 밖으로 나가지 않게 체크)
                tx, ty = pos.x, max(0, pos.y - 1)
                
                e_id = self.world.create_entity().entity_id
                self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
                self.world.add_component(e_id, RenderComponent(char='?', color='yellow'))
                self.world.add_component(e_id, EffectComponent(duration=0.2))
            
            self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}가 기절했습니다!"))

    def _handle_knockback(self, target, dx, dy):
        """넉백 효과: 타격 방향으로 밀어냄"""
        pos = target.get_component(PositionComponent)
        if not pos: return

        # 1칸 밀어내기 시도
        new_x = pos.x + dx
        new_y = pos.y + dy

        map_entity_list = self.world.get_entities_with_components({MapComponent})
        if not map_entity_list: return
        map_comp = map_entity_list[0].get_component(MapComponent)

        # 벽이나 경계 체크
        if 0 <= new_x < map_comp.width and 0 <= new_y < map_comp.height:
            if map_comp.tiles[new_y][new_x] == '#':
                # 벽에 부딪힘 -> 추가 데미지
                stats = target.get_component(StatsComponent)
                if stats:
                    extra_dmg = 5
                    stats.current_hp -= extra_dmg
                    self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}가 벽에 부딪혀 {extra_dmg}의 추가 피해를 입었습니다!"))
                return

            # 다른 엔티티 있는지 체크
            blocking_entities = [
                e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                if e.get_component(PositionComponent).x == new_x 
                and e.get_component(PositionComponent).y == new_y
                and e.entity_id != target.entity_id
            ]

            if blocking_entities:
                collision_target = blocking_entities[0]
                stats_target = target.get_component(StatsComponent)
                stats_collision = collision_target.get_component(StatsComponent)
                
                impact_dmg = 5
                if stats_target: stats_target.current_hp -= impact_dmg
                if stats_collision: stats_collision.current_hp -= impact_dmg
                
                name_target = self.world.engine._get_entity_name(target)
                name_collision = self.world.engine._get_entity_name(collision_target)
                self.event_manager.push(MessageEvent(f"{name_target}와 {name_collision}가 충돌하여 서로 {impact_dmg}의 피해를 입었습니다!"))
                return

            # 가로막는 것이 없으면 이동
            pos.x, pos.y = new_x, new_y
            self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}가 뒤로 밀려났습니다!"))
        else:
            # 맵 경계 밖 (벽 취급)
            stats = target.get_component(StatsComponent)
            if stats:
                stats.current_hp -= 5
                self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}가 벽에 부딪혀 피해를 입었습니다!"))

    def _get_entity_name(self, entity) -> str:
        """엔티티의 이름을 가져옵니다 (메시지용)"""
        monster = entity.get_component(MonsterComponent)
        if monster:
            return monster.type_name
        
        # 플레이어인 경우 Engine에 저장된 실제 이름 사용
        player_entity = self.world.get_player_entity()
        if player_entity and entity.entity_id == player_entity.entity_id:
            return self.world.engine.player_name
            
        return f"Entity {entity.entity_id}"


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
                     # 미믹 체크
                     mimic = target_entity.get_component(MimicComponent)
                     if mimic and mimic.is_disguised:
                         mimic.is_disguised = False
                         # 기습 크리티컬 발동
                         self.event_manager.push(MessageEvent("보물상자가 갑자기 몬스터로 변했습니다! 기습 공격을 받았습니다!", "red"))
                         combat_sys = self.world.get_system(CombatSystem)
                         if combat_sys:
                             # 기습 공격 (항상 크리티컬)
                             player = self.world.get_player_entity()
                             # _apply_damage를 직접 호출하기엔 구조상 불편할 수 있으니 
                             # 여기서는 강제로 크리티컬이 발생하게 플래그를 주거나 직접 계산
                             # 일단 간단히 기습 데미지 메시지와 함께 체력 감소
                             combat_sys._apply_damage(target_entity, player, distance=1, damage_factor=1.5) # 1.5배 (크리티컬 느낌)
                         
                         # 보물상자 컴포넌트 제거 (더이상 상자가 아님)
                         target_entity.remove_component(ChestComponent)
                         target_entity.remove_component(LootComponent)
                         # 렌더링 변경은 Engine._render에서 MimicComponent.is_disguised를 보고 처리할 예정
                         return

                     monster_comp = target_entity.get_component(MonsterComponent)
                     if monster_comp:
                         if monster_comp.type_name == "상인":
                             message_comp.add_message("상인을 만났습니다. (거래 가능)")
                         else:
                             message_comp.add_message(f"{monster_comp.type_name}와 충돌했습니다. 전투가 시작됩니다.")
                     else:
                         message_comp.add_message(f"알 수 없는 엔티티와 충돌했습니다.")
            else:
                 message_comp.add_message(f"충돌 발생: {event.collision_type}")

    # handle_move_success_event는 현재 특별한 메시지가 필요 없으므로 생략
class RegenerationSystem(System):
    """실시간 HP/MP/Stamina 회복 및 소모를 처리하는 시스템"""
    def __init__(self, world):
        super().__init__(world)
        self.last_hp_regen_time = time.time()
        self.last_mp_regen_time = time.time()

    def process(self):
        current_time = time.time()
        
        # 1. HP 자연 회복 (1초마다)
        if current_time - self.last_hp_regen_time >= 1.0:
            self.last_hp_regen_time = current_time
            for entity in self.world.get_entities_with_components({StatsComponent}):
                stats = entity.get_component(StatsComponent)
                if stats.current_hp > 0 and stats.current_hp < stats.max_hp:
                    stats.current_hp = min(stats.max_hp, stats.current_hp + 1)
                    # 플레이어인 경우 메시지 출력
                    if entity == self.world.get_player_entity():
                         self.world.event_manager.push(MessageEvent("체력이 1 회복되었습니다."))

        # 2. MP 자연 회복 (2초마다)
        if current_time - self.last_mp_regen_time >= 2.0:
            self.last_mp_regen_time = current_time
            for entity in self.world.get_entities_with_components({StatsComponent}):
                stats = entity.get_component(StatsComponent)
                if stats.current_mp < stats.max_mp:
                    stats.current_mp = min(stats.max_mp, stats.current_mp + 1)
                    # 플레이어인 경우 메시지 출력
                    if entity == self.world.get_player_entity():
                         self.world.event_manager.push(MessageEvent("마력이 1 회복되었습니다."))

        # 3. 스테미너 자연 회복: 제거됨 (아이템으로만 회복)

class TimeSystem(System):
    """지속 시간(Duration)이 있는 컴포넌트들을 실시간으로 관리하는 시스템"""
    def __init__(self, world):
        super().__init__(world)
        self.last_tick = time.time()
        self.regen_timer = 0.0 # 자동 회복 타이머

    def process(self):
        current_time = time.time()
        dt = current_time - self.last_tick
        self.last_tick = current_time

        # 0. 자동 회복 (RegenerationSystem으로 이동됨 - 중복 제거)
        # self.regen_timer += dt ... 로직 삭제

        # 1. 스턴(Stun) 시간 감액
        stun_entities = self.world.get_entities_with_components({StunComponent})
        for entity in list(stun_entities):
            stun = entity.get_component(StunComponent)
            stun.duration -= dt
            if stun.duration <= 0:
                entity.remove_component(StunComponent)
                self.world.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 기절이 해제되었습니다!"))

        # 1-1. 수면(Sleep) 시간 감액
        sleep_entities = self.world.get_entities_with_components({SleepComponent})
        for entity in list(sleep_entities):
            sleep = entity.get_component(SleepComponent)
            sleep.duration -= dt
            if sleep.duration <= 0:
                entity.remove_component(SleepComponent)
                self.world.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}가 잠에서 깨어났습니다!"))

        # 1-2. 중독(Poison) 시간 감액 및 데미지 처리
        poison_entities = self.world.get_entities_with_components({PoisonComponent})
        for entity in list(poison_entities):
            poison = entity.get_component(PoisonComponent)
            poison.duration -= dt
            poison.tick_timer -= dt
            
            if poison.tick_timer <= 0:
                poison.tick_timer = 1.0 # 1초 주기로 리셋
                stats = entity.get_component(StatsComponent)
                if stats:
                    damage = poison.damage
                    stats.current_hp -= damage
                    # 피격 애니메이션(HitFlash) 추가
                    if not entity.has_component(HitFlashComponent):
                        entity.add_component(HitFlashComponent(duration=0.15))
                    
                    # 사망 체크 등은 CombatSystem._apply_damage와 유사하게 처리해야 하지만 
                    # 여기서는 간단히 HP 차감만 하고 사망 시 처리는 다음 턴이나 헬퍼 함수로 처리 가능
                    # 일단 직관적인 사망 처리 로직 추가
                    if stats.current_hp <= 0:
                        stats.current_hp = 0
                        entity_name = self.world.engine._get_entity_name(entity)
                        self.event_manager.push(MessageEvent(f"{entity_name}이(가) 독에 의해 쓰러졌습니다!"))
                        # 실제 사망 처리는 CombatSystem에서 수행되거나 여기서 직접 트리거 가능 (최소한 시체로 변하는 로직 필요)
                        # 여기서는 단순하게 Message만 발생시키고, 실제 삭제/변환은 다음 턴 Combat 로직이 잡도록 하거나 직접 수행
                        # 안전을 위해 시체 변환 로직은 CombatSystem의 로직을 재사용하는 것이 좋음.
            
            if poison.duration <= 0:
                entity.remove_component(PoisonComponent)
                self.world.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 중독 상태가 해제되었습니다."))

        # 2. 횃불(VISION_UP) 시간 감액
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats and "VISION_UP" in stats.flags:
                if current_time >= stats.vision_expires_at:
                    stats.vision_range = 5
                    stats.flags.remove("VISION_UP")
                    self.world.event_manager.push(MessageEvent("횃불이 모두 타버려 다시 어두워졌습니다."))
            
            if stats and stats.sees_hidden:
                if current_time >= stats.sees_hidden_expires_at:
                    stats.sees_hidden = False
                    self.world.event_manager.push(MessageEvent("영험한 기운이 사라져 숨겨진 것들이 보이지 않게 되었습니다."))

        # 2. 시각 효과(Effect) 시간 감액
        effect_entities = self.world.get_entities_with_components({EffectComponent})
        for entity in list(effect_entities):
            effect = entity.get_component(EffectComponent)
            effect.duration -= dt
            if effect.duration <= 0:
                self.world.delete_entity(entity.entity_id)

        # 3. 지속 스킬(SkillEffect) 시간 감액
        skill_entities = self.world.get_entities_with_components({SkillEffectComponent})
        for entity in list(skill_entities):
            skill = entity.get_component(SkillEffectComponent)
            skill.duration -= dt
            if skill.duration <= 0:
                entity.remove_component(SkillEffectComponent)
                self.event_manager.push(MessageEvent(f"{skill.name} 효과가 끝났습니다."))

        # 4. 피격 피드백(HitFlash) 시간 감액
        flash_entities = self.world.get_entities_with_components({HitFlashComponent})
        for entity in list(flash_entities):
            flash = entity.get_component(HitFlashComponent)
            flash.duration -= dt
            if flash.duration <= 0:
                entity.remove_component(HitFlashComponent)

        # 1-3. 능력치 버강/버프(StatModifier) 만료 체크
        needs_recalc = False
        current_time = time.time()
        for entity in list(self.world._entities.values()):
            modifiers = entity.get_components(StatModifierComponent)
            if not modifiers: continue
            
            for mod in list(modifiers):
                if current_time >= mod.expires_at:
                    entity.remove_component_instance(mod)
                    needs_recalc = True
                    self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 효과가 만료되었습니다."))
        
        if needs_recalc and hasattr(self.world.engine, '_recalculate_stats'):
            self.world.engine._recalculate_stats()

class LevelSystem(System):
    """경험치 획득 및 레벨업 로직을 처리하는 시스템"""
    def process(self):
        pass # 레벨업은 이벤트 기반으로 작동함
    def gain_exp(self, entity: Entity, amount: int):
        level_comp = entity.get_component(LevelComponent)
        if not level_comp: return

        # 만렙(99) 도달 시 경험치 보상 중단 또는 레벨업 중단
        if level_comp.level >= 999:
            return

        level_comp.exp += amount
        leveled_up = False
        
        while level_comp.exp >= level_comp.exp_to_next and level_comp.level < 99:
            leveled_up = True
            level_comp.exp -= level_comp.exp_to_next
            self._level_up(entity)
            
        if leveled_up:
            self.event_manager.push(MessageEvent(f"레벨업! 현재 레벨: {level_comp.level}"))
            self.event_manager.push(SoundEvent("LEVEL_UP", "레벨 업!"))

    def _level_up(self, entity: Entity):
        level_comp = entity.get_component(LevelComponent)
        stats_comp = entity.get_component(StatsComponent)
        
        level_comp.level += 1
        # 다음 레벨까지 필요한 경험치 증가 (1.25배)
        level_comp.exp_to_next = int(level_comp.exp_to_next * 1.25)
        
        if stats_comp:
            # [Diablo 1] 직업별 성장치 반영
            hp_gain = 10.0  # 기본값
            mp_gain = 5.0   # 기본값
            
            if hasattr(self.world.engine, 'class_defs') and level_comp.job:
                class_def = self.world.engine.class_defs.get(level_comp.job)
                if class_def:
                    hp_gain = class_def.hp_gain
                    mp_gain = class_def.mp_gain
            
            stats_comp.max_hp = int(stats_comp.max_hp + hp_gain)
            stats_comp.current_hp = stats_comp.max_hp
            stats_comp.max_mp = int(stats_comp.max_mp + mp_gain)
            stats_comp.current_mp = stats_comp.max_mp
            
            # 스탯 상승 (기본 +1씩, 주력 스탯 보너스 등도 고려 가능하나 현재는 평이하게 적용)
            stats_comp.base_str += 1
            stats_comp.base_mag += 1
            stats_comp.base_dex += 1
            stats_comp.base_vit += 1
            
            # 엔진 레벨 보정 스탯 재계산 호출 (장착 아이템 등 반영)
            if hasattr(self.world.engine, '_recalculate_stats'):
                self.world.engine._recalculate_stats()

class TrapSystem(System):
    """함정 발동 및 처리를 담당하는 시스템"""
    def process(self):
        player = self.world.get_player_entity()
        if not player: return
        
        # 위치 컴포넌트가 있는 모든 엔티티 (플레이어, 몬스터)
        entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        # 함정 엔티티
        traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
        
        for entity in list(entities):
            e_pos = entity.get_component(PositionComponent)
            for trap_ent in traps:
                t_pos = trap_ent.get_component(PositionComponent)
                trap = trap_ent.get_component(TrapComponent)
                
                # 같은 위치이고 아직 발동되지 않은 함정
                if not trap.is_triggered and e_pos.x == t_pos.x and e_pos.y == t_pos.y:
                    self._trigger_trap(entity, trap_ent)

    def _trigger_trap(self, victim, trap_ent):
        """함정 발동 효과 처리"""
        trap = trap_ent.get_component(TrapComponent)
        self.event_manager.push(SoundEvent("BASH", f"철컥! 함정이 발동되었습니다! ({trap.trap_type})"))
        trap = trap_ent.get_component(TrapComponent)
        stats = victim.get_component(StatsComponent)
        
        trap.is_triggered = True
        trap.visible = True # 발동되면 보임
        
        is_player = victim.entity_id == self.world.get_player_entity().entity_id
        victim_name = "당신" if is_player else "몬스터"
        self.event_manager.push(MessageEvent(f"{victim_name}이(가) {trap.trap_type} 함정을 밟았습니다!"))
        
        # 데미지 적용
        stats.current_hp -= trap.damage
        if stats.current_hp < 0: stats.current_hp = 0
        
        # 상태 이상 적용
        if trap.effect == "STUN":
            victim.add_component(StunComponent(duration=2.0))
            self.event_manager.push(MessageEvent(f"{victim_name}이(가) 기절했습니다!"))
        
        # 시각적 피드백
        victim.add_component(HitFlashComponent())
