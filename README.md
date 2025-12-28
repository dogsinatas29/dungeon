# Dungeon Crawl

**English** | [한국어](README.ko.md)

Diablo like real time rogue for terminal

![Gameplay Screenshot](screenshots/gameplay_test.png)

### [Watch Gameplay Video](https://youtu.be/o8M7aBofsvQ)

**Note**: This project was developed using Gemini as a pair programming assistant.

**Status**: Currently undergoing balance testing.

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

## Recent Updates (2025-12-29)

### 1. Advanced Shrine & Enhancement System
- **Oil System**: Permanent stat boosts and utility (Sharpness, Accuracy, Hardening, Stability, Fortitude, Skill, Repair).
- **Sacrifice System**: Risk mitigation and special upgrades (Blood for success rate, Feather for protection, Rune for reroll, Crystal for rarity upgrade).
- **Destruction Mechanic**: Shrines are now powerful, single-use objects that are destroyed after one interaction.

### 2. Hack & Slash Overhaul
- **Monster Nests**: Increased spawn density and grouping for a more intense combat experience.
- **Loot Explosion**: Defeating monsters now triggers satisfying item drops and visual feedback.

### 3. Inventory & UI 2.0
- **UI Expansion**: Re-engineered inventory popup (60x18 -> 66x24) to fit dual-affix item stats.
- **Enhanced Detailed View**: Separated stat displays into multiple lines for clarity.
- **Durability Warning**: Visual indicators when equipment is nearing breakage.

## TODO List

### High Priority
- [/] **Diablo 1 Boss System**:
  - [x] **Boss Summoning Mechanic** (Desperate Call at 50% HP)
  - [x] **Aggressive Boss AI** (All bosses use CHASE mode)
  - [x] **Final Boss: Diablo** (Epic encounter on Floor 99)
  - [ ] Other Unique Bosses (Butcher, Leoric, etc.)
  - [ ] Boss dialogue/bark system ("Ah... Fresh Meat!")
  - [ ] Guaranteed unique item drops per boss
  - [x] Hand-crafted boss maps (Reached goal for Floor 99)
- [x] **Staff Combat System** - dual-mode weapon mechanics:
  - [x] Physical bash attack (melee, uses durability, STR-based damage)
  - [x] Magic Charge mode (consumes staff charges instead of MP for Sorcerers)
  - [x] Random spell assignment to staves
  - [ ] 'S' key to activate spell mode + directional casting (currently integrated into quickslots)
- [ ] **Special Spell Effects** (12 spells need implementation):
  - [ ] Holy Bolt - bonus damage vs undead
  - [ ] Inferno - persistent flame wall
  - [ ] Stone Curse - petrification effect
  - [ ] Phasing - random teleport
  - [ ] Chain Lightning - chain attack
  - [ ] Flame Wave - fire wave attack
  - [ ] Guardian - summon turret
  - [ ] Teleport - directional teleport
  - [ ] Mana Shield - absorb damage with mana
  - [ ] Nova - omnidirectional attack
  - [ ] Golem - summon golem
  - [ ] Apocalypse - screen-wide attack

### Medium Priority
- [ ] **Item Drop System Overhaul**:
  - [ ] Drop chance formula (15-25% for normal, 100% for boss)
  - [ ] Rarity determination (Normal 85%, Magic 14.5%, Unique 0.5%)
  - [ ] Monster level-based item restrictions
  - [ ] Magic affix rolling (40% prefix, 40% suffix, 20% both)
  - [ ] Magic Find (MF) system for accessories
  - [ ] Boss-specific loot tables
- [ ] **Language Selection Menu** - choose Korean/English at startup
- [ ] **Dynamic Job System** - auto-change job based on highest skill level
- [ ] **Player Action Cooldown** - enforce cooldown in input handling
- [ ] **Balance Adjustments** - tune difficulty for real-time gameplay
- [ ] **UI Improvements**:
  - [ ] Cooldown indicators
  - [ ] Real-time HP/MP bar animations
  - [ ] Monster action prediction

### Low Priority
- [ ] **Boss Special Patterns** - unique boss behaviors
- [ ] **More Character Classes** - expand beyond 4 classes
- [ ] **Multiplayer Support** - co-op gameplay

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
├── test_classes.py       # Class balance test environment
├── sandbox_test.py       # High-end systems & sandbox environment
├── sounds/               # Audio effect files (.wav)
├── data/                 # Game data files
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
**참고**: 이 프로젝트는 Gemini를 페어 프로그래밍 도우미로 사용하여 개발되었습니다.

**상태**: 현재 밸런스 테스트 진행 중...

### Unimplemented Skills (Known Issues)
Currently, definitions exist in `skills.csv`, but the following skills lack full system logic implementation:

1. **REPAIR** (Warrior Trait): Operates as HP Recovery; equipment durability repair logic missing.
2. **DISARM** (Rogue Trait): Operates as HP Recovery; trap removal logic missing.
3. **RECHARGE** (Sorcerer Trait): Operates as HP Recovery; staff charge restoration logic missing.
4. **MANA_SHIELD** (Sorcerer): Mana damage absorption formula missing.
5. **PHASING**: Random teleportation logic missing.
6. **TELEPORT**: Targeted teleportation logic missing.
7. **GOLEM**: Summon AI and entity creation logic missing.
8. **GUARDIAN** (Hydra): Turret summoning and attack logic missing.
9. **INFERNO**: Continuous damage projectile logic missing.
10. **FLASH**: Area of Effect damage logic missing (visual only).
11. **NOVA**: Expanding wave damage logic missing.
12. **CHAIN_LIGHTNING**: Chain hit logic missing.
13. **FLAME_WAVE**: Moving wall projectile logic missing.
14. **APOCALYPSE**: Screen-wide attack logic missing.