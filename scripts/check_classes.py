
import sys
import os

sys.path.append(os.path.abspath("/home/dogsinatas/python_project/dungeon"))

from dungeon.data_manager import load_class_definitions

def verify():
    print("Loading class definitions...")
    defs = load_class_definitions()
    print(f"Loaded {len(defs)} classes.")
    for k, v in defs.items():
        print(f"Key: '{k}', ID: '{v.class_id}', Name: '{v.name}'")

    if "WARRIOR" in defs:
        print("PASS: WARRIOR class found.")
    else:
        print("FAIL: WARRIOR class NOT found.")
        
if __name__ == "__main__":
    verify()
