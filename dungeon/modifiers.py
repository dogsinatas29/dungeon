import json
import os
import copy
import random
from .data_manager import ItemDefinition, MonsterDefinition

class ModifierManager:
    """접두어 데이터를 로드하고 아이템/몬스터에 적용하는 관리자"""
    def __init__(self):
        self.prefixes = {}
        self.load_prefixes()

    def load_prefixes(self):
        try:
            path = os.path.join(os.path.dirname(__file__), '..', 'data', 'prefixes.json')
            with open(path, 'r', encoding='utf-8') as f:
                self.prefixes = json.load(f)
        except Exception as e:
            print(f"Error loading prefixes: {e}")

    def get_random_prefix(self):
        if not self.prefixes: return None
        return random.choice(list(self.prefixes.keys()))

    def apply_item_prefix(self, item_def: ItemDefinition, prefix_name: str = None) -> ItemDefinition:
        """아이템에 접두어 적용 (ItemDefinition 복제본 반환)"""
        if not self.prefixes: return item_def
        
        if prefix_name is None:
            prefix_name = self.get_random_prefix()
            
        if prefix_name not in self.prefixes:
            return item_def
        
        prefix_data = self.prefixes[prefix_name]
        new_item = copy.copy(item_def)
        
        # 이름 변경
        new_item.name = f"{prefix_data['name_kr']} {item_def.name}"
        
        # 스탯 적용
        new_item.attack += prefix_data.get('attack_bonus', 0)
        new_item.defense += prefix_data.get('defense_bonus', 0)
        
        # 속성 적용
        if 'element' in prefix_data:
            # StatsComponent.flags 로직을 위해 flags에도 추가
            new_item.flags.add(prefix_data['element'].upper())
            if prefix_data['element'] == '불': new_item.color = 'red'
            elif prefix_data['element'] == '물': new_item.color = 'blue'
                
        # 플래그 적용
        p_flags = prefix_data.get('flags', [])
        new_item.flags = new_item.flags.copy()
        for f in p_flags:
            new_item.flags.add(f.strip().upper())
            
        return new_item

    def apply_monster_prefix(self, monster_def: MonsterDefinition, prefix_name: str = None) -> MonsterDefinition:
        """몬스터에 접두어 적용 (MonsterDefinition 복제본 반환)"""
        if not self.prefixes: return monster_def

        if prefix_name is None:
            prefix_name = self.get_random_prefix()
            
        if prefix_name not in self.prefixes:
            return monster_def
            
        prefix_data = self.prefixes[prefix_name]
        new_mon = copy.copy(monster_def)
        
        # 이름 변경
        new_mon.name = f"{prefix_data['name_kr']} {monster_def.name}"
        
        # 스탯 적용
        new_mon.attack += prefix_data.get('attack_bonus', 0)
        new_mon.defense += prefix_data.get('defense_bonus', 0)
        new_mon.hp += prefix_data.get('hp_bonus', 0)
        # MP나 Stamina는 MonsterDefinition에 기본적으로 없을 수 있으나, 
        # 시스템 확장성을 위해 속성이 있다면 더해줌 (일단은 무시하거나 동적으로 할당)
        
        # 속성 적용
        if 'element' in prefix_data:
            # 몬스터 기본 속성이 있었다면 교체? 아니면 추가? -> 여기선 교체/추가 개념이 모호하므로 flags에 추가
            new_mon.element = prefix_data['element']
            new_mon.flags.add(prefix_data['element'].upper())
            if prefix_data['element'] == '불': new_mon.color = 'red'
            elif prefix_data['element'] == '물': new_mon.color = 'blue'

        # 플래그 적용
        p_flags = prefix_data.get('flags', [])
        new_mon.flags = new_mon.flags.copy()
        for f in p_flags:
            new_mon.flags.add(f.strip().upper())
            
        return new_mon
