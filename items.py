# items.py

class Item:
    def __init__(self, item_id, name, description, item_type, value, required_level):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.item_type = item_type
        self.value = value
        self.required_level = required_level

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type,
            "value": self.value,
            "required_level": self.required_level
        }

    @classmethod
    def from_dict(cls, data):
        # 아이템 타입에 따라 적절한 클래스의 인스턴스를 생성
        item_type = data.get('item_type')
        if item_type == 'equipment':
            return Equipment.from_dict(data)
        elif item_type == 'consumable':
            return Consumable.from_dict(data)
        elif item_type == 'key':
            return Key.from_dict(data)
        elif item_type == 'skill_book':
            return SkillBook.from_dict(data)
        return cls(
            item_id=data.get('item_id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            required_level=data.get('required_level')
        )

    @classmethod
    def from_definition(cls, definition):
        """ItemDefinition으로부터 Item 객체를 생성합니다."""
        # ItemDefinition의 속성을 기반으로 적절한 Item 서브클래스 인스턴스 생성
        # 이 예시에서는 모든 타입을 기본 Item으로 생성하지만,
        # 실제로는 definition.item_type에 따라 분기해야 합니다.
        # 지금은 data_manager.ItemDefinition의 구체적인 속성을 알 수 없으므로 일반적인 형태로 작성합니다.
        
        # 가정: definition 객체는 id, name, description 등의 속성을 가짐
        # 가정: Equipment의 경우 equip_slot, effect_type, value 등의 속성을 가짐
        
        item_type = getattr(definition, 'item_type', 'item') # 기본값 설정
        
        if item_type == 'EQUIP':
            return Equipment(
                item_id=definition.id,
                name=definition.name,
                description=definition.description,
                value=definition.value,
                required_level=definition.req_level,
                effect_type=definition.effect_type,
                slot=definition.equip_slot # Equipment에 slot 속성 추가 필요
            )
        elif item_type == 'CONSUMABLE':
             return Consumable(
                item_id=definition.id,
                name=definition.name,
                description=definition.description,
                value=definition.value,
                required_level=definition.req_level,
                effect_type=definition.effect_type
            )
        # TODO: 다른 아이템 타입에 대한 처리 추가 (SKILL_BOOK 등)
        else:
            return cls(
                item_id=definition.id,
                name=definition.name,
                description=definition.description,
                item_type=item_type,
                value=definition.value,
                required_level=definition.req_level
            )

class Equipment(Item):
    """장비 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, required_level, effect_type, slot):
        super().__init__(item_id, name, description, 'equipment', value, required_level)
        self.effect_type = effect_type
        self.slot = slot

    def to_dict(self):
        data = super().to_dict()
        data['effect_type'] = self.effect_type
        data['slot'] = self.slot
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('item_id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            required_level=data.get('required_level'),
            effect_type=data.get('effect_type'),
            slot=data.get('slot')
        )

class Consumable(Item):
    """소모성 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, required_level, effect_type):
        super().__init__(item_id, name, description, 'consumable', value, required_level)
        self.effect_type = effect_type
    
    def to_dict(self):
        data = super().to_dict()
        data['effect_type'] = self.effect_type
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('item_id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            required_level=data.get('required_level'),
            effect_type=data.get('effect_type')
        )

class Key(Item):
    """열쇠 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, required_level):
        super().__init__(item_id, name, description, 'key', value, required_level)
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('item_id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            required_level=data.get('required_level')
        )

class SkillBook(Item):
    """스킬북 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, required_level, skill_id):
        super().__init__(item_id, name, description, 'skill_book', value, required_level)
        self.skill_id = skill_id

    def to_dict(self):
        data = super().to_dict()
        data['skill_id'] = self.skill_id
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('item_id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            required_level=data.get('required_level'),
            skill_id=data.get('skill_id')
        )

