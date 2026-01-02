# dungeon/events.py - 모든 게임 이벤트를 정의하는 모듈

from typing import Tuple
from .ecs import Event

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
    def __init__(self, text: str, color: str = None):
        self.text = text
        self.color = color

class MapTransitionEvent(Event):
    """플레이어가 계단 등을 통해 맵을 이동할 때 발생"""
    def __init__(self, target_level: int):
        self.target_level = target_level

class ShopOpenEvent(Event):
    """상인과 충돌 시 상점 UI를 열기 위해 발생"""
    def __init__(self, shopkeeper_id: int):
        self.shopkeeper_id = shopkeeper_id

class ShrineOpenEvent(Event):
    """신전과 충돌 시 신전 UI를 열기 위해 발생"""
    def __init__(self, shrine_id: int):
        self.shrine_id = shrine_id

class DirectionalAttackEvent(Event):
    """플레이어가 특정 방향으로 원거리 공격을 수행할 때 발생"""
    def __init__(self, attacker_id: int, dx: int, dy: int, range_dist: int):
        self.attacker_id = attacker_id
        self.dx = dx
        self.dy = dy
        self.range_dist = range_dist

class SkillUseEvent(Event):
    """플레이어가 스킬을 사용할 때 발생"""
    def __init__(self, attacker_id: int, skill_name: str, dx: int, dy: int = 0, cost: int = None):
        self.attacker_id = attacker_id
        self.skill_name = skill_name
        self.dx = dx
        self.dy = dy
        self.cost = cost # None이면 기본 비용 사용, 값이 있으면 이 값 사용 (0 포함)

class SoundEvent(Event):
    """효과음 재생을 위한 이벤트"""
    def __init__(self, sound_type: str, message: str = ""):
        self.sound_type = sound_type # e.g., 'ATTACK', 'HIT', 'MAGIC', 'CRITICAL', 'STEP', 'COIN'
        self.message = message
        self.type = "SOUND" # SoundSystem에서 식별용

class CombatResultEvent(Event):
    """(혹시 누락된 경우를 대비해 추가하거나 이미 있다면 무시) -> Actually verify logic below"""
    def __init__(self, attacker_id: int, target_id: int, damage: int, is_critical: bool, is_alive: bool):
        self.attacker_id = attacker_id
        self.target_id = target_id
        self.damage = damage
        self.is_critical = is_critical
        self.is_alive = is_alive

class InteractEvent(Event):
    """문, 레버 등과 상호작용할 때 발생"""
    def __init__(self, who: int, target: int, action: str = "TOGGLE"):
        self.who = who
        self.target = target
        self.action = action # "OPEN", "CLOSE", "TOGGLE"

class TrapTriggerEvent(Event):
    """함정이 발동될 때 발생"""
    def __init__(self, trap_entity_id: int, victim_entity_id: int = None, location: Tuple[int, int] = None):
        self.trap_entity_id = trap_entity_id
        self.victim_entity_id = victim_entity_id
        self.location = location
