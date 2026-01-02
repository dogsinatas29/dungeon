import os
import sys
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World, EventManager
from dungeon.components import InventoryComponent, LevelComponent, StatsComponent, PositionComponent, RenderComponent, MonsterComponent
from dungeon.systems import MessageEvent, CombatSystem, SkillUseEvent
from dungeon.data_manager import ItemDefinition, load_data_from_csv

class TestEngine(Engine):
    def __init__(self):
        super().__init__(player_name="LevelTester")
        # 테스트 환경 설정
        self.item_defs = load_data_from_csv('/home/dogsinatas/python_project/dungeon/data/items.csv', ItemDefinition)
        self.world.event_manager.push = MagicMock() # 메시지 캡처용

def verify_level_requirements():
    print("=== Verifying Level Requirements ===")
    
    engine = TestEngine()
    player = engine.world.get_player_entity()
    inv = player.get_component(InventoryComponent)
    level = player.get_component(LevelComponent)
    
    # 1. 레벨 1로 초기화
    level.level = 1
    print(f"[Setup] Player Level: {level.level}")
    
    # 2. 고레벨 장비 장착 테스트 (강철 검: Lv.5)
    print("[Test 1] Equip High Level Weapon (Steel Sword, Lv.5)...", end=" ")
    steel_sword = engine.item_defs.get("강철 검")
    if steel_sword:
        inv.items["SteelSword"] = {'item': steel_sword, 'qty': 1}
        # 인벤토리 인덱스 선택 시뮬레이션 (간략하게 직접 장착 함수 호출)
        engine._equip_selected_item({'item': steel_sword, 'qty': 1})
        
        # 장착 확인
        if inv.equipped.get("손1") == steel_sword:
            print("FAIL (Equipped despite low level)")
        else:
            # 메시지 확인
            calls = engine.world.event_manager.push.call_args_list
            expected_msg_part = "레벨이 부족하여"
            found = False
            for call in calls:
                if isinstance(call[0][0], MessageEvent) and expected_msg_part in call[0][0].text:
                    found = True
                    break
            
            if found:
                print("PASS (Blocked with message)")
            else:
                print("FAIL (Blocked but no message?)")
    else:
        print("SKIP (Steel Sword not found in data)")

    engine.world.event_manager.push.reset_mock()

    # 3. 고레벨 스킬북 사용 테스트 (파이어볼 Lv3: Lv.10)
    print("[Test 2] Use High Level Skillbook (Fireball Lv3, Lv.10)...", end=" ")
    fb_book_lv3 = engine.item_defs.get("파이어볼 스킬북 Lv3")
    if fb_book_lv3:
        # 엔진 초기화 시 기본적으로 들어있는 스킬 제거 (테스트 환경 정화)
        inv.skills = []
        inv.skill_levels = {}
        
        inv.items["FB_Book_Lv3"] = {'item': fb_book_lv3, 'qty': 1}
        engine._use_item("FB_Book_Lv3", inv.items["FB_Book_Lv3"])
        
        # 스킬 습득 확인
        if "파이어볼 Lv3" in inv.skills or inv.skill_levels.get("파이어볼", 0) >= 3:
            print(f"FAIL (Learned/Used despite low level. Skills: {inv.skills}, Level: {inv.skill_levels.get('파이어볼', 0)})")
        else:
            # 메시지 확인
            calls = engine.world.event_manager.push.call_args_list
            found = False
            for call in calls:
                if isinstance(call[0][0], MessageEvent) and "레벨이 부족하여" in call[0][0].text:
                    found = True
                    break
            if found:
                print("PASS (Blocked with message)")
            else:
                print("FAIL (Blocked but no message?)")
    else:
        print("SKIP (Fireball Book Lv3 not found)")

    engine.world.event_manager.push.reset_mock()
    
    # 4. 스킬 사용 레벨 제한 테스트
    # 강제로 스킬을 배웠다고 가정하고 사용 시도
    # (주의: 스킬북 사용은 _use_item에서 막히지만, 이미 배운 스킬을 '사용'하는 단계인 handle_skill_use_event도 막아야 함)
    # 직접 스킬 use event 발생 시키기
    print("[Test 3] Use High Level Skill (Simulated)...", end=" ")
    
    # 임시 스킬 정의 (Engine에 주입)
    skill_mock = type('obj', (object,), {
        'name': 'Ultima', 'required_level': 99, 'flags': set(), 'cost_value': 0
    })
    engine.skill_defs = {'Ultima': skill_mock}
    
    # 이벤트 발생
    combat_system = CombatSystem(engine.world)
    combat_system.event_manager.push = MagicMock() # CombatSystem의 EM도 Mocking
    
    event = SkillUseEvent(attacker_id=player.entity_id, skill_name='Ultima', dx=0, dy=0)
    combat_system.handle_skill_use_event(event)
    
    # 메시지 확인
    calls = combat_system.event_manager.push.call_args_list
    found = False
    for call in calls:
        if isinstance(call[0][0], MessageEvent) and "레벨이 부족하여" in call[0][0].text: # 시스템에서 출력하는 메시지 확인 필요
            # 시스템 메시지는 "아직 이 기술을 사용할 수 없습니다. (필요: Lv.X)" 로 구현함
            found = True
            break
        elif isinstance(call[0][0], MessageEvent) and "아직 이 기술을" in call[0][0].text:
             found = True
             break
            
    if found:
        print("PASS (Blocked with message)")
    else:
        print("FAIL (Skill used or no blocking message)")
        # 디버깅용
        # for call in calls:
        #    if isinstance(call[0][0], MessageEvent): print(f"Msg: {call[0][0].text}")

    print("=== Verification Complete ===\n")

if __name__ == "__main__":
    verify_level_requirements()
