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

class StatModifierComponent(Component):
    """일시적인 능력치 증감 (버프/디버프)"""
    def __init__(self, str_mod: int = 0, mag_mod: int = 0, dex_mod: int = 0, vit_bonus: int = 0, duration: float = 0.0, source: str = ""):
        self.str_mod = str_mod
        self.mag_mod = mag_mod
        self.dex_mod = dex_mod
        self.vit_mod = vit_bonus # items.csv 헤더가 vit_bonus이므로 호환성 유지
        self.duration = duration
        self.expires_at = 0.0 # TimeSystem에서 설정됨
        self.source = source

class StatsComponent(Component):
    """전투 및 능력치 데이터 (GEMINI.md 호환)"""
    def __init__(self, max_hp: int, current_hp: int, attack: int, defense: int, max_mp: int = 0, current_mp: int = 0, max_stamina: float = 100.0, current_stamina: float = 100.0, element: str = "NONE", gold: int = 0, base_attack: int = None, base_defense: int = None, 
                 strength: int = 10, mag: int = 10, dex: int = 10, vit: int = 10, attack_min: int = None, attack_max: int = None, defense_min: int = None, defense_max: int = None, **kwargs):
        self.max_hp = max_hp
        self.current_hp = current_hp
        self.attack = attack_max if attack_max is not None else attack
        self.attack_min = attack_min if attack_min is not None else self.attack
        self.attack_max = attack_max if attack_max is not None else self.attack
        self.defense = defense_max if defense_max is not None else defense
        self.defense_min = defense_min if defense_min is not None else self.defense
        self.defense_max = defense_max if defense_max is not None else self.defense
        
        # 기본 능력치 (장비 효과 제외)
        self.base_attack = base_attack if base_attack is not None else self.attack
        self.base_attack_min = attack_min if attack_min is not None else self.attack_min
        self.base_attack_max = attack_max if attack_max is not None else self.attack_max
        self.base_defense = base_defense if base_defense is not None else self.defense
        self.base_defense_min = defense_min if defense_min is not None else self.defense_min
        self.base_defense_max = defense_max if defense_max is not None else self.defense_max
        
        # [Fix] Base Max HP/MP for recalc
        self.base_max_hp = max_hp
        self.base_max_mp = max_mp
        
        # 신규 스탯 (STR, MAG, DEX, VIT)
        self.str = strength
        self.mag = mag
        self.dex = dex
        self.vit = vit
        
        # 기본 능력치 저장 (강화/버프 제외 순수 능력치)
        self.base_str = strength
        self.base_mag = mag
        self.base_dex = dex
        self.base_vit = vit
        
        self.max_mp = max_mp
        self.current_mp = current_mp
        self.max_stamina = max_stamina
        self.current_stamina = current_stamina
        self.element = element
        self.gold = gold
        self.weapon_range = 1 # 장착된 무기의 사거리
        self.vision_range = 5 # 기본 시야 반경
        
        # [Diablo 1] 저항력 (Fire, Ice, Lightning, Poison)
        self.res_fire = kwargs.get('res_fire', 0)
        self.res_ice = kwargs.get('res_ice', 0)
        self.res_lightning = kwargs.get('res_lightning', 0)
        self.res_poison = kwargs.get('res_poison', 0)
        self.res_all = kwargs.get('res_all', 0)
        
        # [Affix System] 추가 스탯
        self.damage_percent = 0 # 데미지 % 증가
        self.damage_max_bonus = 0 # 최대 데미지 추가 (of Carnage)
        self.to_hit_bonus = 0   # 명중률 % 증가
        self.life_leech = 0     # 생명력 흡수 (%)
        self.attack_speed = 0   # 공격 속도 (단계)

        # 실시간 액션 관련 (초 단위)
        self.last_action_time = 0.0
        self.action_delay = 0.2 # 기본 공격/이동 쿨다운 (0.2초)
        
        # 어빌리티 플래그 (Set[str])
        # JSON 로딩 시 list로 들어오거나 콤마 구분자 문자열로 들어올 수 있음
        if isinstance(kwargs.get('flags'), list):
            self.flags = set(kwargs['flags'])
        else:
            self.flags = {f.strip().upper() for f in element.split(',') if f.strip()} if isinstance(element, str) and ',' in element else set()
            if isinstance(element, str) and element != "NONE" and ',' not in element:
                self.flags.add(element.upper())
        
        # 기본 플래그 복원
        if isinstance(kwargs.get('base_flags'), list):
            self.base_flags = set(kwargs['base_flags'])
        else:
            self.base_flags = self.flags.copy()
        
        # 특수 상태
        self.sees_hidden = False
        self.sees_hidden_expires_at = 0.0
        
    @property
    def is_alive(self):
        return self.current_hp > 0

    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환 (set은 list로 변환)"""
        data = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        if 'flags' in data and isinstance(data['flags'], set):
            data['flags'] = list(data['flags'])
        if 'base_flags' in data and isinstance(data['base_flags'], set):
            data['base_flags'] = list(data['base_flags'])
        return data

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
    def __init__(self, items: dict = None, equipped: dict = None, item_slots: list = None, skill_slots: list = None, skills: list = None, skill_levels: dict = None, skill_books_read: dict = None):
        self.items = items if items else {}
        self.equipped = equipped if equipped else {}
        self.item_slots = item_slots if item_slots else [None] * 5 # 1~5번 아이템
        self.skill_slots = skill_slots if skill_slots else [None] * 5 # 6~0번 스킬
        self.skills = skills if skills else ["기본 공격"]
        # 스킬 레벨 관리 (Dict[skill_name, level])
        self.skill_levels = skill_levels if skill_levels else {name: 1 for name in self.skills}
        # 스킬북 읽은 횟수 (Dict[skill_name, read_count])
        self.skill_books_read = skill_books_read if skill_books_read else {name: 0 for name in self.skills}

    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환 (ItemDefinition 객체 처리)"""
        serialized_items = {}
        for k, v in self.items.items():
            # v: {'item': ItemDefinition, 'qty': int, 'prefix': str(optional), ...}
            new_v = v.copy()
            if "item" in new_v and hasattr(new_v["item"], "to_dict"):
                new_v["item"] = new_v["item"].to_dict()
            # prefix는 문자열 ID이므로 그대로 저장
            serialized_items[k] = new_v
        
        return {
            "items": serialized_items,
            "equipped": {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.equipped.items()},
            "item_slots": self.item_slots,
            "skill_slots": self.skill_slots,
            "skills": self.skills,
            "skill_levels": self.skill_levels,
            "skill_books_read": self.skill_books_read
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

    def to_dict(self):
        serialized_items = []
        for v in self.items:
            # v: {'item': ItemDefinition, 'qty': int, ...}
            new_v = v.copy()
            if "item" in new_v and hasattr(new_v["item"], "to_dict"):
                new_v["item"] = new_v["item"].to_dict()
            serialized_items.append(new_v)
        return {
            "items": serialized_items,
            "gold": self.gold
        }

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

    def to_dict(self):
        serialized_items = []
        for v in self.items:
            # v: {'item': ItemDefinition, 'price': int, ...}
            new_v = v.copy()
            if "item" in new_v and hasattr(new_v["item"], "to_dict"):
                new_v["item"] = new_v["item"].to_dict()
            serialized_items.append(new_v)
        return {
            "items": serialized_items
        }

class ShrineComponent(Component):
    """신전 컴포넌트 - 복구 또는 강화 서비스 제공"""
    def __init__(self, is_used: bool = False):
        self.is_used = is_used  # 사용 여부 (한 번 사용하면 소멸)
    
    def to_dict(self):
        return {
            "is_used": self.is_used
        }

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
        self.flags = set(flags) if flags else set() # list 등으로 들어와도 set으로 변환
        self.tick_count = 0 # 시각 효과(깜빡임)를 위한 카운터

    def to_dict(self):
        return {
            "name": self.name,
            "duration": self.duration,
            "damage": self.damage,
            "radius": self.radius,
            "effect_type": self.effect_type,
            "flags": list(self.flags),
            "tick_count": self.tick_count
        }

class HitFlashComponent(Component):
    """피격 시 시각적 피드백(번쩍임)을 위한 컴포넌트"""
    def __init__(self, duration: float = 0.15):
        self.duration = duration

class HiddenComponent(Component):
    """숨겨진 아이템임을 나타내는 컴포넌트 (횃불 등 특수 효과로만 보임)"""
    def __init__(self, blink: bool = True):
        self.blink = blink

class MimicComponent(Component):
    """보물상자로 의태한 몬스터임을 나타내는 컴포넌트"""
    def __init__(self, is_disguised: bool = True):
        self.is_disguised = is_disguised

class TrapComponent(Component):
    """맵에 배치된 함정 컴포넌트"""
    def __init__(self, trap_type: str = "SPIKE", damage: int = 10, effect: str = None, is_triggered: bool = False, visible: bool = False):
        self.trap_type = trap_type
        self.damage = damage
        self.effect = effect
        self.is_triggered = is_triggered
        self.visible = visible # 횃불 등으로 발견 가능

class SleepComponent(Component):
    """수면 상태: 행동 불가, 데미지 입을 시 해제"""
    def __init__(self, duration: float = 5.0):
        self.duration = duration

class PoisonComponent(Component):
    """중독 상태: 일정 시간마다 데미지 입음"""
    def __init__(self, damage: int = 5, duration: float = 10.0):
        self.damage = damage
        self.duration = duration
        self.tick_timer = 1.0 # 1초마다 데미지
