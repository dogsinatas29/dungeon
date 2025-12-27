# dungeon/ecs.py

from typing import Dict, List, Set, Type, Any

# --- 1.1 기본 구성 요소 (Core ECS) ---

class Component:
    """엔티티에 부착되는 데이터 컨테이너"""
    pass

class Entity:
    """게임 내 모든 객체를 나타내며, 컴포넌트들의 묶음"""
    def __init__(self, entity_id: int):
        self.entity_id = entity_id
        # 컴포넌트 타입별로 인스턴스 리스트 저장 (여러 보너스/상태이상 중첩 지원)
        self._components: Dict[Type[Component], List[Component]] = {}

    def add_component(self, component: Component, overwrite: bool = False):
        """컴포넌트를 추가합니다. overwrite=True이면 기존 동일 타입 컴포넌트를 제거하고 추가합니다."""
        c_type = type(component)
        if overwrite or c_type not in self._components:
            self._components[c_type] = [component]
        else:
            self._components[c_type].append(component)
        # 역방향 참조 (편의용)
        if hasattr(component, 'entity'):
            component.entity = self

    def remove_component(self, component_type: Type[Component]):
        """해당 타입의 모든 컴포넌트를 제거합니다."""
        if component_type in self._components:
            del self._components[component_type]

    def remove_component_instance(self, component: Component):
        """특정 컴포넌트 인스턴스 하나만 제거합니다."""
        c_type = type(component)
        if c_type in self._components:
            if component in self._components[c_type]:
                self._components[c_type].remove(component)
                if not self._components[c_type]:
                    del self._components[c_type]

    def get_component(self, component_type: Type[Component]) -> Component | None:
        """해당 타입의 첫 번째 컴포넌트를 반환합니다."""
        comps = self._components.get(component_type)
        return comps[0] if comps else None

    def get_components(self, component_type: Type[Component]) -> List[Component]:
        """해당 타입의 모든 컴포넌트 인스턴스 리스트를 반환합니다."""
        return self._components.get(component_type, [])

    def has_component(self, component_type: Type[Component]) -> bool:
        """해당 타입의 컴포넌트가 하나라도 있는지 확인합니다."""
        return component_type in self._components and len(self._components[component_type]) > 0

class Event:
    """시스템 간 통신을 위한 메시지"""
    pass

class System:
    """
    특정 컴포넌트 묶음을 가진 엔티티에 게임 로직을 실행하는 클래스.
    모든 시스템은 process 메서드를 가져야 합니다.
    """
    _required_components: Set[Type[Component]] = set()

    def __init__(self, world: Any):
        self.world = world
        self.event_manager = world.event_manager

    def process(self):
        """매 턴(프레임)마다 실행될 게임 로직"""
        raise NotImplementedError

# --- 1.2 이벤트 관리자 (Event Manager) ---

class EventManager:
    """이벤트를 구독하고 발행하는 중앙 집중식 관리자"""
    def __init__(self):
        # {EventType: [handler1, handler2, ...]}
        self.listeners: Dict[Type[Event], List[Any]] = {}
        self.event_queue: List[Event] = []

    def register(self, event_type: Type[Event], listener: Any):
        """특정 이벤트 타입에 대한 핸들러(리스너)를 등록"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def push(self, event: Event):
        """이벤트 큐에 이벤트를 추가"""
        self.event_queue.append(event)

    def process_events(self):
        """큐에 쌓인 모든 이벤트를 처리하고 큐를 비움"""
        while self.event_queue:
            event = self.event_queue.pop(0)
            event_type = type(event)
            
            if event_type in self.listeners:
                # 이벤트 리스너의 메서드 이름 규칙: handle_snake_case (예: MessageEvent -> handle_message_event)
                class_name = event_type.__name__
                # CamelCase to snake_case
                import re
                snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                handler_name = f"handle_{snake_name}"
                
                # 하위 호환성을 위해 이전 방식(handle_messageevent)도 체크 가능하지만, 
                # 현재 코드베이스가 모두 언더바를 사용하므로 언더바 방식으로 통일
                
                for listener in self.listeners[event_type]:
                    handler = getattr(listener, handler_name, None)
                    # 만약 언더바 버전이 없으면 언더바 없는 버전도 시도
                    if not handler:
                        old_handler_name = f"handle_{class_name.lower()}"
                        handler = getattr(listener, old_handler_name, None)
                        
                    if handler:
                        handler(event)

# --- 1.3 월드 (World) ---

class World:
    """엔티티, 컴포넌트, 시스템을 통합 관리하는 컨테이너"""
    def __init__(self, engine: Any):
        self._next_entity_id = 1
        self._entities: Dict[int, Entity] = {}
        self._systems: List[System] = []
        self.event_manager = EventManager()
        self.engine = engine # Engine 인스턴스 참조

    def create_entity(self) -> Entity:
        entity_id = self._next_entity_id
        entity = Entity(entity_id)
        self._entities[entity_id] = entity
        self._next_entity_id += 1
        return entity

    def delete_entity(self, entity_id: int):
        """엔티티를 월드에서 영구적으로 제거합니다."""
        if entity_id in self._entities:
            del self._entities[entity_id]

    def add_component(self, entity_id: int, component: Component, overwrite: bool = False):
        if entity_id in self._entities:
            self._entities[entity_id].add_component(component, overwrite)

    def remove_component(self, entity_id: int, component_type: Type[Component]):
        if entity_id in self._entities:
            self._entities[entity_id].remove_component(component_type)

    def get_entity(self, entity_id: int) -> Entity | None:
        return self._entities.get(entity_id)

    def get_player_entity(self) -> Entity | None:
        """플레이어 엔티티를 찾아서 반환 (일반적으로 첫 번째 엔티티가 플레이어)"""
        if not self._entities:
            return None
        return self._entities.get(1) # 플레이어 ID를 1로 가정

    def get_entities_with_components(self, component_types: Set[Type[Component]]) -> List[Entity]:
        """필수 컴포넌트를 모두 가진 엔티티 목록을 반환"""
        results = []
        for entity in self._entities.values():
            has_all = True
            for comp_type in component_types:
                if not entity.has_component(comp_type):
                    has_all = False
                    break
            if has_all:
                results.append(entity)
        return results

    def add_system(self, system: System):
        """시스템을 등록하고 이벤트 리스너로 등록"""
        self._systems.append(system)
        
        # 시스템이 처리할 이벤트 타입을 EventManager에 등록
        for event_type in self.event_manager.listeners.keys():
            class_name = event_type.__name__
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            handler_name = f"handle_{snake_name}"
            
            if hasattr(system, handler_name):
                self.event_manager.register(event_type, system)
            else:
                # 하위 호환성 (언더바 없는 버전)
                old_handler_name = f"handle_{class_name.lower()}"
                if hasattr(system, old_handler_name):
                    self.event_manager.register(event_type, system)

    def process_systems(self):
        """등록된 모든 시스템의 process 메서드를 순차적으로 실행"""
        for system in self._systems:
            system.process()

# --- World 초기화 시 이벤트 리스너 등록을 위한 헬퍼 함수 ---
def initialize_event_listeners(world: World):
    """모든 시스템을 순회하며 EventManager에 리스너 등록"""
    # 시스템들이 사용할 이벤트 타입 목록을 systems 모듈에서 가져옵니다.
    # 주의: 순환 참조를 막기 위해 함수 내에서 임포트합니다.
    from .systems import (
    InputSystem, MovementSystem, CombatSystem, MonsterAISystem, RenderSystem,
    MessageEvent, CollisionEvent, MoveSuccessEvent, DirectionalAttackEvent, MapTransitionEvent, ShopOpenEvent, SkillUseEvent
)
    
    # EventManager에 이벤트 타입이 등록되어 있어야 함 (빈 리스트라도)
    world.event_manager.listeners[MoveSuccessEvent] = []
    world.event_manager.listeners[CollisionEvent] = []
    world.event_manager.listeners[MessageEvent] = []
    world.event_manager.listeners[DirectionalAttackEvent] = []
    world.event_manager.listeners[MapTransitionEvent] = []
    world.event_manager.listeners[ShopOpenEvent] = []
    world.event_manager.listeners[SkillUseEvent] = []

    for system in world._systems:
        for event_type in world.event_manager.listeners.keys():
            class_name = event_type.__name__
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            handler_name = f"handle_{snake_name}"
            
            if hasattr(system, handler_name):
                world.event_manager.register(event_type, system)
            else:
                old_handler_name = f"handle_{class_name.lower()}"
                if hasattr(system, old_handler_name):
                    world.event_manager.register(event_type, system)
