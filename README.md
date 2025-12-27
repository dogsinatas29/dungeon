# Python ECS Real-Time Dungeon Crawler

A classic terminal-based roguelike dungeon crawler built with Python, featuring an Entity Component System (ECS) architecture and inspired by Diablo 1.

**Note**: This project was developed using Gemini as a pair programming assistant.

## Features

### Core Gameplay
- **Real-time combat system** with turn-based mechanics
- **Procedurally generated dungeons** with multiple floor types
- **Permadeath** - true roguelike experience
- **Character progression** with dynamic job system based on skill usage

### Combat & Skills
- **18 Diablo 1 Spells** across 4 tiers:
  - Tier 1: Firebolt, Charged Bolt, Healing, Holy Bolt, Inferno
  - Tier 2: Fireball, Lightning, Stone Curse, Flash, Phasing
  - Tier 3: Chain Lightning, Flame Wave, Guardian, Teleport
  - Tier 4: Mana Shield, Nova, Golem, Apocalypse
- **Skill Book System** with exponential leveling (3^n progression: 1→3→9→27 books)
- **Elemental System** with rock-paper-scissors mechanics (Water > Fire > Wood > Earth > Water)
- **Special Damage Types**: Poison, Undead bonus (maces), Ranged attacks

### Items & Equipment
- **99+ Base Items**:
  - 30 Weapons (Swords, Axes, Maces, Bows, Staves)
  - 26 Armor pieces (Helms, Shields, Body Armor)
  - 2 Accessories (Rings, Amulets)
  - 18 Skill Books
  - Various consumables and scrolls

### Diablo 1-Inspired Systems
- **Magic Item System** with prefix/suffix combinations:
  - 22 Prefixes (Sharp, Obsidian, Dragon's, etc.)
  - 17 Suffixes (of the Zodiac, of the Heavens, etc.)
  - 11 Accessory-only prefixes (Jade, Ruby, Sapphire, etc.)
  - 2 Accessory-only suffixes (of the Moon, of Regeneration)
- **Durability System** - equipment degrades in combat
- **Enhancement System**:
  - Oil enhancements for weapons/armor
  - Shrine enhancement (0 to +10) with success/failure mechanics
- **Shrine System** - appears every 2 floors with restoration or enhancement options

### Advanced Features
- **Stamina System** - depletes with movement and skill usage
- **Resource Management** - food, potions, and inventory limits
- **Shop System** - buy/sell items and repair equipment
- **Sound System** - audio feedback for actions
- **Double-buffered UI** - smooth terminal rendering with ANSI colors
- **Save/Load System** - persistent game state

## Requirements

```bash
sudo apt install python3-gi python3-gi-cairo python3-dbus gir1.2-gtk-3.0
pip install readchar
```

## How to Play

```bash
python3 dungeon/Start.py
```

### Controls
- **Arrow Keys**: Move character
- **Space**: Toggle attack mode
- **I**: Open inventory
- **Q**: Quit game
- **1-9**: Use quick slots

### Game Mechanics

#### Stats
- **HP**: Health points
- **MP**: Mana points for skills
- **Stamina**: Depletes with movement (20 tiles = 1 stamina) and skill usage
- **STR/DEX/MAG/VIT**: Core attributes affecting combat and equipment

#### Combat
- **Attack Types**: Melee, Ranged, Projectile, Splash
- **Defense**: Shields and armor reduce damage
- **Elemental Advantages**: Deal bonus damage with correct element matchups
- **Durability Loss**: 10% chance per hit for attacker's weapon and defender's armor

#### Progression
- **Dynamic Jobs**: Your job changes based on your highest-level skill
- **Skill Leveling**: Read multiple skill books to level up (1→3→9→27 books)
- **Item Enhancement**: Use oils or shrines to upgrade equipment
- **Permanent Stats**: Elixirs provide permanent stat increases

## Project Structure

```
dungeon/
├── Start.py              # Main entry point
├── dungeon/
│   ├── game.py          # Main game loop
│   ├── engine.py        # Game engine and state management
│   ├── ecs.py           # Entity Component System
│   ├── components.py    # ECS components
│   ├── systems.py       # ECS systems (combat, movement, etc.)
│   ├── player.py        # Player class
│   ├── dungeon_map.py   # Map generation
│   ├── ui.py            # Terminal UI rendering
│   ├── data_manager.py  # Data loading
│   └── sound_system.py  # Audio system
├── data/
│   ├── items.csv        # Item definitions
│   ├── skills.csv       # Skill definitions
│   ├── prefixes.json    # Magic item prefixes
│   ├── suffixes.json    # Magic item suffixes
│   └── monster_data.txt # Monster definitions
└── game_data/           # Save files (JSON)
```

## Development

### Coding Style
- Follow PEP 8 standards
- Use `black` for automatic formatting

### Key Design Patterns
- **ECS Architecture**: Separation of data (Components) and logic (Systems)
- **Event-Driven**: Event manager for game events
- **Data-Driven**: Items, skills, and monsters defined in CSV/JSON files

## License

This project is open source and available for educational purposes.

---

**Developed with Gemini AI as a pair programming assistant**