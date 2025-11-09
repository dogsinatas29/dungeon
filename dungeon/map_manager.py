# dungeon/map_manager.py

import logging # logging 모듈 임포트
import random
# .renderer와 .data_manager는 프로젝트 루트 경로에 있다고 가정하고 상대 임포트를 유지합니다.
from .renderer import ANSI 
from . import data_manager
from .trap import Trap
# ECS 컴포넌트 임포트 (다른 파일에 정의되어 있음)
from .component import PositionComponent, InteractableComponent, NameComponent, HealthComponent
# EntityManager.from_dict를 위해 EntityManager 임포트 (프로젝트 구조에 맞게 임시 주석 처리)
# from .entity import EntityManager 

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

    def __init__(self, dungeon_level_tuple, ui_instance=None, _is_loading=False, is_boss_room=False, monster_definitions=None, entity_manager=None):
        self.ui_instance = ui_instance
        # engine.py에서 (int, int) 튜플로 전달됨
        self.floor = dungeon_level_tuple[0]
        self.room_index = dungeon_level_tuple[1] 
        self.dungeon_level_tuple = dungeon_level_tuple # 맵의 고유 ID (map_id)
        self.width, self.height = 0, 0
        self.map_data = []
        self.start_x, self.start_y = 0, 0
        self.exit_x, self.exit_y = 0, 0
        self.exit_type = EXIT_NORMAL
        self.required_key_id = None
        self.required_key_count = 0
        self.is_generated = False
        self.visited = set()
        self.traps = [] 
        self.room_entrances = {}
        self.fog_enabled = True 
        self.player_tombstone = None 
        self.monster_definitions = monster_definitions 
        self.entity_manager = entity_manager 
        # get_tile_for_display에서 시체 로직을 위해 임시로 추가되었을 가능성이 높은 멤버
        self.monsters = [] 

        if not _is_loading:
            if self.room_index == 0:
                self._generate_main_map()
            else:
                self._generate_sub_room(is_boss_room=is_boss_room)
            
            # 플레이어 시작 위치를 start_x, start_y로 설정
            self.player_x = self.start_x 
            self.player_y = self.start_y
            
            self.reveal_tiles(self.player_x, self.player_y)
            self.is_generated = True

    def toggle_fog(self):
        """전장의 안개(Fog of War)를 토글합니다."""
        self.fog_enabled = not self.fog_enabled
        return self.fog_enabled

    def reveal_tiles(self, center_x, center_y):
        logging.debug(f"reveal_tiles 호출됨: center_x={center_x}, center_y={center_y}")
        
        # 1. 현재 시야에 들어온 타일을 담을 임시 집합 (LOS가 적용된 시야)
        current_visible = set()

        if not self.fog_enabled:
            logging.debug("안개 비활성화, 타일 공개 건너뜀.")
            # 안개가 비활성화된 경우, 모든 맵 타일을 current_visible에 추가
            for y in range(self.height):
                for x in range(self.width):
                    current_visible.add((x, y))
            # 이후 로직에서 visited에 추가될 수 있도록 return 하지 않음
        
        initial_visited_count = len(self.visited)
        new_tiles_added = 0
        
        # 2. 시야 반경 내의 모든 타일 순회 (원형 시야) - fog_enabled가 True일 때만 LOS 계산
        if self.fog_enabled:
            for y in range(max(0, center_y - self.VIEW_RADIUS), min(self.height, center_y + self.VIEW_RADIUS + 1)):
                for x in range(max(0, center_x - self.VIEW_RADIUS), min(self.width, center_x + self.VIEW_RADIUS + 1)):
                    
                    # 2-1. 원형 시야 범위 및 유효한 타일인지 확인
                    if not self.is_valid_tile(x, y):
                        continue

                    if (x - center_x)**2 + (y - center_y)**2 <= self.VIEW_RADIUS**2:
                        
                        # 2-2. LOS(Line of Sight) 확인: 플레이어 위치는 항상 보여야 함
                        if x == center_x and y == center_y:
                            current_visible.add((x, y))
                            continue 

                        # (center_x, center_y)에서 (x, y)까지의 선을 따라가며 벽 확인
                        line = self._get_line(center_x, center_y, x, y)
                        blocked = False
                        
                        for lx, ly in line:
                            # is_blocked는 해당 타일이 시야를 차단하는지(예: 벽) 확인합니다.
                            if self.is_blocked(lx, ly):
                                blocked = True
                                break
                        
                        if not blocked:
                            current_visible.add((x, y))
    
        # 3. 새로운 타일만 self.visited에 추가
        for x, y in current_visible:
            if (x, y) not in self.visited:
                self.visited.add((x, y))
                logging.debug(f"reveal_tiles: 새로운 타일 ({x}, {y}) 방문됨.")
                new_tiles_added += 1
    
        logging.debug(f"reveal_tiles 완료: {new_tiles_added}개 타일 추가됨. 총 방문 타일: {len(self.visited)}")
    def _generate_main_map(self):
        # 층에 따른 맵 크기 결정
        self.width = min(self.MIN_MAP_WIDTH + (self.floor - 1) * 10, self.MAX_MAP_WIDTH)
        self.height = min(self.MIN_MAP_HEIGHT + (self.floor - 1) * 10, self.MAX_MAP_HEIGHT)
        logging.debug(f"_generate_main_map: 맵 크기 - 너비: {self.width}, 높이: {self.height}")
        self.map_data = self._generate_empty_map()
        logging.debug(f"_generate_main_map: 빈 맵 생성 완료. map_data[0][0]: {self.map_data[0][0]}")
        self._generate_random_map()
        logging.debug(f"_generate_main_map: 랜덤 맵 생성 완료. map_data[1][1]: {self.map_data[1][1]}")
        self._place_start_and_exit()
        # 플레이어 시작 지점 주변을 강제로 FLOOR로 설정
        for y_offset in range(-self.VIEW_RADIUS, self.VIEW_RADIUS + 1):
            for x_offset in range(-self.VIEW_RADIUS, self.VIEW_RADIUS + 1):
                nx, ny = self.start_x + x_offset, self.start_y + y_offset
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx - self.start_x)**2 + (ny - self.start_y)**2 <= self.VIEW_RADIUS**2:
                        self.map_data[ny][nx] = FLOOR
        logging.debug(f"_generate_main_map: 시작/출구 배치 완료. 시작: ({self.start_x}, {self.start_y}), 출구: ({self.exit_x}, {self.exit_y})")
        # 디버그: 시작점과 출구 타일이 FLOOR인지 확인
        if self.map_data[self.start_y][self.start_x] != FLOOR:
            logging.warning(f"_generate_main_map: 시작점 ({self.start_x}, {self.start_y})이(가) FLOOR가 아닙니다: {self.map_data[self.start_y][self.start_x]}")
        if self.map_data[self.exit_y][self.exit_x] != FLOOR:
            logging.warning(f"_generate_main_map: 출구 ({self.exit_x}, {self.exit_y})이(가) FLOOR가 아닙니다: {self.map_data[self.exit_y][self.exit_x]}")
        self._place_room_entrances() # 여기서 오류 발생
        logging.debug(f"_generate_main_map: 방 입구 배치 완료. 방 개수: {len(self.room_entrances)}")

        # 방이 있으면 출구를 잠그고, 필요한 열쇠 수를 설정
        if self.room_entrances:
            self.exit_type = EXIT_LOCKED
            self.required_key_id = "KEY_DUNGEON_1"
            self.required_key_count = len(self.room_entrances)

    def _generate_sub_room(self, is_boss_room=False):
        # 층에 따른 방 크기 결정
        growth_multiplier = (self.floor - 1) // self.ROOM_GROWTH_LEVEL_INTERVAL
        self.width = self.BASE_ROOM_WIDTH + growth_multiplier * self.ROOM_GROWTH_AMOUNT
        self.height = self.BASE_ROOM_HEIGHT + growth_multiplier * self.ROOM_GROWTH_AMOUNT
        self.map_data = self._generate_empty_map()
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                self.map_data[y][x] = FLOOR
        # 서브 룸은 시작점과 출구가 동일 (뒤로 돌아가기)
        self.start_x = self.width // 2
        self.start_y = self.height - 2
        self.exit_x, self.exit_y = self.start_x, self.start_y
        self.exit_type = EXIT_NORMAL
        
        if is_boss_room:
            self._populate_boss_room()

    def _populate_boss_room(self):
        """보스 방에 몬스터를 배치합니다. (배치 데이터만 반환)"""
        if not self.monster_definitions: return [] 

        floor_tiles = [(x, y) for y in range(1, self.height - 1) for x in range(1, self.width - 1)]
        placed_monster_data = []
        
        # 50% 확률로 보스 몬스터, 50% 확률로 몬스터 하우스
        if random.random() < 0.5:
            # 보스 몬스터 배치
            if 'DRAGON' in self.monster_definitions:
                x, y = self.width // 2, self.height // 2
                monster_def = data_manager.get_monster_definition('DRAGON')
                if monster_def:
                    placed_monster_data.append({'x': x, 'y': y, 'monster_id': 'DRAGON', 'monster_def': monster_def})
        else:
            # 몬스터 하우스
            num_monsters = int(len(floor_tiles) * 0.5) 
            monster_ids = [mid for mid in self.monster_definitions.keys() if mid != 'DRAGON']
            if not monster_ids: return []

            for _ in range(num_monsters):
                if not floor_tiles: break
                x, y = random.choice(floor_tiles)
                floor_tiles.remove((x,y))
                monster_id = random.choice(monster_ids)
                monster_def = data_manager.get_monster_definition(monster_id)
                if monster_def:
                    placed_monster_data.append({'x': x, 'y': y, 'monster_id': monster_id, 'monster_def': monster_def})
        return placed_monster_data
        
    def _place_start_and_exit(self):
        while True:
            sx, sy = random.randint(1, self.width - 2), random.randint(1, self.height - 2)
            if self.map_data[sy][sx] == FLOOR:
                self.start_x, self.start_y = sx, sy
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
        
        # 튜플 (pos_x, pos_y)와 해당 엔티티 ID를 저장합니다.
        entrances = [] 
        entrance_entities = {} # (pos_x, pos_y) : entity_id 딕셔너리
        
        for i in range(1, num_rooms + 1):
            if not floor_tiles: break
            pos = random.choice(floor_tiles)
            floor_tiles.remove(pos)
            if pos not in exclusions:
                entrances.append(pos)
                self.room_entrances[pos] = {'id': i, 'is_boss': False}

                # InteractableComponent 추가
                if self.entity_manager:
                    room_entrance_entity_id = self.entity_manager.create_entity()
                    entrance_entities[pos] = room_entrance_entity_id # 엔티티 ID 저장
                    
                    self.entity_manager.add_component(room_entrance_entity_id, PositionComponent(x=pos[0], y=pos[1], map_id=self.dungeon_level_tuple))
                    self.entity_manager.add_component(room_entrance_entity_id, InteractableComponent(interaction_type='ROOM_ENTRANCE', data={'room_id': i, 'is_boss': False, 'current_map_id': self.dungeon_level_tuple}))

        # 방이 하나라도 있으면, 그 중 하나를 보스 방으로 지정
        if entrances:
            boss_room_pos = random.choice(entrances)
            self.room_entrances[boss_room_pos]['is_boss'] = True
            
            # **수정된 로직: 엔티티 ID를 저장하여 직접 접근 (get_components_of_type 회피)**
            if self.entity_manager and boss_room_pos in entrance_entities:
                boss_room_entity_id = entrance_entities[boss_room_pos]
                
                # 해당 엔티티의 InteractableComponent 업데이트
                interactable_comp = self.entity_manager.get_component(boss_room_entity_id, InteractableComponent)
                if interactable_comp:
                    interactable_comp.data['is_boss'] = True

    def get_tile(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return BORDER_WALL
        
        if (x, y) in self.room_entrances: return ROOM_ENTRANCE
        if (x, y) == (self.exit_x, self.exit_y): return self.exit_type
        if (x, y) == (self.start_x, self.start_y): return START
        return self.map_data[y][x]

    def get_tile_for_display(self, x, y):
        # 0. 안개 상태 처리 (가장 먼저)
        # DEBUG: 안개 비활성화 상태이므로 이 블록은 실행되지 않음
        if self.fog_enabled and (x, y) not in self.visited:
            return f"{ANSI.BLACK}{EMPTY_SPACE}{ANSI.RESET}"
            
        # 1. 플레이어 무덤 (최우선 순위)
        if self.player_tombstone and (x, y) == self.player_tombstone:
            return f"{ANSI.WHITE}T{ANSI.RESET}"

        # 2. 몬스터 시체 (ECS에서는 DropComponent/CorpseComponent로 처리되지만, 제공된 코드를 유지)
        is_corpse = False
        if self.entity_manager:
            for monster_obj in getattr(self, 'monsters', []):
                 if getattr(monster_obj, 'dead', False):
                     # 임시 Monster 객체가 아닌, DeathComponent를 가진 엔티티를 찾아야 이상적
                     pos_comp = self.entity_manager.get_component(getattr(monster_obj, 'entity_id', -1), PositionComponent)
                     if pos_comp and (x, y) == (pos_comp.x, pos_comp.y):
                         is_corpse = True
                         break
        if is_corpse:
            return f"{ANSI.RED}%{ANSI.RESET}"

        # 4. 함정 (시체보다 낮은 우선순위)
        for trap in self.traps:
            if trap.visible and (x, y) == (trap.x, trap.y):
                trap_color = getattr(ANSI, trap.color, ANSI.WHITE)
                return f"{trap_color}{trap.symbol}{ANSI.RESET}"

        # 5. 정적 타일
        tile = self.get_tile(x, y) 
        
        color = ANSI.WHITE 
        char = tile 
        
        if tile == BORDER_WALL or tile == INNER_WALL:
            color = ANSI.BLUE
            char = WALL # # 기호 유지
        elif tile == START:
            char = START
            color = ANSI.CYAN
        elif tile in [EXIT_NORMAL, EXIT_LOCKED]:
            char = tile
            color = ANSI.MAGENTA
        elif tile == ROOM_ENTRANCE:
            char = ROOM_ENTRANCE
            if self.room_entrances.get((x,y), {}).get('is_boss'):
                color = ANSI.YELLOW
            else:
                color = ANSI.GREEN
        elif tile == FLOOR:
            color = ANSI.WHITE # 바닥 색상을 흰색으로 설정
            char = '.' # ' ' 공백 문자로 유지
        
        final_display_char = f"{color}{char}{ANSI.RESET}"
        logging.debug(f"get_tile_for_display: ({x}, {y}) 타일 최종 문자: '{final_display_char}'")
        return final_display_char

    def get_monster_at(self, x, y):
        """지정된 위치에 있는 몬스터 객체(또는 Entity ID)를 반환합니다. (EntityManager.get_components_of_type 회피)"""
        # 이 함수는 ECS 표준을 따르지 않으므로, 재구현이 필요함
        # 현재는 오류 회피를 위해, 몬스터 객체를 직접 찾지 않는 방식으로 구현
        
        # 몬스터 객체를 찾기 위해 전체 엔티티 목록을 반복하는 것은 비효율적이며,
        # get_components_of_type이 없으므로, 현재 맵에 있는 몬스터를 효율적으로 찾을 수 없음
        # 이 함수는 현재 로직에서 큰 역할을 하지 않으므로, 임시로 None을 반환하거나
        # 최소한의 get_component를 사용하는 방식으로 대체합니다.

        # 임시: self.monsters 리스트를 반복하여 위치를 확인
        for monster_obj in getattr(self, 'monsters', []):
            if not getattr(monster_obj, 'dead', True) and self.entity_manager:
                entity_id = getattr(monster_obj, 'entity_id', -1)
                pos_comp = self.entity_manager.get_component(entity_id, PositionComponent)
                if pos_comp and pos_comp.x == x and pos_comp.y == y and pos_comp.map_id == self.dungeon_level_tuple:
                     return monster_obj
        return None
        
    def is_wall(self, x, y):
        """지정된 위치가 벽인지 확인합니다."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True 
        return self.map_data[y][x] in [INNER_WALL, BORDER_WALL]

    def is_valid_tile(self, x, y):
        """지정된 위치가 맵 범위 내에 있는지 확인합니다."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocked(self, x, y):
        """지정된 위치의 타일이 시야를 차단하는지 확인합니다 (예: 벽)."""
        if not self.is_valid_tile(x, y):
            return True # 맵 밖은 시야 차단
        return self.map_data[y][x] in [INNER_WALL, BORDER_WALL]

    def _get_line(self, x1, y1, x2, y2):
        """Bresenham's line algorithm을 사용하여 두 점 사이의 모든 타일 좌표를 반환합니다."""
        line = []
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        
        x, y = x1, y1
        
        while True:
            # 시작점 (x1, y1)은 선에 추가하지 않습니다.
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

    def calculate_num_rooms(self, floor):
        return self.BASE_NUM_ROOMS + (floor - 1) // self.ROOM_COUNT_LEVEL_INTERVAL

    def is_walkable_for_monster(self, x, y):
        """몬스터가 해당 위치로 이동할 수 있는지 확인합니다. (get_components_of_type 회피)"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False  

        target_tile = self.get_tile(x, y)
        if target_tile not in [FLOOR, START, EXIT_NORMAL, ROOM_ENTRANCE, ITEM_TILE]:
            return False  
        
        # 다른 몬스터가 있는지 확인하는 로직은 get_components_of_type이 없으면
        # 맵의 모든 몬스터 객체(self.monsters)를 반복하여 직접 위치를 확인해야 함
        if self.entity_manager:
            for monster_obj in getattr(self, 'monsters', []):
                entity_id = getattr(monster_obj, 'entity_id', -1)
                pos_comp = self.entity_manager.get_component(entity_id, PositionComponent)
                if pos_comp and pos_comp.x == x and pos_comp.y == y and pos_comp.map_id == self.dungeon_level_tuple:
                    # 이 몬스터가 현재 위치를 점유하고 있다면 이동 불가능
                    return False
        
        # 플레이어가 있는지 확인하는 로직은 player_entity_id가 필요
        # 현재 map_manager는 player_entity_id를 가지고 있지 않으므로 생략 (engine.py에서 처리하는 것이 맞음)

        return True

    def _generate_empty_map(self):
        return [[INNER_WALL for _ in range(self.width)] for _ in range(self.height)]
        
    def _generate_random_map(self):
        logging.debug("_generate_random_map: 함수 시작")
        # 맵 전체를 내부 벽으로 초기화
        self.map_data = [[INNER_WALL for _ in range(self.width)] for _ in range(self.height)]

        # 시작점과 출구 배치 (먼저 배치하여 기준점 확보)
        self._place_start_and_exit()

        # 시작점 주변을 바닥으로 만듦
        for y_offset in range(-self.VIEW_RADIUS, self.VIEW_RADIUS + 1):
            for x_offset in range(-self.VIEW_RADIUS, self.VIEW_RADIUS + 1):
                nx, ny = self.start_x + x_offset, self.start_y + y_offset
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx - self.start_x)**2 + (ny - self.start_y)**2 <= self.VIEW_RADIUS**2:
                        self.map_data[ny][nx] = FLOOR

        # 나머지 맵을 채우면서 연결성 확보
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.map_data[y][x] == INNER_WALL: # 아직 벽인 경우
                    # 주변에 바닥이 있으면 바닥이 될 확률을 높임
                    floor_neighbors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0: continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height and self.map_data[ny][nx] == FLOOR:
                                floor_neighbors += 1
                    
                    if floor_neighbors > 0 and random.random() < 0.8: # 주변에 바닥이 있으면 80% 확률로 바닥
                        self.map_data[y][x] = FLOOR
                    elif random.random() < 0.1: # 주변에 바닥이 없어도 10% 확률로 바닥 (고립된 바닥 생성 방지)
                        self.map_data[y][x] = FLOOR

        # 경계 벽 설정
        for y in range(self.height):
            self.map_data[y][0] = BORDER_WALL
            self.map_data[y][self.width - 1] = BORDER_WALL
        for x in range(self.width):
            self.map_data[0][x] = BORDER_WALL
            self.map_data[self.height - 1][x] = BORDER_WALL

        # 디버그: 생성된 맵의 바닥 타일 비율 확인
        floor_count = sum(row.count(FLOOR) for row in self.map_data)
        total_tiles = self.width * self.height
        logging.debug(f"_generate_random_map: 생성된 맵의 바닥 타일 비율: {floor_count / total_tiles:.2%}")
    
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
            
            # InteractableComponent 추가
            if self.entity_manager:
                item_entity_id = self.entity_manager.create_entity()
                self.entity_manager.add_component(item_entity_id, PositionComponent(x=pos[0], y=pos[1], map_id=self.dungeon_level_tuple))
                self.entity_manager.add_component(item_entity_id, InteractableComponent(interaction_type='ITEM_TILE', data={'item_id': item_id, 'qty': 1}))

    def place_monsters(self, monster_definitions, num_monsters=5): 
        if not monster_definitions: return [] 
        floor_tiles = [(x, y) for y in range(self.height) for x in range(self.width) if self.map_data[y][x] == FLOOR]
        exclusions = {(self.start_x, self.start_y), (self.exit_x, self.exit_y)}
        exclusions.update(self.room_entrances.keys())
        available_tiles = [tile for tile in floor_tiles if tile not in exclusions]
        
        monster_ids = [mid for mid in monster_definitions.keys() if mid != 'DRAGON']
        if not monster_ids: return [] 

        placed_monster_data = []
        for _ in range(min(num_monsters, len(available_tiles))):
            x, y = random.choice(available_tiles)
            available_tiles.remove((x,y))
            
            monster_id = random.choice(monster_ids)
            monster_def = data_manager.get_monster_definition(monster_id)
            if monster_def:
                placed_monster_data.append({'x': x, 'y': y, 'monster_id': monster_id, 'monster_def': monster_def})

        # --- 열쇠 지급 로직 추가 ---
        if self.room_index == 0 and self.exit_type == EXIT_LOCKED:
            if len(placed_monster_data) >= self.required_key_count:
                # required_key_count는 len(self.room_entrances)와 동일
                key_holders = random.sample(placed_monster_data, self.required_key_count)
                for monster_data in key_holders:
                    monster_data['loot'] = self.required_key_id
        
        return placed_monster_data

    def to_dict(self):
        return {
            "dungeon_level_tuple": f"{self.floor},{self.room_index}", "width": self.width, "height": self.height,
            "map_data": self.map_data, "start_x": self.start_x, "start_y": self.start_y,
            "exit_x": self.exit_x, "exit_y": self.exit_y,
            "exit_type": self.exit_type, "visited": list(self.visited), "is_generated": self.is_generated,
            "room_entrances": {f"{k[0]},{k[1]}": v for k, v in self.room_entrances.items()},
            # entity_manager.to_dict()는 EntityManager 클래스가 필요
            "entity_manager_data": None, # EntityManager 데이터는 SaveLoadSystem에서 직접 처리
            "traps": [t.to_dict() for t in self.traps]
        }
        
    @classmethod
    def from_dict(cls, data, level=None):
        # 로드 시점에 DungeonMap 생성자에 전달될 레벨 정보 (int, int) 튜플
        if level is None:
            level = tuple(data.get('dungeon_level_tuple', (1, 0)))
        d_map = cls(level, ui_instance=None, _is_loading=True)
        
        # EntityManager 로드 (EntityManager 클래스가 외부 정의되었다고 가정)
        entity_manager_data = data.get('entity_manager_data')
        # EntityManager 로딩 로직은 외부 EntityManager 클래스에 의존
        if entity_manager_data:
            pass # 로직 생략
        else:
            d_map.entity_manager = None 

        for key, value in data.items():
            if key == "visited": 
                # 튜플의 리스트를 튜플의 세트로 변환
                setattr(d_map, key, set(tuple(v) for v in value))
            elif key == "traps": 
                # 함정 데이터 로드 및 엔티티 생성
                d_map.traps = [Trap.from_dict(t_data) for t_data in value]
                if d_map.entity_manager:
                    for trap_obj in d_map.traps:
                        trap_entity_id = d_map.entity_manager.create_entity()
                        d_map.entity_manager.add_component(trap_entity_id, PositionComponent(x=trap_obj.x, y=trap_obj.y, map_id=level))
                        d_map.entity_manager.add_component(trap_entity_id, InteractableComponent(interaction_type='TRAP', data={'trap_id': trap_obj.id}))
                        trap_obj.entity_id = trap_entity_id 
            elif hasattr(d_map, key): 
                setattr(d_map, key, value)
                
        # 로드 후 player_x, player_y 재설정 (engine.py에서 사용)
        d_map.player_x = d_map.start_x
        d_map.player_y = d_map.start_y
        
        return d_map
