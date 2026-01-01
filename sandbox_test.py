import sys
import os

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon import engine
from dungeon.components import InventoryComponent, AIComponent, PositionComponent, MonsterComponent, StatsComponent, LevelComponent
from dungeon.data_manager import load_item_definitions
from Start import main_menu

class SandboxEngine(engine.Engine):
    def _initialize_world(self, game_data=None, preserve_player=None, spawn_at="START"):
        # Call original initialization
        super()._initialize_world(game_data, preserve_player, spawn_at)
        
        # 1. Inject Skill Books (30 of each), Remove others
        player = self.world.get_player_entity()
        if player:
            inv = player.get_component(InventoryComponent)
            # Reload to allow script modifications to take effect
            item_defs = load_item_definitions()
            
            # Remove any existing Skillbooks
            keys_to_remove = [k for k, v in inv.items.items() if getattr(v['item'], 'type', '') == 'SKILLBOOK']
            for k in keys_to_remove:
                del inv.items[k]

            target_books = ["레이지 스킬북", "수리 스킬북", "함정 해제 스킬북", "충전 스킬북"]
            count = 0
            for name in target_books:
                # Find Def (item_defs is dict of ID -> Def)
                book_def = next((d for d in item_defs.values() if d.name == name), None)
                if book_def:
                    inv.items[name] = {
                        'item': book_def,
                        'qty': 30,
                        'prefix': None, 'suffix': None
                    }
                    count += 1
            print(f"[Sandbox] Cleared existing books. Injected {count} types of class books (30 each).")

            # Add Oils and Sacrifices for test
            oil_items = [
                "날카로움의 오일", "정밀함의 오일", "단단함의 오일", "안정성의 오일", 
                "요새의 오일", "숙련의 오일", "대장장이의 오일"
            ]
            sac_items = [
                "녹슨 고철", "악마의 피", "천사의 깃털", "룬석", "어둠의 수정"
            ]
            
            for item_name in oil_items + sac_items:
                item_def = self.item_defs.get(item_name)
                if item_def:
                    inv.items[item_name] = {'item': item_def, 'qty': 99}
            print(f"[Sandbox] Injected 99 of each Oil and Sacrifice for advanced shrine testing.")

            # Add high-end items with affixes (Unique-style)
            # Weapon
            weapon = self._create_item_with_affix("큰 도끼", "King's", "of Haste")
            if weapon:
                inv.items[weapon.name] = {'item': weapon, 'qty': 1}
            # Armor
            armor = self._create_item_with_affix("고딕 플레이트", "Obsidian", "of the Zodiac")
            if armor:
                inv.items[armor.name] = {'item': armor, 'qty': 1}
            # Accessory
            acc = self._create_item_with_affix("목걸이", "Glorious", "of the Heavens")
            if acc:
                inv.items[acc.name] = {'item': acc, 'qty': 1}
            
            # Add Identify Scrolls
            id_scroll = self.item_defs.get("확인 스크롤")
            if id_scroll:
                inv.items["확인 스크롤"] = {'item': id_scroll, 'qty': 99}
                
            print(f"[Sandbox] Injected 99 Identify Scrolls and set items to unidentified for testing.")

        # 2. Force Stationary on initial monsters
        for ent in self.world.get_entities_with_components({MonsterComponent, AIComponent}):
            ai = ent.get_component(AIComponent)
            ai.behavior = AIComponent.STATIONARY # 0

        # 3. Add Shrine next to Shop (Shop is at x1+1, y1+1)
        starting_room = self.dungeon_map.rooms[0] if self.dungeon_map and self.dungeon_map.rooms else None
        if starting_room:
            self._spawn_shrine(starting_room.x1 + 2, starting_room.y1 + 1)
            print(f"[Sandbox] Spawned Shrine next to Shop at ({starting_room.x1 + 2}, {starting_room.y1 + 1})")

        # 4. Set Player to Max Level and Stats
        if player:
            stats = player.get_component(StatsComponent)
            level = player.get_component(LevelComponent)
            if level:
                level.level = 99
                level.exp_to_next = 999999
            
            if stats:
                stats.base_str = 100
                stats.base_dex = 100
                stats.base_vit = 100
                stats.base_mag = 100
                
                # Recalculate and fill
                self._recalculate_stats()
                stats.current_hp = stats.max_hp
                stats.current_mp = stats.max_mp

        # 5. Spawn The Butcher near the player
        if starting_room:
            bx, by = starting_room.x1 + 3, starting_room.y1 + 3
            self._spawn_boss(bx, by, "BUTCHER")
            print(f"[Sandbox] Spawned The Butcher at ({bx}, {by})")
        
        # 6. Ensure player equipment is at full durability
        if player:
            inv = player.get_component(InventoryComponent)
            if inv:
                # Ensure all equipped items are at full durability
                for slot, item in inv.equipped.items():
                    if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                        item.current_durability = item.max_durability
            print("[Sandbox] Set Player to Level 99 and Max Stats for stable testing.")

    def _spawn_monster_at(self, x, y, monster_def=None, pool=None):
        monster = super()._spawn_monster_at(x, y, monster_def, pool)
        if monster:
             ai = monster.get_component(AIComponent)
             if ai:
                 ai.behavior = AIComponent.STATIONARY
        return monster

    def handle_sandbox_input(self, action: str) -> bool:
        """샌드박스 전용 명령어 처리"""
        from dungeon.events import MapTransitionEvent, MessageEvent
        
        # 'F': 10층 건너뛰기
        if action == 'F':
            target = min(99, self.current_level + 10)
            self.world.event_manager.push(MessageEvent(f"[Sandbox] {target}층으로 건너뜁니다!"))
            self.world.event_manager.push(MapTransitionEvent(target_level=target))
            return True
        
        # 'B': 10층 뒤로가기
        if action == 'B':
            target = max(1, self.current_level - 10)
            self.world.event_manager.push(MessageEvent(f"[Sandbox] {target}층으로 돌아갑니다!"))
            self.world.event_manager.push(MapTransitionEvent(target_level=target))
            return True
            
        # 'G': 골드 1000 추가
        if action == 'G':
            player = self.world.get_player_entity()
            if player:
                stats = player.get_component(StatsComponent)
                if stats:
                    stats.gold += 1000
                    self.world.event_manager.push(MessageEvent("[Sandbox] 골드 1000을 획득했습니다!"))
            return True
        
        # 'L': 레벨 설정 (입력 받기)
        if action == 'L':
            import termios, tty
            fd = sys.stdin.fileno()
            # 터미널 설정 일시 복구
            termios.tcsetattr(fd, termios.TCSADRAIN, self.old_settings)
            sys.stdout.write("\033[?25h")  # 커서 보이기
            sys.stdout.write("\n[Set Level] Enter level (1-99): ")
            sys.stdout.flush()
            
            try:
                line = sys.stdin.readline().strip()
                if line.isdigit():
                    target_level = max(1, min(99, int(line)))
                    player = self.world.get_player_entity()
                    if player:
                        level_comp = player.get_component(LevelComponent)
                        if level_comp:
                            old_level = level_comp.level
                            level_comp.level = target_level
                            level_comp.exp = 0
                            level_comp.exp_to_next = int(100 * (1.5 ** (level_comp.level - 1)))
                            
                            # Grant stat points based on level difference
                            if target_level > old_level:
                                points_gained = (target_level - old_level) * 5
                                level_comp.stat_points += points_gained
                                self.world.event_manager.push(MessageEvent(
                                    f"[Sandbox] 레벨 {target_level}로 설정! 스탯 포인트 +{points_gained}"
                                ))
                            else:
                                self.world.event_manager.push(MessageEvent(
                                    f"[Sandbox] 레벨 {target_level}로 설정!"
                                ))
                            
                            self._recalculate_stats()
                else:
                    self.world.event_manager.push(MessageEvent("[Sandbox] 올바른 레벨을 입력해주세요."))
            except Exception:
                pass
            
            # cbreak 모드 재진입
            tty.setcbreak(fd)
            sys.stdout.write("\033[?25l")  # 커서 숨기기
            sys.stdout.flush()
            self._render()
            return True

        # 'J': 특정 층으로 이동 (입력 받기)
        if action == 'J':
            import termios, tty
            fd = sys.stdin.fileno()
            # 1. 터미널 설정 일시 복구 (입력 받기 위해)
            termios.tcsetattr(fd, termios.TCSADRAIN, self.old_settings)
            sys.stdout.write("\033[?25h") # 커서 보이기
            sys.stdout.write("\n[Jump Floor] Go to floor (1-99): ")
            sys.stdout.flush()
            
            try:
                line = sys.stdin.readline().strip()
                if line.isdigit():
                    target = max(1, min(99, int(line)))
                    self.world.event_manager.push(MessageEvent(f"[Sandbox] {target}층으로 차원 이동합니다!"))
                    self.world.event_manager.push(MapTransitionEvent(target_level=target))
                else:
                    self.world.event_manager.push(MessageEvent("[Sandbox] 올바른 층 번호를 입력해주세요."))
            except Exception:
                pass
            
            # 2. cbreak 모드 재진입
            tty.setcbreak(fd)
            sys.stdout.write("\033[?25l") # 커서 다시 숨기기
            sys.stdout.flush()
            self._render() # 화면 갱신
            return True

        return False

# Monkey Patch the Engine class used by Start.py
engine.Engine = SandboxEngine

if __name__ == "__main__":
    print("=== DUNGEON SANDBOX MODE ===")
    print("Features:")
    print(" 1. All Character Skill Books (30x) in inventory.")
    print(" 2. Monsters are fixed (Stationary).")
    print("Usage: Start a new game and select a class to test.")
    print("============================")
    try:
        main_menu()
    except KeyboardInterrupt:
        pass
