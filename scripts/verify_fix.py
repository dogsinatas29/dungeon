import json
import os
import sys

# Mocking parts of the system for testing
class Component: pass

from dungeon.components import StatsComponent

def test_stats_serialization():
    print("--- StatsComponent Serialization Test ---")
    
    # Create a stats object with some flags
    stats = StatsComponent(max_hp=100, current_hp=100, attack=10, defense=5, element="FIRE")
    print(f"Initial flags: {stats.flags} (type: {type(stats.flags)})")
    
    # Convert to dict
    data = stats.to_dict()
    print(f"Serialized data flags: {data.get('flags')} (type: {type(data.get('flags'))})")
    
    if not isinstance(data.get('flags'), list):
        print("❌ FAILED: flags should be a list in to_dict")
        return False
        
    # JSON dump/load simulation
    json_str = json.dumps(data)
    loaded_data = json.loads(json_str)
    
    # Restore from dict
    restored_stats = StatsComponent(**loaded_data)
    print(f"Restored flags: {restored_stats.flags} (type: {type(restored_stats.flags)})")
    
    if not isinstance(restored_stats.flags, set):
        print("❌ FAILED: restored flags should be a set")
        return False
        
    if restored_stats.flags != {"FIRE"}:
        print(f"❌ FAILED: restored flags mismatch. Expected {{'FIRE'}}, got {restored_stats.flags}")
        return False

    print("✅ SUCCESS: StatsComponent correctly serialized and restored.")
    return True

if __name__ == "__main__":
    # Ensure dungeon package is in path
    sys.path.append(os.getcwd())
    if test_stats_serialization():
        sys.exit(0)
    else:
        sys.exit(1)
