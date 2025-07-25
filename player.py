# player.py

class Player:
    def __init__(self, name, hp, mp, level=1):
        self.name = name
        self.hp = hp
        self.max_hp = hp 
        self.mp = mp
        self.max_mp = mp 
        self.level = level
        self.exp = 0 # 경험치 추가
        self.exp_to_next_level = 100 # 다음 레벨업에 필요한 경험치 추가
        self.attack = 10  # 공격력 추가
        self.defense = 5   # 방어력 추가
        self.x = 0 
        self.y = 0 
        self.skills = {
            'Fireball': {'level': 1, 'mp_cost': 10, 'base_damage': 15},
            'Heal': {'level': 1, 'mp_cost': 15, 'base_heal': 20}
        }
        self.inventory = {} 
        self.dungeon_level = (1, 0)

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
        
    def to_dict(self):
        """플레이어 데이터를 딕셔너리 형태로 ��환하여 반환합니다."""
        return {
            'name': self.name,
            'hp': self.hp,
            'max_hp': self.max_hp, 
            'mp': self.mp,
            'max_mp': self.max_mp,
            'level': self.level,
            'exp': self.exp, # 경험치 저장
            'exp_to_next_level': self.exp_to_next_level, # 다음 레벨업 경험치 저장
            'attack': self.attack,
            'defense': self.defense,
            'x': self.x, 
            'y': self.y, 
            'skills': self.skills, 
            'inventory': self.inventory, 
            'dungeon_level': self.dungeon_level 
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 Player 객체를 생성하여 반환합니다."""
        player = cls(
            data.get('name', '용사'),
            data.get('hp', 100),
            data.get('mp', 50),
            data.get('level', 1)
        )
        player.max_hp = data.get('max_hp', player.hp)
        player.max_mp = data.get('max_mp', player.mp)
        player.exp = data.get('exp', 0) # 경험치 로드
        player.exp_to_next_level = data.get('exp_to_next_level', 100) # 다음 레벨업 경험치 로드
        player.attack = data.get('attack', 10)
        player.defense = data.get('defense', 5)
        player.x = data.get('x', 0) 
        player.y = data.get('y', 0) 
        player.skills = data.get('skills', {}) 
        player.inventory = data.get('inventory', {})
        player.dungeon_level = tuple(data.get('dungeon_level', (1, 0)))
        
        return player