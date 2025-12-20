# main.py - 게임의 시작점

from dungeon.ui import ConsoleUI
from dungeon.engine import Engine
import sys

def main():
    try:
        ui = ConsoleUI()
        while True:
            choice = ui.show_main_menu()

            if choice == 0: # 새 게임
                player_name = ui.get_player_name()
                if not player_name: # 이름 없이 Enter를 누르면 기본 이름 사용
                    player_name = "Hero"
                engine = Engine(ui, player_name)
                engine.run()
            elif choice == 1: # 이어하기 (TODO: 추후 구현)
                ui.add_message("이어하기 기능은 아직 구현되지 않았습니다. 새 게임을 시작합니다.")
                player_name = ui.get_player_name()
                if not player_name: # 이름 없이 Enter를 누르면 기본 이름 사용
                    player_name = "Hero"
                engine = Engine(ui, player_name)
                engine.run()
            elif choice == 2: # 게임 종료
                print("\n[시스템] 게임을 종료합니다.")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n[시스템] 게임 종료 요청.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[시스템] 치명적인 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()