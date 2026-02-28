# minepyt Project Status

**Last Updated:** 2026-03-01

## Overview

**minepyt** - Python port of [mineflayer](https://github.com/PrismarineJS/mineflayer) for Minecraft 1.21.4 (protocol 769)

### Current Progress: ~60-65%

```
Protocol      ████████████████████ 100%
Game State    ████████████████████ 100%
Health        ████████████████████ 100%
Entities      ██████████████████░░  90%
Blocks/World  ████████████████████ 100%
Digging       ████████████████████ 100%
Inventory     ████████████░░░░░░░░  60%
Crafting      ██████████████░░░░░░  70%
NBT           ████████████████████ 100%
Components    ██████████████████░░  90%
Movement      ░░░░░░░░░░░░░░░░░░░░   0%
Chat          ██░░░░░░░░░░░░░░░░░░  10%
Combat        ░░░░░░░░░░░░░░░░░░░░   0%
```

---

## Files Structure

```
minepyt/
├── minepyt/
│   ├── protocol.py      ~3040 lines  # Main protocol + all handlers
│   ├── entities.py       ~710 lines  # Entity system
│   ├── digging.py        ~480 lines  # Digging helpers
│   ├── components.py     ~510 lines  # 1.21.4 item components
│   ├── recipes.py        ~550 lines  # Recipe system
│   ├── nbt.py            ~580 lines  # NBT parser (12 types)
│   ├── chunk_utils.py    ~700 lines  # Chunk parsing
│   ├── block_registry.py ~350 lines  # Block registry
│   └── lib/plugins/      ~400 lines  # Plugins
│
├── tests/
│   ├── test_01_protocol_core.py
│   ├── test_02_game_plugin.py
│   ├── test_03_health_plugin.py
│   ├── test_04_entities_plugin.py
│   ├── test_05_blocks_plugin.py
│   ├── test_06_integration.py
│   ├── test_07_digging.py
│   ├── test_08_inventory.py
│   ├── test_09_click_modes.py
│   ├── test_10_nbt_components_recipes.py
│   ├── test_11_entities.py
│   ├── test_12_blocks.py
│   └── test_13_digging.py
│
└── PROJECT_STATUS.md                   # This file
```

**Total: ~7,800 lines of code**

---

## Tests Status: 13/13 ✅

| # | Test | Status | Description |
|---|------|--------|-------------|
| 1 | Protocol Core | ✅ | Connection, handshake, keep-alive |
| 2 | Game Plugin | ✅ | Game mode, dimension, time |
| 3 | Health Plugin | ✅ | Health, food, death, respawn |
| 4 | Entities Plugin | ✅ | Player tracking, entity dict |
| 5 | Blocks Plugin | ✅ | Chunks, block_at |
| 6 | Integration | ✅ | 2+ min online stability |
| 7 | Digging | ✅ | dig(), stop_digging() |
| 8 | Inventory | ✅ | Slots, containers |
| 9 | Click Modes | ✅ | Click, shift-click, drop |
| 10 | NBT/Components/Recipes | ✅ | NBT parsing, components |
| 11 | Full Entity System | ✅ | Spawn, tracking, removal |
| 12 | Full Block System | ✅ | findBlock, helpers |
| 13 | Full Digging System | ✅ | dig_time, can_harvest |

---

## Implemented Features

### Protocol (100%)
- [x] Handshake
- [x] Login (offline mode)
- [x] Configuration state (1.20.5+)
- [x] Play state
- [x] Keep-Alive (infinite connection)
- [x] Compression

### Game State (100%)
- [x] Game mode tracking
- [x] Dimension tracking
- [x] Time tracking
- [x] Respawn handling

### Health (100%)
- [x] Health tracking
- [x] Food tracking
- [x] Saturation tracking
- [x] Death detection
- [x] Auto-respawn

### Entities (90%)
- [x] Player tracking (Player Info Update)
- [x] Entity spawn (0x01, 0x02, 0x05, 0x5A)
- [x] Entity movement (0x1F, 0x20, 0x21, 0x3F)
- [x] Entity removal (0x3E)
- [x] Entity equipment (0x48)
- [x] Entity metadata (0x4D)
- [x] Entity attributes (0x56)
- [x] Entity damage (0x47)
- [x] Entity passengers (0x5B)
- [x] EntityManager class
- [x] nearest_entity(), nearest_player(), nearest_hostile()
- [ ] Mob AI detection

### Blocks/World (100%)
- [x] Chunk loading (0x28)
- [x] Chunk unloading (0x25)
- [x] block_at()
- [x] Block updates (0x09)
- [x] Block action (0x08)
- [x] Block entity data (0x07)
- [x] Multi block change (0x10)
- [x] findBlock()
- [x] blocksInRadius()
- [x] blockAtFace()
- [x] canDigBlock()
- [x] canSeeBlock()

### Digging (100%)
- [x] dig()
- [x] stop_digging()
- [x] Break animation tracking
- [x] dig_time() calculation
- [x] can_harvest() checking
- [x] best_tool() finding
- [x] tool_tier() / tool_type()
- [x] Block hardness (150+ blocks)
- [x] Tool speed multipliers

### Inventory (60%)
- [x] Slot parsing
- [x] Container tracking
- [x] Click modes (left, right, shift)
- [x] Drop items
- [x] Held item slot
- [ ] Drag mode
- [ ] Creative inventory
- [ ] Full container sync

### Crafting (70%)
- [x] Recipe registry
- [x] Shaped recipes
- [x] Shapeless recipes
- [x] Smelting recipes
- [x] Stonecutting recipes
- [x] Recipe matching
- [ ] Auto recipe selection
- [ ] Crafting output prediction

### NBT (100%)
- [x] All 12 tag types
- [x] NBT reading
- [x] NBT writing

### Components (90%)
- [x] Enchantments
- [x] Attribute modifiers
- [x] Custom names
- [x] Lore
- [x] Durability
- [x] Unbreakable
- [ ] Full 1.21.4 component list

### Movement (0%)
- [ ] Pathfinder
- [ ] Physics
- [ ] Collision detection
- [ ] Jump/climb

### Chat (10%)
- [x] System chat receive
- [ ] Chat send (message signing)
- [ ] Whisper
- [ ] Commands

### Combat (0%)
- [ ] attack()
- [ ] PvP logic
- [ ] Mob targeting

---

## Packet Coverage

### Clientbound (Server → Client)

| Packet | ID | Status |
|--------|-----|--------|
| Keep Alive | 0x27 | ✅ |
| Login (Join Game) | 0x2C | ✅ |
| Sync Player Position | 0x42 | ✅ |
| Disconnect | 0x1A | ✅ |
| Respawn | 0x3D | ✅ |
| Game State Change | 0x4A | ✅ |
| Update Time | 0x4E | ✅ |
| Update Health | 0x52 | ✅ |
| Player Info Update | 0x40 | ✅ |
| Player Info Remove | 0x3F | ✅ |
| System Chat | 0x73 | ✅ |
| Level Chunk With Light | 0x28 | ✅ |
| Forget Level Chunk | 0x25 | ✅ |
| Block Update | 0x09 | ✅ |
| Block Break Animation | 0x06 | ✅ |
| Block Action | 0x08 | ✅ |
| Block Entity Data | 0x07 | ✅ |
| Multi Block Change | 0x10 | ✅ |
| Spawn Entity | 0x01 | ✅ |
| Spawn Experience Orb | 0x02 | ✅ |
| Spawn Mob | 0x05 | ✅ |
| Spawn Painting | 0x0A | ✅ |
| Spawn Player | 0x5A | ✅ |
| Entity Animation | 0x03 | ✅ |
| Entity Position | 0x1F | ✅ |
| Entity Pos+Rot | 0x20 | ✅ |
| Entity Rotation | 0x21 | ✅ |
| Entity Velocity | 0x4C | ✅ |
| Entity Damage | 0x47 | ✅ |
| Head Look | 0x3D | ✅ |
| Remove Entities | 0x3E | ✅ |
| Teleport Entity | 0x3F | ✅ |
| Entity Equipment | 0x48 | ✅ |
| Set Entity Metadata | 0x4D | ✅ |
| Entity Link | 0x4B | ✅ |
| Entity Attributes | 0x56 | ✅ |
| Set Passengers | 0x5B | ✅ |
| Entity Event | 0x19 | ✅ |
| Set Container Content | 0x14 | ✅ |
| Set Container Slot | 0x15 | ✅ |
| Open Screen | 0x3B | ✅ |
| Declare Recipes | 0x42 | ✅ |

### Serverbound (Client → Server)

| Packet | ID | Status |
|--------|-----|--------|
| Keep Alive | 0x0F | ✅ |
| Player Position | 0x1B | ✅ |
| Player Position & Rotation | 0x1D | ✅ |
| Player Digging | 0x1E | ✅ |
| Set Held Item | 0x28 | ✅ |
| Click Container | 0x0F | ✅ |
| Close Container | 0x12 | ✅ |
| Client Information | 0x00 | ✅ |
| Acknowledge Block Change | 0x04 | ✅ |

---

## Comparison with mineflayer

| Feature | mineflayer | minepyt |
|---------|------------|---------|
| Protocol version | 1.8-1.21 | 1.21.4 only |
| Language | JavaScript | Python |
| Dependencies | 10+ | 1 (mcproto) |
| Lines of code | ~15,000+ | ~7,800 |
| Plugins | 40+ | 4 |
| Tests | ? | 13 |
| Async/await | Callbacks | Native async |
| Type hints | No | Yes |

---

## Roadmap

### Priority 1 (High Impact)
- [ ] **Movement/Pathfinder** - Navigate to positions
- [ ] **Chat send** - Fix message signing for 1.19+
- [ ] **Entity interaction** - attack(), useOn()

### Priority 2 (Medium Impact)
- [ ] **Containers** - Full chest/furnace control
- [ ] **Experience** - XP tracking
- [ ] **Creative inventory** - Creative mode support

### Priority 3 (Nice to Have)
- [ ] **Auto-eat** - Automatic food consumption
- [ ] **Collector** - Item pickup
- [ ] **Villager trading**
- [ ] **Boss bar tracking**
- [ ] **Scoreboard**

---

## How to Run Tests

```bash
# Run all tests
python tests/test_01_protocol_core.py
python tests/test_02_game_plugin.py
# ... etc

# Or run specific test
python tests/test_13_digging.py
```

Requirements:
- Minecraft server 1.21.4 running on localhost:25565
- Offline mode enabled

---

## Changelog

### 2026-03-01
- Added full digging system (digging.py)
- Added block helper methods (findBlock, blocksInRadius, etc.)
- Added block packets (0x07, 0x08, 0x10)
- Added entity packets (0x05 Spawn Mob, 0x4C, 0x3D, 0x47, 0x5B)
- Tests 11-13 added and passing
- Progress: 60-65%

### Previous sessions
- Core protocol implementation
- NBT parser (12 types)
- Component system (1.21.4)
- Recipe system
- Entity system
- Block system
- Digging basics
- Inventory basics

---

## Dependencies

```
mcproto>=0.1.0
```

---

## License

MIT (same as mineflayer)
