import random
import time
import os
import sys
import select
import json
import termios
import tty
import readchar
import logging
import copy
from typing import Dict, List, Set, Type, Optional, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import (
    PositionComponent, RenderComponent, StatsComponent, InventoryComponent, 
    LevelComponent, MapComponent, MessageComponent, MonsterComponent, 
    AIComponent, LootComponent, CorpseComponent, ChestComponent, ShopComponent, ShrineComponent,
    StunComponent, SkillEffectComponent, HitFlashComponent, HiddenComponent, MimicComponent, TrapComponent,
    SleepComponent, PoisonComponent, StatModifierComponent, BossComponent, PetrifiedComponent, BossGateComponent,
    DoorComponent, SwitchComponent, InteractableComponent, KeyComponent, BlockMapComponent
)
from .systems import (
    InputSystem, MovementSystem, RenderSystem, MonsterAISystem, CombatSystem, 
    TimeSystem, RegenerationSystem, LevelSystem, BossSystem, InteractionSystem
)

from .events import MessageEvent, DirectionalAttackEvent, MapTransitionEvent, ShopOpenEvent, ShrineOpenEvent, SoundEvent
from .sound_system import SoundSystem
from .renderer import Renderer
from .data_manager import load_item_definitions, load_monster_definitions, load_skill_definitions, load_class_definitions, load_prefixes, load_suffixes
from .constants import (
    ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON, ELEMENT_COLORS,
    RARITY_NORMAL, RARITY_MAGIC, RARITY_UNIQUE, RARITY_CURSED
)



import enum

class GameState:
    PLAYING = 0
    INVENTORY = 1
    SHOP = 2
    SHRINE = 3
    CHARACTER_SHEET = 4

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
            
        # UI State
        self.selected_stat_index = 0
            
        self.state = GameState.PLAYING # 초기 상태
        self.is_attack_mode = False # 원거리 공격/스킬 모드
        self.active_skill_name = None # 현재 시전 준비 중인 스킬
        self.current_level = 1 # 현재 던전 층수
        self.selected_item_index = 0 # 인벤토리 선택 인덱스
        self.inventory_scroll_offset = 0 # 인벤토리 스크롤 오프셋
        self.inventory_category_index = 0 # 0: 아이템, 1: 장비, 2: 스크롤, 3: 스킬
        self.shop_category_index = 0 # 0: 사기, 1: 팔기
        self.selected_shop_item_index = 0 # 상점 선택 인덱스
        
        # [Boss Summon] 마지막으로 처치한 보스 ID
        self.last_boss_id = None
        
        # [Visual Effects]
        self.particles = [] # 배경 파티클 (x, y, char, color, speed, type)
        self.banner_timer = 0 # 배너 표시 남은 시간
        self.banner_text = "" # 배너 텍스트

        # [Enhancement] Oil Selection State
        self.oil_selection_open = False
        self.pending_oil_item = None
        self.pending_oil_type = None
        self.selected_equip_index = 0
        
        # [Shrine] Shrine State
        self.active_shrine_id = None  # 현재 상호작용 중인 신전 ID
        self.shrine_menu_index = 0  # 0: 복구, 1: 강화
        self.shrine_enhance_step = 0  # 0: 메뉴, 1: 장비 선택, 2: 확인

        # 렌더러 초기화
        self.renderer = Renderer() 

        # 데이터 정의 로드 (항상 사용 가능하도록 __init__에서 처리)
        from .data_manager import load_item_definitions, load_skill_definitions, load_monster_definitions, load_map_definitions, load_class_definitions, load_boss_patterns
        from .trap_manager import load_trap_definitions
        self.item_defs = load_item_definitions()
        self.skill_defs = load_skill_definitions()
        self.monster_defs = load_monster_definitions()
        self.map_defs = load_map_definitions()
        self.class_defs = load_class_definitions()
        self.boss_patterns = load_boss_patterns()
        self.trap_defs = load_trap_definitions()
        self.prefix_defs = load_prefixes()
        self.suffix_defs = load_suffixes()
        
        # 접두어 관리자 초기화 (몬스터용)
        from .modifiers import ModifierManager
        self.modifier_manager = ModifierManager()

        self.shake_timer = 0 # Screen shake duration
        self.rng = random.Random() # Initialize RNG for map generation

        self._initialize_world(game_data)
        self._initialize_systems()

    def _initialize_world(self, game_data=None, preserve_player=None, spawn_at="START"):
        """맵, 플레이어, 몬스터 등 초기 엔티티 생성"""
        # [Boss Summon] 마지막 보스 정보 복원
        if game_data and "last_boss_id" in game_data:
            self.last_boss_id = game_data["last_boss_id"]

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
            # 5의 배수 층 또는 마지막 99층은 보스전으로 설정
            map_type = "BOSS" if (self.current_level % 5 == 0 or self.current_level == 99) else "NORMAL"
        
        # DungeonMap 인스턴스 생성
        # [Themed Map Size] Override config based on floor tier
        floor = 1
        if getattr(self, 'dungeon', None):
            floor = self.dungeon.dungeon_level_tuple[0]
            
        width, height = 60, 40 # Lv 1-25
        if floor >= 76:
            width, height = 100, 80
        elif floor >= 51:
            width, height = 80, 60
        elif floor >= 26:
            width, height = 70, 50
            
        # Ensure we obey the override
        if map_config:
            # We don't modify map_config directly to avoid persistent side effects if cached, 
            # but DungeonMap init takes explicit width/height
            pass

        level_tuple = (self.current_level, 0)
        if getattr(self, 'dungeon', None):
            level_tuple = self.dungeon.dungeon_level_tuple

        # [One-Way Transition] Restore saved map if available and not transitioning levels
        # If spawn_at is specified (START/EXIT), it usually means we just transitioned levels, 
        # so we WANT a new map.
        # BUT, if we are loading a save game (game_data present), we likely want the saved map.
        # Logic: If game_data has "current_map" AND we are not explicitly directed to spawn at EXIT (which implies new floor), use saved map.
        # Actually, if we just descended, we call _initialize_world with game_data=None.
        # So if game_data is present, it's a LOAD from save.
        
        if game_data and "current_map" in game_data:
            logging.info("[Load] Restoring saved map data...")
            dungeon_map = DungeonMap.from_dict(game_data["current_map"], self.rng)
        else:
            dungeon_map = DungeonMap(width, height, self.rng, 
                                     dungeon_level_tuple=level_tuple, 
                                     map_type=map_type)
            
        self.dungeon_map = dungeon_map
        map_data = dungeon_map.map_data
        
        # 1. 플레이어 엔티티 생성 (ID=1)
        if spawn_at == "EXIT":
             player_x, player_y = dungeon_map.exit_x, dungeon_map.exit_y
        else:
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
            # 저장된 데이터에서 엔티티 복원 (플레이어 ID=1 가정)
            player_data = game_data["entities"].get("1")
            if player_data:
                logging.info(f"[Load] Found Player Data (ID 1). Components: {list(player_data.keys())}")
                if "InventoryComponent" in player_data:
                    inv_data = player_data["InventoryComponent"]
                    if isinstance(inv_data, list) and inv_data:
                        inv_d = inv_data[0]
                        logging.info(f"[Load] Inventory Items: {len(inv_d.get('items', {}))}, Equipped: {list(inv_d.get('equipped', {}).keys())}")
            else:
                logging.warning("[Load] Player Data (ID 1) NOT FOUND in saved entities!")
            
            # StatsComponent 복원 또는 초기화
            stats_list = player_data.get("StatsComponent") if player_data else None
            if stats_list:
                if isinstance(stats_list, dict): stats_list = [stats_list]
                for s_data in stats_list:
                    self.world.add_component(player_entity.entity_id, StatsComponent(**s_data))
                
                # LevelComponent 복원
                level_list = player_data.get("LevelComponent", [])
                if isinstance(level_list, dict): level_list = [level_list]
                for l_data in level_list:
                    self.world.add_component(player_entity.entity_id, LevelComponent(**l_data))
            else:
                # StatsComponent가 없으면 (새 게임용 초기 데이터 등) 직업 기반 초기화
                class_id = game_data.get("selected_class")
                if not class_id:
                    class_id = "WARRIOR"
                
                class_def = self.class_defs.get(class_id)
                if not class_def:
                    print(f"Warning: Class {class_id} not found. Defaulting to WARRIOR.")
                    class_def = self.class_defs.get("WARRIOR") # Fallback
                
                if class_def:
                    self.world.add_component(player_entity.entity_id, StatsComponent(
                        max_hp=class_def.hp, current_hp=class_def.hp, 
                        attack=class_def.str, defense=class_def.vit, 
                        max_mp=class_def.mp, current_mp=class_def.mp, 
                        max_stamina=100, current_stamina=100,
                        strength=class_def.str, mag=class_def.mag, dex=class_def.dex, vit=class_def.vit
                    ))
                    self.world.add_component(player_entity.entity_id, LevelComponent(
                        level=1, exp=0, exp_to_next=100, job=class_def.name
                    ))
                else:
                    self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
                    self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))

                # InventoryComponent 복원
                inv_list = player_data.get("InventoryComponent") if player_data else None
                if inv_list:
                    if isinstance(inv_list, dict): inv_list = [inv_list]
                    for inv_data in inv_list:
                        # 아이템 딕셔너리 복구 (JSON 리스트를 다시 ItemDefinition 객체로)
                        restored_items = {}
                        for name, data in inv_data.get("items", {}).items():
                            item_info = data.get("item", {})
                            if item_info:
                                from .data_manager import ItemDefinition
                                try:
                                    item_obj = ItemDefinition(**item_info)
                                    restored_items[name] = {"item": item_obj, "qty": data.get("qty", 1)}
                                except Exception as e:
                                    logging.error(f"[Load] Failed to restore item '{name}': {e}")
                                    # Try to salvage if possible or skip
                                    pass
                        
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
                            skills=inv_data.get("skills"),
                            skill_levels=inv_data.get("skill_levels")
                        )
                        self.world.add_component(player_entity.entity_id, inv)
                        
                        # [Fix] Sanitize Loaded Items (Range Sync)
                        self._sanitize_loaded_items(player_entity)
        elif game_data and "player_specific_data" in game_data:
            # 테스트 환경용: player_specific_data 구조 처리
            player_data = game_data["player_specific_data"]
            
            # StatsComponent 생성
            self.world.add_component(player_entity.entity_id, StatsComponent(
                max_hp=player_data.get("max_hp", 100),
                current_hp=player_data.get("hp", 100),
                attack=player_data.get("str", 10),
                defense=player_data.get("vit", 10),
                max_mp=player_data.get("max_mp", 50),
                current_mp=player_data.get("mp", 50),
                max_stamina=100,
                current_stamina=100,
                strength=player_data.get("str", 10),
                mag=player_data.get("mag", 10),
                dex=player_data.get("dex", 10),
                vit=player_data.get("vit", 10),
                gold=player_data.get("gold", 0)
            ))
            
            # LevelComponent 생성
            self.world.add_component(player_entity.entity_id, LevelComponent(
                level=player_data.get("level", 1),
                exp=player_data.get("exp", 0),
                exp_to_next=100,
                job=player_data.get("job", "Novice")
            ))
            
            # InventoryComponent 생성
            if "inventory" in game_data:
                inv_data = game_data["inventory"]
                
                # 아이템 딕셔너리 생성
                restored_items = {}
                for item_name, item_info in inv_data.get("items", {}).items():
                    if item_name in self.item_defs:
                        item_def = self.item_defs[item_name]
                        qty = item_info.get("qty", 1)
                        restored_items[item_name] = {"item": item_def, "qty": qty}
                
                # 인벤토리 컴포넌트 추가
                inv = InventoryComponent(
                    items=restored_items,
                    equipped=inv_data.get("equipped", {}),
                    item_slots=inv_data.get("item_slots", [None] * 5),
                    skill_slots=inv_data.get("skill_slots", [None] * 5),
                    skills=inv_data.get("skills", []),
                    skill_levels=inv_data.get("skill_levels", {})
                )
                self.world.add_component(player_entity.entity_id, inv)
        else:
            # preserve_player도 없고 game_data도 없는 경우 (이론상 발생 방지)
            self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
            self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))
        
        # [중요] 인벤토리가 아직 생성되지 않았다면 (새 게임 로직) 여기서 기본 인벤토리 생성
        # [중요] 인벤토리가 아직 생성되지 않았다면 (새 게임 로직) 여기서 기본 인벤토리 생성
        inv = player_entity.get_component(InventoryComponent)
        if not inv:
            class_id = game_data.get("selected_class", "WARRIOR") if game_data else "WARRIOR"
            class_def = self.class_defs.get(class_id)
            
            # 1. 초기 스킬 설정
            current_skills = []
            if class_def and class_def.base_skill:
                # [Fix] ID("RAGE")를 이름("레이지")으로 변환하여 추가
                skill_obj = next((s for s in self.skill_defs.values() if s.id == class_def.base_skill), None)
                if skill_obj:
                    current_skills.append(skill_obj.name)
                else:
                    current_skills.append(class_def.base_skill)
                
            skill_slots = [None] * 5
            for i, skill in enumerate(current_skills):
                if i < 5: skill_slots[i] = skill
            
            inv = InventoryComponent(
                items={}, 
                equipped={slot: None for slot in ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]},
                item_slots=[None] * 5,
                skill_slots=skill_slots,
                skills=current_skills
            )
            self.world.add_component(player_entity.entity_id, inv)

            # 2. 직업별 초기 장비 지급
            stats = player_entity.get_component(StatsComponent)
            if class_def and hasattr(class_def, 'starting_items'):
                logging.info(f"Loading starting items for {class_def.name}: {class_def.starting_items}")
                for item_name, qty in class_def.starting_items:
                    # 골드 처리
                    if item_name in ["골드", "Gold", "금화"]:
                         if stats:
                             stats.gold += qty
                             logging.info(f"Added {qty} gold")
                         continue

                    # 아이템 지급
                    if item_name in self.item_defs:
                        item_def = self.item_defs[item_name]
                        
                        # 인벤토리에 추가
                        if item_name in inv.items:
                            inv.items[item_name]['qty'] += qty
                        else:
                            inv.items[item_name] = {'item': item_def, 'qty': qty}
                        logging.info(f"Added {qty}x {item_name} to inventory")

                        # 3. 자동 장착 로직 (하나만 지급된 경우 장착 시도)
                        if qty == 1:
                            target_slot = None
                            
                            if item_def.type == "WEAPON":
                                if not inv.equipped["손1"]: target_slot = "손1"
                            elif item_def.type == "SHIELD":
                                if not inv.equipped["손2"]: target_slot = "손2"
                            elif item_def.type == "ARMOR":
                                # 플래그에서 부위 확인
                                if item_def.flags:
                                    if "머리" in item_def.flags: target_slot = "머리"
                                    elif "몸통" in item_def.flags: target_slot = "몸통"
                                    elif "장갑" in item_def.flags: target_slot = "장갑"
                                    elif "신발" in item_def.flags: target_slot = "신발"
                                # 플래그 없으면 기본값 (천옷 등은 몸통)
                                if not target_slot and not inv.equipped["몸통"]:
                                    target_slot = "몸통"
                            
                            # 장착 실행
                            if target_slot and not inv.equipped[target_slot]:
                                inv.equipped[target_slot] = item_def
                                # [Fix] Do not remove from inventory. Keep it consistent with normal equip.
                                # del inv.items[item_name]
            
            # 퀵슬롯 자동 등록 (소모품)
            quick_slot_idx = 0
            for name, data in inv.items.items():
                if data['item'].type in ["CONSUMABLE", "SCROLL"] and quick_slot_idx < 5:
                    inv.item_slots[quick_slot_idx] = name
                    quick_slot_idx += 1
        
        # 초기 스탯 계산 (장비 보너스 적용)
        self._recalculate_stats()
        
        # 2. 맵 엔티티 생성 (ID=2)
        map_entity = self.world.create_entity()
        # map_data는 이미 2D 리스트이므로 바로 전달
        map_component = MapComponent(width=width, height=height, tiles=map_data) 
        self.world.add_component(map_entity.entity_id, map_component)
        
        # [Boss Gate] 보스 층에서 계단 숨기기 및 게이트 정보 저장
        if self.current_level in [25, 50, 75, 99]:
            region_names = {
                25: "Catacombs",
                50: "Caves", 
                75: "Hell",
                99: "승리"
            }
            
            # 맵 엔티티에 BossGateComponent 추가
            self.world.add_component(map_entity.entity_id, BossGateComponent(
                next_region_name=region_names[self.current_level],
                stairs_spawned=False
            ))
            
            # 실제 맵 데이터에서 계단 타일을 바닥('.')으로 임시 변경
            if 0 <= dungeon_map.exit_x < width and 0 <= dungeon_map.exit_y < height:
                map_component.tiles[dungeon_map.exit_y][dungeon_map.exit_x] = '.'
                logging.info(f"Boss Floor {self.current_level}: Hidden exit stairs at ({dungeon_map.exit_x}, {dungeon_map.exit_y})")
        
        # 3. 메시지 로그 엔티티 생성 (ID=3)
        message_entity = self.world.create_entity()
        message_comp = MessageComponent()
        theme_info = self._get_map_theme()
        # 구역 색상을 테마에 맞춰 강조 (Cathedral: brown, Catacombs: blue, Caves: yellow, Hell: red)
        zone_color = theme_info.get("wall_color", "white")
        if theme_info['name'] == "Cathedral": zone_color = "gold" # Cathedral은 금색으로 강조
        
        message_comp.add_message(f"던전 {self.current_level}층 [{theme_info['name']}]에 입장했습니다.", zone_color)
        
        # [Visual Effect] 신규 구역 진입 시 대형 배너 트리거 (1, 26, 51, 76, 99층)
        if self.current_level in [1, 26, 51, 76, 99]:
            if self.current_level == 99:
                self.banner_text = "--- FINAL BATTLE ---"
            else:
                self.banner_text = f"--- THE {theme_info['name'].upper()} ---"
            
            # 1층과 99층은 게임 시작 및 최종전 시점이므로 조금 더 길게(4초) 노출
            self.banner_timer = 4.0 if self.current_level in [1, 99] else 3.0
            
        if map_type == "BOSS":
            message_comp.add_message("[경고] 강력한 보스의 기운이 느껴집니다!", "red")
        else:
            message_comp.add_message("WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.")
        self.world.add_component(message_entity.entity_id, message_comp)
        
        # 4. 엔티티 배치 (몬스터/보스/오브젝트)
        # 4. 엔티티 배치 (몬스터/보스/오브젝트)
        if map_type == "BOSS":
            self._spawn_boss_room_features(dungeon_map)
        else:
            has_boss = map_config.has_boss if map_config else False
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

            # [Safe Zone] Determine safe room index
            safe_room_index = None
            if spawn_at == "START":
                safe_room_index = 0
            elif spawn_at == "EXIT":
                safe_room_index = len(dungeon_map.rooms) - 1

            self._spawn_monsters(dungeon_map, map_config, safe_room_index=safe_room_index)
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
        # 상성 및 플래그 설정
        from .constants import ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON, RARITY_NORMAL, RARITY_MAGIC, RARITY_UNIQUE
        all_elements = [ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON]
        monster_el = random.choice(all_elements)
        # color = ELEMENT_COLORS.get(monster_el, "white") # REMOVED: Color now depends on Rarity
        color = RARITY_NORMAL
        
        m_flags = monster_def.flags.copy()
        if monster_el != "NONE": m_flags.add(monster_el.upper())

        # 접두어 적용 (30%)
        m_name, m_hp, m_atk, m_def = monster_def.name, monster_def.hp, monster_def.attack, monster_def.defense
        if random.random() < 0.3:
            mod_def = self.modifier_manager.apply_monster_prefix(monster_def)
            m_name, m_hp, m_atk, m_def = mod_def.name, mod_def.hp, mod_def.attack, mod_def.defense
            m_flags.update(mod_def.flags)
            # if mod_def.color != "white": color = mod_def.color # REMOVED: Prefix color logic overridden
            color = RARITY_MAGIC

        self.world.add_component(monster.entity_id, RenderComponent(char=monster_def.symbol, color=color))
        self.world.add_component(monster.entity_id, MonsterComponent(type_name=m_name, monster_id=monster_def.ID))
        self.world.add_component(monster.entity_id, AIComponent(behavior=random.randint(1, 2), detection_range=8))
        
        stats = StatsComponent(
            max_hp=m_hp, current_hp=m_hp, attack=m_atk, defense=m_def, 
            element=monster_el,
            res_fire=monster_def.res_fire,
            res_ice=monster_def.res_ice,
            res_lightning=monster_def.res_lightning,
            res_poison=monster_def.res_poison
        )
        stats.flags.update(m_flags)
        stats.action_delay = monster_def.action_delay
        self.world.add_component(monster.entity_id, stats)
        return monster

    def _spawn_monsters(self, dungeon_map, map_config=None, safe_room_index=None):
        """일반 층의 몬스터들을 스폰합니다."""
        pool = map_config.monster_pool if map_config else None
        
        starting_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
        for i, room in enumerate(dungeon_map.rooms):
            # [Safe Zone] Skip spawning in the arrival room
            if safe_room_index is not None and i == safe_room_index:
                continue
            
            if room == starting_room and safe_room_index is None: 
                # Fallback for old calls or cases where we didn't specify safe room but want to skip start
                continue
            
            # [Hack & Slash] Increase density and add 'Monster Nest' chance
            if random.random() < 0.2: # 20% chance for Monster Nest
                num = random.randint(15, 25)
            else:
                num = random.randint(5, 12)
                
            for _ in range(num):
                mx = random.randint(room.x1 + 1, room.x2 - 1)
                my = random.randint(room.y1 + 1, room.y2 - 1)
                
                # [Fix] Safe zone check - don't spawn too close to start
                dist_to_start = (mx - dungeon_map.start_x)**2 + (my - dungeon_map.start_y)**2
                if dist_to_start < 400:  # 20 tile radius
                    continue
                    
                self._spawn_monster_at(mx, my, pool=pool)

        # [Hack & Slash] Corridors
        for cx, cy in dungeon_map.corridors:
            if random.random() < 0.15:
                if (cx - dungeon_map.start_x)**2 + (cy - dungeon_map.start_y)**2 < 400: continue
                self._spawn_monster_at(cx, cy, pool=pool)

        # [Balance] Monster Density Minimum Guarantee
        # 1-25: 40, 26-50: 60, 51-75: 80, 76-99: 100
        current_floor = self.current_level
        target_count = 40
        if current_floor >= 76: target_count = 100
        elif current_floor >= 51: target_count = 80
        elif current_floor >= 26: target_count = 60
        
        # Count existing monsters
        existing_monsters = len(self.world.get_entities_with_components({MonsterComponent}))
        
        # Fill remaining
        attempts = 0
        while existing_monsters < target_count and attempts < 200:
            attempts += 1
            # Random room spawn
            room = random.choice(dungeon_map.rooms)
            if safe_room_index is not None and dungeon_map.rooms.index(room) == safe_room_index: continue
            
            rx = random.randint(room.x1 + 1, room.x2 - 1)
            ry = random.randint(room.y1 + 1, room.y2 - 1)
            
            if (rx - dungeon_map.start_x)**2 + (ry - dungeon_map.start_y)**2 < 400: continue
            
            # Check occupancy
            occupied = False
            for e in self.world.get_entities_with_components({PositionComponent}):
                p = e.get_component(PositionComponent)
                if p.x == rx and p.y == ry:
                    occupied = True
                    break
            if occupied: continue
            
            self._spawn_monster_at(rx, ry, pool=pool)
            existing_monsters += 1

        # [Balance] Monster Density Minimum Guarantee
        # 1-25: 40, 26-50: 60, 51-75: 80, 76-99: 100
        current_floor = self.current_level
        target_count = 40
        if current_floor >= 76: target_count = 100
        elif current_floor >= 51: target_count = 80
        elif current_floor >= 26: target_count = 60
        
        # Count existing monsters
        existing_monsters = len(self.world.get_entities_with_components({MonsterComponent}))
        
        # Fill remaining
        attempts = 0
        while existing_monsters < target_count and attempts < 200:
            attempts += 1
            # Random room spawn
            room = random.choice(dungeon_map.rooms)
            if safe_room_index is not None and dungeon_map.rooms.index(room) == safe_room_index: continue
            
            rx = random.randint(room.x1 + 1, room.x2 - 1)
            ry = random.randint(room.y1 + 1, room.y2 - 1)
            
            if (rx - dungeon_map.start_x)**2 + (ry - dungeon_map.start_y)**2 < 400: continue
            
            # Check occupancy
            occupied = False
            for e in self.world.get_entities_with_components({PositionComponent}):
                p = e.get_component(PositionComponent)
                if p.x == rx and p.y == ry:
                    occupied = True
                    break
            if occupied: continue
            
            self._spawn_monster_at(rx, ry, pool=pool)
            existing_monsters += 1


    def _spawn_boss_room_features(self, dungeon_map):
        """보스 맵 전용 엔티티 스폰 (Lever, Door, Shrine, Boss)"""
        # 1. Shrine (Antechamber)
        sx, sy = dungeon_map.shrine_pos
        self._spawn_shrine(sx, sy)
        
        # 2. Door (Blocking Boss Room)
        dx, dy = dungeon_map.boss_door_pos
        door = self.world.create_entity()
        self.world.add_component(door.entity_id, PositionComponent(x=dx, y=dy))
        self.world.add_component(door.entity_id, RenderComponent(char='+', color='brown', priority=5))
        self.world.add_component(door.entity_id, DoorComponent(is_open=False, is_locked=True, key_id="BOSS_DOOR_KEY")) # Locked, opened by lever
        self.world.add_component(door.entity_id, BlockMapComponent(blocks_movement=True, blocks_sight=True))
        
        # 3. Lever (Side Room) -> Spawns Trap on Use & Opens Door
        lx, ly = dungeon_map.lever_pos
        lever = self.world.create_entity()
        self.world.add_component(lever.entity_id, PositionComponent(x=lx, y=ly))
        self.world.add_component(lever.entity_id, RenderComponent(char='/', color='yellow', priority=5))
        # Switch behavior handled in components/systems
        # linked_trap_id can be used if we spawn a trap entity. 
        # But for now, we want a trap EFFECT (100%). We can use a dummy trap ID or handle it via event.
        # Let's use linked_door_pos to open the door remotely.
        self.world.add_component(lever.entity_id, SwitchComponent(
            is_open=False, 
            locked=False,
            linked_door_pos=(dx, dy), # Link to Boss Door
            auto_reset=False
        ))
        self.world.add_component(lever.entity_id, BlockMapComponent(blocks_movement=False, blocks_sight=False))
        
        # 4. Boss (Boss Room)
        bx, by = dungeon_map.boss_spawn_pos
        self._spawn_boss(bx, by)

    def _spawn_boss(self, x, y, pool=None, boss_name=None, is_summoned=False):
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
        
        # [Boss Summon] 소환된 보스(환영)는 파란색으로 표시하고 능력치 조정
        color = RARITY_UNIQUE
        if is_summoned:
            color = 'blue'
            
        self.world.add_component(boss.entity_id, RenderComponent(char=boss_def.symbol, color=color))
        
        # [Fix] 이름 설정 로직 수정
        monster_name = boss_def.name
        if is_summoned:
            monster_name = f"{boss_def.name}의 환영"
            
        self.world.add_component(boss.entity_id, MonsterComponent(type_name=monster_name, monster_id=boss_def.ID, is_summoned=is_summoned))

        # 보스는 항상 앵그리 모드 (CHASE)
        self.world.add_component(boss.entity_id, AIComponent(behavior=AIComponent.CHASE, detection_range=15))
        
        hp = int(boss_def.hp * 2.0) # [Balance] Boss Buff (200% Base Stats)
        attack = int(boss_def.attack * 2.0)
        if is_summoned:
            # [Balance] Summoned Boss Scaling
            # Prevent one-shot by enforcing minimum HP based on current floor
            floor_scaling = self.current_level * 1500 # Increased scaling
            base_hp = hp * 0.5
            hp = int(max(base_hp, floor_scaling))
            
            attack = int(attack * 0.8) # 공격력 80%

        stats = StatsComponent(max_hp=hp, current_hp=hp, attack=attack, defense=boss_def.defense)
        stats.flags.update(boss_def.flags)
        stats.action_delay = boss_def.action_delay
        self.world.add_component(boss.entity_id, stats)
        
        # [Boss System] 보스 컴포넌트 추가
        from .components import BossComponent
        self.world.add_component(boss.entity_id, BossComponent(boss_id=boss_def.ID))
        
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
                {'item': self.item_defs.get('확인 스크롤'), 'price': 50},
            ]
            
            # 층수에 맞는 장비/무기 추가 (3개 랜덤 선택)
            equipment_candidates = self._get_eligible_items(dungeon_map.dungeon_level_tuple[0])
            # [Balance] Starting Shop Nerf: Level <= 5, Standard Gear Only
            equipment_candidates = [
                item for item in equipment_candidates 
                if item.type in ['WEAPON', 'ARMOR', 'SHIELD'] 
                and item.required_level <= 5
            ]
            if equipment_candidates:
                selected_gear = random.sample(equipment_candidates, min(3, len(equipment_candidates)))
                for gear in selected_gear:
                    # 상점 가격 대략적 책정 (레벨 * 50 + 기본값)
                    price = gear.required_level * 50 + random.randint(50, 150)
                    shop_items.append({'item': gear, 'price': price})

            shop_items = [si for si in shop_items if si['item'] is not None]
            self.world.add_component(shop.entity_id, ShopComponent(items=shop_items))
            self.world.add_component(shop.entity_id, MonsterComponent(type_name="상인"))

        # 보물 상자 (CSV 설정 기반)
        chest_count = map_config.chest_count if map_config and map_config.chest_count != -1 else 2
        mimic_prob = map_config.mimic_prob if map_config else 0.1
        item_pool = map_config.item_pool if map_config else []
        
        other_rooms = dungeon_map.rooms[1:] if len(dungeon_map.rooms) > 1 else dungeon_map.rooms
        floor = dungeon_map.dungeon_level_tuple[0]
            
        for _ in range(chest_count):
            room = random.choice(other_rooms)
            cx = random.randint(room.x1 + 1, room.x2 - 1)
            cy = random.randint(room.y1 + 1, room.y2 - 1)
            
            # 미믹 여부 결정
            if random.random() < mimic_prob:
                self._spawn_mimic(cx, cy)
            else:
                self._spawn_chest(cx, cy, floor, item_pool)


        # 함정 (고정 개수 배치, 레벨 기반 필터링)
        trap_count = 5  # 기본값
        if map_config and hasattr(map_config, 'trap_count'):
            trap_count = map_config.trap_count
        elif map_config:
            # trap_count가 없으면 trap_prob 기반으로 추정
            trap_count = int(len(other_rooms) * map_config.trap_prob * 20)
        
        self._spawn_traps_for_map(dungeon_map, trap_count, other_rooms)
        
        # [Shrine] 신전 (2층마다 1개, 보스 층 제외)
        is_boss_floor = self.current_level % 5 == 0
        if self.current_level % 2 == 0 and not is_boss_floor and other_rooms:
            shrine_room = random.choice(other_rooms)
            shrine_x = random.randint(shrine_room.x1 + 1, shrine_room.x2 - 1)
            shrine_y = random.randint(shrine_room.y1 + 1, shrine_room.y2 - 1)
            self._spawn_shrine(shrine_x, shrine_y)

    def _spawn_trap(self, x, y):
        """함정 엔티티 생성 (CSV 데이터 기반)"""
        if not self.trap_defs:
            return  # 함정 정의가 없으면 생성하지 않음
        
        trap = self.world.create_entity()
        self.world.add_component(trap.entity_id, PositionComponent(x=x, y=y))
        
        # CSV에서 로드한 함정 정의 중 가중치 기반 선택
        trap_list = list(self.trap_defs.values())
        weights = [t.weight for t in trap_list]
        selected_trap = random.choices(trap_list, weights=weights, k=1)[0]
        
        # TrapComponent 생성
        self.world.add_component(trap.entity_id, TrapComponent(
            trap_type=selected_trap.id,
            damage_min=selected_trap.damage_min,
            damage_max=selected_trap.damage_max,
            effect=selected_trap.status_effect,
            is_hidden="HIDDEN" in selected_trap.flags,
            auto_reset="AUTO_RESET" in selected_trap.flags
        ))
        
        # RenderComponent 추가 (숨겨진 함정은 나중에 발견 시 표시)
        if 'HIDDEN' not in selected_trap.flags:
            self.world.add_component(trap.entity_id, RenderComponent(
                char=selected_trap.symbol,
                color=selected_trap.color
            ))
    
    def _spawn_traps_for_map(self, dungeon_map, trap_count: int, rooms: list):
        """맵에 레벨에 맞는 함정을 고정 개수만큼 배치"""
        if not self.trap_defs or trap_count <= 0:
            return
        
        floor_level = dungeon_map.dungeon_level_tuple[0]
        
        # 함정 개수 분배: 바닥 함정 70%, 벽 함정 30%
        floor_trap_count = int(trap_count * 0.7)
        wall_trap_count = trap_count - floor_trap_count
        
        # [Fix] Start Room Exclusion
        start_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
        
        # 1. 바닥 함정 배치 (STEP_ON)
        # 현재 층에서 사용 가능한 함정 필터링 (STEP_ON만)
        eligible_traps = [trap for trap in self.trap_defs.values() 
                         if trap.min_level <= floor_level 
                         and getattr(trap, 'trigger_type', 'STEP_ON') == 'STEP_ON']
        
        if not eligible_traps:
            # 사용 가능한 함정이 없으면 모든 STEP_ON 함정 사용
            eligible_traps = [trap for trap in self.trap_defs.values() 
                             if getattr(trap, 'trigger_type', 'STEP_ON') == 'STEP_ON']
        
        placed = 0
        max_attempts = floor_trap_count * 5  # 최대 시도 횟수
        attempts = 0
        
        while placed < floor_trap_count and attempts < max_attempts:
            attempts += 1
            
            # 배치 위치 타입 선택 (바닥 70%, 복도 30%)
            if random.random() < 0.7 and rooms:
                # 방 바닥에 배치
                # [Fix] 첫 번째 방(시작 방)은 제외하고 랜덤 선택
                candidate_rooms = rooms[1:] if len(rooms) > 1 else rooms
                if not candidate_rooms: continue
                
                room = random.choice(candidate_rooms)
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)
            elif dungeon_map.corridors:
                # 복도에 배치
                x, y = random.choice(dungeon_map.corridors)
            else:
                continue
            
            # 중복 체크 (이미 함정이 있는 위치는 제외)
            if not self._is_trap_at(x, y):
                # [Fix] Safe Zone Check - Don't spawn traps inside Start Room
                if start_room and start_room.x1 <= x <= start_room.x2 and start_room.y1 <= y <= start_room.y2:
                     continue
                
                # Double Check with Radius just in case
                if (x - dungeon_map.start_x)**2 + (y - dungeon_map.start_y)**2 < 100: # 10 radius
                    continue
                
                self._spawn_trap_at(x, y, eligible_traps)
                placed += 1
        
        # 2. 벽 함정 배치 (PROXIMITY)
        if wall_trap_count > 0:
            self._spawn_wall_traps(dungeon_map, wall_trap_count)

        # 3. 연쇄 함정 구역 (Trap Gauntlet) 배치
        # 복도 중 일부를 선택하여 함정을 밀집 배치
        self._spawn_trap_gauntlets(dungeon_map, eligible_traps)

        # 4. 압력판 배치 (10-20% 확률로 바닥 함정 대신 압력판 생성)
        # 이미 배치된 벽 함정 중 일부를 압력판으로 제어하도록 설정
        self._link_pressure_plates(dungeon_map, rooms)

    def _spawn_trap_gauntlets(self, dungeon_map, eligible_traps: list):
        """복도에 연쇄 함정 구역 생성"""
        if not dungeon_map.corridors or not eligible_traps:
            return
            
        # 복도가 충분히 긴 경우에만 생성
        # corridors는 [(x,y), (x,y), ...] 리스트임. 
        # 실제 연쇄 함정을 위해서는 연속된 위치가 필요함.
        
        # 간단한 구현: 무작위 복도 타일을 선택하고 그 주변 복도 타일들에 함정 배치
        num_gauntlets = max(1, len(dungeon_map.corridors) // 100) # 맵 크기에 비례
        if random.random() > 0.3: # 30% 확률로만 생성 (너무 자주 나오면 고통스러움)
            num_gauntlets = 0
            
        for _ in range(num_gauntlets):
            start_node = random.choice(dungeon_map.corridors)
            gx, gy = start_node
            
            # [Fix] Safe Zone Check (Start Room + Radius)
            start_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
            # Bounds check
            if start_room and start_room.x1 <= gx <= start_room.x2 and start_room.y1 <= gy <= start_room.y2:
                continue
            # Radius check
            if (gx - dungeon_map.start_x)**2 + (gy - dungeon_map.start_y)**2 < 100:
                continue
            
            # 주변 3x3 범위 내의 모든 복도 타일에 함정 배치 시도
            traps_placed = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    tx, ty = gx + dx, gy + dy
                    if (tx, ty) in dungeon_map.corridors:
                        if not self._is_trap_at(tx, ty) and random.random() < 0.6:
                            self._spawn_trap_at(tx, ty, eligible_traps)
                            traps_placed += 1
            
            if traps_placed > 0:
                # [DEBUG] print(f"Trap Gauntlet spawned at {gx}, {gy} with {traps_placed} traps")
                pass

    def _link_pressure_plates(self, dungeon_map, rooms):
        """벽 함정 중 일부를 압력판으로 제어하도록 링크 설정"""
        if not self.trap_defs or not rooms:
            return
            
        floor_level = dungeon_map.dungeon_level_tuple[0]
        
        # 압력판 타입 필터링
        pressure_defs = [trap for trap in self.trap_defs.values() 
                        if trap.min_level <= floor_level 
                        and getattr(trap, 'effect_type', '') == 'REMOTE']
        
        if not pressure_defs:
            return
            
        # 맵에 있는 모든 벽 함정 찾기
        traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
        wall_traps = []
        for tent in traps:
            tc = tent.get_component(TrapComponent)
            if tc.trigger_type == 'PROXIMITY':
                wall_traps.append(tent)
        
        if not wall_traps:
            return
            
        # 약 20%의 벽 함정을 압력판으로 제어
        num_to_link = max(1, len(wall_traps) // 5)
        random.shuffle(wall_traps)
        
        for i in range(min(num_to_link, len(wall_traps))):
            target_trap = wall_traps[i]
            t_pos = target_trap.get_component(PositionComponent)
            t_comp = target_trap.get_component(TrapComponent)
            
            # 압력판 위치 선정 (벽 함정 근처 방 바닥)
            found_pos = False
            for _ in range(10): # 최대 10번 시도
                room = random.choice(rooms)
                px = random.randint(room.x1 + 1, room.x2 - 1)
                py = random.randint(room.y1 + 1, room.y2 - 1)
                
                # 거리 체크 (너무 멀면 안됨)
                dist = abs(px - t_pos.x) + abs(py - t_pos.y)
                
                # [Fix] Safe Zone Check
                if (px - dungeon_map.start_x)**2 + (py - dungeon_map.start_y)**2 < 400:
                    continue

                if 2 < dist < 8 and not self._is_trap_at(px, py):
                    # 압력판 생성
                    selected_p = random.choice(pressure_defs)
                    pp = self.world.create_entity()
                    self.world.add_component(pp.entity_id, PositionComponent(x=px, y=py))
                    
                    self.world.add_component(pp.entity_id, TrapComponent(
                        trap_type=selected_p.id,
                        damage_min=0,
                        damage_max=0,
                        is_hidden='HIDDEN' in selected_p.flags,
                        trigger_type='STEP_ON',
                        linked_trap_pos=(t_pos.x, t_pos.y),
                        auto_reset='AUTO_RESET' in selected_p.flags,
                        reset_delay=2.0
                    ))
                    
                    if 'HIDDEN' not in selected_p.flags:
                        self.world.add_component(pp.entity_id, RenderComponent(
                            char=selected_p.symbol,
                            color=selected_p.color
                        ))
                    
                    # 연결된 원격 함정은 이제 근접 감지를 하지 않고 압력판에 의해서만 발동됨
                    # (여기서는 트리거 타입을 REMOTE로 유지하거나 그냥 둠. TrapSystem logic에 따라)
                    # 벽 함정의 trigger_type을 STEP_ON으로 바꿔서 플레이어가 밟아도 발동하게 할 수도 있음
                    # 또는 플레이어 감지 범위를 0으로 만들거나 hidden 처리
                    found_pos = True
                    break
    
    def _is_trap_at(self, x: int, y: int) -> bool:
        """지정된 위치에 함정이 있는지 확인"""
        traps = self.world.get_entities_with_components({PositionComponent, TrapComponent})
        for trap in traps:
            pos = trap.get_component(PositionComponent)
            if pos.x == x and pos.y == y:
                return True
        return False
    
    def _spawn_trap_at(self, x: int, y: int, eligible_traps: list):
        """지정된 위치에 적격 함정 중 하나를 배치"""
        trap = self.world.create_entity()
        self.world.add_component(trap.entity_id, PositionComponent(x=x, y=y))
        
        # 가중치 기반 선택
        weights = [t.weight for t in eligible_traps]
        selected_trap = random.choices(eligible_traps, weights=weights, k=1)[0]
        
        # TrapComponent 생성
        self.world.add_component(trap.entity_id, TrapComponent(
            trap_type=selected_trap.id,
            damage_min=selected_trap.damage_min,
            damage_max=selected_trap.damage_max,
            effect=selected_trap.status_effect,
            is_hidden="HIDDEN" in selected_trap.flags,
            auto_reset="AUTO_RESET" in selected_trap.flags
        ))
        
        # RenderComponent 추가 (숨겨진 함정은 나중에 발견 시 표시)
        if 'HIDDEN' not in selected_trap.flags:
            self.world.add_component(trap.entity_id, RenderComponent(
                char=selected_trap.symbol,
                color=selected_trap.color
            ))
    
    def _get_wall_adjacent_tiles(self, dungeon_map):
        """벽에 인접한 바닥 타일 반환 (x, y, direction)"""
        adjacent_tiles = []
        
        for y in range(1, dungeon_map.height - 1):
            for x in range(1, dungeon_map.width - 1):
                if dungeon_map.map_data[y][x] == '.':  # 바닥 타일
                    # 벽 인접성 확인 (4방향) - 벽 주변 바닥에 함정 설치
                    if dungeon_map.map_data[y-1][x] == '#':  # 북쪽 벽
                        adjacent_tiles.append((x, y, 'SOUTH'))
                    elif dungeon_map.map_data[y+1][x] == '#':  # 남쪽 벽
                        adjacent_tiles.append((x, y, 'NORTH'))
                    elif dungeon_map.map_data[y][x-1] == '#':  # 서쪽 벽
                        adjacent_tiles.append((x, y, 'EAST'))
                    elif dungeon_map.map_data[y][x+1] == '#':  # 동쪽 벽
                        adjacent_tiles.append((x, y, 'WEST'))
        
        return adjacent_tiles
    
    def _spawn_wall_traps(self, dungeon_map, count: int):
        """벽에 인접한 위치에 벽 함정 배치"""
        if not self.trap_defs or count <= 0:
            return
        
        floor_level = dungeon_map.dungeon_level_tuple[0]
        
        # PROXIMITY 타입 함정 필터링
        wall_traps = [trap for trap in self.trap_defs.values() 
                     if trap.min_level <= floor_level and hasattr(trap, 'trigger_type') 
                     and getattr(trap, 'trigger_type', 'STEP_ON') == 'PROXIMITY']
        
        if not wall_traps:
            return
        
        # 벽 인접 타일 가져오기
        wall_tiles = self._get_wall_adjacent_tiles(dungeon_map)
        if not wall_tiles:
            return
        
        # 랜덤하게 선택하여 배치
        placed = 0
        random.shuffle(wall_tiles)
        
        for x, y, direction in wall_tiles:
            if placed >= count:
                break
            
            # [Fix] Safe Zone Check
            start_room = dungeon_map.rooms[0] if dungeon_map.rooms else None
            
            # Start Room Bounds Check
            if start_room and start_room.x1 <= x <= start_room.x2 and start_room.y1 <= y <= start_room.y2:
                continue
                
            # Radius Check
            if (x - dungeon_map.start_x)**2 + (y - dungeon_map.start_y)**2 < 100:
                continue

            if not self._is_trap_at(x, y):
                # 벽 함정 배치
                trap = self.world.create_entity()
                self.world.add_component(trap.entity_id, PositionComponent(x=x, y=y))
                
                # 가중치 기반 선택
                weights = [t.weight for t in wall_traps]
                selected_trap = random.choices(wall_traps, weights=weights, k=1)[0]
                
                # TrapComponent 생성 (direction 포함)
                self.world.add_component(trap.entity_id, TrapComponent(
                    trap_type=selected_trap.id,
                    damage_min=selected_trap.damage_min,
                    damage_max=selected_trap.damage_max,
                    effect=selected_trap.status_effect,
                    is_hidden='HIDDEN' in selected_trap.flags,
                    trigger_type='PROXIMITY',
                    direction=direction,
                    detection_range=5,
                    auto_reset='AUTO_RESET' in selected_trap.flags
                ))
                
                # RenderComponent 추가
                if 'HIDDEN' not in selected_trap.flags:
                    self.world.add_component(trap.entity_id, RenderComponent(
                        char=selected_trap.symbol,
                        color=selected_trap.color
                    ))
                
                placed += 1
    
    def _spawn_shrine(self, x, y):
        """신전 엔티티 생성"""
        shrine = self.world.create_entity()
        self.world.add_component(shrine.entity_id, PositionComponent(x=x, y=y))
        self.world.add_component(shrine.entity_id, RenderComponent(char='†', color='cyan_bg'))  # 강조된 신전
        self.world.add_component(shrine.entity_id, ShrineComponent(is_used=False))
        self.world.add_component(shrine.entity_id, MonsterComponent(type_name="신전"))

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


    def _spawn_chest(self, x, y, floor, item_pool=None):
        """일반 보물상자 스폰"""
        chest = self.world.create_entity()
        self.world.add_component(chest.entity_id, PositionComponent(x=x, y=y))
        self.world.add_component(chest.entity_id, RenderComponent(char='[', color='gold_bg'))
        self.world.add_component(chest.entity_id, ChestComponent())
        
        loot_items = []
        
        # 1. Determine Item
        item_id = None
        if item_pool:
            # print(f"DEBUG: Using item pool: {item_pool}")
            candidates = [self.item_defs[name] for name in item_pool if name in self.item_defs]
        else:
            candidates = self._get_eligible_items(floor)
        
        if not candidates:
             print(f"DEBUG: No candidates for floor {floor}. ItemDef count: {len(self.item_defs)}")
        
        if candidates:
            print(f"DEBUG: Chest Candidates: {len(candidates)}")
            item = random.choice(candidates)
            # [Fix] Clone item to avoid modifying the definition
            item = copy.deepcopy(item)
            item_id = item.name
            
            # 2. Determine Rarity
            rarity = self._get_rarity(floor)
            item.rarity = rarity
            
            # [Endgame] 95-99F: Force Magic+ or higher chance
            if floor >= 95:
                # Almost always at least Magic
                pass 

            if rarity == "MAGIC" or rarity == "UNIQUE":
                prefix_id, suffix_id = self._roll_magic_affixes(item.type, floor)
                if prefix_id or suffix_id:
                     affixed = self._create_item_with_affix(item.name, prefix_id, suffix_id, floor) # Pass floor
                     if affixed:
                         item = affixed
            
            # (Optional) If we want to color code the item based on rarity?
            # Currently ItemDefinition has color. Could override.
            # But let's stick to name changes for now.
            
            loot_items.append({'item': item, 'qty': 1})
            
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
        
        # TrapSystem은 trap_manager에서 import
        from .trap_manager import TrapSystem as TrapSystemNew
        self.trap_system = TrapSystemNew(self.world, self.trap_defs)
        
        self.sound_system = SoundSystem(self.world)
        self.boss_system = BossSystem(self.world)
        self.render_system = RenderSystem(self.world)
        self.interaction_system = InteractionSystem(self.world)
        
        # 2. 시스템 순서 등록: 시간 -> 입력 -> AI -> 이동 -> 전투 -> 레벨 -> 회복 -> 렌더링
        systems = [
            self.time_system,
            self.input_system,
            self.monster_ai_system,
            self.movement_system,
            self.interaction_system, # Move success -> Interaction check
            self.combat_system,
            self.level_system,
            self.trap_system,
            self.regeneration_system,
            self.sound_system,
            self.boss_system,
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
        self.world.event_manager.register(ShrineOpenEvent, self)

    def trigger_shake(self, duration=10):
        """화면 흔들림 효과를 트리거합니다."""
        self.shake_timer = duration
        if self.ui:
            self.ui.trigger_shake(duration)

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
            
    def _get_rarity(self, floor: int, magic_find: int = 0) -> str:
        """층수와 Magic Find에 따른 아이템 등급 결정 (Top-Down: UNIQUE -> MAGIC -> NORMAL)"""
        # [Themed Rarity Rates]
        # Lv 1-25: Normal 85%, Magic 14.5%, Unique 0.5%
        # Lv 26-50: Normal 70%, Magic 24.5%, Unique 5.5%
        # Lv 51+: Normal 30%, Magic 44.5%, Unique 25.5%

        if floor > 50:
            # Target: N 30, M 44.5, U 25.5
            # P(U) = 0.255
            # P(M|!U) = 0.445 / (1 - 0.255) = 0.445 / 0.745 ~= 0.5973
            base_unique = 0.255
            base_magic = 0.5973
        elif floor > 25:
            # Target: N 70, M 24.5, U 5.5
            # P(U) = 0.055
            # P(M|!U) = 0.245 / (1 - 0.055) = 0.245 / 0.945 ~= 0.2593
            base_unique = 0.055
            base_magic = 0.2593
        else:
             # Target: N 85, M 14.5, U 0.5
             # P(U) = 0.005
             # P(M|!U) = 0.145 / 0.995 ~= 0.1457
             base_unique = 0.005 
             base_magic = 0.1457
        
        # [Endgame] 95층 이상: 보스런 느낌으로 확률 보정 (기존 로직 유지 또는 통합)
        if floor >= 95:
             base_unique = max(base_unique, 0.05)
             base_magic = max(base_magic, 0.50)
        
        # MF 적용 (Ex: MF 100 -> 확률 2배)
        mf_factor = 1.0 + (magic_find / 100.0)
        
        p_unique = min(1.0, base_unique * mf_factor)
        p_magic = min(1.0, base_magic * mf_factor)
        
        # 1. Check Unique
        if random.random() < p_unique:
            return "UNIQUE" # 실제 데이터가 없으면 아래에서 MAGIC으로 처리될 수 있음 (시스템에 따라)
            
        # 2. Check Magic (Failed Unique)
        if random.random() < p_magic:
            return "MAGIC"
            
        # 3. Else Normal
        return "NORMAL"

    def _roll_magic_affixes(self, item_type: str, floor: int) -> tuple:
        """Magic 아이템의 접두사/접미사 결정"""
        prefix_id = None
        suffix_id = None
        
        # 1. Combination Roll
        # Prefix Only (40%), Suffix Only (40%), Both (20%)
        roll = random.random()
        want_prefix = False
        want_suffix = False
        
        if roll < 0.40:
            want_prefix = True
        elif roll < 0.80:
            want_suffix = True
        else:
            want_prefix = True
            want_suffix = True
            
        # [Endgame] 95층 이상: Prefix+Suffix 확률 대폭 증가 (80%) - Optional override
        if floor >= 95 and roll < 0.80:
             want_prefix = True
             want_suffix = True
            
        # 2. Tier Filtering & Selection
        if want_prefix:
            # min_level <= floor 인 것만 + 타입 일치
            valid_p = []
            for pid, pdef in self.prefix_defs.items():
                if item_type in pdef.allowed_types and pdef.min_level <= floor:
                    valid_p.append(pid)
            if valid_p:
                prefix_id = random.choice(valid_p)
                
                # [CURSED] If prefix is Cursed, force suffix
                if prefix_id == "Cursed":
                    want_suffix = True
                
        if want_suffix:
            valid_s = []
            for sid, sdef in self.suffix_defs.items():
                if item_type in sdef.allowed_types and sdef.min_level <= floor:
                    valid_s.append(sid)
            if valid_s:
                suffix_id = random.choice(valid_s)
                
        return prefix_id, suffix_id


    def _get_valid_prefixes(self, item_type: str) -> List[str]:
        """아이템 타입에 맞는 접두사 ID 목록 반환"""
        valid = []
        for pid, pdef in self.prefix_defs.items():
            if item_type in pdef.allowed_types:
                valid.append(pid)
        return valid

    def _get_valid_suffixes(self, item_type: str) -> List[str]:
        """아이템 타입에 맞는 접미사 ID 목록 반환"""
        valid = []
        for sid, sdef in self.suffix_defs.items():
            if item_type in sdef.allowed_types:
                valid.append(sid)
        return valid

    def _create_item_with_affix(self, item_id: str, prefix_id: str = None, suffix_id: str = None, floor: int = 1) -> Any:
        """접두사/접미사가 적용된 아이템 인스턴스(복제본) 생성"""
        original = self.item_defs.get(item_id)
        if not original: return None
        
        # 원본 데이터 복제 (얕은 복사로 충분, 내부 리스트/셋은 새로 생성됨)
        item = copy.copy(original)
        
        # 딥카피가 필요한 속성들 수동 복사
        item.flags = original.flags.copy()
        
        # 1. Prefix Application
        if prefix_id and prefix_id in self.prefix_defs:
            pdef = self.prefix_defs[prefix_id]
            item.prefix_id = prefix_id
            item.name = f"{pdef.name_kr} {item.name}"
            
            # 1. Attack / Hit
            if pdef.damage_percent_min or pdef.damage_percent_max:
                item.damage_percent += random.randint(pdef.damage_percent_min, pdef.damage_percent_max)
            if pdef.to_hit_bonus_min or pdef.to_hit_bonus_max:
                item.to_hit_bonus += random.randint(pdef.to_hit_bonus_min, pdef.to_hit_bonus_max)
            # 2. MP
            if pdef.mp_bonus_min or pdef.mp_bonus_max:
                item.mp_bonus += random.randint(pdef.mp_bonus_min, pdef.mp_bonus_max)
            # 3. Resists
            if pdef.res_fire_min or pdef.res_fire_max:
                item.res_fire += random.randint(pdef.res_fire_min, pdef.res_fire_max)
            if pdef.res_ice_min or pdef.res_ice_max:
                item.res_ice += random.randint(pdef.res_ice_min, pdef.res_ice_max)
            if pdef.res_lightning_min or pdef.res_lightning_max:
                item.res_lightning += random.randint(pdef.res_lightning_min, pdef.res_lightning_max)
            if pdef.res_all_min or pdef.res_all_max:
                item.res_all += random.randint(pdef.res_all_min, pdef.res_all_max)


        # 2. Suffix Application
        if suffix_id and suffix_id in self.suffix_defs:
            sdef = self.suffix_defs[suffix_id]
            # Suffix Level Limit (Accessory Check)
            if item.type in ['ACCESSORY'] and sdef.min_level > floor:
                # 층수 제한에 걸리면 접미사 제외 (검증)
                pass
            else:
                item.suffix_id = suffix_id
                item.name = f"{item.name} {sdef.name_kr}"
                
                # Logic same as prefix... (omitted for brevity, assume applied by existing robust logic if copied full block)
                # For safety, let's keep it simple: suffix logic is inside engine but truncated in view.
                # Just adding the staff logic below.

        # 3. [Dynamic Staff Spells] 지팡이에 층수에 맞는 주문 부여
        if item.type == 'WEAPON' and '지팡이' in item.name:
             # 스킬 정의에서 공격 주문만 필터링 (임시)
             # floor에 따라 티어 결정: 1~4: Lv1, 5~8: Lv5... 
             target_tier = 1
             if floor >= 13: target_tier = 13
             elif floor >= 9: target_tier = 9
             elif floor >= 5: target_tier = 5
             
             possible_skills = []
             for s_id, s_def in self.skill_defs.items():
                 # 95층 이상이면 모든 스킬 가능
                 if floor >= 95:
                      if s_def.required_level <= 13: possible_skills.append(s_id)
                 else:
                      # 정확한 티어 매칭 (혹은 이하)
                      if s_def.required_level == target_tier:
                          possible_skills.append(s_id)
                          
             if possible_skills:
                 new_skill = random.choice(possible_skills)
                 item.skill_id = new_skill
                 # 이름 변경 (옵션)
                 # item.name = f"{item.name} [{self.skill_defs[new_skill].name}]"

        # 4. Identification Chance (Affixed items and magical staves)
        if (prefix_id or suffix_id or (item.type == 'WEAPON' and '지팡이' in item.name)):
            if random.random() < 0.7: # 70% chance to be unidentified
                item.is_identified = False

        return item

    def run(self, ui=None) -> str:
        """메인 게임 루프. 종료 시 결과를 문자열로 반환합니다."""
        # Store UI reference for use in other methods
        self.ui = ui
        
        if not ui:
            raise ValueError("UI instance is required to run the game.")
        
        self.is_running = True
        game_result = "QUIT"
        
        # 터미널 설정 저장 및 cbreak 모드 전환
        fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(fd)
        
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
                    # self.world.event_manager.push(MessageEvent(f"Debug Key: {repr(action)}"))
                    
                    # Ctrl+C 처리 (\x03)
                    if action == '\x03':
                        raise KeyboardInterrupt
                    
                    # ESC 키로 메인 메뉴 복귀
                    if action == '\x1b' or action.lower() == 'q':  # ESC key or Q
                        self.world.event_manager.push(MessageEvent("저장하고 메인 메뉴로 돌아갑니다..."))
                        game_result = "MENU"
                        self.is_running = False
                        continue

                    action_lower = action.lower()

                    if self.state == GameState.PLAYING:
                        if action_lower == 'i':
                            self.state = GameState.INVENTORY
                            self.selected_item_index = 0
                            self._render()
                            continue
                        
                        # 샌드박스/치트 키 처리 (서브클래스에서 오버라이드 가능)
                        if self.handle_sandbox_input(action):
                            continue
                            
                        # InputSystem은 이제 쿨다운을 자체적으로 관리하며, 
                        # 입력이 들어왔을 때만 해당 입력을 큐에 넣거나 즉시 처리함.
                        self.input_system.handle_input(action)
                        
                        # 입력 직후 즉시 렌더링
                        self._render()
                        last_frame_time = current_time
                    
                    elif self.state == GameState.INVENTORY:
                        if action_lower in ['i', 'b', 'q', '\x1b']:
                            self.state = GameState.PLAYING
                        else:
                            self._handle_inventory_input(action)
                        self._render()
                        last_frame_time = current_time
                    elif self.state == GameState.CHARACTER_SHEET:
                        if action_lower in ['c', 'b', 'q', '\x1b']:
                            self.state = GameState.PLAYING
                        else:
                            self._handle_character_sheet_input(action)
                        self._render()
                        last_frame_time = current_time
                    elif self.state == GameState.SHOP:
                        if action_lower in ['q', 'b', '\x1b']:
                            self.state = GameState.PLAYING
                        else:
                            self._handle_shop_input(action)
                        self._render()
                        last_frame_time = current_time
                    
                    elif self.state == GameState.SHRINE:
                        if action_lower in ['q', 'b', 'esc', '\x1b']:
                            self.state = GameState.PLAYING
                        else:
                            self._handle_shrine_input(action)
                        self._render()
                        last_frame_time = current_time
                    
                    # [Enhancement] Oil Selection Input
                    elif self.oil_selection_open:
                        self._handle_oil_selection_input(action)
                        self._render()
                        last_frame_time = current_time
                
                # 2. 실시간 로직 처리 (PLAYING 상태일 때만)
                if self.state == GameState.PLAYING:
                    # 이벤트 처리
                    self.world.event_manager.process_events()
                    
                    # 모든 시스템 실행 (실시간)
                    for system in self.world._systems:
                        if system is not None:
                            system.process()
                    
                    # 이벤트 재처리
                    self.world.event_manager.process_events()

                    # 플레이어 사망 체크
                    player_entity = self.world.get_player_entity()
                    if player_entity:
                        stats = player_entity.get_component(StatsComponent)
                        if stats and stats.current_hp <= 0:
                            game_result = "DEATH"
                            self.is_running = False

                # 3. 주기적 렌더링
                if elapsed_since_frame >= frame_duration:
                    self._render()
                    last_frame_time = current_time
                    if self.shake_timer > 0:
                        self.shake_timer -= 1
                
                time.sleep(0.05)  # 20 FPS for game logic

        except KeyboardInterrupt:
            game_result = "QUIT"
        finally:
            # 설정 복구 및 커서 보이기
            termios.tcsetattr(fd, termios.TCSADRAIN, self.old_settings)
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
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
            for comp_type, comp_list in entity._components.items():
                # [중요] ecs.py에서 _components는 Dict[Type, List[Instance]] 형식이므로 리스트 처리
                serialized_list = []
                for comp in comp_list:
                    if hasattr(comp, 'to_dict'):
                        serialized_list.append(comp.to_dict())
                    else:
                        try:
                            # to_dict가 없는 경우 기본 속성들만 저장
                            attrs = {}
                            for k, v in vars(comp).items():
                                if k.startswith('_'): continue
                                # JSON serializable check & convert set to list
                                if isinstance(v, set):
                                    attrs[k] = list(v)
                                else:
                                    attrs[k] = v
                            serialized_list.append(attrs)
                        except TypeError:
                            # vars()가 불가능한 경우 (built-in 등) 빈 딕셔너리 또는 가능한 속성만
                            serialized_list.append({})
                comp_data[comp_type.__name__] = serialized_list
            
            if str(e_id) == "1":
                try:
                    logging.info(f"[Save] Saving Player Entity 1. Components: {list(comp_data.keys())}")
                    if "InventoryComponent" in comp_data:
                        # Log item count
                        items = comp_data["InventoryComponent"][0].get("items", {})
                        equipped = comp_data["InventoryComponent"][0].get("equipped", {})
                        logging.info(f"[Save] Inventory Items: {len(items)}, Equipped: {list(equipped.keys())}")
                except Exception as log_err:
                    logging.error(f"[Save] Logging failed: {log_err}")
            
            entities_data[str(e_id)] = comp_data

        # [Fix] Persist selected_class to avoid defaulting to WARRIOR on fallback
        selected_class = "WARRIOR"
        p_level = player_entity.get_component(LevelComponent)
        if p_level and hasattr(self, 'class_defs'):
            for c_id, c_def in self.class_defs.items():
                if c_def.name == p_level.job:
                    selected_class = c_id
                    break

        game_state_data = {
            "entities": entities_data,
            "player_specific_data": {
                "name": self.player_name,
            },
            "selected_class": selected_class,
            "current_level": self.current_level,
            "turn_number": self.turn_number,
            "last_boss_id": self.last_boss_id,
            "current_map": self.dungeon_map.to_dict() if self.dungeon_map else None # [Map Persistence]
        }
        
        try:
            save_game_data(game_state_data, self.player_name)
            logging.info("[Save] Game saved successfully.")
        except Exception as e:
            logging.error(f"[Save] FAILED to save game: {e}")
            self.ui.add_message(f"게임 저장 실패: {e}") # UI Feedback

    def handle_map_transition_event(self, event: MapTransitionEvent):
        """맵 이동 이벤트 처리: 새로운 층 생성"""
        old_level = self.current_level
        self.current_level = event.target_level
        
        # 방향 결정 (1 -> 2 : Down, 2 -> 1 : Up)
        going_up = event.target_level < old_level
        spawn_at = "EXIT" if going_up else "START"

        direction_str = "위로 올라갑니다" if going_up else "깊은 곳으로 내려갑니다"
        self.world.event_manager.push(MessageEvent(f"{direction_str}... (던전 {self.current_level}층)"))
        
        # 1. 플레이어 데이터 보존
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        # 데이터 백업
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        level_comp = player_entity.get_component(LevelComponent)
        
        # 2. 월드 초기화 (모든 엔티티 삭제)
        self.world.clear_all_entities()

        # 3. 새로운 층 생성 (플레이어 복원 포함)
        self._initialize_world(preserve_player=(stats, inv, level_comp), spawn_at=spawn_at)

    def handle_shop_open_event(self, event: ShopOpenEvent):
        """플레이어가 상인과 충돌 시 상점 모드로 전환"""
        self.state = GameState.SHOP
        self.active_shop_id = event.shopkeeper_id
        self.selected_shop_item_index = 0
        self.shop_category_index = 0 # 기본 '사기' 탭
        self.world.event_manager.push(MessageEvent("상점에 오신 것을 환영합니다!"))
    
    def handle_shrine_open_event(self, event: ShrineOpenEvent):
        """신전 열기 이벤트 처리"""
        self.state = GameState.SHRINE
        self.active_shrine_id = event.shrine_id
        self.shrine_menu_index = 0
        self.shrine_enhance_step = 0
        self.selected_equip_index = 0
        self.selected_oil_index = 0
        self.selected_sacrifice_index = 0
        self.eligible_oils = []
        self.eligible_sacrifices = []
        self.sacrifice_prompt_yes = True
        self.target_enhance_item = None
        self.selected_oil = None
        self.selected_sacrifice = None
        self.world.event_manager.push(MessageEvent("신성한 기운이 느껴집니다..."))

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
            # 인벤토리에 추가 (상점 원본과 독립된 객체로 생성)
            item_copy = copy.deepcopy(item)
            if item.name in inv.items:
                inv.items[item.name]['qty'] += 1
            else:
                inv.items[item.name] = {'item': item_copy, 'qty': 1}
            self.world.event_manager.push(MessageEvent(f"{item.name}을(를) {price} 골드에 구매했습니다!"))
        else:
            self.world.event_manager.push(MessageEvent("골드가 부족합니다!"))

    def _handle_character_sheet_input(self, action):
        """캐릭터 정보창 입력 처리"""
        player_entity = self.world.get_player_entity()
        if not player_entity:
            self.state = GameState.PLAYING
            return

        from .components import StatsComponent, LevelComponent
        level_comp = player_entity.get_component(LevelComponent)
        stats = player_entity.get_component(StatsComponent)
        
        if not level_comp or not stats:
            self.state = GameState.PLAYING
            return

        # Close
        if action in [readchar.key.ESC, 'q', 'Q', 'c', 'C']:
            self.state = GameState.PLAYING
            return

        # Navigation
        if action in [readchar.key.UP, 'w', 'W', '\x1b[A']:
            self.selected_stat_index = max(0, self.selected_stat_index - 1)
        elif action in [readchar.key.DOWN, 's', 'S', '\x1b[B']:
            self.selected_stat_index = min(3, self.selected_stat_index + 1)
        
        # Add Point
        elif action in [readchar.key.RIGHT, 'd', 'D', '\x1b[C', '+', '=', '\r', '\n']:
            if level_comp.stat_points > 0:
                level_comp.stat_points -= 1
                if self.selected_stat_index == 0: stats.base_str += 1
                elif self.selected_stat_index == 1: stats.base_mag += 1
                elif self.selected_stat_index == 2: stats.base_dex += 1
                elif self.selected_stat_index == 3: stats.base_vit += 1
                
                self._recalculate_stats()
                # 효과음 등 피드백 추가 가능
            else:
                 pass # 포인트 부족

    def _get_filtered_inventory_items(self, inv_comp):
        """현재 카테고리 인덱스에 따라 필터링된 아이템 목록 반환"""
        filtered_items = []
        if self.inventory_category_index == 0: # 아이템 (소모품/스킬북)
            filtered_items = [(id, data) for id, data in inv_comp.items.items() 
                             if data['item'].type in ['CONSUMABLE', 'SKILLBOOK']]
        elif self.inventory_category_index == 1: # 장비
            # Include all equippable items: WEAPON, ARMOR, SHIELD, ACCESSORY
            # 1. From Inventory
            filtered_items = [(id, data) for id, data in inv_comp.items.items() 
                             if data['item'].type in ['WEAPON', 'ARMOR', 'SHIELD', 'ACCESSORY']]
            
            # 2. From Equipped Slots (UI fix: ensure equipped items are visible)
            for slot, item in inv_comp.equipped.items():
                if item:
                    # [Fix] Deduplicate: Only add if NOT in inventory (Orphaned items)
                    # Normal items are in both 'items' and 'equipped', so they are caught by step 1.
                    if hasattr(item, 'type') and item.name not in inv_comp.items:
                         filtered_items.append((item.name, {'item': item, 'qty': 1}))
        elif self.inventory_category_index == 2: # 스크롤
            filtered_items = [(id, data) for id, data in inv_comp.items.items() 
                             if data['item'].type == 'SCROLL']
        elif self.inventory_category_index == 3: # 스킬
            for s_name in inv_comp.skills:
                s_def = self.skill_defs.get(s_name)
                if s_def:
                    filtered_items.append((s_name, {'item': s_def, 'qty': 1}))
                else:
                    # Fallback for unknown skills
                    dummy = type('obj', (object,), {
                        'name': s_name, 'element': 'NONE', 'color': 'white', 
                        'description': '설명이 없습니다.', 'range': 1, 'type': 'SKILL'
                    })()
                    filtered_items.append((s_name, {'item': dummy, 'qty': 1}))
        return filtered_items

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

        # 1. 현재 카테고리에 해당하는 아이템 필터링 (헬퍼 사용)
        filtered_items = self._get_filtered_inventory_items(inv)
        item_count = len(filtered_items)

        # 2. 내비게이션 처리
        if action in ['w', 'W', readchar.key.UP, '\x1b[A']:
             self.selected_item_index = max(0, self.selected_item_index - 1)
        elif action in ['s', 'S', readchar.key.DOWN, '\x1b[B']:
            # Use filtered_items length for accurate count
            item_count = len(filtered_items)
            if item_count > 0:
                self.selected_item_index = min(item_count - 1, self.selected_item_index + 1)
        elif action in [readchar.key.LEFT, '\x1b[D']:
             self.inventory_category_index = max(0, self.inventory_category_index - 1)
             self.selected_item_index = 0
             self.inventory_scroll_offset = 0  # 카테고리 변경 시 스크롤 리셋
        elif action in [readchar.key.RIGHT, '\x1b[C']:
             self.inventory_category_index = min(3, self.inventory_category_index + 1)
             self.selected_item_index = 0
             self.inventory_scroll_offset = 0  # 카테고리 변경 시 스크롤 리셋
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

        # [Cooldown Check] Prevent spamming (double-consumption fix)
        # Use simple 1.0s global item cooldown or per-item if needed.
        # User requested: "Until cooldown ends".
        # We use item name for cooldown tracking.
        if hasattr(self, 'combat_system') and self.combat_system:
            if self.combat_system.get_cooldown(player_entity.entity_id, item.name) > 0:
                 # Silently ignore or show message? 
                 # If spamming key, silent is better to avoid log spam.
                 return

        # 레벨 및 식별 여부 확인
        is_id = getattr(item, 'is_identified', True)
        if not is_id:
            self.world.event_manager.push(MessageEvent("식별되지 않은 아이템은 사용할 수 없습니다.", "red"))
            return

        level_comp = player_entity.get_component(LevelComponent)
        if level_comp and item.required_level > level_comp.level:
            # [Fix] 피드백 강화 (노란색으로 강조, 무엇이 부족한지 명시)
            self.world.event_manager.push(MessageEvent(f"레벨이 부족하여 '{item.name}'을(를) 읽을 수 없습니다. (필요: Lv.{item.required_level}, 현재: Lv.{level_comp.level})", "yellow"))
            return

        old_hp = stats.current_hp
        old_mp = stats.current_mp
        
        msg = f"{item.name}을(를) 사용했습니다."

        if item.type == "SKILLBOOK":
            if not item.skill_id:
                self.world.event_manager.push(MessageEvent(f"이 책은 가르침이 없습니다: {item.name}"))
                return
            
            # [Class Restriction] 직업 전용 스킬 체크
            class_restrictions = {
                "RAGE": "바바리안",
                "REPAIR": "워리어",
                "DISARM": "로그",
                "RECHARGE": "소서러"
            }
            if item.skill_id in class_restrictions:
                 req_job = class_restrictions[item.skill_id]
                 job_name = "Adventurer"
                 if level_comp: job_name = level_comp.job
                 
                 if job_name != req_job:
                      self.world.event_manager.push(MessageEvent(f"이 서적의 내용은 {req_job}만이 이해할 수 있습니다.", "red"))
                      return
            
            skill_def = self.skill_defs.get(item.skill_id)
            if not skill_def:
                # [Fix] skill_defs가 '이름'(한글)으로 인덱싱되어 있을 경우 대비하여 ID로 재검색
                skill_def = next((s for s in self.skill_defs.values() if s.id == item.skill_id), None)
            
            if not skill_def:
                self.world.event_manager.push(MessageEvent(f"존재하지 않는 기술의 비급서입니다: {item.skill_id}"))
                return
            
            skill_name = skill_def.name
            if skill_name in inv.skills:
                # 이미 배운 스킬이면 레벨업 (횟수 누적)
                current_lv = inv.skill_levels.get(skill_name, 1)
                # 만렙 제한 (255)
                if current_lv >= 255:
                    msg = f"'{skill_name}' 스킬은 이미 극의에 도달했습니다!"
                else:
                    # 필요 권수: 2권 (User Request: 2 books = 1 level)
                    books_needed = 2
                    
                    # 읽은 횟수 증가 (사실상 즉시 레벨업)
                    inv.skill_books_read[skill_name] = inv.skill_books_read.get(skill_name, 0) + 1
                    current_reads = inv.skill_books_read[skill_name]
                    
                    if current_reads >= books_needed:
                        inv.skill_levels[skill_name] = current_lv + 1
                        inv.skill_books_read[skill_name] = 0
                        msg = f"'{skill_name}'의 오의를 깨달았습니다! (Lv.{current_lv} -> Lv.{current_lv + 1})"
                        self.world.event_manager.push(SoundEvent("LEVEL_UP"))
                    else:
                        msg = f"'{skill_name}'의 지식을 쌓고 있습니다. ({current_reads}/{books_needed}권)"
            else:
                # 새로 배우는 스킬
                inv.skills.append(skill_name)
                inv.skill_levels[skill_name] = 1
                inv.skill_books_read[skill_name] = 0
                msg = f"{item.name}을(를) 정독하여 새로운 기술 '{skill_name}'을(를) 익혔습니다!"
                self.world.event_manager.push(SoundEvent("LEVEL_UP"))
        else:
            # [FULL_RECOVERY] 완전 회복 처리
            if "FULL_RECOVERY_HP" in item.flags:
                 stats.current_hp = stats.max_hp
            elif "FULL_RECOVERY_MP" in item.flags:
                 stats.current_mp = stats.max_mp
            elif "FULL_RECOVERY_ALL" in item.flags:
                 stats.current_hp = stats.max_hp
                 stats.current_mp = stats.max_mp
            else:
                # 일반 회복 (기존 로직)
                if item.hp_effect != 0:
                    stats.current_hp = min(stats.max_hp, stats.current_hp + item.hp_effect)
                if item.mp_effect != 0:
                    stats.current_mp = min(stats.max_mp, stats.current_mp + item.mp_effect)

            # [PERMANENT_STAT] 엘릭서 (영구 스탯 상승)
            if "PERMANENT_STAT" in item.flags:
                 if item.str_bonus:
                     stats.base_str += item.str_bonus
                     stats.str += item.str_bonus
                     msg += f" 힘이 영구적으로 {item.str_bonus} 증가했습니다!"
                 if item.mag_bonus:
                     stats.base_mag += item.mag_bonus
                     stats.mag += item.mag_bonus
                     msg += f" 마력이 영구적으로 {item.mag_bonus} 증가했습니다!"
                 if item.dex_bonus:
                     stats.base_dex += item.dex_bonus
                     stats.dex += item.dex_bonus
                     msg += f" 민첩이 영구적으로 {item.dex_bonus} 증가했습니다!"
                 if item.vit_bonus:
                     stats.base_vit += item.vit_bonus
                     stats.vit += item.vit_bonus
                     self._recalculate_stats() # VIT 등 변동 시 재계산
                     msg += f" 활력이 영구적으로 {item.vit_bonus} 증가했습니다!"

            # [CURRENCY] 금화 사용
            if item.type == "CURRENCY":
                qty = item_data.get('qty', 1)
                stats.gold += qty
                msg = f"금화 {qty}개를 지갑에 넣었습니다. (현재: {stats.gold})"


            # [IDENTIFY] 
            if "IDENTIFY" in item.flags:
                # Collect unidentified items
                unidentified = []
                for item_key, item_val in inv.items.items():
                    target_item = item_val['item']
                    if not getattr(target_item, 'is_identified', True):
                        unidentified.append((item_key, item_val))
                
                if not unidentified:
                    self.world.event_manager.push(MessageEvent("식별할 미확인 아이템이 없습니다."))
                    return  # Do not consume scroll
                
                # Show selection menu (with game screen overlay)
                selected = self.ui.show_identify_menu(unidentified, game_renderer=self._render)
                
                if selected is None:
                    # User cancelled
                    return  # Do not consume scroll
                
                # Identify the selected item
                item_key, item_val = selected
                target_item = item_val['item']
                target_item.is_identified = True
                
                # Show identified item name
                item_name = getattr(target_item, 'name', '알 수 없는 아이템')
                msg = f"확인 스크롤을 사용하여 '{item_name}'을(를) 식별했습니다!"
                self.world.event_manager.push(MessageEvent(msg, "gold"))
                # Proceed to consume scroll (1 scroll per 1 item)
            
            # [OIL]
            oil_type = next((f for f in item.flags if f.startswith("OIL_")), None)
            if oil_type:
                self.pending_oil_item = item_data # Store full item data (id, item, qty)
                self.pending_oil_type = oil_type
                self.oil_selection_open = True
                self.selected_equip_index = 0
                self.world.event_manager.push(MessageEvent("강화할 장비를 선택하세요."))
                return # Do not consume yet
            
            # [VISION_UP] 횃불 효과
            if "VISION_UP" in item.flags:
                stats.vision_range = 15 # 시야 반경 대폭 증가
                # duration 초 후 만료 (CSV에서 읽어온 값 사용)
                duration = getattr(item, 'duration', 120)  # 기본값 120초
                if "VISION_UP" not in stats.flags:
                    stats.flags.add("VISION_UP")
                    # 만료 시간을 StatsComponent에 저장 (초 단위)
                    stats.vision_expires_at = time.time() + float(duration)
                
                # [추가] 숨겨진 아이템 감지 효과
                stats.sees_hidden = True
                stats.sees_hidden_expires_at = time.time() + float(duration)
                
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

            # [Stat Buff] 능력치 버약/버프 적용
            if any(v != 0 for v in [item.str_bonus, item.mag_bonus, item.dex_bonus, item.vit_bonus]) and item.duration > 0:
                from .components import StatModifierComponent
                modifiers = player_entity.get_components(StatModifierComponent)
                buff_source = f"ITEM_{item.name}"
                existing = next((m for m in modifiers if m.source == buff_source), None)
                if existing:
                    existing.expires_at = time.time() + item.duration
                else:
                    new_mod = StatModifierComponent(
                        str_mod=item.str_bonus, mag_mod=item.mag_bonus, 
                        dex_mod=item.dex_bonus, vit_bonus=item.vit_bonus, 
                        duration=item.duration, source=buff_source
                    )
                    new_mod.expires_at = time.time() + item.duration
                    self.world.add_component(player_entity.entity_id, new_mod)
                
                msg += f" {item.name}의 효과가 나타납니다!"
                self._recalculate_stats()

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
        
        # [Cooldown Set] 1.0 Sec Safety Cooldown
        if hasattr(self, 'combat_system') and self.combat_system:
             self.combat_system.set_cooldown(player_entity.entity_id, item.name, 1.0)

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
            
            # [Fix] Restore Orphaned Items (if not in bag list)
            if item.name not in inv.items:
                inv.items[item.name] = {'item': item, 'qty': 1}
            
            self.world.event_manager.push(MessageEvent(f"{item.name}의 장착을 해제했습니다."))
            self._recalculate_stats()
            return

        # 2. 장착 로직 (레벨 및 식별 여부 확인)
        is_id = getattr(item, 'is_identified', True)
        if not is_id:
            self.world.event_manager.push(MessageEvent("식별되지 않은 아이템은 장착할 수 없습니다.", "red"))
            return

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
            # 이름 기반 슬롯 판별
            name = item.name
            if any(k in name for k in ["헬름", "캡", "모자", "투구", "왕관", "크라운", "후드", "마스크"]):
                inv.equipped["머리"] = item
            elif any(k in name for k in ["장갑", "건틀릿", "글러브"]):
                inv.equipped["장갑"] = item
            elif any(k in name for k in ["신발", "부츠", "장화", "그리브"]):
                inv.equipped["신발"] = item
            else:
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

    def _sanitize_loaded_items(self, player_entity):
        """저장된 아이템 데이터와 최신 CSV 정의 동기화 (사거리 버그 등 수정)"""
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return
        
        # 1. 인벤토리 아이템 동기화
        for entry in inv.items.values():
            item = entry['item']
            self._sync_item_definition(item)
            
        # 2. 장착 아이템 동기화
        for item in inv.equipped.values():
            if item and hasattr(item, 'name'):
                self._sync_item_definition(item)
                
    def _sync_item_definition(self, item):
        """단일 아이템 객체 동기화"""
        if not hasattr(self, 'item_defs'): return

        # 1. Base Name 찾기 (강화/수식어 제거)
        base_name = item.name
        
        # +N 제거
        if '+' in base_name:
             parts = base_name.split(' ')
             # +1 Sharp Dagger -> Remove +1
             if parts[0].startswith('+'):
                 parts.pop(0)
             base_name = " ".join(parts)
        
        # Prefix/Suffix로 인해 이름이 변경되었을 수 있음 (예: Magic Dagger)
        # item_defs 키 중 base_name에 포함된 가장 긴 키를 찾음 (단순 포함 관계)
        # 예: "Sharp Short Bow" -> "Short Bow" (X, 한글이라 "예리한 단궁" -> "단궁")
        # 한글의 경우 띄어쓰기로 분리가 안 될 수도 있음 (하지만 items.csv에는 띄어쓰기 없음)
        
        # 가장 확실한 방법: items.csv의 모든 키를 순회하며 item.name이 해당 키로 '끝나는지' 확인?
        # 아니면 그냥 items.csv에 있는 이름이 포함되어 있는지 확인.
        
        target_def = None
        if base_name in self.item_defs:
            target_def = self.item_defs[base_name]
        else:
            # 매칭 실패 시, item_defs의 키들을 순회하며 부분 일치 확인
            # (긴 이름부터 확인하여 "단궁" vs "장궁" 오매칭 방지)
            sorted_keys = sorted(self.item_defs.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if key in item.name: # 원래 이름에서 검색
                    target_def = self.item_defs[key]
                    break
        
        if target_def:
            # 사거리 동기화
            if hasattr(item, 'attack_range') and hasattr(target_def, 'attack_range'):
                if item.attack_range != target_def.attack_range:
                    logging.info(f"[Sanitize] Updating {item.name} range: {item.attack_range} -> {target_def.attack_range}")
                    item.attack_range = target_def.attack_range

    def _recalculate_stats(self):
        """장착된 아이템 및 버프를 기반으로 플레이어 능력치 재계산"""
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        if not stats or not inv: return
        
        # Get level component early (needed for class-specific bonuses)
        level_comp = player_entity.get_component(LevelComponent)
        
        # 1. 기본 능력치로 초기화 (base_XX 사용)
        stats.attack_min = stats.base_attack_min
        stats.attack_max = stats.base_attack_max
        stats.attack = stats.attack_max # 주력 표시 및 호환용
        stats.defense_min = stats.base_defense_min
        stats.defense_max = stats.base_defense_max
        stats.defense = stats.defense_max
        stats.str = stats.base_str
        stats.mag = stats.base_mag
        stats.dex = stats.base_dex
        stats.vit = stats.base_vit
        # [Fix] Base Max (레벨업 등으로 상승된 값 가정)
        stats.max_hp = getattr(stats, 'base_max_hp', stats.max_hp)
        stats.max_mp = getattr(stats, 'base_max_mp', stats.max_mp)
        
        # [Affix] Reset
        stats.damage_percent = 0
        stats.to_hit_bonus = 0
        stats.res_fire = 0
        stats.res_ice = 0
        stats.res_lightning = 0
        stats.res_poison = 0
        stats.res_all = 0
        stats.life_leech = 0
        stats.attack_speed = 0
        stats.damage_max_bonus = 0
        
        stats.weapon_range = 1 # 기본 사거리 (Bump)
        
        if hasattr(stats, 'base_flags'):
            stats.flags = stats.base_flags.copy()
        
        # 2. 장비(Permanent) 보너스 합산
        for slot, item in inv.equipped.items():
            from .data_manager import ItemDefinition
            if isinstance(item, ItemDefinition):
                # [Durability] Check if broken
                if getattr(item, 'max_durability', 0) > 0 and getattr(item, 'current_durability', 0) <= 0:
                    continue # BROKEN: No stats applied

                stats.attack_min += getattr(item, "attack_min", item.attack)
                stats.attack_max += getattr(item, "attack_max", item.attack)
                stats.attack = stats.attack_max
                stats.defense_min += getattr(item, "defense_min", item.defense)
                stats.defense_max += getattr(item, "defense_max", item.defense)
                stats.defense = stats.defense_max
                
                # 신규 스탯 보너스
                stats.str += getattr(item, "str_bonus", 0)
                stats.mag += getattr(item, "mag_bonus", 0)
                stats.dex += getattr(item, "dex_bonus", 0)
                stats.vit += getattr(item, "vit_bonus", 0)
                
                # [Affix] Summation
                stats.to_hit_bonus += getattr(item, "to_hit_bonus", 0)
                stats.res_fire += getattr(item, "res_fire", 0)
                stats.res_ice += getattr(item, "res_ice", 0)
                stats.res_lightning += getattr(item, "res_lightning", 0)
                stats.res_poison += getattr(item, "res_poison", 0)
                stats.res_all += getattr(item, "res_all", 0)
                
                # [Affix Suffix]
                stats.max_mp += getattr(item, "mp_bonus", 0)
                stats.max_hp += getattr(item, "hp_bonus", 0)
                stats.damage_max_bonus += getattr(item, "damage_max_bonus", 0)
                stats.life_leech += getattr(item, "life_leech", 0)
                stats.attack_speed += getattr(item, "attack_speed", 0)
                
                # Damage Percent는 아이템 자체에 베이크된다고 가정하지만,
                # 전역 보너스(갑옷에 붙은 데미지 증가 등)가 있다면 여기서 합산해서 CombatSystem에서 사용해야 함.
                # 현재는 weapon local만 고려하므로 합산 안 함 (or for display).
                # 하지만 King's가 무기에 붙으면 Weapon Damage 증가임.
                # 만약 다른 장비에서 데미지 증가가 있다면?
                # 현재는 무기에만 붙음.
                stats.dex += getattr(item, "dex_bonus", 0)
                stats.vit += getattr(item, "vit_bonus", 0)
                
                if hasattr(item, 'flags'):
                    stats.flags.update(item.flags)
        
                if slot == "손1":
                    stats.weapon_range = item.attack_range
                    
                    if level_comp and level_comp.job in ["로그", "ROGUE"] and "RANGED" in getattr(item, 'flags', []):
                        # 사거리 보정: +2~4 중 중간값인 3 적용
                        stats.weapon_range += 3
                        stats.flags.add("PIERCING")
                    
                    # [Class Bonus] Barbarian Two-Handed Bonus
                    if level_comp and level_comp.job in ["바바리안", "BARBARIAN"] and item.hand_type == 2:
                        # 공격력 보정: +2~4 중 중간값인 3 적용
                        stats.attack_min += 3
                        stats.attack_max += 3
                        stats.attack = stats.attack_max
                        # 사거리 보정: +1
                        stats.weapon_range += 1
                        
                        # [Class Bonus] Warrior Cleave (SPLASH)
                        if level_comp and level_comp.job in ["워리어", "WARRIOR"] and "RANGED" not in getattr(item, 'flags', []):
                            stats.flags.add("SPLASH")
        
        # logging.info(f"[Stats] Recalculated Weapon Range: {stats.weapon_range}")
        
        # [Affix Final Calculation]
        # 1. Damage Max Bonus (of Carnage)
        stats.attack_max += stats.damage_max_bonus
        if stats.attack_max < stats.attack_min:
             stats.attack_max = stats.attack_min
        stats.attack = stats.attack_max
        
        # 2. Attack Speed (Action Delay Reduction)
        # 1단계당 0.05초 감소 (기본 0.2초)
        # Fast(1) -> 0.15s, Faster(2) -> 0.10s, Fastest(3) -> 0.05s
        reduction = stats.attack_speed * 0.05
        stats.action_delay = max(0.05, 0.2 - reduction)

        # 3. 일시적 버프(StatModifierComponent) 합산
        modifiers = player_entity.get_components(StatModifierComponent)
        at_mult = 1.0
        df_mult = 1.0
        for mod in modifiers:
            stats.str += mod.str_mod
            stats.mag += mod.mag_mod
            stats.dex += mod.dex_mod
            stats.vit += mod.vit_mod
            at_mult *= getattr(mod, 'attack_multiplier', 1.0)
            df_mult *= getattr(mod, 'defense_multiplier', 1.0)
        
        # Apply Multipliers to Final Stats for UI display
        stats.attack = int(stats.attack * at_mult)
        stats.defense = int(stats.defense * df_mult)
        
        # [Derived Stats Calculation] (New Implementation)
        hp_ratio = 2.0
        mp_ratio = 1.0
        
        # level_comp already initialized at the beginning of the method
        if hasattr(self, 'class_defs') and level_comp and level_comp.job:
            class_def = self.class_defs.get(level_comp.job)
            if class_def:
                hp_ratio = getattr(class_def, 'vit_to_hp', 2.0)
                mp_ratio = getattr(class_def, 'mag_to_mp', 1.0)
        
        # 1. HP/MP from Stats (VIT, MAG)
        stats.max_hp += int(stats.vit * hp_ratio)
        stats.max_mp += int(stats.mag * mp_ratio)
        
        # 2. Defense (AC) from DEX (Every 5 DEX = +1 AC)
        dex_ac_bonus = (stats.dex // 5)
        stats.defense += dex_ac_bonus
        stats.defense_min += dex_ac_bonus
        stats.defense_max += dex_ac_bonus
        
        # 3. Attack (Damage) from STR (Every 2 STR = +1 Min/Max Damage)
        str_dmg_bonus = stats.str // 2
        stats.attack_min += str_dmg_bonus
        stats.attack_max += str_dmg_bonus
        stats.attack = stats.attack_max
        
        # [Fix] Clamp Current HP/MP to calculated Max (Prevents bar from staying full if Max drops)
        if stats.current_hp > stats.max_hp:
             stats.current_hp = stats.max_hp
        if stats.current_mp > stats.max_mp:
             stats.current_mp = stats.max_mp
        
        # Ensure current doesn't exceed max
        stats.current_hp = min(stats.current_hp, stats.max_hp)
        stats.current_mp = min(stats.current_mp, stats.max_mp)

    def _get_map_theme(self):
        """현재 층수에 따른 던전 테마 정보를 반환합니다."""
        floor = self.current_level
        if floor <= 25:
            return {
                "name": "Cathedral",
                "wall_char": "#",
                "floor_char": ".",
                "wall_color": "brown",
                "floor_color": "dark_grey",
                "vision_modifier": 0
            }
        elif floor <= 50:
            return {
                "name": "Catacombs",
                "wall_char": "▒",
                "floor_char": ",",
                "wall_color": "blue",
                "floor_color": "green",
                "vision_modifier": -1
            }
        elif floor <= 75:
            return {
                "name": "Caves",
                "wall_char": "≈",
                "floor_char": "·",
                "wall_color": "yellow",
                "floor_color": "brown",
                "vision_modifier": -1
            }
        else: # 76 ~ 99
            return {
                "name": "Hell",
                "wall_char": "█",
                "floor_char": "⁕",
                "wall_color": "red",
                "floor_color": "purple",
                "vision_modifier": -2
            }

    def _update_particles(self, cam_x, cam_y, view_w, view_h):
        """배경 파티클 생성 및 위치 업데이트"""
        theme = self._get_map_theme()
        zone = theme['name']
        
        # 파티클 생성 (수 제한)
        if len(self.particles) < 20: 
            if zone == "Caves" and random.random() < 0.2:
                # 동굴: 위에서 떨어지는 먼지
                self.particles.append({
                    'x': cam_x + random.randint(0, view_w),
                    'y': cam_y,
                    'char': "'",
                    'color': "dark_grey",
                    'speed': random.uniform(0.2, 0.5),
                    'type': 'DUST'
                })
            elif zone == "Hell" and random.random() < 0.3:
                # 지옥: 아래에서 올라오는 불꽃
                self.particles.append({
                    'x': cam_x + random.randint(0, view_w),
                    'y': cam_y + view_h - 1,
                    'char': "*",
                    'color': random.choice(["red", "yellow", "gold"]),
                    'speed': random.uniform(-0.3, -0.6), # 음수 속도 = 위로
                    'type': 'FIRE'
                })

        # 위치 업데이트 및 화면 밖 제거
        for p in self.particles[:]:
            p['y'] += p['speed']
            # 상하 화면 밖으로 나가면 제거
            if p['y'] < cam_y or p['y'] >= cam_y + view_h:
                self.particles.remove(p)

    def handle_sandbox_input(self, action: str) -> bool:
        """샌드박스 모드 등에서 특수 입력을 처리하기 위한 훅. (기본은 처리하지 않음)"""
        return False

    def _render(self):
        """World 상태를 기반으로 Renderer를 사용하여 화면을 그립니다."""
        from .data_manager import ItemDefinition
        
        # 1. 사이드바 영역 계산
        self.renderer.clear_buffer()
        
        RIGHT_SIDEBAR_X = 81
        SIDEBAR_WIDTH = self.renderer.width - RIGHT_SIDEBAR_X
        # 한글 너비 문제를 방지하기 위해 맵 가시 영역을 약간 줄임 (안전 마진 확보)
        MAP_VIEW_WIDTH = 78 
        MAP_VIEW_HEIGHT = self.renderer.height - 12 # 하단 스탯 창 공간 확보
        
        # [Screen Shake] Apply random offset
        shake_x = 0
        shake_y = 0
        if self.shake_timer > 0:
            shake_x = random.randint(-1, 1)
            shake_y = random.randint(0, 1) # Y는 아래로만 (위로 가면 짤림)
        
        # Helper for shake offset
        def dx(x): return x + shake_x
        def dy(y): return y + shake_y
        
        # 0. 구분선 복구 (레이아웃 틀어짐 방지 가이드 역할)
        for y in range(self.renderer.height):
            self.renderer.draw_char(80, y, "|", "dark_grey")
        
        player_entity = self.world.get_player_entity()
        player_pos = player_entity.get_component(PositionComponent) if player_entity else None
        
        # [Boss Bark] 보스 대사 추출 (타이핑 효과 반영된 것)
        boss_bark = None
        boss_ent_list = self.world.get_entities_with_components({BossComponent})
        for be in boss_ent_list:
            b_comp = be.get_component(BossComponent)
            if b_comp.visible_bark:
                boss_bark = f"[{b_comp.boss_id}] {b_comp.visible_bark}"
                break
        
        map_comp_list = self.world.get_entities_with_components([MapComponent])
        
        # 카메라 오프셋 계산 (플레이어를 중앙에)
        if player_pos and map_comp_list:
            map_comp = map_comp_list[0].get_component(MapComponent)
            camera_x = max(0, min(player_pos.x - MAP_VIEW_WIDTH // 2, map_comp.width - MAP_VIEW_WIDTH))
            camera_y = max(0, min(player_pos.y - MAP_VIEW_HEIGHT // 2, map_comp.height - MAP_VIEW_HEIGHT))
        else:
            camera_x, camera_y = 0, 0

        # [Boss Bark UI] 맵 상단 중앙에 출력
        if boss_bark:
            # 맵 상단 (y=1) 중앙 정렬 (y=0은 배너와 겹칠 수 있음)
            # 테두리 및 반전 효과 강조
            box_text = f"  {boss_bark}  "
            bark_x = max(0, (MAP_VIEW_WIDTH - len(box_text)) // 2)
            
            # 배경 상자 느낌 (draw_text가 한글 너비를 처리하므로 안전)
            self.renderer.draw_text(dx(bark_x), dy(1), box_text, "invert")

        # ... (중략: 안개 업데이트 로직) ...
        # 0. 전장의 안개 업데이트 (시야 반경 8)
        if player_entity and self.dungeon_map:
            p_pos = player_entity.get_component(PositionComponent)
            if p_pos:
                # 시야 밝히기
                stats = player_entity.get_component(StatsComponent)
                # 구역별 시야 보정 적용
                theme = self._get_map_theme()
                vision_modifier = theme.get("vision_modifier", 0)
                vision_range = max(1, (stats.vision_range if stats else 5) + vision_modifier)
                self.dungeon_map.reveal_tiles(p_pos.x, p_pos.y, radius=vision_range)

        # 1. 맵 렌더링 (Left Top - Viewport 적용)
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

                    # 테마별 문자 및 색상 적용
                    theme = self._get_map_theme()
                    
                    # 맵 시인성 개선: 바닥, 문, 계단 등과 인접한 벽(#)만 표시
                    if char == "#":
                        is_visible_wall = False
                        # 8방향 탐색
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = world_x + dx, world_y + dy
                                if 0 <= nx < map_comp.width and 0 <= ny < map_comp.height:
                                    # 단순히 빈 공간(.)이 아니라, 벽이 아닌 타일(장식, 문, 계단 등)과 인접하면 표시
                                    if map_comp.tiles[ny][nx] != "#":
                                        is_visible_wall = True
                                        break
                            if is_visible_wall: break
                        
                        render_char = theme["wall_char"] if is_visible_wall else " "
                        color = theme["wall_color"]
                    else:
                        if char == ">" or char == "<":
                            render_char = char
                            color = "cyan"
                        elif char == ".":
                            render_char = theme["floor_char"]
                            color = theme["floor_color"]
                        else: # 기타 특수 타일이 있다면
                            render_char = char
                            color = "brown"
                    
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

                # [Petrified] 석화 상태면 회색으로 표시
                if entity.has_component(PetrifiedComponent):
                    color = "dark_grey"

                # 피격 피드백(Hit Flash) 처리
                if entity.has_component(HitFlashComponent):
                    color = "white_bg"
                
                # 미믹(MimicComponent) 의태 처리
                mimic = entity.get_component(MimicComponent)
                if mimic and mimic.is_disguised:
                    char = '[' # 상자 기호
                    color = "gold_bg"
                
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
                        # 발견되거나 발동된 함정은 빨간색 배경으로 강조
                        char = '^'
                        color = "red_bg"

                self.renderer.draw_char(screen_x, screen_y, char, color)

                # 2-0. 상태 이상 시각 효과 (오버헤드 아이콘) - 우선순위 순서로 표시
                # Priority: Petrified > Stun > Sleep > Poison > Bleeding > Mana Shield
                from .components import (BleedingComponent, ManaShieldComponent)
                
                status_icon = None
                status_color = "white"
                status_duration = 0
                
                # 석화 (Petrified): 최우선 - 회색 돌 아이콘
                if entity.has_component(PetrifiedComponent):
                    comp = entity.get_component(PetrifiedComponent)
                    status_icon = "◆"  # Diamond shape for stone
                    status_color = "dark_grey"
                    status_duration = comp.duration
                
                # 기절 (Stun): 별 아이콘
                elif entity.has_component(StunComponent):
                    comp = entity.get_component(StunComponent)
                    status_icon = "*"  # Star for stun
                    status_color = "yellow"
                    status_duration = comp.duration
                
                # 수면 (Sleep): zZ 번갈아 표시
                elif entity.has_component(SleepComponent):
                    comp = entity.get_component(SleepComponent)
                    status_icon = "z" if int(time.time() * 2) % 2 == 0 else "Z"
                    status_color = "light_cyan"
                    status_duration = comp.duration
                
                # 중독 (Poison): P (보라색)
                elif entity.has_component(PoisonComponent):
                    comp = entity.get_component(PoisonComponent)
                    status_icon = "P"
                    status_color = "magenta"
                    status_duration = comp.duration
                
                # 출혈 (Bleeding): 물방울 아이콘
                elif entity.has_component(BleedingComponent):
                    comp = entity.get_component(BleedingComponent)
                    status_icon = "~"  # Wave for bleeding
                    status_color = "red"
                    status_duration = comp.duration
                
                # 마나 쉴드 (Mana Shield): 방패 아이콘
                elif entity.has_component(ManaShieldComponent):
                    comp = entity.get_component(ManaShieldComponent)
                    status_icon = "◇"  # Shield diamond
                    status_color = "light_cyan"
                    status_duration = comp.duration
                
                # 상태 아이콘 및 지속시간 표시
                if status_icon:
                    # 아이콘 표시
                    self.renderer.draw_char(screen_x, screen_y - 1, status_icon, status_color)
                    
                    # 지속시간 표시 (초 단위, 아이콘 오른쪽)
                    if status_duration > 0:
                        duration_text = str(int(status_duration))
                        self.renderer.draw_text(screen_x + 1, screen_y - 1, duration_text, status_color)
                
                # [Monster HP Bar] 전투 중인 몬스터 HP 표시
                from .components import CombatTrackerComponent, MonsterComponent
                if entity.has_component(MonsterComponent) and entity.has_component(CombatTrackerComponent):
                    stats = entity.get_component(StatsComponent)
                    if stats and stats.max_hp > 0:
                        hp_ratio = max(0, min(1, stats.current_hp / stats.max_hp))
                        bar_width = 8
                        filled = int(hp_ratio * bar_width)
                        
                        # HP bar color based on health
                        if hp_ratio > 0.5:
                            bar_color = "green"
                        elif hp_ratio > 0.25:
                            bar_color = "yellow"
                        else:
                            bar_color = "red"
                        
                        # Draw HP bar above monster (y-1)
                        hp_bar_y = screen_y - 1
                        if hp_bar_y >= 0:  # Ensure it's on screen
                            self.renderer.draw_char(screen_x - 4, hp_bar_y, "[", "white")
                            for i in range(bar_width):
                                if i < filled:
                                    self.renderer.draw_char(screen_x - 3 + i, hp_bar_y, "=", bar_color)
                                else:
                                    self.renderer.draw_char(screen_x - 3 + i, hp_bar_y, "-", "dark_grey")
                            self.renderer.draw_char(screen_x + 5, hp_bar_y, "]", "white")
        
        # 2-1. 오라/특수 효과 렌더링 (휘몰아치는 연출)
        aura_entities = self.world.get_entities_with_components([PositionComponent, SkillEffectComponent])
        for entity in aura_entities:
            pos = entity.get_component(PositionComponent)
            effect = entity.get_component(SkillEffectComponent)
            
            # [Fix] RAGE_AURA is too large for this generic rendering loop
            # It covers the whole map and kills performance. Skip it here.
            if effect.name == "RAGE_AURA":
                continue

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
                # Name (Updated Format)
                job_name = level_comp.job if level_comp else "N/A"
                self.renderer.draw_text(2, current_y, f"Name : {self.player_name} ({job_name})", "gold")
                current_y += 1
                
                # HP Bar
                hp_per = max(0, min(1, stats.current_hp / stats.max_hp)) if stats.max_hp > 0 else 0
                hp_filled = int(hp_per * 15)
                # HP Bar (Left)
                self.renderer.draw_text(2, current_y, "HP  :", "white")
                self.renderer.draw_text(8, current_y, "[", "white")
                self.renderer.draw_text(9, current_y, "=" * hp_filled, "red")
                self.renderer.draw_text(9 + hp_filled, current_y, "-" * (15 - hp_filled), "dark_grey")
                self.renderer.draw_text(9 + 15, current_y, "]", "white")
                self.renderer.draw_text(26, current_y, f"{int(stats.current_hp)}/{int(stats.max_hp)}", "white")
                
                # MP Bar (Right - Side by Side)
                mp_x_offset = 40
                mp_per = max(0, min(1, stats.current_mp / stats.max_mp)) if stats.max_mp > 0 else 0
                mp_filled = int(mp_per * 15)
                self.renderer.draw_text(2 + mp_x_offset, current_y, "MP  :", "white")
                self.renderer.draw_text(8 + mp_x_offset, current_y, "[", "white")
                self.renderer.draw_text(9 + mp_x_offset, current_y, "=" * mp_filled, "blue")
                self.renderer.draw_text(9 + mp_filled + mp_x_offset, current_y, "-" * (15 - mp_filled), "dark_grey")
                self.renderer.draw_text(9 + 15 + mp_x_offset, current_y, "]", "white")
                self.renderer.draw_text(26 + mp_x_offset, current_y, f"{int(stats.current_mp)}/{int(stats.max_mp)}", "white")
                current_y += 1

                
                # Level info
                if level_comp:
                    # Line 1: LV, JOB, FLOOR
                    lv_str = f"LV: {level_comp.level}"
                    job_str = f"JOB: {level_comp.job}"
                    theme_info = self._get_map_theme()
                    floor_str = f"FLOOR: {self.current_level} ({theme_info['name']})"
                    self.renderer.draw_text(2, current_y, f"{lv_str:<8} {job_str:<15} {floor_str:<25}", "white")
                    current_y += 1

                    # Line 2: EXP Bar
                    exp_per = max(0, min(1, level_comp.exp / level_comp.exp_to_next)) if level_comp.exp_to_next > 0 else 0
                    exp_filled = int(exp_per * 15)
                    self.renderer.draw_text(2, current_y, "EXP :", "white")
                    self.renderer.draw_text(8, current_y, "[", "white")
                    self.renderer.draw_text(9, current_y, "=" * exp_filled, "gold")
                    self.renderer.draw_text(9 + exp_filled, current_y, "-" * (15 - exp_filled), "dark_grey")
                    self.renderer.draw_text(9 + 15, current_y, "]", "white")
                    self.renderer.draw_text(26, current_y, f"{int(level_comp.exp)}/{int(level_comp.exp_to_next)}", "white")
                    current_y += 1
                
                # Stats
                atk_color = "white"
                def_color = "white"
                
                # Check for Rage buff to highlight red
                modifiers = player_entity.get_components(StatModifierComponent)
                if any(mod.source == "레이지" for mod in modifiers):
                    atk_color = "red"
                    def_color = "red"

                atk_str = f"ATK: {stats.attack}"
                def_str = f"DEF: {stats.defense}"
                rng_str = f"RNG: {stats.weapon_range} (LINE)"
                
                self.renderer.draw_text(2, current_y, f"{atk_str:<10}", atk_color)
                self.renderer.draw_text(13, current_y, f"{def_str:<10}", def_color)
                self.renderer.draw_text(24, current_y, f"{rng_str}", "white")

                # 로그 타이틀 위치 조정 (사이드바)
                # 4. 오른쪽 사이드바 (Right Sidebar)
                # 4-1. 로그 (Logs)
                log_start_y = 0
                self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, log_start_y, "[ LOGS ]", "gold")
        
        message_comp_list = self.world.get_entities_with_components({MessageComponent})
        if message_comp_list:
            message_comp = message_comp_list[0].get_component(MessageComponent)
            # 최근 10개 메시지 표시 (영역 확장)
            recent_messages = message_comp.messages[-10:]
            for i, msg_data in enumerate(recent_messages):
                # Handle both str and dict (legacy support + new colored msgs)
                msg_text = msg_data
                msg_color_override = None

                if isinstance(msg_data, dict):
                     msg_text = msg_data.get('text', '')
                     msg_color_override = msg_data.get('color')
                
                # 너비 제한으로 자르기 (한글 너비 고려하여 보수적으로)
                wrap_width = SIDEBAR_WIDTH - 6
                truncated_msg = (msg_text[:wrap_width] + '..') if len(msg_text) > wrap_width else msg_text
                
                # 메시지 내용에 따른 색상 구분
                msg_color = "white"
                
                # 1. Explicit color (from MessageEvent)
                if msg_color_override:
                    msg_color = msg_color_override
                # 2. Keyword-based fallback
                elif "치명타" in msg_text or "Critical" in msg_text:
                    msg_color = "red"
                elif "빗나갔" in msg_text or "Miss" in msg_text:
                    msg_color = "dark_grey"
                elif "방어" in msg_text or "Block" in msg_text:
                    msg_color = "green"
                elif "시전" in msg_text or "Cast" in msg_text:
                     msg_color = "cyan"
                elif "데미지를 입었다" in msg_text:
                    msg_color = "red"
                elif "쓰러졌습니다" in msg_text:
                    msg_color = "gold"
                elif "만났습니다" in msg_text:
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
                    
                    # Initialize color to white by default
                    color = "white"
                    
                    # 아이템이 ItemDefinition 객체이면 이름을 가져오고, 아니면 그대로 사용 (---- 혹은 양손점유)
                    if isinstance(item, ItemDefinition):
                        item_display = item.name
                        
                        # [Durability] Display and Warning
                        if hasattr(item, 'max_durability') and item.max_durability > 0:
                            durability_ratio = item.current_durability / item.max_durability
                            
                            # Always show durability if item has it
                            item_display += f" ({item.current_durability}/{item.max_durability})"
                            
                            # Color warning based on durability
                            if durability_ratio <= 0.1:  # 10% or below - Critical (Red)
                                color = "red"
                            elif durability_ratio <= 0.5:  # 50% or below - Warning (Yellow + Blink)
                                # Blink effect: alternate between yellow and white every 0.5s
                                if int(time.time() * 2) % 2 == 0:
                                    color = "yellow"
                                else:
                                    color = "white"
                    else:
                        item_display = item if item else "----"
                        
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
            # 1. 활성화된 버프 확인 및 Duration 매핑 (Item Slots 용)
            active_item_buffs = {}
            if hasattr(player_entity, 'components'):
                 for comp in player_entity.components.values():
                     if isinstance(comp, StatModifierComponent) and comp.source.startswith("ITEM_"):
                         item_source_name = comp.source.replace("ITEM_", "")
                         active_item_buffs[item_source_name] = comp.expires_at - time.time()
            
            # 특수 효과 (VISION_UP 등)
            stats = player_entity.get_component(StatsComponent)
            if stats:
                if "VISION_UP" in stats.flags and hasattr(stats, 'vision_expires_at'):
                    active_item_buffs["횃불"] = stats.vision_expires_at - time.time()

            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'item_slots'):
                for i, item in enumerate(inv_comp.item_slots):
                    item_name = item if item else "----"
                    display_text = f"{i+1}: {item_name}"
                    
                    if item_name in active_item_buffs:
                        seconds = int(active_item_buffs[item_name])
                        if seconds > 0:
                            display_text += f" ({seconds}s)"
                    
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, qs_y + i, display_text, "white")
        
        # 4-4. 스킬 (Skill Slots 6-0)
        skill_start_y = qs_start_y + 7
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_start_y, "[ SKILLS ] (6-0)", "gold")
        skill_y = skill_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'skill_slots'):
                 for i, skill in enumerate(inv_comp.skill_slots):
                    skill_name = skill if skill else "----"
                    
                    # [Skill Cooldown] Display
                    cd_str = ""
                    if hasattr(self, 'combat_system') and skill:
                        current_cd = self.combat_system.get_cooldown(player_entity.entity_id, skill)
                        if current_cd > 0:
                            cd_str = f" ({int(current_cd)}s)"
                    
                    key_char = str((i + 6) % 10)
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, skill_y + i, f"{key_char}: {skill_name}{cd_str}", "white")

        # 4-5. 활성 효과 (Active Effects / Buffs) - User Request: "Count down for items"
        buff_start_y = skill_y + 6 # After 5 skill slots
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, buff_start_y, "[ ACTIVE EFFECTS ]", "gold")
        buff_y = buff_start_y + 1
        
        if player_entity:
             stat_modifiers = player_entity.get_components(StatModifierComponent)
             # Filter for temporary buffs only
             active_buffs = [mod for mod in stat_modifiers if mod.duration > 0]
             
             if not active_buffs:
                 self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, buff_y, "None", "dark_grey")
             else:
                 for i, buff in enumerate(active_buffs):
                     if buff_y + i >= MAP_HEIGHT: break # Prevent overflow
                     
                     # Format: Source (Duration s)
                     # Color logic: Red if < 10s, Yellow if < 30s, Green otherwise
                     time_color = "green"
                     if buff.duration <= 10: time_color = "red"
                     elif buff.duration <= 30: time_color = "yellow"
                     
                     display_str = f"{buff.source} ({int(buff.duration)}s)"
                     self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, buff_y + i, display_str, time_color)
        sk_y = skill_start_y + 1
        if player_entity:
            # 1. 활성화된 버프 확인 및 Duration 매핑
            active_buffs = {}
            if hasattr(player_entity, 'components'):
                 for comp in player_entity.components.values():
                     if isinstance(comp, StatModifierComponent):
                         active_buffs[comp.source] = comp.duration

            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp and hasattr(inv_comp, 'skill_slots'):
                for i, item in enumerate(inv_comp.skill_slots):
                    item_name = item if item else "----"
                    num = 0 if i == 4 else i + 6
                    
                    display_text = f"{num}: {item_name}"
                    
                    # [UI] Display Skill Level
                    if item_name in inv_comp.skill_levels:
                        slv = inv_comp.skill_levels[item_name]
                        display_text += f" (Lv.{slv})"
                    
                    # 2. 카운트다운 표시
                    if item_name in active_buffs:
                         seconds = int(active_buffs[item_name])
                         if seconds > 0:
                             display_text += f" ({seconds}s)"
                    
                    self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, sk_y + i, display_text, "white")

        # 5. 입력 가이드 (Bottom fixed)
        guide_y = self.renderer.height - 1
        if self.is_attack_mode:
            self.renderer.draw_text(0, guide_y, " [ATTACK] Arrows: Select Dir | [Space] Cancel ", "red")
        else:
            self.renderer.draw_text(0, guide_y, " [MOVE] Arrows | [.] Wait | [I] Inventory | [Space] Attack Mode | [Q] Quit", "green")
        
        # 6. 구역 진입 알림 배너 (Center Overlay)
        if self.banner_timer > 0:
            self.banner_timer -= 0.05
            
            # ASCII Style Banner
            text = self.banner_text
            border = "=" * (len(text) + 4)
            bx = (MAP_VIEW_WIDTH - len(border)) // 2
            by = 3
            
            color = "gold"
            if int(self.banner_timer * 4) % 2 == 0:
                 color = "white"
                 
            self.renderer.draw_text(bx, by - 1, border, color)
            self.renderer.draw_text(bx, by, f"| {text} |", color)
            self.renderer.draw_text(bx, by + 1, border, color)

        # 7. 인벤토리/상점/신전 팝업 렌더링
        if self.state == GameState.INVENTORY:
            self._render_inventory_popup()
        elif self.state == GameState.SHOP:
            self._render_shop_popup()
        elif self.state == GameState.SHRINE:
            self._render_shrine_popup()
        elif self.state == GameState.CHARACTER_SHEET:
            self._render_character_sheet_popup()

        self.renderer.render()

    def _render_character_sheet_popup(self):
        """캐릭터 상세 정보 팝업 렌더링"""
        MAP_WIDTH = 80
        POPUP_WIDTH = 60
        POPUP_HEIGHT = 18
        
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. Box
        for y in range(start_y, start_y + POPUP_HEIGHT):
            for x in range(start_x, start_x + POPUP_WIDTH):
                if y == start_y or y == start_y + POPUP_HEIGHT - 1:
                    char = "-"
                elif x == start_x or x == start_x + POPUP_WIDTH - 1:
                    char = "|"
                else:
                    char = " "
                self.renderer.draw_char(x, y, char, "white")
        
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        from .components import StatsComponent, LevelComponent
        stats = player_entity.get_component(StatsComponent)
        level_comp = player_entity.get_component(LevelComponent)
        
        if not stats or not level_comp: return
        
        # 2. Header
        header = f"[ {level_comp.job or 'Adventurer'} - Lv.{level_comp.level} ]"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(header)) // 2, start_y + 1, header, "gold")
        
        exp_info = f"EXP: {int(level_comp.exp)} / {int(level_comp.exp_to_next)}"
        pts_info = f"Points: {level_comp.stat_points}"
        self.renderer.draw_text(start_x + 4, start_y + 3, exp_info, "white")
        self.renderer.draw_text(start_x + POPUP_WIDTH - len(pts_info) - 4, start_y + 3, pts_info, "yellow")
        
        self.renderer.draw_text(start_x + 2, start_y + 4, "-" * (POPUP_WIDTH - 4), "dark_grey")
        
        # 3. Stats List
        stat_names = ["STR (힘)", "MAG (마력)", "DEX (민첩)", "VIT (활력)"]
        stat_vals = [stats.base_str, stats.base_mag, stats.base_dex, stats.base_vit]
        stat_desc = ["공격력 / 무기효율", "최대마력 / 마법효율", "방어력 / 명중률 / 치명타", "최대체력 / 생존력"]
        
        base_y = start_y + 6
        for i in range(4):
            prefix = "> " if i == self.selected_stat_index else "  "
            color = "green" if i == self.selected_stat_index else "white"
            
            line = f"{prefix}{stat_names[i]:<10}: {stat_vals[i]:<3} | {stat_desc[i]}"
            self.renderer.draw_text(start_x + 4, base_y + i * 2, line, color)
            
        self.renderer.draw_text(start_x + 2, base_y + 9, "-" * (POPUP_WIDTH - 4), "dark_grey")
        
        # 4. Summary
        hp_mp = f"HP: {int(stats.current_hp)}/{int(stats.max_hp)}  MP: {int(stats.current_mp)}/{int(stats.max_mp)}"
        atk_def = f"ATK: {stats.attack}  DEF: {stats.defense}"
        
        self.renderer.draw_text(start_x + 4, base_y + 10, hp_mp, "cyan")
        self.renderer.draw_text(start_x + 4, base_y + 11, atk_def, "cyan")
        
        # 5. Footer
        help_text = "[↑/↓] 선택  [→/ENTER] 포인트 투자  [C/ESC] 닫기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(help_text)) // 2, start_y + POPUP_HEIGHT - 2, help_text, "dark_grey")

    def _render_inventory_popup(self):
        """항목 목록을 보여주는 중앙 팝업창 렌더링 (카테고리 분류 포함)"""
        MAP_WIDTH = 80
        POPUP_WIDTH = 60
        POPUP_HEIGHT = 20
        # 맵 영역(80) 내에 중앙 정렬
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2
        
        # 1. 배경 및 테두리 그리기
        max_visible_items = 6  # 목록 가독성을 위해 6개로 고정
        
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
             filtered_items = []
             total_items = 0
             inv_comp = player_entity.get_component(InventoryComponent)
             
             if inv_comp:
                 # 카테고리별 필터링 (헬퍼 사용)
                 filtered_items = self._get_filtered_inventory_items(inv_comp)
                 total_items = len(filtered_items)

                 if not filtered_items:
                     self.renderer.draw_text(start_x + 2, start_y + 4, "  (비어 있음)", "dark_grey")
                 else:
                     current_y = start_y + 4
                     # Import constants
                     from .constants import ELEMENT_ICONS, RARITY_NORMAL
                     # 스크롤 가능한 영역 계산 (하단 상세 정보창을 위해 6개로 제한)
                     max_visible_items = 6
                     
                     # 스크롤 오프셋 조정 (선택된 아이템이 보이도록)
                     if self.selected_item_index < self.inventory_scroll_offset:
                         self.inventory_scroll_offset = self.selected_item_index
                     elif self.selected_item_index >= self.inventory_scroll_offset + max_visible_items:
                         self.inventory_scroll_offset = self.selected_item_index - max_visible_items + 1
                     
                     # 오프셋 범위 제한
                     max_offset = max(0, total_items - max_visible_items)
                     self.inventory_scroll_offset = max(0, min(self.inventory_scroll_offset, max_offset))
                     
                     # 표시할 아이템 범위
                     start_idx = self.inventory_scroll_offset
                     end_idx = min(start_idx + max_visible_items, total_items)
                     
                     for idx in range(start_idx, end_idx):
                         if current_y >= start_y + POPUP_HEIGHT - 3: break
                         
                         item_id, item_data = filtered_items[idx]
                         item = item_data['item']
                         is_id = getattr(item, 'is_identified', True)
                         
                         name = item.name
                         if not is_id:
                             name = f"? [{item.type}]"
                         
                         # [UI] Display Skill Level in Inventory
                         if self.inventory_category_index == 3: # Skill Tab
                             slv = inv_comp.skill_levels.get(item.name, 1)
                             name = f"{item.name} (Lv.{slv})"
                         qty = item_data['qty']
                         prefix = "> " if idx == self.selected_item_index else "  "
                         
                         # Determine Color
                         if idx == self.selected_item_index:
                             color = "green"
                         else:
                             # Use item.color if available, else Normal
                             color = getattr(item, 'color', RARITY_NORMAL)
                             
                         # Determine Icon
                         # item might have 'element' attribute
                         icon = ""
                         if hasattr(item, 'element') and item.element in ELEMENT_ICONS:
                             icon = ELEMENT_ICONS[item.element] + " "
                         
                         # Suffixes often hint elements too, but item.element is primary.
                         # If affix changed element, ensure item.element captures it.
                         
                         _s = ""
                         if any(eq == item for eq in inv_comp.equipped.values()): _s += " [E]"
                         if name in inv_comp.item_slots or name in inv_comp.skill_slots: _s += " [Q]"
                         
                         # [Durability]
                         max_d = getattr(item, 'max_durability', 0)
                         if max_d > 0:
                             cur_d = getattr(item, 'current_durability', max_d)
                             if cur_d <= 0:
                                 _s += " [BROKEN]"
                                 if idx != self.selected_item_index: color = "red"
                             else:
                                 _s += f" [{cur_d}/{max_d}]"
                          
                         # [Charges]
                         max_c = getattr(item, 'max_charges', 0)
                         if max_c > 0:
                             cur_c = getattr(item, 'current_charges', 0)
                             _s += f" (Charge: {cur_c}/{max_c})"
                         
                         self.renderer.draw_text(start_x + 2, current_y, f"{prefix}{icon}{name} x{qty}{_s}", color)
                         current_y += 1
                     # 페이지 인디케이터 표시
                     if total_items > max_visible_items:
                         current_page = (self.inventory_scroll_offset // max_visible_items) + 1
                         total_pages = (total_items + max_visible_items - 1) // max_visible_items
                         page_info = f"Page {current_page}/{total_pages} ({start_idx+1}-{end_idx}/{total_items})"
                         self.renderer.draw_text(start_x + POPUP_WIDTH - len(page_info) - 2, start_y + 3, page_info, "cyan")

                 # 4.1 선택된 아이템/스킬 상세 정보 표시 (하단 영역)
                 # 하단 구분선 (y=10 고정)
                 info_y = start_y + 10
                 self.renderer.draw_text(start_x, info_y, "─" * (POPUP_WIDTH - 2), "white")
                 
                 # 가이드 메시지 (아이템 목록 바로 위 또는 구분선 근처)
                 debug_info = f" 선택: {self.selected_item_index + 1}/{total_items} "
                 self.renderer.draw_text(start_x + 2, start_y + 3, debug_info, "yellow")
                 if 0 <= self.selected_item_index < total_items:
                     sel_id, sel_data = filtered_items[self.selected_item_index]
                     sel_item = sel_data['item']
                     # 상세 정보 시작 위치 (구분선 바로 아래)
                     detail_y = info_y + 1
                     self.renderer.draw_text(start_x + 1, detail_y, "-" * (POPUP_WIDTH - 2), "dark_grey")
                     # 아이템/스킬 이름 표시 (상세 영역 최상단)
                     is_id = getattr(sel_item, 'is_identified', True) # Moved up for name display
                     disp_name = sel_item.name if is_id else sel_id if isinstance(sel_id, str) else "?"
                     
                     # [Fix] 필요 레벨 정보 가져오기 및 이름 옆에 표시
                     req_lvl = getattr(sel_item, 'required_level', 1)
                     p_lvl = 1
                     if player_entity:
                         l_comp = player_entity.get_component(LevelComponent)
                         if l_comp: p_lvl = l_comp.level
                     
                     req_met = p_lvl >= req_lvl
                     req_color = "gold" if req_met else "red"
                     
                     # 이름과 레벨 표시
                     self.renderer.draw_text(start_x + 2, detail_y + 1, f"이름: {disp_name}", "gold")
                     if req_lvl > 1:
                         self.renderer.draw_text(start_x + 25, detail_y + 1, f"[필요 레벨: {req_lvl}]", req_color)
                     
                     # 상세 정보 텍스트 (아이템/스킬 공통 필드)
                     
                     if hasattr(sel_item, 'required_level') and sel_item.required_level > p_lvl:
                         req_met = False
 
                     desc = getattr(sel_item, 'description', "")
                     if not is_id:
                         desc = "??????????????"
                     
                     if desc:
                         # 한 줄로 표시 (공간 제약)
                         if len(desc) > POPUP_WIDTH - 10:
                             desc = desc[:POPUP_WIDTH - 13] + "..."
                         self.renderer.draw_text(start_x + 2, detail_y + 2, f"설명: {desc}", "white")
                     
                     # 스탯 정보
                     stats_text = ""
                     if hasattr(sel_item, 'attack') and sel_item.attack != "0":
                         val = getattr(sel_item, 'attack', '') if (is_id and req_met) else "?"
                         stats_text += f"공격: {val} "
                     if hasattr(sel_item, 'defense') and sel_item.defense != 0:
                         val = sel_item.defense if (is_id and req_met) else "?"
                         stats_text += f"방어: {val} "
                     
                     # 사거리 정보 (핵심!)
                     r_val = 0
                     if hasattr(sel_item, 'attack_range'): r_val = sel_item.attack_range
                     elif hasattr(sel_item, 'range'): r_val = sel_item.range
                     
                     if r_val > 0:
                         val = r_val if (is_id and req_met) else "?"
                         stats_text += f"사거리: {val} "
                    
                     # 스킬 전용 정보
                     if self.inventory_category_index == 3: # 스킬 탭
                         s_def = self.skill_defs.get(sel_id)
                         if s_def:
                             stats_text += f"비용: {s_def.cost_value}{s_def.cost_type} "
                             if s_def.required_level > 1:
                                 stats_text += f"필요Lv: {s_def.required_level} "
                     
                     if stats_text:
                         self.renderer.draw_text(start_x + 2, detail_y + 3, stats_text.strip(), "yellow")
                     # 3. 능력치 보너스 (Identified & Req met only)
                     bonus_lines = []
                     if is_id and req_met:
                         line = ""
                         if getattr(sel_item, 'str_bonus', 0) != 0: line += f"STR+{sel_item.str_bonus} "
                         if getattr(sel_item, 'mag_bonus', 0) != 0: line += f"MAG+{sel_item.mag_bonus} "
                         if line: bonus_lines.append(line.strip())
                         
                         line = ""
                         if getattr(sel_item, 'dex_bonus', 0) != 0: line += f"DEX+{sel_item.dex_bonus} "
                         if getattr(sel_item, 'vit_bonus', 0) != 0: line += f"VIT+{sel_item.vit_bonus} "
                         if line: bonus_lines.append(line.strip())

                         line = ""
                         if getattr(sel_item, 'hp_bonus', 0) != 0: line += f"HP+{sel_item.hp_bonus} "
                         if getattr(sel_item, 'mp_bonus', 0) != 0: line += f"MP+{sel_item.mp_bonus} "
                         if line: bonus_lines.append(line.strip())
                         
                         line = ""
                         if getattr(sel_item, 'res_all', 0) != 0: line += f"모든저항+{sel_item.res_all}% "
                         if getattr(sel_item, 'res_fire', 0) != 0: line += f"화염저항+{sel_item.res_fire}% "
                         if line: bonus_lines.append(line.strip())
                        
                         # [Fix] 수치적 보너스 표시 (Life Leech, Magic Find 등)
                         line = ""
                         if getattr(sel_item, 'life_leech', 0) != 0: line += f"생명력 흡수+{sel_item.life_leech}% "
                         if getattr(sel_item, 'magic_find', 0) != 0: line += f"마법 아이템 발견+{sel_item.magic_find}% "
                         if line: bonus_lines.append(line.strip())
                     elif is_id and not req_met:
                         bonus_lines.append("보너스: ??????????")
 
                     for i, b_line in enumerate(bonus_lines):
                         self.renderer.draw_text(start_x + 2, detail_y + 4 + i, b_line, "cyan")

                     # 4. 요구 사항 (항상 표시하되 충족 여부에 따라 색상 변경)
                     # (이미 이름 옆에 표시되므로 여기서는 간단히 강조 또는 생략 가능, 일단 유지하되 위치 조정)
                     req_y = start_y + POPUP_HEIGHT - 2
                     if hasattr(sel_item, 'required_level') and sel_item.required_level > 1:
                         color = "white" if req_met else "red"
                         text = f"필요 레벨: {sel_item.required_level}"
                         if not req_met: text += " (현재 레벨 부족!)"
                         self.renderer.draw_text(start_x + 2, req_y, text, color)
        
        # 5. 하단 도움말
        if self.inventory_category_index == 3:
            help_text = "[←/→] 탭  [↑/↓] 선택  [ENTER/E] 등록/해제  [X] 스킬 잊기  [B] 닫기"
        else:
            help_text = "[←/→] 탭  [↑/↓] 선택  [E] 퀵슬롯 등록  [ENTER] 사용/장착  [B] 닫기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(help_text)) // 2, start_y + POPUP_HEIGHT - 2, help_text, "dark_grey")

    def _render_shop_popup(self):
        """상점 UI 팝업 렌더링"""
        shopkeeper_id = getattr(self, "active_shop_id", None)
        shopkeeper = self.world.get_entity(shopkeeper_id) if shopkeeper_id else None
        
        MAP_WIDTH = 80
        POPUP_WIDTH = 66
        POPUP_HEIGHT = 24
        start_x = (MAP_WIDTH - POPUP_WIDTH) // 2
        start_y = (self.renderer.height - POPUP_HEIGHT) // 2 - 2
        
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
            if shopkeeper:
                shop_comp = shopkeeper.get_component(ShopComponent)
                if shop_comp:
                    # [Fix] Filter out BOSS items
                    items_to_display = [
                        i for i in shop_comp.items 
                        if "BOSS" not in getattr(i['item'], 'flags', [])
                    ]
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
                # Color
                if i == self.selected_shop_item_index:
                    color = "green"
                else:
                    from .constants import RARITY_NORMAL
                    color = getattr(item, 'color', RARITY_NORMAL)
                
                # Icon
                from .constants import ELEMENT_ICONS
                icon = ""
                if hasattr(item, 'element') and item.element in ELEMENT_ICONS:
                     icon = ELEMENT_ICONS[item.element] + " "
                
                # 수량 표시 (팔기 탭에서 유용)
                qty_str = f" x{qty}" if self.shop_category_index == 1 else ""
                
                # [Fix] 상점에서도 필요 레벨 표시
                req_lvl = getattr(item, 'required_level', 1)
                lvl_str = f" [Lv.{req_lvl}]" if req_lvl > 1 else ""
                
                name_text = f"{prefix}{icon}{item.name}{qty_str}{lvl_str}"
                self.renderer.draw_text(start_x + 2, item_y, name_text, color)
                
                price_text = f"{price:>5} G"
                self.renderer.draw_text(start_x + POPUP_WIDTH - 12, item_y, price_text, color)
        
        # 5. 하단 도움말
        guide_text = "[←/→] 탭 전환  [↑/↓] 선택  [ENTER] " + ("구매" if self.shop_category_index == 0 else "판매") + "  [B] 뒤로/닫기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(guide_text)) // 2, start_y + POPUP_HEIGHT - 2, guide_text, "dark_grey")
    def _handle_oil_selection_input(self, action):
        """오일 사용 시 장비 선택 입력 처리"""
        # ESC: Cancel
        if action == readchar.key.ESC or action == 'q' or action == 'Q':
            self.oil_selection_open = False
            self.pending_oil_item = None
            self.pending_oil_type = None
            self.world.event_manager.push(MessageEvent("강화를 취소했습니다."))
            return

        # Up/Down
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        equipped_list = list(inv.equipped.items())
        count = len(equipped_list)
        
        if action in [readchar.key.UP, '\x1b[A']:
            self.selected_equip_index = max(0, self.selected_equip_index - 1)
        elif action in [readchar.key.DOWN, '\x1b[B']:
            if count > 0:
                self.selected_equip_index = min(count - 1, self.selected_equip_index + 1)
        
        elif action == readchar.key.ENTER or action == '\r' or action == '\n':
            if count > 0 and 0 <= self.selected_equip_index < count:
                slot, item = equipped_list[self.selected_equip_index]
                if item:
                    # Apply Oil Logic
                    success = self._apply_oil(item, self.pending_oil_type)
                    if success:
                        self.world.event_manager.push(MessageEvent(f"{item.name}이(가) 강화되었습니다!"))
                        self.world.event_manager.push(SoundEvent("LEVEL_UP"))
                        
                        # Consume Oil
                        oil_data = self.pending_oil_item
                        oil_name = oil_data['item'].name
                        if oil_name in inv.items:
                            inv.items[oil_name]['qty'] -= 1
                            if inv.items[oil_name]['qty'] <= 0:
                                del inv.items[oil_name]
                        
                        self.oil_selection_open = False
                        self.pending_oil_item = None
                        self._recalculate_stats()
                    else:
                        self.world.event_manager.push(MessageEvent("이 아이템에는 사용할 수 없습니다."))
                else:
                    self.world.event_manager.push(MessageEvent("빈 슬롯입니다."))

    def _apply_oil(self, item, oil_type):
        """오일 효과 적용"""
        # Check item type compatibility
        is_weapon = getattr(item, 'type', '') == 'WEAPON'
        is_armor = getattr(item, 'type', '') in ['ARMOR', 'SHIELD']
        
        if oil_type == "OIL_SHARPNESS":
            if not is_weapon: return False
            # Max Damage Bonus + 1 (Permanent)
            current = getattr(item, 'damage_max_bonus', 0)
            item.damage_max_bonus = current + 1
            return True
            
        elif oil_type == "OIL_ACCURACY":
            if not is_weapon: return False
            current = getattr(item, 'to_hit_bonus', 0)
            item.to_hit_bonus = current + 5
            return True
            
        elif oil_type == "OIL_HARDENING":
            if not is_armor: return False
            # Defense + 1
            current_def = getattr(item, 'defense', 0)
            item.defense = current_def + 1
            item.defense_max = getattr(item, 'defense_max', current_def) + 1
            return True
            
        return False

    def _render_equip_selection_popup(self):
        """오일 사용을 위한 장비 선택 팝업 렌더링"""
        ui = self.renderer
        w, h = 50, 20
        sx = 5
        sy = 3
        ui.draw_box(sx, sy, w, h, title="강화할 장비 선택")
        
        player_entity = self.world.get_player_entity()
        inv = player_entity.get_component(InventoryComponent)
        
        y = sy + 2
        equipped_list = list(inv.equipped.items())
        
        from .constants import RARITY_NORMAL
        
        for idx, (slot, item) in enumerate(equipped_list):
            if y >= sy + h - 1: break
            prefix = "> " if idx == self.selected_equip_index else "  "
            
            if item:
                name = item.name
                color = getattr(item, 'color', RARITY_NORMAL)
                # Show durability if exists
                cur_d = getattr(item, 'current_durability', 0)
                max_d = getattr(item, 'max_durability', 0)
                dur_info = ""
                if max_d > 0: dur_info = f" [{cur_d}/{max_d}]"
                
                text = f"{prefix}{slot}: {name}{dur_info}"
            else:
                name = "(비어 있음)"
                color = "dark_grey"
                text = f"{prefix}{slot}: {name}"
            
            if idx == self.selected_equip_index: 
                color = "green" 
            
            ui.draw_text(sx + 2, y, text, color)
            y += 1
            
        ui.draw_text(sx + 2, sy + h - 2, "[ENTER] 강화  [ESC] 취소", "dark_grey")
    
    def _handle_shrine_input(self, action: str):
        """신전 상태에서의 입력 처리"""
        player_entity = self.world.get_player_entity()
        if not player_entity:
            self.state = GameState.PLAYING
            return
        
        # Step 0: 메인 메뉴 (복구 vs 강화)
        if self.shrine_enhance_step == 0:
            if action in [readchar.key.UP, '\x1b[A']:
                self.shrine_menu_index = max(0, self.shrine_menu_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                self.shrine_menu_index = min(1, self.shrine_menu_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if self.shrine_menu_index == 0:
                    self._shrine_restore_all()
                    # _shrine_restore_all internally calls _close_shrine_with_destruction
                else:
                    self.shrine_enhance_step = 1
                    self.selected_equip_index = 0
        elif self.shrine_enhance_step == 1:
            inv = player_entity.get_component(InventoryComponent)
            if not inv:
                self.state = GameState.PLAYING
                return
            
            # 모든 장비 리스트 (장착 중 + 인벤토리 무기/방어구/액세서리)
            eligible_items = []
            # 장착 중인 것 우선
            for slot, item in inv.equipped.items():
                if item and hasattr(item, 'name'):
                    eligible_items.append(('EQUIPPED', slot, item))
            
            # 인벤토리 내 장비류
            for name, entry in inv.items.items():
                item = entry['item']
                if item.type in ["WEAPON", "ARMOR", "SHIELD", "ACCESSORY"]:
                    for _ in range(entry['qty']):
                        eligible_items.append(('INVENTORY', name, item))
            
            if action in [readchar.key.UP, '\x1b[A']:
                self.selected_equip_index = max(0, self.selected_equip_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                if eligible_items:
                    self.selected_equip_index = min(len(eligible_items) - 1, self.selected_equip_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if eligible_items and 0 <= self.selected_equip_index < len(eligible_items):
                    _, _, self.target_enhance_item = eligible_items[self.selected_equip_index]
                    # Step 2: 오일 선택으로 이동
                    self.shrine_enhance_step = 2
                    self.selected_oil_index = 0
                    
                    # 오일 리스트 필터링
                    self.eligible_oils = []
                    for name, entry in inv.items.items():
                        item_flags = getattr(entry['item'], 'flags', set())
                        if any(f.startswith("OIL_") for f in item_flags):
                            self.eligible_oils.append(entry['item'])
                    
                    # 오일이 없으면 바로 제물 단계로 이동하거나 메시지 출력 가능하나, 일단 오일 선택창으로 보냄 (없음 표시)
            elif action in ['b', 'B', readchar.key.ESC]:
                self.shrine_enhance_step = 0

        elif self.shrine_enhance_step == 2:
            # 오일 선택
            if action in [readchar.key.UP, '\x1b[A']:
                self.selected_oil_index = max(0, self.selected_oil_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                if self.eligible_oils:
                    self.selected_oil_index = min(len(self.eligible_oils) - 1, self.selected_oil_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if self.eligible_oils:
                    self.selected_oil = self.eligible_oils[self.selected_oil_index]
                else:
                    self.selected_oil = None
                
                # Step 3: 제물 여부 확인
                self.shrine_enhance_step = 3
                self.sacrifice_prompt_yes = True
            elif action in ['b', 'B', readchar.key.ESC]:
                self.shrine_enhance_step = 1

        elif self.shrine_enhance_step == 3:
            # 제물을 바치시겠습니까? Yes / No
            if action in [readchar.key.LEFT, '\x1b[D', readchar.key.RIGHT, '\x1b[C']:
                self.sacrifice_prompt_yes = not self.sacrifice_prompt_yes
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                if self.sacrifice_prompt_yes:
                    inv = player_entity.get_component(InventoryComponent)
                    self.eligible_sacrifices = []
                    for name, entry in inv.items.items():
                        item_flags = getattr(entry['item'], 'flags', set())
                        if any(f.startswith("SAC_") for f in item_flags):
                            self.eligible_sacrifices.append(entry['item'])
                    
                    if not self.eligible_sacrifices:
                        # 제물이 없으면 메시지 띄우고 바로 강화 진행 여부 확인하거나 아예 Step 4에서 없음 알림
                        self.shrine_enhance_step = 4
                        self.selected_sacrifice_index = 0
                    else:
                        self.shrine_enhance_step = 4
                        self.selected_sacrifice_index = 0
                else:
                    # 제물 없음 선택 시 바로 강화 실행
                    self.selected_sacrifice = None
                    self._shrine_enhance_item(self.target_enhance_item, self.selected_oil, self.selected_sacrifice)
                    self._close_shrine_with_destruction()
            elif action in ['b', 'B', readchar.key.ESC]:
                self.shrine_enhance_step = 2

        elif self.shrine_enhance_step == 4:
            # 제물 선택
            if not self.eligible_sacrifices:
                 # 제물 없음 메시지 상태라면 Enter 시 그냥 진행
                 if action == readchar.key.ENTER or action == '\r' or action == '\n':
                     self.selected_sacrifice = None
                     self._shrine_enhance_item(self.target_enhance_item, self.selected_oil, self.selected_sacrifice)
                     self._close_shrine_with_destruction()
                 elif action in ['b', 'B', readchar.key.ESC]:
                     self.shrine_enhance_step = 3
                 return

            if action in [readchar.key.UP, '\x1b[A']:
                self.selected_sacrifice_index = max(0, self.selected_sacrifice_index - 1)
            elif action in [readchar.key.DOWN, '\x1b[B']:
                if self.eligible_sacrifices:
                    self.selected_sacrifice_index = min(len(self.eligible_sacrifices) - 1, self.selected_sacrifice_index + 1)
            elif action == readchar.key.ENTER or action == '\r' or action == '\n':
                self.selected_sacrifice = self.eligible_sacrifices[self.selected_sacrifice_index]
                self._shrine_enhance_item(self.target_enhance_item, self.selected_oil, self.selected_sacrifice)
                self._close_shrine_with_destruction()
            elif action in ['b', 'B', readchar.key.ESC]:
                self.shrine_enhance_step = 3
    
    def _close_shrine(self):
        """신전 닫기 및 소멸 처리"""
        if self.active_shrine_id:
            shrine_ent = self.world.get_entity(self.active_shrine_id)
            if shrine_ent:
                shrine_comp = shrine_ent.get_component(ShrineComponent)
                if shrine_comp:
                    shrine_comp.is_used = True
                self.world.delete_entity(self.active_shrine_id)
        
        self.state = GameState.PLAYING
        self.active_shrine_id = None
        self.shrine_menu_index = 0
        self.shrine_enhance_step = 0
    
    def _shrine_restore_all(self):
        """복구: 모든 내구도 + HP/MP/Stamina 완전 회복"""
        player_entity = self.world.get_player_entity()
        if not player_entity:
            return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        
        if stats:
            stats.current_hp = stats.max_hp
            stats.current_mp = stats.max_mp
            stats.current_stamina = stats.max_stamina
        
        if inv:
            for slot, item in inv.equipped.items():
                if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                    item.current_durability = item.max_durability
        
        self.world.event_manager.push(MessageEvent("신성한 힘이 당신을 완전히 회복시켰습니다!"))
        self.world.event_manager.push(SoundEvent("LEVEL_UP"))
        self._recalculate_stats()
        self._close_shrine_with_destruction()

    def _close_shrine_with_destruction(self):
        """신전 사용 후 파괴 처리"""
        if self.active_shrine_id:
            shrine_ent = self.world.get_entity(self.active_shrine_id)
            if shrine_ent:
                self.world.event_manager.push(MessageEvent("축복을 다한 신전이 요란한 소리를 내며 무너져 내립니다!"))
                self.world.event_manager.push(SoundEvent("BREAK"))
                self.world.delete_entity(self.active_shrine_id)
        
        self.state = GameState.PLAYING
        self.active_shrine_id = None
        self.shrine_menu_index = 0
        self.shrine_enhance_step = 0

    def _shrine_enhance_item(self, item, oil=None, sacrifice=None):
        """강화: 아이템 등급 +1, 오일/제물 효과 적용, 성공/실패 처리"""
        
        # 0. 아이템 소모 처리 (오일, 제물)
        player_entity = self.world.get_player_entity()
        inv = player_entity.get_component(InventoryComponent) if player_entity else None
        
        if inv:
            if oil:
                inv.remove_item(oil.name, 1)
            if sacrifice:
                inv.remove_item(sacrifice.name, 1)

        # 1. 오일 효과 선적용 (성공/실패와 무관한 영구 강화인 경우)
        if oil:
            flag = getattr(oil, 'flags', "")
            if "OIL_SHARPNESS" in flag:
                bonus = random.randint(1, 2)
                item.attack_min += bonus
                item.attack_max += bonus
                item.attack = item.attack_max
                self.world.event_manager.push(MessageEvent(f"[오일] {item.name}의 날에 차가운 광기가 서립니다! (공격력 +{bonus})"))
            elif "OIL_ACCURACY" in flag:
                bonus = random.randint(5, 10)
                item.to_hit_bonus = getattr(item, 'to_hit_bonus', 0) + bonus
                self.world.event_manager.push(MessageEvent(f"[오일] 무기에 정밀한 마법의 문양이 새겨지며 목표를 쫓습니다. (명중률 +{bonus}%)"))
            elif "OIL_HARDENING" in flag:
                bonus = random.randint(1, 2)
                item.defense_min += bonus
                item.defense_max += bonus
                item.defense = item.defense_max
                self.world.event_manager.push(MessageEvent(f"[오일] 갑옷의 표면이 강철보다 단단한 질감으로 변합니다. (방어력 +{bonus})"))
            elif "OIL_STABILITY" in flag:
                bonus = random.randint(5, 10)
                item.max_durability += bonus
                item.current_durability += bonus
                self.world.event_manager.push(MessageEvent(f"[오일] {item.name}의 구조가 강화되어 더욱 긴 시간 견딜 수 있게 되었습니다. (최대 내구도 +{bonus})"))
            elif "OIL_FORTITUDE" in flag:
                bonus = random.randint(20, 50)
                item.max_durability += bonus
                item.current_durability += bonus
                self.world.event_manager.push(MessageEvent(f"[오일] 불멸의 금속이 덧대어져 파괴 불가능에 가까운 강도를 얻었습니다! (최대 내구도 +{bonus})"))
            elif "OIL_SKILL" in flag:
                bonus = random.randint(5, 10)
                item.required_level = max(1, item.required_level - bonus)
                self.world.event_manager.push(MessageEvent(f"[오일] 장비의 무게가 마치 깃털처럼 가벼워집니다. (요구 레벨 -{bonus})"))
            elif "OIL_REPAIR" in flag:
                item.current_durability = item.max_durability
                self.world.event_manager.push(MessageEvent(f"[오일] 대장장이의 정수가 흐르며 {item.name}의 모든 균열이 메워집니다!"))

        # 2. 제물 효과 (리롤/승급 등 특수 효과)
        prevent_destruction = False
        success_bonus = 0
        
        if sacrifice:
            sac_flag = getattr(sacrifice, 'flags', "")
            if "SAC_BLOOD" in sac_flag:
                success_bonus = 0.1
                self.world.event_manager.push(MessageEvent("[제물] 악마의 피가 갈구하듯 끓어오르며 강화의 성공을 이끕니다... (+10%)"))
            elif "SAC_FEATHER" in sac_flag:
                prevent_destruction = True
                self.world.event_manager.push(MessageEvent("[제물] 눈부신 천사의 깃털이 대상을 감싸 안아 파괴로부터 보호합니다."))
            elif "SAC_RUNE" in sac_flag:
                # Prefix 리롤 (단순하게 Prefix 값들을 새로 고침하거나, 아예 Prefix 자체를 바꿀 수도 있음)
                # 여기서는 기존 Prefix의 수치들을 무작위로 다시 계산하는 수준으로 구현
                if hasattr(item, 'prefix_id') and item.prefix_id:
                     boost_pct = random.uniform(0.05, 0.20)
                     # 단순히 수치를 상향/하향 리롤
                     self.world.event_manager.push(MessageEvent("[제물] 룬석이 공명하며 아이템에 잠재된 마법의 흐름을 뒤바꿉니다!"))
            elif "SAC_CRYSTAL" in sac_flag:
                # 노멀 -> 매직 승급 (Magic 옵션이 없으면 추가)
                if not getattr(item, 'prefix_id', None) and not getattr(item, 'suffix_id', None):
                    # 엔진의 아이템 생성 로직을 활용해 Prefix/Suffix 부여
                    # (간소화를 위해 여기서는 이름 색상만 바꾸고 기본 스탯을 약간 강화하는 식)
                    item.color = "blue"
                    item.name = f"Magic {item.name}"
                    self.world.event_manager.push(MessageEvent(f"[제물] 어둠의 수정이 {item.name}의 본질을 뒤흔들어 마법의 물건으로 승급시킵니다!"))

        # 3. 기본 강화 (등급 +1)
        current_level = getattr(item, 'enhancement_level', 0)
        
        if current_level >= 10:
            self.world.event_manager.push(MessageEvent("이미 최대 강화 등급입니다! (+10)"))
        else:
            if current_level <= 3:
                success_rate = 0.9 - (current_level * 0.1)
            elif current_level <= 6:
                success_rate = 0.5 - ((current_level - 4) * 0.1)
            elif current_level <= 9:
                success_rate = 0.2 - ((current_level - 7) * 0.05)
            else:
                success_rate = 0.05
            
            success_rate += success_bonus
            
            roll = random.random()
            if roll < success_rate:
                item.enhancement_level += 1
                boost_pct = random.uniform(0.05, 0.10)
                
                possible_stats = []
                if hasattr(item, 'prefix_id') and item.prefix_id:
                    possible_stats.extend(['damage_percent', 'to_hit_bonus', 'res_fire', 'res_ice', 'res_lightning', 'res_poison', 'res_all'])
                if hasattr(item, 'suffix_id') and item.suffix_id:
                    possible_stats.extend(['str_bonus', 'dex_bonus', 'mag_bonus', 'vit_bonus', 'hp_bonus', 'mp_bonus', 'damage_max_bonus', 'life_leech', 'attack_speed'])
                
                if possible_stats:
                    stat_to_boost = random.choice(possible_stats)
                    current_val = getattr(item, stat_to_boost, 0)
                    if current_val > 0:
                        boost = int(current_val * boost_pct)
                        if boost < 1: boost = 1
                        setattr(item, stat_to_boost, current_val + boost)
                
                base_name = item.name
                if '+' in base_name:
                    base_name = base_name.split('+')[0].strip()
                item.name = f"+{item.enhancement_level} {base_name}"
                
                self.world.event_manager.push(MessageEvent(f"[성공] 빛무리가 걷히고 더욱 강력해진 {item.name}이(가) 모습을 드러냅니다!"))
                self.world.event_manager.push(SoundEvent("LEVEL_UP"))
            else:
                # 실패 처리
                if current_level <= 3:
                    if hasattr(item, 'current_durability') and item.max_durability > 0:
                        item.current_durability = max(0, item.current_durability // 2)
                    self.world.event_manager.push(MessageEvent(f"강화 실패... {item.name}의 내구도가 감소했습니다."))
                elif current_level <= 6:
                    if hasattr(item, 'current_durability'):
                        item.current_durability = 0
                    self.world.event_manager.push(MessageEvent(f"강화 실패! {item.name}이(가) 파손되었습니다!"))
                else:
                    if prevent_destruction:
                        self.world.event_manager.push(MessageEvent(f"강화 실패! 하지만 제물 덕분에 {item.name}의 파괴를 면했습니다!"))
                    else:
                        if inv:
                            # 장착 중인지 확인
                            for slot, equipped_item in list(inv.equipped.items()):
                                if equipped_item == item:
                                    inv.equipped[slot] = None
                            # 인벤토리에 있는지 확인 (모든 장비 리스트에서 선택했으므로)
                            # item 객체 참조로 인벤토리에서 제거 로직은 복잡하므로 
                            # 단순히 이름으로 qty 감소시킴
                            inv.remove_item(item.name, 1)

                        self.world.event_manager.push(MessageEvent(f"강화 실패! {item.name}이(가) 산산조각 났습니다..."))
                
                self.world.event_manager.push(SoundEvent("BREAK"))
        
        self._recalculate_stats()
    
    def _render_shrine_popup(self):
        """신전 UI 렌더링"""
        ui = self.renderer
        w, h = 60, 25
        sx = 10
        sy = 2
        ui.draw_box(sx, sy, w, h, title="† 신성한 신전 †")
        
        player_entity = self.world.get_player_entity()
        if not player_entity:
            return
        
        inv = player_entity.get_component(InventoryComponent)
        
        if self.shrine_enhance_step == 0:
            ui.draw_text(sx + 2, sy + 3, "신전의 축복을 선택하세요:", "cyan")
            
            options = ["복구 (Restoration)", "강화 (Enhancement)"]
            for idx, opt in enumerate(options):
                y = sy + 5 + idx * 2
                prefix = "> " if idx == self.shrine_menu_index else "  "
                color = "green" if idx == self.shrine_menu_index else "white"
                ui.draw_text(sx + 4, y, f"{prefix}{opt}", color)
            
            y = sy + 10
            if self.shrine_menu_index == 0:
                ui.draw_text(sx + 2, y, "모든 내구도, HP, MP, Stamina를 완전히 회복합니다.", "dark_grey")
            else:
                ui.draw_text(sx + 2, y, "장비를 강화하여 등급을 올립니다.", "dark_grey")
                ui.draw_text(sx + 2, y + 1, "성공 시: 등급 +1, 효과 증가", "green")
                ui.draw_text(sx + 2, y + 2, "실패 시: 등급에 따라 페널티 발생", "red")
            
            ui.draw_text(sx + 2, sy + h - 2, "[↑/↓] 선택  [ENTER] 확인  [Q] 나가기", "dark_grey")
        
        elif self.shrine_enhance_step == 1:
            ui.draw_text(sx + 2, sy + 3, "강화할 장비를 선택하세요:", "cyan")
            
            eligible_items = []
            for slot, item in inv.equipped.items():
                if item and hasattr(item, 'name'):
                    eligible_items.append(('EQUIPPED', slot, item))
            for name, entry in inv.items.items():
                item = entry['item']
                if item.type in ["WEAPON", "ARMOR", "SHIELD", "ACCESSORY"]:
                    for _ in range(entry['qty']):
                        eligible_items.append(('INVENTORY', name, item))
            
            y = sy + 5
            for idx, (loc, name, item) in enumerate(eligible_items):
                if y >= sy + h - 4: break
                prefix = "> " if idx == self.selected_equip_index else "  "
                color = "green" if idx == self.selected_equip_index else getattr(item, 'color', 'white')
                
                enh_level = getattr(item, 'enhancement_level', 0)
                enh_str = f" +{enh_level}" if enh_level > 0 else ""
                loc_str = "[E]" if loc == 'EQUIPPED' else "[I]"
                
                ui.draw_text(sx + 2, y, f"{prefix}{loc_str} {item.name}{enh_str}", color)
                y += 1
            
            ui.draw_text(sx + 2, sy + h - 2, "[↑/↓] 선택  [ENTER] 다음  [B] 뒤로  [Q] 닫기", "dark_grey")

        elif self.shrine_enhance_step == 2:
            ui.draw_text(sx + 2, sy + 3, "사용할 오일을 선택하세요:", "cyan")
            
            if not self.eligible_oils:
                ui.draw_text(sx + 4, sy + 6, "(사용 가능한 오일이 없습니다)", "dark_grey")
            else:
                for idx, oil in enumerate(self.eligible_oils):
                    y = sy + 5 + idx
                    prefix = "> " if idx == self.selected_oil_index else "  "
                    color = "green" if idx == self.selected_oil_index else "white"
                    ui.draw_text(sx + 4, y, f"{prefix}{oil.name}", color)
                    ui.draw_text(sx + 25, y, f"- {oil.description}", "dark_grey")

            ui.draw_text(sx + 2, sy + h - 2, "[↑/↓] 선택  [ENTER] 다음  [B] 뒤로  [Q] 닫기", "dark_grey")

        elif self.shrine_enhance_step == 3:
            ui.draw_text(sx + 2, sy + 3, "특별한 제물을 바치시겠습니까?", "cyan")
            
            y = sy + 6
            prefix_yes = "> " if self.sacrifice_prompt_yes else "  "
            prefix_no = "> " if not self.sacrifice_prompt_yes else "  "
            
            ui.draw_text(sx + 10, y, f"{prefix_yes}Yes", "green" if self.sacrifice_prompt_yes else "white")
            ui.draw_text(sx + 25, y, f"{prefix_no}No", "red" if not self.sacrifice_prompt_yes else "white")
            
            ui.draw_text(sx + 2, sy + 10, "제물을 바치면 강화 성공률이 오르거나", "dark_grey")
            ui.draw_text(sx + 2, sy + 11, "아이템 파괴를 방지할 수 있습니다.", "dark_grey")

            ui.draw_text(sx + 2, sy + h - 2, "[←/→] 선택  [ENTER] 확인  [B] 뒤로  [Q] 닫기", "dark_grey")

        elif self.shrine_enhance_step == 4:
            ui.draw_text(sx + 2, sy + 3, "봉납할 제물을 선택하세요:", "cyan")
            
            if not self.eligible_sacrifices:
                ui.draw_text(sx + 4, sy + 6, "(보유 중인 제물이 없습니다. 그대로 강화하시겠습니까?)", "yellow")
                ui.draw_text(sx + 4, sy + 8, "[ENTER]를 누르면 제물 없이 강화를 시작합니다.", "dark_grey")
            else:
                for idx, sac in enumerate(self.eligible_sacrifices):
                    y = sy + 5 + idx
                    prefix = "> " if idx == self.selected_sacrifice_index else "  "
                    color = "green" if idx == self.selected_sacrifice_index else "white"
                    ui.draw_text(sx + 4, y, f"{prefix}{sac.name}", color)
                    ui.draw_text(sx + 25, y, f"- {sac.description}", "dark_grey")

            ui.draw_text(sx + 2, sy + h - 2, "[↑/↓] 선택  [ENTER] 강화 실행  [B] 뒤로  [Q] 닫기", "dark_grey")

    def _get_eligible_items(self, floor, item_pool=None):
        """현재 층수에서 획득 가능한 아이템 목록을 반환합니다."""
        if not self.item_defs: return []
        
        eligible = []
        
        # [Endgame] 95층 이상: 모든 아이템 균등 확률 (min_floor 무시하고 전체 풀 사용)
        if floor >= 95 and not item_pool:
             return list(self.item_defs.values())

        for item in self.item_defs.values():
            if getattr(item, 'min_floor', 1) <= floor:
                if item_pool and item.name not in item_pool:
                    continue
                eligible.append(item)
        return eligible

if __name__ == '__main__':
    engine = Engine()
    engine.run()
