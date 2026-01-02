import sys
import os
import time

# 프로젝트 경로 추가
sys.path.append('/home/dogsinatas/python_project/dungeon')

from dungeon.engine import Engine
from dungeon.components import StatsComponent, InventoryComponent, StatModifierComponent, LevelComponent
from dungeon.data_manager import ItemDefinition

def test_stat_modifiers():
    print("--- 능력치 강화 시스템 검증 시작 ---")
    
    # 1. 엔진 초기화 (테스트용)
    engine = Engine(player_name="Tester")
    world = engine.world
    player = world.get_player_entity()
    
    stats = player.get_component(StatsComponent)
    inv = player.get_component(InventoryComponent)
    
    if not stats:
        print("StatsComponent를 찾을 수 없습니다. 기본 생성 시도.")
        stats = StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5)
        player.add_component(stats)
    
    # base_str 등이 설정되어 있는지 확인 (components.py 업데이트 확인)
    if not hasattr(stats, 'base_str'):
        print("StatsComponent에 base_str이 없습니다. 업데이트 실패 여부 확인 필요.")
        return

    print(f"기본 스탯: STR={stats.str}, VIT={stats.vit}")
    base_str = stats.base_str
    base_vit = stats.base_vit

    # 2. 장비 착용 테스트
    print("\n[테스트 1] 장비 착용 (힘의 반지: STR +3)")
    ring = ItemDefinition(name="힘의 반지", type="ACCESSORY", description="", symbol="o", color="yellow", 
                          required_level=1, attack=0, defense=0, hp_effect=0, mp_effect=0, str_bonus=3)
    inv.equipped["액세서리1"] = ring
    engine._recalculate_stats()
    print(f"장착 후 스탯: STR={stats.str} (예상: {base_str + 3})")
    if stats.str != base_str + 3:
        raise ValueError(f"STR 불일치: {stats.str} != {base_str + 3}")

    # 3. 브약(Consumable) 사용 테스트
    print("\n[테스트 2] 소모품 사용 (힘의 비약: STR +10, 2초)")
    elixir = ItemDefinition(name="힘의 비약", type="CONSUMABLE", description="", symbol="!", color="red", 
                            required_level=1, attack=0, defense=0, hp_effect=0, mp_effect=0, str_bonus=10, duration=2)
    
    buff_source = f"ITEM_{elixir.name}"
    new_mod = StatModifierComponent(str_mod=elixir.str_bonus, duration=elixir.duration, source=buff_source)
    new_mod.expires_at = time.time() + elixir.duration
    player.add_component(new_mod)
    engine._recalculate_stats()
    
    print(f"버프 적용 후 스탯: STR={stats.str} (예상: {base_str + 3 + 10})")
    if stats.str != base_str + 13:
        raise ValueError(f"STR 불일치: {stats.str} != {base_str + 13}")

    # 4. 시간 경과에 따른 버프 만료 테스트
    print("\n[테스트 3] 버프 만료 대기 (3초)")
    time.sleep(3)
    
    # TimeSystem.process() 호출 시뮬레이션
    from dungeon.systems import TimeSystem
    time_sys = None
    for s in world._systems:
        if isinstance(s, TimeSystem):
            time_sys = s
            break
    
    if time_sys:
        time_sys.process()
        print(f"만료 후 스탯: STR={stats.str} (예상: {base_str + 3})")
        if stats.str != base_str + 3:
            raise ValueError(f"만료 후 STR 불일치: {stats.str} != {base_str + 3}")
    else:
        print("TimeSystem을 찾을 수 없습니다.")

    print("\n--- 모든 검증 완료! ---")

if __name__ == "__main__":
    try:
        test_stat_modifiers()
    except Exception as e:
        print(f"검증 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
