import csv
import os

# -----------------------------------------------------------------------
# ItemDefinition 클래스 정의 (기존 내용 유지)
# -----------------------------------------------------------------------
class ItemDefinition:
    # 'item_type' 대신 CSV 헤더와 동일하게 'type'으로 인자명을 통일합니다.
    def __init__(self, name, type, description, symbol, color, required_level, attack, defense, hp_effect, mp_effect):
        self.name = name
        self.type = type # 'self.type'에 'type' 인자를 할당합니다.
        self.description = description
        self.symbol = symbol
        self.color = color
        self.required_level = int(required_level)
        self.attack = int(attack)
        self.defense = int(defense)
        self.hp_effect = int(hp_effect)
        self.mp_effect = int(mp_effect)

# 참고: Python 내장 함수 'type'과 이름이 겹치지만, **row 언패킹을 위해 이 이름을 사용해야 합니다.**

# -----------------------------------------------------------------------
# [추가] MonsterDefinition 클래스 추가 (오류 해결의 핵심: 'hp' 속성 포함)
# -----------------------------------------------------------------------
class MonsterDefinition:
    # CSV 헤더(monster_data.txt의 헤더)에 맞춰 정의
    def __init__(self, ID, Name, Symbol, Color, HP, ATT, DEF, LV, EXP_GIVEN, CRIT_CHANCE, CRIT_MULT, MOVE_TYPE, ACTION_DELAY, **kwargs):
        self.ID = ID
        self.name = Name 
        self.symbol = Symbol
        self.color = Color
        self.hp = int(HP)  # <-- system.py에서 필요로 하는 'hp' 속성
        self.attack = int(ATT)
        self.defense = int(DEF)
        self.level = int(LV)
        self.xp_value = int(EXP_GIVEN)
        self.crit_chance = float(CRIT_CHANCE)
        self.crit_mult = float(CRIT_MULT)
        self.move_type = MOVE_TYPE
        self.action_delay = float(ACTION_DELAY)
        # kwargs는 향후 필드 추가에 대비한 안전장치

# -----------------------------------------------------------------------
# [추가] load_data_from_csv 헬퍼 함수
# -----------------------------------------------------------------------
def load_data_from_csv(file_name, definition_class, data_path="data"):
    DATA_DEFINITIONS = {}
    file_path = os.path.join(data_path, file_name)
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # DictReader의 row를 클래스 __init__ 인자에 언패킹하여 객체 생성
                def_obj = definition_class(**row)

                # 딕셔너리 키 설정 (아이템은 name, 몬스터는 ID 사용)
                key = row.get('name') if definition_class is ItemDefinition else row.get('ID')
                
                if key:
                    DATA_DEFINITIONS[key] = def_obj
        
        # print(f"Loaded {len(DATA_DEFINITIONS)} {definition_class.__name__} definitions from {file_path}")
        return DATA_DEFINITIONS
    except FileNotFoundError:
        print(f"ERROR: Data file not found at {file_path}. Using empty data.")
        return {}
    except Exception as e:
        print(f"ERROR loading data from {file_name}: {e}. Skipping row: {row}")
        return {}


# -----------------------------------------------------------------------
# [수정] load_game_data 함수 수정: 아이템 및 몬스터 데이터 모두 로드
# -----------------------------------------------------------------------
    return game_definitions

# --- Start.py Compatibility Layer ---

def load_item_definitions():
    """Start.py 호환성: 아이템 정의만 로드하여 반환"""
    return load_data_from_csv('items.csv', ItemDefinition)

def get_item_definition(item_id):
    """Start.py 호환성: 특정 아이템 정의 반환"""
    defs = load_item_definitions()
    return defs.get(item_id)

def load_skill_definitions():
    """Start.py 호환성: 스킬 정의 로드 (placeholder)"""
    return {}

def save_game_data(data, filename="savegame.json"):
    """Start.py 호환성: 게임 데이터 저장"""
    import json
    save_dir = "game_data"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    file_path = os.path.join(save_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Game saved to {file_path}")

def load_game_data(filename="savegame.json"):
    """Start.py 호환성: 저장된 게임 데이터 로드 (JSON)"""
    import json
    file_path = os.path.join("game_data", filename)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load save file: {e}")
        return None

def delete_save_data(filename="savegame.json"):
    """Start.py 호환성: 저장 데이터 삭제"""
    file_path = os.path.join("game_data", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print("Save file deleted.")

