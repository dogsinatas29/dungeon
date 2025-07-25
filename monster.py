# monster.py
import data_manager # data_manager 모듈 임포트

class Monster:
    def __init__(self, x, y, ui_instance=None, monster_id=None, name=None, hp=None, attack=None, defense=None, level=None, exp_given=None):
        self.ui_instance = ui_instance
        
        if monster_id:
            # monster_id가 제공되면 정의에서 로드
            monster_def = data_manager.get_monster_definition(monster_id)
            if monster_def:
                self.name = monster_def.name
                self.hp = monster_def.hp
                self.max_hp = monster_def.hp
                self.attack = monster_def.attack
                self.defense = monster_def.defense
                self.level = monster_def.level
                self.exp_given = monster_def.exp_given
            else:
                # 정의를 찾을 수 없으면 기본값 사용 (경고 메시지 추가 가능)
                self.name = name if name else "알 수 없는 몬스터"
                self.hp = hp if hp else 30
                self.max_hp = self.hp
                self.attack = attack if attack else 8
                self.defense = defense if defense else 2
                self.level = level if level else 1
                self.exp_given = exp_given if exp_given else 10
                if self.ui_instance:
                    self.ui_instance.add_message(f"경고: 몬스터 정의 '{monster_id}'를 찾을 수 없습니다. 기본값 사용.")
        else:
            # monster_id가 없으면 인자로 받은 값 사용 (기존 방식)
            self.name = name if name else "몬스터"
            self.hp = hp if hp else 30
            self.max_hp = self.hp
            self.attack = attack if attack else 8
            self.defense = defense if defense else 2
            self.level = level if level else 1
            self.exp_given = exp_given if exp_given else 10

        self.x = x
        self.y = y
        self.char = self.name[0] # 이름의 첫 글자를 표시
        self.dead = False

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
        return self.dead
    
    def attack(self, target_player):
        # 전투 로직은 combat.py로 이동 예정
        if self.ui_instance:
            self.ui_instance.add_message(f"{self.name}이(가) 공격합니다!")
        
        # 임시 데미지 계산
        damage = max(1, self.attack - target_player.defense)
        target_player.take_damage(damage)

        if self.ui_instance:
            self.ui_instance.add_message(f"{damage}의 데미지를 입었습니다! 남은 HP: {target_player.hp}")
            if not target_player.is_alive():
                self.ui_instance.add_message("당신은 쓰러졌습니다...")

    def to_dict(self):
        return {
            "name": self.name, "x": self.x, "y": self.y,
            "hp": self.hp, "max_hp": self.max_hp,
            "attack": self.attack, "defense": self.defense,
            "level": self.level,
            "exp_given": self.exp_given, # 경험치 저장
            "dead": self.dead
        }

    @classmethod
    def from_dict(cls, data):
        monster = cls(
            x=data['x'], y=data['y'],
            name=data.get('name', '몬스터'),
            hp=data.get('hp', 30),
            attack=data.get('attack', 8),
            defense=data.get('defense', 2),
            level=data.get('level', 1),
            exp_given=data.get('exp_given', 10) # 경험치 로드
        )
        monster.max_hp = data.get('max_hp', monster.hp)
        monster.dead = data.get('dead', False)
        return monster

