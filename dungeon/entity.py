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

    def get_entities_with(self, *comp_types):
        """주어진 모든 컴포넌트를 가진 엔티티들을 반환합니다 (시스템이 사용할 핵심 메서드)."""
        if not comp_types:
            return []

        # 가장 적은 엔티티를 가진 컴포넌트 타입부터 찾기
        comp_types = sorted(comp_types, key=lambda t: len(self.components.get(t, {})))
        
        # 가장 작은 컴포넌트 셋을 기준으로 교집합 찾기
        base_entities = set(self.components.get(comp_types[0], {}).keys())
        if not base_entities:
            return []

        for comp_type in comp_types[1:]:
            other_entities = set(self.components.get(comp_type, {}).keys())
            base_entities.intersection_update(other_entities)
            if not base_entities:
                return []
                
        return list(base_entities)
