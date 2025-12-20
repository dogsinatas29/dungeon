import sys
import os

# Add python_project to path so we can import dungeon
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from dungeon.engine import Engine
    print("Import successful.")
    
    print("Initializing Engine...")
    eng = Engine("Tester")
    print("Engine Initialized.")
    
    print(f"Renderer type: {type(eng.renderer)}")
    print(f"World entities: {len(eng.world._entities)}")
    
    # Check if StatsComponent is known (by checking imports in checking code, or just ensuring no crash)
    from dungeon.components import StatsComponent
    print("StatsComponent imported successfully.")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
