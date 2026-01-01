import csv
import os

# -----------------------------------------------------------------------
# ItemDefinition 클래스 정의 (기존 내용 유지)
# -----------------------------------------------------------------------
def parse_damage_range(value):
    """'10-20' 또는 '15' 같은 값을 (min, max) 튜플로 변환"""
    if isinstance(value, (int, float)):
        return int(value), int(value)
    
    if not isinstance(value, str) or not value.strip():
        return 0, 0
        
    if '-' in value:
        try:
            parts = value.split('-')
            return int(parts[0].strip()), int(parts[1].strip())
        except (ValueError, IndexError):
            return 0, 0
    else:
        try:
            val = int(value.strip())
            return val, val
        except ValueError:
            return 0, 0


# -----------------------------------------------------------------------
class PrefixDefinition:
    def __init__(self, id, data):
        self.id = id
        self.name_kr = data.get("name_kr", id)
        self.allowed_types = set(data.get("allowed_types", []))
        self.min_level = data.get("min_level", 1)
        
        # Stats Ranges (Min, Max)
        self.to_hit_bonus_min = data.get("to_hit_bonus_min", 0)
        self.to_hit_bonus_max = data.get("to_hit_bonus_max", 0)
        
        self.damage_percent_min = data.get("damage_percent_min", 0)
        self.damage_percent_max = data.get("damage_percent_max", 0)
        
        self.mp_bonus_min = data.get("mp_bonus_min", 0)
        self.mp_bonus_max = data.get("mp_bonus_max", 0)
        
        self.res_lightning_min = data.get("res_lightning_min", 0)
        self.res_lightning_max = data.get("res_lightning_max", 0)
        
        self.res_ice_min = data.get("res_ice_min", 0)
        self.res_ice_max = data.get("res_ice_max", 0)
        
        self.res_fire_min = data.get("res_fire_min", 0)
        self.res_fire_max = data.get("res_fire_max", 0)
        
        self.res_poison_min = data.get("res_poison_min", 0)
        self.res_poison_max = data.get("res_poison_max", 0)
        
        self.res_all_min = data.get("res_all_min", 0)
        self.res_all_max = data.get("res_all_max", 0)
        
        # Element override (optional)
        self.element = data.get("element", None)
        
        # Flags
        self.flags = set(data.get("flags", []))

def load_prefixes():
    import json
    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', 'prefixes.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {k: PrefixDefinition(k, v) for k, v in data.items()}
    except FileNotFoundError:
        print(f"Warning: {filepath} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding {filepath}: {e}")
        return {}

# -----------------------------------------------------------------------
class SuffixDefinition:
    def __init__(self, id, data):
        self.id = id
        self.name_kr = data.get("name_kr", id)
        self.allowed_types = set(data.get("allowed_types", []))
        self.min_level = data.get("min_level", 1)
        
        # Stat Ranges
        self.str_bonus_min = data.get("str_bonus_min", 0)
        self.str_bonus_max = data.get("str_bonus_max", 0)
        
        self.dex_bonus_min = data.get("dex_bonus_min", 0)
        self.dex_bonus_max = data.get("dex_bonus_max", 0)
        
        self.mag_bonus_min = data.get("mag_bonus_min", 0)
        self.mag_bonus_max = data.get("mag_bonus_max", 0)
        
        self.vit_bonus_min = data.get("vit_bonus_min", 0)
        self.vit_bonus_max = data.get("vit_bonus_max", 0)
        
        self.hp_bonus_min = data.get("hp_bonus_min", 0)
        self.hp_bonus_max = data.get("hp_bonus_max", 0)
        
        self.mp_bonus_min = data.get("mp_bonus_min", 0)
        self.mp_bonus_max = data.get("mp_bonus_max", 0)
        
        self.damage_max_bonus_min = data.get("damage_max_bonus_min", 0)
        self.damage_max_bonus_max = data.get("damage_max_bonus_max", 0)
        
        # Fixed Value Stats
        self.life_leech_min = data.get("life_leech_min", 0)
        self.life_leech_max = data.get("life_leech_max", 0)
        
        self.attack_speed = data.get("attack_speed", 0)

def load_suffixes():
    import json
    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', 'suffixes.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {k: SuffixDefinition(k, v) for k, v in data.items()}
    except FileNotFoundError:
        print(f"Warning: {filepath} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding {filepath}: {e}")
        return {}

# -----------------------------------------------------------------------
# ItemDefinition 클래스 정의 (기존 내용 유지)
# -----------------------------------------------------------------------
class ItemDefinition:
    # 'item_type' 대신 CSV 헤더와 동일하게 'type'으로 인자명을 통일합니다.
    def __init__(self, name, type, description, symbol, color, required_level, attack, defense, hp_effect, mp_effect, hand_type=1, attack_range=1, skill_id=None, flags="", 
                 str_bonus=0, mag_bonus=0, dex_bonus=0, vit_bonus=0, duration=0, min_floor=1, **kwargs):
        self.name = name
        self.type = type # 'self.type'에 'type' 인자를 할당합니다.
        self.description = description
        self.symbol = symbol
        self.color = color
        self.required_level = int(required_level)
        self.min_floor = int(min_floor)
        self.attack_min, self.attack_max = parse_damage_range(attack)
        self.attack = self.attack_max # 하위 호환성 유지 (최댓값을 기본 attack으로)
        self.defense_min, self.defense_max = parse_damage_range(defense)
        self.defense = self.defense_max
        self.hp_effect = int(hp_effect)
        self.mp_effect = int(mp_effect)
        self.hand_type = int(hand_type) # 1: 한손, 2: 양손
        self.attack_range = int(attack_range)
        self.skill_id = skill_id
        # 능력치 보너스
        self.str_bonus = int(str_bonus)
        self.mag_bonus = int(mag_bonus)
        self.dex_bonus = int(dex_bonus)
        self.vit_bonus = int(vit_bonus)
        self.duration = int(duration)
        
        # Durability
        self.max_durability = int(kwargs.get('max_durability', 0))
        self.current_durability = int(kwargs.get('current_durability', self.max_durability))
        
        # Charges (Magic staffs)
        self.max_charges = int(kwargs.get('max_charges', 0))
        if self.type == "SKILLBOOK":
            self.max_charges = 0 # Skill books should never have charges
        elif self.max_charges == 0 and self.skill_id and self.skill_id != "None":
             self.max_charges = 20 # Default charges for magical items (staves etc)
             
        self.current_charges = int(kwargs.get('current_charges', self.max_charges))
        
        # [Shrine] Enhancement Level
        self.enhancement_level = int(kwargs.get('enhancement_level', 0))  # 0 to +10

        # 플래그 처리 (콤마로 구분된 문자열을 Set으로 변환, 리스트인 경우 그대로 변환)
        if isinstance(flags, list):
             self.flags = set(flags)
        elif isinstance(flags, str):
             self.flags = {f.strip().upper() for f in flags.split(',') if f.strip()}
        else:
             self.flags = set()
        

        # [Affix System] 접두사/접미사 보너스 저장을 위한 동적 속성 (인스턴스 생성 시 오버라이드 됨)
        # kwargs에서 복원 시도
        self.prefix_id = kwargs.get('prefix_id', None)
        self.suffix_id = kwargs.get('suffix_id', None)
        
        self.damage_percent = kwargs.get('damage_percent', 0)
        self.to_hit_bonus = kwargs.get('to_hit_bonus', 0)
        self.mp_bonus = kwargs.get('mp_bonus', 0)
        self.hp_bonus = kwargs.get('hp_bonus', 0)
        self.damage_max_bonus = kwargs.get('damage_max_bonus', 0)
        
        self.res_fire = kwargs.get('res_fire', 0)
        self.res_ice = kwargs.get('res_ice', 0)
        self.res_lightning = kwargs.get('res_lightning', 0)
        self.res_poison = kwargs.get('res_poison', 0)
        self.res_all = kwargs.get('res_all', 0)
        
        # Suffix Only
        self.life_leech = kwargs.get('life_leech', 0)
        self.attack_speed = kwargs.get('attack_speed', 0)
        
        # Identification Status
        self.is_identified = kwargs.get('is_identified', True)


    def to_dict(self):
        """JSON 저장을 위해 딕셔너리로 변환"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "symbol": self.symbol,
            "color": self.color,
            "required_level": self.required_level,
            "min_floor": self.min_floor,
            "attack": self.attack_max,
            "attack_min": self.attack_min,
            "attack_max": self.attack_max,
            "defense": self.defense,
            "hp_effect": self.hp_effect,
            "mp_effect": self.mp_effect,
            "hand_type": self.hand_type,
            "attack_range": self.attack_range,
            "skill_id": getattr(self, "skill_id", None),
            "str_bonus": self.str_bonus,
            "mag_bonus": self.mag_bonus,
            "dex_bonus": self.dex_bonus,
            "vit_bonus": self.vit_bonus,
            "duration": self.duration,
            "flags": ",".join(self.flags),
            
            # [Affix System]
            "prefix_id": self.prefix_id,
            "suffix_id": self.suffix_id,
            
            "damage_percent": self.damage_percent,
            "to_hit_bonus": self.to_hit_bonus,
            "mp_bonus": self.mp_bonus,
            "hp_bonus": self.hp_bonus,
            "damage_max_bonus": self.damage_max_bonus,
            
            "res_fire": self.res_fire,
            "res_ice": self.res_ice,
            "res_lightning": self.res_lightning,
            "res_poison": self.res_poison,
            "res_all": self.res_all,
            
            "is_identified": self.is_identified,
            
            "life_leech": self.life_leech,
            "attack_speed": self.attack_speed,
            
            # [Durability]
            "current_durability": getattr(self, "current_durability", 0),
            "max_durability": getattr(self, "max_durability", 0),
            
            # [Charges]
            "current_charges": getattr(self, "current_charges", 0),
            "max_charges": getattr(self, "max_charges", 0),
            
            # [Shrine]
            "enhancement_level": getattr(self, "enhancement_level", 0)
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
        self.attack_min, self.attack_max = parse_damage_range(ATT)
        self.attack = self.attack_max # 하위 호환성 유지
        self.defense = int(DEF)
        self.level = int(LV)
        self.xp_value = int(EXP_GIVEN)
        self.crit_chance = float(CRIT_CHANCE)
        self.crit_mult = float(CRIT_MULT)
        self.move_type = MOVE_TYPE
        self.action_delay = float(ACTION_DELAY)
        
        # 신규 속성 및 플래그
        self.element = kwargs.get('element', 'NONE').upper()
        self.flags = {f.strip().upper() for f in flags.split(',') if f.strip()} if isinstance(flags, str) else set()
        
        # [Diablo 1] 저항력
        self.res_fire = int(kwargs.get('res_fire', 0))
        self.res_ice = int(kwargs.get('res_ice', 0))
        self.res_lightning = int(kwargs.get('res_lightning', 0))
        self.res_poison = int(kwargs.get('res_poison', 0))

class ClassDefinition:
    """캐릭터 직업 정의 (Warrior, Rogue, 등)"""
    def __init__(self, class_id, name, hp, mp, strength, mag, dex, vit, base_skill, description, **kwargs):
        self.class_id = class_id
        self.name = name
        self.hp = int(hp)
        self.mp = int(mp)
        self.str = int(strength)
        self.mag = int(mag)
        self.dex = int(dex)
        self.vit = int(vit)
        self.base_skill = base_skill
        self.description = description
        
        # 기본값 설정 및 kwargs 대응
        self.crit_chance = float(kwargs.get('crit_chance', 0.05))
        self.crit_mult = float(kwargs.get('crit_mult', 1.5))
        self.move_type = kwargs.get('move_type', "WALK")
        self.action_delay = float(kwargs.get('action_delay', 0.2))
        self.element = kwargs.get('element', "NONE")
        
        # 플래그 처리
        flags_str = kwargs.get('flags', "")
        self.flags = {f.strip().upper() for f in flags_str.split(',') if f.strip()}

        # [Diablo 1] 성장치
        self.hp_gain = float(kwargs.get('hp_gain', 2.0))
        self.mp_gain = float(kwargs.get('mp_gain', 1.0))
        
        # [New] 스탯 변환 비율
        self.vit_to_hp = float(kwargs.get('vit_to_hp', 2.0))
        self.mag_to_mp = float(kwargs.get('mag_to_mp', 1.0))

        # [New] 초기 지급 아이템 파싱 (Format: "Item1:1|Item2:5|Gold:100")
        self.starting_items = []
        raw_items = kwargs.get('starting_items', "")
        if raw_items:
            for entry in raw_items.split('|'):
                if ':' in entry:
                    name, qty_str = entry.split(':')
                    try:
                        self.starting_items.append((name.strip(), int(qty_str)))
                    except ValueError:
                        pass
                else:
                    self.starting_items.append((entry.strip(), 1))

class SkillDefinition:
    """스킬 데이터를 담는 컨테이너 (CSV/텍스트파일 연동)"""
    def __init__(self, ID, 이름, 분류, 필요레벨, 속성, 소모타입, 소모값, 필요장비, 효과_설명, 데미지, 스킬타입, 스킬서브타입, 사거리, 적중효과="없음", flags="", 
                 str_bonus=0, mag_bonus=0, dex_bonus=0, vit_bonus=0, duration=0, **kwargs):
        self.id = ID
        self.name = 이름
        self.category = 분류
        self.required_level = int(필요레벨)
        self.element = 속성
        self.cost_type = 소모타입
        self.cost_value = int(소모값)
        self.required_weapon = 필요장비
        self.description = 효과_설명
        self.damage_min, self.damage_max = parse_damage_range(데미지)
        self.damage = self.damage_max # 하위 호환성 유지
        self.type = 스킬타입           # ATTACK, RECOVERY
        self.subtype = 스킬서브타입    # PROJECTILE, AREA, SELF
        self.range = int(사거리)
        self.on_hit_effect = 적중효과 # EXPLOSION, STUN, KNOCKBACK 등
        # 능력치 보너스 및 지속 시간
        self.str_bonus = int(str_bonus)
        self.mag_bonus = int(mag_bonus)
        self.dex_bonus = int(dex_bonus)
        self.vit_bonus = int(vit_bonus)
        self.duration = int(duration)
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

def load_class_definitions(data_path="data"):
    """classes.csv 파일에서 캐릭터 직업 정의 로드"""
    return load_data_from_csv('classes.csv', ClassDefinition, data_path, key_field='class_id')

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


