import os
import re

dungeon_dir = "/home/dogsinatas/python_project/dungeon"
files = [f for f in os.listdir(dungeon_dir) if f.endswith(".py")]

modules = [f[:-3] for f in files]

for filename in files:
    if filename == "__init__.py":
        continue
    
    filepath = os.path.join(dungeon_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace 'from module import ...' with 'from .module import ...'
    for module in modules:
        # Match 'from module import' with any leading whitespace
        pattern = rf"^(\s*)from {module} import"
        content = re.sub(pattern, rf"\1from .{module} import", content, flags=re.MULTILINE)
        
        # Match 'import module' with any leading whitespace (for whole module imports)
        # Be careful not to match 'import os' if os is not in modules
        pattern = rf"^(\s*)import {module}$"
        content = re.sub(pattern, rf"\1from . import {module}", content, flags=re.MULTILINE)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Imports fixed (v2).")
