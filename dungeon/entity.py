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

    def get_entities_with(self, *comp_types):
        """
        주어진 모든 컴포넌트를 가진 엔티티들을 반환합니다 (시스템이 사용할 핵심 메서드).
        반환 형식: [(EntityID, [CompInst1, CompInst2, ...]), ...]
        """
        if not comp_types:
            return []

        # 1. 쿼리 최적화: 가장 적은 엔티티를 가진 컴포넌트 타입부터 찾기
        #    (이 부분이 사용자님의 성능 최적화 로직입니다. 그대로 유지합니다.)
        comp_types_sorted = sorted(comp_types, key=lambda t: len(self.components.get(t, {})))
        
        base_entities = set(self.components.get(comp_types_sorted[0], {}).keys())
        if not base_entities:
            return []

        for comp_type in comp_types_sorted[1:]:
            other_entities = set(self.components.get(comp_type, {}).keys())
            base_entities.intersection_update(other_entities)
            if not base_entities:
                return []
                
        # 2. 반환 부분 수정: EntityID와 해당 컴포넌트 인스턴스들을 함께 묶어 반환
        results = []
        for entity_id in base_entities:
            # 쿼리된 컴포넌트 타입(*comp_types*) 순서대로 인스턴스를 가져와 리스트로 만듭니다.
            # (정렬된 comp_types_sorted가 아닌, 입력 순서인 comp_types를 사용해야 시스템에서 정확히 언패킹할 수 있습니다.)
            components = [self.entities[entity_id][t] for t in comp_types]
            results.append((entity_id, components))
            
        return results
