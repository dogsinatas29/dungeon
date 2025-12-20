# player.py
from . import data_manager
from .components import StatsComponent


class Player:
    def __init__(self, name, hp=100, mp=50, level=1, dungeon_level=(1, 0)):
        # self.name = name # NameComponent에서 관리
        self.char = '@'
        self.entity_id = None # ECS 엔티티 ID 추가
        
        # 기본 스탯
        self.level = level
        # self.max_hp = hp # HealthComponent에서 관리
        # self.hp = hp # HealthComponent에서 관리
        self.max_mp = mp
        self.mp = mp
        self.max_stamina = 100.0
        self.stamina = 100.0
        # 보너스 스탯 (아이템, 버프 등)
        self.att_bonus = 0
        self.def_bonus = 0
        
        # 경험치
        self.exp = 0
        self.exp_to_next_level = 100
        
        # 기타
        self.dungeon_level = dungeon_level
        self.skills = {}
        self.item_quick_slots = {i: None for i in range(1, 6)}
        self.skill_quick_slots = {i: None for i in range(6, 11)}
        # self.equipment는 이제 self.inventory.equipped로 대체됩니다.
        self.is_provoked = False

    def is_alive(self, entity_manager):
        """플레이어가 살아있는지 여부를 반환합니다."""
    def is_alive(self, entity_manager):
        """플레이어가 살아있는지 여부를 반환합니다."""
        stats_comp = entity_manager.get_component(self.entity_id, StatsComponent)
        return stats_comp.is_alive if stats_comp else False

    def gain_exp(self, amount, entity_manager):
        """경험치를 얻고 레벨업을 확인합니다."""
        self.exp += amount
        leveled_up = False
        message = ""
        while self.exp >= self.exp_to_next_level:
            leveled_up = True
            self.exp -= self.exp_to_next_level
            self.level_up(entity_manager)
            message += f"레벨업! {self.level - 1} -> {self.level}. "
        return leveled_up, message.strip()

    def level_up(self, entity_manager):
        """플레이어의 레벨을 올리고 스탯을 강화합니다."""
        self.level += 1
        stats_comp = entity_manager.get_component(self.entity_id, StatsComponent)
        if stats_comp:
            stats_comp.max_hp += 10
            stats_comp.current_hp = stats_comp.max_hp
            stats_comp.attack += 2
            stats_comp.defense += 1

        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        
    def to_dict(self):
        """플레이어 데이터를 딕셔너리 형태로 변환하여 반환합니다."""
        return {
            # 'name': self.name, # NameComponent에서 관리
            # 'hp': self.hp, # HealthComponent에서 관리
            # 'max_hp': self.max_hp, # HealthComponent에서 관리
            'mp': self.mp, 'max_mp': self.max_mp,
            'stamina': self.stamina, 'max_stamina': self.max_stamina,
            'level': self.level, 'exp': self.exp, 'exp_to_next_level': self.exp_to_next_level,
            'skills': self.skills, 'dungeon_level': self.dungeon_level,
            'item_quick_slots': self.item_quick_slots, 'skill_quick_slots': self.skill_quick_slots,
            'entity_id': self.entity_id
            # 'equipment'는 inventory에 포함되므로 중복 저장할 필요 없음
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리 데이터로부터 Player 객체를 생성하여 반환합니다."""
        player = cls(
            # name=data.get('name', '용사'), # NameComponent에서 관리
            # hp=data.get('hp', 100), # HealthComponent에서 관리
            mp=data.get('mp', 50),
            level=data.get('level', 1),
            dungeon_level=tuple(data.get('dungeon_level', (1, 0)))
        )
        player.entity_id = data.get('entity_id', None)
        # player.max_hp = data.get('max_hp', player.hp) # HealthComponent에서 관리
        player.max_mp = data.get('max_mp', player.mp)
        player.stamina = float(data.get('stamina', 100.0))
        player.max_stamina = float(data.get('max_stamina', 100.0))
        player.exp = data.get('exp', 0)
        player.exp_to_next_level = data.get('exp_to_next_level', 100)
        
        player.skills = data.get('skills', {})
        player.item_quick_slots = data.get('item_quick_slots', {i: None for i in range(1, 6)})
        player.skill_quick_slots = data.get('skill_quick_slots', {i: None for i in range(6, 11)})
        
        return player
