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
        self._components: Dict[Type[Component], Component] = {}

    def add_component(self, component: Component):
        self._components[type(component)] = component

    def remove_component(self, component_type: Type[Component]):
        if component_type in self._components:
            del self._components[component_type]

    def get_component(self, component_type: Type[Component]) -> Component | None:
        return self._components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        return component_type in self._components

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
                # 이벤트 리스너의 메서드 이름 규칙: handle_[event_type_name]
                handler_name = f"handle_{event_type.__name__.lower()}"
                
                for listener in self.listeners[event_type]:
                    handler = getattr(listener, handler_name, None)
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

    def add_component(self, entity_id: int, component: Component):
        if entity_id in self._entities:
            self._entities[entity_id].add_component(component)

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
            handler_name = f"handle_{event_type.__name__.lower()}"
            if hasattr(system, handler_name):
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
    from .systems import MoveSuccessEvent, CollisionEvent, MessageEvent 
    
    # EventManager에 이벤트 타입이 등록되어 있어야 함 (빈 리스트라도)
    world.event_manager.listeners[MoveSuccessEvent] = []
    world.event_manager.listeners[CollisionEvent] = []
    world.event_manager.listeners[MessageEvent] = [] # 메시지 이벤트 추가

    for system in world._systems:
        for event_type in world.event_manager.listeners.keys():
            handler_name = f"handle_{event_type.__name__.lower()}"
            if hasattr(system, handler_name):
                world.event_manager.register(event_type, system)
