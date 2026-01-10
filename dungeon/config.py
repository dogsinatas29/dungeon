# dungeon/config.py - 게임 전역 설정 상수

# 던전 크기 설정
MAP_WIDTH = 80
MAP_HEIGHT = 20

# 언어 설정 ("ko", "en")
LANGUAGE = "ko"

# 방 생성을 위한 설정
MAX_ROOMS = 10
ROOM_MIN_SIZE = 6
ROOM_MAX_SIZE = 12

# -------------------------------------------------------------------------
# Balance Configuration (Fixed by User Request 2026-01-10)
# -------------------------------------------------------------------------

# 1. Enhancement System
# Success Rates per Level (+0 -> +1 is index 0)
ENHANCE_SUCCESS_RATES = {
    0: 0.90, # +0 -> +1
    1: 0.80, # +1 -> +2
    2: 0.70, # +2 -> +3
    3: 0.60, # +3 -> +4
    4: 0.50, # +4 -> +5
    5: 0.40, # +5 -> +6
    6: 0.30, # +6 -> +7
    7: 0.20, # +7 -> +8
    8: 0.15, # +8 -> +9
    9: 0.10  # +9 -> +10
    # +10 is Max, so no +10 -> +11 rate needed
}

# Failure Penalties
ENHANCE_SAFE_LIMIT = 3       # Levels <= 3: Failure = Durability Loss
ENHANCE_BREAK_LIMIT = 6      # Levels <= 6: Failure = Break (Durability 0)
# Levels > 6: Failure = Destruction

# 2. Loot System
# Drop Chance by Floor Range
LOOT_DROP_CHANCE = [
    (25, 0.15, 0.25),  # Floor <= 25: 15-25%
    (50, 0.30, 0.50),  # Floor <= 50: 30-50%
    (999, 0.15, 0.25)  # Floor > 50:  15-25%
]

# Gold Drop Formula
# Base Gold = GOLD_DROP_BASE + (Floor * GOLD_DROP_SCALING)
GOLD_DROP_BASE = 10
GOLD_DROP_SCALING = 5
GOLD_VARIANCE = 2.0 # Max typical gold is Base * Variance

BOSS_DROP_CHANCE = 1.0
BOSS_DROP_COUNT_MIN = 5
BOSS_DROP_COUNT_MAX = 10
BOSS_GOLD_MIN = 1000
BOSS_GOLD_MAX = 3000

NORMAL_DROP_COUNT_MIN = 1
NORMAL_DROP_COUNT_MAX = 3
NORMAL_DROP_LUCKY_CHANCE = 0.2
NORMAL_DROP_LUCKY_MIN = 3
NORMAL_DROP_LUCKY_MAX = 5