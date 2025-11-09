# monster.py
from . import data_manager # data_manager 모듈 임포트

class Monster:
    def __init__(self, ui_instance=None, monster_id=None, name=None, symbol=None, color=None, hp=None, attack=None, defense=None, level=None, exp_given=None):
        self.ui_instance = ui_instance
        
        if monster_id:
            monster_def = data_manager.get_monster_definition(monster_id)
            if monster_def:
                self.symbol = monster_def.symbol
                self.color = monster_def.color # 색상 추가
                self.level = monster_def.level
                self.exp_given = monster_def.exp_given
                self.move_type = monster_def.move_type
                self.original_move_type = self.move_type
            else:
                self.symbol = symbol if symbol else '?'
                self.color = color if color else 'white' # 색상 기본값
                self.level = level if level else 1
                self.exp_given = exp_given if exp_given else 10
                self.move_type = 'STATIONARY'
                self.original_move_type = self.move_type
                if self.ui_instance:
                    self.ui_instance.add_message(f"경고: 몬스터 정의 '{monster_id}'를 찾을 수 없습니다. 기본값 사용.")
        else:
            self.symbol = symbol if symbol else name[0] if name else 'M'
            self.color = color if color else 'white' # 색상 기본값
            self.level = level if level else 1
            self.exp_given = exp_given if exp_given else 10
            self.move_type = 'STATIONARY'
            self.original_move_type = self.move_type

        self.dead = False
        self.is_provoked = False
        self.loot = None
        self.entity_id = None

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "color": self.color, # 색상 추가
            "level": self.level,
            "exp_given": self.exp_given,
            "move_type": self.move_type,
            "original_move_type": self.original_move_type,
            "is_provoked": self.is_provoked,
            "dead": self.dead,
            "loot": self.loot,
            "entity_id": self.entity_id
        }

    @classmethod
    def from_dict(cls, data):
        monster = cls(
            symbol=data.get('symbol', data.get('name', 'M')[0]),
            color=data.get('color', 'white'), # 색상 로드
            level=data.get('level', 1),
            exp_given=data.get('exp_given', 10)
        )
        monster.move_type = data.get('move_type', 'STATIONARY')
        return monster

