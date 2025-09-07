# player.py
import data_manager
from inventory import Inventory

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
        self.max_stamina = 100.0
        self.stamina = 100.0
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
        self.inventory = Inventory()
        self.skills = {}
        self.item_quick_slots = {i: None for i in range(1, 6)}
        self.skill_quick_slots = {i: None for i in range(6, 11)}
        # self.equipment는 이제 self.inventory.equipped로 대체됩니다.
        self.is_provoked = False

    @property
    def equipment(self):
        """인벤토리 객체의 장착 상태를 직접 참조합니다."""
        return self.inventory.equipped

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
        return self.hp > 0 and self.stamina > 0

    def add_item(self, item_to_add, qty=1):
        """인벤토리에 아이템을 추가합니다."""
        return self.inventory.add_item(item_to_add, qty)

    def remove_item(self, item_to_remove, qty=1):
        """인벤토리에서 아이템을 제거합니다."""
        return self.inventory.remove_item(item_to_remove, qty)

    def get_item_quantity(self, item_id):
        """인벤토리에서 특정 아이템의 개수를 반환합니다."""
        return self.inventory.get_item_quantity(item_id)

    def equip(self, equipment_item):
        """아이템을 장착합니다."""
        unequipped_item, message = self.inventory.equip(equipment_item)
        if unequipped_item is not None or "장착했습니다" in message:
             self._update_stats_from_equipment()
        return message

    def unequip(self, slot):
        """지정된 슬롯의 아이템을 해제합니다."""
        item_to_unequip = self.inventory.unequip(slot)
        if item_to_unequip:
            self._update_stats_from_equipment()
            return f"{item_to_unequip.name}을(를) 해제했습니다."
        return "해당 부위에 장착한 아이템이 없습니다."

    def drop_item(self, item_to_drop, qty=1):
        """인벤토리에서 아이템을 버립니다."""
        # Inventory.remove_item은 성공 시 True를 반환
        if self.inventory.remove_item(item_to_drop, qty):
            return f"{item_to_drop.name}을(를) 버렸습니다."
        return "아이템을 버리는 데 실패했습니다."

    def assign_item_to_quickslot(self, item, slot):
        """아이템 또는 스크롤을 퀵슬롯 1-5번에 등록합니다."""
        if not (1 <= slot <= 5):
            return "아이템 퀵슬롯은 1-5번만 가능합니다."
        self.item_quick_slots[slot] = item.id
        return f"퀵슬롯 {slot}번에 {item.name}을(를) 등록했습니다."

    def assign_skill_to_quickslot(self, skill_book, slot):
        """스킬북을 퀵슬롯 6-0번에 등록합니다."""
        slot_key = slot if slot != 0 else 10 # 0번 키는 10번 인덱스로 처리
        if not (6 <= slot_key <= 10):
            return "스킬 퀵슬롯은 6-0번만 가능합니다."
        self.skill_quick_slots[slot_key] = skill_book.id
        return f"퀵슬롯 {slot}번에 {skill_book.name}을(를) 등록했습니다."

    def use_item(self, item):
        """소모품 아이템을 사용합니다."""
        if not hasattr(item, 'effect_type'):
            return False, f"{item.name}은(는) 사용할 수 없는 아이템입니다."

        if item.effect_type == 'HP_RECOVER':
            self.restore_hp(item.value)
            self.remove_item(item, 1)
            return True, f"{item.name}을(를) 사용하여 HP를 {item.value}만큼 회복했습니다."
        elif item.effect_type == 'MP_RECOVER':
            self.restore_mp(item.value)
            self.remove_item(item, 1)
            return True, f"{item.name}을(를) 사용하여 MP를 {item.value}만큼 회복했습니다."
        
        return False, f"{item.name}은(는) 아직 사용할 수 없습니다."

    def _update_stats_from_equipment(self):
        """장비에 따라 스탯 보너스를 다시 계산합니다."""
        self.att_bonus = 0
        self.def_bonus = 0
        for item in self.equipment.values():
            if item:
                # 이제 item은 item_id가 아닌 Item 객체입니다.
                if item.effect_type == 'ATTACK':
                    self.att_bonus += item.value
                elif item.effect_type == 'DEFENSE':
                    self.def_bonus += item.value

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
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        
    def to_dict(self):
        """플레이어 데이터를 딕셔너리 형태로 변환하여 반환합니다."""
        return {
            'name': self.name, 'x': self.x, 'y': self.y, 'hp': self.hp,
            'max_hp': self.max_hp, 'mp': self.mp, 'max_mp': self.max_mp,
            'stamina': self.stamina, 'max_stamina': self.max_stamina,
            'level': self.level, 'exp': self.exp, 'exp_to_next_level': self.exp_to_next_level,
            'base_att': self.base_att, 'base_def': self.base_def,
            'att_bonus': self.att_bonus, 'def_bonus': self.def_bonus,
            'critical_chance': self.critical_chance, 'critical_damage_multiplier': self.critical_damage_multiplier,
            'inventory': self.inventory.to_dict(),  # Inventory 객체의 to_dict 호출
            'skills': self.skills, 'dungeon_level': self.dungeon_level,
            'item_quick_slots': self.item_quick_slots, 'skill_quick_slots': self.skill_quick_slots,
            # 'equipment'는 inventory에 포함되므로 중복 저장할 필요 없음
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 Player 객체를 생성하여 반환합니다."""
        player = cls(
            name=data.get('name', '용사'), hp=data.get('hp', 100), mp=data.get('mp', 50),
            x=data.get('x', 0), y=data.get('y', 0), level=data.get('level', 1),
            dungeon_level=tuple(data.get('dungeon_level', (1, 0)))
        )
        player.max_hp = data.get('max_hp', player.hp)
        player.max_mp = data.get('max_mp', player.mp)
        player.stamina = float(data.get('stamina', 100.0))
        player.max_stamina = float(data.get('max_stamina', 100.0))
        player.exp = data.get('exp', 0)
        player.exp_to_next_level = data.get('exp_to_next_level', 100)
        player.base_att = data.get('base_att', 10)
        player.base_def = data.get('base_def', 5)
        player.att_bonus = data.get('att_bonus', 0)
        player.def_bonus = data.get('def_bonus', 0)
        player.critical_chance = data.get('critical_chance', 0.05)
        player.critical_damage_multiplier = data.get('critical_damage_multiplier', 1.5)
        
        # Inventory 객체 복원
        inventory_data = data.get('inventory')
        if inventory_data:
            player.inventory = Inventory.from_dict(inventory_data)
        else:
            player.inventory = Inventory()

        player.skills = data.get('skills', {})
        player.item_quick_slots = data.get('item_quick_slots', {i: None for i in range(1, 6)})
        player.skill_quick_slots = data.get('skill_quick_slots', {i: None for i in range(6, 11)})
        
        # 로드 후 스탯 재계산
        player._update_stats_from_equipment()
        
        return player
