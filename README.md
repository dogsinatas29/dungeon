![Dungeon Crawl Title Screen](assets/title_screen.png)

**English** | [한국어](README.ko.md)

Diablo-like real-time roguelike engine for terminal

![Gameplay Screenshot](dungeon/screenshots/gameplay_test.png)

### [Watch Gameplay Video](https://youtu.be/o8M7aBofsvQ)

**Note**: This project was developed using Gemini as a pair programming assistant.

**Status**: Currently undergoing balance testing.

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dogsinatas29/dungeon.git
   cd dungeon
   ```

2. **Install dependencies**
   ```bash
   pip install readchar
   ```

3. **Run the game**
   ```bash
   python3 Start.py
   ```

## Requirements
- **Audio**: `ffmpeg` or `aplay` (ALSA) is required for sound effects and BGM.
    - Ubuntu/Debian: `sudo apt install ffmpeg` or `sudo apt install alsa-utils`

## Features

### Core Gameplay
- **Real-time combat system** with turn-based mechanics
- **Procedurally generated dungeons** with multiple floor types
- **Permadeath** - true roguelike experience
- **Character progression** with dynamic job system based on skill usage
- **Job Specializations**: Unique weapon bonuses for each class (Rogue bows, Barbarian 2H, Sorcerer staves)

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
- **Advanced Shrine System**: Multi-step enhancement using Oils and Sacrifices. One-time use and destruction mechanics.
- **Hack & Slash Experience**: Increased monster density (Monster Nests) and loot explosions.
- **Improved Identification**: 70% chance for unidentified magic drops, Identify Scrolls, and prefix/suffix support for accessories.
- **UI Enhancements**: 
  - Expanded inventory detail view (66x24) for complex item stats.
  - Low durability warning UI.
  - Standardized popup dimensions.
- **Stamina System** - depletes with movement and skill usage
- **Resource Management** - food, potions, and inventory limits
- **Shop System** - buy/sell items and repair equipment
- **Sound System** - audio feedback for actions
- **Double-buffered UI** - smooth terminal rendering with ANSI colors
- **Save/Load System** - persistent game state

## Recent Updates (2026-01-02)

### 1. Boss Room Redesign & Interaction System
- **Boss Room Layout**: Three-room structure (Antechamber, Lever Room, Boss Room)
- **Lever Mechanism**: Lever opens locked boss door and triggers trap (20 damage)
- **InteractionSystem**: New ECS system for handling switch/lever interactions
- **Components**: Added `DoorComponent`, `BlockMapComponent`, `SwitchComponent` with door linking

### 2. Trap System Refactoring
- **Modular Design**: Extracted `TrapSystem` to `trap_manager.py` module
- **CSV Data Management**: All trap data now in `data/traps.csv`
- **TrapDefinition Class**: Structured trap data with validation
- **8 Trap Types**: Arrow, Spike, Lightning, Gas, Nova, Fire, Ice, Teleport

### 3. Level-Based Trap System
- **MinLevel Requirement**: Traps spawn based on floor level (Lv1-50)
- **Guaranteed Placement**: Fixed trap count per floor (default: 5)
- **Level Filtering**: Only appropriate traps spawn on each floor
  - Floor 1: Arrow traps only
  - Floor 10: Arrow, Spike, Lightning traps
  - Floor 50: All trap types available
- **Weighted Selection**: Higher-level traps are rarer (lower weight)
- **Multiple Locations**: Traps spawn in rooms (70%) and corridors (30%)

### 4. Sandbox Testing Environment
- **DISARM Skill Books**: 30 copies added to test character
- **Trap Showcase**: All 8 trap types placed in starting room
- **Visible Traps**: Test mode shows all traps for easy testing


## Recent Updates (2025-12-29)

### 1. Advanced Shrine & Enhancement System
- **Oil System**: Permanent stat boosts and utility (Sharpness, Accuracy, Hardening, Stability, Fortitude, Skill, Repair).
- **Sacrifice System**: Risk mitigation and special upgrades (Blood for success rate, Feather for protection, Rune for reroll, Crystal for rarity upgrade).
- **Destruction Mechanic**: Shrines are now powerful, single-use objects that are destroyed after one interaction.

### 2. Skill System Overhaul (Phase 1-3)
- **Phase 1 (Utility)**: Implemented actual logic for `REPAIR`, `DISARM`, `RECHARGE`, and `MANA_SHIELD`.
- **Phase 2 (Movement)**: Implemented `PHASING` (random teleport) and `TELEPORT` (targeted movement).
- **Phase 3 (AoE Magic)**: Implemented `FLASH`, `NOVA`, `CHAIN_LIGHTNING`, and `FLAME_WAVE` with advanced hit detection and chain logic.

### 3. Engine & UI Improvements
- **Large Map Support**: Fixed camera rendering bugs on 99-floor sized maps.
- **Stability**: Resolved multiple `UnboundLocalError` issues in combat and rendering systems.
- **Visuals**: Added particle effects for different dungeon themes (Caves, Hell).
- **Sandbox**: Added floor jumping (F/B/J) and gold cheat (G) commands for testing.

### 4. Skill System Completion (Phase 4 & Final) (2026-01-01)
- **Summoning System**: Implemented `SummonComponent` and faction-based AI for friendly minions.
- **Guardian**: Summonable turret that automatically attacks nearby enemies.
- **Golem**: Mobile melee minion that fights alongside the player.
- **Apocalypse**: Screen-wide ultimate spell dealing massive damage to all enemies.
- **Utility & Crowd Control**:
    - **Holy Bolt**: Bonus damage against Undead enemies.
    - **Inferno**: Creates burning ground zones that deal damage over time.
    - **Stone Curse**: Petrifies enemies, rendering them unable to act.

### 5. Identification & Inventory System Improvements (2026-01-01)
- **Interactive Identification**: Identify scrolls now trigger a dedicated overlay popup.
- **Overlay UI**: Selection menu appears on top of the game screen using ANSI box characters.
- **Filtered Navigation**: Fixed bugs where Shield and Accessory items were excluded from the equipment tab.
- **Navigation Keys**: Added `W/S` key support for inventory and menu navigation.

### 6. Stability & Bug Fixes (2026-01-01)
- **Combat Fixes**: Resolved "Invisible monster combat" by implementing proper detection (10 tiles) and chase (15 tiles) ranges.
- **Experience Fix**: Fixed a bug where experience wasn't granted due to early corpse checks.
- **Ghost Events**: Implemented status effect cleanup on death to prevent "ghost" messages and screen shaking.
- **Safe Zones**: Enhanced monster spawning to ensure a 20-tile safe zone around the player's starting position.
- **Sandbox Features**: Added interactive Level Setting (`L`) and Floor Jumping (`J`) with terminal input handling.

### 7. Stability & Bug Fixes (2026-01-03)
- **Start Room Safety**: Guaranteed safe start by preventing traps in the starting room.
- **Shop Fixes**: Fixed empty shop inventory bug and balanced starting shop items (Level <= 5).
- **Map Persistence**: Implemented save/load logic for DungeonMap to prevent regeneration on load.
- **Friendly Fire**: Fixed monsters attacking each other by adding faction checks.
- **Sound**: Optimized sound effect duration for better audio experience.
## TODO List

### High Priority
- [x] **Diablo 1 Boss System**:
    - [x] **Boss Summoning Mechanic** (Desperate Call at 50% HP)
    - [x] **Aggressive Boss AI** (All bosses use CHASE mode)
    - [x] **Final Boss: Diablo** (Epic encounter on Floor 99)
    - [x] Other Unique Bosses (Butcher, Leoric, Diablo)
    - [x] Boss dialogue/bark system ("Ah... Fresh Meat!")
    - [ ] Guaranteed unique item drops per boss
    - [x] Hand-crafted boss maps (Reached goal for Floor 99)
- [x] **Skill System Implementation (Phase 1-3)**:
    - [x] Utility skills (Repair, Disarm, Recharge)
    - [x] Survival skills (Mana Shield, Phasing, Teleport)
    - [x] Combat magic (Flash, Nova, Chain Lightning, Flame Wave)
- [x] **Skill System Implementation (Phase 4)**:
    - [x] Guardian (Hydra) - summon turret
    - [x] Golem - summon golem
    - [x] Apocalypse - screen-wide attack

### Medium Priority
- [x] **Item Drop System Overhaul** (Loot tables, Affixes, MF)
- [x] **Language Selection Menu** - choose Korean/English at startup
    - ✅ **Fully localized UI and system messages** (English/Korean)
    - ✅ **Complete message translation** for all game events, combat, bosses, and traps
    - Select language upon game launch
- [ ] **Player Action Cooldown** - enforce cooldown in input handling
- [ ] **Balance Adjustments** - tune difficulty for real-time gameplay
- [ ] **UI Improvements**:
  - [ ] Cooldown indicators (Gauge next to skill names)
  - [ ] Real-time HP/MP bar animations
  - [ ] Monster action prediction

### Low Priority
- [ ] **Boss Special Patterns** - unique boss behaviors (In Progress)
- [x] **More Character Classes** - 4 classes implemented (Warrior, Rogue, Sorcerer, Barbarian)
- [x] **Localization System Completion** - 100% of user-facing strings externalized

### Localization & Multi-Language System

The game features a fully integrated localization system that supports multiple languages. Currently, **English** and **Korean** are fully supported.

### Architecture
- **Central Translation Map**: All user-facing strings are managed in `dungeon/localization.py` within the `TRANSLATIONS` dictionary.
- **`_()` Function**: The code uses a standard `_("Source Text")` function (with an alias `L()`) to look up translations based on the `config.LANGUAGE` setting.
- **Dynamic Messages**: Supports dynamic content using Python's `.format()` method:
  `_("{} has been poisoned!").format(entity_name)`

### Language Pack Guide (Adding/Modifying Languages)

To add a new language (e.g., Japanese `ja`) or modify:

1. **Update `dungeon/localization.py`**:
   - Add a new `"ja"` key to the `TRANSLATIONS` dictionary.
   - Copy key-value pairs from `"ko"` (Korean) or English, then replace values with translated text.
   - *Example*:
     ```python
     "ja": {
         "Hello": "こんにちは",
         "Firebolt": "ファイアボルト",
         # ...
     }
     ```

2. **Translate Data Files (CSVs)**:
   - Create a subfolder `dungeon/data/ja/`.
   - Copy `boss_dialogues.csv` (and any other localized CSVs) there.
   - Translate the text columns while keeping the IDs intact.

3. **Register Language in Startup**:
   - Update `ConsoleUI.show_language_selection()` in `dungeon/ui.py` to add "Japanese".
   - Update `Start.py` to handle the new selection index and set `config.LANGUAGE = "ja"`.

## Keyboard Shortcuts

### General Controls
- **Movement**: `Arrow Keys` or `W`, `A`, `S`, `D`
- **Wait / Pass Turn**: `.`, `X`, `Z`, or `5`
- **Interact / Pick Up / Use Stairs**: `ENTER`
- **Attack Mode (Toggle)**: `SPACE` (Once active, press a direction key to attack)
- **Quick Slots**: `1` through `0` (Use bound skills or items)
- **Character Sheet**: `C` (View stats and allocate bonus points)
- **Inventory**: `I` (Open/Close inventory)
- **Quit Game**: `Q`

### Inventory & Menus
- **Navigate**: `Arrow Keys` or `W`, `S`
- **Switch Tabs**: `Left` / `Right` Arrow keys (Inside Inventory)
- **Use / Equip**: `E` or `ENTER`
- **Drop Item**: `X`
- **Close Menu**: `ESC`, `Q`, or the menu's toggle key (`I`, `C`)

### Character Sheet (Stat Point Allocation)
- **Select Stat**: `UP` / `DOWN` Arrow keys or `W`, `S`
- **Allocate Point**: `RIGHT` Arrow key, `D`, `+`, `=`, or `ENTER`
- **Close**: `C`, `ESC`, or `Q`

## Requirements
```bash
sudo apt install python3-gi python3-gi-cairo python3-dbus gir1.2-gtk-3.0
pip install readchar
```

## How to Play
```bash
python3 dungeon/Start.py
```

## Testing

### Test Environment (test_classes.py)
For comprehensive testing of all game features, use the test environment script:
```bash
python3 test_classes.py
```

**Features**:
- Pre-configured characters at level 10
- 10,000 gold for shop testing
- All weapons, armor, and accessories
- All skillbooks (Lv1-3) for every spell
- 99 of each consumable item
- Enhanced stats (+10 to all attributes)

**Available Test Classes**:
1. **Warrior** - High HP (180), STR 40, melee specialist
2. **Rogue** - High DEX (40), critical hits, trap expert
3. **Sorcerer** - High MAG (40), spell damage specialist
4. **Barbarian** - Highest HP (240), STR 50, berserker

**What to Test**:
- Character progression
- Shop interactions

### Sandbox Environment (sandbox_test.py)
For high-end game logic testing (Shrines, Bosses, Affixed items):
```bash
python3 sandbox_test.py
```

**Features**:
- Player level 99 with maxed stats (STR/MAG/DEX/VIT 100)
- Injected with Advanced Shrine materials (99 Oils & Sacrifices)
- Injected with unique-style affixed items for verification
- Immediate access to Shrines and Boss encounters

**Debug Keys (Sandbox Only)**:
- `F`: Jump **Forward** 10 floors
- `B`: Jump **Backward** 10 floors
- `J`: **Jump** to a specific floor (Input required in terminal)
- `G`: Get **1,000 Gold** immediately
- `L`: Set **Level** (Input required in terminal)
- `Z`: Summon **Butcher** (Boss)
- `W`: Get **Warrior Set** (Level 21 + Full Plate/Great Axe)

### Balance Simulator (balance_simulator.py)
For automated testing of item drop rates, boss balance, and general stability without UI rendering:
```bash
python3 -m dungeon.balance_simulator
```
**Features**:
- **Headless Mode**: Runs simulation without graphic rendering for speed.
- **Drop Rate Testing**: Verifies item drop probabilities, rarity distribution, and skill book rates.
- **Boss Combat Simulation**: Tests various class builds against Bosses (Butcher, Leoric, etc.) to evaluate win rates and turn counts.
- **Automated Logging**: Tracks key metrics like simulated turns, pot usage, and critical events.

### Game Mechanics

#### Stats
- **HP**: Health points
- **MP**: Mana points for skills
- **Stamina**: Depletes with movement (20 tiles = 1 stamina) and skill usage
- **STR/DEX/MAG/VIT**: Core attributes affecting combat and equipment

#### Job Specializations
- **Warrior**: High defense and health; masters all weapon types equally.
- **Rogue**: **Bow Expert**. +3 Range bonus with bows and arrows always **Piercing** through enemies.
- **Barbarian**: **Two-Handed Master**. +3 Attack and +1 Range bonus when using two-handed weapons.
- **Sorcerer**: **Magic Staff Recharge**. Can use spells using staff **Charges** instead of MP when a staff is equipped.

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
├── test_classes.py       # Class balance test environment
├── sandbox_test.py       # High-end systems & sandbox environment
├── dungeon/              # Core Game Package
│   ├── engine.py        # Game engine and state management
│   ├── systems.py       # ECS systems (combat, movement, etc.)
│   ├── components.py    # ECS components
│   ├── ecs.py           # Entity Component System core
│   ├── ui.py            # Terminal UI rendering
│   ├── map.py           # Map generation
│   ├── player.py        # Player entity logic
│   ├── monster.py       # Monster entity logic
│   ├── items.py         # Item definitions and logic
│   ├── inventory.py     # Inventory management
│   ├── skills.py        # Skill system
│   ├── trap_manager.py  # Trap system (refactored)
│   ├── shrine_methods.py # Shrine interactions
│   ├── events.py        # Event definition and handling
│   ├── constants.py     # Game constants
│   ├── config.py        # Configuration settings
│   ├── data_manager.py  # Data loading utility
│   └── sound_system.py  # Audio system
├── data/                 # Game Data Files
│   ├── items.csv        # Item definitions
│   ├── skills.csv       # Skill definitions
│   ├── monsters.csv     # Monster definitions
│   ├── Boss.csv         # Boss stats
│   ├── classes.csv      # Character class definitions
│   ├── maps.csv         # Map generation parameters
│   ├── traps.csv        # Trap definitions
│   ├── prefixes.json    # Magic item prefixes
│   └── suffixes.json    # Magic item suffixes
├── game_data/           # Save files (JSON)
└── sounds/              # Audio effect files (.wav)
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
**참고**: 이 프로젝트는 Gemini를 페어 프로그래밍 도우미로 사용하여 개발되었습니다.

**상태**: 현재 밸런스 테스트 진행 중...

### Unimplemented Skills (Known Issues)
All original Diablo 1 spells are now fully implemented with system logic!
