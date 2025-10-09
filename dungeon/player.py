# player.py
from . import data_manager
from .inventory import Inventory

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
        
        # 중복 등록 방지
        if item.id in self.item_quick_slots.values():
            return "이미 다른 퀵슬롯에 등록된 아이템입니다."

        self.item_quick_slots[slot] = item.id
        return f"퀵슬롯 {slot}번에 {item.name}을(를) 등록했습니다."

    def assign_skill_to_quickslot(self, skill_book, slot):
        """배운 스킬을 퀵슬롯 6-0번에 등록합니다."""
        slot_key = slot if slot != 0 else 10 # 0번 키는 10번 인덱스로 처리
        if not (6 <= slot_key <= 10):
            return "스킬 퀵슬롯은 6-0번만 가능합니다."
        
        # 스킬을 배웠는지 먼저 확인
        if skill_book.id not in self.skills:
            return f"'{skill_book.name}' 스킬을 아직 배우지 않았습니다. 먼저 'u' 키로 사용하세요."
            
        self.skill_quick_slots[slot_key] = skill_book.id
        return f"퀵슬롯 {slot}번에 {skill_book.name}을(를) 등록했습니다."

    def assign_to_empty_quickslot(self, item):
        """소모품을 비어있는 퀵슬롯 1-5번에 등록합니다."""
        # 중복 등록 방지
        if item.id in self.item_quick_slots.values():
            return "이미 다른 퀵슬롯에 등록된 아이템입니다."

        for slot in range(1, 6):
            if self.item_quick_slots.get(slot) is None:
                self.item_quick_slots[slot] = item.id
                return f"퀵슬롯 {slot}번에 {item.name}을(를) 등록했습니다."
        return "모든 퀵슬롯이 가득 찼습니다."

    def assign_to_empty_skill_quickslot(self, skill_book):
        """배운 스킬을 비어있는 스킬 퀵슬롯 6-0번에 등록합니다."""
        # 스킬을 배웠는지 먼저 확인
        if skill_book.id not in self.skills:
            return f"'{skill_book.name}' 스킬을 아직 배우지 않았습니다. 먼저 'u' 키로 사용하세요."

        # 0번 키는 10번 인덱스로 사용
        for slot in list(range(6, 11)):
            if self.skill_quick_slots.get(slot) is None:
                self.skill_quick_slots[slot] = skill_book.id
                
                display_slot = 0 if slot == 10 else slot
                return f"퀵슬롯 {display_slot}번에 {skill_book.name}을(를) 등록했습니다."
        return "모든 스킬 퀵슬롯이 가득 찼습니다."

    def acquire_skill_from_book(self, skill_book):
        """스킬북을 획득하여 즉시 스킬을 배우거나 레벨업합니다."""
        skill_id = skill_book.id
        
        # 스킬북의 요구 레벨 확인
        if self.level < skill_book.req_level:
            # 레벨이 부족하면 스킬북을 얻을 수 없음 (메시지 반환 후 아이템은 사라짐)
            return f"레벨 {skill_book.req_level}이 되지 않아 '{skill_book.name}' 스킬북을 읽을 수 없습니다."

        if skill_id in self.skills:
            # 스킬 레벨업
            self.skills[skill_id]['level'] += 1
            new_level = self.skills[skill_id]['level']
            return f"'{skill_book.name}' 스킬의 레벨이 올랐습니다! (Lv.{new_level - 1} -> Lv.{new_level})"
        else:
            # 새로운 스킬 배우기
            self.skills[skill_id] = {'level': 1, 'exp': 0}
            return f"새로운 스킬 '{skill_book.name}'을(를) 배웠습니다!"

    def use_item(self, item):
        """소모품 아이템을 사용하고, 개수가 0이 되면 퀵슬롯을 비웁니다."""
        if not hasattr(item, 'effect_type') or item.item_type != 'CONSUMABLE':
            return False, f"{item.name}은(는) 사용할 수 없는 아이템입니다."

        effect_applied = False
        message = ""

        if item.effect_type == 'HP_RECOVER':
            self.restore_hp(item.value)
            message = f"{item.name}을(를) 사용하여 HP를 {item.value}만큼 회복했습니다."
            effect_applied = True
        elif item.effect_type == 'MP_RECOVER':
            self.restore_mp(item.value)
            message = f"{item.name}을(를) 사용하여 MP를 {item.value}만큼 회복했습니다."
            effect_applied = True
        elif item.effect_type == 'STAMINA_RECOVER':
            self.restore_stamina(item.value)
            message = f"{item.name}을(를) 사용하여 스태미나를 {item.value}만큼 회복했습니다."
            effect_applied = True
        
        if effect_applied:
            self.remove_item(item, 1)
            # 아이템을 사용한 후 개수가 0이 되었는지 확인
            if self.get_item_quantity(item.id) <= 0:
                # 모든 퀵슬롯을 확인하여 해당 아이템 ID를 가진 슬롯을 비움
                for slot, item_id in self.item_quick_slots.items():
                    if item_id == item.id:
                        self.item_quick_slots[slot] = None
            return True, message
        
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

    def restore_stamina(self, amount):
        """플레이어의 스태미나를 회복시킵니다."""
        self.stamina = min(self.stamina + amount, self.max_stamina)

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
