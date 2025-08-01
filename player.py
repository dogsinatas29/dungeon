# player.py

class Player:
    def __init__(self, name, hp=100, mp=50, x=0, y=0, level=1, dungeon_level=(1, 0)):
        self.name = name
        self.char = '@'
        self.x = x
        self.y = y
        
        # 기본 스탯
        self.level = level
        self.max_hp = hp
        self.hp = hp
        self.max_mp = mp
        self.mp = mp
        self.base_att = 10
        self.base_def = 5
        
        # 보너스 스탯 (아이템, 버프 등)
        self.att_bonus = 0
        self.def_bonus = 0
        
        # 경험치
        self.exp = 0
        self.exp_to_next_level = 100
        
        # 치명타
        self.critical_chance = 0.05  # 5%
        self.critical_damage_multiplier = 1.5 # 150%
        
        # 기타
        self.dungeon_level = dungeon_level
        self.inventory = {}
        self.skills = {} # 스킬 추가
        self.is_provoked = False

    @property
    def attack(self):
        """최종 공격력 (기본 + 보너스)"""
        return self.base_att + self.att_bonus

    @property
    def defense(self):
        """최종 방어력 (기본 + 보너스)"""
        return self.base_def + self.def_bonus

    def is_alive(self):
        """플레이어가 살아있는지 여부를 반환합니다."""
        return self.hp > 0

    def add_item(self, item_id, item_name, qty=1):
        """인벤토리에 아이템을 추가합니다."""
        if item_id in self.inventory:
            self.inventory[item_id]['qty'] += qty
        else:
            self.inventory[item_id] = {'name': item_name, 'qty': qty}
        return True

    def remove_item(self, item_id, qty=1):
        """인벤토리에서 아이템을 제거합니다."""
        if item_id in self.inventory and self.inventory[item_id]['qty'] >= qty:
            self.inventory[item_id]['qty'] -= qty
            if self.inventory[item_id]['qty'] <= 0:
                del self.inventory[item_id]
            return True
        return False 

    def get_item_quantity(self, item_id):
        """인벤토리에서 특정 아이템의 개수를 반환합니다."""
        return self.inventory.get(item_id, {}).get('qty', 0)

    def take_damage(self, damage):
        """플레이어가 데미지를 입습니다."""
        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

    def restore_hp(self, amount):
        """플레이어의 HP를 회복시킵니다."""
        self.hp = min(self.hp + amount, self.max_hp)

    def restore_mp(self, amount):
        """플레이어의 MP를 회복시킵니다."""
        self.mp = min(self.mp + amount, self.max_mp)

    def gain_exp(self, amount):
        """경험치를 얻고 레벨업을 확인합니다."""
        self.exp += amount
        leveled_up = False
        message = ""
        while self.exp >= self.exp_to_next_level:
            leveled_up = True
            self.exp -= self.exp_to_next_level
            self.level_up()
            message += f"레벨업! {self.level - 1} -> {self.level}. "
        return leveled_up, message.strip()

    def level_up(self):
        """플레이어의 레벨을 올리고 스탯을 강화합니다."""
        self.level += 1
        self.max_hp += 10
        self.max_mp += 5
        self.base_att += 2
        self.base_def += 1
        self.hp = self.max_hp  # 레벨업 시 체력과 마력을 모두 회복
        self.mp = self.max_mp
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5) # 다음 필요 경험치 증가
        
    def to_dict(self):
        """플레이어 데이터를 딕셔너리 형태로 변환하여 반환합니다."""
        return {
            'name': self.name,
            'x': self.x, 
            'y': self.y, 
            'hp': self.hp,
            'max_hp': self.max_hp, 
            'mp': self.mp,
            'max_mp': self.max_mp,
            'level': self.level,
            'exp': self.exp,
            'exp_to_next_level': self.exp_to_next_level,
            'base_att': self.base_att,
            'base_def': self.base_def,
            'att_bonus': self.att_bonus,
            'def_bonus': self.def_bonus,
            'critical_chance': self.critical_chance,
            'critical_damage_multiplier': self.critical_damage_multiplier,
            'inventory': self.inventory, 
            'skills': self.skills, 
            'dungeon_level': self.dungeon_level 
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 Player 객체를 생성하여 반환합니다."""
        player = cls(
            name=data.get('name', '용사'),
            hp=data.get('hp', 100),
            mp=data.get('mp', 50),
            x=data.get('x', 0),
            y=data.get('y', 0),
            level=data.get('level', 1),
            dungeon_level=tuple(data.get('dungeon_level', (1, 0)))
        )
        player.max_hp = data.get('max_hp', player.hp)
        player.max_mp = data.get('max_mp', player.mp)
        player.exp = data.get('exp', 0)
        player.exp_to_next_level = data.get('exp_to_next_level', 100)
        player.base_att = data.get('base_att', 10)
        player.base_def = data.get('base_def', 5)
        player.att_bonus = data.get('att_bonus', 0)
        player.def_bonus = data.get('def_bonus', 0)
        player.critical_chance = data.get('critical_chance', 0.05)
        player.critical_damage_multiplier = data.get('critical_damage_multiplier', 1.5)
        player.inventory = data.get('inventory', {})
        player.skills = data.get('skills', {}) 
        
        return player