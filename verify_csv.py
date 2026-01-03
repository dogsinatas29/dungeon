
import sys
import os

# Add project root to path
sys.path.append('/home/dogsinatas/python_project')

from dungeon.data_manager import load_item_definitions

def verify():
    print("Loading item definitions...")
    defs = load_item_definitions()
    
    target = "단궁"
    if target in defs:
        item = defs[target]
        print(f"Item: {item.name}")
        print(f"Attack Range: {item.attack_range}")
        
        if item.attack_range == 5:
            print("SUCCESS: Range is 5 as expected.")
        else:
            print(f"FAILURE: Range is {item.attack_range}, expected 5.")
    else:
        print(f"FAILURE: Item {target} not found in definitions.")

if __name__ == "__main__":
    verify()
