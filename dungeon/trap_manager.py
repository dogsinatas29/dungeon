# dungeon/trap_manager.py - 함정 시스템 관리 모듈

import csv
import os
import random
from typing import Dict, List
from .ecs import System
from .components import (
    PositionComponent, StatsComponent, TrapComponent, 
    StunComponent, PoisonComponent, HitFlashComponent
)
from .events import MessageEvent, SoundEvent


class TrapDefinition:
    """함정 데이터 정의 클래스"""
    def __init__(self, trap_id: str, name: str, symbol: str, color: str, 
                 trigger_type: str, effect_type: str, damage_min: int, 
                 damage_max: int, radius: int, status_effect: str, 
                 duration: float, flags: str, weight: int, min_level: int):
        self.id = trap_id
        self.name = name
        self.symbol = symbol
        self.color = color
        self.trigger_type = trigger_type  # STEP_ON, PROXIMITY, TIMER
        self.effect_type = effect_type    # SINGLE_TARGET, AREA
        self.damage_min = int(damage_min)
        self.damage_max = int(damage_max)
        self.radius = int(radius)
        self.status_effect = status_effect  # STUN, POISON, NONE
        self.duration = float(duration)
        self.flags = set(flags.split('|')) if flags else set()
        self.weight = int(weight)
        self.min_level = int(min_level)


def load_trap_definitions(data_path: str = None) -> Dict[str, TrapDefinition]:
    """traps.csv 파일에서 함정 정의를 로드합니다."""
    if data_path is None:
        data_path = os.path.join(os.path.dirname(__file__), 'data')
    
    trap_defs = {}
    file_path = os.path.join(data_path, 'traps.csv')
    
    if not os.path.exists(file_path):
        print(f"WARNING: Trap definitions file not found at {file_path}")
        return {}
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                trap_def = TrapDefinition(
                    trap_id=row['ID'],
                    name=row['Name'],
                    symbol=row['Symbol'],
                    color=row['Color'],
                    trigger_type=row['TriggerType'],
                    effect_type=row['EffectType'],
                    damage_min=row['DamageMin'],
                    damage_max=row['DamageMax'],
                    radius=row['Radius'],
                    status_effect=row['StatusEffect'],
                    duration=row['Duration'],
                    flags=row['Flags'],
                    weight=row['Weight'],
                    min_level=row['MinLevel']
                )
                trap_defs[trap_def.id] = trap_def
        
        print(f"Loaded {len(trap_defs)} trap definitions from {file_path}")
        return trap_defs
    except Exception as e:
        print(f"ERROR loading trap definitions: {e}")
        return {}


class TrapSystem(System):
    """함정 발동 및 처리를 담당하는 시스템"""
    def __init__(self, world, trap_definitions: Dict[str, TrapDefinition] = None):
        super().__init__(world)
        self.trap_defs = trap_definitions or {}
    
    def process(self):
        player = self.world.get_player_entity()
        if not player:
            return
        
        player_pos = player.get_component(PositionComponent)
        
        # 위치 컴포넌트가 있는 모든 엔티티 (플레이어, 몬스터)
        entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        # 함정 엔티티
        traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
        
        # 1. STEP_ON 함정 처리 (기존 로직)
        for entity in list(entities):
            e_pos = entity.get_component(PositionComponent)
            for trap_ent in traps:
                t_pos = trap_ent.get_component(PositionComponent)
                trap = trap_ent.get_component(TrapComponent)
                
                # 같은 위치이고 아직 발동되지 않은 함정
                if trap.trigger_type == "STEP_ON" and not trap.is_triggered:
                    if e_pos.x == t_pos.x and e_pos.y == t_pos.y:
                        self._trigger_trap(entity, trap_ent)
        
        # 2. PROXIMITY 함정 처리 (벽 함정)
        for trap_ent in traps:
            trap = trap_ent.get_component(TrapComponent)
            if trap.trigger_type == "PROXIMITY" and not trap.is_triggered:
                t_pos = trap_ent.get_component(PositionComponent)
                
                # 플레이어 및 몬스터 모두 감지 대상에 포함
                candidates = self.world.get_entities_with_components({PositionComponent, StatsComponent})
                
                for candidate in candidates:
                    c_pos = candidate.get_component(PositionComponent)
                    dist = abs(c_pos.x - t_pos.x) + abs(c_pos.y - t_pos.y)
                    
                    if dist <= trap.detection_range:
                        # 발사체 발사 (타겟 지정)
                        self._fire_projectile(trap_ent, candidate)
                        break # 한 번 발동하면 루프 종료
        
        # 3. 자동 리셋 함정 처리 (압력판 등)
        import time
        current_time = time.time()
        for trap_ent in traps:
            trap = trap_ent.get_component(TrapComponent)
            if trap.is_triggered and trap.auto_reset:
                if current_time - trap.last_trigger_time >= trap.reset_delay:
                    trap.is_triggered = False
                    # 시각적 복구 (숨겨진 함정은 다시 숨김)
                    if 'HIDDEN' in self.trap_defs.get(trap.trap_type, TrapDefinition("", "", "", "", "", "", 0, 0, 0, "", 0, "", 0, 1)).flags:
                        trap.visible = False

    def _trigger_trap(self, victim, trap_ent, damage_multiplier: float = 1.0):
        """함정 발동 효과 처리 (데미지 배율 지원)"""
        trap = trap_ent.get_component(TrapComponent)
        stats = victim.get_component(StatsComponent)
        
        # 함정 정의 가져오기
        trap_def = self.trap_defs.get(trap.trap_type)
        
        # 함정 발동 표시
        import time
        trap.is_triggered = True
        trap.visible = True
        trap.last_trigger_time = time.time()
        
        # 사운드 및 메시지
        self.event_manager.push(SoundEvent("BASH", f"철컥! 함정이 발동되었습니다! ({trap.trap_type})"))
        
        is_player = victim.entity_id == self.world.get_player_entity().entity_id
        victim_name = "당신" if is_player else self.world.engine._get_entity_name(victim)
        
        # 0. REMOTE 타입 처리 (압력판)
        if trap_def and trap_def.effect_type == "REMOTE":
            if trap.linked_trap_pos:
                lx, ly = trap.linked_trap_pos
                # 해당 위치의 원격 함정 찾기
                remote_traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
                for rt_ent in remote_traps:
                    rt_pos = rt_ent.get_component(PositionComponent)
                    if rt_pos.x == lx and rt_pos.y == ly:
                        rt_c = rt_ent.get_component(TrapComponent)
                        if rt_c.trigger_type == "PROXIMITY":
                            self._fire_projectile(rt_ent, victim)
                        else:
                            self._trigger_trap(victim, rt_ent)
                        break
            # 압력판 자체 데미지는 없으므로 리턴
            return

        # 데미지 계산 및 적용 (최대 HP 퍼센트 기반)
        damage_pct = random.randint(trap.damage_min, trap.damage_max)
        damage = int(stats.max_hp * (damage_pct / 100.0) * damage_multiplier)
        
        # 최소 데미지 보장
        if damage < 5 and damage_pct > 0: damage = 5
        
        stats.current_hp -= damage
        if stats.current_hp < 0:
            stats.current_hp = 0
        
        # [Visual Effect] 치명적 피해 시 화면 테두리 붉은색 효과 (20% 이상 피해)
        if is_player and damage >= stats.max_hp * 0.2:
            from .dungeon.ui import ConsoleUI
            ui = getattr(self.world.engine, 'ui', None)
            if ui:
                ui.blood_overlay_timer = 10 # 약 1~2초간 지속

        # [Log Enhancement] 플레이어와 몬스터 메시지 구분
        if is_player:
            self.event_manager.push(MessageEvent(f"당신은 {trap.trap_type} 함정에 걸려 최대 체력의 {damage_pct}% 피해를 입었습니다!", "red"))
        else:
            self.event_manager.push(MessageEvent(f"{victim_name}이(가) {trap.trap_type} 함정에 걸려 {damage}의 피해를 입었습니다!", "red"))
        
        # 상태 이상 적용
        if trap.effect == "STUN":
            victim.add_component(StunComponent(duration=2.0))
            self.event_manager.push(MessageEvent(f"{victim_name}이(가) 기절했습니다!", "yellow"))
        elif trap.effect == "POISON":
            if not victim.has_component(PoisonComponent):
                victim.add_component(PoisonComponent(damage=5, duration=10.0))
                self.event_manager.push(MessageEvent(f"{victim_name}이(가) 중독되었습니다!", "green"))
        
        # 시각적 피드백
        victim.add_component(HitFlashComponent())
        
        # 범위 효과 (AREA 타입) - trap_def에서 확인
        if trap_def and trap_def.effect_type == "AREA" and trap_def.radius > 0:
            self._apply_area_damage(trap_ent, damage, trap_def.radius)
    
    def _apply_area_damage(self, trap_ent, base_damage: int, radius: int, damage_multiplier: float = 1.0):
        """범위 피해 적용"""
        t_pos = trap_ent.get_component(PositionComponent)
        entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        
        for entity in entities:
            e_pos = entity.get_component(PositionComponent)
            dist = abs(e_pos.x - t_pos.x) + abs(e_pos.y - t_pos.y)
            
            # 범위 내이고 함정 위치가 아닌 경우
            if 0 < dist <= radius:
                stats = entity.get_component(StatsComponent)
                # 거리에 따라 피해 감소 및 배율 적용
                damage = int((base_damage // (dist + 1)) * damage_multiplier)
                stats.current_hp -= damage
                if stats.current_hp < 0:
                    stats.current_hp = 0
                
                is_player = entity.entity_id == self.world.get_player_entity().entity_id
                victim_name = "당신" if is_player else self.world.engine._get_entity_name(entity)
                
                # [Log Enhancement] 범위 피해 메시지 구분
                trap = trap_ent.get_component(TrapComponent)
                trap_name = trap.trap_type if trap else "폭발"
                
                if is_player:
                    pct = int((damage / stats.max_hp) * 100) if stats.max_hp > 0 else 0
                    self.event_manager.push(MessageEvent(f"당신은 {trap_name} 함정의 폭발에 휘말려 최대 체력의 {pct}% 피해를 입었습니다!", "red"))
                else:
                    self.event_manager.push(MessageEvent(f"{victim_name}이(가) {trap_name} 폭발에 휘말려 {damage}의 피해를 입었습니다!", "red"))
                
                entity.add_component(HitFlashComponent())

    def _fire_projectile(self, trap_ent, target, damage_multiplier: float = 1.0):
        """벽 함정에서 발사체 발사 (데미지 배율 지원)"""
        import time
        from .components import RenderComponent, EffectComponent
        
        trap = trap_ent.get_component(TrapComponent)
        t_pos = trap_ent.get_component(PositionComponent)
        target_pos = target.get_component(PositionComponent)
        
        # 함정 발동 표시
        trap.is_triggered = True
        trap.last_trigger_time = time.time()
        
        # 사운드 및 메시지
        self.event_manager.push(SoundEvent("BASH", f"벽에서 발사체가 날아옵니다!"))
        self.event_manager.push(MessageEvent(f"벽 함정이 발동되었습니다! ({trap.trap_type})", "yellow"))
        
        # 발사 방향 결정
        if trap.direction:
            # 지정된 방향으로 발사
            direction_map = {
                'NORTH': (0, -1),
                'SOUTH': (0, 1),
                'EAST': (1, 0),
                'WEST': (-1, 0)
            }
            dx, dy = direction_map.get(trap.direction, (0, 0))
        else:
            # 타겟 방향으로 발사
            dx = 1 if target_pos.x > t_pos.x else (-1 if target_pos.x < t_pos.x else 0)
            dy = 1 if target_pos.y > t_pos.y else (-1 if target_pos.y < t_pos.y else 0)
        
        # 발사체 애니메이션 및 데미지 적용
        max_range = trap.detection_range
        for dist in range(1, max_range + 1):
            proj_x = t_pos.x + (dx * dist)
            proj_y = t_pos.y + (dy * dist)
            
            # 맵 경계 체크
            map_entities = self.world.get_entities_with_components({MapComponent})
            if map_entities:
                from .components import MapComponent
                map_comp = map_entities[0].get_component(MapComponent)
                if not (0 <= proj_x < map_comp.width and 0 <= proj_y < map_comp.height):
                    break
                if map_comp.tiles[proj_y][proj_x] == '#':
                    break
            
            # 발사체 이펙트 생성
            effect = self.world.create_entity()
            self.world.add_component(effect.entity_id, PositionComponent(x=proj_x, y=proj_y))
            effect_char = '-' if dx != 0 else '|'
            self.world.add_component(effect.entity_id, RenderComponent(char=effect_char, color='yellow'))
            self.world.add_component(effect.entity_id, EffectComponent(duration=0.1))
            
            # 즉시 렌더링 (애니메이션 효과)
            if hasattr(self.world, 'engine'):
                self.world.engine._render()
                time.sleep(0.05)
            
            # 엔티티와 충돌 체크
            entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
            for entity in entities:
                e_pos = entity.get_component(PositionComponent)
                if e_pos.x == proj_x and e_pos.y == proj_y:
                    # 데미지 적용 (최대 HP 퍼센트 기반)
                    stats = entity.get_component(StatsComponent)
                    damage_pct = random.randint(trap.damage_min, trap.damage_max)
                    damage = int(stats.max_hp * (damage_pct / 100.0) * damage_multiplier)
                    
                    if damage < 5 and damage_pct > 0: damage = 5
                    
                    stats.current_hp -= damage
                    if stats.current_hp < 0:
                        stats.current_hp = 0
                    
                    is_player = entity.entity_id == self.world.get_player_entity().entity_id
                    victim_name = "당신" if is_player else self.world.engine._get_entity_name(entity)
                    
                    if is_player:
                        self.event_manager.push(MessageEvent(f"당신은 {trap.trap_type} 발사체에 맞아 최대 체력의 {damage_pct}% 피해를 입었습니다!", "red"))
                    else:
                        self.event_manager.push(MessageEvent(f"{victim_name}이(가) {trap.trap_type} 발사체에 맞아 {damage}의 피해를 입었습니다!", "red"))
                    
                    # 상태 이상 적용
                    if trap.effect == "STUN":
                        entity.add_component(StunComponent(duration=1.0))
                        self.event_manager.push(MessageEvent(f"{victim_name}이(가) 기절했습니다!", "yellow"))
                    
                    # 시각적 피드백
                    entity.add_component(HitFlashComponent())
                    
                    # 발사체 소멸
                    self.world.delete_entity(effect.entity_id)
                    return
            
            # 이펙트 제거
            self.world.delete_entity(effect.entity_id)
