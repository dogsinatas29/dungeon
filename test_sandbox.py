import os
import sys

# 프로젝트 루트 경로 추가 (부모 디렉토리 임포트 가능하도록)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon.engine import Engine
from dungeon.ecs import World
from dungeon.components import (
    PositionComponent, RenderComponent, StatsComponent, 
    InventoryComponent, LevelComponent, MonsterComponent, AIComponent, MapComponent
)
from dungeon.data_manager import ItemDefinition
from dungeon.ui import ConsoleUI

class SandboxEngine(Engine):
    """테스트를 위해 환경이 미리 설정된 샌드박스 엔진"""
    def __init__(self):
        super().__init__(player_name="TESTER")
        self._setup_sandbox()

    def _setup_sandbox(self):
        """환경 하드코딩 설정"""
        self.world.event_manager.push(dict(type="MessageEvent", text="=== SANDBOX MODE ENABLED ==="))
        
        # 1. 테스트용 무기 생성 및 장착
        long_bow = ItemDefinition(
            name="슈퍼 활", type="WEAPON", description="테스트용 초장거리 활", 
            symbol="{", color="gold", required_level=1, attack=20, defense=0, 
            hp_effect=0, mp_effect=0, hand_type=2, attack_range=10
        )
        
        spear = ItemDefinition(
            name="실험용 창", type="WEAPON", description="테스트용 관통 창", 
            symbol="/", color="cyan", required_level=1, attack=15, defense=5, 
            hp_effect=0, mp_effect=0, hand_type=2, attack_range=4
        )
        
        player_entity = self.world.get_player_entity()
        if player_entity:
            inv = player_entity.get_component(InventoryComponent)
            # 아이템 추가
            inv.items["BOW_TEST"] = {'item': long_bow, 'qty': 1}
            inv.items["SPEAR_TEST"] = {'item': spear, 'qty': 1}
            
            # 활 즉시 장착
            inv.equipped["손1"] = long_bow
            inv.equipped["손2"] = "(양손 점유)"
            
            # 스킬 비우기 (스킬북 테스트용)
            inv.skills = []
            inv.skill_slots = [None] * 5
            
            # 스킬북 추가
            from dungeon.data_manager import load_data_from_csv
            # items.csv 로드 (절대 경로 혹은 실행 위치 기준)
            items_dict = load_data_from_csv('/home/dogsinatas/python_project/dungeon/data/items.csv', ItemDefinition)
            fb_book = items_dict.get("파이어볼 스킬북")
            if fb_book:
                inv.items["파이어볼 스킬북"] = {"item": fb_book, "qty": 1}
            
            ww_book = items_dict.get("휠윈드 스킬북")
            if ww_book:
                inv.items["휠윈드 스킬북"] = {"item": ww_book, "qty": 1}

            ib_book = items_dict.get("아이스 볼트 스킬북")
            if ib_book:
                inv.items["아이스 볼트 스킬북"] = {"item": ib_book, "qty": 1}
            
            sb_book = items_dict.get("방패 밀치기 스킬북")
            if sb_book:
                inv.items["방패 밀치기 스킬북"] = {"item": sb_book, "qty": 1}

            self._recalculate_stats()

        # 2. 테스트용 몬스터 배치 (직선 상에 배치하여 관통 테스트)
        for i in range(1, 6):
            # 플레이어 우측으로 나란히 배치 (플레이어는 보통 중앙 근처 맵 생성 로직에 따라 배치됨)
            # 안전하게 플레이어 위치 기준으로 상대 배치
            p_pos = player_entity.get_component(PositionComponent)
            m = self.world.create_entity()
            self.world.add_component(m.entity_id, PositionComponent(x=p_pos.x + (i * 2), y=p_pos.y))
            self.world.add_component(m.entity_id, RenderComponent(char="M", color="red"))
            self.world.add_component(m.entity_id, StatsComponent(max_hp=50, current_hp=50, attack=5, defense=2))
            self.world.add_component(m.entity_id, MonsterComponent(type_name="샌드백", level=1))
            self.world.add_component(m.entity_id, AIComponent(behavior=AIComponent.STATIONARY))

        # 3. 테스트용 몬스터 배치 (플레이어 좌측 2x2 뭉치 - 범위 공격 테스트용)
        for row in range(2):
            for col in range(2):
                mx, my = p_pos.x - 2 - col, p_pos.y + row
                m = self.world.create_entity()
                self.world.add_component(m.entity_id, PositionComponent(x=mx, y=my))
                self.world.add_component(m.entity_id, RenderComponent(char="D", color="purple"))
                self.world.add_component(m.entity_id, StatsComponent(max_hp=100, current_hp=100, attack=0, defense=0))
                self.world.add_component(m.entity_id, MonsterComponent(type_name="더미", level=1))
                self.world.add_component(m.entity_id, AIComponent(behavior=AIComponent.STATIONARY))

def run_sandbox():
    ui = ConsoleUI()
    engine = SandboxEngine()
    try:
        engine.run()
    except Exception as e:
        print(f"Error in Sandbox: {e}")
        import traceback
        traceback.print_exc()
    finally:
        del ui

if __name__ == "__main__":
    run_sandbox()
