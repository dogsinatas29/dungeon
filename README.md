## 7. ECS 아키텍처 전환 및 최종 정리 (2025년 10월 11일)

이전의 절차적/객체 지향적 코드에서 컴포넌트-엔티티-시스템(ECS) 아키텍처로의 전환을 완료했습니다. 이로써 게임의 확장성, 유지보수성, 재사용성이 크게 향상되었습니다.

### 주요 변경 사항

*   **ECS 핵심 로직 분리 완료**:
    *   **`dungeon/player.py`**: 플레이어 클래스가 더 이상 스탯(공격력, 방어력, 치명타 등)이나 인벤토리 데이터를 직접 관리하지 않습니다. 대신 `entity_id`를 통해 `HealthComponent`, `AttackComponent`, `DefenseComponent`, `InventoryComponent` 등의 컴포넌트를 조회하고 수정하도록 변경되었습니다. `gain_exp` 및 `level_up` 메서드도 `EntityManager`를 통해 컴포넌트를 직접 업데이트합니다.
    *   **`dungeon/engine.py`**: 게임의 메인 루프가 `game_over_flag`와 같은 전역 상태 변수 대신 `GameOverSystem`의 `GameOverComponent`를 통해 게임 종료 조건을 확인하도록 변경되었습니다. 렌더링 로직은 `RenderingSystem`으로 완전히 위임되었으며, 아이템 사용, 장착/해제, 루팅, 저장/로드와 같은 복잡한 상호작용 로직은 각각 `InventorySystem` 및 `SaveLoadSystem`으로 분리되었습니다.
    *   **`dungeon/system.py`**:
        *   **`RenderingSystem`**: `PositionComponent`와 `RenderComponent`를 가진 모든 엔티티를 쿼리하여 화면에 그리는 역할을 담당합니다.
        *   **`InventorySystem`**: 아이템 추가/제거, 사용, 장착/해제, 퀵슬롯 관리, 루팅 등 모든 인벤토리 관련 로직을 처리합니다.
        *   **`SaveLoadSystem`**: `EntityManager`에 저장된 모든 엔티티와 컴포넌트를 직렬화하여 저장하고, 게임 로드 시 이를 역직렬화하여 게임 상태를 복원합니다.
    *   **`dungeon/component.py`**: `InventoryComponent`, `ItemUseRequestComponent`, `EquipmentComponent`가 추가되어 인벤토리 및 장비 관련 데이터를 ECS 방식으로 관리합니다.
    *   **`dungeon/data_manager.py`**: `save_game_data` 및 `load_game_data` 함수가 `SaveLoadSystem`과 연동되도록 수정되어 전체 게임 상태 데이터를 효율적으로 직렬화/역직렬화합니다.
    *   **`dungeon/map_manager.py`**: `player_x`, `player_y`, `items_on_map`, `monsters`와 같은 속성들이 제거되고, 해당 데이터는 이제 컴포넌트와 `EntityManager`에 의해 관리됩니다.

*   **최종 레거시 코드 제거**: `player.py`, `monster.py`, `map_manager.py` 등에서 더 이상 사용되지 않는 레거시 속성 및 메서드들이 제거되어 코드베이스가 더욱 간결해지고 ECS 원칙에 부합하게 되었습니다.