# items.py

class Item:
    def __init__(self, item_id, name, item_type, description=""):
        self.id = item_id
        self.name = name
        self.item_type = item_type
        self.description = description

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'item_type': self.item_type,
            'description': self.description,
            'class': self.__class__.__name__
        }

    @classmethod
    def from_dict(cls, data):
        class_name = data.pop('class', 'Item')
        
        if class_name == 'Equipment':
            return Equipment.from_dict(data)
        elif class_name == 'Consumable':
            return Consumable.from_dict(data)
        elif class_name == 'SkillBook':
            return SkillBook.from_dict(data)
        
        # 기본 Item 객체 또는 다른 서브클래스 처리
        item = cls(
            item_id=data['id'],
            name=data['name'],
            item_type=data['item_type'],
            description=data.get('description', "")
        )
        return item

    @classmethod
    def from_definition(cls, definition):
        """ItemDefinition으로부터 Item 객체를 생성합니다."""
        # ItemDefinition의 속성을 기반으로 적절한 Item 서브클래스 인스턴스 생성
        # 이 예시에서는 모든 타입을 기본 Item으로 생성하지만,
        # 실제로는 definition.item_type에 따라 분기해야 합니다.
        # 지금은 data_manager.ItemDefinition의 구체적인 속성을 알 수 없으므로 일반적인 형태로 작성합니다.
        
        # 가정: definition 객체는 id, name, description 등의 속성을 가짐
        # 가정: Equipment의 경우 equip_slot, effect_type, value 등의 속성을 가짐
        
        item_type = getattr(definition, 'item_type', 'item').upper() # 기본값 설정 및 대문자 변환
        
        if item_type == 'EQUIP':
            return Equipment(
                item_id=definition.id,
                name=definition.name,
                description=getattr(definition, 'description', ""),
                item_type=item_type,
                value=getattr(definition, 'value', 0),
                req_level=getattr(definition, 'req_level', 0),
                effect_type=getattr(definition, 'effect_type', 'NONE'),
                slot=getattr(definition, 'equip_slot', 'NONE')
            )
        elif item_type == 'CONSUMABLE':
             return Consumable(
                item_id=definition.id,
                name=definition.name,
                description=getattr(definition, 'description', ""),
                item_type=item_type,
                value=getattr(definition, 'value', 0),
                req_level=getattr(definition, 'req_level', 0),
                effect_type=getattr(definition, 'effect_type', 'NONE')
            )
        elif item_type == 'SKILLBOOK':
            return SkillBook(
                item_id=definition.id,
                name=definition.name,
                description=getattr(definition, 'description', ""),
                item_type=item_type,
                value=getattr(definition, 'value', 0),
                req_level=getattr(definition, 'req_level', 0),
                # items.txt에서 effect_type 필드를 skill_id로 사용
                skill_id=getattr(definition, 'effect_type', 'NONE')
            )
        # TODO: 다른 아이템 타입에 대한 처리 추가 (ETC 등)
        else: # ETC 등 다른 모든 타입
            return cls(
                item_id=definition.id,
                name=definition.name,
                description=getattr(definition, 'description', ""),
                item_type=item_type
            )

class Equipment(Item):
    """장비 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, req_level, effect_type, slot):
        super().__init__(item_id, name, item_type, description)
        self.value = value
        self.req_level = req_level
        self.effect_type = effect_type
        self.slot = slot

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'value': self.value,
            'req_level': self.req_level,
            'effect_type': self.effect_type,
            'slot': self.slot
        })
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            req_level=data.get('req_level'),
            effect_type=data.get('effect_type'),
            slot=data.get('slot')
        )

class Consumable(Item):
    """소모성 아이템 클래스"""
    def __init__(self, item_id, name, description, item_type, value, req_level, effect_type):
        super().__init__(item_id, name, item_type, description)
        self.value = value
        self.req_level = req_level
        self.effect_type = effect_type
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'value': self.value,
            'req_level': self.req_level,
            'effect_type': self.effect_type
        })
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            req_level=data.get('req_level'),
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
    def __init__(self, item_id, name, description, item_type, value, req_level, skill_id):
        super().__init__(item_id, name, item_type, description)
        self.value = value
        self.req_level = req_level
        self.skill_id = skill_id

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'value': self.value,
            'req_level': self.req_level,
            'skill_id': self.skill_id
        })
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_id=data.get('id'),
            name=data.get('name'),
            description=data.get('description'),
            item_type=data.get('item_type'),
            value=data.get('value'),
            req_level=data.get('req_level'),
            skill_id=data.get('skill_id')
        )

