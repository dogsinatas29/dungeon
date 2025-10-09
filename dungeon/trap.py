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

    def trigger(self):
        """함정을 발동시킵니다."""
        if not self.triggered:
            self.triggered = True
            self.visible = True # 발동되면 보이도록 설정
            return True
        return False

    def to_dict(self):
        """함정 데이터를 딕셔너리로 변환합니다."""
        return {
            'x': self.x,
            'y': self.y,
            'trap_id': self.trap_id,
            'triggered': self.triggered,
            'visible': self.visible
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리로부터 Trap 객체를 생성합니다."""
        trap = cls(data['x'], data['y'], data['trap_id'])
        trap.triggered = data.get('triggered', False)
        trap.visible = data.get('visible', False)
        return trap
