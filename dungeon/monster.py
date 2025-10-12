# monster.py
from . import data_manager # data_manager 모듈 임포트

class Monster:
    def __init__(self, ui_instance=None, monster_id=None, name=None, symbol=None, hp=None, attack=None, defense=None, level=None, exp_given=None):
        self.ui_instance = ui_instance
        
        if monster_id:
            monster_def = data_manager.get_monster_definition(monster_id)
            if monster_def:
                # self.name = monster_def.name # NameComponent에서 관리
                self.symbol = monster_def.symbol
                # self.hp = monster_def.hp # HealthComponent에서 관리
                # self.max_hp = monster_def.hp # HealthComponent에서 관리
                # self.attack = monster_def.attack # AttackComponent에서 관리
                # self.defense = monster_def.defense # DefenseComponent에서 관리
                self.level = monster_def.level
                self.exp_given = monster_def.exp_given
                # self.critical_chance = monster_def.critical_chance # AttackComponent에서 관리
                # self.critical_damage_multiplier = monster_def.critical_damage_multiplier # AttackComponent에서 관리
                self.move_type = monster_def.move_type
                self.original_move_type = self.move_type
            else:
                # self.name = name if name else "알 수 없는 몬스터" # NameComponent에서 관리
                self.symbol = symbol if symbol else '?'
                # self.hp = hp if hp else 30 # HealthComponent에서 관리
                # self.max_hp = self.hp # HealthComponent에서 관리
                # self.attack = attack if attack else 8 # AttackComponent에서 관리
                # self.defense = defense if defense else 2 # DefenseComponent에서 관리
                self.level = level if level else 1
                self.exp_given = exp_given if exp_given else 10
                # self.critical_chance = 0.05 # AttackComponent에서 관리
                # self.critical_damage_multiplier = 1.5 # AttackComponent에서 관리
                self.move_type = 'STATIONARY'
                self.original_move_type = self.move_type
                if self.ui_instance:
                    self.ui_instance.add_message(f"경고: 몬스터 정의 '{monster_id}'를 찾을 수 없습니다. 기본값 사용.")
        else:
            # self.name = name if name else "몬스터" # NameComponent에서 관리
            self.symbol = symbol if symbol else name[0] if name else 'M'
            # self.hp = hp if hp else 30 # HealthComponent에서 관리
            # self.max_hp = self.hp # HealthComponent에서 관리
            # self.attack = attack if attack else 8 # AttackComponent에서 관리
            # self.defense = defense if defense else 2 # DefenseComponent에서 관리
            self.level = level if level else 1
            self.exp_given = exp_given if exp_given else 10
            # self.critical_chance = 0.05 # AttackComponent에서 관리
            # self.critical_damage_multiplier = 1.5 # AttackComponent에서 관리
            self.move_type = 'STATIONARY'
            self.original_move_type = self.move_type

        self.dead = False
        self.is_provoked = False
        self.loot = None  # 몬스터가 떨어뜨릴 아이템 추가
        self.entity_id = None # ECS 엔티티 ID 추가

    def to_dict(self):
        return {
            "symbol": self.symbol,
            # "attack": self.attack, # AttackComponent에서 관리
            # "defense": self.defense, # DefenseComponent에서 관리
            "level": self.level,
            "exp_given": self.exp_given,
            # "critical_chance": self.critical_chance, # AttackComponent에서 관리
            # "critical_damage_multiplier": self.critical_damage_multiplier, # AttackComponent에서 관리
            "move_type": self.move_type,
            "original_move_type": self.original_move_type,
            "is_provoked": self.is_provoked,
            "dead": self.dead,
            "loot": self.loot,
            "entity_id": self.entity_id
        }

    @classmethod
    def from_dict(cls, data):
        monster = cls(
            symbol=data.get('symbol', data.get('name', 'M')[0]),
            level=data.get('level', 1),
            exp_given=data.get('exp_given', 10)
        )
        # monster.max_hp = data.get('max_hp', monster.hp) # HealthComponent에서 관리
        # monster.critical_chance = data.get('critical_chance', 0.05) # AttackComponent에서 관리
        # monster.critical_damage_multiplier = data.get('critical_damage_multiplier', 1.5) # AttackComponent에서 관리
        monster.move_type = data.get('move_type', 'STATIONARY')
        return monster

