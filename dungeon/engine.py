# /home/dogsinatas/python_project/dungeon/dungeon/engine.py (수정될 전체 코드)

import sys
import time
import math
import random
import re
import logging
# tcod 대신 readchar를 사용하므로 tcod 관련 import는 제거

# 로깅 설정
logging.basicConfig(filename='game_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- 필요한 모듈 및 클래스 임포트 (기존 코드 기반) ---
from events.event_manager import event_manager
from .map_manager import DungeonMap, EXIT_NORMAL, EXIT_LOCKED, ITEM_TILE, ROOM_ENTRANCE
from .renderer import UI, ANSI
from . import data_manager
from .items import Item
from .monster import Monster
from .player import Player
from .entity import EntityManager
from .component import PositionComponent, MovableComponent, MoveRequestComponent, InteractableComponent, ProjectileComponent, DamageRequestComponent, HealthComponent, NameComponent, AttackComponent, DefenseComponent, DeathComponent, GameOverComponent, InventoryComponent, EquipmentComponent, QuickSlotComponent, RenderComponent, ManaComponent, ColliderComponent, AIComponent
from .system import MovementSystem, CollisionSystem, InteractionSystem, ProjectileSystem, CombatSystem, DungeonGenerationSystem, DeathSystem, GameOverSystem, InventorySystem, SaveLoadSystem, RenderingSystem, LoggingSystem, AISystem
from .trap import Trap
from typing import Optional, Tuple, List # List 타입 힌트 추가

# ----------------------------------------------------

# --- Configuration ---
MAP_WIDTH = 80
MAP_HEIGHT = 45
UI_HEIGHT = 5

# 디버깅: readchar 임포트 확인
try:
    import readchar
    import readchar.key
except ImportError:
    print("Error: readchar not installed. Please install it using 'pip install readchar'")
    sys.exit(1)

# UIManager는 UI 클래스의 인스턴스로 가정합니다.
class UIManager(UI):
    def __init__(self, console_width, ui_height):
        super().__init__() # UI 클래스의 __init__ 호출
        self.MAP_VIEWPORT_WIDTH = console_width # 임시 설정
        self.MAP_VIEWPORT_HEIGHT = ui_height # 임시 설정 (맵 높이 아님)

# RNG 클래스 (시드 관리용)
class RNG:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else int(time.time())
        random.seed(self.seed)

    def randint(self, a, b):
        return random.randint(a, b)

class Engine:
    """게임의 메인 루프와 초기화를 담당하는 클래스입니다."""

    def __init__(self, rng_seed: Optional[int] = None):
        """엔진을 초기화합니다."""
        self.rng = RNG(rng_seed)
        self.ui_instance = UIManager(MAP_WIDTH, MAP_HEIGHT) # UI 클래스 인스턴스 생성
        self.entity_manager = EntityManager()
        self.rng_seed = self.rng.seed
        
        # 플레이어 엔티티 생성
        self.player_entity_id = self.entity_manager.create_entity()
        player_obj_template = Player("용사", hp=100, mp=50) # Player 클래스를 템플릿처럼 사용
        self.entity_manager.add_component(self.player_entity_id, PositionComponent(x=0, y=0, map_id=(1,0)))
        self.entity_manager.add_component(self.player_entity_id, MovableComponent())
        self.entity_manager.add_component(self.player_entity_id, HealthComponent(max_hp=player_obj_template.max_hp, current_hp=player_obj_template.hp))
        self.entity_manager.add_component(self.player_entity_id, NameComponent(name="용사"))
        self.entity_manager.add_component(self.player_entity_id, AttackComponent(power=10, critical_chance=0.05, critical_damage_multiplier=1.5))
        self.entity_manager.add_component(self.player_entity_id, DefenseComponent(value=3))
        self.entity_manager.add_component(self.player_entity_id, ManaComponent(max_mp=player_obj_template.max_mp, current_mp=player_obj_template.mp))
        self.entity_manager.add_component(self.player_entity_id, InventoryComponent())
        self.entity_manager.add_component(self.player_entity_id, EquipmentComponent())
        self.entity_manager.add_component(self.player_entity_id, QuickSlotComponent())
        self.entity_manager.add_component(self.player_entity_id, ColliderComponent(width=1, height=1))
        self.entity_manager.add_component(self.player_entity_id, RenderComponent(symbol=player_obj_template.char, color='white'))

        # 엔티티 정의 로드 (data_manager에서 로드)
        self.item_definitions = data_manager.load_item_definitions(self.ui_instance)
        self.monster_definitions = data_manager.load_monster_definitions(self.ui_instance)
        
        # 던전 맵 생성 (초기 맵)
        self.current_dungeon_level = (1, 0)
        self.all_dungeon_maps = {}
        self.dungeon_map = self._get_or_create_map(self.current_dungeon_level, self.all_dungeon_maps, self.ui_instance, self.item_definitions, self.monster_definitions)

        # 시스템 초기화
        self.movement_system = MovementSystem(self.entity_manager, self.dungeon_map)
        self.collision_system = CollisionSystem(self.entity_manager, self.dungeon_map, self.player_entity_id)
        self.interaction_system = InteractionSystem(self.entity_manager, self.dungeon_map, self.player_entity_id, self.ui_instance)
        self.projectile_system = ProjectileSystem(self.entity_manager, self.dungeon_map, self.ui_instance)
        self.combat_system = CombatSystem(self.entity_manager, self.ui_instance)
        self.dungeon_generation_system = DungeonGenerationSystem(self.entity_manager, self.dungeon_map, self.ui_instance, self.item_definitions, self.monster_definitions)
        self.death_system = DeathSystem(self.entity_manager, self.dungeon_map, self.ui_instance, self.player_entity_id)
        self.game_over_system = GameOverSystem(self.entity_manager, self.dungeon_map, self.ui_instance, self.player_entity_id)
        self.ai_system = AISystem(self.entity_manager, self.dungeon_map, self.player_entity_id)
        self.rendering_system = RenderingSystem(self.entity_manager, self.dungeon_map, self.ui_instance, self.player_entity_id)
        self.inventory_system = InventorySystem(self.entity_manager, self.ui_instance, self.item_definitions)
        self.logging_system = LoggingSystem(self.entity_manager, self.ui_instance)

        # 초기 던전 엔티티 생성 및 플레이어 위치 설정
        self.dungeon_generation_system.generate_dungeon_entities(self.current_dungeon_level)
        player_pos_comp = self.entity_manager.get_component(self.player_entity_id, PositionComponent)
        if player_pos_comp:
            player_pos_comp.x = self.dungeon_map.start_x
            player_pos_comp.y = self.dungeon_map.start_y
            self.dungeon_map.reveal_tiles(player_pos_comp.x, player_pos_comp.y)

        # 초기 메시지
        self.ui_instance.add_message("환영합니다! 던전에 오신 것을 환영합니다!")

        self.simulated_inputs: List[str] = []
        self.last_frame_time = time.time()

    def _get_or_create_map(self, level_tuple, all_dungeon_maps, ui_instance, item_definitions, monster_definitions):
        if level_tuple not in all_dungeon_maps:
            new_map = DungeonMap(MAP_WIDTH, MAP_HEIGHT, self.rng, level=level_tuple)
            new_map.generate_map(level_tuple, ui_instance)
            all_dungeon_maps[level_tuple] = new_map
        return all_dungeon_maps[level_tuple]

    def handle_input(self, key: Optional[str]) -> bool:
        """키 입력을 처리하고, 플레이어의 행동이 있었는지 여부를 반환합니다."""
        if key is None:
            return False

        player_pos = self.entity_manager.get_component(self.player_entity_id, PositionComponent)
        if not player_pos: return False

        player_action_taken = False
        
        inventory_open = False # 임시
        log_viewer_open = False # 임시

        if inventory_open:
            if key == readchar.key.UP:
                self.ui_instance.add_message("인벤토리: 위")
            elif key == readchar.key.DOWN:
                self.ui_instance.add_message("인벤토리: 아래")
            elif key == 'i':
                inventory_open = False
            player_action_taken = False

        elif log_viewer_open:
            if key == readchar.key.UP: pass
            elif key == readchar.key.DOWN: pass
            elif key == 'm': log_viewer_open = False
            player_action_taken = False

        else: # NORMAL 게임 상태
            dx, dy = 0, 0
            move_keys = {
                readchar.key.UP: (0, -1), readchar.key.DOWN: (0, 1),
                readchar.key.LEFT: (-1, 0), readchar.key.RIGHT: (1, 0),
                'k': (0, -1), 'j': (0, 1), 'h': (-1, 0), 'l': (1, 0),
                'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1)
            }
            
            if key in move_keys:
                dx, dy = move_keys[key]
                new_x, new_y = player_pos.x + dx, player_pos.y + dy

                target_monster_entity_id = None
                for eid, pos_comp in self.entity_manager.get_components_of_type(PositionComponent).items():
                    if eid != self.player_entity_id and pos_comp.x == new_x and pos_comp.y == new_y and self.entity_manager.has_component(eid, HealthComponent):
                        target_monster_entity_id = eid
                        break

                if target_monster_entity_id:
                    player_attack_comp = self.entity_manager.get_component(self.player_entity_id, AttackComponent)
                    if player_attack_comp:
                        self.entity_manager.add_component(target_monster_entity_id, DamageRequestComponent(
                            target_id=target_monster_entity_id, 
                            amount=player_attack_comp.power, 
                            attacker_id=self.player_entity_id
                        ))
                        self.ui_instance.add_message(f"플레이어가 {self.entity_manager.get_component(target_monster_entity_id, NameComponent).name}을(를) 공격했습니다!")
                        player_action_taken = True
                else:
                    self.entity_manager.add_component(self.player_entity_id, MoveRequestComponent(entity_id=self.player_entity_id, dx=dx, dy=dy))
                    player_action_taken = True
                    
            elif key == '.': # 대기
                self.ui_instance.add_message("플레이어가 대기합니다.")
                player_action_taken = True

            elif key == 'i': # 인벤토리 열기 (토글)
                inventory_open = True
                self.ui_instance.add_message("인벤토리를 엽니다.")
                player_action_taken = False
            
            elif key == 'q': # 게임 종료
                self.ui_instance.add_message("게임을 종료합니다.")
                sys.exit(0)

            elif key == 'r': # 아이템 루팅
                message, looted = self.inventory_system.loot_items(self.player_entity_id, self.dungeon_map)
                self.ui_instance.add_message(message)
                if looted:
                    player_action_taken = True

            elif key in "1234567890":
                slot_num = 10 if key == '0' else int(key)
                quickslot_comp = self.entity_manager.get_component(self.player_entity_id, QuickSlotComponent)
                mana_comp = self.entity_manager.get_component(self.player_entity_id, ManaComponent)
                
                if not quickslot_comp: return False

                if 1 <= slot_num <= 5: # 아이템 퀵슬롯
                    item_id = quickslot_comp.item_slots.get(slot_num)
                    if item_id:
                        self.entity_manager.add_component(self.player_entity_id, ItemUseRequestComponent(entity_id=self.player_entity_id, item_id=item_id))
                        player_action_taken = True
                    else:
                        self.ui_instance.add_message(f"퀵슬롯 {slot_num}번이 비어있습니다.")

                elif 6 <= slot_num <= 10: # 스킬 퀵슬롯
                    skill_id = quickslot_comp.skill_slots.get(slot_num)
                    if skill_id:
                        skill_def = data_manager.get_skill_definition(skill_id)
                        if skill_def and mana_comp and mana_comp.current_mp >= skill_def.cost_value:
                            mana_comp.current_mp -= skill_def.cost_value
                            if skill_def.skill_subtype == 'PROJECTILE':
                                # TODO: use_projectile_skill 함수 Engine 클래스 메서드로 이동 또는 ProjectileSystem 통합
                                self.ui_instance.add_message(f"'{skill_def.name}' 스킬 사용 (구현 예정)")
                                player_action_taken = True
                            else:
                                self.ui_instance.add_message(f"'{skill_def.name}' 스킬은 아직 구현되지 않았습니다.")
                            player_action_taken = True
                        else:
                            self.ui_instance.add_message("스킬을 사용하기 위한 MP가 부족하거나 스킬을 찾을 수 없습니다.")
                    else:
                        self.ui_instance.add_message(f"퀵슬롯 {slot_num}번이 비어있습니다.")

        return player_action_taken

    def run_game_loop(self):
        """메인 게임 루프입니다. 프레임 기반의 실시간으로 동작합니다."""
        
        while True:
            current_time = time.time()
            dt = current_time - self.last_frame_time # 델타 타임 계산
            self.last_frame_time = current_time

            # 1. 입력 처리 (논블로킹)
            key = None
            if self.simulated_inputs:
                key = self.simulated_inputs.pop(0) # 시뮬레이션된 입력 처리
            else:
                # sys.stdin의 논블로킹 읽기를 시도합니다.
                # 이는 UNIX 계열 시스템에서만 동작하며, Windows에서는 다른 방법을 사용해야 합니다.
                try:
                    import select
                    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        key = readchar.readkey() # 입력이 있으면 읽습니다.
                except Exception:
                    pass # 입력이 없거나 오류 발생 시 무시

            self.handle_input(key)

            # 2. ECS 업데이트 (매 프레임 실행)
            # 모든 시스템을 델타 타임(dt)과 함께 업데이트합니다.
            self.movement_system.update() 
            self.collision_system.update()
            self.interaction_system.update() 
            self.projectile_system.update()
            self.combat_system.update() 
            self.ai_system.update(dt) # AISystem에 dt 전달
            self.death_system.update() 
            self.game_over_system.update()
            self.inventory_system.update()
            self.logging_system.update()

            # 3. 렌더링 및 UI 업데이트 (항상 실행)
            self.rendering_system.update()
            self.ui_instance.refresh() # UI 렌더링 및 메시지 표시

            # 게임 오버 상태 확인
            game_over_comp = self.entity_manager.get_component(self.player_entity_id, GameOverComponent)
            if game_over_comp:
                message = "게임 승리!" if game_over_comp.win else "게임 오버!"
                self.ui_instance.add_message(f"{message} 'q'를 눌러 종료하세요.")
                self.ui_instance.refresh()
                key = readchar.readchar() # 게임 오버 상태에서는 블로킹 입력 대기
                if key == 'q':
                    break
                continue

            # 프레임 속도 조절 (예: 초당 30프레임)
            frame_time = time.time() - current_time
            if frame_time < (1 / 30): # 목표 FPS (예: 30)
                time.sleep((1 / 30) - frame_time)


def run_game(rng_seed: Optional[int] = None):
    """게임 인스턴스를 생성하고 실행합니다."""
    engine = Engine(rng_seed)
    engine.run_game_loop()

if __name__ == '__main__':
    # 시드 고정 또는 랜덤 시드 사용
    RNG_SEED = int(time.time()) 
    run_game(RNG_SEED)