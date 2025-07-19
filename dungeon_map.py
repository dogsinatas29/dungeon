# dungeon_map.py

import random
from ui import ANSI
from monster import Monster

# 맵 타일 정의
BORDER_WALL = '▓'
INNER_WALL = '▒'
FLOOR = ' '
PLAYER = '@'
START = 'S'

# 출구 타일 정의 변경
EXIT_NORMAL = 'E'
EXIT_LOCKED = 'X'

# 아이템 타일
ITEM_TILE = 'I'

EXPLORED = ' '
EMPTY_SPACE = ' '
WALL = INNER_WALL

class DungeonMap:
    MIN_MAP_WIDTH = 60
    MIN_MAP_HEIGHT = 20
    MAX_MAP_WIDTH = 150
    MAX_MAP_HEIGHT = 80

    MAP_GROWTH_LEVEL_INTERVAL = 5
    MAP_GROWTH_AMOUNT_WIDTH = 10
    MAP_GROWTH_AMOUNT_HEIGHT = 5

    # ui_instance 인자 추가
    def __init__(self, dungeon_level_tuple, ui_instance=None):
        self.ui_instance = ui_instance # UI 인스턴스 저장
        # dungeon_level_tuple은 (floor, room) 형태
        floor = dungeon_level_tuple[0]
        growth_multiplier = floor // self.MAP_GROWTH_LEVEL_INTERVAL # 층에 따라 맵 크기 조절
        
        self.width = min(self.MIN_MAP_WIDTH + growth_multiplier * self.MAP_GROWTH_AMOUNT_WIDTH, self.MAX_MAP_WIDTH)
        self.height = min(self.MIN_MAP_HEIGHT + growth_multiplier * self.MAP_GROWTH_AMOUNT_HEIGHT, self.MAX_MAP_HEIGHT)

        self.map_data = self._generate_empty_map()
        self.start_x = 0
        self.start_y = 0
        self.player_x = 0
        self.player_y = 0
        self.exit_x = 0
        self.exit_y = 0
        self.exit_type = EXIT_NORMAL
        self.required_key_id = None
        self.required_key_count = 0
        self.is_generated = False
        self.visited = set()
        self.items_on_map = {}
        self.monsters = []

    def _generate_empty_map(self):
        return [[INNER_WALL for _ in range(self.width)] for _ in range(self.height)]
        
    def _generate_random_map(self):
        for y in range(self.height):
            for x in range(self.width):
                if x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1:
                    self.map_data[y][x] = BORDER_WALL
                else:
                    self.map_data[y][x] = FLOOR if random.random() < 0.7 else INNER_WALL

    def _place_start_and_exit(self):
        """시작점과 출구를 맵에 배치하고, 주변에 충분한 통로를 확보합니다."""
        while True:
            sx = random.randint(1, self.width // 4)
            sy = random.randint(1, self.height // 4)
            
            is_valid_spot = True
            for y_offset in range(-1, 2):
                for x_offset in range(-1, 2):
                    nx, ny = sx + x_offset, sy + y_offset
                    if not (0 < nx < self.width - 1 and 0 < ny < self.height - 1):
                        is_valid_spot = False
                        break
                if not is_valid_spot:
                    break

            if is_valid_spot:
                for y_offset in range(-1, 2):
                    for x_offset in range(-1, 2):
                        self.map_data[sy + y_offset][sx + x_offset] = FLOOR
                
                self.map_data[sy][sx] = START
                self.start_x, self.start_y = sx, sy
                self.player_x, self.player_y = sx, sy
                self.visited.add((sx, sy))
                break

        while True:
            ex = random.randint(self.width * 3 // 4, self.width - 2)
            ey = random.randint(self.height * 3 // 4, self.height - 2)
            
            is_valid_spot = True
            for y_offset in range(-1, 2):
                for x_offset in range(-1, 2):
                    nx, ny = ex + x_offset, ey + y_offset
                    if not (0 < nx < self.width - 1 and 0 < ny < self.height - 1):
                        is_valid_spot = False
                        break
                if not is_valid_spot:
                    break

            if is_valid_spot and (ex, ey) != (sx, sy):
                for y_offset in range(-1, 2):
                    for x_offset in range(-1, 2):
                        self.map_data[ey + y_offset][ex + x_offset] = FLOOR

                self.exit_x, self.exit_y = ex, ey
                if random.random() < 0.5:
                    self.exit_type = EXIT_LOCKED
                    self.required_key_id = f"{random.randint(1, 5)}F_Key" # 1~5층 키 중 랜덤
                    self.required_key_count = random.randint(1, 3) # 1~3개 랜덤
                    self.map_data[ey][ex] = EXIT_LOCKED
                else:
                    self.exit_type = EXIT_NORMAL
                    self.map_data[ey][ex] = EXIT_NORMAL
                break
        
    def place_random_items(self, item_definitions, num_items=3):
        if self.ui_instance:
            self.ui_instance.add_message("DEBUG (DungeonMap.place_random_items): Starting item placement.")
        
        reachable_tiles = self._get_reachable_tiles()
        # 시작점, 출구는 아이템 배치에서 제외
        reachable_tiles = [tile for tile in reachable_tiles if tile != (self.player_x, self.player_y) and tile != (self.exit_x, self.exit_y)]

        if self.ui_instance:
            self.ui_instance.add_message(f"DEBUG (DungeonMap.place_random_items): Available reachable tiles for items: {len(reachable_tiles)}")

        # 잠긴 문에 필요한 열쇠를 먼저 배치
        if self.exit_type == EXIT_LOCKED and self.required_key_id and self.required_key_count > 0:
            for _ in range(self.required_key_count):
                if not reachable_tiles:
                    if self.ui_instance:
                        self.ui_instance.add_message("DEBUG (DungeonMap.place_random_items): No more reachable tiles to place required keys.")
                    break
                
                place_x, place_y = random.choice(reachable_tiles)
                self.items_on_map[(place_x, place_y)] = {'id': self.required_key_id, 'qty': 1}
                reachable_tiles.remove((place_x, place_y))
                if self.ui_instance:
                    self.ui_instance.add_message(f"DEBUG (DungeonMap.place_random_items): Placed {self.required_key_id} at ({place_x},{place_y}).")

        # 나머지 아이템 배치 로직은 그대로 유지
        other_item_ids = [
            item_id for item_id, item_def in item_definitions.items()
            if item_def and (item_def.usage_type == 'MANUAL' or item_def.usage_type == 'EQUIP')
        ]

        if not other_item_ids:
            if self.ui_instance:
                self.ui_instance.add_message("DEBUG (DungeonMap.place_random_items): No other manual/equip items to place.")
            return

        # 남은 아이템 수 계산 (num_items에서 열쇠 수 제외)
        remaining_items_to_place = num_items - self.required_key_count
        for _ in range(min(remaining_items_to_place, len(reachable_tiles))):
            item_id = random.choice(other_item_ids)
            place_x, place_y = random.choice(reachable_tiles)
            self.items_on_map[(place_x, place_y)] = {'id': item_id, 'qty': 1}
            reachable_tiles.remove((place_x, place_y))
            if self.ui_instance:
                self.ui_instance.add_message(f"DEBUG (DungeonMap.place_random_items): Placed {item_id} at ({place_x},{place_y}).")
            
        if self.ui_instance:
            self.ui_instance.add_message(f"DEBUG (DungeonMap.place_random_items): Final items_on_map (DungeonMap internal): {self.items_on_map}")


    def place_monsters(self, num_monsters=5):
        """맵의 빈 공간에 몬스터를 배치합니다."""
        reachable_tiles = self._get_reachable_tiles()
        # 시작점, 출구, 아이템이 없는 도달 가능한 바닥에만 몬스터 배치
        reachable_tiles = [tile for tile in reachable_tiles if \
                           tile != (self.start_x, self.start_y) and \
                           tile != (self.exit_x, self.exit_y) and \
                           tile not in self.items_on_map]

        for _ in range(min(num_monsters, len(reachable_tiles))):
            x, y = random.choice(reachable_tiles)
            self.monsters.append(Monster(x, y, self.ui_instance))
            reachable_tiles.remove((x, y))
            if self.ui_instance:
                self.ui_instance.add_message(f"DEBUG: Monster placed at ({x}, {y})")

    def get_tile(self, x, y):
        """특정 좌표의 '실제' 타일 유형을 반환합니다. (플레이어 심볼 제외)"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return BORDER_WALL

        if (x, y) in self.items_on_map:
            return ITEM_TILE
        
        if (x, y) == (self.exit_x, self.exit_y):
            return self.exit_type

        return self.map_data[y][x]

    def _get_reachable_tiles(self):
        """플레이어 시작 위치에서 도달 가능한 모든 바닥 타일의 좌표를 반환합니다."""
        reachable = set()
        queue = [(self.start_x, self.start_y)]
        visited_bfs = set([(self.start_x, self.start_y)])

        while queue:
            cx, cy = queue.pop(0)
            reachable.add((cx, cy))

            # 상하좌우 이동
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < self.width and 0 <= ny < self.height and
                    (nx, ny) not in visited_bfs and
                    self.map_data[ny][nx] in [FLOOR, START, EXIT_NORMAL, EXIT_LOCKED]): # 이동 가능한 타일
                    visited_bfs.add((nx, ny))
                    queue.append((nx, ny))
        return list(reachable)

    def can_move(self, dx, dy):
        """플레이어가 이동할 수 있는지 확인합니다."""
        new_x, new_y = self.player_x + dx, self.player_y + dy
        
        if self.ui_instance:
            self.ui_instance.add_message(f"DEBUG (DungeonMap.can_move): Checking move to ({new_x},{new_y}) from ({self.player_x},{self.player_y})")
        
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            if self.ui_instance:
                self.ui_instance.add_message(f"DEBUG (DungeonMap.can_move): Out of bounds.")
            return False

        target_tile_type = self.get_tile(new_x, new_y)
        if self.ui_instance:
            self.ui_instance.add_message(f"DEBUG (DungeonMap.can_move): Target tile type: '{target_tile_type}'")

        movable_tiles = [FLOOR, START, ITEM_TILE, EXIT_NORMAL, EXIT_LOCKED]
        
        if target_tile_type in movable_tiles:
            if self.ui_instance:
                self.ui_instance.add_message(f"DEBUG (DungeonMap.can_move): Move allowed. Target in {movable_tiles}")
            return True
        else:
            if self.ui_instance:
                self.ui_instance.add_message(f"DEBUG (DungeonMap.can_move): Move denied. Target '{target_tile_type}' not in {movable_tiles}")
            return False

    def move_player(self, dx, dy):
        """플레이어를 이동시키고, 지나온 길을 기록합니다."""
        if not self.can_move(dx, dy):
            target_x, target_y = self.player_x + dx, self.player_y + dy
            tile_type = self.get_tile(target_x, target_y)
            return False, f"이동 불가능: ({target_x},{target_y})는 '{tile_type}'입니다. 벽이거나 갈 수 없는 길입니다."

        self.player_x += dx
        self.player_y += dy
        self.visited.add((self.player_x, self.player_y))
        
        return True, "이동했습니다."

    def get_tile_for_display(self, x, y, player_x, player_y):
        """
        주어진 (x,y) 좌표에 대해 맵에 표시할 실제 캐릭터를 반환합니다.
        플레이어, 아이템, 출구 등 시각적인 요소를 포함합니다.
        """
        if (x, y) == (player_x, player_y):
            return PLAYER
        
        # 몬스터를 플레이어보다 먼저 그려서, 플레이어가 몬스터 위에 설 수 있도록 함
        for monster in self.monsters:
            if not monster.dead and (x, y) == (monster.x, monster.y):
                return f"{ANSI.YELLOW}{monster.char}{ANSI.RESET}"

        if (x, y) == (self.start_x, self.start_y):
            return f"{ANSI.CYAN}{START}{ANSI.RESET}"

        if (x, y) in self.items_on_map:
            item_data = self.items_on_map[(x, y)]
            item_id = item_data['id']
            
            import re
            if re.match(r'(\d+)F_Key', item_id):
                return f"{ANSI.RED}K{ANSI.RESET}"
            else:
                return ITEM_TILE
        
        if (x, y) == (self.exit_x, self.exit_y):
            return f"{ANSI.MAGENTA}{self.exit_type}{ANSI.RESET}"
        
        if (x, y) in self.visited:
            return EXPLORED
        
        if self.map_data[y][x] == START:
            return START

        return self.map_data[y][x]


    def to_dict(self):
        """현재 맵 상태를 딕셔너리로 변환하여 반환합니다."""
        serializable_items_on_map = {f"{k[0]},{k[1]}": v for k, v in self.items_on_map.items()}
        serializable_monsters = [
            {'x': m.x, 'y': m.y, 'hp': m.hp, 'char': m.char, 'dead': m.dead} 
            for m in self.monsters
        ]

        return {
            "width": self.width,
            "height": self.height,
            "map_data": self.map_data,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "player_x": self.player_x,
            "player_y": self.player_y,
            "exit_x": self.exit_x,
            "exit_y": self.exit_y,
            "exit_type": self.exit_type,
            "required_key_id": self.required_key_id,
            "required_key_count": self.required_key_count,
            "visited": list(self.visited),
            "is_generated": self.is_generated,
            "items_on_map": serializable_items_on_map,
            "monsters": serializable_monsters
        }

    @classmethod
    # from_dict 클래스 메서드는 ui_instance를 인자로 받지 않습니다.
    # 이는 DungeonMap 객체가 직렬화된 데이터에서 생성될 때 UI 인스턴스에 대한 직접적인 접근이 필요 없기 때문입니다.
    # UI 인스턴스는 DungeonMap이 게임 루프에 통합될 때 game.py에서 전달됩니다.
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 DungeonMap 객체를 생성하여 반환합니다."""
        # 더미 레벨 (0, 0)으로 초기화 (width, height는 아래에서 덮어씀). ui_instance는 이 시점에 필요 없음.
        d_map = cls((0, 0), ui_instance=None)
        
        d_map.width = data.get('width', d_map.MIN_MAP_WIDTH)
        d_map.height = data.get('height', d_map.MIN_MAP_HEIGHT)
        d_map.map_data = data.get('map_data', [])
        d_map.start_x = data.get('start_x', 0)
        d_map.start_y = data.get('start_y', 0)
        d_map.player_x = data.get('player_x', 0)
        d_map.player_y = data.get('player_y', 0)
        d_map.exit_x = data.get('exit_x', 0)
        d_map.exit_y = data.get('exit_y', 0)
        d_map.exit_type = data.get('exit_type', EXIT_NORMAL)
        d_map.required_key_id = data.get('required_key_id')
        d_map.required_key_count = data.get('required_key_count', 0)
        d_map.visited = set(tuple(v) for v in data.get('visited', []))
        d_map.is_generated = data.get('is_generated', True)
        
        deserializable_items_on_map = {}
        for key_str, item_data in data.get('items_on_map', {}).items():
            x_str, y_str = key_str.split(',')
            deserializable_items_on_map[(int(x_str), int(y_str))] = item_data
        d_map.items_on_map = deserializable_items_on_map
        
        d_map.monsters = []
        for monster_data in data.get('monsters', []):
            monster = Monster(monster_data['x'], monster_data['y'], ui_instance=None)
            monster.hp = monster_data.get('hp', 30)
            monster.char = monster_data.get('char', 'M')
            monster.dead = monster_data.get('dead', False)
            d_map.monsters.append(monster)
        
        return d_map

