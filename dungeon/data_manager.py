import csv
import os

# -----------------------------------------------------------------------
# ItemDefinition 클래스 정의 (기존 내용 유지)
# -----------------------------------------------------------------------
class ItemDefinition:
    # 'item_type' 대신 CSV 헤더와 동일하게 'type'으로 인자명을 통일합니다.
    def __init__(self, name, type, description, symbol, color, required_level, attack, defense, hp_effect, mp_effect, hand_type=1, attack_range=1, skill_id=None, flags="", **kwargs):
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
        self.hand_type = int(hand_type) # 1: 한손, 2: 양손
        self.attack_range = int(attack_range)
        self.skill_id = skill_id
        # 플래그 처리 (콤마로 구분된 문자열을 Set으로 변환)
        self.flags = {f.strip().upper() for f in flags.split(',') if f.strip()}

    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "symbol": self.symbol,
            "color": self.color,
            "required_level": self.required_level,
            "attack": self.attack,
            "defense": self.defense,
            "hp_effect": self.hp_effect,
            "mp_effect": self.mp_effect,
            "hand_type": self.hand_type,
            "attack_range": self.attack_range,
            "skill_id": getattr(self, "skill_id", None)
        }

# 참고: Python 내장 함수 'type'과 이름이 겹치지만, **row 언패킹을 위해 이 이름을 사용해야 합니다.**

# -----------------------------------------------------------------------
# [추가] MonsterDefinition 클래스 추가 (오류 해결의 핵심: 'hp' 속성 포함)
# -----------------------------------------------------------------------
class MonsterDefinition:
    # CSV 헤더(monster_data.txt의 헤더)에 맞춰 정의
    def __init__(self, ID, Name, Symbol, Color, HP, ATT, DEF, LV, EXP_GIVEN, CRIT_CHANCE, CRIT_MULT, MOVE_TYPE, ACTION_DELAY, flags="", **kwargs):
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
        self.element = "NONE"
        # 플래그 처리
        self.flags = {f.strip().upper() for f in flags.split(',') if f.strip()}
        # kwargs는 향후 필드 추가에 대비한 안전장치

class SkillDefinition:
    """스킬 데이터를 담는 컨테이너 (CSV/텍스트파일 연동)"""
    def __init__(self, ID, 이름, 필요레벨, 속성, 소모타입, 소모값, 필요장비, 효과_설명, 데미지, 스킬타입, 스킬서브타입, 사거리, 적중효과="없음", flags="", **kwargs):
        self.id = ID
        self.name = 이름
        self.required_level = int(필요레벨)
        self.element = 속성
        self.cost_type = 소모타입
        self.cost_value = int(소모값)
        self.required_weapon = 필요장비
        self.description = 효과_설명
        self.damage = int(데미지)
        self.type = 스킬타입           # ATTACK, RECOVERY
        self.subtype = 스킬서브타입    # PROJECTILE, AREA, SELF
        self.range = int(사거리)
        self.on_hit_effect = 적중효과 # EXPLOSION, STUN, KNOCKBACK 등
        # 플래그 처리
        self.flags = {f.strip().upper() for f in flags.split(',') if f.strip()}

class MapConfigDefinition:
    """층별 맵 설정을 담는 컨테이너"""
    def __init__(self, floor, width, height, monster_pool, item_pool, chest_count, mimic_prob, trap_prob, min_lvl, max_lvl, map_type, has_boss=0, boss_count=0, boss_ids="", **kwargs):
        self.floor = int(floor)
        self.width = int(width)
        self.height = int(height)
        self.monster_pool = [m.strip() for m in monster_pool.split(',') if m.strip()]
        self.item_pool = [i.strip() for i in item_pool.split(',') if i.strip()]
        self.chest_count = int(chest_count)
        self.mimic_prob = float(mimic_prob)
        self.trap_prob = float(trap_prob)
        self.min_lvl = int(min_lvl)
        self.max_lvl = int(max_lvl)
        self.map_type = map_type
        self.has_boss = int(has_boss) > 0
        self.boss_count = int(boss_count)
        self.boss_ids = [b.strip() for b in boss_ids.split(',') if b.strip()]

# -----------------------------------------------------------------------
# [추가] load_data_from_csv 헬퍼 함수
# -----------------------------------------------------------------------
def load_data_from_csv(file_name, definition_class, data_path="data", key_field=None):
    DATA_DEFINITIONS = {}
    file_path = os.path.join(data_path, file_name)
    
    if not os.path.exists(file_path):
        print(f"WARNING: Data file not found at {file_path}")
        return {}

    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 키 정제 (공백 및 # 제거)
                clean_row = {}
                for k, v in row.items():
                    if k:
                        clean_key = k.strip().lstrip('#').strip()
                        clean_row[clean_key] = v
                
                # 정제된 딕셔너리로 객체 생성
                def_obj = definition_class(**clean_row)

                # 키 설정
                if key_field:
                    key = clean_row.get(key_field)
                else:
                    # 기본 휴리스틱 (하위 호환성)
                    if definition_class is ItemDefinition:
                        key = clean_row.get('name')
                    elif definition_class is SkillDefinition:
                        key = clean_row.get('이름') or clean_row.get('name')
                    else:
                        key = clean_row.get('ID')
                
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

def load_monster_definitions(data_path="data"):
    """monsters.csv 및 Boss.csv 파일에서 몬스터 정의 로드"""
    defs = load_data_from_csv('monsters.csv', MonsterDefinition, data_path, key_field='ID')
    bosses = load_data_from_csv('Boss.csv', MonsterDefinition, data_path, key_field='ID')
    defs.update(bosses)
    return defs

def load_skill_definitions(data_path="data"):
    """skills.csv 파일에서 스킬 정의 로드"""
    return load_data_from_csv('skills.csv', SkillDefinition, data_path, key_field='이름')

def load_map_definitions(data_path="data"):
    """maps.csv 파일에서 층별 맵 설정 로드"""
    return load_data_from_csv('maps.csv', MapConfigDefinition, data_path, key_field='floor')

def save_game_data(data, name):
    """플레이어 이름을 기반으로 게임 데이터 저장"""
    import json
    save_dir = "game_data"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    filename = f"{name}.json"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    # print(f"Game saved to {file_path}")

def load_game_data(name):
    """플레이어 이름을 기반으로 저장된 게임 데이터 로드 (JSON)"""
    import json
    filename = f"{name}.json"
    file_path = os.path.join("game_data", filename)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load save file: {e}")
        return None

def delete_save_data(name):
    """플레이어 이름을 기반으로 저장 데이터 삭제"""
    filename = f"{name}.json"
    file_path = os.path.join("game_data", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        # print(f"Save file {filename} deleted.")

def list_save_files():
    """game_data 디렉토리의 모든 세이브 파일(.json) 목록을 반환"""
    save_dir = "game_data"
    if not os.path.exists(save_dir) or not os.path.isdir(save_dir):
        return []
    
    files = [f.replace('.json', '') for f in os.listdir(save_dir) if f.endswith('.json')]
    return sorted(files)


