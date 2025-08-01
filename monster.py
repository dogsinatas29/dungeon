# monster.py
import data_manager # data_manager 모듈 임포트

class Monster:
    def __init__(self, x, y, ui_instance=None, monster_id=None, name=None, symbol=None, hp=None, attack=None, defense=None, level=None, exp_given=None):
        self.ui_instance = ui_instance
        
        if monster_id:
            monster_def = data_manager.get_monster_definition(monster_id)
            if monster_def:
                self.name = monster_def.name
                self.symbol = monster_def.symbol
                self.hp = monster_def.hp
                self.max_hp = monster_def.hp
                self.attack = monster_def.attack
                self.defense = monster_def.defense
                self.level = monster_def.level
                self.exp_given = monster_def.exp_given
                self.critical_chance = monster_def.critical_chance
                self.critical_damage_multiplier = monster_def.critical_damage_multiplier
                self.move_type = monster_def.move_type
            else:
                self.name = name if name else "알 수 없는 몬스터"
                self.symbol = symbol if symbol else '?'
                self.hp = hp if hp else 30
                self.max_hp = self.hp
                self.attack = attack if attack else 8
                self.defense = defense if defense else 2
                self.level = level if level else 1
                self.exp_given = exp_given if exp_given else 10
                self.critical_chance = 0.05
                self.critical_damage_multiplier = 1.5
                self.move_type = 'STATIONARY'
                if self.ui_instance:
                    self.ui_instance.add_message(f"경고: 몬스터 정의 '{monster_id}'를 찾을 수 없습니다. 기본값 사용.")
        else:
            self.name = name if name else "몬스터"
            self.symbol = symbol if symbol else name[0] if name else 'M'
            self.hp = hp if hp else 30
            self.max_hp = self.hp
            self.attack = attack if attack else 8
            self.defense = defense if defense else 2
            self.level = level if level else 1
            self.exp_given = exp_given if exp_given else 10
            self.critical_chance = 0.05
            self.critical_damage_multiplier = 1.5
            self.move_type = 'STATIONARY'

        self.x = x
        self.y = y
        self.dead = False
        self.is_provoked = False
        self.loot = None  # 몬스터가 떨어뜨릴 아이템 추가
        self.loot = None  # 몬스터가 떨어뜨릴 아이템 추가
        self.loot = None  # 몬스터가 떨어뜨릴 아이템 추가

    def take_damage(self, amount):
        self.hp -= amount
        self.is_provoked = True
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
        return self.dead
    
    def attack(self, target_player):
        if self.ui_instance:
            self.ui_instance.add_message(f"{self.name}이(가) 공격합니다!")
        
        damage = max(1, self.attack - target_player.defense)
        target_player.take_damage(damage)

        if self.ui_instance:
            self.ui_instance.add_message(f"{damage}의 데미지를 입었습니다! 남은 HP: {target_player.hp}")
            if not target_player.is_alive():
                self.ui_instance.add_message("당신은 쓰러졌습니다...")

    def to_dict(self):
        return {
            "name": self.name, "symbol": self.symbol, "x": self.x, "y": self.y,
            "hp": self.hp, "max_hp": self.max_hp,
            "attack": self.attack, "defense": self.defense,
            "level": self.level,
            "exp_given": self.exp_given,
            "critical_chance": self.critical_chance,
            "critical_damage_multiplier": self.critical_damage_multiplier,
            "move_type": self.move_type,
            "is_provoked": self.is_provoked,
            "dead": self.dead,
            "loot": self.loot
        }

    @classmethod
    def from_dict(cls, data):
        monster = cls(
            x=data['x'], y=data['y'],
            name=data.get('name', '몬스터'),
            symbol=data.get('symbol', data.get('name', 'M')[0]),
            hp=data.get('hp', 30),
            attack=data.get('attack', 8),
            defense=data.get('defense', 2),
            level=data.get('level', 1),
            exp_given=data.get('exp_given', 10)
        )
        monster.max_hp = data.get('max_hp', monster.hp)
        monster.critical_chance = data.get('critical_chance', 0.05)
        monster.critical_damage_multiplier = data.get('critical_damage_multiplier', 1.5)
        monster.move_type = data.get('move_type', 'STATIONARY')
        monster.is_provoked = data.get('is_provoked', False)
        monster.dead = data.get('dead', False)
        monster.loot = data.get('loot', None)
        return monster

