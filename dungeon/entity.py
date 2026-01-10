# dungeon/entity.py

from typing import Tuple # Tuple 임포트 추가
from components import PositionComponent, RenderComponent, ColliderComponent, DoorComponent, KeyComponent, HealthComponent, AttackComponent, DefenseComponent, MovableComponent, NameComponent, AIComponent # 필요한 컴포넌트 임포트
from player import Player # Player 클래스 임포트
from monster import Monster # Monster 클래스 임포트
import data_manager

class EntityManager:
    """모든 엔티티를 관리하고, 컴포넌트를 할당하는 역할."""
    def __init__(self):
        self.next_entity_id = 0
        self.entities = {}        # {ID: {ComponentClass: ComponentInstance}}
        self.components = {}      # {ComponentClass: {ID: ComponentInstance}}

    def create_entity(self):
        """새로운 엔티티(고유 ID)를 생성합니다."""
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        self.entities[entity_id] = {}
        return entity_id

    def add_entity_with_id(self, entity_id: int):
        """특정 ID로 엔티티를 추가합니다. 주로 게임 로드 시 사용됩니다."""
        if entity_id in self.entities:
            import logging
            logging.warning(f"EntityManager: Entity ID {entity_id} already exists. Overwriting.")
        self.entities[entity_id] = {}
        if entity_id >= self.next_entity_id:
            self.next_entity_id = entity_id + 1
        return entity_id

    def destroy_entity(self, entity_id):
        """엔티티를 제거하고 모든 컴포넌트 인덱스에서 제거합니다."""
        if entity_id in self.entities:
            for comp_type in self.entities[entity_id]:
                if entity_id in self.components.get(comp_type, {}):
                    del self.components[comp_type][entity_id]
            del self.entities[entity_id]

    def add_component(self, entity_id, component):
        """엔티티에 컴포넌트 인스턴스를 추가합니다."""
        comp_type = type(component)
        self.entities[entity_id][comp_type] = component
        if comp_type not in self.components:
            self.components[comp_type] = {}
        self.components[comp_type][entity_id] = component

    def get_component(self, entity_id, comp_type):
        """특정 엔티티에서 컴포넌트를 가져옵니다."""
        return self.entities[entity_id].get(comp_type)

    def has_component(self, entity_id, comp_type):
        """엔티티가 특정 컴포넌트 타입을 가지고 있는지 확인합니다."""
        return comp_type in self.entities.get(entity_id, {})

    def remove_component(self, entity_id, comp_type):
        """엔티티에서 컴포넌트를 제거합니다."""
        if entity_id in self.entities and comp_type in self.entities[entity_id]:
            del self.entities[entity_id][comp_type]
            if comp_type in self.components and entity_id in self.components[comp_type]:
                del self.components[comp_type][entity_id]

    def get_components_of_type(self, comp_type):
        """특정 타입의 모든 컴포넌트 인스턴스를 {entity_id: component_instance} 형태로 반환합니다."""
        return self.components.get(comp_type, {})

    def get_entities_with(self, *comp_types):
        """주어진 모든 컴포넌트를 가진 엔티티들을 반환합니다 (시스템이 사용할 핵심 메서드).
        반환 형식: [(EntityID, [CompInst1, CompInst2, ...]), ...]
        """

# TILE CONSTANTS
WALL_CHAR = '#'
FLOOR_CHAR = '.'
DOOR_CLOSED_CHAR = '+'
DOOR_OPEN_CHAR = '/'
KEY_CHAR = 'k'

# === New: Door and Key Entity Functions ===

def make_door(entity_manager: EntityManager, x: int, y: int, map_id: Tuple[int, int], is_locked: bool = True, key_id: str = "default_key"):
    """잠긴/잠기지 않은 문 엔티티를 생성합니다."""
    door_id = entity_manager.create_entity()
    entity_manager.add_component(door_id, PositionComponent(x=x, y=y, map_id=map_id))
    
    char = DOOR_CLOSED_CHAR # 초기에는 닫힌 문 캐릭터
    color = "brown"
    
    entity_manager.add_component(door_id, RenderComponent(symbol=char, color=color))
    entity_manager.add_component(door_id, ColliderComponent(width=1, height=1, is_solid=True)) # 문이 닫혀있으면 움직임 차단
    entity_manager.add_component(door_id, DoorComponent(is_open=False, is_locked=is_locked, key_id=key_id))
    entity_manager.add_component(door_id, NameComponent(name=f"문({key_id})"))
    return door_id

def make_key(entity_manager: EntityManager, x: int, y: int, map_id: Tuple[int, int], key_id: str = "default_key"):
    """문과 연결된 열쇠 아이템 엔티티를 생성합니다."""
    key_entity_id = entity_manager.create_entity()
    entity_manager.add_component(key_entity_id, PositionComponent(x=x, y=y, map_id=map_id))
    entity_manager.add_component(key_entity_id, RenderComponent(symbol=KEY_CHAR, color="gold"))
    entity_manager.add_component(key_entity_id, ColliderComponent(width=1, height=1, is_solid=False)) # 열쇠는 충돌을 막지 않음
    entity_manager.add_component(key_entity_id, KeyComponent(key_id=key_id))
    entity_manager.add_component(key_entity_id, NameComponent(name=f"열쇠({key_id})"))
    entity_manager.add_component(key_entity_id, InteractableComponent(interaction_type='ITEM_PICKUP', data={'item_id': f'key_{key_id}', 'qty': 1})) # 상호작용 가능하도록 추가
    return key_entity_id