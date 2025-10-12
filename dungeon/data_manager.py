# data_manager.py

import os
import re
import json
from .items import Item

# 게임 데이터 저장 경로
SAVE_DIR = "game_data"
PLAYER_SAVE_FILE = os.path.join(SAVE_DIR, "player_data.json")
DUNGEON_MAPS_SAVE_FILE = os.path.join(SAVE_DIR, "all_dungeon_maps.json")


# 아이템 데이터 파일 경로
ITEM_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "items.txt")
# 몬스터 데이터 파일 경로 추가
MONSTER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "monster_data.txt")
# 스킬 데이터 파일 경로 추가
SKILL_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "skills.txt")
# 함정 데이터 파일 경로 추가
TRAP_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "traps.txt")

class ItemDefinition:
    """아이템의 정의(템플릿)를 저장하는 클래스."""
    def __init__(self, item_id, name, item_type, equip_slot, effect_type, value, description="", req_level=0):
        self.id = item_id
        self.name = name
        self.item_type = item_type    # EQUIP, SKILLBOOK, CONSUMABLE, ETC
        self.equip_slot = equip_slot  # WEAPON, SHIELD, HELMET, ARMOR, GLOVES, BOOTS, NECKLACE, RING, NONE
        self.effect_type = effect_type # HP_RECOVER, MP_RECOVER, ATTACK, DEFENSE, KEY, NONE
        self.value = value             # 회복량, 공격력/방어력 증가량 등
        self.description = description
        self.req_level = req_level

    def __repr__(self):
        return (
            f"ItemDefinition(id={self.id}, name={self.name}, item_type={self.item_type}, "
            f"equip_slot={self.equip_slot}, effect_type={self.effect_type}, value={self.value}, "
            f"description='{self.description}', req_level={self.req_level})"
        )
class TrapDefinition:
    """함정의 정의(템플릿)를 저장하는 클래스."""
    def __init__(self, trap_id, name, symbol, color, trigger_type, effect_type, damage, radius):
        self.id = trap_id
        self.name = name
        self.symbol = symbol
        self.color = color
        self.trigger_type = trigger_type
        self.effect_type = effect_type
        self.damage = damage
        self.radius = radius

    def __repr__(self):
        return (
            f"TrapDefinition(id={self.id}, name={self.name}, symbol='{self.symbol}', color='{self.color}', "
            f"trigger_type='{self.trigger_type}', effect_type='{self.effect_type}', "
            f"damage={self.damage}, radius={self.radius})"
        )

class SkillDefinition:
    """스킬의 정의(템플릿)를 저장하는 클래스."""
    def __init__(self, skill_id, name, req_level, attribute, cost_type, cost_value, req_equip, description, damage, skill_type, skill_subtype, range_str):
        self.id = skill_id
        self.name = name
        self.req_level = req_level
        self.attribute = attribute
        self.cost_type = cost_type
        self.cost_value = cost_value
        self.req_equip = req_equip
        self.description = description
        self.damage = damage
        self.skill_type = skill_type
        self.skill_subtype = skill_subtype
        self.range_str = range_str

    def __repr__(self):
        return (
            f"SkillDefinition(id={self.id}, name={self.name}, req_level={self.req_level}, "
            f"attribute={self.attribute}, cost_type={self.cost_type}, cost_value={self.cost_value}, "
            f"req_equip={self.req_equip}, description='{self.description}', damage={self.damage}, "
            f"skill_type='{self.skill_type}', skill_subtype='{self.skill_subtype}', range_str={self.range_str})"
        )

class MonsterDefinition:
    """몬스터의 정의(템플릿)를 저장하는 클래스."""
    def __init__(self, monster_id, name, symbol, hp, attack, defense, level, exp_given, critical_chance, critical_damage_multiplier, move_type):
        self.id = monster_id
        self.name = name
        self.symbol = symbol
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.level = level
        self.exp_given = exp_given
        self.critical_chance = critical_chance
        self.critical_damage_multiplier = critical_damage_multiplier
        self.move_type = move_type

    def __repr__(self):
        return (
            f"MonsterDefinition(id={self.id}, name={self.name}, symbol={self.symbol}, hp={self.hp}, attack={self.attack}, "
            f"defense={self.defense}, level={self.level}, exp_given={self.exp_given}, "
            f"critical_chance={self.critical_chance}, critical_damage_multiplier={self.critical_damage_multiplier}, "
            f"move_type={self.move_type})"
        )

_item_definitions = {} # 아이템 정의를 저장할 전역 딕셔너리
_monster_definitions = {} # 몬스터 정의를 저장할 전역 딕셔너리
_skill_definitions = {} # 스킬 정의를 저장할 전역 딕셔너리
_trap_definitions = {} # 함정 정의를 저장할 전역 딕셔너리

def load_item_definitions(ui_instance=None):
    """items.txt 파일에서 아이템 정의를 로드합니다."""
    if _item_definitions: # 이미 로드된 경우 다시 로드하지 않음
        return _item_definitions

    if not os.path.exists(ITEM_DATA_FILE):
        if ui_instance:
            ui_instance.add_message(f"오류: 아이템 데이터 파일이 존재하지 않습니다: {ITEM_DATA_FILE}")
        else:
            print(f"오류: 아이템 데이터 파일이 존재하지 않습니다: {ITEM_DATA_FILE}")
        return {}

    with open(ITEM_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): # 빈 줄 또는 주석 건너뛰기
                continue
            
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6: # 최소 6개의 필드 확인
                item_id, name, item_type, equip_slot, effect_type, value_str = parts[:6]
                req_level_str = parts[6] if len(parts) > 6 else "0"
                description = parts[7] if len(parts) > 7 else ""

                # 값 변환
                try:
                    value = float(value_str)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    value = value_str # 숫자로 변환할 수 없으면 문자열로 유지
                
                try:
                    req_level = int(req_level_str)
                except ValueError:
                    req_level = 0


                _item_definitions[item_id] = ItemDefinition(
                    item_id, name, item_type.upper(), equip_slot.upper(), effect_type.upper(), value, description, req_level
                )
            else:
                if ui_instance:
                    ui_instance.add_message(f"경고: 잘못된 형식의 아이템 데이터 줄: {line}")
                else:
                    print(f"경고: 잘못된 형식의 아이템 데이터 줄: {line}")
    return _item_definitions

def get_item_definition(item_id):
    """지정된 ID의 아이템 정의를 반환합니다. 동적 키 생성 포함."""
    if not _item_definitions:
        load_item_definitions()

    # 먼저 기존 정의에서 찾아봅니다.
    if item_id in _item_definitions:
        return _item_definitions[item_id]

    # 동적 열쇠 ID 형식인지 확인 (예: "1F_Key", "12F_Key")
    match = re.match(r'(\d+)F_Key', item_id)
    if match:
        level = int(match.group(1))
        # 동적으로 ItemDefinition 객체를 생성하여 반환
        return ItemDefinition(
            item_id=item_id,
            name=f"{level}층 열쇠",
            item_type='ETC',
            equip_slot='NONE',
            effect_type='KEY',
            value=0
        )

    # 어디에도 해당하지 않으면 None을 반환
    return None

def get_monster_definition(monster_id):
    """지정된 ID의 몬스터 정의를 반환합니다."""
    if not _monster_definitions:
        load_monster_definitions()
    return _monster_definitions.get(monster_id)

def load_monster_definitions(ui_instance=None):
    """monster_data.txt 파일에서 몬스터 정의를 로드합니다."""
    if _monster_definitions: # 이미 로드된 경우 다시 로드하지 않음
        return _monster_definitions

    if not os.path.exists(MONSTER_DATA_FILE):
        if ui_instance:
            ui_instance.add_message(f"오류: 몬스터 데이터 파일이 존재하지 않습니다: {MONSTER_DATA_FILE}")
        else:
            print(f"오류: 몬스터 데이터 파일이 존재하지 않습니다: {MONSTER_DATA_FILE}")
        return {}

    with open(MONSTER_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): # 빈 줄 또는 주석 건너뛰기
                continue
            
            parts = [p.strip() for p in line.split(',')]
            
            # 필드 개수에 따라 하위 호환성 유지
            if len(parts) >= 11: # 심볼, 이동 타입 포함
                monster_id, name, symbol, hp, attack, defense, level, exp_given, crit_chance, crit_mult, move_type = parts[:11]
                _monster_definitions[monster_id] = MonsterDefinition(
                    monster_id, name, symbol, int(hp), int(attack), int(defense), int(level), int(exp_given),
                    float(crit_chance), float(crit_mult), move_type
                )
            elif len(parts) >= 10: # 심볼 미포함, 이동 타입 포함 (하위호환)
                monster_id, name, hp, attack, defense, level, exp_given, crit_chance, crit_mult, move_type = parts[:10]
                _monster_definitions[monster_id] = MonsterDefinition(
                    monster_id, name, name[0], int(hp), int(attack), int(defense), int(level), int(exp_given),
                    float(crit_chance), float(crit_mult), move_type
                )
            else:
                if ui_instance:
                    ui_instance.add_message(f"경고: 잘못된 형식의 몬스터 데이터 줄: {line}")
                else:
                    print(f"경고: 잘못된 형식의 몬스터 데이터 줄: {line}")
    return _monster_definitions

def load_skill_definitions(ui_instance=None):
    """skills.txt 파일에서 스킬 정의를 로드합니다."""
    if _skill_definitions: # 이미 로드된 경우 다시 로드하지 않음
        return _skill_definitions

    if not os.path.exists(SKILL_DATA_FILE):
        if ui_instance:
            ui_instance.add_message(f"오류: 스킬 데이터 파일이 존재하지 않습니다: {SKILL_DATA_FILE}")
        else:
            print(f"오류: 스킬 데이터 파일이 존재하지 않습니다: {SKILL_DATA_FILE}")
        return {}

    with open(SKILL_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                # parts = line.split(',')
                parts = [p.strip() for p in line.split(',')] # 공백 제거
                if len(parts) < 12:
                    # 하위 호환성을 위해 기본값 설정
                    parts.extend(['UNKNOWN', '0'] * (12 - len(parts)))
                
                skill_id, name, req_level, attribute, cost_type, cost_value, req_equip, description, damage, skill_type, skill_subtype, range_str = parts[:12]
                _skill_definitions[skill_id] = SkillDefinition(
                    skill_id, name, int(req_level), attribute, cost_type, int(cost_value), 
                    req_equip, description, int(damage), skill_type, skill_subtype, int(range_str)
                )
            except (ValueError, IndexError) as e:
                error_message = f"경고: 잘못된 형식의 스킬 데이터 줄: {line} (오류: {e})"
                if ui_instance:
                    ui_instance.add_message(error_message)
                else:
                    print(error_message)
    return _skill_definitions

def get_skill_definition(skill_id):
    """지정된 ID의 스킬 정의를 반환합니다."""
    if not _skill_definitions:
        load_skill_definitions()
    return _skill_definitions.get(skill_id)

def load_trap_definitions(ui_instance=None):
    """traps.txt 파일에서 함정 정의를 로드합니다."""
    if _trap_definitions:
        return _trap_definitions

    if not os.path.exists(TRAP_DATA_FILE):
        if ui_instance:
            ui_instance.add_message(f"오류: 함정 데이터 파일이 존재하지 않습니다: {TRAP_DATA_FILE}")
        else:
            print(f"오류: 함정 데이터 파일이 존재하지 않습니다: {TRAP_DATA_FILE}")
        return {}

    with open(TRAP_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 8:
                    continue
                
                trap_id, name, symbol, color, trigger_type, effect_type, damage, radius = parts[:8]
                _trap_definitions[trap_id] = TrapDefinition(
                    trap_id, name, symbol, color, trigger_type, effect_type, int(damage), int(radius)
                )
            except (ValueError, IndexError) as e:
                error_message = f"경고: 잘못된 형식의 함정 데이터 줄: {line} (오류: {e})"
                if ui_instance:
                    ui_instance.add_message(error_message)
                else:
                    print(error_message)
    return _trap_definitions

def get_trap_definition(trap_id):
    """지정된 ID의 함정 정의를 반환합니다."""
    if not _trap_definitions:
        load_trap_definitions()
    return _trap_definitions.get(trap_id)

# --- 게임 데이터 저장 및 로드 함수 ---

def save_game_data(player_entity_id, all_dungeon_maps, ui_instance, game_state_data):
    """게임 데이터를 파일에 저장합니다."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    try:
        # 1. 전체 게임 상태 데이터 저장
        with open(PLAYER_SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(game_state_data, f, ensure_ascii=False, indent=4)
        
        if ui_instance:
            ui_instance.add_message("게임 데이터가 성공적으로 저장되었습니다.")
            
    except Exception as e:
        if ui_instance:
            ui_instance.add_message(f"데이터 저장 중 오류 발생: {e}")

def load_game_data():
    """저장된 전체 게임 데이터를 불러옵니다."""
    if not os.path.exists(PLAYER_SAVE_FILE):
        return None
    with open(PLAYER_SAVE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_save_data():
    """모든 저장 데이터를 삭제합니다."""
    if os.path.exists(PLAYER_SAVE_FILE):
        os.remove(PLAYER_SAVE_FILE)
    if os.path.exists(DUNGEON_MAPS_SAVE_FILE):
        os.remove(DUNGEON_MAPS_SAVE_FILE)


# 스크립트 실행 시 자동으로 아이템 정의 로드
if __name__ == "__main__":
    definitions = load_item_definitions()
    print("로드된 아이템 정의:")
    for item_id, item_def in definitions.items():
        print(item_def)
    
    monster_defs = load_monster_definitions()
    print("\n로드된 몬스터 정의:")
    for monster_id, monster_def in monster_defs.items():
        print(monster_def)

    skill_defs = load_skill_definitions()
    print("\n로드된 스킬 정의:")
    for skill_id, skill_def in skill_defs.items():
        print(skill_def)
