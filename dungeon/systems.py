# dungeon/systems.py - 게임 로직을 실행하는 모듈

from typing import Set, Tuple, List, Any
from .ecs import System, Entity, Event, EventManager # EventManager는 필요 없음
from .components import (
    PositionComponent, DesiredPositionComponent, MapComponent, MonsterComponent, 
    MessageComponent, StatsComponent, AIComponent, LootComponent, CorpseComponent,
    RenderComponent, InventoryComponent, ChestComponent, ShopComponent, StunComponent,
    EffectComponent, SkillEffectComponent, HitFlashComponent, LevelComponent,
    HiddenComponent, MimicComponent, TrapComponent, SleepComponent, PoisonComponent,
    StatModifierComponent, ShrineComponent, ManaShieldComponent, SummonComponent,
    PetrifiedComponent, BleedingComponent, BossComponent, CombatTrackerComponent,
    ChargeComponent, SwitchComponent, BossGateComponent, BlockMapComponent, DoorComponent
)
import readchar
import random
import time
import logging
from .ui import COLOR_MAP
from .localization import _
from .events import (
    MoveSuccessEvent, CollisionEvent, MessageEvent, MapTransitionEvent,
    ShopOpenEvent, DirectionalAttackEvent, SkillUseEvent, SoundEvent, CombatResultEvent,
    InteractEvent, TrapTriggerEvent
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
        
        # [Petrified] 1스택 이상: Action Delay 50% 증가 (Slow)
        # 3스택: 행동 불가 (Stunned)
        p_comp = player_entity.get_component(PetrifiedComponent)
        monster_delay = stats.action_delay
        if p_comp:
            if p_comp.stacks >= 3:
                # 3스택(Full): 행동 불가
                if action == 'q':
                    self.world.engine.is_running = False
                    return True
                if current_time - stats.last_action_time > 1.0: # 메시지 도배 방지
                    self.event_manager.push(MessageEvent(_("전신이 석화되어 움직일 수 없습니다!"), "gray"))
                    stats.last_action_time = current_time # 쿨다운 갱신하여 메시지 텀 주기
                return False
            elif p_comp.stacks >= 1:
                # 1~2스택: 행동 지연 증가
                monster_delay *= 1.5

        if current_time - stats.last_action_time < monster_delay:
            if action.lower() != 'q':
                return False

        # 스턴 상태 확인
        stun = player_entity.get_component(StunComponent)
        if stun:
            if action == 'q':
                self.world.engine.is_running = False
                return True
            self.event_manager.push(MessageEvent(_("몸이 움직이지 않습니다... (기절 중)")))
            return False

        # 수면 상태 확인
        sleep = player_entity.get_component(SleepComponent)
        if sleep:
            if action == 'q':
                self.world.engine.is_running = False
                return True
            self.event_manager.push(MessageEvent(_("깊은 잠에 빠져 움직일 수 없습니다... (수면 중)")))
            return False

        # 액션 허용됨 -> 시간 갱신 (실제 이동/공격 로직에서 한 번 더 갱신할 수 있음)
        stats.last_action_time = current_time

        # 공격 모드 전환 (Space 키)
        if action == ' ':
            # Engine의 is_attack_mode 토글
            self.world.engine.is_attack_mode = not self.world.engine.is_attack_mode
            if self.world.engine.is_attack_mode:
                self.event_manager.push(MessageEvent(_("공격 방향을 선택하세요... [Space] 취소")))
            else:
                self.event_manager.push(MessageEvent(_("공격 모드 해제.")))
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
                
                # [Charge Skill] 스킬 충전 확인 (ChargeComponent)
                c_comp = player_entity.get_component(ChargeComponent)
                active_skill = getattr(self.world.engine, 'active_skill_name', None)
                
                if c_comp and c_comp.stored_skill_name:
                    # 충전된 스킬 발사!
                    skill_name = c_comp.stored_skill_name
                    
                    # [Heal Check] 회복 스킬이면 자신에게 시전
                    # (단순히 이름에 'Heal'이나 '회복'이 포함되는지, 또는 Skill Defs의 type을 확인)
                    # 여기서는 간단히 로직 처리
                    is_heal = False
                    skill_defs = getattr(self.world.engine, 'skill_defs', {})
                    if skill_name in skill_defs:
                        skill_def = skill_defs[skill_name]
                        if getattr(skill_def, 'type', '') == 'HEAL' or 'Heal' in skill_name or '회복' in skill_name:
                            is_heal = True
                    
                    if is_heal:
                        # 자신에게 시전 (dx=0, dy=0), Cost=0 (Free)
                        self.event_manager.push(MessageEvent(_("지팡이에 충전된 '{}'을(를) 방출하여 자신을 치유합니다!").format(skill_name), "yellow"))
                        self.event_manager.push(SkillUseEvent(
                            attacker_id=player_entity.entity_id,
                            skill_name=skill_name,
                            dx=0,
                            dy=0,
                            cost=0 # FREE
                        ))
                    else:
                        # 방향 발사, Cost=0 (Free)
                        self.event_manager.push(MessageEvent(_("지팡이에 충전된 '{}'을(를) 방출합니다!").format(skill_name), "yellow"))
                        self.event_manager.push(SkillUseEvent(
                            attacker_id=player_entity.entity_id,
                            skill_name=skill_name,
                            dx=dx,
                            dy=dy,
                            cost=0 # FREE
                        ))
                    
                    # 충전 해제
                    player_entity.remove_component(ChargeComponent)
                    return True # 턴 소모

                # 활성화된 스킬이 있는 경우 (Quick Slot 등)
                elif active_skill:
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
        
        # Character Sheet (C)
        if action in ['c', 'C']:
            from .engine import GameState
            if self.world.engine.state == GameState.PLAYING:
                self.world.engine.state = GameState.CHARACTER_SHEET
            elif self.world.engine.state == GameState.CHARACTER_SHEET:
                self.world.engine.state = GameState.PLAYING
            return False

        # 퀵슬롯 (1~0)
        if action_clean and action_clean in "1234567890":
            return self.world.engine._trigger_quick_slot(action_clean)
        
        # 상호작용/줍기 (Enter)
        if action in ['\r', '\n']:
            # 제자리 대기 효과 부여 (턴 소모)
            self.event_manager.push(MessageEvent(_("주변을 살펴봅니다.")))
            player_pos = player_entity.get_component(PositionComponent)
            if player_pos:
                # 1. 시체 확인
                corpses = self.world.get_entities_with_components({CorpseComponent, PositionComponent})
                found_corpse = False
                for c in corpses:
                    c_pos = c.get_component(PositionComponent)
                    if c_pos.x == player_pos.x and c_pos.y == player_pos.y:
                        corpse_comp = c.get_component(CorpseComponent)
                        self.event_manager.push(MessageEvent(_("{}의 시체를 살펴봅니다...").format(corpse_comp.original_name)))
                        found_corpse = True
                        break
                
                # 2. 계단 확인 (시체가 없거나 시체 확인 후에도 계단 확인 가능)
                from .constants import EXIT_NORMAL, START
                map_entities = self.world.get_entities_with_components({MapComponent})
                if map_entities:
                    map_comp = map_entities[0].get_component(MapComponent)
                    tile = map_comp.tiles[player_pos.y][player_pos.x]
                    
                    if tile == EXIT_NORMAL:
                        target_level = getattr(self.world.engine, 'current_level', 1) + 1
                        self.event_manager.push(MapTransitionEvent(target_level=target_level))
                        return True
                    elif tile == START:
                        current_level = getattr(self.world.engine, 'current_level', 1)
                        if current_level > 1:
                            target_level = current_level - 1
                            self.event_manager.push(MapTransitionEvent(target_level=target_level))
                            return True
                        else:
                             self.event_manager.push(MessageEvent(_("지상으로 나가는 출구는 막혀있습니다.")))
                             return True
                        
                if found_corpse: return True
            return True
        
        # 제자리 대기 (Wait)
        if action_lower in ['.', '5', 'x', 'z']: # 대기 키 확장
            self.event_manager.push(MessageEvent(_("제자리에서 대기합니다.")))
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
            
            if not is_collision:
                collision_data = self._check_entity_collision(entity, new_x, new_y)
                if collision_data:
                    collided_id, collision_type = collision_data
                    
                    if collision_type == "SWITCH":
                        # 스위치 상호작용 (문 열기 등)
                        self.event_manager.push(InteractEvent(entity.entity_id, collided_id, "TOGGLE"))
                        is_collision = True # 상호작용 하느라 이동은 못함 (한 턴 소모)
                    else:
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
                        self.event_manager.push(MessageEvent(_("탈진하여 쓰러졌습니다! (Stamina 0)")))

                # 4. 계단 확인 (플레이어만)
                if entity.entity_id == self.world.get_player_entity().entity_id:
                    from .constants import EXIT_NORMAL, START
                    current_tile = map_component.tiles[new_y][new_x]
                    if current_tile == EXIT_NORMAL:
                        self.event_manager.push(MessageEvent(_("다음 층으로 연결되는 계단입니다. [ENTER] 키를 눌러 내려가시겠습니까?")))
                    elif current_tile == START:
                        self.event_manager.push(MessageEvent(_("이전 층으로 연결되는 계단입니다. [ENTER] 키를 눌러 올라가시겠습니까?")))

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
                                 self.event_manager.push(MessageEvent(_("숨겨진 무언가를 발견했습니다!")))

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
            and e.get_component(CorpseComponent) is None # 시체는 통과 가능
            and e.get_component(TrapComponent) is None # 함정도 통과 가능
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
            
        # 스위치(문/레버) 체크
        switch_comp = collided_entity.get_component(SwitchComponent)
        if switch_comp and not switch_comp.is_open:
            return collided_entity.entity_id, "SWITCH"
            
        # [Debug] OTHER collision identification
        col_name = self.world.engine._get_entity_name(collided_entity)
        # Fix: World.get_components doesn't exist. Use entity._components directly or iterate.
        # Entity stores components in self._components dict {Type: List[Instance]}
        comp_types = [t.__name__ for t in collided_entity._components.keys()]
        msg = f"[Debug] Collision OTHER with {col_name} (ID: {collided_entity.entity_id}, Comps: {comp_types})"
        self.event_manager.push(MessageEvent(msg, color="red"))
        logging.info(msg)
            
        return collided_entity.entity_id, "OTHER"


class MonsterAISystem(System):
    """몬스터의 행동 패턴에 따라 DesiredPositionComponent를 추가합니다."""
    _required_components: Set = {MonsterComponent, PositionComponent, AIComponent}

    def process(self):
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        player_pos = player_entity.get_component(PositionComponent)
        if not player_pos: return

        # 모든 AI 엔티티와 전투 가능 엔티티 미리 수집
        all_ai_entities = self.world.get_entities_with_components({AIComponent, PositionComponent, StatsComponent})
        all_combat_entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        
        for entity in all_ai_entities:
            # 안전장치: 플레이어는 제외
            if entity.entity_id == player_entity.entity_id: continue

            # 스턴/수면/석화 상태 확인 (TimeSystem에서 시간 감액 처리함)
            if entity.has_component(StunComponent) or entity.has_component(SleepComponent) or entity.has_component(PetrifiedComponent):
                continue
            
            ai = entity.get_component(AIComponent)
            pos = entity.get_component(PositionComponent)
            stats = entity.get_component(StatsComponent)
            if not ai or not pos or not stats: continue

            # 실시간 행동 지연(Cooldown) 확인
            current_time = time.time()
            # 몬스터는 플레이어보다 약간 느리게 설정 (기본 0.6초 지연)
            monster_delay = getattr(stats, 'action_delay', 0.6)
            if current_time - stats.last_action_time < monster_delay:
                continue
            
            # --- 타겟 선정 로직 ---
            target = None
            target_pos = None
            
            if ai.faction == "MONSTER":
                # 기본 몬스터: 플레이어 또는 PLAYER 진영 소환수 타겟팅
                # 여기서는 일단 플레이어를 우선 순위로 둠
                target = player_entity
                target_pos = player_pos
                
                # 주변에 더 가까운 PLAYER 진영 소환수가 있다면 타겟 변경 고려 (옵션)
            else:
                # 소환수 (PLAYER 진영): 가장 가까운 MONSTER 진영 엔티티 타겟팅
                enemies = [e for e in all_combat_entities if e.entity_id != entity.entity_id]
                closest_enemy = None
                min_dist = 999
                
                for e in enemies:
                    # 몬스터 컴포넌트가 있거나 AI가 MONSTER 진영인 대상
                    e_ai = e.get_component(AIComponent)
                    if (e.has_component(MonsterComponent) and (not e_ai or e_ai.faction == "MONSTER")):
                        e_pos = e.get_component(PositionComponent)
                        d = abs(e_pos.x - pos.x) + abs(e_pos.y - pos.y)
                        if d < min_dist:
                            min_dist = d
                            closest_enemy = e
                
                if closest_enemy:
                    target = closest_enemy
                    target_pos = closest_enemy.get_component(PositionComponent)
                else:
                    # 적이 없으면 플레이어를 따라다님
                    target = player_entity
                    target_pos = player_pos

            if not target or not target_pos: continue
            
            # [Fix] Friendly Fire Prevention
            # Ensure we don't target same faction (unless it's Berserk/Confused, which we don't have yet)
            if target.has_component(AIComponent):
                t_ai = target.get_component(AIComponent)
                if t_ai and t_ai.faction == ai.faction:
                    continue
            
            # 맨해튼 거리 계산
            dist = abs(target_pos.x - pos.x) + abs(target_pos.y - pos.y)

            # [Update] Check Rage Aura (Continuous Provocation) - Only for Monsters VS Player
            if ai.faction == "MONSTER" and target == player_entity:
                player_auras = player_entity.get_components(SkillEffectComponent)
                rage_aura = next((a for a in player_auras if a.name == "RAGE_AURA"), None)
                
                if rage_aura and dist <= rage_aura.radius:
                    if ai.behavior != AIComponent.CHASE:
                        ai.behavior = AIComponent.CHASE
                        self.event_manager.push(MessageEvent(_("{}가 분노에 이끌려 달려옵니다!").format(self.world.engine._get_entity_name(entity))))
            
            # 5. 행동 결정 (플래그 기반 확장)
            if "TELEPORT" in stats.flags and random.random() < 0.2:
                # 30% 확률로 타겟 근처로 순간이동
                map_ent = self.world.get_entities_with_components({MapComponent})
                if map_ent:
                    mc = map_ent[0].get_component(MapComponent)
                    tx, ty = target_pos.x + random.randint(-1, 1), target_pos.y + random.randint(-1, 1)
                    if 0 <= tx < mc.width and 0 <= ty < mc.height and mc.tiles[ty][tx] == '.':
                        pos.x, pos.y = tx, ty
                        self.event_manager.push(MessageEvent(_("{}가 갑자기 이동했습니다!").format(self.world.engine._get_entity_name(entity))))
                        stats.last_action_time = current_time
                        continue

            # [BUTCHER] "Fresh Meat" Encounter Trigger
            if "BUTCHER" in stats.flags and dist <= 10:
                if ai.behavior != AIComponent.CHASE:
                    ai.behavior = AIComponent.CHASE
                    # Play "Ah... Fresh Meat!" sound/msg only once (use detection_range as flag or add state)
                    # For simplicity, we assume encountering triggers CHASE and that's it.
                    self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _('도살자: "Ah... Fresh Meat!"') + f"{COLOR_MAP['reset']}", "red"))
            
            # [Fix] Detection Range - Monsters should only engage when player is nearby
            # This prevents invisible monsters from attacking from across the map
            detection_range = getattr(ai, 'detection_range', 10)  # Default 10 tiles
            max_chase_range = 15  # Maximum distance to chase (even in CHASE mode)
            
            # If monster is too far away (beyond max chase range), reset to STATIONARY
            if dist > max_chase_range:
                if ai.behavior == AIComponent.CHASE:
                    ai.behavior = AIComponent.STATIONARY  # Stop chasing if too far
                continue  # Skip this monster entirely
            
            # If monster is not in CHASE mode and target is out of detection range, skip
            if ai.behavior != AIComponent.CHASE and dist > detection_range:
                continue

            # [Hack & Slash] Swarm AI: Auto-chase within detection range
            if dist <= detection_range and ai.behavior not in [AIComponent.CHASE, AIComponent.FLEE]:
                ai.behavior = AIComponent.CHASE
            
            # [Hack & Slash] Alert neighbors if chasing
            if ai.behavior == AIComponent.CHASE and ai.faction == "MONSTER":
                # 30% chance per frame to alert nearby monsters
                if random.random() < 0.3:
                    nearby_monsters = [
                        m for m in all_ai_entities 
                        if m.entity_id != entity.entity_id 
                        and m.get_component(AIComponent).faction == "MONSTER"
                        and abs(m.get_component(PositionComponent).x - pos.x) + abs(m.get_component(PositionComponent).y - pos.y) <= 7
                    ]
                    for nm in nearby_monsters:
                        nm_ai = nm.get_component(AIComponent)
                        if nm_ai and nm_ai.behavior != AIComponent.CHASE:
                            nm_ai.behavior = AIComponent.CHASE

            # 탐지 범위 밖이면 무시 (단, 추적 중에는 거리 무시하고 계속 추적)
            # 소환수는 플레이어를 따라다녀야 하므로 예외
            if dist > ai.detection_range and ai.behavior != AIComponent.CHASE and ai.faction == "MONSTER":
                continue
            
            # 만약 소환수가 타겟이 없거나 너무 멀면 플레이어 옆으로 CHASE
            if ai.faction == "PLAYER" and target == player_entity and dist > 2:
                 ai.behavior = AIComponent.CHASE
            
            dx, dy = 0, 0
            
            # 공격 시야 확보 (가디언 등을 위해 distance 1 이상에서도 공격 트리거 가능하게 설계)
            if dist == 1 and ai.behavior == AIComponent.CHASE:
                # 인접한 경우 공격 시도 (이동 대신)
                combat_sys = self.world.get_system(CombatSystem)
                if combat_sys:
                    combat_sys._apply_damage(entity, target, dist)
                    stats.last_action_time = current_time
                    continue
            
            # [NEW] 원거리 공격 (가디언 또는 RANGED 플래그가 있고 사거리 내인 경우)
            if dist > 1 and dist <= ai.detection_range and ("RANGED" in stats.flags or "가디언" in getattr(entity.get_component(MonsterComponent), 'type_name', "")):
                combat_sys = self.world.get_system(CombatSystem)
                if combat_sys:
                    # [Guardian Tier 4+] Check for CopiedSkillComponent
                    from .components import CopiedSkillComponent
                    copied_skill = entity.get_component(CopiedSkillComponent)
                    
                    dx = 1 if target_pos.x > pos.x else (-1 if target_pos.x < pos.x else 0)
                    dy = 1 if target_pos.y > pos.y else (-1 if target_pos.y < pos.y else 0)
                    if dx != 0 and dy != 0: dx = 0 # 일직선 공격 우선 (단순화: 일단 4방향)

                    if copied_skill:
                        # Use Copied Skill (Cost 0 for Summon)
                        self.event_manager.push(SkillUseEvent(attacker_id=entity.entity_id, skill_name=copied_skill.skill_id, dx=dx, dy=dy, cost=0))
                        self.event_manager.push(MessageEvent(_("{}가 '{}'을(를) 모방하여 시전합니다!").format(self.world.engine._get_entity_name(entity), copied_skill.skill_name), "cyan"))
                    else:
                        # Default Behavior (Tier 1-3): Firebolt (Cost 0)
                        from .data_manager import SkillDefinition
                        # ... (SkillDefinition code is just comment/mock here, actual event uses implementation)
                        self.event_manager.push(SkillUseEvent(attacker_id=entity.entity_id, skill_name="FIREBOLT", dx=dx, dy=dy, cost=0))
                        
                    stats.last_action_time = current_time
                    continue

            if ai.behavior == AIComponent.CHASE:
                # 타겟 방향으로 이동 결정
                if target_pos.x > pos.x: dx = 1
                elif target_pos.x < pos.x: dx = -1
                elif target_pos.y > pos.y: dy = 1
                elif target_pos.y < pos.y: dy = -1
                
            elif ai.behavior == AIComponent.FLEE:
                # 타겟 반대 방향으로 이동 결정
                if target_pos.x > pos.x: dx = -1
                elif target_pos.x < pos.x: dx = 1
                elif target_pos.y > pos.y: dy = -1
                elif target_pos.y < pos.y: dy = 1
            
            if dx != 0 or dy != 0:
                if entity.has_component(DesiredPositionComponent):
                    entity.remove_component(DesiredPositionComponent)
                entity.add_component(DesiredPositionComponent(dx=dx, dy=dy))
                # 행동 수행 시간 기록
                stats.last_action_time = current_time

            # [BOSS 전용] 보스 소환 및 특수 패턴 (체력 50% 이하 시 1회 소환)
            if "BOSS" in stats.flags and stats.current_hp < stats.max_hp * 0.5:
                if not hasattr(ai, 'has_summoned') or not ai.has_summoned:
                    ai.has_summoned = True
                    
                    if "BUTCHER" in stats.flags:
                        self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("도살자가 분노하여 지원군을 부릅니다!") + f"{COLOR_MAP['reset']}", "red"))
                        # Summon Goblins as "Small Demons"
                        for _i in range(3):
                            mx, my = pos.x + random.randint(-1, 1), pos.y + random.randint(-1, 1)
                            if hasattr(self.world.engine, '_spawn_minion'):
                                self.world.engine._spawn_minion(mx, my, "GOBLIN")
                    elif "LEORIC" in stats.flags:
                        self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("해골 왕이 영원한 충성을 요구합니다!") + f"{COLOR_MAP['reset']}", "red"))
                        # Summon Skeletons
                        for _i in range(4):
                            mx, my = pos.x + random.randint(-2, 2), pos.y + random.randint(-2, 2)
                            if hasattr(self.world.engine, '_spawn_minion'):
                                self.world.engine._spawn_minion(mx, my, "SKELETON")
                    else:
                        self.event_manager.push(MessageEvent(_("{}가 지원군을 부릅니다!").format(self.world.engine._get_entity_name(entity))))
                        # 주변에 미니언 소환 (2-3마리)
                        for _i in range(random.randint(2, 3)):
                            mx, my = pos.x + random.randint(-1, 1), pos.y + random.randint(-1, 1)
                            if hasattr(self.world.engine, '_spawn_minion'):
                                self.world.engine._spawn_minion(mx, my, "GOBLIN")

            # [LEORIC] Resurrect Dead Skeletons (Every 3 seconds chance)
            if "RESURRECT" in stats.flags and random.random() < 0.1:
                # Find corpses nearby
                corpses = [e for e in self.world.get_entities_with_components({CorpseComponent, PositionComponent}) 
                           if abs(e.get_component(PositionComponent).x - pos.x) + abs(e.get_component(PositionComponent).y - pos.y) <= 5]
                if corpses:
                    corpse = random.choice(corpses)
                    c_pos = corpse.get_component(PositionComponent)
                    self.world.delete_entity(corpse.entity_id)
                    if hasattr(self.world.engine, '_spawn_minion'):
                        self.world.engine._spawn_minion(c_pos.x, c_pos.y, "SKELETON")
                        self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("해골 왕이 죽은 자를 다시 일으켜 세웁니다!") + f"{COLOR_MAP['reset']}", "red"))

            # [DIABLO] Apocalypse (Map-wide Fire Damage)
            if "APOCALYPSE" in stats.flags:
                if random.random() < 0.05: # 5% chance per tick
                    self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("디아블로가 파멸의 화염(Apocalypse)을 시전합니다!") + f"{COLOR_MAP['reset']}", "red"))
                    self.world.engine.ui.trigger_shake(5)
                    # Damage all non-Diablo entities
                for target in self.world.get_entities_with_components({StatsComponent, PositionComponent}):
                     if target.entity_id != entity.entity_id and "DIABLO" not in getattr(target.get_component(StatsComponent), 'flags', []):
                         t_stats = target.get_component(StatsComponent)
                         damage = random.randint(10, 20)
                         t_stats.current_hp -= damage
                         self.event_manager.push(MessageEvent(_("화염이 {}을 덮쳐 {}의 피해를 입혔습니다!").format(self.world.engine._get_entity_name(target), damage), "red"))
                         
                         if t_stats.current_hp <= 0:
                             combat_sys = self.world.get_system(CombatSystem)
                             if combat_sys:
                                 combat_sys._handle_death(entity, target)
                         
                         # 사망 체크
                         if t_stats.current_hp <= 0:
                             combat_sys = self.world.get_system(CombatSystem)
                             if combat_sys:
                                 combat_sys._handle_death(entity, target)


class CombatSystem(System):
    """엔티티 간 충돌 시 전투(데미지 계산)를 처리합니다."""
    def __init__(self, world):
        super().__init__(world)
        self.cooldowns = {} # Dict[entity_id, Dict[skill_name, expiry_time]]

    def get_cooldown(self, entity_id, skill_name):
        """남은 쿨타임(초)을 반환합니다."""
        import time
        if entity_id not in self.cooldowns: return 0
        if skill_name not in self.cooldowns[entity_id]: return 0
        
        expiry = self.cooldowns[entity_id][skill_name]
        remaining = expiry - time.time()
        
        if remaining <= 0:
            del self.cooldowns[entity_id][skill_name]
            return 0
        return remaining

    def set_cooldown(self, entity_id, skill_name, duration):
        """쿨타임을 설정합니다."""
        import time
        if duration <= 0: return
        
        if entity_id not in self.cooldowns:
            self.cooldowns[entity_id] = {}
        
        self.cooldowns[entity_id][skill_name] = time.time() + duration

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
        if not a_pos or not t_pos: return

        # 밀려날 방향 (공격자 -> 대상 방향 그대로)
        dx = 1 if t_pos.x > a_pos.x else (-1 if t_pos.x < a_pos.x else 0)
        dy = 1 if t_pos.y > a_pos.y else (-1 if t_pos.y < a_pos.y else 0)
        
        # Unified Logic using _handle_knockback
        self._handle_knockback(target, dx, dy, attacker=attacker)

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
        self.event_manager.push(MessageEvent(_('"{}"의 원거리 공격!').format(attacker_name)))
        self.event_manager.push(MessageEvent(f"[Debug] Range Hit: {event.range_dist}", "yellow"))

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
                time.sleep(0.08) # 80ms 대기 (User fedback: animation not visible)

            if map_comp.tiles[target_y][target_x] == '#':
                self.event_manager.push(MessageEvent(_("공격이 벽에 막혔습니다.")))
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
                # damage_factor가 있으면 적용 (기본 1.0)
                d_factor = getattr(event, 'damage_factor', 1.0)
                self._apply_damage(attacker, target, dist, damage_factor=d_factor)
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
            from .ui import COLOR_MAP
            from .constants import RARITY_COLORS, RARITY_NORMAL
            
            rarity = getattr(item, 'rarity', 'NORMAL')
            color_name = RARITY_COLORS.get(rarity, RARITY_NORMAL)
            color_code = COLOR_MAP.get(color_name, COLOR_MAP['reset'])
            
            loot_msg.append(f"{color_code}{item.name}{COLOR_MAP['reset']} x{qty}")

        if loot_msg:
            msg = ", ".join(loot_msg)
            corpse = loot_entity.get_component(CorpseComponent)
            chest = loot_entity.get_component(ChestComponent)
            
            source = "시체"
            if chest: source = "보물상자"
            elif not corpse: source = "아이템"
            elif corpse and corpse.original_name: source = f"{corpse.original_name}의 시체"
            
            translated_source = _(source) if source in ["시체", "보물상자", "아이템"] else source
            self.event_manager.push(MessageEvent(_("{source}에서 {}을(를) 획득했습니다!").format(msg, source=translated_source)))
            
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
            
            translated_source = _(source) if source in ["시체", "보물상자", "아이템"] else source
            self.event_manager.push(MessageEvent(_("{source}를 살펴봅니다... 아무것도 발견하지 못했습니다.").format(source=translated_source)))

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
        a_stats = attacker.get_component(StatsComponent)
        t_stats = target.get_component(StatsComponent)
        player_entity = self.world.get_player_entity()

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
        
        # [Modifier] Attacker Damage Bonus
        if hasattr(attacker, 'components'):
             # [Petrified] 2스택 이상: 공격력 50% 감소 (Weaken)
             p_comp = attacker.get_component(PetrifiedComponent)
             if p_comp and p_comp.stacks >= 2:
                 damage_multiplier *= 0.5

             for comp in attacker.components.values():
                 if isinstance(comp, StatModifierComponent) and hasattr(comp, 'attack_multiplier'):
                     damage_multiplier *= comp.attack_multiplier
        
        advantage_msg = ""
        
        # 상성 체크
        if ELEMENT_ADVANTAGE.get(attack_element) == defense_element:
            # 상성 우위: 데미지 +1~5%, 크리티컬 +10%
            bonus = random.uniform(0.01, 0.05)
            damage_multiplier = 1.0 + bonus
            crit_chance += 0.1
            advantage_msg = " " + _("상성 우위! +{}%").format(int(bonus*100))
        elif ELEMENT_ADVANTAGE.get(defense_element) == attack_element:
            # 상성 열위: 데미지 -1~5%, 크리티컬 -10%
            malus = random.uniform(0.01, 0.05)
            damage_multiplier = 1.0 - malus
            crit_chance -= 0.1
            advantage_msg = " " + _("상성 열위.. -{}%").format(int(malus*100))

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
            defense_mult = 1.0
            if hasattr(target, 'components'):
                 for comp in target.components.values():
                     if isinstance(comp, StatModifierComponent) and hasattr(comp, 'defense_multiplier'):
                         defense_mult *= comp.defense_multiplier
            
            d_min = getattr(t_stats, 'defense_min', t_stats.defense)
            d_max = getattr(t_stats, 'defense_max', t_stats.defense)
            target_ac = random.randint(d_min, d_max) * defense_mult
            to_hit = 50 + (a_stats.dex / 2) + (a_lv - t_lv) - target_ac
            # boundaries: 5% ~ 95%
            to_hit = max(5, min(95, to_hit))
            
            if random.random() * 100 > to_hit:
                msg = _("'{}'의 공격이 '{}'에게 빗나갔습니다! (확률: {}%)").format(attacker_name, target_name, int(to_hit))
                self.event_manager.push(MessageEvent(msg, color="dark_grey"))
                self.event_manager.push(SoundEvent("MISS"))
                # [Boss] Combat Result Event for barks
                self.event_manager.push(CombatResultEvent(attacker, target, 0, False, True, skill))
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
            msg = _("'{}'이(가) '{}'의 공격을 가뿐히 받아냈습니다!").format(target_name, attacker_name)
            self.event_manager.push(MessageEvent(msg, color="green"))
            self.event_manager.push(SoundEvent("BLOCK"))
        else:
            final_damage = max(1, final_damage) if final_damage > 0 or is_magic else 0
            
            # Determine Color
            log_color = "white"
            if skill:
                 log_color = "cyan"
            if is_critical:
                 log_color = "red"
            
            if skill:
                msg = _("'{}'의 {}! '{}'에게 {} 데미지!{}").format(attacker_name, skill.name, target_name, final_damage, advantage_msg)
            else:
                msg = _("'{}'의 공격! '{}'에게 {} 데미지!{}").format(attacker_name, target_name, final_damage, advantage_msg)
            self.event_manager.push(MessageEvent(msg, color=log_color))
            
            # [BUTCHER] Screen Shake & Bleeding Effect on Hit
            # Only if damage > 0
            if final_damage > 0:
                # [Boss] Combat Result Event for barks
                self.event_manager.push(CombatResultEvent(attacker, target, final_damage, is_critical, False, skill))
                
                attacker_is_butcher = "BUTCHER" in getattr(a_stats, 'flags', "")
                if attacker_is_butcher:
                     self.world.engine.ui.trigger_shake(2)
                     # Apply Bleeding (High chance)
                     if not target.has_component(BleedingComponent):
                         target.add_component(BleedingComponent(damage=3, duration=10, attacker_id=attacker.entity_id))
                         self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("도살자의 식칼에 베여 과다출혈이 발생합니다!") + f"{COLOR_MAP['reset']}", "red"))
                
                # [Check Weapon Flags] e.g. BLEEDING on Items (Player or Monster)
                # If attacker has BLEEDING flag (from Weapon or Monster stats)
                if "BLEEDING" in getattr(a_stats, 'flags', ""):
                     if not target.has_component(BleedingComponent):
                         target.add_component(BleedingComponent(damage=2, duration=5, attacker_id=attacker.entity_id))
                         self.event_manager.push(MessageEvent(_("{}이(가) 출혈 상태가 되었습니다!").format(target_name), "red"))

            # [Mana Shield Absorption]
            ms_comp = target.get_component(ManaShieldComponent)
            if ms_comp and t_stats.current_mp > 0:
                # MP로 흡수 (1:1 비율)
                absorb_amount = min(final_damage, int(t_stats.current_mp))
                t_stats.current_mp -= absorb_amount
                remaining_damage = final_damage - absorb_amount
                
                if absorb_amount > 0:
                    self.event_manager.push(MessageEvent(_("마법 장막이 {}의 피해를 흡수했습니다! (남은 MP: {})").format(absorb_amount, int(t_stats.current_mp)), "light_cyan"))
                
                if remaining_damage > 0:
                    t_stats.current_hp -= remaining_damage
            else:
                t_stats.current_hp -= final_damage
            
            # [HP Bar Display] Track combat for monsters
            if target.has_component(MonsterComponent) and final_damage > 0:
                import time
                from .components import CombatTrackerComponent
                
                # Add or update combat tracker
                tracker = target.get_component(CombatTrackerComponent)
                if tracker:
                    tracker.last_damaged_time = time.time()
                else:
                    target.add_component(CombatTrackerComponent(last_damaged_time=time.time()))
            
            # [Boss Overhaul] 지원군 소환 트리거 (체력 50% 이하)
            if target.has_component(MonsterComponent):
                m_comp = target.get_component(MonsterComponent)
                if "BOSS" in t_stats.flags and not getattr(m_comp, 'is_summoned', False) and not getattr(t_stats, 'has_summoned_help', False):
                    if t_stats.current_hp > 0 and t_stats.current_hp <= t_stats.max_hp / 2:
                        # 소환 로직 실행
                        self._trigger_boss_summon(attacker, target)

            # [Affix] Life Leech (생명력 흡수)
            leech_percent = getattr(a_stats, 'life_leech', 0)
            
            # [Petrified] 2스택 이상: 받는 피해 50% 증가
            t_p_comp = target.get_component(PetrifiedComponent)
            if t_p_comp and t_p_comp.stacks >= 2:
                final_damage = int(final_damage * 1.5)
            
            # [Flag Check] LIFE_STEAL (from Items or Monster Stats)
            if "LIFE_STEAL" in getattr(a_stats, 'flags', set()):
                leech_percent = max(leech_percent, 5) # Default 5% for LIFE_STEAL flag
            
            # [LEORIC] Specialized Life Steal: Melee hits leech 30%
            a_monster_id = getattr(attacker.get_component(MonsterComponent), 'monster_id', None) if attacker.has_component(MonsterComponent) else None
            # print(f"DEBUG: a_monster_id={a_monster_id}, distance={distance}, final_damage={final_damage}")
            if a_monster_id == "LEORIC" and distance <= 1:
                leech_percent = 30
            
            if leech_percent > 0 and final_damage > 0:
                print(f"DEBUG: Leeching {leech_percent}%")
                leech_amount = int(final_damage * leech_percent / 100)
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
                    self.event_manager.push(MessageEvent(_("'{}'이(가) 강력한 충격으로 경직되었습니다!").format(target_name)))
            
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
                             self.event_manager.push(MessageEvent(_("[경고] {}의 {}이(가) 파손되었습니다!").format(attacker_name, w_item.name)))
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
                             self.event_manager.push(MessageEvent(_("[경고] {}의 {}이(가) 파손되었습니다!").format(target_name, a_item.name)))
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
                   self.event_manager.push(MessageEvent(_("{}이(가) 충격으로 기절했습니다!").format(target_name)))
            
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
        

        # 3.5 주변 동료 분노 (Angry AI)
        # 플레이어가 몬스터를 공격한 경우에만 발동
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
            self.event_manager.push(MessageEvent(_("{}이(가) 공격을 받아 잠에서 깨어났습니다!").format(target_name)))

        # 4. 사망 처리
        if t_stats.current_hp <= 0:
            t_stats.current_hp = 0
            self._handle_death(attacker, target)

    def _handle_death(self, attacker: Entity | None, target: Entity):
        """사망 처리 (경험치, 드랍, 상태제거 등)"""
        t_stats = target.get_component(StatsComponent)
        if not t_stats: return

        target_name = self.world.engine._get_entity_name(target)
        self.event_manager.push(MessageEvent(_("{}이(가) 쓰러졌습니다!").format(target_name)))
        
        if target.has_component(MonsterComponent):
            m_comp = target.get_component(MonsterComponent)
            m_type = m_comp.type_name
            
            # 몬스터 사망 시 시체로 변환 (영구적 죽음)
            pos = target.get_component(PositionComponent)
            if pos:
                # 1. 전리품 및 경험치 계산을 위해 몬스터 정의 가져오기
                m_defs = self.world.engine.monster_defs if hasattr(self.world.engine, 'monster_defs') else {}
                m_def = m_defs.get(m_comp.monster_id) if m_comp.monster_id else m_defs.get(m_type)
                
                # 2. 경험치 보상 (플레이어에게)
                player_entity = self.world.get_player_entity() 
                
                # 공격자가 플레이어거나, 공격자가 없더라도(DoT 등) 플레이어가 사망 시점에 존재하면 XP 지급
                is_player_kill = player_entity and attacker and attacker.entity_id == player_entity.entity_id
                
                if player_entity and (is_player_kill or not attacker):
                    if m_def:
                        # LevelSystem을 통해 경험치 획득
                        level_sys = self.world.get_system(LevelSystem)
                        if level_sys:
                            xp_gained = int(m_def.xp_value * 0.9)
                            if xp_gained < 1: xp_gained = 1
                            
                            level_sys.gain_exp(player_entity, xp_gained)
                            self.event_manager.push(MessageEvent(_("경험치 {}를 획득했습니다.").format(xp_gained), "yellow"))
                        else:
                            logging.error("LevelSystem NOT FOUND during death handling")

                        # [Bonus Points] Boss Reward
                        if "BOSS" in getattr(m_def, 'flags', []):
                            points = 1
                            if "DIABLO" in getattr(m_def, 'flags', []):
                                points = 2
                            
                            boss_name = getattr(m_def, 'name', 'Boss')
                            if level_sys:
                                level_sys.grant_stat_points(player_entity, points, reason=f"{boss_name} 처치")
                    else:
                        logging.warning(f"m_def NOT FOUND for {m_comp.monster_id or m_type}")
                
                # 3. 컴포넌트 정리
                target.remove_component(AIComponent)
                target.remove_component(MonsterComponent)
                # StatsComponent는 시체에도 남겨둘 수 있지만, 여기선 제거 (재사용 방지) - 단, 시체 루팅 로직에서 Stats가 필요하면 유지해야 함? 
                # Corpse doesn't strictly need Stats, but removing it is safer for "death".
                target.remove_component(StatsComponent) 
                
                # [Fix] Remove all existing status effect components
                status_components = [
                    StunComponent, PoisonComponent, SleepComponent, BleedingComponent,
                    PetrifiedComponent, ManaShieldComponent, StatModifierComponent,
                    SkillEffectComponent, CombatTrackerComponent, HitFlashComponent
                ]
                for comp_type in status_components:
                    target.remove_component(comp_type)

                # [Boss] Handle Boss Death Patterns
                boss_comp = target.get_component(BossComponent)
                if boss_comp:
                    boss_id = boss_comp.boss_id
                    self.world.engine.last_boss_id = boss_id
                    pattern = self.world.engine.boss_patterns.get(boss_id)
                    if pattern:
                        # Death Bark
                        death_bark = pattern.get("death_bark")
                        if death_bark:
                            from .events import BossBarkEvent
                            self.event_manager.push(BossBarkEvent(target, "DEATH", death_bark))
                        
                        # Prepare Boss Loot from Pattern
                        if pattern.get("loot_table"):
                            from . import config
                            bg_min = getattr(config, 'BOSS_GOLD_MIN', 1000)
                            bg_max = getattr(config, 'BOSS_GOLD_MAX', 3000)
                            
                            if not target.has_component(LootComponent):
                                target.add_component(LootComponent(gold=random.randint(bg_min, bg_max)))
                            loot = target.get_component(LootComponent)
                            if loot.gold == 0: loot.gold = random.randint(bg_min, bg_max) # Ensure boss has gold
                            for item_name, chance in pattern["loot_table"].items():
                                if random.random() < chance:
                                    item_def = self.world.engine.item_defs.get(item_name)
                                    if item_def:
                                        loot.items.append({"item": item_def, "qty": 1})
                                        self.event_manager.push(MessageEvent(_("{}의 전리품: {}이(가) 떨어졌습니다!").format(boss_id, item_name), "gold"))

                    # [Boss Gate]
                    map_ents = self.world.get_entities_with_components({MapComponent, BossGateComponent})
                    if map_ents:
                        map_ent = map_ents[0]
                        map_comp = map_ent.get_component(MapComponent)
                        boss_gate = map_ent.get_component(BossGateComponent)
                        
                        if not boss_gate.stairs_spawned:
                            boss_gate.stairs_spawned = True
                            d_map = getattr(self.world.engine, 'dungeon_map', None)
                            if d_map:
                                ex, ey = d_map.exit_x, d_map.exit_y
                                if 0 <= ex < map_comp.width and 0 <= ey < map_comp.height:
                                    from .constants import EXIT_NORMAL
                                    map_comp.tiles[ey][ex] = EXIT_NORMAL
                                    
                                    region = boss_gate.next_region_name
                                    if region == "승리":
                                            self.event_manager.push(MessageEvent(_("!!! 던전을 정복했습니다 !!!"), "gold"))
                                    else:
                                            self.event_manager.push(MessageEvent(_("!!! {}(으)로 가는 계단이 나타났습니다 !!!").format(region), "light_cyan"))
                                    
                                    self.event_manager.push(SoundEvent("LEVEL_UP"))

                # 4. 시체 컴포넌트 추가
                target.add_component(CorpseComponent(original_name=target_name))
                render = target.get_component(RenderComponent)
                if render:
                    render.char = '%'
                    render.color = 'dark_grey'
                    render.z_index = 0

                # 5. 아이템 드랍 (Loot)
                if not target.has_component(LootComponent):
                    loot_items = []
                    dungeon = getattr(self.world.engine, 'dungeon', None)
                    if dungeon:
                        floor = dungeon.dungeon_level_tuple[0]
                    else:
                        floor = getattr(self.world.engine, 'current_level', 1)
                    eligible = self.world.engine._get_eligible_items(floor)
                    
                    from . import config
                    
                    drop_chance = 0.0
                    loot_ranges = getattr(config, 'LOOT_DROP_CHANCE', [])
                    for limit, min_c, max_c in loot_ranges:
                        if floor <= limit:
                            drop_chance = random.uniform(min_c, max_c)
                            break
                    
                    is_boss = (m_def and 'BOSS' in m_def.flags) or boss_comp is not None
                    if is_boss:
                        drop_chance = getattr(config, 'BOSS_DROP_CHANCE', 1.0)
                    
                    num_drops = 0
                    if eligible and random.random() < drop_chance:
                        if is_boss:
                            b_min = getattr(config, 'BOSS_DROP_COUNT_MIN', 5)
                            b_max = getattr(config, 'BOSS_DROP_COUNT_MAX', 10)
                            num_drops = random.randint(b_min, b_max)
                        else:
                            lucky_chance = getattr(config, 'NORMAL_DROP_LUCKY_CHANCE', 0.2)
                            if random.random() < lucky_chance:
                                n_min = getattr(config, 'NORMAL_DROP_LUCKY_MIN', 3)
                                n_max = getattr(config, 'NORMAL_DROP_LUCKY_MAX', 5)
                                num_drops = random.randint(n_min, n_max)
                            else:
                                n_min = getattr(config, 'NORMAL_DROP_COUNT_MIN', 1)
                                n_max = getattr(config, 'NORMAL_DROP_COUNT_MAX', 3)
                                num_drops = random.randint(n_min, n_max)
                    
                    for _i in range(num_drops):
                        item = random.choice(eligible)
                        if not item: continue
                        
                        player_mf = 0
                        if player_entity:
                            p_stats = player_entity.get_component(StatsComponent)
                            if p_stats:
                                player_mf += p_stats.magic_find
                            p_inv = player_entity.get_component(InventoryComponent)
                            if p_inv:
                                for eq_item in p_inv.equipped.values():
                                    if eq_item:
                                        player_mf += getattr(eq_item, 'magic_find', 0)
                        
                        rarity = self.world.engine._get_rarity(floor, magic_find=player_mf)
                        if rarity == "MAGIC" or rarity == "UNIQUE":
                            prefix_id, suffix_id = self.world.engine._roll_magic_affixes(item.type, floor)
                            if prefix_id or suffix_id:
                                affixed = self.world.engine._create_item_with_affix(item.name, prefix_id, suffix_id, floor)
                                if affixed: item = affixed
                                
                        is_essential = "IDENTIFY" in getattr(item, 'flags', []) or getattr(item, 'type', '') == "CURRENCY"
                        if not is_essential and getattr(item, 'is_identified', True) and random.random() < 0.2:
                            item.is_identified = False

                        loot_items.append({'item': item, 'qty': 1})
                    
                    # Gold Drop (Guaranteed + Floor Scaling)
                    # Gold Drop (Guaranteed + Floor Scaling)
                    from . import config
                    g_base = getattr(config, 'GOLD_DROP_BASE', 10)
                    g_scale = getattr(config, 'GOLD_DROP_SCALING', 5)
                    g_var = getattr(config, 'GOLD_VARIANCE', 2.0)
                    
                    base_gold = g_base + (floor * g_scale)
                    random_gold = random.randint(base_gold, int(base_gold * g_var))
                    target.add_component(LootComponent(items=loot_items, gold=random_gold))
                    
                    # [Visual] Set corpse color based on loot
                    if render:
                        from .constants import RARITY_COLORS
                        max_rarity_val = 0
                        rarity_map = {"NORMAL": 1, "MAGIC": 2, "UNIQUE": 3}
                        best_rarity = "NORMAL"
                        has_items = False
                        for li in loot_items:
                            item_obj = li['item']
                            has_items = True
                            r = getattr(item_obj, 'rarity', 'NORMAL')
                            val = rarity_map.get(r, 0)
                            if val > max_rarity_val:
                                max_rarity_val = val
                                best_rarity = r
                        
                        if has_items:
                            render.color = RARITY_COLORS.get(best_rarity, 'white')
                        else:
                            render.color = 'dark_grey'

        elif target.entity_id == self.world.get_player_entity().entity_id:
            # 플레이어 사망
            self.event_manager.push(MessageEvent(f"{COLOR_MAP['red']}" + _("당신은 죽었습니다...") + f"{COLOR_MAP['reset']}", "red"))

    def _trigger_boss_summon(self, attacker: Entity, target: Entity, specific_boss_id: str = None):
        """보스의 체력이 낮아지면 지원군을 소환합니다. specific_boss_id가 있으면 해당 보스 소환."""
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
        self.event_manager.push(MessageEvent(_("'{}'이(가) 강력한 포효와 함께 지원군을 부릅니다!").format(target_name)))
        self.event_manager.push(SoundEvent("BOSS_ROAR"))
        
        engine = self.world.engine
        
        spawn_id = None
        if specific_boss_id:
            spawn_id = specific_boss_id
        elif boss_id == "DIABLO":
            # 디아블로는 외부 로직에서 specific_boss_id를 넘겨주므로 이 분기엔 잘 안 옴
            # Default fallback: random previous boss?
            pass
        else:
            # 이전 보스 1마리 소환 (기존 로직)
            idx = BOSS_SEQUENCE.index(boss_id)
            if idx > 0:
                spawn_id = BOSS_SEQUENCE[idx - 1]
        
        if spawn_id:
            tx, ty = self._find_spawn_pos(t_pos.x, t_pos.y)
            engine._spawn_boss(tx, ty, boss_name=spawn_id, is_summoned=True)
            self.event_manager.push(MessageEvent(_("!!! {}이(가) {}의 환영을 불러냅니다! !!!").format(boss_id, spawn_id), "purple"))

    def _find_spawn_pos(self, x, y):
        """주변 빈 공간을 찾습니다."""
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not map_ent: return x, y
        mc = map_ent[0].get_component(MapComponent)
        
        for _i in range(15): # 15번 시도
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
        
        if target.has_component(ShrineComponent) and attacker.entity_id == self.world.get_player_entity().entity_id:
            shrine_comp = target.get_component(ShrineComponent)
            if not shrine_comp.is_used:
                from .events import ShrineOpenEvent
                self.event_manager.push(ShrineOpenEvent(shrine_id=target.entity_id))
            return

        # [Fix] Friendly Fire Prevention (Collision Based)
        # If both are Monsters (same faction), do not attack on collision (just block)
        if attacker.has_component(AIComponent) and target.has_component(AIComponent):
             a_ai = attacker.get_component(AIComponent)
             t_ai = target.get_component(AIComponent)
             if a_ai and t_ai and a_ai.faction == t_ai.faction:
                 return

        if not target.has_component(ShopComponent):
            # 상인이 아니면 공격 소리 발생
            self.event_manager.push(SoundEvent("ATTACK"))
            
        self._apply_damage(attacker, target, distance=1)

    def handle_skill_use_event(self, event: SkillUseEvent):
        """스킬 사용 로직 처리"""
        attacker = self.world.get_entity(event.attacker_id)
        if not attacker: return
        
        # [Cooldown Check] Global check before any specific logic
        # Charge/Repair are special cases, but can still respect cooldown if needed.
        # Here we only check generic cooldown if set.
        if self.get_cooldown(attacker.entity_id, event.skill_name) > 0:
            remaining = int(self.get_cooldown(attacker.entity_id, event.skill_name)) + 1
            self.event_manager.push(MessageEvent(_("기술이 준비되지 않았습니다! ({}초)").format(remaining), "white"))
            return
        
        # [Charge Skill] 특별 처리
        if event.skill_name == "Charge" or event.skill_name == "차지":
             inv = attacker.get_component(InventoryComponent)
             known_skills = list(inv.skill_levels.keys()) if inv else []
             
             # Show UI
             if hasattr(self.world.engine, 'ui'):
                 selected_skill = self.world.engine.ui.show_skill_selection_menu(known_skills, self.world.engine._render)
                 
                 if selected_skill:
                     # Add ChargeComponent
                     # 기존 차지 제거 (덮어쓰기)
                     if attacker.has_component(ChargeComponent):
                         attacker.remove_component(ChargeComponent)
                     
                     attacker.add_component(ChargeComponent(selected_skill))
                     self.event_manager.push(MessageEvent(_("지팡이에 '{}' 마력을 충전했습니다!").format(selected_skill), "cyan"))
                     self.event_manager.push(MessageEvent(_("충전을 취소했습니다.")))
             return

        # [Repair Skill] 특별 처리
        if event.skill_name == "Repair" or event.skill_name == "수리":
            inv = attacker.get_component(InventoryComponent)
            if not inv: 
                self.event_manager.push(MessageEvent(_("수리할 장비가 없습니다.")))
                return

            # 내구도가 감소된 아이템 찾기 (착용 중 + 인벤토리)
            repairable_items = []
            
            # 1. Equipped
            for slot, item in inv.equipped.items():
                if item:
                    max_d = getattr(item, 'max_durability', 0)
                    curr_d = getattr(item, 'current_durability', 0)
                    if max_d > 0 and curr_d < max_d:
                        repairable_items.append(item)
            # ... (Rest of Repair Logic) ...
            # Repair logic continues and returns. If we want CD for Repair, we must add it there. 
            # For now, skipping CD set for Repair as it consumes items usually?
            # Actually, let's keep it simple.

        # (Existing Code)
            
            # 2. Inventory
            for key, entry in inv.items.items():
                item = entry['item']
                max_d = getattr(item, 'max_durability', 0)
                curr_d = getattr(item, 'current_durability', 0)
                if max_d > 0 and curr_d < max_d:
                    if item not in repairable_items: # 중복 방지
                        repairable_items.append(item)
            
            if not repairable_items:
                self.event_manager.push(MessageEvent(_("수리가 필요한 아이템이 없습니다."), "yellow"))
                return

            # Show UI
            if hasattr(self.world.engine, 'ui'):
                selected_item = self.world.engine.ui.show_repair_menu(repairable_items, self.world.engine._render)
                
                if selected_item:
                    # Repair Attempt (60% Chance)
                    import random
                    if random.random() < 0.6:
                        # Success
                        selected_item.current_durability = selected_item.max_durability
                        self.event_manager.push(MessageEvent(_("'{}' 수리에 성공했습니다!").format(selected_item.name), "green"))
                        self.event_manager.push(SoundEvent("LEVEL_UP")) # 긍정적 효과음
                    else:
                        # Fail
                        self.event_manager.push(MessageEvent(_("'{}' 수리에 실패했습니다...").format(selected_item.name), "red"))
                        # 페널티는 현재 턴 소모 뿐
                else:
                    self.event_manager.push(MessageEvent(_("수리를 취소했습니다.")))
            return

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
                self.event_manager.push(MessageEvent(_("알 수 없는 스킬입니다: {}").format(event.skill_name)))
                return

        if not skill:
            return

        # 레벨 제한 확인
        level_comp = attacker.get_component(LevelComponent)
        req_level = getattr(skill, 'required_level', 1)
        if level_comp and req_level > level_comp.level:
            self.event_manager.push(MessageEvent(_("아직 이 기술을 사용할 수 없습니다. (필요: Lv.{})").format(req_level)))
            return

        # 스킬 플래그 가져오기
        s_flags = getattr(skill, 'flags', set())

        # [Check] 스킬 레벨 가져오기 (비용 및 효율 계산을 위해 위로 이동)
        inv = attacker.get_component(InventoryComponent)
        skill_level = 1
        if inv:
            if skill.name in inv.skill_levels:
                skill_level = inv.skill_levels[skill.name]
            else:
                # 베이스 네임으로 재시도 (LvX 제거된 이름)
                import re
                base_name = re.sub(r' Lv\d+', '', skill.name)
                skill_level = inv.skill_levels.get(base_name, 1)

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
                        # [Class Bonus] Sorcerer Efficiency: Higher skill level = Chance to save charge
                        # Chance: 2% per skill level (Max 50% at Lv.25)
                        savings_chance = min(0.50, skill_level * 0.02)
                        
                        if random.random() < savings_chance:
                            # Charge Saved!
                            used_charge = True
                            resource_used = f"STAFF CHARGE SAVED ({staff.current_charges}/{staff.max_charges})"
                            self.event_manager.push(MessageEvent(_("숙련된 마법 시전으로 지팡이 마력을 보존했습니다! (확률: {}%)").format(int(savings_chance*100)), "light_blue"))
                        else:
                            # Charge Consumed
                            staff.current_charges -= 1
                            used_charge = True
                            resource_used = f"STAFF CHARGE -1 ({staff.current_charges}/{staff.max_charges})"
                            self.event_manager.push(MessageEvent(_("지팡이의 마력을 사용하여 정신력을 보존했습니다! (남은 충전: {})").format(staff.current_charges)))

        # 자원 소모 로직 (플래그 우선 -> 기존 cost_type 폴백)

        # 자원 소모 로직 (플래그 우선 -> 기존 cost_type 폴백)
        cost_val = skill.cost_value
        
        # [Override] Event에서 cost를 지정했다면 (예: Charge Skill Release = 0)
        if hasattr(event, 'cost') and event.cost is not None:
            cost_val = event.cost
        
        # [Update] MP Cost Scaling: +1.5 per level
        # Goal: At Lv.255, Cost ~391 (Max MP ~812 naked Barb). 2 Uses -> Remainder ~30.
        mp_scaling = ("COST_MP" in s_flags or (hasattr(skill, 'cost_type') and skill.cost_type == "MP"))
        if mp_scaling:
            cost_val += int((skill_level - 1) * 1.5)

        resource_used = ""
        
        if not used_charge:
            if "COST_HP" in s_flags:
                if a_stats.current_hp <= cost_val:
                    self.event_manager.push(MessageEvent(_("체력이 부족합니다!")))
                    return
                a_stats.current_hp -= cost_val
                resource_used = f"HP -{cost_val}"
            elif "COST_STM" in s_flags or (hasattr(skill, 'cost_type') and skill.cost_type == "STAMINA"):
                # [Balance] STM 삭제 -> HP + MP 소모로 변경
                hp_cost = int(cost_val * 0.5) # 절반은 HP
                mp_cost = int(cost_val * 0.5) # 절반은 MP
                if hp_cost < 1: hp_cost = 1
                if mp_cost < 1: mp_cost = 1
                
                if a_stats.current_hp <= hp_cost:
                    self.event_manager.push(MessageEvent(_("체력이 부족하여 기술을 사용할 수 없습니다!")))
                    return
                if a_stats.current_mp < mp_cost:
                    self.event_manager.push(MessageEvent(_("마력이 부족하여 기술을 사용할 수 없습니다!")))
                    return
                    
                a_stats.current_hp -= hp_cost
                a_stats.current_mp -= mp_cost
                resource_used = f"HP -{hp_cost}, MP -{mp_cost}"
            elif "COST_MP" in s_flags or (hasattr(skill, 'cost_type') and skill.cost_type == "MP"):
                if a_stats.current_mp < cost_val:
                    self.event_manager.push(MessageEvent(_("마력이 부족하여 기술을 사용할 수 없습니다!")))
                    return
                a_stats.current_mp -= cost_val
                resource_used = f"MP -{cost_val}"

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
            self.event_manager.push(MessageEvent(_("{}의 효과로 능력이 향상되었습니다!").format(skill.name)))

        # [Clean] 스킬 레벨은 위에서 이미 계산됨 (skill_level)
        # inv 변수도 위에서 이미 할당됨
        
        # 레벨 기반 스케일링
        if "RAGE" == getattr(skill, 'id', '') or "레이지" == skill.name:
            # [Adjust] Rage Flip-Flop Scaling
            # Level 1 increment (Lv2): Range +1
            # Level 2 increment (Lv3): Duration +0.5s
            # Range: Base 15 + (Lv // 2)
            scaled_range = skill.range + (skill_level // 2)
            # Duration: Base 5.0 + ((Lv - 1) // 2) * 0.5
            scaled_duration = getattr(skill, 'duration', 5.0) + ((skill_level - 1) // 2) * 0.5
            scaled_damage = skill.damage # No damage scaling for Rage buff
            
        elif "SCALABLE" in getattr(skill, 'flags', set()):
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
        
        # [Cooldown Set]
        # Use cooldown from skill definition, default 0
        cooldown_val = getattr(skill, 'cooldown', 0.0)
        # [Balance] Optional: Min cooldown for powerful skills?
        # For now, trust the data.
        if cooldown_val > 0:
            self.set_cooldown(attacker.entity_id, skill.name, cooldown_val)

        self.event_manager.push(MessageEvent(_("'{}' 발동! (Lv.{}, {})").format(effective_skill.name, skill_level, resource_used)))

        # 스킬 타입별 처리 (플래그 기반)
        if "PROJECTILE" in effective_skill.flags or effective_skill.subtype == "PROJECTILE":
            self._handle_projectile_skill(attacker, effective_skill, event.dx, event.dy)
        elif "AREA" in effective_skill.flags or effective_skill.subtype == "AREA":
            self._handle_area_skill(attacker, effective_skill)
        elif ("AURA" in effective_skill.flags or effective_skill.subtype == "SELF" and "STUN" in effective_skill.flags) and effective_skill.duration > 0:
            # 지속형 오라 효과 (예: 휠 윈드)
            attacker.add_component(SkillEffectComponent(
                name=effective_skill.name,
                duration=effective_skill.duration,
                damage=effective_skill.damage,
                radius=effective_skill.range,
                flags=effective_skill.flags
            ))
        elif effective_skill.id == "MANA_SHIELD" or effective_skill.name == "마나 실드":
            # 마나 실드 컴포넌트 추가/갱신
            attacker.add_component(ManaShieldComponent(duration=effective_skill.duration))
            self.event_manager.push(MessageEvent(_("마법 장막이 생겨나 데미지를 마나로 흡수합니다! (지속 {}초)").format(int(effective_skill.duration)), "light_cyan"))
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
            elif "MOVING_WALL" in skill.flags: # 전진하는 벽 (화염 파도 등)
                if dx != 0: positions = [(tx, ty - 1), (tx, ty), (tx, ty + 1)]
                else: positions = [(tx - 1, ty), (tx, ty), (tx + 1, ty)]
            else: # 일반
                positions = [(tx, ty)]

            # 유효한 위치만 필터링 (벽 체크 등)
            valid_positions = []
            for px, py in positions:
                if (0 <= px < map_comp.width and 0 <= py < map_comp.height) and map_comp.tiles[py][px] != '#':
                    valid_positions.append((px, py))
            
            if not valid_positions: # 벽이나 맵 경계에 막히면 종료
                break
            
            # [Teleport Hook] 마지막 유효 좌표 저장 (텔레포트 스킬용)
            last_tx, last_ty = tx, ty
            
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

                # [Animation] Render frame immediately to show projectile moving
                if hasattr(self.world, 'engine'):
                    self.world.engine._render()
                    import time
                    time.sleep(0.03) # Adjust speed as needed

                # [NEW] Inferno: 투사체가 지나간 자리에 지속 화염 장판 생성
                if skill.id == "INFERNO" or skill.name == "인페르노":
                    # 해당 위치에 5초 동안 지속되는 화염 오라 생성
                    fire_aura = self.world.create_entity()
                    self.world.add_component(fire_aura.entity_id, PositionComponent(x=px, y=py))
                    self.world.add_component(fire_aura.entity_id, SkillEffectComponent(
                        name="FIRE_TRAIL", duration=5.0, damage=skill.damage // 2, radius=0
                    ))
                    self.world.add_component(fire_aura.entity_id, RenderComponent(char='*', color='red'))
                    self.world.add_component(fire_aura.entity_id, EffectComponent(duration=5.0))

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
                    
                    for target in targets:
                        # [NEW] Holy Bolt: 언데드만 타격
                        if skill.id == "HOLY_BOLT" or skill.name == "홀리 볼트":
                            sc = target.get_component(StatsComponent)
                            if not sc or "UNDEAD" not in getattr(sc, 'flags', []):
                                continue # 언데드가 아니면 무시 (통과)

                        # [NEW] Stone Curse: 석화 효과 부여
                        if skill.id == "STONE_CURSE" or skill.name == "석화 저주":
                            self._handle_status_effect(target, "STONE_CURSE", duration=skill.duration)
                            # 석화는 데미지를 주지 않을 수도 있음 (기획에 따라 다름)
                            # 일단 데미지 팩터를 0으로 주거나 정해진 데미지 적용
                            if skill.damage > 0:
                                self._apply_skill_damage(attacker, target, skill, dx, dy, damage_factor=1.0)
                        else:
                            self._apply_skill_damage(attacker, target, skill, dx, dy, damage_factor=1.0)
                            
                        hit_target = True
                        
                        # [NEW] 체인 라이트닝 처리
                        if "CHAIN" in skill.flags:
                            self._handle_chain_lightning(attacker, target, skill, depth=1, hit_targets={target.entity_id})
                    
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

        # [NEW] TELEPORT 스킬 처리
        if "TELEPORT" in skill.flags or skill.id == "TELEPORT" or skill.name == "텔레포트":
            # 투사체가 도달한 마지막 유효 좌표 확인
            if 'last_tx' in locals() and 'last_ty' in locals():
                target_x, target_y = last_tx, last_ty
                
                pos = attacker.get_component(PositionComponent)
                if pos:
                    pos.x, pos.y = target_x, target_y
                    self.event_manager.push(MessageEvent(_("차원 문을 통해 이동했습니다! ({}, {})").format(target_x, target_y), "cyan"))
                    self.event_manager.push(SoundEvent("TELEPORT"))
                    if hasattr(self.world.engine, '_render'):
                        self.world.engine._render()

    def _handle_chain_lightning(self, attacker, last_target, skill, depth, hit_targets=None):
        """연쇄 번개: 적중한 대상 주변의 다른 적에게 전이"""
        if depth >= 5: # 최대 5번 전이
            return
            
        if hit_targets is None:
            hit_targets = {last_target.entity_id}
        else:
            hit_targets.add(last_target.entity_id)
            
        l_pos = last_target.get_component(PositionComponent)
        if not l_pos: return
        
        # 주변 적 탐색 (사거리 3 이내)
        targets = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        candidates = []
        for t in targets:
            # 시전자, 현재 타겟, 그리고 이미 맞은 타겟 제외
            if t.entity_id == attacker.entity_id or t.entity_id in hit_targets:
                continue
            t_pos = t.get_component(PositionComponent)
            dist = abs(t_pos.x - l_pos.x) + abs(t_pos.y - l_pos.y)
            if dist <= 3:
                candidates.append((dist, t.entity_id, t))
        
        if not candidates:
            return
            
        # 가장 가까운 적 선택
        candidates.sort()
        next_dist, _i, next_target = candidates[0]
        nt_pos = next_target.get_component(PositionComponent)
        
        # 시각적 이펙트 (직선 연결)
        steps = max(abs(nt_pos.x - l_pos.x), abs(nt_pos.y - l_pos.y))
        for s in range(1, steps + 1):
            tx = l_pos.x + int((nt_pos.x - l_pos.x) * s / steps)
            ty = l_pos.y + int((nt_pos.y - l_pos.y) * s / steps)
            e_id = self.world.create_entity().entity_id
            self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
            self.world.add_component(e_id, RenderComponent(char='+', color='light_blue'))
            self.world.add_component(e_id, EffectComponent(duration=0.1))
            
        if hasattr(self.world.engine, '_render'):
            self.world.engine._render()
            time.sleep(0.04)
            
        # 데미지 적용 (전이될 때마다 20%씩 감소)
        factor = 0.8 ** depth
        self._apply_skill_damage(attacker, next_target, skill, 0, 0, damage_factor=factor)
        
        # 다음 전이
        self._handle_chain_lightning(attacker, next_target, skill, depth + 1, hit_targets)

    def _handle_explosion(self, attacker, cx, cy, skill):
        """폭발 효과: 지정된 좌표 주변 8방향(3x3)에 피해 및 이펙트 생성"""
        
        self.event_manager.push(MessageEvent(_("!!! '{}' 폭발 !!!").format(skill.name)))
        
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx, ty = cx + dx, cy + dy
                
                # 시각적 이펙트 (폭발 느낌)
                e_id = self.world.create_entity().entity_id
                self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
                self.world.add_component(e_id, RenderComponent(char='#', color='yellow'))
                self.world.add_component(e_id, EffectComponent(duration=0.2))
                
                # 범위 내 모든 엔티티 피해 적용 (시전자 제외)
                targets = [
                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                    if e.get_component(PositionComponent).x == tx 
                    and e.get_component(PositionComponent).y == ty
                    and e.entity_id != attacker.entity_id
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
        if skill.id == "REPAIR" or skill.name == "수리":
            # 무기 및 방어구 내구도 회복
            inv = attacker.get_component(InventoryComponent)
            if inv:
                repaired = False
                for part in ["손1", "손2", "머리", "몸통", "신발", "장갑"]:
                    item = inv.equipped.get(part)
                    if item and hasattr(item, 'current_durability') and hasattr(item, 'max_durability'):
                        if item.current_durability < item.max_durability:
                            # 레벨당 더 많이 회복? (기본 20% 회복으로 가정)
                            recovery = int(item.max_durability * 0.2)
                            old_dur = item.current_durability
                            item.current_durability = min(item.max_durability, item.current_durability + recovery)
                            if item.current_durability > old_dur:
                                repaired = True
                                self.event_manager.push(MessageEvent(_("[{}]의 내구도를 {} 회복했습니다.").format(item.name, item.current_durability - old_dur)))
                if not repaired:
                    self.event_manager.push(MessageEvent(_("수리할 장비가 없습니다.")))
                else:
                    self.event_manager.push(SoundEvent("REPAIR"))

        elif skill.id == "DISARM" or skill.name == "함정 해제":
            # 주변 함정 제거
            pos = attacker.get_component(PositionComponent)
            inv = attacker.get_component(InventoryComponent)
            
            if pos and inv:
                skill_name = skill.name if skill.name else "함정 해제"
                level = inv.skill_levels.get(skill_name, 1)
                
                # 1~10레벨 기준으로 선형 스케일링 (10레벨 이상은 최대치 고정)
                clamped_lv = max(1, min(10, level))
                
                # 성공 확률: 1레벨(80%) ~ 10레벨(95%)
                success_rate = 0.80 + (clamped_lv - 1) * (0.15 / 9.0)
                # 데미지 감쇄: 1레벨(10%) ~ 10레벨(50%)
                mitigation = 0.10 + (clamped_lv - 1) * (0.40 / 9.0)
                
                trap_entities = self.world.get_entities_with_components({TrapComponent, PositionComponent})
                removed_count = 0
                triggered_count = 0
                
                # TrapSystem 참조 가져오기 (원격 발동 및 발사체 발동용)
                from .trap_manager import TrapSystem
                trap_system = self.world.get_system(TrapSystem)
                
                # 주변 3x3 범위 함정 확인
                for trap_ent in list(trap_entities):
                    t_pos = trap_ent.get_component(PositionComponent)
                    if abs(t_pos.x - pos.x) <= 2 and abs(t_pos.y - pos.y) <= 2:
                        # 확률 체크
                        if random.random() < success_rate:
                            # 성공: 함정 안전 제거
                            self.world.delete_entity(trap_ent.entity_id)
                            removed_count += 1
                        else:
                            # 실패: 함정 발동 (감쇄된 데미지)
                            triggered_count += 1
                            if trap_system:
                                tc = trap_ent.get_component(TrapComponent)
                                if tc.trigger_type == "PROXIMITY":
                                    trap_system._fire_projectile(trap_ent, attacker, damage_multiplier=(1.0 - mitigation))
                                else:
                                    trap_system._trigger_trap(attacker, trap_ent, damage_multiplier=(1.0 - mitigation))
                            else:
                                # fallback: 그냥 제거
                                self.world.delete_entity(trap_ent.entity_id)
                
                if removed_count > 0 or triggered_count > 0:
                    if removed_count > 0:
                        # 경험치 지급 (함정당 5~15 XP)
                        total_xp = removed_count * random.randint(5, 15)
                        level_comp = attacker.get_component(LevelComponent)
                        if level_comp:
                            level_comp.exp += total_xp
                        
                        # 아이템 수거 확률 (30% 확률로 화살 또는 기계 부품)
                        loot_msg = ""
                        if random.random() < 0.3:
                            from .data_manager import load_item_definitions
                            item_defs = load_item_definitions()
                            loot_id = random.choice(["화살", "기계 부품"])
                            loot_def = next((d for d in item_defs.values() if d.name == loot_id), None)
                            
                            if loot_def:
                                inv.add_item(loot_def, 1)
                                loot_msg = f" (수거: {loot_id})"
                        
                        self.event_manager.push(MessageEvent(_("함정 {}개를 안전하게 해제했습니다! (+{}XP){}(성공률 {}%)").format(removed_count, total_xp, loot_msg, int(success_rate*100)), "green"))
                    
                    if triggered_count > 0:
                        self.event_manager.push(MessageEvent(_("해제에 실패하여 함정 {}개가 발동되었습니다! (피해 감쇄 {}%)").format(triggered_count, int(mitigation*100)), "yellow"))
                    
                    self.event_manager.push(SoundEvent("UNLOCK"))
                else:
                    self.event_manager.push(MessageEvent(_("주변에 해제할 함정이 발견되지 않았습니다."), "white"))

        elif skill.id == "RECHARGE" or skill.name == "충전":
            # 지팡이 차지 회복
            inv = attacker.get_component(InventoryComponent)
            if inv:
                staff = inv.equipped.get("손1")
                from .data_manager import ItemDefinition
                if staff and isinstance(staff, ItemDefinition) and hasattr(staff, 'current_charges'):
                    if staff.current_charges < staff.max_charges:
                        # 지팡이 차지 회복 (최대치의 30% 또는 3회)
                        recovery = max(3, int(staff.max_charges * 0.3))
                        old_chg = staff.current_charges
                        staff.current_charges = min(staff.max_charges, staff.current_charges + recovery)
                        self.event_manager.push(MessageEvent(_("지팡이에 마력을 {}회 충전했습니다! ({}/{})").format(staff.current_charges - old_chg, staff.current_charges, staff.max_charges), "blue"))
                        self.event_manager.push(SoundEvent("CHARGE"))
                    else:
                        self.event_manager.push(MessageEvent(_("지팡이의 마력이 이미 가득 차 있습니다.")))
                else:
                    self.event_manager.push(MessageEvent(_("마력을 충전할 지팡이를 들고 있지 않습니다.")))
        
        elif skill.id == "PHASING" or skill.name == "페이징" or "TELEPORT_RANDOM" in getattr(skill, 'flags', set()):
            # 랜덤 텔레포트
            map_entities = self.world.get_entities_with_components({MapComponent})
            if map_entities:
                map_comp = map_entities[0].get_component(MapComponent)
                floor_tiles = []
                for y in range(map_comp.height):
                    for x in range(map_comp.width):
                        if map_comp.tiles[y][x] == '.':
                            # 현재 위치 제외
                            pos = attacker.get_component(PositionComponent)
                            if pos and (pos.x != x or pos.y != y):
                                floor_tiles.append((x, y))
                
                if floor_tiles:
                    tx, ty = random.choice(floor_tiles)
                    pos = attacker.get_component(PositionComponent)
                    if pos:
                        pos.x, pos.y = tx, ty
                        self.event_manager.push(MessageEvent(_("시공간이 뒤틀리며 무작위 위치로 이동했습니다! ({}, {})").format(tx, ty), "cyan"))
                        self.event_manager.push(SoundEvent("TELEPORT"))
                        if hasattr(self.world.engine, '_render'):
                            self.world.engine._render()
                else:
                    self.event_manager.push(MessageEvent(_("이동할 수 있는 빈 공간이 없습니다.")))

            stats = attacker.get_component(StatsComponent)
            old_hp = stats.current_hp
            heal_amount = getattr(skill, 'damage', 10)
            stats.current_hp = min(stats.max_hp, stats.current_hp + heal_amount)
            recovered = stats.current_hp - old_hp
            
            self.event_manager.push(MessageEvent(_("체력을 {} 회복했습니다!").format(recovered)))
        
        elif skill.type == "BUFF":
            if skill.id == "RAGE":
                # 1. Duration (Already scaled by Skill Level in handle_skill_use_event)
                duration = getattr(skill, 'duration', 5)
                
                # 2. Add Buff (Stat Modifier)
                mod = StatModifierComponent(duration=duration, source=skill.name)
                mod.attack_multiplier = 1.5
                mod.defense_multiplier = 1.5
                attacker.add_component(mod)
                
                name = self._get_entity_name(attacker)
                self.event_manager.push(MessageEvent(_("'{}'가 분노를 폭발시킵니다! (지속 {}초)").format(name, int(duration)), "red"))
                self.event_manager.push(SoundEvent("ROAR"))
                
                # 3. Taunt (Angry Mode)
                # Provocation Range (Already scaled: Base 15 + (Skill Level - 1))
                provoke_range = getattr(skill, 'range', 15)
                
                aura = SkillEffectComponent(name="RAGE_AURA", duration=duration, damage=0, radius=provoke_range, effect_type="AURA")
                attacker.add_component(aura)
                
                # Initial Taunt (Instant check)
                pos = attacker.get_component(PositionComponent)
                if pos:
                    targets = self.world.get_entities_with_components({MonsterComponent, AIComponent, PositionComponent})
                    provoked = 0
                    for t in targets:
                        if t.entity_id == attacker.entity_id: continue
                        t_pos = t.get_component(PositionComponent)
                        if abs(pos.x - t_pos.x) + abs(pos.y - t_pos.y) <= provoke_range:
                            ai = t.get_component(AIComponent)
                            if ai.behavior != AIComponent.CHASE:
                                ai.behavior = AIComponent.CHASE
                                provoked += 1

        elif skill.id == "FLASH" or skill.name == "플래시":
            # 주변 즉발 폭발 (3x3)
            pos = attacker.get_component(PositionComponent)
            if pos:
                self.event_manager.push(MessageEvent(f"'{skill.name}'!! 번개 폭발이 주변을 뒤덮습니다!"))
                self.event_manager.push(SoundEvent("MAGIC_BOLT"))
                self._handle_explosion(attacker, pos.x, pos.y, skill)

        elif skill.id == "APOCALYPSE" or skill.name == "아포칼립스":
            self.event_manager.push(MessageEvent(f"'{skill.name}'!!! 종말의 불꽃이 모든 것을 뒤덮습니다!", "red"))
            self.event_manager.push(SoundEvent("MAGIC_BOLT"))
            
            # 화면 내 모든 적군 타격 (거리 15 이내)
            p_pos = attacker.get_component(PositionComponent)
            all_combat_entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
            
            for entity in all_combat_entities:
                if entity.entity_id == attacker.entity_id: continue
                ai = entity.get_component(AIComponent)
                if entity.has_component(MonsterComponent) or (ai and ai.faction == "MONSTER"):
                    e_pos = entity.get_component(PositionComponent)
                    dist = abs(e_pos.x - p_pos.x) + abs(e_pos.y - p_pos.y)
                    if dist <= 15:
                        self._apply_damage(attacker, entity, distance=dist, skill=skill)
                        # 폭발 연출
                        e_id = self.world.create_entity().entity_id
                        self.world.add_component(e_id, PositionComponent(x=e_pos.x, y=e_pos.y))
                        self.world.add_component(e_id, RenderComponent(char='*', color='red'))
                        self.world.add_component(e_id, EffectComponent(duration=0.3))

        elif skill.id == "GUARDIAN" or skill.name == "가디언":
            self.event_manager.push(MessageEvent(f"'{skill.name}'!! 수호자 포탑을 소환합니다!", "green"))
            self.event_manager.push(SoundEvent("MAGIC_BOLT"))
            p_pos = attacker.get_component(PositionComponent)
            # 플레이어 바로 옆(오른쪽)에 소환 시도
            self._spawn_summon(attacker, "가디언", p_pos.x + 1, p_pos.y, skill, behavior=AIComponent.STATIONARY)

        elif skill.id == "GOLEM" or skill.name == "골렘":
            self.event_manager.push(MessageEvent(f"'{skill.name}'!! 강력한 진흙 골렘을 소환합니다!", "gray"))
            self.event_manager.push(SoundEvent("MAGIC_BOLT"))
            p_pos = attacker.get_component(PositionComponent)
            # 플레이어 바로 옆(왼쪽)에 소환 시도
            self._spawn_summon(attacker, "골렘", p_pos.x - 1, p_pos.y, skill, behavior=AIComponent.CHASE)

        elif skill.id == "NOVA" or skill.name == "노바" or "NOVA" in getattr(skill, 'flags', set()):
            # 시전자 중심 원형 파동 공격
            pos = attacker.get_component(PositionComponent)
            if pos:
                # 노바의 사거리는 레벨에 따라 확장 (기본 3 ~ Lv255 10+)
                # CSV에는 0으로 되어 있으므로 기본값 설정
                base_range = skill.range if skill.range > 0 else 3
                # 레벨당 사거리 보정은 handle_skill_use_event에서 이미 처리됨 (scaled_range)
                radius = skill.range if skill.range > 0 else 3
                
                self.event_manager.push(MessageEvent(_("'{}'!! 서늘한 번개 파동이 퍼져나갑니다!").format(skill.name)))
                self.event_manager.push(SoundEvent("MAGIC_BOLT"))
                
                # 파동 연출 (거리 1부터 radius까지 확장)
                for r in range(1, radius + 1):
                    for dy in range(-r, r + 1):
                        for dx in range(-r, r + 1):
                            # 원형 판정 (맨해튼 거리 또는 유클리드 근사)
                            if r-1 < abs(dx) + abs(dy) <= r:
                                tx, ty = pos.x + dx, pos.y + dy
                                
                                # 이펙트 생성
                                e_id = self.world.create_entity().entity_id
                                self.world.add_component(e_id, PositionComponent(x=tx, y=ty))
                                self.world.add_component(e_id, RenderComponent(char='O', color='light_blue'))
                                self.world.add_component(e_id, EffectComponent(duration=0.1))
                                
                                # 데미지 적용
                                targets = [
                                    e for e in self.world.get_entities_with_components({PositionComponent, StatsComponent})
                                    if e.get_component(PositionComponent).x == tx 
                                    and e.get_component(PositionComponent).y == ty
                                    and e.entity_id != attacker.entity_id
                                ]
                                for target in targets:
                                    self._apply_skill_damage(attacker, target, skill, dx, dy)
                    
                    if hasattr(self.world.engine, '_render'):
                        self.world.engine._render()
                        time.sleep(0.05)

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
                for _i in range(3): # 3번 흔들림
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

    def _handle_knockback(self, target, dx, dy, attacker=None):
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
            
            # [Knockback Trap Trigger]
            # 넉백된 위치에 함정이 있다면 강제로 발동
            traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
            for trap_ent in traps:
                t_pos = trap_ent.get_component(PositionComponent)
                if t_pos.x == new_x and t_pos.y == new_y:
                    t_comp = trap_ent.get_component(TrapComponent)
                    if not t_comp.is_triggered and t_comp.trigger_type == "STEP_ON":
                        # TrapSystem 찾기
                        from .trap_manager import TrapSystem
                        trap_sys = next((s for s in self.world.systems if isinstance(s, TrapSystem)), None)
                        if trap_sys:
                            trap_sys.trigger_trap(target, trap_ent, source_entity=attacker)
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


    def _spawn_summon(self, owner, name, x, y, skill, behavior=AIComponent.CHASE):
        """소환수 에티티 생성 및 설정"""
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not map_ent: return
        mc = map_ent[0].get_component(MapComponent)
        
        # 유효 위치 확인 (벽이 아니고 다른 엔티티가 없는 곳)
        if not (0 <= x < mc.width and 0 <= y < mc.height) or mc.tiles[y][x] != '.':
            # 주변 빈칸 검색 (단순화: 일단 안되면 소환 실패 또는 주인 위치)
            found = False
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < mc.width and 0 <= ny < mc.height and mc.tiles[ny][nx] == '.':
                        x, y = nx, ny
                        found = True
                        break
                if found: break
        
        summon = self.world.create_entity()
        self.world.add_component(summon.entity_id, PositionComponent(x=x, y=y))
        
        char = 'G' if "가디언" in name else 'M'
        color = 'green' if "가디언" in name else 'gray'
        self.world.add_component(summon.entity_id, RenderComponent(char=char, color=color))
        
        if "가디언" in name:
            # [Guardian Tier System]
            # Tier 1 (Lv 1-2): Base Stats
            # Tier 2 (Lv 3-4): Range Up (+3)
            # Tier 3 (Lv 5-9): Attack Up (+5), Range Up (+3)
            # Tier 4 (Lv 10-26): Fire Player's Highest Skill
            # Tier 5 (Lv 27+): Fire Player's Highest Skill, Atk (+15), Range (+5)
            
            tier = 1
            if skill.level >= 27: tier = 5
            elif skill.level >= 10: tier = 4
            elif skill.level >= 5: tier = 3
            elif skill.level >= 3: tier = 2
            
            # Stat Scaling based on Tier
            hp_bonus = 0
            atk_bonus = 0
            range_bonus = 0
            
            if tier >= 3: atk_bonus += 5
            if tier >= 5: atk_bonus += 15
            
            if tier >= 2: range_bonus += 3
            if tier >= 5: range_bonus += 2 
            
            hp = 50 + (skill.level * 20) + hp_bonus
            attack = 5 + (skill.level * 3) + atk_bonus
            detect_range = 10 + range_bonus
            duration = 5.0 # Fixed 5s for Guardian
            
            self.world.add_component(summon.entity_id, StatsComponent(max_hp=hp, current_hp=hp, attack=attack, defense=5))
            self.world.add_component(summon.entity_id, AIComponent(behavior=behavior, detection_range=detect_range, faction="PLAYER"))
            self.world.add_component(summon.entity_id, SummonComponent(owner_id=owner.entity_id, duration=duration))
            self.world.add_component(summon.entity_id, MonsterComponent(type_name=name, level=skill.level))
            
            summon.get_component(StatsComponent).flags.add("RANGED")
            
            # [Tier 4+] Copy Player's Highest Skill
            if tier >= 4:
                best_skill = None
                best_lv = -1
                # Check owner's known skills (Stored in InventoryComponent)
                from .components import InventoryComponent
                # from data_manager import DataManager # Removed
                
                if owner.has_component(InventoryComponent):
                    inv = owner.get_component(InventoryComponent)
                    if inv and inv.skill_levels:
                        for s_id, s_lv in inv.skill_levels.items():
                             # Exclude Guardian itself
                             if s_id == "GUARDIAN": continue
                             
                             # [Recursion Prevention] Exclude SUMMON type skills
                             # Use self.world.engine.skill_defs
                             s_def = self.world.engine.skill_defs.get(s_id)
                             if s_def and (s_def.type == "SUMMON" or s_def.type == "소환"):
                                 continue

                             if s_lv > best_lv:
                                 best_lv = s_lv
                                 best_skill = s_id
                
                if best_skill:
                    from .components import CopiedSkillComponent
                    # from data_manager import DataManager
                    skill_def = self.world.engine.skill_defs.get(best_skill)
                    skill_name = skill_def.name if skill_def else best_skill
                    self.world.add_component(summon.entity_id, CopiedSkillComponent(skill_id=best_skill, skill_name=skill_name))

        elif "골렘" in name:
            # [Golem Overhaul]
            # Stats: Scale with Owner (Similar to Character Level)
            # Duration: Base 10s + (Level * 2s)
            
            owner_stats = owner.get_component(StatsComponent)
            if owner_stats:
                # HP: Owner's Max HP * 0.8 + Skill Bonus
                hp = int(owner_stats.max_hp * 0.8) + (skill.level * 10)
                # Attack: Owner's Attack
                attack = owner_stats.attack + (skill.level * 2)
            else:
                # Fallback if owner has no stats (shouldn't happen for player)
                hp = 100 + (skill.level * 30)
                attack = 10 + (skill.level * 5)
            
            duration = 10.0 + (skill.level * 2.0)
            
            self.world.add_component(summon.entity_id, StatsComponent(max_hp=hp, current_hp=hp, attack=attack, defense=10))
            self.world.add_component(summon.entity_id, AIComponent(behavior=behavior, detection_range=10, faction="PLAYER"))
            self.world.add_component(summon.entity_id, SummonComponent(owner_id=owner.entity_id, duration=duration))
            self.world.add_component(summon.entity_id, MonsterComponent(type_name=name, level=skill.level))

        else:
            # Default / Fallback for other potential summons
            hp = 50 + (skill.level * 20)
            attack = 5 + (skill.level * 3)
            self.world.add_component(summon.entity_id, StatsComponent(max_hp=hp, current_hp=hp, attack=attack, defense=5))
            self.world.add_component(summon.entity_id, AIComponent(behavior=behavior, detection_range=10, faction="PLAYER"))
            self.world.add_component(summon.entity_id, SummonComponent(owner_id=owner.entity_id, duration=skill.duration))
            self.world.add_component(summon.entity_id, MonsterComponent(type_name=name, level=skill.level))

        return summon

    def _handle_status_effect(self, target, effect_type, duration=5.0):
        """개별 엔티티에 상태 이상 부여"""
        if effect_type == "STONE_CURSE":
            if not target.has_component(PetrifiedComponent):
                target.add_component(PetrifiedComponent(duration=duration))
                self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(target)}이(가) 돌로 변했습니다!"))
                # 시각 효과
                render = target.get_component(RenderComponent)
                if render:
                    render.color = 'gray'
        elif effect_type == "STUN":
            if not target.has_component(StunComponent):
                target.add_component(StunComponent(duration=duration))
        elif effect_type == "SLEEP":
            if not target.has_component(SleepComponent):
                target.add_component(SleepComponent(duration=duration))

    def _handle_area_status_effect(self, attacker, skill, radius, effect_type):
        """범위 내 모든 적에게 상태 이상 부여"""
        pos = attacker.get_component(PositionComponent)
        if not pos: return
        
        all_combat_entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        for entity in all_combat_entities:
            if entity.entity_id == attacker.entity_id: continue
            
            e_pos = entity.get_component(PositionComponent)
            if abs(e_pos.x - pos.x) <= radius and abs(e_pos.y - pos.y) <= radius:
                self._handle_status_effect(entity, effect_type, duration=skill.duration)

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
            message_comp.add_message(event.text, event.color)

    def handle_collision_event(self, event: CollisionEvent):
        """충돌 이벤트 발생 시 메시지 로그 업데이트"""
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            
            if event.collision_type == "WALL":
                 # [Fix] Don't spam wall messages - too noisy when AI bumps into walls
                 pass  # message_comp.add_message("벽에 막혔습니다.")
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
                             message_comp.add_message(_("상인을 만났습니다. (거래 가능)"))
                         else:
                             message_comp.add_message(_("{}와 충돌했습니다. 전투가 시작됩니다.").format(monster_comp.type_name))
                     else:
                         message_comp.add_message(_("알 수 없는 엔티티와 충돌했습니다."))
            else:
                 message_comp.add_message(_("충돌 발생: {}").format(event.collision_type))

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
                    # [Ghost Refinement] 소환된 보스 환영은 HP 회복 불가
                    monster_comp = entity.get_component(MonsterComponent)
                    if monster_comp and monster_comp.is_summoned:
                        continue
                        
                    stats.current_hp = min(stats.max_hp, stats.current_hp + 1)
                    # 플레이어인 경우 메시지 출력
                    if entity == self.world.get_player_entity():
                         self.world.event_manager.push(MessageEvent(_("체력이 1 회복되었습니다.")))

        # 2. MP 자연 회복 (2초마다)
        if current_time - self.last_mp_regen_time >= 2.0:
            self.last_mp_regen_time = current_time
            for entity in self.world.get_entities_with_components({StatsComponent}):
                stats = entity.get_component(StatsComponent)
                if stats.current_mp < stats.max_mp:
                    stats.current_mp = min(stats.max_mp, stats.current_mp + 1)
                    # 플레이어인 경우 메시지 출력
                    if entity == self.world.get_player_entity():
                         self.world.event_manager.push(MessageEvent(_("마력이 1 회복되었습니다.")))

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

        # 1-2. 석화(Petrified) 시간 감액
        petrified_entities = self.world.get_entities_with_components({PetrifiedComponent})
        for entity in list(petrified_entities):
            petrified = entity.get_component(PetrifiedComponent)
            petrified.duration -= dt
            if petrified.duration <= 0:
                entity.remove_component(PetrifiedComponent)
                self.world.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 석화가 해제되었습니다!"))

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
                        
                        # [Fix] DoT 사망 시에도 정식 사망 로직 트리거
                        combat_sys = self.world.get_system(CombatSystem)
                        if combat_sys:
                            # attacker=None으로 전달하여 플레이어 존재 시 XP 부여되게 함
                            combat_sys._handle_death(None, entity)
                        else:
                            # Fallback: 직접 삭제 (시스템 부재 시)
                            self.world.delete_entity(entity.entity_id)
                        # 안전을 위해 시체 변환 로직은 CombatSystem의 로직을 재사용하는 것이 좋음.
            
            if poison.duration <= 0:
                entity.remove_component(PoisonComponent)
                self.world.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 중독 상태가 해제되었습니다."))

        # 1-3. 출혈(Bleeding) 시간 감액 및 데미지 처리
        bleeding_entities = self.world.get_entities_with_components({BleedingComponent})
        for entity in list(bleeding_entities):
            bleed = entity.get_component(BleedingComponent)
            bleed.duration -= dt
            
            # 출혈은 매 1초마다 데미지를 입힘 (Tick Timer 단순화: 매 프레임 확률적 처리보다는 Time accumulation 방식 권장)
            # 여기서는 편의상 Poison과 달리 1초마다 정기적으로 처리하기 위해 tick_timer를 추가하거나
            # 단순히 duration이 감소할 때마다 데미지를 입히는 방식을 사용할 수 있음.
            # Poison 코드를 참조하여 tick_timer를 동적으로 관리하는 것이 좋음. BleedingComponent에 tick_timer가 없으므로 추가 필요할 수 있음.
            # 하지만 Component 구조 변경 없이 하려면, duration의 정수부가 바뀔 때마다 데미지를 입히는 trick 사용.
            
            # [Fix] BleedingComponent should track tick. For now, assume simplified 1 dmg per sec roughly?
            # Or assume dt ~ 0.016. Let's rely on adding tick_timer attribute strictly, 
            # BUT since modifying Component __init__ affects existing pickles/instantiations potentially (though unlikely here),
            # I will dynamically add attribute if missing or use random chance scaled by dt.
            
            # Deterministic approach: store last_tick_time in component or engine? No.
            # Probabilistic approach: Expectation 1 dmg/sec -> prob = dt.
            if random.random() < dt: # 1 damage per second on average check
                stats = entity.get_component(StatsComponent)
                if stats:
                    stats.current_hp -= bleed.damage
                    if not entity.has_component(HitFlashComponent):
                        entity.add_component(HitFlashComponent(duration=0.1))
                    if stats.current_hp <= 0:
                        stats.current_hp = 0
                        self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}이(가) 과다출혈로 사망했습니다!", "red"))
                        
                        # [Fix] Bleeding 사망 시에도 정식 사망 로직 트리거
                        combat_sys = self.world.get_system(CombatSystem)
                        if combat_sys:
                            combat_sys._handle_death(None, entity)
                        else:
                            self.world.delete_entity(entity.entity_id)
            
            if bleed.duration <= 0:
                entity.remove_component(BleedingComponent)
                self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 출혈이 멈췄습니다."))

        # 1-3. StatModifier (Buff/Debuff) 시간 감액
        stat_mod_entities = self.world.get_entities_with_components({StatModifierComponent})
        for entity in list(stat_mod_entities):
            mod = entity.get_component(StatModifierComponent)
            mod.duration -= dt
            if mod.duration <= 0:
                entity.remove_component(StatModifierComponent)
                name = self.world.engine._get_entity_name(entity)
                self.event_manager.push(MessageEvent(f"{name}의 '{mod.source}' 효과가 끝났습니다.", "blue"))
                if hasattr(self.world.engine, '_recalculate_stats'):
                    self.world.engine._recalculate_stats()

        # 1-4. ManaShield 시간 감액
        ms_entities = self.world.get_entities_with_components({ManaShieldComponent})
        for entity in list(ms_entities):
            ms = entity.get_component(ManaShieldComponent)
            ms.duration -= dt
            if ms.duration <= 0:
                entity.remove_component(ManaShieldComponent)
                self.event_manager.push(MessageEvent(f"{self.world.engine._get_entity_name(entity)}의 마법 장막이 사라졌습니다.", "cyan"))

        # 1-5. 소환수(Summon) 시간 감액 및 소멸 처리
        summon_entities = self.world.get_entities_with_components({SummonComponent})
        for entity in list(summon_entities):
            summon = entity.get_component(SummonComponent)
            summon.duration -= dt
            if summon.duration <= 0:
                self.event_manager.push(MessageEvent(_("{}의 소환 시간이 만료되어 사라집니다.").format(self.world.engine._get_entity_name(entity)), "gray"))
                self.world.delete_entity(entity.entity_id)

        # 2. 횃불(VISION_UP) 시간 감액
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats and "VISION_UP" in stats.flags:
                if current_time >= stats.vision_expires_at:
                    stats.vision_range = 5
                    stats.flags.remove("VISION_UP")
                    self.world.event_manager.push(MessageEvent(_("횃불이 모두 타버려 다시 어두워졌습니다.")))
            
            if stats and stats.sees_hidden:
                if current_time >= stats.sees_hidden_expires_at:
                    stats.sees_hidden = False
                    self.world.event_manager.push(MessageEvent(_("영험한 기운이 사라져 숨겨진 것들이 보이지 않게 되었습니다.")))

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
            
            # [Visual] Rage Aura Blink (User Request: Blue Blink on Character)
            if skill.name == "RAGE_AURA":
                skill.tick_count += dt
                render = entity.get_component(RenderComponent)
                if render:
                    # Toggle every 0.5s
                    if int(skill.tick_count * 2) % 2 == 0:
                        render.color = 'blue'
                    else:
                        render.color = 'white'

            if skill.duration <= 0:
                entity.remove_component(SkillEffectComponent)
                # Reset Color
                render = entity.get_component(RenderComponent)
                if render: render.color = 'white'
                
                self.event_manager.push(MessageEvent(_("{} 효과가 끝났습니다.").format(skill.name)))

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
        player_ent = self.world.get_player_entity()

        for entity in list(self.world._entities.values()):
            modifiers = entity.get_components(StatModifierComponent)
            if not modifiers: continue
            
            for mod in list(modifiers):
                # Duration based logic
                mod.duration -= dt
                
                if mod.duration <= 0:
                    entity.remove_component_instance(mod)
                    needs_recalc = True
                    if entity == player_ent:
                        self.world.event_manager.push(MessageEvent(_("{} 효과가 만료되었습니다.").format(mod.source)))
        
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
            self.event_manager.push(MessageEvent(_("레벨업! 현재 레벨: {}").format(level_comp.level)))
            self.event_manager.push(SoundEvent("LEVEL_UP", "레벨 업!"))

    def _level_up(self, entity: Entity):
        level_comp = entity.get_component(LevelComponent)
        stats_comp = entity.get_component(StatsComponent)
        
        level_comp.level += 1
        # [Diablo Curve] 1.5x Multiplier for steeper curve
        level_comp.exp_to_next = int(level_comp.exp_to_next * 1.5)
        
        # [Stat Points] 5 points per level
        level_comp.stat_points += 5
        
        if stats_comp:
            # [Fixed Gain] Class specific fixed HP/MP gain
            hp_gain = 2.0
            mp_gain = 1.0
            
            if hasattr(self.world.engine, 'class_defs') and level_comp.job:
                class_def = self.world.engine.class_defs.get(level_comp.job)
                if class_def:
                    hp_gain = class_def.hp_gain
                    mp_gain = class_def.mp_gain
            
            stats_comp.base_max_hp = int(stats_comp.base_max_hp + hp_gain)
            stats_comp.base_max_mp = int(stats_comp.base_max_mp + mp_gain)
            
            # [Full Recovery] & Recalculate
            # 엔진 레벨 보정 스탯 재계산 호출
            if hasattr(self.world.engine, '_recalculate_stats'):
                self.world.engine._recalculate_stats()
                
            # Recalculate 후 최대 체력으로 회복
            stats_comp.current_hp = stats_comp.max_hp
            stats_comp.current_mp = stats_comp.max_mp
            
            self.event_manager.push(MessageEvent(_("체력과 마력이 모두 회복되었습니다!"), "green"))

    def grant_stat_points(self, entity: Entity, amount: int, reason: str = ""):
        """외부 요인(퀘스트, 보스 처치 등)으로 스탯 포인트를 지급"""
        level_comp = entity.get_component(LevelComponent)
        if level_comp:
            level_comp.stat_points += amount
            
            msg = _("보너스 스탯 포인트 +{} 획득!").format(amount)
            if reason:
                 msg += f" ({reason})"
            
            self.event_manager.push(MessageEvent(msg, "gold"))
            # 레벨업 사운드 재사용 (또는 별도 사운드)
            self.event_manager.push(SoundEvent("LEVEL_UP", "보너스 포인트!"))


class BossSystem(System):
    """보스 몬스터의 특수 패턴, 대사, 페이즈 전환을 관리하는 시스템"""
    BARK_COOLDOWN = 3.0 # 대사 간 최소 간격 (초)

    def __init__(self, world):
        super().__init__(world)
        self.patterns = self.world.engine.boss_patterns
        
        # 이벤트 리스너 등록
        from .events import CombatResultEvent, MapTransitionEvent, BossBarkEvent
        self.event_manager.register(CombatResultEvent, self._handle_combat_result)
        self.event_manager.register(MapTransitionEvent, self._handle_map_transition)
        self.event_manager.register(BossBarkEvent, self._handle_boss_bark)

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
    def _trigger_boss_summon(self, attacker: Entity, target: Entity, specific_boss_id: str = None):
        """보스의 체력이 낮아지면 지원군을 소환합니다. specific_boss_id가 있으면 해당 보스 소환."""
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
        self.event_manager.push(MessageEvent(_("'{}'이(가) 강력한 포효와 함께 지원군을 부릅니다!").format(target_name)))
        self.event_manager.push(SoundEvent("BOSS_ROAR"))
        
        engine = self.world.engine
        
        spawn_id = None
        if specific_boss_id:
            spawn_id = specific_boss_id
        elif boss_id == "DIABLO":
            pass
        else:
            # 이전 보스 1마리 소환
            idx = BOSS_SEQUENCE.index(boss_id)
            if idx > 0:
                spawn_id = BOSS_SEQUENCE[idx - 1]
        
        if spawn_id:
            tx, ty = self._find_spawn_pos(t_pos.x, t_pos.y)
            engine._spawn_boss(tx, ty, boss_name=spawn_id, is_summoned=True)
            self.event_manager.push(MessageEvent(_("!!! {}이(가) {}의 환영을 불러냅니다! !!!").format(boss_id, spawn_id), "purple"))

    def _find_spawn_pos(self, x, y):
        """주변 빈 공간을 찾습니다."""
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not map_ent: return x, y
        mc = map_ent[0].get_component(MapComponent)
        
        for _i in range(15): # 15번 시도
            tx, ty = x + random.randint(-3, 3), y + random.randint(-3, 3)
            if 0 <= tx < mc.width and 0 <= ty < mc.height and mc.tiles[ty][tx] == '.':
                return tx, ty
        return x, y

    def _announce_skill(self, text, color="red"):
        """UI에 중앙 알림을 띄웁니다. (파파팍 효과)"""
        if hasattr(self.world.engine, 'ui') and self.world.engine.ui:
             self.world.engine.ui.show_center_dialogue(text, color)

    def process(self):
        player = self.world.get_player_entity()
        if not player: return
        
        p_pos = player.get_component(PositionComponent)
        boss_entities = self.world.get_entities_with_components({BossComponent, PositionComponent, StatsComponent})
        
        # 맵 정보 가져오기
        map_ent = self.world.get_entities_with_components({MapComponent})
        map_comp = map_ent[0].get_component(MapComponent) if map_ent else None
        if not map_comp: return
        
        # 델타 타임 (턴 베이스이므로 고정값 사용하거나 타이핑 간격 조절)
        # 렌더 스테이트에서 계속 호출된다면 더 좋겠지만, 여기서는 process 호출 시마다 한 자씩 공개
        
        for boss_ent in list(boss_entities):
            boss = boss_ent.get_component(BossComponent)
            pos = boss_ent.get_component(PositionComponent)
            stats = boss_ent.get_component(StatsComponent)
            
            # 몬스터 행동 지연(Cooldown) 확인
            current_time = time.time()
            monster_delay = getattr(stats, 'action_delay', 0.6)
            if current_time - stats.last_action_time < monster_delay:
                continue
            
            pattern = self.patterns.get(boss.boss_id)
            if not pattern: continue

            # [Ghost Refinement] 소환된 환영 보스는 10~20% 확률로 너프된 위력 사용
            monster_comp = boss_ent.get_component(MonsterComponent)
            is_ghost = monster_comp.is_summoned if monster_comp else False
            nerf_factor = random.uniform(0.8, 0.9) if is_ghost else 1.0

            # --- 1. 대사 타이핑/표시 로직 ---
            if boss.active_bark:
                # 타이핑 진행
                if len(boss.visible_bark) < len(boss.active_bark):
                    # 다음 문자 추가
                    boss.visible_bark = boss.active_bark[:len(boss.visible_bark) + 1]
                    # 타이핑 중에는 지속 시간 리셋
                    # (bark_display_timer는 _trigger_bark에서 이미 설정됨)
                else:
                    # 타이핑 완료 후 대기
                    boss.bark_display_timer -= 0.1 # 대략적인 감쇠 (턴 기반 한계)
                    if boss.bark_display_timer <= 0:
                        boss.active_bark = ""
                        boss.visible_bark = ""

            # --- 2. 조우 및 접근 대사 ---
            dist = abs(p_pos.x - pos.x) + abs(p_pos.y - pos.y)
            
            # [Proximity] 진입 대사 (Entry Bark) - 거리가 가까워지면 (12-15칸)
            if not getattr(boss, 'entry_bark_triggered', False):
                if dist <= 15:
                    boss.entry_bark_triggered = True
                    bark = pattern.get("on_floor_entry")
                    if bark:
                        self._trigger_bark(boss_ent, bark, duration=4.0)
            
            # [Encounter] 조우 대사 (Entrance Bark)
            if not boss.is_engaged:
                if dist <= 5: # 5타일 이내 조우 시
                    boss.is_engaged = True
                    bark = pattern.get("entrance_bark")
                    if bark:
                        self._trigger_bark(boss_ent, bark, duration=5.0)
                        self.event_manager.push(SoundEvent("BOSS_INTRO", "보스 등장!"))
                        # [Encounter] BGM 트리거
                        self.event_manager.push(SoundEvent("BGM_BOSS", "전용 테마 연주 시작"))

            # --- 3. 페이즈 및 HP 트리거 ---
            if stats.current_hp > 0:
                hp_percent = stats.current_hp / stats.max_hp
                
                # HP 임계값 대사 (50%, 20% 등)
                for threshold in [0.5, 0.33, 0.2]:
                    t_str = str(threshold)
                    if hp_percent <= threshold and t_str not in boss.triggered_hps:
                        boss.triggered_hps.add(t_str)
                        
                        # [Boss Summon] 이전 보스 소환 트리거
                        is_summon_threshold = (threshold == 0.5 if boss.boss_id == "LEORIC" else threshold == 0.33)
                        
                        if is_summon_threshold:
                            # [Boss Summon] 마지막 보스 환영 소환 (첫 번째 보스인 도살자는 제외)
                            last_id = getattr(self.world.engine, 'last_boss_id', None)
                            if last_id and last_id != boss.boss_id and boss.boss_id != "BUTCHER":
                                # 소환 대사
                                summon_bark = pattern.get("summon_bark", "과거의 영혼이여, 나를 도우라!")
                                self._trigger_bark(boss_ent, summon_bark)
                                self._announce_skill(summon_bark, "purple") # Center Alert
                                # 근처에 소환
                                self.world.engine._spawn_boss(pos.x + 1, pos.y + 1, boss_name=last_id, is_summoned=True)
                                self.event_manager.push(MessageEvent(_("!!! {}이(가) 이전의 적 {}의 환영을 불러냅니다! !!!").format(boss.boss_id, last_id), "purple"))
                        else:
                            bark_key = f"on_hp_{int(threshold*100)}"
                            bark = pattern.get(bark_key)
                            if bark:
                                 self._trigger_bark(boss_ent, bark)
                                 # HP 20% 임계값 돌파 시 화면 흔들림 효과 추가
                                 if threshold == 0.2 and hasattr(self.world.engine, 'trigger_shake'):
                                     self.world.engine.trigger_shake(10)

                if boss.boss_id == "DIABLO":
                    # [DIABLO] Sequential Summoning (85% -> BUTCHER, 70% -> LEORIC, 55% -> LICH_KING)
                    # 20% -> Enrage (All Shall Suffer)
                    diablo_thresholds = {
                        0.85: "BUTCHER",
                        0.70: "LEORIC",
                        0.55: "LICH_KING"
                    }
                    
                    for th, spawn_boss in diablo_thresholds.items():
                        t_str = f"diablo_summon_{int(th*100)}"
                        # print(f"DEBUG: Checking {t_str}, hp={hp_percent}, th={th}, triggered={boss.triggered_hps}")
                        if hp_percent <= th and t_str not in boss.triggered_hps:
                            boss.triggered_hps.add(t_str)
                            bark_key = f"on_hp_{int(th*100)}"
                            bark = pattern.get(bark_key)
                            if bark: 
                                self._trigger_bark(boss_ent, bark)
                                self._announce_skill(bark, "red") # Center Alert
                            
                            # Specific Summon
                            self._trigger_boss_summon(None, boss_ent, specific_boss_id=spawn_boss)
                            if hasattr(self.world.engine, 'trigger_shake'):
                                self.world.engine.trigger_shake(8)

                    # 20% Threshold (Enrage)
                    if hp_percent <= 0.2 and "diablo_enrage" not in boss.triggered_hps:
                        boss.triggered_hps.add("diablo_enrage")
                        bark = pattern.get("on_hp_20") # ALL SHALL SUFFER
                        if bark:
                            self._announce_skill(bark, "red") # Center Alert
                            self.event_manager.push(MessageEvent(f"!!! {boss.boss_id}: {bark} !!!", "red"))
                            # 광폭화: 본체 행동 속도 증가
                            stats.action_delay *= 0.5
                            if hasattr(self.world.engine, 'trigger_shake'):
                                self.world.engine.trigger_shake(15)

                # [LEORIC] 10% HP Interval Smite
                if boss.boss_id == "LEORIC":
                    for interval in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]:
                        s_key = f"smite_{int(interval*100)}"
                        if hp_percent <= interval and s_key not in boss.triggered_hps:
                            boss.triggered_hps.add(s_key)
                            bark = pattern.get("on_skill_smite")
                            if bark:
                                self._trigger_bark(boss_ent, bark)
                                self._announce_skill(bark, "red") # Center Alert
                            self.event_manager.push(MessageEvent(_("!!! {}의 광역 강타! !!!").format(boss.boss_id), "red"))
                            
                            from .events import DirectionalAttackEvent
                            for ddy in range(-4, 5):
                                for ddx in range(-4, 5):
                                    if ddx == 0 and ddy == 0: continue
                                    if abs(ddx) + abs(ddy) <= 4:
                                         self.event_manager.push(DirectionalAttackEvent(boss_ent.entity_id, ddx, ddy, range_dist=1, damage_factor=0.8))
                            
                            if hasattr(self.world.engine, 'trigger_shake'):
                                self.world.engine.trigger_shake(8)

                # 기존 페이즈 로직 (동작 유지)
                phase_list = pattern.get("phases", [])
                if boss.current_phase < len(phase_list):
                    next_phase = phase_list[boss.current_phase]
                    if hp_percent <= next_phase.get("hp_threshold", 0):
                        boss.current_phase += 1
                        bark = next_phase.get("bark")
                        if bark: 
                            self._trigger_bark(boss_ent, bark)
                            self._announce_skill(bark, "yellow") # Center Alert
                            # 분노 페이즈(20% 이하) 진입 시 화면 흔들림
                            if next_phase.get("hp_threshold", 0) <= 0.2 and hasattr(self.world.engine, 'trigger_shake'):
                                self.world.engine.trigger_shake(10)
                        
                        boost = next_phase.get("stat_boost")
                        if boost:
                            if "attack" in boost:
                                stats.attack = int(stats.attack * boost["attack"])
                                stats.attack_min = int(getattr(stats, 'attack_min', stats.attack) * boost["attack"])
                                stats.attack_max = int(getattr(stats, 'attack_max', stats.attack) * boost["attack"])
                            if "action_delay" in boost:
                                stats.action_delay *= boost["action_delay"]
                            self.event_manager.push(MessageEvent(_("!!! {}이(가) 분노하여 더욱 강력해집니다! !!!").format(boss.boss_id), "red"))
                            stats.last_action_time = current_time # 페이즈 전환도 행동으로 간주하거나 쿨다운 갱신

                # --- 4. 스킬 및 행동 AI (Logic) ---
                # 매 턴 10% 확률로 특수 패턴 발동 (Engagement 상태일 때만)
                if boss.is_engaged and random.random() < 0.1:
                    # 보스별 특수 스킬 트리거 (나중에 skill_defs 연동 가능)
                    self.event_manager.push(MessageEvent(_("{}의 강력한 기운이 방출됩니다!").format(boss.boss_id), "purple"))
                    if hasattr(self.world.engine, 'trigger_shake'):
                        self.world.engine.trigger_shake(5)
                    stats.last_action_time = current_time

                # 거리 기반 스킬 AI
                dist = abs(p_pos.x - pos.x) + abs(p_pos.y - pos.y)
                if boss.is_engaged:
                    # 도살자(BUTCHER) 고유 스킬 셋
                    if boss.boss_id == "BUTCHER":
                        if self._process_butcher_logic(boss_ent, p_pos, dist, map_comp, nerf_factor):
                            stats.last_action_time = current_time
                    elif boss.boss_id == "LEORIC":
                        if self._process_leoric_logic(boss_ent, p_pos, dist, map_comp):
                            stats.last_action_time = current_time
                    elif boss.boss_id == "LICH_KING":
                        if self._process_lich_king_logic(boss_ent, p_pos, dist, map_comp):
                            stats.last_action_time = current_time
                    elif boss.boss_id == "DIABLO":
                        if self._process_diablo_logic(boss_ent, p_pos, dist, map_comp):
                            stats.last_action_time = current_time
                    else:
                        # 일반 보스 AI (Dash/Spin)
                        if dist > 3 and random.random() < 0.2:
                            # [Dash] 돌진
                            self._trigger_bark(boss_ent, "거기 서라!")
                            self.event_manager.push(MessageEvent(_("{}이(가) 당신을 향해 급격히 돌진합니다!").format(boss.boss_id), "red"))
                            dx = 1 if p_pos.x > pos.x else (-1 if p_pos.x < pos.x else 0)
                            dy = 1 if p_pos.y > pos.y else (-1 if p_pos.y < pos.y else 0)
                            if map_comp.tiles[pos.y + dy][pos.x + dx] == '.':
                                pos.x += dx
                                pos.y += dy
                                stats.last_action_time = current_time

                        elif dist <= 1 and random.random() < 0.3:
                            # [AoE] 대회전
                            self._trigger_bark(boss_ent, "모두 사라져라!")
                            from .events import DirectionalAttackEvent
                            self.event_manager.push(MessageEvent(_("{}의 대회전 공격!").format(boss.boss_id), "red"))
                            if is_ghost:
                                self.event_manager.push(MessageEvent(_("환영의 일격이라 위력이 약합니다."), "gray"))
                            
                            for ddy in [-1, 0, 1]:
                                for ddx in [-1, 0, 1]:
                                    if ddx == 0 and ddy == 0: continue
                                    self.event_manager.push(DirectionalAttackEvent(boss_ent.entity_id, ddx, ddy, range_dist=1))
                            stats.last_action_time = current_time

    def _process_butcher_logic(self, boss_ent, p_pos, dist, map_comp, nerf_factor=1.0):
        """도살자의 특수 AI 로직: 훅, 슬램, 분노의 돌진 (nerf_factor 적용)"""
        boss = boss_ent.get_component(BossComponent)
        pos = boss_ent.get_component(PositionComponent)
        stats = boss_ent.get_component(StatsComponent)
        pattern = self.patterns.get(boss.boss_id)

        # 1. 훅 (Hook): 거리가 벌어졌을 때 (3~6 타일)
        if 3 <= dist <= 6 and random.random() < 0.25:
            bark = pattern.get("on_skill_hook", "Come here!")
            self._trigger_bark(boss_ent, bark)
            self._announce_skill(f"'{bark}'", "red") # Center Alert
            self.event_manager.push(MessageEvent(_("!!! 도살자가 피 묻은 갈고리를 던집니다! !!!"), "red"))
            
            # 플레이어를 보스 바로 앞으로 끌어당김
            player_ent = self.world.get_player_entity()
            p_pos_comp = player_ent.get_component(PositionComponent)
            
            # 방향 계산
            dx = 1 if p_pos.x > pos.x else (-1 if p_pos.x < pos.x else 0)
            dy = 1 if p_pos.y > pos.y else (-1 if p_pos.y < pos.y else 0)
            
            target_x, target_y = pos.x + dx, pos.y + dy
            if map_comp.tiles[target_y][target_x] == '.':
                p_pos_comp.x, p_pos_comp.y = target_x, target_y
                # 짧은 기절 부여 (nerf_factor 반영)
                from .components import StunComponent
                player_ent.add_component(StunComponent(duration=1.0 * nerf_factor))
                self.event_manager.push(MessageEvent(_("갈고리에 끌려가 기절했습니다!"), "yellow"))
            return True

        # 2. 슬램 (Slam): 인접했을 때
        if dist <= 1 and random.random() < 0.3:
            bark = pattern.get("on_skill_slam", "Fresh Meat!")
            self._trigger_bark(boss_ent, bark)
            self._announce_skill(f"'{bark}'", "red") # Center Alert
            self.event_manager.push(MessageEvent(_("!!! 도살자의 강력한 내려치기! !!!"), "red"))
            
            player_ent = self.world.get_player_entity()
            # 1.5배 데미지 적용 (CombatSystem의 로직을 간소하게 재현하거나 이벤트를 보내야 함)
            # 여기서는 직접 stats를 깎거나 이벤트를 발행. 
            # 일관성을 위해 _apply_damage를 호출하고 싶지만 CombatSystem 메서드임.
            # 임시로 메시지와 함께 데미지 부여 로직 (CombatSystem 접근 권한 확인 필요)
            self.event_manager.push(MessageEvent(_("큰 충격과 함께 뒤로 밀려납니다!"), "yellow"))
            # 넉백 처리 (AI 단에서 직접 수행)
            self._apply_manual_knockback(boss_ent, player_ent, map_comp)
            # 데미지 이벤트는 없으므로 직접 처리 (stats 깎기, nerf_factor 반영)
            p_stats = player_ent.get_component(StatsComponent)
            if p_stats:
                damage = int(stats.attack * 1.5 * nerf_factor)
                p_stats.current_hp -= max(1, damage - p_stats.defense)
            return True

        # 3. 분노의 돌진 (Frenzy Charge): 직선상에 있을 때
        is_linear = (p_pos.x == pos.x or p_pos.y == pos.y)
        if is_linear and dist >= 2 and random.random() < 0.15:
            bark = pattern.get("on_skill_charge", "RRRRAAAARRRRGH!")
            self._trigger_bark(boss_ent, bark)
            self._announce_skill(f"'{bark}'", "red") # Center Alert
            self.event_manager.push(MessageEvent(_("!!! 도살자가 미친 듯이 돌진합니다! !!!"), "red"))
            
            dx = 1 if p_pos.x > pos.x else (-1 if p_pos.x < pos.x else 0)
            dy = 1 if p_pos.y > pos.y else (-1 if p_pos.y < pos.y else 0)
            
            # 직선 돌진 로직
            curr_x, curr_y = pos.x, pos.y
            hit_wall = False
            hit_player = False
            
            # 최대 10칸 돌진
            for _i in range(10):
                nx, ny = curr_x + dx, curr_y + dy
                if map_comp.tiles[ny][nx] == '#':
                    hit_wall = True
                    break
                
                # 플레이어 충돌 체크
                if nx == p_pos.x and ny == p_pos.y:
                    hit_player = True
                    # 플레이어 위치 업데이트 (치여서 밀려남)
                    p_pos.x += dx
                    p_pos.y += dy
                    break
                
                curr_x, curr_y = nx, ny
            
            pos.x, pos.y = curr_x, curr_y
            
            if hit_player:
                self.event_manager.push(MessageEvent(_("도살자의 돌진에 치여 큰 피해를 입었습니다!"), "red"))
                player_ent = self.world.get_player_entity()
                p_stats = player_ent.get_component(StatsComponent) if player_ent else None
                if p_stats:
                    p_stats.current_hp -= int(stats.attack * 2.0 * nerf_factor)
            
            if hit_wall:
                self.event_manager.push(MessageEvent(_("도살자가 벽에 들이받고 기절했습니다!"), "yellow"))
                from .components import StunComponent
                # 보스 기절 시간은 너프하지 않음 (오히려 패널티니까)
                boss_ent.add_component(StunComponent(duration=2.0))
            return True
        
        return False

    def _process_leoric_logic(self, boss_ent, p_pos, dist, map_comp):
        """레오닉의 특수 AI 로직: 군단 소환, 석화 마법"""
        boss = boss_ent.get_component(BossComponent)
        pos = boss_ent.get_component(PositionComponent)
        stats = boss_ent.get_component(StatsComponent)
        pattern = self.patterns.get(boss.boss_id)
        current_time = time.time()

        # 1. 군단 소환 (HP > 50% 구간에서 몬스터 수가 15마리 미만일 때)
        hp_percent = stats.current_hp / stats.max_hp
        
        # 현재 맵의 모든 해골(SKELETON) 수 파악
        all_monsters = self.world.get_entities_with_components({MonsterComponent})
        skeletons = [m for m in all_monsters if m.get_component(MonsterComponent).monster_id == "SKELETON"]
        
        if hp_percent > 0.5 and len(skeletons) < 15 and random.random() < 0.3:
            # 소환 대사 (쿨다운 10초)
            if current_time - getattr(boss, 'last_swarm_time', 0) > 10.0:
                bark = pattern.get("on_skill_swarm")
                if bark:
                    self._trigger_bark(boss_ent, bark)
                boss.last_swarm_time = current_time
            
            # 부족한 만큼 또는 최대 5마리 소환
            num_to_spawn = min(5, 15 - len(skeletons))
            spawned_any = False
            for _i in range(num_to_spawn):
                tx, ty = self._find_spawn_pos(pos.x, pos.y)
                if self.world.engine._spawn_monster_at(tx, ty, pool=["SKELETON"]):
                    spawned_any = True
            
            if spawned_any:
                self._announce_skill("깨어나라, 나의 군대여!", "gray") # Center Alert
                self.event_manager.push(MessageEvent(_("{}이(가) 해골 군단을 소환합니다!").format(boss.boss_id), "gray"))
                return True

        # 2. 석화 마법 (소환수가 15마리 이상일 때)
        if len(skeletons) >= 15 and random.random() < 0.3:
            player = self.world.get_player_entity()
            if player and dist <= 10:
                # 쿨다운 15초
                if current_time - getattr(boss, 'last_petrify_time', 0) > 15.0:
                    bark = pattern.get("on_skill_petrify")
                    if bark:
                        self._trigger_bark(boss_ent, bark)
                    boss.last_petrify_time = current_time
                    
                    if not player.has_component(PetrifiedComponent):
                        self._announce_skill("굳어버려라!", "yellow") # Center Alert
                        player.add_component(PetrifiedComponent(duration=3.0))
                        self.event_manager.push(MessageEvent(_("!!! {}의 마법으로 전신이 석화되었습니다! !!!").format(boss.boss_id), "yellow"))
                        # 석화 시 이펙트
                        if hasattr(self.world.engine, 'trigger_shake'):
                            self.world.engine.trigger_shake(5)
                    return True

        return False

    def _process_lich_king_logic(self, boss_ent, p_pos, dist, map_comp):
        """리치 왕의 특수 AI 로직: 메두사의 시선, 대지의 저주, 연계 소환"""
        boss = boss_ent.get_component(BossComponent)
        stats = boss_ent.get_component(StatsComponent)
        pattern = self.patterns.get(boss.boss_id)
        current_time = time.time()
        
        player = self.world.get_player_entity()
        if not player: return False

        # HP 20% 이하 (분노 상태) -> 쿨다운 감소
        hp_percent = stats.current_hp / stats.max_hp
        is_enraged = hp_percent <= 0.2
        cooldown_mod = 0.5 if is_enraged else 1.0

        # 1. 메두사의 시선 (석화 스택) - 사거리 8
        gaze_cd = 12.0 * cooldown_mod
        if dist <= 8 and random.random() < 0.2:
            if current_time - getattr(boss, 'last_gaze_time', 0) > gaze_cd:
                boss.last_gaze_time = current_time
                bark = pattern.get("on_skill_gaze")
                if bark: self._trigger_bark(boss_ent, bark)
                
                # 플레이어에게 석화 컴포넌트 추가/갱신
                p_comp = player.get_component(PetrifiedComponent)
                if p_comp:
                    if p_comp.stacks < p_comp.max_stacks:
                        p_comp.stacks += 1
                        p_comp.duration = 5.0 # 지속시간 갱신
                        self._announce_skill("죽음의 냉기...", "cyan")
                        self.event_manager.push(MessageEvent(_("!!! 리치 왕의 시선에 몸이 더욱 굳어갑니다! (석화 {}스택) !!!").format(p_comp.stacks), "gray"))
                    else:
                        self.event_manager.push(MessageEvent(_("!!! 이미 완전히 석화된 상태입니다! !!!"), "gray"))
                else:
                    player.add_component(PetrifiedComponent(duration=5.0, stacks=1))
                    self._announce_skill("죽음의 시선...", "cyan")
                    self.event_manager.push(MessageEvent(_("!!! 리치 왕의 시선이 당신을 굳게 만듭니다! (석화 1스택) !!!"), "gray"))
                
                return True

        # 2. 대지의 저주 (Root/속박) - 사거리 10
        curse_cd = 15.0 * cooldown_mod
        if dist <= 10 and random.random() < 0.15:
            from .components import StatModifierComponent
            # 이동 불가 디버프 (여기서는 간단히 Action Delay를 매우 크게 늘리거나 Root 컴포넌트 사용)
            # 일단 Action Delay를 대폭 늘리는 StatModifier로 구현
            if current_time - getattr(boss, 'last_curse_time', 0) > curse_cd:
                boss.last_curse_time = current_time
                bark = pattern.get("on_skill_curse")
                if bark: self._trigger_bark(boss_ent, bark)
                
                # 'Root' 효과: 지속시간 동안 아무것도 못하거나 이동만 못함 using StunComponent is easiest for "Stop Movement"
                # But request says "Root" (tied feet).
                # For simplicity in V9, let's treat it as a heavy Slow or Root if implemented.
                # Actually, let's use a specialized modifier to increase action delay massively?
                # Request: "Play's feet tied". Let's instantiate a Stun for 1.5s
                if not player.has_component(StunComponent):
                    self._announce_skill("대지가 너를 삼키리라...", "brown")
                    player.add_component(StunComponent(duration=2.0))
                    self.event_manager.push(MessageEvent(_("!!! 대지의 저주가 당신의 발을 묶습니다! !!!"), "brown"))
                return True
    

    def _process_diablo_logic(self, boss_ent, p_pos, dist, map_comp):
        """디아블로 전용 로직: 광폭화 효과 지속 관리"""
        boss = boss_ent.get_component(BossComponent)
        stats = boss_ent.get_component(StatsComponent)
        
        # Enrage Phase (HP <= 20%)
        # 지속적으로 소환된 몬스터들의 속도를 증가시킴
        if stats.current_hp <= stats.max_hp * 0.2:
            # 맵 상의 모는 MonsterComponent를 가진 엔티티 검색
            all_monsters = self.world.get_entities_with_components({MonsterComponent, StatsComponent})
            for m_ent in all_monsters:
                m_comp = m_ent.get_component(MonsterComponent)
                if m_comp.is_summoned: # 소환된 환영/졸개들
                    m_stats = m_ent.get_component(StatsComponent)
                    # 이미 버프된 상태인지 확인하는 플래그가 없으므로
                    # action_delay를 체크하거나, 매직 넘버 사용. 
                    # 안전하게: 0.3 이하면 더 줄이지 않음 (기본 0.6 -> 0.3)
                    if getattr(m_stats, 'action_delay', 0.6) > 0.3:
                         m_stats.action_delay = 0.3
                         # 이펙트 메시지는 너무 자주 뜨면 안되므로 생략하거나 1회성으로 처리해야 함
        
        return False

    def _apply_manual_knockback(self, attacker, target, map_comp):
        """AI 로직 내에서 간단한 넉백 적용"""
        a_pos = attacker.get_component(PositionComponent)
        t_pos = target.get_component(PositionComponent)
        
        dx = 1 if t_pos.x > a_pos.x else (-1 if t_pos.x < a_pos.x else 0)
        dy = 1 if t_pos.y > a_pos.y else (-1 if t_pos.y < a_pos.y else 0)
        
        nx, ny = t_pos.x + dx, t_pos.y + dy
        if 0 <= nx < map_comp.width and 0 <= ny < map_comp.height and map_comp.tiles[ny][nx] == '.':
            t_pos.x, t_pos.y = nx, ny

    def _find_spawn_pos(self, x, y):
        """주변 빈 공간을 찾습니다."""
        map_ent = self.world.get_entities_with_components({MapComponent})
        if not map_ent: return x, y
        mc = map_ent[0].get_component(MapComponent)
        
        for _i in range(15): # 15번 시도
            tx, ty = x + random.randint(-4, 4), y + random.randint(-4, 4)
            if 0 <= tx < mc.width and 0 <= ty < mc.height and mc.tiles[ty][tx] == '.':
                return tx, ty
        return x, y

    def _trigger_bark(self, boss_ent, text, duration=5.0, bypass_cooldown=False):
        """보스 대사 트리거 (쿨다운 및 타이핑 애니메이션 시작)"""
        boss = boss_ent.get_component(BossComponent)
        if not boss: return

        # 쿨다운 체크
        current_time = time.time()
        if not bypass_cooldown and hasattr(boss, 'last_bark_time'):
            if current_time - boss.last_bark_time < self.BARK_COOLDOWN:
                return # 쿨다운 중이면 무시
        
        boss.active_bark = text
        boss.visible_bark = ""
        boss.bark_display_timer = duration
        boss.last_bark_time = current_time
        # 로그에도 남김
        from .events import MessageEvent
        self.event_manager.push(MessageEvent(f"[{boss.boss_id}] \"{text}\"", "gold"))

    def _handle_combat_result(self, event):
        """전투 결과를 바탕으로 보스 대사 결정"""
        if type(event).__name__ != "CombatResultEvent": return
        
        # 1. 플레이어가 보스를 공격했을 때
        target = getattr(event, 'target', None)
        if target:
            target_boss = target.get_component(BossComponent)
            if target_boss:
                pattern = self.patterns.get(target_boss.boss_id)
                if pattern:
                    if getattr(event, 'is_miss', False):
                        bark = pattern.get("on_dodge")
                        if bark: self._trigger_bark(target, bark)
                    elif getattr(event, 'is_crit', False):
                        bark = pattern.get("on_crit_received")
                        if bark: self._trigger_bark(target, bark)

        # 2. 보스가 플레이어를 공격했을 때
        attacker = getattr(event, 'attacker', None)
        if attacker:
            attacker_boss = attacker.get_component(BossComponent)
            if attacker_boss:
                pattern = self.patterns.get(attacker_boss.boss_id)
                if pattern:
                    if not getattr(event, 'is_miss', False):
                        # 보스가 스킬을 썼는가?
                        if getattr(event, 'skill', None):
                            # on_skill_1, on_skill_2 등 (랜덤 또는 순차)
                            bark = pattern.get("on_skill_1") # 고정 예시
                            if bark: self._trigger_bark(attacker, bark)
                        else:
                            bark = pattern.get("on_hit_player")
                            if bark: self._trigger_bark(attacker, bark)

    def _handle_map_transition(self, event):
        """맵 이동 시 보스 층 조우 대사"""
        # 엔진에서 새로운 맵을 생성한 후 호출됨
        # (실제로는 엔진이 보스를 스폰한 직후 process가 돌면서 체크하는 것이 더 쉬움)
        pass

    def _handle_boss_bark(self, event):
        """커스텀 보스 대사 이벤트 처리"""
        if type(event).__name__ != "BossBarkEvent": return
        boss_ent = getattr(event, 'boss_entity', None)
        text = getattr(event, 'text', None)
        bark_type = getattr(event, 'bark_type', None)
        
        # 사망 대사 등 특정 타입은 지속 시간 길게 및 쿨다운 무시
        duration = 5.0
        bypass = False
        if bark_type == "DEATH":
            duration = 8.0 # 사망 대사 보정
            bypass = True

        if boss_ent:
            self._trigger_bark(boss_ent, text or "...", duration=duration, bypass_cooldown=bypass)
        else:
            print("DEBUG: _handle_boss_bark failed - no boss_ent in event")

    def _trigger_summon(self, boss_ent, minion_type, count):
        """보스 주변에 부하 몬스터 소환"""
        pos = boss_ent.get_component(PositionComponent)
        from .events import MessageEvent
        self.event_manager.push(MessageEvent(_("{}들이 보스의 부름에 응답하여 나타납니다!").format(minion_type), "purple"))

class InteractionSystem(System):
    """상호작용 이벤트(InteractEvent)를 처리하는 시스템"""
    def process(self):
        pass # Event-driven system

    def handle_interact_event(self, event):
        entity_id = event.who
        target_id = event.target
        action = event.action # "TOGGLE" etc.
        
        target = self.world.get_entity(target_id)
        if not target: return
        
        entity = self.world.get_entity(entity_id)
        
        # 1. 스위치(레버/문) 상호작용
        switch = target.get_component(SwitchComponent)
        if switch and action == "TOGGLE":
            # 문 함정 체크 (문을 열기 전)
            door_comp = target.get_component(DoorComponent)
            if door_comp and door_comp.has_trap and not door_comp.is_open:
                self._trigger_door_trap(entity, door_comp)
                door_comp.has_trap = False  # 1회 발동 후 소멸
            
            self._handle_switch_toggle(target, switch)

    def _handle_switch_toggle(self, entity, switch):
        """스위치/레버/문 토글 처리"""
        # 잠김 확인
        if switch.locked:
            # 키 확인 로직 (플레이어 인벤토리 등)
            player = self.world.get_player_entity()
            has_key = False
            if player and switch.key_name:
                inv = player.get_component(InventoryComponent)
                if inv:
                    # 인벤토리에서 키 찾기 (구현 필요, 일단은 PASS or Message)
                    # 여기서는 간단히 메시지만 출력하고 리턴
                    pass
            
            if not has_key:
                self.event_manager.push(MessageEvent(_("잠겨있습니다. 열쇠가 필요합니다."), "gray"))
                return

        # 상태 변경
        switch.is_open = not switch.is_open
        
        # 시각적 변경 (RenderComponent char 변경 등)
        render = entity.get_component(RenderComponent)
        if render:
            if switch.is_open:
                render.char = "'" if render.char == "+" else "/" # 문이면 ', 레버면 / 유지?
                # 레버의 경우 보통 모양이 바뀌진 않고 색이나 메시지로 피드백
                if render.char == '/': 
                    render.char = '\\' # 레버 젖혀짐
            else:
                if render.char == "'": render.char = "+"
                if render.char == "\\": render.char = "/"

        # BlockMapComponent 업데이트
        block = entity.get_component(BlockMapComponent)
        if block:
            block.blocks_movement = not switch.is_open
            block.blocks_sight = not switch.is_open

        # 효과 메시지
        name = "문" if getattr(render, 'char', '') in ['+', "'"] else "레버"
        state = "열렸습니다" if switch.is_open else "닫혔습니다"
        # 레버인 경우
        if getattr(render, 'char', '') in ['/', '\\']:
            state = "당겨졌습니다" if switch.is_open else "원위치되었습니다"
        
        self.event_manager.push(MessageEvent(_("{}이(가) {}.").format(name, state)))
        self.event_manager.push(SoundEvent("DOOR" if name == "문" else "CLICK"))

        # [Boss Room] Linkage Logic (Lever opens Door)
        if switch.linked_door_pos and switch.is_open:
            lx, ly = switch.linked_door_pos
            # 해당 위치의 문 엔티티 찾기
            entities = self.world.get_entities_with_components({DoorComponent, PositionComponent})
            found_door = False
            for ent in entities:
                pos = ent.get_component(PositionComponent)
                if pos.x == lx and pos.y == ly:
                    door_comp = ent.get_component(DoorComponent)
                    if door_comp:
                        door_comp.is_locked = False
                        door_comp.is_open = True
                        
                        # 시각적 업데이트
                        r = ent.get_component(RenderComponent)
                        if r: r.char = "'"
                        
                        # 물리적 업데이트
                        b = ent.get_component(BlockMapComponent)
                        if b: 
                            b.blocks_movement = False
                            b.blocks_sight = False
                            
                        self.event_manager.push(MessageEvent(_("쿠쿠쿵! 어딘가에서 거대한 문이 열리는 소리가 들립니다!"), "yellow"))
                        self.event_manager.push(SoundEvent("DOOR_OPEN_HEAVY"))
                        found_door = True
                        
                        # [Trap Trigger] 100% Trap Effect on Lever Pull
                        # 레버를 당기면 함정도 같이 발동 (User Request: 100% trap that also opens door)
                        player = self.world.get_player_entity()
                        if player:
                             # 1. 폭발 함정 효과 (Explosion Trap)
                             self.event_manager.push(MessageEvent(_("레버를 당기자 함정이 발동했습니다! 폭발이 일어납니다!"), "red"))
                             self.event_manager.push(SoundEvent("EXPLOSION"))
                             
                             # 데미지 처리
                             p_stats = player.get_component(StatsComponent)
                             if p_stats:
                                 damage_pct = 50 # 50% fixed for this special lever
                                 damage = int(p_stats.max_hp * (damage_pct / 100.0))
                                 p_stats.current_hp -= damage
                                 player.add_component(HitFlashComponent())
                                 self.event_manager.push(MessageEvent(_("폭발으로 인해 {}의 피해를 입었습니다! (HP {}%)").format(damage, damage_pct), "red"))
                        
                        break
            
            if not found_door:
                print(f"DEBUG: Linked door not found at {lx}, {ly}")

        # [Legacy] Linkage Logic via Linked Trap ID (Optional)
        if switch.linked_trap_id:
            pass # 나중에 TrapSystem과 연동 가능


    def _trigger_door_trap(self, victim, door_comp, damage_multiplier: float = 1.0):
        """문 함정 발동 (데미지 배율 지원)"""
        import random
        from .components import PoisonComponent, CurseComponent, HitFlashComponent
        
        is_player = victim.entity_id == self.world.get_player_entity().entity_id
        victim_name = "당신" if is_player else "몬스터"
        stats = victim.get_component(StatsComponent)
        
        # 함정 효과 처리
        if door_comp.trap_type == "POISON_NEEDLE":
            # 독침 함정
            self.event_manager.push(MessageEvent(_("문에서 독침이 튀어나왔습니다!"), "green"))
            self.event_manager.push(SoundEvent("BASH"))
            
            # 독 상태 이상 적용 (틱당 데미지도 Max HP 비례로 할 수 있지만 일단 고정)
            if not victim.has_component(PoisonComponent):
                # 총 데미지가 약 30-50% 되도록 설정 (10틱 * 4% = 40%)
                tick_pct = 4
                tick_damage = max(2, int(stats.max_hp * (tick_pct / 100.0) * damage_multiplier)) if stats else 10
                victim.add_component(PoisonComponent(damage=tick_damage, duration=15.0))
                self.event_manager.push(MessageEvent(_("{}이(가) 중독되었습니다!").format(victim_name), "green"))
            
            victim.add_component(HitFlashComponent())
            
        elif door_comp.trap_type == "EXPLOSION":
            # 폭발 함정
            self.event_manager.push(MessageEvent(_("문이 폭발했습니다!"), "red"))
            self.event_manager.push(SoundEvent("EXPLOSION"))
            
            # 데미지 적용
            if stats:
                damage_pct = random.randint(45, 60) # 50% 내외
                damage = int(stats.max_hp * (damage_pct / 100.0) * damage_multiplier)
                stats.current_hp -= damage
                if stats.current_hp < 0:
                    stats.current_hp = 0
                self.event_manager.push(MessageEvent(_("{}이(가) {}의 피해를 입었습니다! (HP {}%, 감쇄 {}%)").format(victim_name, damage, damage_pct, int((1-damage_multiplier)*100)), "red"))
            
            victim.add_component(HitFlashComponent())
            
        elif door_comp.trap_type == "CURSE":
            # 저주 함정
            self.event_manager.push(MessageEvent(_("문에서 사악한 기운이 뿜어져 나옵니다!"), "magenta"))
            self.event_manager.push(SoundEvent("CURSE"))
            
            # 저주 상태 이상 적용 (공격력/방어력 감소)
            if not victim.has_component(CurseComponent):
                victim.add_component(CurseComponent(duration=30.0))
                self.event_manager.push(MessageEvent(_("{}이(가) 저주에 걸렸습니다!").format(victim_name), "magenta"))
            
        elif door_comp.trap_type == "GAS":
            # 가스 함정
            self.event_manager.push(MessageEvent(_("문에서 독가스가 분출됩니다!"), "green"))
            self.event_manager.push(SoundEvent("GAS"))
            
            # 주변 2칸 범위에 독 구름 생성
            door_pos = None
            entities = self.world.get_entities_with_components({DoorComponent, PositionComponent})
            for ent in entities:
                dc = ent.get_component(DoorComponent)
                if dc == door_comp:
                    door_pos = ent.get_component(PositionComponent)
                    break
            
            if door_pos:
                # 범위 내 모든 엔티티에 독 적용
                all_entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
                for entity in all_entities:
                    e_pos = entity.get_component(PositionComponent)
                    dist = abs(e_pos.x - door_pos.x) + abs(e_pos.y - door_pos.y)
                    
                    if dist <= 2:
                        if not entity.has_component(PoisonComponent):
                            entity.add_component(PoisonComponent(damage=5, duration=10.0))
                            e_is_player = entity.entity_id == self.world.get_player_entity().entity_id
                            e_name = "당신" if e_is_player else "몬스터"
                            self.event_manager.push(MessageEvent(_("{}이(가) 독가스에 중독되었습니다!").format(e_name), "green"))
