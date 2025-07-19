# player.py

class Player:
    def __init__(self, name, hp, mp):
        self.name = name
        self.hp = hp
        self.max_hp = hp 
        self.mp = mp
        self.max_mp = mp 
        self.x = 0 
        self.y = 0 
        self.skills = {
            'Fireball': {'level': 1, 'mp_cost': 10, 'base_damage': 15},
            'Heal': {'level': 1, 'mp_cost': 15, 'base_heal': 20}
        }
        self.inventory = [] 
        self.dungeon_level = (0, 0) # (floor, room) 튜플로 변경 

    def is_alive(self):
        """플레이어가 살아있는지 여부를 반환합니다."""
        return self.hp > 0

    def add_item(self, item_id, qty=1):
        """인벤토리에 아이템을 추가합니다. 이미 있는 아이템은 수량을 증가시킵니다."""
        for item_slot in self.inventory:
            if item_slot['id'] == item_id:
                item_slot['qty'] += qty
                return True
        self.inventory.append({'id': item_id, 'qty': qty})
        return True

    def remove_item(self, item_id, qty=1):
        """인벤토리에서 아이템을 제거합니다. 수량이 부족하면 False를 반환합니다."""
        for item_slot in self.inventory:
            if item_slot['id'] == item_id:
                if item_slot['qty'] >= qty:
                    item_slot['qty'] -= qty
                    if item_slot['qty'] == 0:
                        self.inventory.remove(item_slot)
                    return True
                else:
                    return False 
        return False 

    def get_item_quantity(self, item_id):
        """인벤토리에서 특정 아이템의 개수를 반환합니다."""
        for item_slot in self.inventory:
            if item_slot['id'] == item_id:
                return item_slot['qty']
        return 0

    def restore_hp(self, amount):
        """플레이어의 HP를 회복시킵니다."""
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def restore_mp(self, amount):
        """플레이어의 MP를 회복시킵니다."""
        self.mp += amount
        if self.mp > self.max_mp:
            self.mp = self.max_mp
        
    def to_dict(self):
        """플레이어 데이터를 딕셔너리 형태로 변환하여 반환합니다 (저장용)."""
        return {
            'name': self.name,
            'hp': self.hp,
            'max_hp': self.max_hp, 
            'mp': self.mp,
            'max_mp': self.max_mp,
            'x': self.x, 
            'y': self.y, 
            'skills': self.skills, 
            'inventory': self.inventory, 
            'dungeon_level': self.dungeon_level 
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 Player 객체를 생성하여 반환합니다 (로드용)."""
        # data.get()을 사용하여 'max_hp', 'max_mp'가 없을 경우 'hp', 'mp' 값으로 대체
        max_hp = data.get('max_hp', data.get('hp', 100)) # 'hp'도 없을 경우 기본값 100
        max_mp = data.get('max_mp', data.get('mp', 50))  # 'mp'도 없을 경우 기본값 50
        
        # Player 객체 생성 시 'hp'와 'mp'를 전달
        player = cls(data['name'], data.get('hp', 100), data.get('mp', 50)) 
        
        # 저장된 x, y 데이터를 사용하여 플레이어 위치 설정
        player.x = data.get('x', 0) 
        player.y = data.get('y', 0) 
        
        player.max_hp = max_hp
        player.max_mp = max_mp
        
        # 'skills'와 'inventory'는 기본값이 빈 리스트이므로 get() 사용
        player.skills = data.get('skills', []) 
        player.inventory = data.get('inventory', []) 
        player.dungeon_level = tuple(data.get('dungeon_level', (0, 0))) # 튜플로 로드 
        
        return player

