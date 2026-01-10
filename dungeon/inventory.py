# inventory.py
from items import Item, Equipment, Consumable

class Inventory:
    def __init__(self):
        # 각 카테고리별 아이템을 저장하는 딕셔너리. key: item_id, value: {'item': ItemObject, 'qty': int}
        self.items = {} 
        self.equipment_items = {}
        self.scrolls = {}
        self.skill_books = {}

        # 장착된 장비를 저장하는 딕셔너리. key: slot, value: EquipmentObject
        self.equipped = {
            "투구": None, "갑옷": None, "무기": None,
            "방패": None, "장갑": None, "신발": None,
            "목걸이": None, "반지1": None, "반지2": None
        }

    def add_item(self, item_to_add, qty=1):
        """인벤토리에 아이템을 추가합니다. Item 객체를 직접 받습니다."""
        if not isinstance(item_to_add, Item):
            return False

        # 아이템 타입에 따라 적절한 인벤토리 섹션 선택
        target_inventory = self._get_inventory_section(item_to_add)
        
        if item_to_add.id in target_inventory:
            target_inventory[item_to_add.id]['qty'] += qty
        else:
            target_inventory[item_to_add.id] = {'item': item_to_add, 'qty': qty}
        return True

    def remove_item(self, item_to_remove, qty=1):
        """인벤토리에서 아이템을 제거합니다."""
        target_inventory = self._get_inventory_section(item_to_remove)

        if item_to_remove.id in target_inventory:
            if target_inventory[item_to_remove.id]['qty'] >= qty:
                target_inventory[item_to_remove.id]['qty'] -= qty
                if target_inventory[item_to_remove.id]['qty'] <= 0:
                    del target_inventory[item_to_remove.id]
                return True
        return False

    def _get_inventory_section(self, item):
        """아이템 종류에 따라 적절한 인벤토리 딕셔너리를 반환합니다."""
        if item.item_type == 'EQUIP':
            return self.equipment_items
        elif item.item_type == 'SKILLBOOK':
            return self.skill_books
        elif item.item_type == 'SCROLL':
            return self.scrolls
        else: # CONSUMABLE 및 기타
            return self.items

    def get_item_quantity(self, item_id):
        """인벤토리의 모든 섹션을 확인하여 특정 아이템의 개수를 반환합니다."""
        for section in [self.items, self.equipment_items, self.scrolls, self.skill_books]:
            if item_id in section:
                return section[item_id]['qty']
        return 0

    def find_item_by_id(self, item_id):
        """인벤토리의 모든 섹션을 검색하여 ID가 일치하는 Item 객체를 반환합니다."""
        for section in [self.items, self.equipment_items, self.scrolls, self.skill_books]:
            if item_id in section:
                return section[item_id]['item']
        return None

    def get_all_items(self):
        """모든 카테고리의 아이템 리스트를 반환합니다."""
        all_items_list = []
        for section in [self.items, self.equipment_items, self.scrolls, self.skill_books]:
            for item_id in section:
                all_items_list.append(section[item_id])
        return all_items_list

    def get_items_by_tab(self, tab):
        """탭 이름에 따라 해당 카테고리의 아이템 리스트를 반환합니다."""
        if tab == 'all':
            all_items_list = []
            all_items_list.extend(self.items.values())
            all_items_list.extend(self.equipment_items.values())
            all_items_list.extend(self.scrolls.values())
            all_items_list.extend(self.skill_books.values())
            return sorted(all_items_list, key=lambda x: x['item'].name) # 이름순으로 정렬
        elif tab == 'item':
            return sorted(list(self.items.values()), key=lambda x: x['item'].name)
        elif tab == 'equipment':
            return sorted(list(self.equipment_items.values()), key=lambda x: x['item'].name)
        elif tab == 'scroll':
            return sorted(list(self.scrolls.values()), key=lambda x: x['item'].name)
        elif tab == 'skill_book':
            return sorted(list(self.skill_books.values()), key=lambda x: x['item'].name)
        return []

    def equip(self, equipment_item):
        """장비를 장착합니다."""
        if not isinstance(equipment_item, Equipment):
            return None, "장비 아이템이 아닙니다."

        # 영문 slot을 한글로 변환
        slot_map = {
            "HELMET": "투구", "ARMOR": "갑옷", "WEAPON": "무기",
            "SHIELD": "방패", "GLOVES": "장갑", "BOOTS": "신발",
            "NECKLACE": "목걸이", "RING": "반지" # 반지는 RING1, RING2 처리 필요
        }
        
        # 기본 slot 변환
        slot_kor = slot_map.get(equipment_item.slot.upper())

        # RING의 경우 RING1, RING2 순차적으로 장착
        if equipment_item.slot.upper() == "RING":
            if self.equipped.get("반지1") is None:
                slot_kor = "반지1"
            elif self.equipped.get("반지2") is None:
                slot_kor = "반지2"
            else:
                # 반지가 모두 찼을 경우, 첫 번째 반지와 교체
                slot_kor = "반지1"

        if not slot_kor or slot_kor not in self.equipped:
            return None, f"알 수 없는 장비 부위입니다: {equipment_item.slot}"

        # 이미 장착된 아이템 해제
        unequipped_item = None
        if self.equipped[slot_kor]:
            unequipped_item = self.unequip(slot_kor)

        self.equipped[slot_kor] = equipment_item
        self.remove_item(equipment_item) # 인벤토리에서 장착한 아이템 제거
        
        return unequipped_item, f"{equipment_item.name}을(를) 장착했습니다."

    def drop_item(self, item_to_drop, qty=1):
        """인벤토리에서 아이템을 버립니다. 성공 시 True, 실패 시 False를 반환합니다."""
        return self.remove_item(item_to_drop, qty)

    def unequip(self, slot):
        """해당 슬롯의 장비를 해제합니다."""
        if slot in self.equipped and self.equipped[slot]:
            item_to_unequip = self.equipped[slot]
            self.equipped[slot] = None
            self.add_item(item_to_unequip) # 해제한 아이템을 인벤토리로 복귀
            return item_to_unequip
        return None

    def to_dict(self):
        """인벤토리 상태를 저장 가능한 딕셔너리로 변환합니다."""
        return {
            'items': {item_id: {'item': data['item'].to_dict(), 'qty': data['qty']} for item_id, data in self.items.items()},
            'equipment_items': {item_id: {'item': data['item'].to_dict(), 'qty': data['qty']} for item_id, data in self.equipment_items.items()},
            'equipped': {slot: item.to_dict() if item else None for slot, item in self.equipped.items()}
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리로부터 인벤토리 상태를 복원합니다."""
        inventory = cls()
        
        # 일반 아이템 복원
        items_data = data.get('items', {})
        for item_id, item_info in items_data.items():
            inventory.items[item_id] = {
                'item': Item.from_dict(item_info['item']),
                'qty': item_info['qty']
            }
            
        # 장비 아이템 복원
        equipment_data = data.get('equipment_items', {})
        for item_id, item_info in equipment_data.items():
            inventory.equipment_items[item_id] = {
                'item': Item.from_dict(item_info['item']),
                'qty': item_info['qty']
            }

        # 장착된 장비 복원
        equipped_data = data.get('equipped', {})
        for slot, item_data in equipped_data.items():
            if item_data:
                inventory.equipped[slot] = Item.from_dict(item_data)
        
        return inventory
