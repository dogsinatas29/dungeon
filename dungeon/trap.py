# trap.py
from . import data_manager

class Trap:
    def __init__(self, x, y, trap_id):
        self.x = x
        self.y = y
        self.trap_id = trap_id
        
        definition = data_manager.get_trap_definition(trap_id)
        if not definition:
            raise ValueError(f"Trap ID '{trap_id}'에 해당하는 함정 정의를 찾을 수 없습니다.")
            
        self.name = definition.name
        self.symbol = definition.symbol
        self.color = definition.color
        self.trigger_type = definition.trigger_type
        self.effect_type = definition.effect_type
        self.damage = definition.damage
        self.radius = definition.radius
        
        self.triggered = False
        self.visible = False # 기본적으로 보이지 않음
        self.entity_id = None # ECS 엔티티 ID 추가

    def trigger(self):
        """함정을 발동시킵니다."""
        if not self.triggered:
            self.triggered = True
            self.visible = True # 발동되면 보이도록 설정
            return True
        return False

    def get_splash_effect_positions(self):
        """함정의 스플래시 효과가 적용될 위치들을 반환합니다."""
        positions = []
        for dy in range(-self.radius, self.radius + 1):
            for dx in range(-self.radius, self.radius + 1):
                # 원형 반경을 위한 간단한 근사치
                if dx*dx + dy*dy <= self.radius*self.radius:
                    positions.append((self.x + dx, self.y + dy))
        return positions

    def to_dict(self):
        return {
            "x": self.x, "y": self.y, "trap_id": self.trap_id,
            "name": self.name, "symbol": self.symbol, "color": self.color,
            "trigger_type": self.trigger_type, "effect_type": self.effect_type,
            "damage": self.damage, "radius": self.radius,
            "triggered": self.triggered, "visible": self.visible,
            "entity_id": self.entity_id
        }

    @classmethod
    def from_dict(cls, data):
        trap = cls(
            x=data['x'], y=data['y'],
            trap_id=data['trap_id']
        )
        trap.name = data.get('name', trap.name)
        trap.symbol = data.get('symbol', trap.symbol)
        trap.color = data.get('color', trap.color)
        trap.trigger_type = data.get('trigger_type', trap.trigger_type)
        trap.effect_type = data.get('effect_type', trap.effect_type)
        trap.damage = data.get('damage', trap.damage)
        trap.radius = data.get('radius', trap.radius)
        trap.triggered = data.get('triggered', trap.triggered)
        trap.visible = data.get('visible', trap.visible)
        trap.entity_id = data.get('entity_id', None)
        return trap
