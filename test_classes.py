#!/usr/bin/env python3
"""
각 직업별 테스트 환경 스크립트
모든 장비와 아이템을 갖춘 상태로 게임을 시작합니다.
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dungeon import engine
from dungeon.ui import ConsoleUI
from dungeon.data_manager import load_class_definitions

def create_test_character(class_id, player_name="TestPlayer"):
    """테스트용 캐릭터 생성 (모든 장비 및 아이템 포함)"""
    
    class_defs = load_class_definitions()
    selected_class = None
    
    # load_class_definitions returns a dictionary with class_id as keys
    if isinstance(class_defs, dict):
        selected_class = class_defs.get(class_id)
    elif isinstance(class_defs, list):
        # Fallback for list format
        for cls in class_defs:
            cls_id = cls.class_id if hasattr(cls, 'class_id') else cls.get('class_id') if isinstance(cls, dict) else cls
            if cls_id == class_id:
                selected_class = cls
                break
    
    if not selected_class:
        print(f"Error: Class {class_id} not found")
        if isinstance(class_defs, dict):
            print(f"Available classes: {list(class_defs.keys())}")
        else:
            print(f"Available classes: {[cls.class_id if hasattr(cls, 'class_id') else cls.get('class_id', cls) if isinstance(cls, dict) else cls for cls in class_defs]}")
        return None
    
    # Extract class attributes
    if hasattr(selected_class, 'hp'):
        # ClassDefinition object
        hp = selected_class.hp
        mp = selected_class.mp
        str_val = selected_class.str
        mag = selected_class.mag
        dex = selected_class.dex
        vit = selected_class.vit
        starting_skills = list(selected_class.starting_skills) if hasattr(selected_class, 'starting_skills') else []
    elif isinstance(selected_class, dict):
        # Dictionary format
        hp = selected_class.get('hp', 100)
        mp = selected_class.get('mp', 50)
        str_val = selected_class.get('str', 10)
        mag = selected_class.get('mag', 10)
        dex = selected_class.get('dex', 10)
        vit = selected_class.get('vit', 10)
        starting_skills = selected_class.get('starting_skills', [])
    else:
        print(f"Error: Unknown class format: {type(selected_class)}")
        print(f"Class data: {selected_class}")
        if hasattr(selected_class, '__dict__'):
            print(f"Attributes: {selected_class.__dict__}")
        return None
    
    # 초기 게임 상태 생성
    initial_state = {
        "player_specific_data": {
            "name": player_name,
            "level": 10,  # 레벨 10으로 시작
            "exp": 0,
            "hp": hp * 2,
            "max_hp": hp * 2,
            "mp": mp * 2,
            "max_mp": mp * 2,
            "gold": 10000,  # 골드 10000
            "str": str_val + 10,
            "mag": mag + 10,
            "dex": dex + 10,
            "vit": vit + 10,
        },
        "inventory": {
            "items": {
                # 소모품
                "체력 물약": {"qty": 99},
                "마력 물약": {"qty": 99},
                "순간 이동 스크롤": {"qty": 20},
                "화염 스크롤": {"qty": 20},
                
                # 무기 (각 직업별)
                "낡은 검": {"qty": 1},
                "강철 검": {"qty": 1},
                "양손 대검": {"qty": 1},
                "활": {"qty": 1},
                "소서러의 지팡이": {"qty": 1},
                
                # 방어구
                "가죽 갑옷": {"qty": 1},
                "체인 메일": {"qty": 1},
                "플레이트 아머": {"qty": 1},
                "방패": {"qty": 1},
                
                # 액세서리
                "수호의 목걸이": {"qty": 1},
                "힘의 반지": {"qty": 1},
            },
            "equipped": {},
            "skills": starting_skills,
        },
        "current_floor": 1,
        "dungeon_maps": {},
        "selected_class": class_id
    }
    
    return initial_state

def test_warrior():
    """전사 테스트"""
    print("=" * 60)
    print("전사 (WARRIOR) 테스트 환경")
    print("=" * 60)
    
    ui = ConsoleUI()
    game_state = create_test_character("WARRIOR", "TestWarrior")
    
    if game_state:
        game_engine = engine.Engine("TestWarrior", game_state)
        result = game_engine.run()
        print(f"Game ended with result: {result}")

def test_rogue():
    """도적 테스트"""
    print("=" * 60)
    print("도적 (ROGUE) 테스트 환경")
    print("=" * 60)
    
    ui = ConsoleUI()
    game_state = create_test_character("ROGUE", "TestRogue")
    
    if game_state:
        game_engine = engine.Engine("TestRogue", game_state)
        result = game_engine.run()
        print(f"Game ended with result: {result}")

def test_sorcerer():
    """마법사 테스트"""
    print("=" * 60)
    print("마법사 (SORCERER) 테스트 환경")
    print("=" * 60)
    
    ui = ConsoleUI()
    game_state = create_test_character("SORCERER", "TestSorcerer")
    
    if game_state:
        game_engine = engine.Engine("TestSorcerer", game_state)
        result = game_engine.run()
        print(f"Game ended with result: {result}")

def test_barbarian():
    """바바리안 테스트"""
    print("=" * 60)
    print("바바리안 (BARBARIAN) 테스트 환경")
    print("=" * 60)
    
    ui = ConsoleUI()
    game_state = create_test_character("BARBARIAN", "TestBarbarian")
    
    if game_state:
        game_engine = engine.Engine("TestBarbarian", game_state)
        result = game_engine.run()
        print(f"Game ended with result: {result}")

def main():
    """메인 테스트 메뉴"""
    print("\n" + "=" * 60)
    print("던전 크롤러 - 직업별 테스트 환경")
    print("=" * 60)
    print("\n테스트할 직업을 선택하세요:")
    print("1. 전사 (WARRIOR)")
    print("2. 도적 (ROGUE)")
    print("3. 마법사 (SORCERER)")
    print("4. 바바리안 (BARBARIAN)")
    print("5. 종료")
    
    choice = input("\n선택 (1-5): ").strip()
    
    if choice == "1":
        test_warrior()
    elif choice == "2":
        test_rogue()
    elif choice == "3":
        test_sorcerer()
    elif choice == "4":
        test_barbarian()
    elif choice == "5":
        print("테스트를 종료합니다.")
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
