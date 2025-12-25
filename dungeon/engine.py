# dungeon/engine.py - 게임의 실행 흐름을 관리하는 메인 모듈

import os
import time
import random
import readchar # readchar 임포트 추가
from typing import List, Dict, Tuple, Any
from .map import DungeonMap

# 필요한 모듈 임포트
from .ecs import World, EventManager, initialize_event_listeners
from .components import (
    PositionComponent, RenderComponent, StatsComponent, InventoryComponent, 
    LevelComponent, MapComponent, MessageComponent, MonsterComponent, 
    AIComponent, LootComponent, CorpseComponent, ChestComponent, ShopComponent
)
from .systems import InputSystem, MovementSystem, RenderSystem, MonsterAISystem, CombatSystem, MessageEvent, DirectionalAttackEvent, MapTransitionEvent, ShopOpenEvent
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
        self.player_name = player_name
        self.state = GameState.PLAYING # 초기 상태
        self.is_attack_mode = False # 원거리 공격 모드
        self.current_level = 1 # 현재 던전 층수
        self.selected_item_index = 0 # 인벤토리 선택 인덱스
        self.inventory_category_index = 0 # 0: 아이템, 1: 장비, 2: 스크롤, 3: 스킬

        # 렌더러 초기화
        self.renderer = Renderer() 

        self._initialize_world(game_data)
        self._initialize_systems()
        
        # 시스템 등록 후, 이벤트 리스너를 한 번 더 초기화하여 시스템-이벤트 간 연결 완료
        initialize_event_listeners(self.world)

    def _initialize_world(self, game_data=None, preserve_player=None):
        """맵, 플레이어, 몬스터 등 초기 엔티티 생성"""
        # 맵 생성 (DungeonMap 사용)
        width = 120
        height = 60
        rng = random.Random()
        
        # 이전 층 데이터가 있으면 초기화
        if preserve_player:
            # 월드 전체 초기화 (EventManager와 System 리스너는 유지되어야 함)
            # ecs.World에 clear_except_systems 같은 메서드가 없으므로 수동으로 엔티티 삭제
            for e_id in list(self.world._entities.keys()):
                self.world.delete_entity(e_id)
            # ID 초기화 (선택적)
            self.world._next_entity_id = 1

        # DungeonMap 인스턴스 생성
        dungeon_map = DungeonMap(width, height, rng)
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
        else:
            self.world.add_component(player_entity.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, max_mp=50, current_mp=50, max_stamina=100, current_stamina=100))
            self.world.add_component(player_entity.entity_id, LevelComponent(level=1, exp=0, exp_to_next=100, job="Novice"))
        
        # 샘플 아이템 추가 (UI 검증용)
        self.item_defs = load_item_definitions()
        item_defs = self.item_defs
        sample_items = {}
        if item_defs:
            # WEAPON, ARMOR, CONSUMABLE 등 다양한 타입 준비
            for name, item in item_defs.items():
                sample_items[name] = {'item': item, 'qty': 1}
        
        # 장착 아이템 설정 (객체 참조로 변경)
        equipped = {slot: None for slot in ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]}
        if "가죽 갑옷" in sample_items:
            equipped["몸통"] = sample_items["가죽 갑옷"]["item"]
        if "낡은 검" in sample_items:
            equipped["손1"] = sample_items["낡은 검"]["item"]
        if "힘의 반지" in sample_items:
            equipped["액세서리1"] = sample_items["힘의 반지"]["item"]

        self.world.add_component(player_entity.entity_id, InventoryComponent(
            items=sample_items, 
            equipped=equipped,
            item_slots=["체력 물약", "마력 물약", "화염 스크롤", "순간 이동 스크롤", "마커"],
            skill_slots=["기본 공격", "파이어볼", "힐", None, None],
            skills=["기본 공격", "파이어볼", "힐"]
        ))
        
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
        message_comp.add_message(f"{self.player_name}님, 던전에 오신 것을 환영합니다!")
        message_comp.add_message("WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.")
        self.world.add_component(message_entity.entity_id, message_comp)
        
        # 4. 몬스터 및 보물상자 엔티티 생성
        all_elements = [ELEMENT_NONE, ELEMENT_WATER, ELEMENT_FIRE, ELEMENT_WOOD, ELEMENT_EARTH, ELEMENT_POISON]
        
        for i, room in enumerate(dungeon_map.rooms[1:]): # 첫 번째 방(플레이어 시작) 제외
            # 방의 중앙에 몬스터 배치
            monster_x, monster_y = room.center
            monster_entity = self.world.create_entity()
            self.world.add_component(monster_entity.entity_id, PositionComponent(x=monster_x, y=monster_y))
            
            # 몬스터 속성 결정 (랜덤)
            monster_element = random.choice(all_elements)
            color = ELEMENT_COLORS.get(monster_element, "white")
            
            # AI 패턴 결정 (0: 정지, 1: 도망, 2: 추적)
            behavior = i % 3
            type_name = "Goblin"
            
            # 능력치 초기화 (기본값)
            max_hp, atk, df = 30, 5, 2
            
            if behavior == AIComponent.CHASE: 
                type_name = "Aggressive Goblin"
                atk = 8  # 추적형은 공격력이 높음
                if monster_element == ELEMENT_FIRE: atk += 2 # 불 속성 공격성 추가
            elif behavior == AIComponent.FLEE: 
                type_name = "Cowardly Goblin"
                df = 5   # 도망형은 방어력이 높음
            else:
                type_name = "Lazy Goblin"
                max_hp = 50 # 정지형은 맷집이 좋음
            
            self.world.add_component(monster_entity.entity_id, RenderComponent(char='g', color=color))
            self.world.add_component(monster_entity.entity_id, MonsterComponent(type_name=type_name))
            self.world.add_component(monster_entity.entity_id, AIComponent(behavior=behavior, detection_range=8))
            self.world.add_component(monster_entity.entity_id, StatsComponent(
                max_hp=max_hp, current_hp=max_hp, attack=atk, defense=df, element=monster_element
            ))

            # 5. 방 구석에 보물상자 배치 (30% 확률)
            if random.random() < 0.3:
                # 방의 랜덤한 위치 (벽이 아닌 곳)
                chest_x = random.randint(room.x1 + 1, room.x2 - 1)
                chest_y = random.randint(room.y1 + 1, room.y2 - 1)
                
                # 플레이어나 몬스터와 겹치지 않는지 확인 (단순화 가능)
                chest_entity = self.world.create_entity()
                self.world.add_component(chest_entity.entity_id, PositionComponent(x=chest_x, y=chest_y))
                self.world.add_component(chest_entity.entity_id, RenderComponent(char='*', color='yellow'))
                self.world.add_component(chest_entity.entity_id, ChestComponent())
                
                # 랜덤 아이템 1~2개 포함
                loot_items = []
                if item_defs:
                    random_keys = random.sample(list(item_defs.keys()), min(len(item_defs), 2))
                    for k in random_keys:
                        loot_items.append({'item': item_defs[k], 'qty': 1})
                
                self.world.add_component(chest_entity.entity_id, LootComponent(items=loot_items, gold=random.randint(10, 50)))

            # 6. 첫 번째 방(시작 방) 근처에 상인 배치 (50% 확률)
            if i == 0 and random.random() < 0.5:
                shop_x, shop_y = room.x1 + 2, room.y1 + 2 # 구석 근처
                shop_entity = self.world.create_entity()
                self.world.add_component(shop_entity.entity_id, PositionComponent(x=shop_x, y=shop_y))
                self.world.add_component(shop_entity.entity_id, RenderComponent(char='S', color='magenta'))
                self.world.add_component(shop_entity.entity_id, ShopComponent(items=[
                    {'item': item_defs.get('체력 물약'), 'price': 20},
                    {'item': item_defs.get('마력 물약'), 'price': 20},
                    {'item': item_defs.get('화염 스크롤'), 'price': 50}
                ]))
                self.world.add_component(shop_entity.entity_id, MonsterComponent(type_name="상인")) # 충돌 감지를 위해 MonsterComponent 활용 가능

    def _initialize_systems(self):
        """시스템 등록 (실행 순서가 중요함)"""
        self.input_system = InputSystem(self.world)
        self.monster_ai_system = MonsterAISystem(self.world)
        self.movement_system = MovementSystem(self.world)
        self.combat_system = CombatSystem(self.world)
        self.render_system = RenderSystem(self.world)
        
        # 2. 시스템 순서 등록: 입력 -> AI -> 이동 -> 전투(이벤트 기반) -> 렌더링
        systems = [
            self.input_system,
            self.monster_ai_system,
            self.movement_system,
            self.combat_system,
            self.render_system
        ]
        for system in systems:
            self.world.add_system(system)
            
        # 3. 추가적인 전역 이벤트 리스너 등록 (Engine 자체 핸들러 등)
        self.world.event_manager.register(MapTransitionEvent, self)
        self.world.event_manager.register(ShopOpenEvent, self)

        # 4. 모든 시스템의 리스너 초기화 헬퍼 호출
        initialize_event_listeners(self.world)

    def _get_input(self) -> str:
        """사용자 입력을 받아 반환 (readchar 사용)"""
        # input() 대신 readchar.readkey()를 사용하여 Enter 없이 즉시 입력 처리
        return readchar.readkey()

    # dungeon/engine.py 내 Engine.run 메서드 수정 (주요 부분만)

    def run(self):
        """메인 게임 루프"""
        self.is_running = True
        
        # 첫 렌더링
        self._render()
        
        while self.is_running:
            # 1. 사용자 입력 처리
            action = self._get_input()
            
            if self.state == GameState.PLAYING:
                if action == 'i' or action == 'I':
                    self.state = GameState.INVENTORY
                    self._render()
                    continue
                
                # 단축키 처리 (1~5번 아이템, 6~0번 스킬)
                if action in "1234567890":
                    self._trigger_quick_slot(action)
                    self._render()
                    continue

                self.turn_number += 1
                
                # InputSystem에서 턴 소모 여부 결정
                turn_spent = self.input_system.handle_input(action)
                
                if turn_spent:
                    # 2. 게임 상태 업데이트 (모든 시스템 순차 실행)
                    # InputSystem은 handle_input에서 이미 처리했으므로 제외하고 실행
                    for system in self.world._systems:
                        if system is not self.input_system and system is not None:
                            system.process()
                    
                    # 3. 이벤트 처리 (충돌 메시지 등 처리)
                    self.world.event_manager.process_events()
                    
                    # 4. 상태 변경 후 화면 다시 그리기
                    self._render()
            
            elif self.state == GameState.INVENTORY:
                self._handle_inventory_input(action)
                self._render()
            elif self.state == GameState.SHOP:
                self._handle_shop_input(action)
                self._render()
                
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
        self.world.event_manager.push(MessageEvent("상점에 오신 것을 환영합니다!"))

    def _handle_shop_input(self, action: str):
        """상점 상태에서의 입력 처리"""
        if action == readchar.key.ESC or action == 'q':
            self.state = GameState.PLAYING
            return

        shopkeeper = self.world.get_entity(self.active_shop_id)
        if not shopkeeper:
            self.state = GameState.PLAYING
            return

        shop_comp = shopkeeper.get_component(ShopComponent)
        if not shop_comp: return

        item_count = len(shop_comp.items)

        if action == readchar.key.UP:
             self.selected_shop_item_index = max(0, self.selected_shop_item_index - 1)
        elif action == readchar.key.DOWN:
             self.selected_shop_item_index = min(item_count - 1, self.selected_shop_item_index + 1)
        elif action == readchar.key.ENTER or action == '\r' or action == '\n':
             # 아이템 구매 로직
             self._buy_item(shop_comp.items[self.selected_shop_item_index])

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
        if action == 'i' or action == 'I' or action == readchar.key.ESC:
            self.state = GameState.PLAYING
            return
        
        player_entity = self.world.get_player_entity()
        if not player_entity: return

        from .components import InventoryComponent
        inv = player_entity.get_component(InventoryComponent)
        if not inv: return

        # 1. 현재 카테고리에 해당하는 아이템 필터링
        filtered_items = []
        if self.inventory_category_index == 0: # 아이템 (소모품)
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type == 'CONSUMABLE']
        elif self.inventory_category_index == 1: # 장비
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type in ['WEAPON', 'ARMOR']]
        elif self.inventory_category_index == 2: # 스크롤
            filtered_items = [(id, data) for id, data in inv.items.items() if data['item'].type == 'SCROLL']
        elif self.inventory_category_index == 3: # 스킬
            filtered_items = [(s, {'item_name': s}) for s in inv.skills]

        item_count = len(filtered_items)

        # 2. 내비게이션 처리
        if action == readchar.key.UP:
             self.selected_item_index = max(0, self.selected_item_index - 1)
        elif action == readchar.key.DOWN:
             if item_count > 0:
                 self.selected_item_index = min(item_count - 1, self.selected_item_index + 1)
        elif action == readchar.key.LEFT:
             self.inventory_category_index = (self.inventory_category_index - 1) % 4
             self.selected_item_index = 0
        elif action == readchar.key.RIGHT:
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
                     self._assign_quick_slot(item_id, "SKILL")

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

        num = int(key)
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
                else:
                    self.world.event_manager.push(MessageEvent(f"{item_name}을(를) 인벤토리에서 찾을 수 없습니다."))
            else:
                self.world.event_manager.push(MessageEvent(f"{num}번 퀵슬롯이 비어있습니다."))
        
        else: # 스킬 슬롯 (6,7,8,9,0)
            # 0번은 10번 슬롯 (index 4)
            idx = 4 if num == 0 else num - 6
            skill_name = inv.skill_slots[idx]
            if skill_name:
                self.world.event_manager.push(MessageEvent(f"{skill_name} 스킬을 사용합니다! (시스템 준비 중)"))
                # TODO: 스킬 시스템 연동 (MP 소모, 효과 등)
            else:
                slot_num = 10 if num == 0 else num
                self.world.event_manager.push(MessageEvent(f"{slot_num}번 스킬 슬롯이 비어있습니다."))

    def _use_item(self, item_id, item_data):
        """소모품 아이템 사용"""
        item = item_data['item']
        player_entity = self.world.get_player_entity()
        if not player_entity: return
        
        stats = player_entity.get_component(StatsComponent)
        inv = player_entity.get_component(InventoryComponent)
        
        if not stats or not inv: return

        # 효과 적용
        old_hp = stats.current_hp
        old_mp = stats.current_mp
        
        if item.hp_effect != 0:
            stats.current_hp = min(stats.max_hp, stats.current_hp + item.hp_effect)
        if item.mp_effect != 0:
            stats.current_mp = min(stats.max_mp, stats.current_mp + item.mp_effect)
            
        hp_recovered = stats.current_hp - old_hp
        
        # 메시지 추가
        msg = f"{item.name}을(를) 사용했습니다."
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

        # 2. 장착 로직
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
        
        # 보너스 합산
        for slot, item in inv.equipped.items():
            # ItemDefinition 객체인 경우에만 스탯 합산
            from .data_manager import ItemDefinition
            if isinstance(item, ItemDefinition):
                stats.attack += item.attack
                stats.defense += item.defense

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
                    
                    char = map_comp.tiles[world_y][world_x]
                    
                    # 맵 시인성 개선: 바닥(.)과 인접하지 않은 벽(#)은 공백으로 처리
                    if char == "#":
                        is_visible_wall = False
                        # 8방향 탐색
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
                self.renderer.draw_char(screen_x, screen_y, render.char, render.color)

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
                self.renderer.draw_text(2, current_y, f"{atk_str:<10} {def_str:<10}", "white")


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
        eq_start_y = 10
        self.renderer.draw_text(RIGHT_SIDEBAR_X + 2, eq_start_y, "[ EQUIP ]", "gold")
        eq_y = eq_start_y + 1
        if player_entity:
            inv_comp = player_entity.get_component(InventoryComponent)
            if inv_comp:
                slots = ["머리", "몸통", "장갑", "신발", "손1", "손2", "액세서리1", "액세서리2"]
                for i, slot in enumerate(slots):
                    if eq_y >= 19: break # 사이드바 높이 제한 (스크롤/스킬 영역 확보)
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
        qs_start_y = 19
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
            self.renderer.draw_text(0, guide_y, " [MOVE] Arrows | [I] Inventory | [Space] Attack Mode | [Q] Quit", "green")
        
        # 6. 인벤토리 팝업 렌더링 (INVENTORY 상태일 때만)
        if self.state == GameState.INVENTORY:
            self._render_inventory_popup()

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
                     filtered_items = [(id, data) for id, data in inv_comp.items.items() if data['item'].type == 'CONSUMABLE']
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
        help_text = "[←/→] 탭 전환  [↑/↓] 선택  [E/ENTER] 장착/등록/사용  [ESC/I] 닫기"
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
        
        # 제목
        title = "[ 상 점 ]"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(title)) // 2, start_y + 1, title, "gold")
        
        # 2. 플레이어 골드 표시
        player_entity = self.world.get_player_entity()
        if player_entity:
            stats = player_entity.get_component(StatsComponent)
            if stats:
                self.renderer.draw_text(start_x + 2, start_y + 3, f"소지 골드: {stats.gold} G", "yellow")
        
        self.renderer.draw_text(start_x + 2, start_y + 4, "-" * (POPUP_WIDTH - 4), "dark_grey")
        
        # 3. 상품 목록 표시
        shopkeeper = self.world.get_entity(self.active_shop_id)
        if shopkeeper:
            shop_comp = shopkeeper.get_component(ShopComponent)
            if shop_comp:
                for i, entry in enumerate(shop_comp.items):
                    item = entry['item']
                    price = entry['price']
                    
                    item_y = start_y + 5 + i
                    if item_y >= start_y + POPUP_HEIGHT - 2: break
                    
                    prefix = "> " if i == self.selected_shop_item_index else "  "
                    color = "white" if i == self.selected_shop_item_index else "dark_grey"
                    if i == self.selected_shop_item_index: color = "green"
                    
                    # 상품명 (왼쪽 정렬) 및 가격 (오른쪽 정렬)
                    name_text = f"{prefix}{item.name}"
                    self.renderer.draw_text(start_x + 2, item_y, name_text, color)
                    price_text = f"{price:>5} G"
                    self.renderer.draw_text(start_x + POPUP_WIDTH - 10, item_y, price_text, color)
        
        # 4. 하단 도움말
        guide_text = "[↑/↓] 선택  [ENTER] 구매  [Q/ESC] 나가기"
        self.renderer.draw_text(start_x + (POPUP_WIDTH - len(guide_text)) // 2, start_y + POPUP_HEIGHT - 2, guide_text, "dark_grey")

if __name__ == '__main__':
    engine = Engine()
    engine.run()
