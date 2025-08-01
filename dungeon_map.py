# dungeon_map.py

import random
from ui import ANSI
from monster import Monster
import data_manager

# --- Tile Definitions ---
BORDER_WALL = '#'
INNER_WALL = '#'
FLOOR = ' '
PLAYER = '@'
START = '<'
EXIT_NORMAL = '>'
EXIT_LOCKED = 'X'
ITEM_TILE = '*'
ROOM_ENTRANCE = '+'

EMPTY_SPACE = ' '
WALL = INNER_WALL

class DungeonMap:
    # --- Constants ---
    MIN_MAP_WIDTH = 60
    MIN_MAP_HEIGHT = 20
    MAX_MAP_WIDTH = 150
    MAX_MAP_HEIGHT = 80
    MAP_GROWTH_LEVEL_INTERVAL = 5
    MAP_GROWTH_AMOUNT_WIDTH = 10
    MAP_GROWTH_AMOUNT_HEIGHT = 5
    BASE_ROOM_WIDTH = 20
    BASE_ROOM_HEIGHT = 10
    ROOM_GROWTH_LEVEL_INTERVAL = 10
    ROOM_GROWTH_AMOUNT = 10
    BASE_NUM_ROOMS = 2
    ROOM_COUNT_LEVEL_INTERVAL = 3
    VIEW_RADIUS = 5

    def __init__(self, dungeon_level_tuple, ui_instance=None, _is_loading=False):
        self.ui_instance = ui_instance
        self.floor, self.room_index = dungeon_level_tuple
        self.width, self.height = 0, 0
        self.map_data = []
        self.start_x, self.start_y = 0, 0
        self.player_x, self.player_y = 0, 0
        self.exit_x, self.exit_y = 0, 0
        self.exit_type = EXIT_NORMAL
        self.required_key_id = None
        self.required_key_count = 0
        self.is_generated = False
        self.visited = set()
        self.items_on_map = {}
        self.monsters = []
        self.room_entrances = {}
        self.fog_enabled = True # 안개 상태 변수 추가
        self.player_tombstone = None # 플레이어 무덤 위치

        if not _is_loading:
            if self.room_index == 0:
                self._generate_main_map()
            else:
                self._generate_sub_room()
            
            self.reveal_tiles(self.player_x, self.player_y)
            self.is_generated = True

    def toggle_fog(self):
        """전장의 안개(Fog of War)를 토글합니다."""
        self.fog_enabled = not self.fog_enabled
        # 안개를 끄면, 모든 타일이 보이게 됨 (get_tile_for_display에서 처리)
        # 안개를 켜면, visited 세트에 있는 타일만 보이게 됨
        return self.fog_enabled

    def reveal_tiles(self, center_x, center_y):
        if not self.fog_enabled:
            return
        for y in range(max(0, center_y - self.VIEW_RADIUS), min(self.height, center_y + self.VIEW_RADIUS + 1)):
            for x in range(max(0, center_x - self.VIEW_RADIUS), min(self.width, center_x + self.VIEW_RADIUS + 1)):
                if (x - center_x)**2 + (y - center_y)**2 <= self.VIEW_RADIUS**2:
                    self.visited.add((x, y))

    def _generate_main_map(self):
        growth_multiplier = (self.floor - 1) // self.MAP_GROWTH_LEVEL_INTERVAL
        self.width = min(self.MIN_MAP_WIDTH + growth_multiplier * self.MAP_GROWTH_AMOUNT_WIDTH, self.MAX_MAP_WIDTH)
        self.height = min(self.MIN_MAP_HEIGHT + growth_multiplier * self.MAP_GROWTH_AMOUNT_HEIGHT, self.MAX_MAP_HEIGHT)
        self.map_data = self._generate_empty_map()
        self._generate_random_map()
        self._place_start_and_exit()
        self._place_room_entrances()

    def _generate_sub_room(self):
        growth_multiplier = (self.floor - 1) // self.ROOM_GROWTH_LEVEL_INTERVAL
        self.width = self.BASE_ROOM_WIDTH + growth_multiplier * self.ROOM_GROWTH_AMOUNT
        self.height = self.BASE_ROOM_HEIGHT + growth_multiplier * self.ROOM_GROWTH_AMOUNT
        self.map_data = self._generate_empty_map()
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                self.map_data[y][x] = FLOOR
        self.start_x = self.width // 2
        self.start_y = self.height - 2
        self.exit_x, self.exit_y = self.start_x, self.start_y
        self.exit_type = EXIT_NORMAL
        self.player_x, self.player_y = self.start_x, self.start_y

    def _place_start_and_exit(self):
        while True:
            sx, sy = random.randint(1, self.width - 2), random.randint(1, self.height - 2)
            if self.map_data[sy][sx] == FLOOR:
                self.start_x, self.start_y = sx, sy
                self.player_x, self.player_y = sx, sy
                break
        while True:
            ex, ey = random.randint(1, self.width - 2), random.randint(1, self.height - 2)
            if self.map_data[ey][ex] == FLOOR and (ex, ey) != (sx, sy):
                self.exit_x, self.exit_y = ex, ey
                self.exit_type = EXIT_NORMAL
                break

    def _place_room_entrances(self):
        num_rooms = self.calculate_num_rooms(self.floor)
        floor_tiles = [(x, y) for y in range(self.height) for x in range(self.width) if self.map_data[y][x] == FLOOR]
        exclusions = {(self.start_x, self.start_y), (self.exit_x, self.exit_y)}
        
        for i in range(1, num_rooms + 1):
            if not floor_tiles: break
            pos = random.choice(floor_tiles)
            floor_tiles.remove(pos)
            if pos not in exclusions:
                self.room_entrances[pos] = i

    def move_player(self, dx, dy):
        new_x, new_y = self.player_x + dx, self.player_y + dy

        # 1. 맵 경계 확인
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            return False, "맵의 끝에 도달했습니다."

        # 2. 목적지에 몬스터가 있는지 확인
        for monster in self.monsters:
            if not monster.dead and monster.x == new_x and monster.y == new_y:
                # 전투 시작, 이동은 하지 않음
                return False, monster

        # 3. 타일 자체가 걸을 수 있는지 확인
        target_tile = self.get_tile(new_x, new_y)
        walkable_tiles = [FLOOR, ITEM_TILE, EXIT_NORMAL, EXIT_LOCKED, ROOM_ENTRANCE, START]
        if target_tile not in walkable_tiles:
            # 벽이나 다른 장애물
            return False, "벽으로 막혀있습니다."

        # 4. 모든 검사를 통과하면 플레이어 이동
        self.player_x = new_x
        self.player_y = new_y
        self.reveal_tiles(self.player_x, self.player_y)
        return True, "이동했습니다."

    def get_tile(self, x, y):
        if (x, y) in self.room_entrances: return ROOM_ENTRANCE
        if (x, y) in self.items_on_map: return ITEM_TILE
        if (x, y) == (self.exit_x, self.exit_y): return self.exit_type
        if (x, y) == (self.start_x, self.start_y): return START
        return self.map_data[y][x]

    def get_tile_for_display(self, x, y):
        # 최종적으로 화면에 표시될 문자열 (ANSI 코드 포함)
        
        # 1. 플레이어 무덤 (최우선 순위)
        if self.player_tombstone and (x, y) == self.player_tombstone:
            return f"{ANSI.WHITE}T{ANSI.RESET}"

        # 2. 몬스터 시체
        # 해당 위치에 죽은 몬스터가 있는지 확인
        is_corpse = any(m.dead for m in self.monsters if (x, y) == (m.x, m.y))
        if is_corpse:
            return f"{ANSI.RED}%{ANSI.RESET}"

        # 3. 정적 타일
        tile = self.get_tile(x, y) # 아이템, 출입구 등 내부 상태를 가져옴
        
        color = ANSI.WHITE # 기본 색상
        char = tile # 기본 문자
        
        if tile == BORDER_WALL:
            color = ANSI.WHITE
        elif tile == INNER_WALL:
            color = ANSI.WHITE # 내부 벽 색상
        elif tile == START:
            char = START
            color = ANSI.CYAN
        elif tile in [EXIT_NORMAL, EXIT_LOCKED]:
            char = tile
            color = ANSI.MAGENTA
        elif tile == ROOM_ENTRANCE:
            char = ROOM_ENTRANCE
            color = ANSI.GREEN
        elif tile == ITEM_TILE:
            char = ITEM_TILE
            color = ANSI.RED
        
        return f"{color}{char}{ANSI.RESET}"

    def calculate_num_rooms(self, floor):
        return self.BASE_NUM_ROOMS + (floor - 1) // self.ROOM_COUNT_LEVEL_INTERVAL

    def is_walkable_for_monster(self, x, y):
        """몬스터가 해당 위치로 이동할 수 있는지 확인합니다."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False  # 맵 범위를 벗어남

        target_tile = self.get_tile(x, y)
        if target_tile not in [FLOOR, START, EXIT_NORMAL, ROOM_ENTRANCE, ITEM_TILE]:
            return False  # 벽이나 기타 장애물

        if (x, y) == (self.player_x, self.player_y):
            return False  # 플레이어 위치
        for m in self.monsters:
            if not m.dead and m.x == x and m.y == y:
                return False  # 다른 몬스터 위치
        return True

    def _generate_empty_map(self):
        return [[INNER_WALL for _ in range(self.width)] for _ in range(self.height)]
    def _generate_random_map(self):
        for y in range(self.height):
            for x in range(self.width):
                if x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1:
                    self.map_data[y][x] = BORDER_WALL
                else:
                    self.map_data[y][x] = FLOOR if random.random() < 0.7 else INNER_WALL
    
    def place_random_items(self, item_definitions, num_items=3):
        if not item_definitions: return
        floor_tiles = [(x, y) for y in range(self.height) for x in range(self.width) if self.map_data[y][x] == FLOOR]
        exclusions = {(self.start_x, self.start_y), (self.exit_x, self.exit_y)}
        exclusions.update(self.room_entrances.keys())
        available_tiles = [tile for tile in floor_tiles if tile not in exclusions]
        item_ids = list(item_definitions.keys())
        for _ in range(min(num_items, len(available_tiles))):
            pos = random.choice(available_tiles)
            available_tiles.remove(pos)
            item_id = random.choice(item_ids)
            self.items_on_map[pos] = {'id': item_id, 'qty': 1}

    def place_monsters(self, monster_definitions, num_monsters=5): # monster_definitions 인자 추가
        if not monster_definitions: return
        floor_tiles = [(x, y) for y in range(self.height) for x in range(self.width) if self.map_data[y][x] == FLOOR]
        exclusions = {(self.start_x, self.start_y), (self.exit_x, self.exit_y)}
        exclusions.update(self.room_entrances.keys())
        exclusions.update(self.items_on_map.keys())
        available_tiles = [tile for tile in floor_tiles if tile not in exclusions]
        
        monster_ids = list(monster_definitions.keys())
        if not monster_ids: return # 정의된 몬스터가 없으면 리턴

        for _ in range(min(num_monsters, len(available_tiles))):
            x, y = random.choice(available_tiles)
            available_tiles.remove((x,y))
            
            # 무작위 몬스터 ID 선택
            monster_id = random.choice(monster_ids)
            self.monsters.append(Monster(x, y, self.ui_instance, monster_id=monster_id)) # monster_id 전달

    def to_dict(self):
        return {
            "dungeon_level_tuple": (self.floor, self.room_index), "width": self.width, "height": self.height,
            "map_data": self.map_data, "start_x": self.start_x, "start_y": self.start_y,
            "player_x": self.player_x, "player_y": self.player_y, "exit_x": self.exit_x, "exit_y": self.exit_y,
            "exit_type": self.exit_type, "visited": list(self.visited), "is_generated": self.is_generated,
            "items_on_map": {f"{k[0]},{k[1]}": v for k, v in self.items_on_map.items()},
            "monsters": [m.to_dict() for m in self.monsters], 
            "room_entrances": {f"{k[0]},{k[1]}": v for k, v in self.room_entrances.items()}
        }
    @classmethod
    def from_dict(cls, data):
        level = tuple(data.get('dungeon_level_tuple', (1, 0)))
        d_map = cls(level, ui_instance=None, _is_loading=True)
        for key, value in data.items():
            if key == "visited": setattr(d_map, key, set(tuple(v) for v in value))
            elif key in ["items_on_map", "room_entrances"]:
                deserialized_dict = {}
                for k_str, v in value.items():
                    x_str, y_str = k_str.split(',')
                    deserialized_dict[(int(x_str), int(y_str))] = v
                setattr(d_map, key, deserialized_dict)
            elif key == "monsters": d_map.monsters = [Monster.from_dict(m_data) for m_data in value]
            elif hasattr(d_map, key): setattr(d_map, key, value)
        return d_map
