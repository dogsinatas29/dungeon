from dataclasses import dataclass
from typing import List, Tuple

from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class PlayerMovedEvent:
    entity_id: int
    old_pos: Tuple[int, int]
    new_pos: Tuple[int, int]
    encountered_monster_ids: List[str]
