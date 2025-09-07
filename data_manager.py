# data_manager.py

import os
import re

# 아이템 데이터 파일 경로
ITEM_DATA_FILE = os.path.join(os.path.dirname(__file__), "items.txt")
# 몬스터 데이터 파일 경로 추가
MONSTER_DATA_FILE = os.path.join(os.path.dirname(__file__), "monster_data.txt")

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
            f"description={self.description}, req_level={self.req_level})"
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