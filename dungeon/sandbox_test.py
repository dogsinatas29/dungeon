import sys
import os

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dungeon import engine
from dungeon.components import InventoryComponent, AIComponent, PositionComponent, MonsterComponent
from dungeon.data_manager import load_item_definitions
from dungeon.Start import main_menu

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

        # 2. Force Stationary on initial monsters
        for ent in self.world.get_entities_with_components({MonsterComponent, AIComponent}):
            ai = ent.get_component(AIComponent)
            ai.behavior = AIComponent.STATIONARY # 0

    def _spawn_monster_at(self, x, y, monster_def=None, pool=None):
        monster = super()._spawn_monster_at(x, y, monster_def, pool)
        if monster:
             ai = monster.get_component(AIComponent)
             if ai:
                 ai.behavior = AIComponent.STATIONARY
        return monster

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
