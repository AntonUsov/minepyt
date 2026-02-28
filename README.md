# MinePyt

A Python implementation of the [mineflayer](https://github.com/PrismarineJS/mineflayer) Minecraft bot library for **Minecraft 1.21.4** (protocol 769).

## Features

- **Full Protocol Support** - Connect and stay online indefinitely with keep-alive handling
- **Entity Tracking** - Track players, mobs, and objects with full metadata
- **World/Block Tracking** - Parse chunks, track block changes, find blocks
- **Health System** - Track health, hunger, and death/respawn
- **Inventory Management** - 1.21.4 item components, click modes, shift-click
- **Crafting** - Recipe matching and crafting execution
- **Digging** - Block breaking with proper timing calculations
- **Entity Interactions** - Attack, interact, and use-on-entity methods
- **NBT Parsing** - Full NBT tag support (12 types)
- **Item Components** - 1.21.4 component system (enchantments, attributes, etc.)

## Installation

```bash
pip install mcproto
```

Or install from source:

```bash
git clone https://github.com/YOUR_USERNAME/minepyt.git
cd minepyt
pip install -e .
```

## Quick Start

```python
import asyncio
from minepyt.protocol import create_bot

async def main():
    def on_spawn():
        print(f"Bot spawned at {bot.position}")
    
    def on_chat(username, message):
        print(f"[{username}] {message}")
    
    bot = await create_bot({
        "host": "localhost",
        "port": 25565,
        "username": "MyBot",
        "on_spawn": on_spawn,
        "on_chat": on_chat,
    })
    
    # Stay connected for 60 seconds
    await bot.stay_alive(duration=60.0)
    
    # Disconnect
    await bot.disconnect()

asyncio.run(main())
```

## Examples

### Find and Attack Nearest Hostile Mob

```python
# Find nearest hostile within 16 blocks
hostile = bot.nearest_hostile(max_distance=16.0)
if hostile:
    await bot.attack(hostile)
```

### Dig a Block

```python
# Dig block at position
success = await bot.dig(100, 64, 200)
if success:
    print("Block broken!")
```

### Find Blocks

```python
# Find nearest stone block
stone_block = bot.findBlock("minecraft:stone", max_distance=32)
if stone_block:
    print(f"Found stone at {stone_block.position}")
```

### Inventory Operations

```python
# List inventory
for item in bot.inventory:
    if not item.is_empty:
        print(f"Slot {item.slot}: {item.name} x{item.count}")

# Click slot (pickup)
await bot.send_container_click(container_id=0, slot=0, button=0, mode=0)
```

## API Reference

### Bot Methods

| Method | Description |
|--------|-------------|
| `dig(x, y, z)` | Dig a block |
| `stop_digging()` | Cancel current dig |
| `attack(entity)` | Attack an entity |
| `interact(entity)` | Right-click interact |
| `use_on(entity, x, y, z)` | Interact at position on entity |
| `look_at(x, y, z)` | Look at coordinates |
| `block_at(x, y, z)` | Get block at position |
| `findBlock(name)` | Find nearest block by name |
| `findBlocks(name)` | Find all matching blocks |
| `nearest_entity()` | Get nearest entity |
| `nearest_player()` | Get nearest player |
| `nearest_hostile()` | Get nearest hostile mob |

### Events

| Event | Description |
|-------|-------------|
| `on_spawn` | Bot spawned in world |
| `on_chat` | Chat message received |
| `on_entity_spawn` | Entity spawned |
| `on_entity_gone` | Entity removed |
| `on_entity_hurt` | Entity took damage |
| `on_entity_death` | Entity died |
| `on_health` | Health/hunger changed |
| `on_dig_complete` | Block broken |
| `on_dig_abort` | Dig cancelled |

## Project Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed progress tracking.

| Module | Progress |
|--------|----------|
| Protocol | 100% |
| Game State | 100% |
| Health | 100% |
| Entities | 100% |
| Blocks/World | 100% |
| Digging | 100% |
| Inventory | 60% |
| Crafting | 70% |
| NBT | 100% |
| Components | 90% |
| Movement | 0% |
| Chat | 10% |

**Overall: ~68%**

## Testing

Run tests against a local Minecraft 1.21.4 server:

```bash
# Run all tests
python tests/test_1_protocol_core.py
python tests/test_2_game_plugin.py
# ... etc
```

## Requirements

- Python 3.10+
- mcproto library
- Minecraft 1.21.4 server (for testing)

## License

MIT License - see [LICENSE](LICENSE) file.

## Credits

- Based on [mineflayer](https://github.com/PrismarineJS/mineflayer) by PrismarineJS
- Protocol implementation uses [mcproto](https://github.com/py-mine/mcproto)
