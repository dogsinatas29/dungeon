import sys
import os

# Add python_project to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from dungeon.engine import Engine
    print("Initializing Engine...")
    eng = Engine("Tester")
    print("Engine Initialized.")
    
    print(f"Renderer size: {eng.renderer.width}x{eng.renderer.height}")
    
    print("Checking monsters and AI...")
    from dungeon.components import MonsterComponent, AIComponent
    monsters = eng.world.get_entities_with_components({MonsterComponent, AIComponent})
    print(f"Found {len(monsters)} monsters with AI.")
    for m in monsters:
        comp = m.get_component(MonsterComponent)
        ai = m.get_component(AIComponent)
        print(f" - Monster: {comp.type_name}, AI Behavior: {ai.behavior}")

    print("Attempting to render frame (PLAYING)...")
    eng._render()
    print("Render PLAYING successful.")
    
    print("Switching to INVENTORY state...")
    from dungeon.engine import GameState
    eng.state = GameState.INVENTORY
    
    print("Attempting to render frame (INVENTORY)...")
    eng._render()
    print("Render INVENTORY successful.")
    
    # Check if Title exists in buffer (simple check)
    found_title = False
    for row in eng.renderer.buffer:
        line = "".join(row)
        if "INVENTORY" in line:
            found_title = True
            break
            
    if found_title:
        print("Inventory Title found in buffer.")
    else:
        print("WARNING: Inventory Title NOT found in buffer.")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
