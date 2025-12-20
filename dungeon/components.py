# dungeon/components.py - 게임 데이터를 정의하는 모듈

# NOTE: 이 파일은 ECS 코어(.ecs)를 임포트해야 합니다.
from .ecs import Component
from typing import List

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
    def __init__(self, max_hp: int, current_hp: int, attack: int, defense: int, max_mp: int = 0, current_mp: int = 0, max_stamina: float = 100.0, current_stamina: float = 100.0):
        self.max_hp = max_hp
        self.current_hp = current_hp
        self.attack = attack
        self.defense = defense
        self.max_mp = max_mp
        self.current_mp = current_mp
        self.max_stamina = max_stamina
        self.current_stamina = current_stamina
        
    @property
    def is_alive(self):
        return self.current_hp > 0

class MonsterComponent(Component):
    """몬스터 유형 식별자"""
    def __init__(self, type_name: str, level: int = 1):
        self.type_name = type_name
    def __init__(self, type_name: str, level: int = 1):
        self.type_name = type_name
        self.level = level

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
    """게임 메시지 로그를 저장하는 컴포넌트"""
    def __init__(self, max_messages: int = 5):
        self.messages: List[str] = []
        self.max_messages = max_messages
        
    def add_message(self, message: str):
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0) # 가장 오래된 메시지 제거
