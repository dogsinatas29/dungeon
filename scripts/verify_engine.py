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
    
    # Verify Map Generation
    from dungeon.components import MapComponent, PositionComponent, MonsterComponent
    
    map_entities = eng.world.get_entities_with_components({MapComponent})
    if map_entities:
        m_comp = map_entities[0].get_component(MapComponent)
        print(f"Map Generated: {m_comp.width}x{m_comp.height}")
    else:
        print("FAIL: No MapComponent found.")

    # Verify Player Position
    # Note: Player doesn't have a specific PlayerComponent in engine.py yet, just ID=1 usually or first created
    # But engine.py stores player entity creation referencing world.create_entity()
    # We can search for Entity with Position + Render('@')
    from dungeon.components import RenderComponent
    players = [e for e in eng.world.get_entities_with_components({PositionComponent, RenderComponent}) 
               if e.get_component(RenderComponent).char == '@']
    
    if players:
        p_pos = players[0].get_component(PositionComponent)
        print(f"Player Position: ({p_pos.x}, {p_pos.y})")
        if p_pos.x == 0 and p_pos.y == 0:
            print("WARNING: Player at (0,0), might be uninitialized.")
    else:
        print("FAIL: No Player found.")

    # Verify Monsters
    monsters = [e for e in eng.world.get_entities_with_components({MonsterComponent})]
    print(f"Monsters Spawned: {len(monsters)}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
