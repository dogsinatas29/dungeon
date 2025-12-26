# dungeon/components.py - 게임 데이터를 정의하는 모듈

# NOTE: 이 파일은 ECS 코어(.ecs)를 임포트해야 합니다.
from .ecs import Component
from typing import List, Dict

# --- 플레이어/몬스터 기본 정보 ---
class PositionComponent(Component):
    """엔티티의 현재 맵 위치"""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

class RenderComponent(Component):
    """콘솔에 표시될 문자 및 색상"""
    def __init__(self, char: str, color: str = 'white'):
        self.char = char
        self.color = color

class StatsComponent(Component):
    """전투 및 능력치 데이터 (GEMINI.md 호환)"""
    def __init__(self, max_hp: int, current_hp: int, attack: int, defense: int, max_mp: int = 0, current_mp: int = 0, max_stamina: float = 100.0, current_stamina: float = 100.0, element: str = "NONE", gold: int = 0, base_attack: int = None, base_defense: int = None, **kwargs):
        self.max_hp = max_hp
        self.current_hp = current_hp
        self.attack = attack
        self.defense = defense
        
        # 기본 능력치 (장비 효과 제외)
        self.base_attack = base_attack if base_attack is not None else attack
        self.base_defense = base_defense if base_defense is not None else defense
        
        self.max_mp = max_mp
        self.current_mp = current_mp
        self.max_stamina = max_stamina
        self.current_stamina = current_stamina
        self.element = element
        self.gold = gold
        self.weapon_range = 1 # 장착된 무기의 사거리

        # 실시간 액션 관련 (초 단위)
        self.last_action_time = 0.0
        self.action_delay = 0.2 # 기본 공격/이동 쿨다운 (0.2초)
        
        # 어빌리티 플래그 (Set[str])
        self.flags = {f.strip().upper() for f in element.split(',') if f.strip()} if isinstance(element, str) and ',' in element else set()
        if isinstance(element, str) and element != "NONE" and ',' not in element:
            self.flags.add(element.upper())
        self.base_flags = self.flags.copy()
        
    @property
    def is_alive(self):
        return self.current_hp > 0

    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환"""
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}

class MonsterComponent(Component):
    """몬스터 유형 식별자"""
    def __init__(self, type_name: str, level: int = 1):
        self.type_name = type_name
        self.level = level

class AIComponent(Component):
    """몬스터의 AI 행동 패턴 정의"""
    STATIONARY = 0 # 정지형
    FLEE = 1       # 도망형
    CHASE = 2      # 추적형
    
    def __init__(self, behavior: int = STATIONARY, detection_range: int = 5):
        self.behavior = behavior
        self.detection_range = detection_range

class InventoryComponent(Component):
    """아이템 및 장비 데이터를 저장"""
    def __init__(self, items: dict = None, equipped: dict = None, item_slots: list = None, skill_slots: list = None, skills: list = None):
        self.items = items if items else {}
        self.equipped = equipped if equipped else {}
        self.item_slots = item_slots if item_slots else [None] * 5 # 1~5번 아이템
        self.skill_slots = skill_slots if skill_slots else [None] * 5 # 6~0번 스킬
        self.skills = skills if skills else ["기본 공격"]
        # 스킬 레벨 관리 (Dict[skill_name, level])
        self.skill_levels = {name: 1 for name in self.skills}

    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환 (ItemDefinition 객체 처리)"""
        return {
            "items": {k: {"item": v["item"].to_dict() if hasattr(v["item"], "to_dict") else v["item"], "qty": v["qty"]} for k, v in self.items.items()},
            "equipped": {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.equipped.items()},
            "item_slots": self.item_slots,
            "skill_slots": self.skill_slots,
            "skills": self.skills,
            "skill_levels": self.skill_levels
        }

class LevelComponent(Component):
    """레벨, 경험치, 직업 데이터"""
    def __init__(self, level: int = 1, exp: int = 0, exp_to_next: int = 100, job: str = "Adventurer"):
        self.level = level
        self.exp = exp
        self.exp_to_next = exp_to_next
        self.job = job

# --- 시스템 데이터 ---
class DesiredPositionComponent(Component):
    """
    엔티티가 다음 턴에 이동을 원하는 목표 위치 컴포넌트.
    MovementSystem이 이 컴포넌트를 보고 이동을 시도합니다.
    """
    def __init__(self, dx: int, dy: int):
        # 목표 위치 대신 이동 방향(delta)을 저장합니다.
        self.dx = dx
        self.dy = dy
        
class MapComponent(Component):
    """맵의 타일 데이터"""
    def __init__(self, width: int, height: int, tiles: List[List[str]]):
        self.width = width
        self.height = height
        self.tiles = tiles # tiles[y][x]

class MessageComponent(Component):
    """게임 내 메시지 기록 (전역 데이터)"""
    def __init__(self, max_messages: int = 50):
        self.messages = []
        self.max_messages = max_messages

    def add_message(self, text: str):
        self.messages.append(text)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0) # 가장 오래된 메시지 제거

class LootComponent(Component):
    """루팅 가능한 아이템 정보를 담는 컴포넌트"""
    def __init__(self, items: List[Dict] = None, gold: int = 0):
        self.items = items if items else []  # [{'item': Item, 'qty': 1}, ...]
        self.gold = gold

class CorpseComponent(Component):
    """시체임을 나타내는 컴포넌트"""
    def __init__(self, original_name: str):
        self.original_name = original_name

class ChestComponent(Component):
    """보물상자 컴포넌트"""
    def __init__(self, is_opened: bool = False):
        self.is_opened = is_opened

class ShopComponent(Component):
    """상점 컴포넌트"""
    def __init__(self, items: List[Dict] = None):
        self.items = items if items else [] # 판매 목록

class EffectComponent(Component):
    """임시 시각적 효과 (공격 궤적 등)"""
    def __init__(self, duration: int = 1):
        self.duration = duration # 표시될 턴 수

class StunComponent(Component):
    """스턴 상태: 일정 턴 동안 행동 불가"""
    def __init__(self, duration: int = 1):
        self.duration = duration

class SkillEffectComponent(Component):
    """지속형 스킬 효과 (예: 휠 윈드 오라)"""
    def __init__(self, name: str, duration: int, damage: int, radius: int = 1, effect_type: str = "AURA", flags: set = None):
        self.name = name
        self.duration = duration
        self.damage = damage
        self.radius = radius
        self.effect_type = effect_type
        self.flags = flags if flags else set()
        self.tick_count = 0 # 시각 효과(깜빡임)를 위한 카운터

class HitFlashComponent(Component):
    """피격 시 시각적 피드백(번쩍임)을 위한 컴포넌트"""
    def __init__(self, duration: float = 0.15):
        self.duration = duration
