# game_engine.py 또는 entity.py 내부에 정의
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
            # 이미 존재하는 엔티티 ID라면 경고 또는 오류 처리
            import logging
            logging.warning(f"EntityManager: Entity ID {entity_id} already exists. Overwriting.")
        self.entities[entity_id] = {}
        # next_entity_id가 로드된 ID보다 작으면 업데이트하여 충돌 방지
        if entity_id >= self.next_entity_id:
            self.next_entity_id = entity_id + 1
        return entity_id

    def destroy_entity(self, entity_id):
        """엔티티를 제거하고 모든 컴포넌트 인덱스에서 제거합니다."""
        if entity_id in self.entities:
            # 1. Component 인덱스 (self.components)에서 제거
            for comp_type in self.entities[entity_id]:
                if entity_id in self.components.get(comp_type, {}):
                    del self.components[comp_type][entity_id]
            
            # 2. Entity 맵 (self.entities)에서 제거
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
