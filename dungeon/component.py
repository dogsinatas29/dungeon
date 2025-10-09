# component.py
from dataclasses import dataclass, field

# 1. 위치 및 외형
@dataclass
class PositionComponent:
    """엔티티의 위치와 맵 ID를 저장합니다."""
    x: int
    y: int
    map_id: str = "1F"  # 현재 맵의 ID (예: 1층)

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
    """스킬 사용 자원 정보를 저장합니다."""
    max_mp: int
    current_mp: int

# 3. 속성 및 전투 관련
@dataclass
class AttackComponent:
    """물리 공격 능력치."""
    base_damage: int
    defense: int

@dataclass
class ElementalComponent: # attribute.py의 내용을 component로 가져와도 좋습니다.
    """아이템, 스킬, 몬스터의 속성 (물, 불 등)."""
    element_type: str # 'FIRE', 'WATER', 'NONE'
    resistance: dict = field(default_factory=dict) # {"FIRE": 0.5, "WATER": 1.2}
