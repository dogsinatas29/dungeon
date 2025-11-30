from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class InputReceivedEvent:
    key: str

@dataclass
class PlayerMovedEvent:
    entity_id: int
    old_pos: Tuple[int, int]
    new_pos: Tuple[int, int]
    encountered_monster_ids: List[str]

@dataclass
class DoorOpenedEvent:
    entity_id: int # 문의 엔티티 ID
    opener_entity_id: int # 문을 연 엔티티 (플레이어)
    door_id: str # 문의 ID (예: key_id와 동일)
    x: int
    y: int

@dataclass
class DoorClosedEvent:
    entity_id: int # 문의 엔티티 ID
    closer_entity_id: int # 문을 닫은 엔티티 (플레이어)
    door_id: str # 문의 ID (예: key_id와 동일)
    x: int
    y: int

@dataclass
class KeyUsedEvent:
    entity_id: int # 열쇠를 사용한 엔티티 (플레이어)
    key_id: str # 사용된 열쇠의 ID
    door_entity_id: int # 열쇠가 사용된 문의 엔티티 ID

@dataclass
class GameMessageEvent:
    message: str

@dataclass
class MonsterDiedEvent:
    monster_entity_id: int
    killer_entity_id: int
    exp_given: int

