# main.py - 게임 실행 진입점

import sys
import os

# 상대 경로 임포트 문제 해결을 위해 현재 디렉토리를 경로에 추가
# 이는 IDE/환경에 따라 필요할 수 있습니다.
if os.path.dirname(__file__) not in sys.path:
    sys.path.append(os.path.dirname(__file__))

# 필요한 모듈 임포트
from dungeon.engine import Engine
from dungeon.ui import ConsoleUI

def main():
    """게임 초기화 및 메인 루프 실행"""
    
    # 1. UI 초기화
    ui = ConsoleUI()
    
    # 2. 메인 메뉴 표시 및 플레이어 이름 입력
    player_name = ui.show_main_menu()
    
    # 3. 게임 엔진 초기화
    try:
        engine = Engine(ui_instance=ui, player_name=player_name)
    except Exception as e:
        ui.show_game_over_screen(f"게임 초기화 실패: {e}")
        return

    # 4. 게임 루프 실행
    try:
        engine.run_game_loop()
    except Exception as e:
        # 게임 루프 중 예상치 못한 오류 발생 시
        ui.show_game_over_screen(f"게임 실행 중 오류 발생: {e}")
        
if __name__ == "__main__":
    main()