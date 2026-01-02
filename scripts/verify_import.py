
import sys
import os
# Append python_project/dungeon so we can import dungeon.components
sys.path.append('/home/dogsinatas/python_project/dungeon')
print(f"Sys Path: {sys.path}")
try:
    import dungeon
    print(f"Dungeon package: {dungeon}")
    print(f"Dungeon path: {dungeon.__path__}")
    from dungeon import components
    print(f"Components module: {components}")
    from dungeon.components import DoorComponent
    print("Import Successful")
except ImportError as e:
    print(f"Import Failed: {e}")
except Exception as e:
    print(f"Error: {e}")
