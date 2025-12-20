from dungeon.component import PositionComponent, ColliderComponent, DesiredPositionComponent

# 임시 상수 정의 (엔진에서 사용되는 타일 크기와 일치해야 함)
# 실제 프로젝트에서는 설정 파일 등에서 로드하는 것이 이상적입니다.
TILE_SIZE = 16

def calculate_bounding_box(position: PositionComponent, collider: ColliderComponent) -> tuple[int, int, int, int]:
    """
    엔티티의 현재 위치와 충돌체 정보를 기반으로 AABB (Axis-Aligned Bounding Box) 경계를 계산합니다.
    (x1, y1, x2, y2) 형태의 튜플을 반환합니다.
    """
    # PositionComponent의 (x, y)는 타일 맵 좌표를 가정합니다. 
    # TILE_SIZE를 곱하여 픽셀 좌표로 변환합니다.
    
    # 충돌 영역의 왼쪽 위(x1, y1) 픽셀 좌표
    x1 = position.x * TILE_SIZE + collider.offset_x
    y1 = position.y * TILE_SIZE + collider.offset_y
    
    # 충돌 영역의 오른쪽 아래(x2, y2) 픽셀 좌표
    x2 = x1 + collider.width
    y2 = y1 + collider.height
    
    return x1, y1, x2, y2

def is_aabb_colliding(box1: tuple[int, int, int, int], box2: tuple[int, int, int, int]) -> bool:
    """
    두 AABB 경계 상자 간의 충돌 여부를 확인합니다.
    box = (x1, y1, x2, y2)
    """
    x1_a, y1_a, x2_a, y2_a = box1
    x1_b, y1_b, x2_b, y2_b = box2
    
    # x축 또는 y축에서 겹치지 않으면 충돌이 아님 (SAT 이론의 기본 원리)
    
    # x축 겹침 검사
    x_overlap = x1_a < x2_b and x2_a > x1_b
    
    # y축 겹침 검사
    y_overlap = y1_a < y2_b and y2_a > y1_b
    
    return x_overlap and y_overlap

def check_entity_collision(
    entity_pos: PositionComponent, 
    entity_desired_pos: DesiredPositionComponent, 
    entity_collider: ColliderComponent,
    other_pos: PositionComponent, 
    other_collider: ColliderComponent
) -> bool:
    """
    엔티티가 목표 위치로 이동할 때 다른 엔티티와 충돌하는지 확인합니다.
    
    Args:
        entity_pos: 현재 위치 (PositionComponent)
        entity_desired_pos: 목표 위치 (DesiredPositionComponent)
        entity_collider: 이동하는 엔티티의 충돌체
        other_pos: 다른 엔티티의 현재 위치
        other_collider: 다른 엔티티의 충돌체
        
    Returns:
        충돌이 발생하면 True, 아니면 False
    """
    # 1. 이동할 엔티티의 목표 위치 기반 AABB 계산
    # DesiredPositionComponent의 x, y를 PositionComponent의 x, y 대신 사용하여 
    # 목표 위치에서의 충돌 박스를 계산합니다.
    
    # 임시 PositionComponent를 생성하여 목표 위치의 AABB를 계산합니다.
    temp_pos = PositionComponent(x=entity_desired_pos.x, y=entity_desired_pos.y)
    moving_box = calculate_bounding_box(temp_pos, entity_collider)
    
    # 2. 고정된 다른 엔티티의 현재 위치 기반 AABB 계산
    other_box = calculate_bounding_box(other_pos, other_collider)
    
    # 3. 두 박스 간의 충돌 검사
    return is_aabb_colliding(moving_box, other_box)

# ------------------------------------------------------------------------------
# 타일 맵 충돌을 위한 헬퍼 함수 (필요한 경우)
# ------------------------------------------------------------------------------

def get_colliding_tile_coords(desired_x: int, desired_y: int, collider: ColliderComponent) -> list[tuple[int, int]]:
    """
    엔티티가 목표 위치로 이동했을 때 경계 상자가 겹치는 모든 타일의 맵 좌표를 계산합니다.
    이 함수는 타일 맵 충돌 검사 시 유용합니다.
    """
    
    # 목표 위치를 임시 PositionComponent로 사용하여 AABB 계산 (픽셀 좌표)
    temp_pos = PositionComponent(x=desired_x, y=desired_y)
    x1_pixel, y1_pixel, x2_pixel, y2_pixel = calculate_bounding_box(temp_pos, collider)

    # 겹치는 타일의 맵 좌표 계산 (타일 좌표)
    # 픽셀 좌표를 TILE_SIZE로 나누고 내림하여 타일 인덱스를 얻습니다.
    # 경계 상자 전체를 덮는 타일 범위를 찾습니다.
    
    start_tile_x = x1_pixel // TILE_SIZE
    end_tile_x = (x2_pixel - 1) // TILE_SIZE # x2는 배타적 경계이므로 -1을 합니다.
    
    start_tile_y = y1_pixel // TILE_SIZE
    end_tile_y = (y2_pixel - 1) // TILE_SIZE

    colliding_tiles = []
    for tx in range(start_tile_x, end_tile_x + 1):
        for ty in range(start_tile_y, end_tile_y + 1):
            colliding_tiles.append((tx, ty))
            
    return colliding_tiles