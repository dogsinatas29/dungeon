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
        stats = victim.get_component(StatsComponent)
        
        # 함정 정의 가져오기
        trap_def = self.trap_defs.get(trap.trap_type)
        
        # 함정 발동 표시
        trap.is_triggered = True
        trap.visible = True
        
        # 사운드 및 메시지
        self.event_manager.push(SoundEvent("BASH", f"철컥! 함정이 발동되었습니다! ({trap.trap_type})"))
        
        is_player = victim.entity_id == self.world.get_player_entity().entity_id
        victim_name = "당신" if is_player else "몬스터"
        self.event_manager.push(MessageEvent(f"{victim_name}이(가) {trap.trap_type} 함정을 밟았습니다!"))
        
        # 데미지 계산 및 적용
        damage = random.randint(trap.damage_min, trap.damage_max)
        stats.current_hp -= damage
        if stats.current_hp < 0:
            stats.current_hp = 0
        
        self.event_manager.push(MessageEvent(f"{damage}의 피해를 입었습니다!", "red"))
        
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
    
    def _apply_area_damage(self, trap_ent, base_damage: int, radius: int):
        """범위 피해 적용"""
        t_pos = trap_ent.get_component(PositionComponent)
        entities = self.world.get_entities_with_components({PositionComponent, StatsComponent})
        
        for entity in entities:
            e_pos = entity.get_component(PositionComponent)
            dist = abs(e_pos.x - t_pos.x) + abs(e_pos.y - t_pos.y)
            
            # 범위 내이고 함정 위치가 아닌 경우
            if 0 < dist <= radius:
                stats = entity.get_component(StatsComponent)
                # 거리에 따라 피해 감소
                damage = base_damage // (dist + 1)
                stats.current_hp -= damage
                if stats.current_hp < 0:
                    stats.current_hp = 0
                
                is_player = entity.entity_id == self.world.get_player_entity().entity_id
                victim_name = "당신" if is_player else self.world.engine._get_entity_name(entity)
                self.event_manager.push(MessageEvent(f"{victim_name}이(가) 폭발에 휘말려 {damage}의 피해를 입었습니다!", "red"))
                entity.add_component(HitFlashComponent())
