from dataclasses import dataclass, field
from typing import Dict, Any

# 1. 위치 및 외형
@dataclass
class PositionComponent:
    """엔티티의 위치와 맵 ID를 저장합니다."""
    x: int
    y: int
    map_id: str = "1F"  # 현재 맵의 ID (예: 1층)

@dataclass
class MovableComponent:
    """이 엔티티는 이동할 수 있다는 능력을 정의합니다."""
    pass

@dataclass
class MoveRequestComponent:
    """엔티티에게 다음 프레임에 (dx, dy)만큼 이동해 달라고 요청하는 이벤트/데이터."""
    entity_id: int
    dx: int
    dy: int
    # original_y 필드는 MovementSystem에서 PositionComponent.y를 사용하면 되므로 제거

@dataclass
class DesiredPositionComponent:
    """엔티티가 이동하고자 하는 목표 위치를 저장합니다. CollisionSystem이 검사합니다."""
    x: int
    y: int
    original_x: int = 0  # 이동 전 위치
    original_y: int = 0

@dataclass
class ProjectileComponent:
    """발사체의 속성(데미지, 사거리, 이펙트 등)을 저장합니다."""
    damage: int
    range: int
    current_range: int # 남은 사거리
    shooter_id: int # 발사한 엔티티의 ID
    dx: int # 이동 방향 x
    dy: int # 이동 방향 y
    impact_effect: Dict[str, Any] = field(default_factory=dict) # 충돌 시 이펙트 정보
    skill_def_id: str = None # 어떤 스킬에 의해 발사되었는지 (스킬 정의 ID)

@dataclass
class DamageRequestComponent:
    """엔티티에게 피해를 요청하는 이벤트/데이터."""
    target_id: int
    amount: int
    attacker_id: int = None # 공격한 엔티티의 ID
    skill_id: str = None # 사용된 스킬 ID (선택 사항)

@dataclass
class InteractableComponent:
    """이 엔티티는 플레이어와 상호작용할 수 있다는 능력을 정의합니다."""
    interaction_type: str # 'ITEM', 'STAIRS', 'ROOM_ENTRANCE', 'TRAP' 등
    data: Dict[str, Any] = field(default_factory=dict) # 상호작용에 필요한 추가 데이터

@dataclass
class RenderComponent:
    """엔티티의 외형(터미널 기호)과 색상을 저장합니다."""
    symbol: str
    color: str # ANSI 색상 코드 (예: 'blue', 'red')

# 2. 생명력 및 자원
@dataclass
class HealthComponent:
    """엔티티의 생명력 정보를 저장합니다."""
    max_hp: int
    current_hp: int
    is_alive: bool = True

@dataclass
class ManaComponent:
    """스킬 사용 자원 정보를 저장합니다. (추가됨)"""
    max_mp: int
    current_mp: int

@dataclass
class StaminaComponent:
    """엔티티의 스태미나 정보를 저장합니다."""
    max_stamina: float
    current_stamina: float

@dataclass
class ExperienceComponent:
    """엔티티의 경험치 정보를 저장합니다."""
    current_exp: int
    exp_to_next_level: int

@dataclass
class LevelComponent:
    """엔티티의 레벨 정보를 저장합니다."""
    level: int

# 3. 속성 및 전투 관련
@dataclass
class AttackComponent:
    """엔티티의 공격력 정보를 저장합니다."""
    power: int
    critical_chance: float = 0.05
    critical_damage_multiplier: float = 1.5

@dataclass
class DefenseComponent:
    """엔티티의 방어력 정보를 저장합니다."""
    value: int

@dataclass
class ElementalComponent:
    """아이템, 스킬, 몬스터의 속성 (물, 불 등)."""
    element_type: str # 'FIRE', 'WATER', 'NONE'
    resistance: Dict[str, float] = field(default_factory=dict) # {"FIRE": 0.5, "WATER": 1.2}

@dataclass
class NameComponent:
    """엔티티의 이름을 저장합니다."""
    name: str

@dataclass
class DeathComponent:
    """엔티티가 죽었음을 표시하는 마커 컴포넌트."""
    pass

@dataclass
class GameOverComponent:
    """게임이 종료되었음을 표시하는 마커 컴포넌트."""
    win: bool = False # 승리 여부 (True: 승리, False: 패배)

# 4. 인벤토리 및 장비
@dataclass
class InventoryComponent:
    """엔티티의 인벤토리 데이터를 저장합니다."""
    # {item_id: {'item': Item 객체, 'qty': int}}
    items: Dict[str, Dict[str, Any]] = field(default_factory=dict) 
    # 장착 정보는 EquipmentComponent로 분리됨.

@dataclass
class EquipmentComponent:
    """엔티티의 장비 착용 상태를 저장합니다."""
    # {slot_name: item_id} (예: {'HAND': 'sword_01'})
    equipped_items: Dict[str, str] = field(default_factory=dict)

@dataclass
class QuickSlotComponent:
    """퀵슬롯에 등록된 아이템과 스킬 정보를 저장합니다. (누락된 컴포넌트 추가)"""
    # 1-5번 슬롯: 아이템 ID
    item_slots: Dict[int, str] = field(default_factory=dict)
    # 6-10번 슬롯: 스킬 ID
    skill_slots: Dict[int, str] = field(default_factory=dict)

@dataclass
class SkillComponent:
    """엔티티의 스킬 정보를 저장합니다."""
    skills: Dict[str, Dict[str, Any]] = field(default_factory=dict) # {skill_id: {'level': int, 'exp': int}}
    skill_quick_slots: Dict[int, str] = field(default_factory=dict) # {slot_num: skill_id}

@dataclass
class ItemUseRequestComponent:
    """아이템 사용 요청 이벤트/데이터."""
    entity_id: int
    item_id: str
    target_id: int = None # 사용 대상 (예: 회복 아이템의 경우 플레이어 자신)

@dataclass
class ItemUseRequestComponent:
    """아이템 사용 요청 이벤트/데이터."""
    entity_id: int
    item_id: str
    target_id: int = None # 사용 대상 (예: 회복 아이템의 경우 플레이어 자신)
