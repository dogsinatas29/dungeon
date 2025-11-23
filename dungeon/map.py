# dungeon/map.py

import random
import logging
from typing import List, Tuple, Dict, Any, Optional

# --- Component Imports ---
from .component import PositionComponent, RenderComponent, ColliderComponent, DoorComponent, KeyComponent, InteractableComponent, NameComponent, HealthComponent, AIComponent, InventoryComponent # InventoryComponent 추가
from .entity import EntityManager, make_door, make_key # make_door, make_key 임포트
from . import data_manager 

# --- Tile Definitions ---
WALL_CHAR = '#'
FLOOR_CHAR = '.'
DOOR_CLOSED_CHAR = '+'
DOOR_OPEN_CHAR = '/'
KEY_CHAR = 'k'
EXIT_CHAR = '>' 
START_CHAR = '<'

class Rect:
    """A rectangular room or corridor."""
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    @property
    def center(self):
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2
        return center_x, center_y

    def intersects(self, other):
        """Returns true if this rectangle intersects with another one."""
        return (self.x1 <= other.x2 + 1 and self.x2 >= other.x1 - 1 and # 방 사이에 1칸 여유
                self.y1 <= other.y2 + 1 and self.y2 >= other.y1 - 1)

class DungeonMap:
    def __init__(self, width: int, height: int, rng, dungeon_level_tuple: Tuple[int, int] = (1, 0), ui_instance=None, entity_manager: EntityManager = None):
        self.width = width
        self.height = height
        self.rng = rng
        self.dungeon_level_tuple = dungeon_level_tuple
        self.ui_instance = ui_instance
        self.entity_manager = entity_manager
        
        self.map_data: List[List[str]] = [] 
        self.rooms: List[Rect] = [] 
        self.corridors: List[Tuple[int, int]] = [] 
        
        self.start_x, self.start_y = 0, 0
        self.exit_x, self.exit_y = 0, 0
        self.exit_type = EXIT_CHAR 
        
        self.visited: set[Tuple[int, int]] = set() 
        self.fog_enabled = True 
        
        self.generate_map() 
        
    def generate_map(self):
        """방과 복도를 이용한 던전 맵을 생성합니다."""
        logging.debug("DungeonMap.generate_map: 맵 생성 시작")
        self.map_data = [[WALL_CHAR for _ in range(self.width)] for _ in range(self.height)]
        self.rooms = []
        self.corridors = []

        max_rooms = 10
        min_room_size = 6
        max_room_size = 10

        for r_num in range(max_rooms):
            w = self.rng.randint(min_room_size, max_room_size)
            h = self.rng.randint(min_room_size, max_room_size)
            x = self.rng.randint(1, self.width - w - 1)
            y = self.rng.randint(1, self.height - h - 1)

            new_room = Rect(x, y, w, h)
            
            intersects = False
            for other_room in self.rooms:
                if new_room.intersects(other_room):
                    intersects = True
                    break

            if not intersects:
                self.rooms.append(new_room)
                for y_room in range(new_room.y1, new_room.y2):
                    for x_room in range(new_room.x1, new_room.x2):
                        if 0 <= x_room < self.width and 0 <= y_room < self.height:
                            self.map_data[y_room][x_room] = FLOOR_CHAR
                
                if len(self.rooms) == 1:
                    self.start_x, self.start_y = new_room.center
                else:
                    prev_room_center_x, prev_room_center_y = self.rooms[-2].center
                    new_room_center_x, new_room_center_y = new_room.center

                    if self.rng.randint(0, 1) == 1:
                        self._create_h_tunnel(prev_room_center_x, new_room_center_x, prev_room_center_y)
                        self._create_v_tunnel(prev_room_center_y, new_room_center_y, new_room_center_x)
                    else:
                        self._create_v_tunnel(prev_room_center_y, new_room_center_y, prev_room_center_x)
                        self._create_h_tunnel(prev_room_center_x, new_room_center_x, new_room_center_y)
        
        if self.rooms:
            self.exit_x, self.exit_y = self.rooms[-1].center
            
            # 출구 주변에 잠긴 문 생성 (예시)
            door_x, door_y = self.exit_x, self.exit_y - 1 
            if self.is_valid_tile(door_x, door_y) and self.map_data[door_y][door_x] == FLOOR_CHAR and self.entity_manager:
                make_door(self.entity_manager, door_x, door_y, self.dungeon_level_tuple, is_locked=True, key_id="exit_key")
                # make_key(self.entity_manager, self.rooms[0].center[0], self.rooms[0].center[1], self.dungeon_level_tuple, key_id="exit_key") 
                # 열쇠는 DungeonGenerationSystem에서 배치할 예정이므로 여기서는 주석 처리

        logging.debug("DungeonMap.generate_map: 맵 생성 완료")

    def _create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.map_data[y][x] = FLOOR_CHAR
                self.corridors.append((x, y))

    def _create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.map_data[y][x] = FLOOR_CHAR
                self.corridors.append((x, y))

    def is_valid_tile(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        if not self.is_valid_tile(x, y):
            return True 
        return self.map_data[y][x] == WALL_CHAR

    def get_tile_for_display(self, x: int, y: int) -> str:
        """주어진 좌표의 타일 문자를 렌더링을 위해 반환합니다."""
        if not self.is_valid_tile(x, y):
            return f"{ANSI.BLUE}{WALL_CHAR}{ANSI.RESET}" 

        if self.fog_enabled and (x, y) not in self.visited:
            return f"{ANSI.BLACK}{FLOOR_CHAR}{ANSI.RESET}" 

        char = self.map_data[y][x]
        color = ANSI.WHITE

        if char == WALL_CHAR:
            color = ANSI.BLUE
        elif char == FLOOR_CHAR:
            color = ANSI.WHITE 
        
        # 엔티티 렌더링은 Engine의 RenderingSystem에서 처리해야 함
        # 여기서는 기본 맵 타일만 반환

        return f"{color}{char}{ANSI.RESET}"

    def reveal_tiles(self, center_x: int, center_y: int, radius: int = 5):
        """지정된 중심점으로부터 반경 내의 타일을 방문 처리합니다."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = center_x + dx, center_y + dy
                if (x - center_x)**2 + (y - center_y)**2 <= radius**2: 
                    if self.is_valid_tile(x, y) and not self._has_line_of_sight(center_x, center_y, x, y): 
                        self.visited.add((x, y))

    def _has_line_of_sight(self, x1, y1, x2, y2) -> bool:
        """두 점 사이에 시야를 가리는 벽이 있는지 확인합니다."""
        points = self._get_line(x1, y1, x2, y2)
        for x, y in points:
            if self.is_wall(x, y):
                return True
        return False

    def _get_line(self, x1, y1, x2, y2) -> List[Tuple[int, int]]:
        """두 점을 잇는 선의 모든 타일 좌표를 반환합니다 (시작점 제외)."""
        line = []
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        
        x, y = x1, y1
        
        while True:
            if x != x1 or y != y1: 
                 line.append((x, y))
            
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return line

    def get_monster_at(self, x: int, y: int) -> Optional[int]:
        """주어진 위치에 몬스터 엔티티가 있는지 확인하고 ID를 반환합니다."""
        if not self.entity_manager: return None
        for entity_id, pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
            if pos_comp.x == x and pos_comp.y == y and pos_comp.map_id == self.dungeon_level_tuple:
                if self.entity_manager.has_component(entity_id, HealthComponent) and self.entity_manager.has_component(entity_id, AIComponent):
                    return entity_id
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "map_data": self.map_data, 
            "dungeon_level_tuple": self.dungeon_level_tuple,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "exit_x": self.exit_x,
            "exit_y": self.exit_y,
            "exit_type": self.exit_type,
            "visited": list(self.visited),
            "fog_enabled": self.fog_enabled,
            "rooms": [{"x1": r.x1, "y1": r.y1, "x2": r.x2, "y2": r.y2} for r in self.rooms],
            "corridors": self.corridors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], rng, ui_instance=None, entity_manager: EntityManager = None):
        d_map = cls(data["width"], data["height"], rng, data["dungeon_level_tuple"], ui_instance, entity_manager)
        d_map.map_data = data["map_data"]
        d_map.start_x = data["start_x"]
        d_map.start_y = data["start_y"]
        d_map.exit_x = data["exit_x"]
        d_map.exit_y = data["exit_y"]
        d_map.exit_type = data["exit_type"]
        d_map.visited = set(tuple(v) for v in data["visited"])
        d_map.fog_enabled = data["fog_enabled"]
        d_map.rooms = [Rect(r["x1"], r["y1"], r["x2"] - r["x1"], r["y2"] - r["y1"]) for r in data["rooms"]]
        d_map.corridors = data["corridors"]
        return d_map