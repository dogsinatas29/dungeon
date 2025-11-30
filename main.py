# main.py - 게임 실행 진입점

import sys
import os

# 상대 경로 임포트 문제 해결을 위해 현재 디렉토리를 경로에 추가
# 이는 IDE/환경에 따라 필요할 수 있습니다.
if os.path.dirname(__file__) not in sys.path:
    sys.path.append(os.path.dirname(__file__))

# 필요한 모듈 임포트
from dungeon.engine import run_game # Engine 클래스 대신 run_game 함수 임포트
from dungeon.ui import ConsoleUI
from dungeon.data_manager import load_item_definitions

def main():
    """게임 초기화 및 메인 루프 실행"""
    
    # 1. UI 초기화
    ui = ConsoleUI()

    # 2. 아이템 정의 로드
    ITEM_DEFINITIONS = load_item_definitions(ui) # ui_instance를 전달
    
    # 3. 메인 메뉴 표시 및 플레이어 이름 입력
    choice = ui.show_main_menu()

    try:
        if choice == 0: # 새 게임
            player_name = ui.get_player_name()
            run_game(player_name=player_name, item_definitions=ITEM_DEFINITIONS, ui_instance=ui)
        elif choice == 1: # 이어하기
            # TODO: 이어하기 로직 구현 (현재는 새 게임과 동일하게 처리)
            player_name = ui.get_player_name()
            run_game(player_name=player_name, item_definitions=ITEM_DEFINITIONS, ui_instance=ui)
        elif choice == 2: # 게임 종료
            return

    except KeyboardInterrupt:
        print("\n[시스템] 게임 종료 요청.")
        sys.exit(0)
    except Exception as e:
        # 게임 루프 중 예상치 못한 오류 발생 시
        ui.show_game_over_screen(f"게임 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
if __name__ == "__main__":
    main()