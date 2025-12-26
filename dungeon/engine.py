import random
import time
import os
import sys
import select
import json
import termios
import tty
import readchar
from typing import Dict, List, Set, Type, Optional, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import (
    PositionComponent, RenderComponent, StatsComponent, InventoryComponent, 
    LevelComponent, MapComponent, MessageComponent, MonsterComponent, 
    AIComponent, LootComponent, CorpseComponent, ChestComponent, ShopComponent,
    StunComponent, SkillEffectComponent, HitFlashComponent, HiddenComponent, MimicComponent, TrapComponent
)
from .systems import (
    InputSystem, MovementSystem, RenderSystem, MonsterAISystem, CombatSystem, 
    TimeSystem, RegenerationSystem, LevelSystem, TrapSystem
)
from .events import MessageEvent, DirectionalAttackEvent, MapTransitionEvent, ShopOpenEvent
from .sound_system import SoundSystem
from .renderer import Renderer
from .data_manager import load_item_definitions
from .constants import (
    ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON, ELEMENT_COLORS
)



import enum

class GameState:
    PLAYING = 0
    INVENTORY = 1
    SHOP = 2

class Engine:
    """게임 루프, 초기화, 시스템 관리를 담당하는 메인 클래스"""
    def __init__(self, player_name="Hero", game_data=None):
        self.is_running = False
        self.world = World(self) # World 초기화 시 Engine 자신을 참조
        self.turn_number = 0
        self.dungeon_map = None # 현재 층의 맵 인스턴스
        
        # game_data가 있고 player_name이 None이면, 저장된 데이터에서 이름 로드
        if game_data and player_name is None:
            self.player_name = game_data["player_specific_data"]["name"]
        else:
            self.player_name = player_name
            
        self.state = GameState.PLAYING # 초기 상태
        self.is_attack_mode = False # 원거리 공격/스킬 모드
        self.active_skill_name = None # 현재 시전 준비 중인 스킬
        self.current_level = 1 # 현재 던전 층수
        self.selected_item_index = 0 # 인벤토리 선택 인덱스
        self.inventory_category_index = 0 # 0: 아이템, 1: 장비, 2: 스크롤, 3: 스킬
        self.shop_category_index = 0 # 0: 사기, 1: 팔기
        self.selected_shop_item_index = 0 # 상점 선택 인덱스

        # 렌더러 초기화
        self.renderer = Renderer() 

        # 데이터 정의 로드 (항상 사용 가능하도록 __init__에서 처리)
        from .data_manager import load_item_definitions, load_skill_definitions, load_monster_definitions, load_map_definitions
        self.item_defs = load_item_definitions()
        self.skill_defs = load_skill_definitions()
        self.monster_defs = load_monster_definitions()
        self.map_defs = load_map_definitions()
        
        # 접두어 관리자 초기화
        from .modifiers import ModifierManager
        self.modifier_manager = ModifierManager()

        self._initialize_world(game_data)
        self._initialize_systems()

    def _initialize_world(self, game_data=None, preserve_player=None):
        """맵, 플레이어, 몬스터 등 초기 엔티티 생성"""
        # 0. 맵 설정 가져오기 (floor는 1부터 시작하므로 문자열 변환 시 1, 2, ... 확인)
        map_config = self.map_defs.get(str(self.current_level))
        if not map_config:
            # 설정이 없으면 기본값 (또는 가장 가까운 층의 설정)
            map_config = next(iter(self.map_defs.values())) if self.map_defs else None
        
        if map_config:
            width = map_config.width
            height = map_config.height
            map_type = map_config.map_type
        else:
            width = 120
            height = 60
            map_type = "BOSS" if self.current_level % 5 == 0 else "NORMAL"
        
        # DungeonMap 인스턴스 생성
        dungeon_map = DungeonMap(width, height, random, map_type=map_type)
        self.dungeon_map = dungeon_map
        map_data = dungeon_map.map_data
        
        # 1. 플레이어 엔티티 생성 (ID=1)
        player_x, player_y = dungeon_map.start_x, dungeon_map.start_y
        player_entity = self.world.create_entity() 
        self.world.add_component(player_entity.entity_id, PositionComponent(x=player_x, y=player_y))
        self.world.add_component(player_entity.entity_id, RenderComponent(char='@', color='yellow'))
        
        if preserve_player:
            p_stats, p_inv, p_level = preserve_player
            self.world.add_component(player_entity.entity_id, p_stats)
            self.world.add_component(player_entity.entity_id, p_inv)
            self.world.add_component(player_entity.entity_id, p_level)
        elif game_data and "entities" in game_data:
            # 저장된 데이터에서 엔티티 복원 (플레이어 ID=1 가정)
            player_data = game_data["entities"].get("1")
            if player_data:
                # StatsComponent 복원
                stats_data = player_data.get("StatsComponent", {})
                stats = StatsComponent(**stats_data)
                self.world.add_component(player_entity.entity_id, stats)
                
                # LevelComponent 복원
                level_data = player_data.get("LevelComponent", {})
                level = LevelComponent(**level_data)
                self.world.add_component(player_entity.entity_id, level)

                # InventoryComponent 복원
                inv_data = player_data.get("InventoryComponent", {})
                # 아이템 딕셔너리 복구 (JSON 리스트를 다시 ItemDefinition 객체로)
                restored_items = {}
                for name, data in inv_data.get("items", {}).items():
                    item_info = data.get("item", {})
                    if item_info:
                        from .data_manager import ItemDefinition
                        item_obj = ItemDefinition(**item_info)
                        restored_items[name] = {"item": item_obj, "qty": data.get("qty", 1)}
                
                # 장착 상태 복구
                restored_equipped = {}
                for slot, eq_data in inv_data.get("equipped", {}).items():
                    if isinstance(eq_data, dict) and "name" in eq_data:
                        from .data_manager import ItemDefinition
                        restored_equipped[slot] = ItemDefinition(**eq_data)
                    else:
                        restored_equipped[slot] = eq_data

                inv = InventoryComponent(
                    items=restored_items,
                    equipped=restored_equipped,
                    item_slots=inv_data.get("item_slots"),
                    skill_slots=inv_data.get("skill_slots"),
                    skills=inv_data.get("skills")
                )
                self.world.add_component(player_entity.entity_id, inv)
            else:
                # 플레이어 데이터 없으면 기본값
                self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
                self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))
        else:
            self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
            self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))
        
        # 기본 스택 및 스킬 설정
        if not preserve_player and (not game_data or "entities" not in game_data):
            # 샘플 아이템 추가 (새 게임 시에만)
            sample_items = {}
            if self.item_defs:
                for name, item in self.item_defs.items():
                    sample_items[name] = {'item': item, 'qty': 1}
            
            equipped = {slot: None for slot in ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]}
            if "가죽 갑옷" in sample_items:
                equipped["몸통"] = sample_items["가죽 갑옷"]["item"]
            if "낡은 검" in sample_items:
                equipped["손1"] = sample_items["낡은 검"]["item"]
            
            # 스킬 슬롯 일부 비워두기 (Lv1만 등록, 나머지는 사용자가 직접)
            self.world.add_component(player_entity.entity_id, InventoryComponent(
                items=sample_items, 
                equipped=equipped,
                item_slots=["체력 물약", "마력 물약", "화염 스크롤", "순간 이동 스크롤", "마커"],
                skill_slots=["기본 공격", "파이어볼 Lv1", None, None, None],
                skills=["기본 공격", "파이어볼 Lv1", "파이어볼 Lv2", "파이어볼 Lv3", "힐"]
            ))
            
            # [추가] 신규 방어구 지급 (테스트용)
            inv = player_entity.get_component(InventoryComponent)
            test_gear = ["가죽 투구", "철제 갑옷", "기사의 건틀릿", "신속의 장화"]
            for gear_name in test_gear:
                if gear_name in self.item_defs:
                    inv.items[gear_name] = {'item': self.item_defs[gear_name], 'qty': 1}
        
        # 테스트용 스킬북 아이템 추가
        inv = player_entity.get_component(InventoryComponent)
        skill_books = ["파이어볼 스킬북 Lv1", "파이어볼 스킬북 Lv2", "파이어볼 스킬북 Lv3", "휠 윈드 스킬북"]
        for book_name in skill_books:
            if book_name in self.item_defs:
                inv.items[book_name] = {'item': self.item_defs[book_name], 'qty': 1}
        
        # 휠 윈드를 배운 상태로 시작 (테스트를 위해)
        if "휠 윈드" not in inv.skills:
            inv.skills.append("휠 윈드")
        
        # 초기 스탯 계산 (장비 보너스 적용)
        self._recalculate_stats()
        
        # 2. 맵 엔티티 생성 (ID=2)
        map_entity = self.world.create_entity()
        # map_data는 이미 2D 리스트이므로 바로 전달
        map_component = MapComponent(width=width, height=height, tiles=map_data) 
        self.world.add_component(map_entity.entity_id, map_component)
        
        # 3. 메시지 로그 엔티티 생성 (ID=3)
        message_entity = self.world.create_entity()
        message_comp = MessageComponent()
        message_comp.add_message(f"던전 {self.current_level}층에 입장했습니다.")
        if map_type == "BOSS":
            message_comp.add_message("[경고] 강력한 보스의 기운이 느껴집니다!", "red")
        else:
            message_comp.add_message("WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.")
        self.world.add_component(message_entity.entity_id, message_comp)
        
        # 4. 엔티티 배치 (몬스터/보스/오브젝트)
        has_boss = map_config.has_boss if map_config else (map_type == "BOSS")
        if has_boss:
            # 보스 설정 가져오기
            boss_ids = map_config.boss_ids if map_config else []
            boss_count = map_config.boss_count if map_config and map_config.boss_count > 0 else (len(boss_ids) if boss_ids else 1)
            attacker_pool = map_config.monster_pool if map_config else []
            
            # 보스 스폰 및 즉각 알림
            for i in range(boss_count):
                # 보스 ID 결정 (리스트 순환하거나 없으면 랜덤)
                b_id = boss_ids[i % len(boss_ids)] if boss_ids else None
                
                # 출구 주변에 분산 배치
                spawn_x = dungeon_map.exit_x - 3 - (i % 3)
                spawn_y = dungeon_map.exit_y + (i // 3) - (boss_count // 6)
                
                boss_ent = self._spawn_boss(spawn_x, spawn_y, attacker_pool, boss_name=b_id)
                if boss_ent:
                    m_comp = boss_ent.get_component(MonsterComponent)
                    name = m_comp.type_name if m_comp else "강력한 적"
                    message_comp.add_message(f"[경고] {name}이(가) 나타났습니다!", "red")

            # 주변 호위병 몇 기
            for _ in range(3):
                rx = dungeon_map.exit_x - random.randint(3, 6)
                ry = dungeon_map.exit_y + random.randint(-3, 3)
                self._spawn_monster_at(rx, ry, pool=attacker_pool)
        
        # 일반 몬스터 및 오브젝트 스폰
        if map_type != "BOSS" or not has_boss:
            self._spawn_monsters(dungeon_map, map_config)
            
        self._spawn_objects(dungeon_map, map_config)

    def _spawn_monster_at(self, x, y, monster_def=None, pool=None):
        """지정된 위치에 몬스터 한 마리를 생성합니다."""
        if not monster_def and self.monster_defs:
            if pool:
                # 풀에서 유효한 몬스터 선택
                candidates = [self.monster_defs[name] for name in pool if name in self.monster_defs]
                if candidates:
                    monster_def = random.choice(candidates)
            
            if not monster_def:
                # 보스 제외한 랜덤 몬스터 선택
                normal_monsters = [m for m in self.monster_defs.values() if 'BOSS' not in m.flags]
                monster_def = random.choice(normal_monsters if normal_monsters else list(self.monster_defs.values()))
        
        if not monster_def: return None

        monster = self.world.create_entity()
        self.world.add_component(monster.entity_id, PositionComponent(x=x, y=y))
        
        # 상성 및 플래그 설정
        from .constants import ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON, ELEMENT_COLORS
        all_elements = [ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON]
        monster_el = random.choice(all_elements)
        color = ELEMENT_COLORS.get(monster_el, "white")
        m_flags = monster_def.flags.copy()
        if monster_el != "NONE": m_flags.add(monster_el.upper())

        # 접두어 적용 (30%)
        m_name, m_hp, m_atk, m_def = monster_def.name, monster_def.hp, monster_def.attack, monster_def.defense
        if random.random() < 0.3:
            mod_def = self.modifier_manager.apply_monster_prefix(monster_def)
            m_name, m_hp, m_atk, m_def = mod_def.name, mod_def.hp, mod_def.attack, mod_def.defense
            m_flags.update(mod_def.flags)
            if mod_def.color != "white": color = mod_def.color

        self.world.add_component(monster.entity_id, RenderComponent(char=monster_def.symbol, color=color))
        self.world.add_component(monster.entity_id, MonsterComponent(type_name=m_name))
        self.world.add_component(monster.entity_id, AIComponent(behavior=random.randint(1, 2), detection_range=8))
        
        stats = StatsComponent(max_hp=m_hp, current_hp=m_hp, attack=m_atk, defense=m_def, element=monster_el)
        stats.flags.update(m_flags)
        stats.action_delay = monster_def.action_delay
        self.world.add_component(monster.entity_id, stats)
        return monster

    def _spawn_monsters(self, dungeon_map, map_config=None):
        """일반 층의 몬스터들을 스폰합니다."""
        pool = map_config.monster_pool if map_config else None
        
        starting_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
        for room in dungeon_map.rooms:
            if room == starting_room: continue
            
            # 방 크기에 비례하여 몬스터 수 결정 (2~5마리)
            num = random.randint(2, 5)
            for _ in range(num):
                mx = random.randint(room.x1 + 1, room.x2 - 1)
                my = random.randint(room.y1 + 1, room.y2 - 1)
                self._spawn_monster_at(mx, my, pool=pool)

        # 복도 스폰 (5% 확률)
        for cx, cy in dungeon_map.corridors:
            if random.random() < 0.05:
                # 시작 지점 근처(반경 15칸)는 스폰 제외
                if (cx - dungeon_map.start_x)**2 + (cy - dungeon_map.start_y)**2 < 225:
                    continue
                self._spawn_monster_at(cx, cy, pool=pool)

    def _spawn_boss(self, x, y, pool=None, boss_name=None):
        """지정된 위치에 보스를 스폰합니다."""
        if not self.monster_defs: return
        
        boss_defs = []
        if boss_name and boss_name in self.monster_defs:
            boss_defs = [self.monster_defs[boss_name]]
        elif pool:
            boss_defs = [self.monster_defs[name] for name in pool if name in self.monster_defs and 'BOSS' in self.monster_defs[name].flags]
        
        if not boss_defs:
            boss_defs = [m for m in self.monster_defs.values() if 'BOSS' in m.flags]
            
        if not boss_defs: return
        
        boss_def = random.choice(boss_defs)
        boss = self.world.create_entity()
        self.world.add_component(boss.entity_id, PositionComponent(x=x, y=y))
        self.world.add_component(boss.entity_id, RenderComponent(char=boss_def.symbol, color=boss_def.color))
        self.world.add_component(boss.entity_id, MonsterComponent(type_name=boss_def.name))
        self.world.add_component(boss.entity_id, AIComponent(behavior=1, detection_range=15)) # AGGRESSIVE
        
        stats = StatsComponent(max_hp=boss_def.hp, current_hp=boss_def.hp, attack=boss_def.attack, defense=boss_def.defense)
        stats.flags.update(boss_def.flags)
        stats.action_delay = boss_def.action_delay
        self.world.add_component(boss.entity_id, stats)
        return boss

    def _spawn_objects(self, dungeon_map, map_config=None):
        """상자, 상인 등 오브젝트를 스폰합니다."""
        starting_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
        
        # 상인 (시작 방 고정)
        if starting_room:
            sx, sy = starting_room.x1 + 1, starting_room.y1 + 1
            shop = self.world.create_entity()
            self.world.add_component(shop.entity_id, PositionComponent(x=sx, y=sy))
            self.world.add_component(shop.entity_id, RenderComponent(char='S', color='magenta'))
            shop_items = [
                {'item': self.item_defs.get('체력 물약'), 'price': 20},
                {'item': self.item_defs.get('마력 물약'), 'price': 20},
                {'item': self.item_defs.get('화염 스크롤'), 'price': 50},
                {'item': self.item_defs.get('가죽 갑옷'), 'price': 100},
                {'item': self.item_defs.get('낡은 검'), 'price': 80},
            ]
            shop_items = [si for si in shop_items if si['item'] is not None]
            self.world.add_component(shop.entity_id, ShopComponent(items=shop_items))
            self.world.add_component(shop.entity_id, MonsterComponent(type_name="상인"))

        # 보물 상자 (CSV 설정 기반)
        chest_count = map_config.chest_count if map_config else 2
        mimic_prob = map_config.mimic_prob if map_config else 0.1
        item_pool = map_config.item_pool if map_config else []
        
        other_rooms = dungeon_map.rooms[1:] if len(dungeon_map.rooms) > 1 else dungeon_map.rooms
        
        for _ in range(chest_count):
            room = random.choice(other_rooms)
            cx = random.randint(room.x1 + 1, room.x2 - 1)
            cy = random.randint(room.y1 + 1, room.y2 - 1)
            
            # 미믹 여부 결정
            if random.random() < mimic_prob:
                self._spawn_mimic(cx, cy)
            else:
                self._spawn_chest(cx, cy, item_pool)

        # 함정 (CSV 설정 기반)
        trap_prob = map_config.trap_prob if map_config else 0.05
        for room in other_rooms:
            if random.random() < trap_prob:
                tx = random.randint(room.x1 + 1, room.x2 - 1)
                ty = random.randint(room.y1 + 1, room.y2 - 1)
                self._spawn_trap(tx, ty)

    def _spawn_trap(self, x, y):
        """함정 엔티티 생성"""
        trap = self.world.create_entity()
        self.world.add_component(trap.entity_id, PositionComponent(x=x, y=y))
        
        trap_types = [
            {"type": "가시", "damage": 10, "effect": None},
            {"type": "마비", "damage": 5, "effect": "STUN"},
        ]
        t_data = random.choice(trap_types)
        self.world.add_component(trap.entity_id, TrapComponent(trap_type=t_data["type"], damage=t_data["damage"], effect=t_data["effect"]))

    def _spawn_mimic(self, x, y):
        """보물상자로 위장한 미믹 스폰"""
        monster_def = self.monster_defs.get("MIMIC")
        if not monster_def:
            # 미믹 정의가 없으면 고블린을 베이스로 이름만 변경
            monster_def = self.monster_defs.get("GOBLIN") or next(iter(self.monster_defs.values()))
        
        monster = self.world.create_entity()
        self.world.add_component(monster.entity_id, PositionComponent(x=x, y=y))
        # 초기 렌더링 (disguised=True 일 때는 상자 기호 '['로 렌더링됨)
        self.world.add_component(monster.entity_id, RenderComponent(char=monster_def.symbol, color=monster_def.color))
        self.world.add_component(monster.entity_id, MonsterComponent(type_name="보물상자?"))
        self.world.add_component(monster.entity_id, AIComponent(behavior=AIComponent.STATIONARY, detection_range=2))
        self.world.add_component(monster.entity_id, MimicComponent(is_disguised=True))
        self.world.add_component(monster.entity_id, ChestComponent()) # 충돌 발생 시 체크용
        
        stats = StatsComponent(max_hp=monster_def.hp*2, current_hp=monster_def.hp*2, attack=monster_def.attack, defense=monster_def.defense)
        stats.action_delay = 0.5
        self.world.add_component(monster.entity_id, stats)

    def _spawn_chest(self, x, y, item_pool=None):
        """일반 보물상자 스폰"""
        chest = self.world.create_entity()
        self.world.add_component(chest.entity_id, PositionComponent(x=x, y=y))
        self.world.add_component(chest.entity_id, RenderComponent(char='[', color='brown'))
        self.world.add_component(chest.entity_id, ChestComponent())
        
        loot_items = []
        if item_pool:
            candidates = [self.item_defs[name] for name in item_pool if name in self.item_defs]
            if candidates:
                loot_items.append({'item': random.choice(candidates), 'qty': 1})
        
        if not loot_items and self.item_defs:
            loot_items.append({'item': random.choice(list(self.item_defs.values())), 'qty': 1})
            
        self.world.add_component(chest.entity_id, LootComponent(items=loot_items, gold=random.randint(10, 50)))
        
        # 20% 확률로 숨겨진 상자 설정
        if random.random() < 0.2:
            self.world.add_component(chest.entity_id, HiddenComponent(blink=True))

    def _spawn_minion(self, x, y, m_id):
        """보스 등이 소환하는 미니언 생성"""
        return self._spawn_monster_at(x, y, self.monster_defs.get(m_id))

    def _initialize_systems(self):
        """시스템 등록 (실행 순서가 중요함)"""
        self.time_system = TimeSystem(self.world)
        self.input_system = InputSystem(self.world)
        self.monster_ai_system = MonsterAISystem(self.world)
        self.movement_system = MovementSystem(self.world)
        self.combat_system = CombatSystem(self.world)
        self.regeneration_system = RegenerationSystem(self.world)
        self.level_system = LevelSystem(self.world)
        self.trap_system = TrapSystem(self.world)
        self.sound_system = SoundSystem(self.world)
        self.render_system = RenderSystem(self.world)
        
        # 2. 시스템 순서 등록: 시간 -> 입력 -> AI -> 이동 -> 전투 -> 레벨 -> 회복 -> 렌더링
        systems = [
            self.time_system,
            self.input_system,
            self.monster_ai_system,
            self.movement_system,
            self.combat_system,
            self.level_system,
            self.trap_system,
            self.regeneration_system,
            self.sound_system,
            self.render_system
        ]
        for system in systems:
            self.world.add_system(system)
            
        # 4. 모든 시스템의 리스너 초기화 헬퍼 호출
        initialize_event_listeners(self.world)

        # 5. 추가적인 전역 이벤트 리스너 등록 (Engine 자체 핸들러 등)
        # initialize_event_listeners가 리스트를 초기화하므로 그 이후에 수동 등록해야 함
        self.world.event_manager.register(MapTransitionEvent, self)
        self.world.event_manager.register(ShopOpenEvent, self)

    def _get_input(self) -> Optional[str]:
        """사용자 입력을 받음 (os.read를 사용한 저수준 정밀 파싱)"""
        fd = sys.stdin.fileno()
        # 데이터가 있는지 확인
        dr, dw, de = select.select([fd], [], [], 0.005)
        if not dr:
            return None

        # 첫 번째 바이트 읽기
        try:
            char_bytes = os.read(fd, 1)
            if not char_bytes:
                return None
            char = char_bytes.decode('utf-8', errors='ignore')
            
            # 이스케이프 시퀀스 시작 감지
            if char == '\x1b':
                seq = char
                # 후속 데이터가 있는지 확인 (연쇄적으로 빠르게 읽음)
                while True:
                    dr, dw, de = select.select([fd], [], [], 0.005)
                    if dr:
                        next_bytes = os.read(fd, 1)
                        if not next_bytes: break
                        next_char = next_bytes.decode('utf-8', errors='ignore')
                        seq += next_char
                        # 방향키 등 일반적인 이스케이프 시퀀스 종료 문자
                        if next_char in 'ABCDHFE~RT':
                            break
                        if len(seq) > 10: break
                    else:
                        break
                return seq
            return char
        except:
            return None

    def run(self) -> str:
        """메인 게임 루프. 종료 시 결과를 문자열로 반환합니다."""
        self.is_running = True
        game_result = "QUIT"
        
        # 터미널 설정 저장 및 cbreak 모드 전환
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setcbreak(fd)
            # 커서 숨기기
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
            
            # 첫 렌더링
            self._render()
            
            last_frame_time = time.time()
            target_fps = 20
            frame_duration = 1.0 / target_fps
            
            while self.is_running:
                current_time = time.time()
                elapsed_since_frame = current_time - last_frame_time
                
                # 1. 사용자 입력 처리 (비차단)
                action = self._get_input()
                
                if action:
                    # [DEBUG] 로그에 입력된 키를 남김 (피드백용)
                    self.world.event_manager.push(MessageEvent(f"Debug Key: {repr(action)}"))
                    
                    # Ctrl+C 처리 (\x03)
                    if action == '\x03':
                        raise KeyboardInterrupt

                    action_lower = action.lower()

                    if self.state == GameState.PLAYING:
                        if action_lower == 'i':
                            self.state = GameState.INVENTORY
                            self.selected_item_index = 0
                            self._render()
                            continue
                        
                        # InputSystem은 이제 쿨다운을 자체적으로 관리하며, 
                        # 입력이 들어왔을 때만 해당 입력을 큐에 넣거나 즉시 처리함.
                        self.input_system.handle_input(action)
                        
                        # 입력 직후 즉시 렌더링
                        self._render()
                        last_frame_time = current_time
                    
                    elif self.state == GameState.INVENTORY:
                        if action_lower == 'i':
                            self.state = GameState.PLAYING
                        else:
                            self._handle_inventory_input(action)
                        self._render()
                        last_frame_time = current_time
                    elif self.state == GameState.SHOP:
                        if action_lower == 'q':
                            self.state = GameState.PLAYING
                        else:
                            self._handle_shop_input(action)
                        self._render()
                        last_frame_time = current_time
                
                # 2. 실시간 로직 처리 (입력 여부와 관계없이 매 프레임 실행)
                if self.state == GameState.PLAYING:
                    self.turn_number += 1 # 이제 turn_number는 전역 틱(Tick) 카운터로 작동
                    
                    # [중요] 시스템 실행 전 이벤트 처리
                    # [중요] 시스템 실행 전 이벤트 처리
                    self.world.event_manager.process_events()
                    
                    # 모든 시스템 순차 실행 (InputSystem은 이미 위에서 입력을 받았으므로 process에서 처리 가능)
                    for system in self.world._systems:
                        if system is not None:
                            system.process()
                    
                    # [중요] 시스템 실행 후 이벤트 처리
                    self.world.event_manager.process_events()

                    # 플레이어 사망 체크
                    player_entity = self.world.get_player_entity()
                    if player_entity:
                        stats = player_entity.get_component(StatsComponent)
                        if stats and stats.current_hp <= 0:
                            game_result = "DEATH"
                            self.is_running = False

                # 3. 주기적 렌더링 (Idle Animation 및 실시간 변화 반영)
                if elapsed_since_frame >= frame_duration:
                    if self.state == GameState.PLAYING:
                        self._render()
                    last_frame_time = current_time
                
                time.sleep(0.002)

        except KeyboardInterrupt:
            game_result = "QUIT"
        finally:
            # 터미널 설정 및 커서 복구
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\033[?25h")
            sys.stdout.write("\033[0m\n")
            sys.stdout.flush()
        
        if game_result != "DEATH":
            self._save_game()
            
        return game_result


    def _get_entity_name(self, entity):
        """엔티티의 이름을 컴포넌트나 ID 기반으로 반환"""
        if entity.entity_id == 1:
            return self.player_name
        
        monster_comp = entity.get_component(MonsterComponent)
        if monster_comp:
            return monster_comp.type_name
            
        shop_comp = entity.get_component(ShopComponent)
        if shop_comp:
            return "상인"
            
        return f"엔티티#{entity.entity_id}"

    def _save_game(self):
        """현재 게임 상태를 저장합니다."""
        from .data_manager import save_game_data
        
        # Engine 상태를 JSON으로 변환 가능한 딕셔너리로 추출 (간소화된 예시)
        # 실제로는 모든 엔티티와 컴포넌트를 저장해야 함
        # 여기서는 Start.py에서 사용하는 형식을 유지하려고 노력함
        
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        # ECS 상태 저장 로직 (ecs.World.to_dict()가 있다면 좋겠지만 일단 수동 구성)
        entities_data = {}
        for e_id, entity in self.world._entities.items():
            comp_data = {}
            for comp_type, comp in entity._components.items():
                if hasattr(comp, 'to_dict'):
                    comp_data[comp_type.__name__] = comp.to_dict()
                else:
                    # to_dict가 없는 경우 기본 속성들만 저장 (간이 구현)
                    # 실제 프로젝트의 컴포넌트 구조에 맞춰야 함
                    comp_data[comp_type.__name__] = {k: v for k, v in vars(comp).items() if not k.startswith('_')}
            entities_data[str(e_id)] = comp_data

        game_state_data = {
            "entities": entities_data,
            "player_specific_data": {
                "name": self.player_name,
                # 필요한 다른 플레이어 데이터...
            },
            "current_level": self.current_level,
            "turn_number": self.turn_number
        }
        
        save_game_data(game_state_data, self.player_name)
                
    def handle_map_transition_event(self, event: MapTransitionEvent):
        """맵 이동 이벤트 처리: 새로운 층 생성"""
        self.current_level = event.target_level
        self.world.event_manager.push(MessageEvent(f"깊은 곳으로 내려갑니다... (던전 {self.current_level}층)"))
        
        # 1. 플레이어 데이터 보존
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        # 데이터 백업
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        level_comp = player_entity.get_component(LevelComponent)
        
        # 2. 월드 초기화 (플레이어 제외 엔티티 삭제 및 시스템 재구성)
        # 단순히 _initialize_world를 다시 호출하는 게 아니라, 맵과 몬스터만 갱신
        self._initialize_world(preserve_player=(stats, inv, level_comp))

    def handle_shop_open_event(self, event: ShopOpenEvent):
        """플레이어가 상인과 충돌 시 상점 모드로 전환"""
        self.state = GameState.SHOP
        self.active_shop_id = event.shopkeeper_id
        self.selected_shop_item_index = 0
        self.shop_category_index = 0 # 기본 '사기' 탭
        self.world.event_manager.push(MessageEvent("상점에 오신 것을 환영합니다!"))

    def _handle_shop_input(self, action: str):
        """상점 상태에서의 입력 처리 (사기/팔기 탭 지원)"""
        shopkeeper = self.world.get_entity(self.active_shop_id)
        player_entity = self.world.get_player_entity()
        if not shopkeeper or not player_entity:
            self.state = GameState.PLAYING
            return

        shop_comp = shopkeeper.get_component(ShopComponent)
        inv_comp = player_entity.get_component(InventoryComponent)
        if not shop_comp or not inv_comp: return

        # 1. 탭 전환 (좌우 키)
        if action in [readchar.key.LEFT, '\x1b[D']:
            self.shop_category_index = (self.shop_category_index - 1) % 2
            self.selected_shop_item_index = 0
            return
        elif action in [readchar.key.RIGHT, '\x1b[C']:
            self.shop_category_index = (self.shop_category_index + 1) % 2
            self.selected_shop_item_index = 0
            return

        # 2. 아이템 목록 필터링
        items_to_display = []
        if self.shop_category_index == 0: # 사기
            items_to_display = shop_comp.items
        else: # 팔기 (인벤토리 아이템 중 장착되지 않은 것)
            # 모든 소지품 중 장착되지 않은 아이템만 추출
            for name, data in inv_comp.items.items():
                is_equipped = any(eq == data['item'] for eq in inv_comp.equipped.values())
                if not is_equipped:
                    # 판매가는 원가의 약 25~50% (여기선 단순 10G 또는 고정가)
                    sell_price = 10 # 기본 판매가
                    items_to_display.append({'item': data['item'], 'price': sell_price, 'qty': data['qty']})

        item_count = len(items_to_display)

        # 3. 위아래 이동 및 실행
        if action in [readchar.key.UP, '\x1b[A']:
             self.selected_shop_item_index = max(0, self.selected_shop_item_index - 1)
        elif action in [readchar.key.DOWN, '\x1b[B']:
             if item_count > 0:
                 self.selected_shop_item_index = min(item_count - 1, self.selected_shop_item_index + 1)
        elif action == readchar.key.ENTER or action == '\r' or action == '\n':
             if items_to_display and 0 <= self.selected_shop_item_index < len(items_to_display):
                 target = items_to_display[self.selected_shop_item_index]
                 if self.shop_category_index == 0:
                     self._buy_item(target)
                 else:
                     self._sell_item(target)

    def _sell_item(self, target_data: Dict):
        """아이템 판매 로직"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        if not stats or not inv: return

        item = target_data['item']
        price = target_data['price']

        # 인벤토리에서 아이템 찾기
        if item.name in inv.items:
            inv.items[item.name]['qty'] -= 1
            stats.gold += price
            self.world.event_manager.push(MessageEvent(f"{item.name}을(를) {price} 골드에 판매했습니다."))
            
            if inv.items[item.name]['qty'] <= 0:
                del inv.items[item.name]
                # 퀵슬롯에서도 제거
                for i in range(len(inv.item_slots)):
                    if inv.item_slots[i] == item.name:
                        inv.item_slots[i] = None
            
            # 인덱스 범위 보정
            self.selected_shop_item_index = max(0, self.selected_shop_item_index - 1)
        else:
            self.world.event_manager.push(MessageEvent("판매할 아이템이 없습니다."))

    def _buy_item(self, shop_item: Dict):
        """아이템 구매 로직"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        if not stats or not inv: return

        item = shop_item['item']
        price = shop_item['price']

        if stats.gold >= price:
            stats.gold -= price
            # 인벤토리에 추가
            if item.name in inv.items:
                inv.items[item.name]['qty'] += 1
            else:
                inv.items[item.name] = {'item': item, 'qty': 1}
            self.world.event_manager.push(MessageEvent(f"{item.name}을(를) {price} 골드에 구매했습니다!"))
        else:
            self.world.event_manager.push(MessageEvent("골드가 부족합니다!"))

    def _handle_inventory_input(self, action):
        """인벤토리 상태에서의 입력 처리"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        from .components import InventoryComponent
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 스턴 상태 확인
        stun = player_entity.get_component(StunComponent)
        if stun:
            # 인벤토리 보기는 가능 (action 'i' 등은 상위에서 처리됨)
            # 여기서는 아이템 사용/버리기 등 주요 액션이 일어나는 시점에 체크
            if action not in [readchar.key.UP, readchar.key.DOWN, readchar.key.LEFT, readchar.key.RIGHT, '\x1b[A', '\x1b[B', '\x1b[D', '\x1b[C', 'i', 'I']:
                self.world.event_manager.push(MessageEvent("몸이 움직이지 않아 아이템을 조작할 수 없습니다!"))
                return

        # 1. 현재 카테고리에 해당하는 아이템 필터링
        filtered_items = []
        if self.inventory_category_index == 0: # 아이템 (소모품/스킬북)
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type in ['CONSUMABLE', 'SKILLBOOK']]
        elif self.inventory_category_index == 1: # 장비
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type in ['WEAPON', 'ARMOR']]
        elif self.inventory_category_index == 2: # 스크롤
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type == 'SCROLL']
        elif self.inventory_category_index == 3: # 스킬
            filtered_items = [(s, {'item': type('obj', (object,), {'name': s})(), 'qty': 1}) for s in inv.skills]

        item_count = len(filtered_items)

        # 2. 내비게이션 처리
        if action in [readchar.key.UP, '\x1b[A']:
             self.selected_item_index = max(0, self.selected_item_index - 1)
        elif action in [readchar.key.DOWN, '\x1b[B']:
             if item_count > 0:
                 self.selected_item_index = min(item_count - 1, self.selected_item_index + 1)
        elif action in [readchar.key.LEFT, '\x1b[D']:
             self.inventory_category_index = (self.inventory_category_index - 1) % 4
             self.selected_item_index = 0
        elif action in [readchar.key.RIGHT, '\x1b[C']:
             self.inventory_category_index = (self.inventory_category_index + 1) % 4
             self.selected_item_index = 0
        elif action == readchar.key.ENTER or action == '\r' or action == '\n' or action == 'e' or action == 'E':
             if filtered_items and 0 <= self.selected_item_index < len(filtered_items):
                 item_id, item_data = filtered_items[self.selected_item_index]
                 # E키 또는 ENTER 입력 시 행동 결정
                 if self.inventory_category_index == 0: # 아이템 (소모품)
                     if action == 'e' or action == 'E':
                         self._assign_quick_slot(item_data['item'].name, "ITEM")
                     else:
                         self._use_item(item_id, item_data) # ENTER는 즉시 사용
                 elif self.inventory_category_index == 1: # 장비
                     self._equip_selected_item(item_data)
                 elif self.inventory_category_index == 2: # 스크롤 (아이템 슬롯에 등록 가능하게)
                     if action == 'e' or action == 'E':
                         self._assign_quick_slot(item_data['item'].name, "ITEM")
                     else:
                         self._use_item(item_id, item_data) 
                 elif self.inventory_category_index == 3: # 스킬
                     if action == 'e' or action == 'E' or action == readchar.key.ENTER or action == '\r' or action == '\n':
                         # E키 또는 ENTER 입력 시 퀵슬롯 등록/해제 (Toggle)
                         self._assign_quick_slot(item_id, "SKILL")
                     elif action == 'x' or action == 'X':
                         # X키 입력 시 스킬 잊기
                         self._forget_skill(item_id)

    def _assign_quick_slot(self, name, category):
        """이름을 기반으로 아이템/스킬을 적절한 퀵슬롯에 등록하거나 해제 (Toggle)"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 대상 슬롯 리스트 결정
        slots = inv.item_slots if category == "ITEM" else inv.skill_slots
        slot_label = "아이템 퀵슬롯" if category == "ITEM" else "스킬 퀵슬롯"
        offset = 0 if category == "ITEM" else 5

        # 이미 등록되어 있는지 확인
        if name in slots:
            idx = slots.index(name)
            slots[idx] = None
            self.world.event_manager.push(MessageEvent(f"{name}을(를) {slot_label} {idx+1+offset}번에서 해제했습니다."))
            return

        # 비어있는 슬롯 찾기
        for i in range(len(slots)):
            if slots[i] is None:
                slots[i] = name
                self.world.event_manager.push(MessageEvent(f"{name}을(를) {slot_label} {i+1+offset}번에 등록했습니다."))
                return
        
        self.world.event_manager.push(MessageEvent(f"{slot_label}이 가득 찼습니다!"))

    def _trigger_quick_slot(self, key):
        """단축키(1~0)를 눌러 퀵슬롯 아이템/스킬 실행"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 스턴 상태 확인
        stun = player_entity.get_component(StunComponent)
        if stun:
            self.world.event_manager.push(MessageEvent("몸이 움직이지 않아 퀵슬롯을 사용할 수 없습니다!"))
            return

        try:
            num = int(key)
        except ValueError:
            return False
        if 1 <= num <= 5: # 아이템 슬롯 (1~5)
            idx = num - 1
            item_name = inv.item_slots[idx]
            if item_name:
                # 인벤토리에서 아이템 찾기
                found_id = None
                found_data = None
                for id, data in inv.items.items():
                    if data['item'].name == item_name:
                        found_id = id
                        found_data = data
                        break
                
                if found_data:
                    self._use_item(found_id, found_data)
                    return True # 턴 소모
                else:
                    self.world.event_manager.push(MessageEvent(f"{item_name}을(를) 인벤토리에서 찾을 수 없습니다."))
                    return False
            else:
                self.world.event_manager.push(MessageEvent(f"{num}번 퀵슬롯이 비어있습니다."))
                return False
        
        else: # 스킬 슬롯 (6,7,8,9,0)
            # 0번은 10번 슬롯 (index 4)
            idx = 4 if num == 0 else num - 6
            skill_name = inv.skill_slots[idx]
            if skill_name:
                skill = self.skill_defs.get(skill_name)
                if not skill:
                    # 만약 DB에 없다면 (샌드박스 등의 하드코딩된 이름일 경우)
                    # 샌드박스용 더미 객체 생성 혹은 로그 출력
                    self.world.event_manager.push(MessageEvent(f"{skill_name} 스킬 데이터가 없습니다."))
                    return

                # 스킬 타입에 따른 처리
                if skill.subtype in ["PROJECTILE", "AREA"] and skill.range > 0:
                    # 방향 선택 모드 진입
                    self.is_attack_mode = True
                    self.active_skill_name = skill_name
                    self.world.event_manager.push(MessageEvent(f"[{skill_name}] 방향을 선택하세요..."))
                    return False # 방향 선택 모드 자체는 턴 소모 안함
                else:
                    # 즉시 발동형 (SELF 등)
                    from .events import SkillUseEvent
                    self.world.event_manager.push(SkillUseEvent(attacker_id=player_entity.entity_id, skill_name=skill_name, dx=0, dy=0))
                    return True # 턴 소모
            else:
                slot_num = 10 if num == 0 else num
                self.world.event_manager.push(MessageEvent(f"{slot_num}번 스킬 슬롯이 비어있습니다."))
                return False
        return False

    def _use_item(self, item_id, item_data):
        """소모품 아이템 사용"""
        item = item_data['item']
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        
        if not stats or not inv: return

        # 효과 적용
        # 레벨 제한 확인
        level_comp = player_entity.get_component(LevelComponent)
        if level_comp and item.required_level > level_comp.level:
            self.world.event_manager.push(MessageEvent(f"레벨이 부족하여 사용할 수 없습니다. (필요: Lv.{item.required_level})"))
            return

        old_hp = stats.current_hp
        old_mp = stats.current_mp
        
        msg = f"{item.name}을(를) 사용했습니다."

        if item.type == "SKILLBOOK":
            skill_to_learn = item.name.replace(" 스킬북", "").strip()
            # 레벨 정보 제거 (예: 파이어볼 Lv1 -> 파이어볼)
            import re
            skill_base_name = re.sub(r' Lv\d+', '', skill_to_learn)
            
            if skill_base_name in inv.skills:
                # 이미 배운 스킬이면 레벨업
                old_level = inv.skill_levels.get(skill_base_name, 1)
                new_level = old_level + 1
                inv.skill_levels[skill_base_name] = new_level
                msg = f"'{skill_base_name}' 스킬의 숙련도가 높아졌습니다! (Lv.{old_level} -> Lv.{new_level})"
            else:
                # 새로 배우는 스킬
                inv.skills.append(skill_base_name)
                inv.skill_levels[skill_base_name] = 1
                msg = f"{item.name}을(를) 읽고 '{skill_base_name}' 스킬을 터득했습니다!"
        else:
            if item.hp_effect != 0:
                stats.current_hp = min(stats.max_hp, stats.current_hp + item.hp_effect)
            if item.mp_effect != 0:
                stats.current_mp = min(stats.max_mp, stats.current_mp + item.mp_effect)
            
            # [VISION_UP] 횃불 효과
            if "VISION_UP" in item.flags:
                stats.vision_range = 15 # 시야 반경 대폭 증가
                # 30초 후 만료를 위해 타이머 대신 TimeSystem 연동 (여기서는 단순히 플래그만 추가하고 TimeSystem에서 처리)
                if "VISION_UP" not in stats.flags:
                    stats.flags.add("VISION_UP")
                    # 만료 시간을 StatsComponent에 저장 (초 단위)
                    stats.vision_expires_at = time.time() + 30.0
                
                # [추가] 숨겨진 아이템 감지 효과
                stats.sees_hidden = True
                stats.sees_hidden_expires_at = time.time() + 30.0
                
                msg += " 어둠이 걷히며 숨겨진 기운들이 느껴집니다!"
                
            # [TELEPORT] 순간 이동 (스크롤 용)
            if "TELEPORT" in item.flags:
                valid_tiles = []
                for y in range(self.dungeon_map.height):
                    for x in range(self.dungeon_map.width):
                        if self.dungeon_map.map_data[y][x] == '.': # FLOOR
                            valid_tiles.append((x, y))
                if valid_tiles:
                    tx, ty = random.choice(valid_tiles)
                    pos = player_entity.get_component(PositionComponent)
                    if pos:
                        pos.x, pos.y = tx, ty
                        msg = f"{item.name}의 힘으로 공간을 뛰어넘었습니다!"
                
            # [FIRE_EXPLOSION] 화염 폭발 (반경 2, 스플래쉬 로직 활용)
            if "FIRE_EXPLOSION" in item.flags:
                pos = player_entity.get_component(PositionComponent)
                if pos:
                    combat_sys = self.world.get_system(CombatSystem)
                    if combat_sys:
                        temp_skill = type('obj', (object,), {
                            'name': '화염 스크롤 폭발', 'damage': 30, 'range': 1, 'element': '불', 'flags': {'EXPLOSION'}
                        })
                        if hasattr(combat_sys, '_handle_explosion'):
                            combat_sys._handle_explosion(player_entity, pos.x, pos.y, temp_skill)
                        msg = f"{item.name}이(가) 폭발하며 주변을 불태웁니다!"

            # [MAGIC_MAPPING] 지도 제작
            if "MAGIC_MAPPING" in item.flags:
                if self.dungeon_map:
                    for y in range(self.dungeon_map.height):
                        for x in range(self.dungeon_map.width):
                            if self.dungeon_map.map_data[y][x] != ' ':
                                self.dungeon_map.visited.add((x, y))
                    msg = f"{item.name}을 사용하자 던전의 전역 지도가 밝아집니다."
                
            # [RECALL] 귀환 (계단 이동)
            if "RECALL" in item.flags:
                if self.dungeon_map:
                    pos = player_entity.get_component(PositionComponent)
                    if pos:
                        pos.x, pos.y = self.dungeon_map.exit_x, self.dungeon_map.exit_y
                        msg = f"{item.name}의 마법으로 다음 층으로 가는 계단 앞에 소환되었습니다!"
                
            hp_recovered = stats.current_hp - old_hp
            if hp_recovered > 0:
                msg += f" (HP {hp_recovered} 회복)"
            
        self.world.event_manager.push(MessageEvent(msg))
        
        # 수량 감소
        item_data['qty'] -= 1
        if item_data['qty'] <= 0:
            del inv.items[item_id]
            # 퀵슬롯에서도 제거
            for i in range(len(inv.item_slots)):
                if inv.item_slots[i] == item.name:
                    inv.item_slots[i] = None
            
            # 인덱스 보정
            self.selected_item_index = max(0, self.selected_item_index - 1)

    def _forget_skill(self, skill_name):
        """배운 스킬을 잊어버림"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        if skill_name in inv.skills:
            inv.skills.remove(skill_name)
            # 퀵슬롯에서도 제거
            for i in range(len(inv.skill_slots)):
                if inv.skill_slots[i] == skill_name:
                    inv.skill_slots[i] = None
            
            self.world.event_manager.push(MessageEvent(f"'{skill_name}' 스킬을 잊었습니다."))
            # 인덱스 보정
            self.selected_item_index = max(0, self.selected_item_index - 1)

    def _equip_selected_item(self, item_data):
        """선택된 아이템을 조건에 맞춰 장착하거나 해제 (Toggle)"""
        item = item_data['item']
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 1. 이미 장착 중인지 확인 (해제 로직)
        already_slot = None
        for slot, eq_item in inv.equipped.items():
            if eq_item == item:
                already_slot = slot
                break
        
        if already_slot:
            inv.equipped[already_slot] = None
            # 양손 무기였을 경우 손2도 해제
            if already_slot == "손1" and inv.equipped.get("손2") == "(양손 점유)":
                inv.equipped["손2"] = None
            
            self.world.event_manager.push(MessageEvent(f"{item.name}의 장착을 해제했습니다."))
            self._recalculate_stats()
            return

        # 2. 장착 로직 (레벨 제한 확인 추가)
        level_comp = player_entity.get_component(LevelComponent)
        if level_comp and item.required_level > level_comp.level:
            self.world.event_manager.push(MessageEvent(f"레벨이 부족하여 장착할 수 없습니다. (필요: Lv.{item.required_level})"))
            return

        inv_comp = player_entity.get_component(InventoryComponent)
        if item.type == 'WEAPON':
            if item.hand_type == 2: # 양손 무기
                inv.equipped["손1"] = item
                inv.equipped["손2"] = "(양손 점유)"
            else: # 한손 무기
                if inv.equipped.get("손2") == "(양손 점유)":
                    inv.equipped["손2"] = None
                
                if not inv.equipped.get("손1"):
                    inv.equipped["손1"] = item
                elif not inv.equipped.get("손2"):
                    inv.equipped["손2"] = item
                else:
                    inv.equipped["손1"] = item
        
        elif item.type == 'SHIELD':
            if inv.equipped.get("손2") == "(양손 점유)":
                inv.equipped["손1"] = None
            inv.equipped["손2"] = item
            
        elif item.type == 'ARMOR':
            inv.equipped["몸통"] = item
        elif item.type == 'ACCESSORY':
            if not inv.equipped.get("액세서리1"):
                inv.equipped["액세서리1"] = item
            elif not inv.equipped.get("액세서리2"):
                inv.equipped["액세서리2"] = item
            else:
                inv.equipped["액세서리1"] = item # 둘 다 있으면 첫 번째 교체
        # TODO: 머리, 장갑, 신발 등 타입 확장
        
        # 장착 메시지 추가
        self.world.event_manager.push(MessageEvent(f"{item.name}을(를) 장착했습니다."))
        
        # 능력치 재계산
        self._recalculate_stats()

    def _recalculate_stats(self):
        """장착된 아이템을 기반으로 플레이어 능력치 재계산"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        if not stats or not inv: return
        
        # 기본 능력치로 초기화
        stats.attack = stats.base_attack
        stats.defense = stats.base_defense
        stats.weapon_range = 1 # 기본 사거리 (Bump)
        if hasattr(stats, 'base_flags'):
            stats.flags = stats.base_flags.copy()
        
        # 보너스 합산
        for slot, item in inv.equipped.items():
            # ItemDefinition 객체인 경우에만 스탯 합산
            from .data_manager import ItemDefinition
            if isinstance(item, ItemDefinition):
                stats.attack += item.attack
                stats.defense += item.defense
                
                # [수정] 플래그 합산 로직 추가
                if hasattr(item, 'flags'):
                    stats.flags.update(item.flags)
                
                # 주무기(손1)의 사거리를 캐릭터 사거리로 설정
                if slot == "손1":
                    stats.weapon_range = item.attack_range

    def _render(self):
        """World 상태를 기반으로 Renderer를 사용하여 화면을 그립니다."""
        self.renderer.clear_buffer()
        
        RIGHT_SIDEBAR_X = 81
        SIDEBAR_WIDTH = self.renderer.width - RIGHT_SIDEBAR_X
        # 한글 너비 문제를 방지하기 위해 맵 가시 영역을 약간 줄임 (안전 마진 확보)
        MAP_VIEW_WIDTH = 78 
        MAP_VIEW_HEIGHT = self.renderer.height - 12 # 하단 스탯 창 공간 확보
        
        # 0. 구분선 복구 (레이아웃 틀어짐 방지 가이드 역할)
        for y in range(self.renderer.height):
            self.renderer.draw_char(80, y, "|", "dark_grey")
        
        player_entity = self.world.get_player_entity()
        player_pos = player_entity.get_component(PositionComponent) if player_entity else None
        
        # 카메라 오프셋 계산 (플레이어를 중앙에)
        if player_pos:
            camera_x = max(0, min(player_pos.x - MAP_VIEW_WIDTH // 2, 120 - MAP_VIEW_WIDTH))
            camera_y = max(0, min(player_pos.y - MAP_VIEW_HEIGHT // 2, 60 - MAP_VIEW_HEIGHT))
        else:
            camera_x, camera_y = 0, 0

        # 0. 전장의 안개 업데이트 (시야 반경 8)
        player_entity = self.world.get_player_entity()
        if player_entity and self.dungeon_map:
            p_pos = player_entity.get_component(PositionComponent)
            if p_pos:
                # 시야 밝히기
                stats = player_entity.get_component(StatsComponent)
                vision_range = stats.vision_range if stats else 5
                self.dungeon_map.reveal_tiles(p_pos.x, p_pos.y, radius=vision_range)

        # 1. 맵 렌더링 (Left Top - Viewport 적용)
        map_comp_list = self.world.get_entities_with_components([MapComponent])
        map_height = 0
        if map_comp_list:
            map_comp = map_comp_list[0].get_component(MapComponent)
            map_height = MAP_VIEW_HEIGHT
            
            for screen_y in range(MAP_VIEW_HEIGHT):
                world_y = camera_y + screen_y
                if world_y >= map_comp.height: break
                
                for screen_x in range(MAP_VIEW_WIDTH):
                    world_x = camera_x + screen_x
                    if world_x >= map_comp.width: break
                    
                    # DungeonMap 기능을 사용하여 타일 문자 결정 (안개 처리됨)
                    char = self.dungeon_map.get_tile_for_display(world_x, world_y)
                    
                    # 안개 지역(미방문)인 경우 공백 처리
                    if self.dungeon_map.fog_enabled and (world_x, world_y) not in self.dungeon_map.visited:
                        self.renderer.draw_char(screen_x, screen_y, " ", "white")
                        continue

                    # 맵 시인성 개선: 바닥(.)과 인접하지 않은 벽(#)은 공백으로 처리
                    if char == "#":
                        is_visible_wall = False
                        # 8방향 탐색 (안개 너머 벽까지 계산되지 않도록 방문한 타일만 고려)
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = world_x + dx, world_y + dy
                                if 0 <= nx < map_comp.width and 0 <= ny < map_comp.height:
                                    if map_comp.tiles[ny][nx] == ".":
                                        is_visible_wall = True
                                        break
                            if is_visible_wall: break
                        
                        render_char = "#" if is_visible_wall else " "
                        color = "brown"
                    else:
                        render_char = char
                        color = "dark_grey" if char == "." else "brown"
                        if char == ">" or char == "<": color = "cyan"
                    
                    self.renderer.draw_char(screen_x, screen_y, render_char, color)

        # 구분선 (Horizontal) - 맵과 스탯 창 사이
        status_start_y = map_height + 1
        self.renderer.draw_text(0, status_start_y, "-" * 80, "dark_grey")

        # 2. 엔티티 렌더링 (플레이어, 몬스터 등 - 카메라 오프셋 적용)
        renderable_entities = self.world.get_entities_with_components([PositionComponent, RenderComponent])
        for entity in renderable_entities:
            pos = entity.get_component(PositionComponent)
            render = entity.get_component(RenderComponent)
            
            # 맵 컴포넌트 엔티티는 제외
            if entity.get_component(MapComponent):
                continue
            
            screen_x = pos.x - camera_x
            screen_y = pos.y - camera_y
            
            if 0 <= screen_x < MAP_VIEW_WIDTH and 0 <= screen_y < MAP_VIEW_HEIGHT:
                # 전장의 안개: 가 본 적 없는 위치의 엔티티는 숨김
                if self.dungeon_map and self.dungeon_map.fog_enabled and (pos.x, pos.y) not in self.dungeon_map.visited:
                    continue

                # 숨겨진 아이템(HiddenComponent) 처리
                hidden = entity.get_component(HiddenComponent)
                player_stats = player_entity.get_component(StatsComponent) if player_entity else None
                if hidden:
                    if not player_stats or not player_stats.sees_hidden:
                        continue # 횃불 효과 없으면 안보임
                    # 깜빡임 효과 (0.5초 주기로 ON/OFF)
                    if hidden.blink and int(time.time() * 4) % 2 == 0:
                        continue

                char = render.char
                color = render.color

                # 피격 피드백(Hit Flash) 처리
                if entity.has_component(HitFlashComponent):
                    color = "white_bg"
                
                # 미믹(MimicComponent) 의태 처리
                mimic = entity.get_component(MimicComponent)
                if mimic and mimic.is_disguised:
                    char = '[' # 상자 기호
                    color = "brown"
                
                # 함정(TrapComponent) 렌더링
                trap = entity.get_component(TrapComponent)
                if trap:
                    if not trap.visible and not trap.is_triggered:
                        # 숨겨진 함정은 횃불 효과가 있을 때만 흐릿하게 보임
                        if player_stats and player_stats.sees_hidden:
                             char = '^'
                             color = "dark_grey"
                        else:
                             continue
                    else:
                        char = '^'
                        color = "red" if trap.is_triggered else "yellow"

                self.renderer.draw_char(screen_x, screen_y, char, color)
        
        # 2-1. 오라/특수 효과 렌더링 (휘몰아치는 연출)
        aura_entities = self.world.get_entities_with_components([PositionComponent, SkillEffectComponent])
        for entity in aura_entities:
            pos = entity.get_component(PositionComponent)
            effect = entity.get_component(SkillEffectComponent)
            
            # 카메라 가시 영역 체크
            screen_x = pos.x - camera_x
            screen_y = pos.y - camera_y
            
            # 깜빡임 및 회전 문자 결정 (실시간 시간 기반)
            anim_tick = int(time.time() * 10) # 초당 10프레임 수준의 애니메이션
            
            chars = ["/", "-", "\\", "|"]
            current_char = chars[anim_tick % len(chars)]
            color = "cyan" if anim_tick % 2 == 0 else "blue"
            
            # 주변 8방향 렌더링
            for dy in range(-effect.radius, effect.radius + 1):
                for dx in range(-effect.radius, effect.radius + 1):
                    if dx == 0 and dy == 0: continue
                    sx, sy = screen_x + dx, screen_y + dy
                    if 0 <= sx < MAP_VIEW_WIDTH and 0 <= sy < MAP_VIEW_HEIGHT:
                        # 맵 타일이 벽이 아닌 경우에만 렌더링 (옵션)
                        # 여기서는 단순하게 그 위에 덧그림
                        self.renderer.draw_char(sx, sy, current_char, color)

        # 3. 캐릭터 스탯 렌더링 (Left Bottom - below Map)
        status_start_y = map_height + 1
        current_y = status_start_y + 1
        player_entity = self.world.get_player_entity()
        
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            level_comp = player_entity.get_component(LevelComponent)
            
            if stats:
                # Name
                self.renderer.draw_text(2, current_y, f"NAME: {self.player_name}", "gold")
                
                # HP, MP, STM Bar 스타일
                hp_str = f"HP  : {stats.current_hp:3}/{stats.max_hp:3}"
                mp_str = f"MP  : {stats.current_mp:3}/{stats.max_mp:3}"
                stm_str = f"STM : {int(stats.current_stamina):3}/{int(stats.max_stamina):3}"
                
                self.renderer.draw_text(20, current_y, hp_str, "red")
                self.renderer.draw_text(40, current_y, mp_str, "blue")
                self.renderer.draw_text(60, current_y, stm_str, "green")
                current_y += 1
                
                # Level info
                if level_comp:
                    lv_str = f"LV  : {level_comp.level}"
                    exp_str = f"EXP : {level_comp.exp}/{level_comp.exp_to_next}"
                    job_str = f"JOB : {level_comp.job}"
                    self.renderer.draw_text(2, current_y, f"{lv_str:<10} {job_str:<15} {exp_str}", "white")
                current_y += 1
                
                # Stats
                atk_str = f"ATK : {stats.attack}"
                def_str = f"DEF : {stats.defense}"
                rng_str = f"RNG : {stats.weapon_range} (LINE)"
                self.renderer.draw_text(2, current_y, f"{atk_str:<10} {def_str:<10} {rng_str}", "white")


        # 4. 오른쪽 사이드바 (Right Sidebar)
        # 4-1. 로그 (Logs)
        log_start_y = 0
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, log_start_y, "[ LOGS ]", "gold")
        
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            # 최근 10개 메시지 표시 (영역 확장)
            recent_messages = message_comp.messages[-10:]
            for i, msg in enumerate(recent_messages):
                # 너비 제한으로 자르기 (한글 너비 고려하여 보수적으로)
                wrap_width = SIDEBAR_WIDTH - 6
                truncated_msg = (msg[:wrap_width] + '..') if len(msg) > wrap_width else msg
                
                # 메시지 내용에 따른 색상 구분
                msg_color = "white"
                if "데미지를 입었다" in msg:
                    msg_color = "red"
                elif "쓰러졌습니다" in msg:
                    msg_color = "gold"
                elif "만났습니다" in msg:
                    msg_color = "yellow"
                
                self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, log_start_y + 1 + i, f"> {truncated_msg}", msg_color)

        # 4-2. 장비 (Equipment)
        eq_start_y = 12 # 로그(10줄)와 겹치지 않도록 시작점 조정
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, eq_start_y, "[ EQUIP ]", "gold")
        eq_y = eq_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp:
                slots = ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]
                for i, slot in enumerate(slots):
                    if eq_y >= 21: break # 사이드바 높이 제한 (스크롤/스킬 영역 확보)
                    item = inv_comp.equipped.get(slot)
                    
                    # 아이템이 ItemDefinition 객체이면 이름을 가져오고, 아니면 그대로 사용 (---- 혹은 양손점유)
                    from .data_manager import ItemDefinition
                    if isinstance(item, ItemDefinition):
                        item_display = item.name
                    else:
                        item_display = item if item else "----"
                        
                    color = "white"
                    if item_display == "(양손 점유)":
                        color = "dark_grey"
                    
                    # 슬롯명과 아이템명을 정돈해서 표시
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, eq_y, f"{slot:<5}: {item_display}", color)
                    eq_y += 1

        # 4-3. 퀵슬롯 (Item Slots 1-5)
        qs_start_y = 21
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, qs_start_y, "[ QUICK SLOTS ]", "gold")
        qs_y = qs_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'item_slots'):
                for i, item in enumerate(inv_comp.item_slots):
                    item_name = item if item else "----"
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, qs_y + i, f"{i+1}: {item_name}", "white")
        
        # 4-4. 스킬 (Skill Slots 6-0)
        skill_start_y = qs_start_y + 7
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y, "[ SKILLS ]", "gold")
        sk_y = skill_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'skill_slots'):
                for i, item in enumerate(inv_comp.skill_slots):
                    item_name = item if item else "----"
                    num = 0 if i == 4 else i + 6
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, sk_y + i, f"{num}: {item_name}", "white")

        # 5. 입력 가이드 (Bottom fixed)
        guide_y = self.renderer.height - 1
        if self.is_attack_mode:
            self.renderer.draw_text(0, guide_y, " [ATTACK] Arrows: Select Dir | [Space] Cancel ", "red")
        else:
            self.renderer.draw_text(0, guide_y, " [MOVE] Arrows | [.] Wait | [I] Inventory | [Space] Attack Mode | [Q] Quit", "green")
        
        # 6. 인벤토리/상점 팝업 렌더링
        if self.state == GameState.INVENTORY:
            self._render_inventory_popup()
        elif self.state == GameState.SHOP:
            self._render_shop_popup()

        self.renderer.render()

    def _render_inventory_popup(self):
        """항목 목록을 보여주는 중앙 팝업창 렌더링 (카테고리 분류 포함)"""
        MAP_WIDTH = 80
        POPUP_WIDTH = 60
        POPUP_HEIGHT = 20
        # 맵 영역(80) 내에 중앙 정렬
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. 배경 및 테두리 그리기 (불투명 처리 보강)
        for y in range(start_y, start_y + POPUP_HEIGHT):
            for x in range(start_x, start_x + POPUP_WIDTH):
                if y == start_y or y == start_y + POPUP_HEIGHT - 1:
                    char = "-"
                elif x == start_x or x == start_x + POPUP_WIDTH - 1:
                    char = "|"
                else:
                    char = " "
                
                # 배경색을 어둡게 지정하여 뒤쪽이 보이지 않도록 함 (다만 현재 렌러더엔 배경색 기능이 없으므로 공백으로 확실히 채움)
                self.renderer.draw_char(x, y, char, "white")
                
        # 2. 카테고리 탭 표시
        categories = ["아이템", "장비", "스크롤", "스킬"]
        tab_x = start_x + 2
        for i, cat in enumerate(categories):
            color = "yellow" if i == self.inventory_category_index else "dark_grey"
            # 선택된 탭은 대괄호 표시
            text = f"[{cat}]" if i == self.inventory_category_index else f" {cat} "
            self.renderer.draw_text(tab_x, start_y + 1, text, color)
            tab_x += len(text) + 2
            
        # 2.1 플레이어 골드 표시 (인벤토리 상단 우측)
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats:
                gold_text = f" {stats.gold} G "
                self.renderer.draw_text(start_x + POPUP_WIDTH - len(gold_text) - 2, start_y + 1, gold_text, "yellow")
        
        # 3. 구분선
        self.renderer.draw_text(start_x + 1, start_y + 2, "-" * (POPUP_WIDTH - 2), "dark_grey")
        
        # 4. 아이템 목록 필터링 및 표시
        player_entity = self.world.get_player_entity()
        if player_entity:
             from .components import InventoryComponent
             inv_comp = player_entity.get_component(InventoryComponent)
             
             if inv_comp:
                 # 카테고리별 필터링
                 filtered_items = []
                 if self.inventory_category_index == 0: # 아이템
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type in ['CONSUMABLE', 'SKILLBOOK']]
                 elif self.inventory_category_index == 1: # 장비
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type in ['WEAPON', 'ARMOR']]
                 elif self.inventory_category_index == 2: # 스크롤
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type == 'SCROLL']
                 elif self.inventory_category_index == 3: # 스킬
                     filtered_items = [(s, {'item': type('obj', (object,), {'name': s})(), 'qty': 1}) for s in inv_comp.skills]

                 if not filtered_items:
                     self.renderer.draw_text(start_x + 2, start_y + 4, "  (비어 있음)", "dark_grey")
                 else:
                     current_y = start_y + 4
                     for idx, (item_id, item_data) in enumerate(filtered_items):
                         if current_y >= start_y + POPUP_HEIGHT - 2: break
                         
                         item = item_data['item']
                         name = item.name
                         qty = item_data['qty']
                         prefix = "> " if idx == self.selected_item_index else "  "
                         color = "green" if idx == self.selected_item_index else "white"
                         
                         _s = ""
                         if any(eq == item for eq in inv_comp.equipped.values()): _s += " [E]"
                         if name in inv_comp.item_slots or name in inv_comp.skill_slots: _s += " [Q]"
                         
                         self.renderer.draw_text(start_x + 2, current_y, f"{prefix}{name} x{qty}{_s}", color)
                         current_y += 1

        # 5. 하단 도움말
        if self.inventory_category_index == 3:
            help_text = "[←/→] 탭  [↑/↓] 선택  [ENTER/E] 등록/해제  [X] 스킬 잊기  [B] 닫기"
        else:
            help_text = "[←/→] 탭  [↑/↓] 선택  [E] 퀵슬롯 등록  [ENTER] 사용/장착  [B] 닫기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(help_text)) // 2, start_y + POPUP_HEIGHT - 2, help_text, "dark_grey")

    def _render_shop_popup(self):
        """상점 UI 팝업 렌더링"""
        MAP_WIDTH = 80
        POPUP_WIDTH = 60
        POPUP_HEIGHT = 20
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. 배경 및 테두리 (골드 색상 테두리)
        for y in range(start_y, start_y + POPUP_HEIGHT):
            for x in range(start_x, start_x + POPUP_WIDTH):
                if y == start_y or y == start_y + POPUP_HEIGHT - 1:
                    char = "="
                elif x == start_x or x == start_x + POPUP_WIDTH - 1:
                    char = "|"
                else:
                    char = " "
                self.renderer.draw_char(x, y, char, "gold")
        
        # 2. 탭 구성 (사기 / 팔기)
        categories = ["사기 (BUY)", "팔기 (SELL)"]
        tab_x = start_x + 4
        for i, cat in enumerate(categories):
            color = "yellow" if i == self.shop_category_index else "dark_grey"
            text = f"[{cat}]" if i == self.shop_category_index else f" {cat} "
            self.renderer.draw_text(tab_x, start_y + 1, text, color)
            tab_x += len(text) + 8
        
        # 3. 플레이어 골드 표시
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats:
                gold_text = f" 소지 골드: {stats.gold} G "
                self.renderer.draw_text(start_x + POPUP_WIDTH - len(gold_text) - 2, start_y + 3, gold_text, "yellow")
        
        self.renderer.draw_text(start_x + 2, start_y + 4, "-" * (POPUP_WIDTH - 4), "dark_grey")
        
        # 4. 물품 목록 표시
        items_to_display = []
        if self.shop_category_index == 0: # 사기
            shopkeeper = self.world.get_entity(self.active_shop_id)
            if shopkeeper:
                shop_comp = shopkeeper.get_component(ShopComponent)
                if shop_comp: items_to_display = shop_comp.items
        else: # 팔기
            if player_entity:
                inv_comp = player_entity.get_component(InventoryComponent)
                if inv_comp:
                    for name, data in inv_comp.items.items():
                        is_equipped = any(eq == data['item'] for eq in inv_comp.equipped.values())
                        if not is_equipped:
                            items_to_display.append({'item': data['item'], 'price': 10, 'qty': data['qty']})

        if not items_to_display:
            self.renderer.draw_text(start_x + 2, start_y + 6, "  (거래 가능한 물품이 없습니다)", "dark_grey")
        else:
            for i, entry in enumerate(items_to_display):
                item = entry['item']
                price = entry['price']
                qty = entry.get('qty', 1)
                
                item_y = start_y + 5 + i
                if item_y >= start_y + POPUP_HEIGHT - 2: break
                
                prefix = "> " if i == self.selected_shop_item_index else "  "
                color = "green" if i == self.selected_shop_item_index else "white"
                
                # 수량 표시 (팔기 탭에서 유용)
                qty_str = f" x{qty}" if self.shop_category_index == 1 else ""
                name_text = f"{prefix}{item.name}{qty_str}"
                self.renderer.draw_text(start_x + 2, item_y, name_text, color)
                
                price_text = f"{price:>5} G"
                self.renderer.draw_text(start_x + POPUP_WIDTH - 12, item_y, price_text, color)
        
        # 5. 하단 도움말
        guide_text = "[←/→] 탭 전환  [↑/↓] 선택  [ENTER] " + ("구매" if self.shop_category_index == 0 else "판매") + "  [Q/ESC] 나가기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(guide_text)) // 2, start_y + POPUP_HEIGHT - 2, guide_text, "dark_grey")

if __name__ == '__main__':
    engine = Engine()
    engine.run()
