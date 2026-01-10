
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dungeon import config
config.LANGUAGE = "en"

from dungeon.localization import L
from dungeon.engine import Engine

print(f"Current Language: {config.LANGUAGE}")
print(f"Test Localization (Item): {L('Items')}")
print(f"Test Localization (Level): {L('Level')}")
print(f"Test Localization (Game Over): {L('GAME OVER')}")

# Check Engine initialization message (if any)
# engine = Engine("Tester")
# print(f"Engine Message: ...")
