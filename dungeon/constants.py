# constants.py
# 게임 전반에 사용되는 상수 정의

# --- Tile Definitions ---
BORDER_WALL = '#'
INNER_WALL = '#'
FLOOR = '.'
FLOOR_CHAR = '.' # FLOOR_CHAR는 FLOOR와 동일
PLAYER = '@'
START = '<'
DOOR_CLOSED_CHAR = '+'
DOOR_OPEN_CHAR = '/'
UNKNOWN_CHAR = ' ' # 안개 또는 미탐색 영역 표시
EXIT_NORMAL = '>'
EXIT_LOCKED = 'X'
ITEM_TILE = '*'
ROOM_ENTRANCE = '+'
MONSTER = 'M'

EMPTY_SPACE = ' '
WALL = INNER_WALL

# --- UI Constants ---
MAP_VIEWPORT_WIDTH = 60
MAP_VIEWPORT_HEIGHT = 20

# --- Elemental System (속성 시스템) ---
# 속성 정의
ELEMENT_NONE = "NONE"
ELEMENT_WATER = "WATER"
ELEMENT_FIRE = "FIRE"
ELEMENT_WOOD = "WOOD"
ELEMENT_EARTH = "EARTH"
ELEMENT_POISON = "POISON"

# 속성 색상 매핑 (Legacy: UI 오버홀 이후에는 RARITY_COLORS 사용 권장)
ELEMENT_COLORS = {
    ELEMENT_NONE: "white",
    ELEMENT_WATER: "blue",
    ELEMENT_FIRE: "red",
    ELEMENT_WOOD: "green",
    ELEMENT_EARTH: "yellow",
    ELEMENT_POISON: "magenta"
}

# 속성 아이콘 매핑 (NEW)
ELEMENT_ICONS = {
    ELEMENT_NONE: "",
    ELEMENT_WATER: "❄️", # User request: Ice='❄️'. Mapping WATER to Ice icon for now.
    ELEMENT_FIRE: "🔥",
    ELEMENT_WOOD: "🌲",
    ELEMENT_EARTH: "⛰️",
    ELEMENT_POISON: "☠️"
}

# 상성 관계 (A > B: A가 B를 공격할 때 우위)
# 물(WATER) > 불(FIRE) > 나무(WOOD) > 흙(EARTH) > 물(WATER)
ELEMENT_ADVANTAGE = {
    ELEMENT_WATER: ELEMENT_FIRE,
    ELEMENT_FIRE: ELEMENT_WOOD,
    ELEMENT_WOOD: ELEMENT_EARTH,
    ELEMENT_EARTH: ELEMENT_WATER
}

# --- Rarity Colors (NEW) ---
RARITY_NORMAL = "white"
RARITY_MAGIC = "cyan"
RARITY_UNIQUE = "yellow"
RARITY_CURSED = "red"

# --- Boss Mechanics ---
BOSS_SEQUENCE = ["GOBLIN_KING", "LICH", "DRAGON", "DIABLO"]

