# MinePyt TODO - Prioritized for 100% Feature Parity

## Priority Legend
- 🔴 CRITICAL - Blocks core functionality, must fix immediately
- � HIGH - Major feature gaps, important for most users
- � MEDIUM - Important but can be deferred
- � LOW - Nice to have, not urgent
- ⬜ OPTIONAL - Future enhancements

---

## 🔴 CRITICAL Priority (Must Fix First)

### C1: Pathfinding Implementation ⭐⭐⭐
**Impact:** Cannot navigate efficiently, cannot plan routes. Most important missing feature.
**Estimated Effort:** 2-3 weeks
**Dependencies:** Movement, World

**Tasks:**
- [ ] Implement A* pathfinding algorithm
- [ ] Add `pathfinding.py` module with:
  - [ ] `AStar` class for pathfinding
  - [ ] Heuristic functions (Euclidean, Manhattan)
  - [ ] Path smoothing
  [ ] Support for walkable blocks
- [ ] Jump and drop detection
- [ ] Navigate around obstacles
- [ ] `goto()` method using pathfinding
- [ ] `follow_path()` method
- [ ] Integrate with movement system
- [ ] Tests for pathfinding

**Acceptance Criteria:**
- Bot can navigate to any position within 64 blocks
- Bot can follow entities using paths
- Bot can avoid obstacles

---

### C2: Message Signing (for 1.19+ Servers) 🔥
**Impact:** Chat blocked on all online servers. Critical for multiplayer.
**Estimated Effort:** 5-7 days
**Dependencies:** Chat, crypto library

**Tasks:**
- [ ] Research Minecraft 1.19 message signing specification
- [ ] Implement `message_signing.py` module
- [ ] Add `sign_chat()` method
- [ ] Add UUID-based session tracking
- [ ] Implement queue for unsigned messages (server will reject)
- [ ] Fallback for offline mode (no signing)
- [ ] Tests for signed chat

**Acceptance Criteria:**
- Bot can send signed messages on 1.19+ servers
- Bot can receive chat messages
- Offline mode works without errors

---

### C3: Window Management System 🎨
**Impact:** Limited container interaction, crashes on complex containers
**Estimated Effort:** 1 week
**Dependencies:** Inventory, protocol

**Tasks:**
- [ ] Create `window_manager.py` module
- [ ] `Window` class with state tracking
- [ ] Support multiple concurrent windows
- [ ] Proper cursor tracking
- [ ] Click sequence support
- [ ] Shift-click integration
- [ ] Tests for window management

**Acceptance:**
- Can manage multiple containers without conflicts
- Proper cursor tracking in all windows
- Shift-click works correctly
- No crashes on container close

---

## � HIGH Priority (Important Features)

### H1: Entity Interaction API
**Impact:** Users must use low-level API, inconvenient
**Estimated Effort:** 2-3 days
**Dependencies:** Protocol, Entities

**Tasks:**
- [ ] Expose `attack(entity)` method (not packet only)
- [ ] Expose `interact(entity)` method
- [ ] Expose `useOn(entity, x, y, z)` method
- [ ] Add `look_at(entity)` method
- [ ] Add proper distance checks
- [ ] Document methods with examples
- [ ] Tests for entity interaction

**Acceptance Criteria:**
- Clean API: `bot.attack(zombie)` works
- Proper error handling (too far, no line of sight)
- Examples in documentation

---

### H2: Villager Trading System
**Impact:** Missing major gameplay feature
**Estimated Effort:** 2 weeks
**Dependencies:** Protocol, Inventory, NBT

**Tasks:**
- [ ] Open villager trading window (0x73)
- [ ] Parse trade data (0x72)
- ] `VillagerWindow` class
- [ ] Trade execution (0x75)
- [ ] Trade discovery API
- [ ] Emerald counting and pricing
- [ ] Trade history tracking
- [ ] Tests for villager trading

**Acceptance Criteria:**
- Can open villager window
- Can view available trades
- Can execute trades
- Can trade with emeralds

---

### H3: Combat Target Selection
**Impact:** Bot attacks random entities, inefficient
**Estimated Effort:** 3-5 days
**Dependencies:** Entities, Combat

**Tasks:**
- [ ] `bot.nearestEntity(filter_func)` - flexible filtering
- [ ] `bot.nearestMob(mob_type)` - filter by type
- [ ] Priority system (attackable > neutral > passive)
- [ ] Target selection AI (weakest → strongest)
- [ ] Hitbox-based selection
- [ ] Damage history tracking
- [ ] Combat state machine (idle → engage → retreat)
- [ ] Tests for combat targeting

**Acceptance Criteria:**
- Can select specific entity types
- Smart target selection (weakest first)
- Combat state machine works
- Tracks damage dealt/received

---

### H4: AI System Integration
**Impact:** Design exists but not usable
**Estimated Effort:** 1 week integration + 1 week testing
**Dependencies:** Sensors, Movement, Actors

**Tasks:**
- [ ] Connect AI to protocol (not just create_bot)
- [ ] Implement real sensor methods (not TODO stubs)
- [ ] Connect MovementBrain to protocol
- [ ] Connect ActionExecutor to protocol
- [ ] Connect ActorSystem to protocol
- [ ] Integrate with existing protocol events
- [ ] Test AI system end-to-end
- [ ] Examples: smart_bot.py working

**Acceptance Criteria:**
- `SmartBot` class works and is usable
- Bot can follow player AND avoid threats simultaneously
- Tasks can be assigned and executed

---

### H5: Advanced Inventory Features
**Impact:** Limited inventory management
**Estimated Effort:** 2 weeks
**Dependencies:** Inventory, Window management

**Tasks:**
- [ ] Anvil interface (0x25)
- [ ] `AnvilWindow` class
- [ ] Combine items
- [ ] Rename items
- [ ] Repair items (exp levels)
- [ ] Enchanting table interface (0x26)
- `EnchantingWindow` class`
- [ ] Put lapis, enchant
- [ ] Experience cost calculation
- [ ] Tests for anvil and enchanting

**Acceptance:**
- Can open anvil
- Can combine items
- Can enchant with lapis
- Can repair items with XP
- XP costs are correct

---

### H6: Vehicle Controls
**Impact:** Basic mount works, no control
**Estimated Effort:** 1 week
**Dependencies:** Entities, Protocol

**Tasks:**
- [ ] Boat control (steer left/right)
- [ ] Horse control (jump, forward, stop)
- [ ] Vehicle state tracking
- [ ] Dismount from vehicle
- [ ] Tests for vehicle controls

**Acceptance:**
- Boat can be steered left/right
- Horse can be controlled (jump, forward, stop)
- State tracking works

---

## � MEDIUM Priority (Important but Can Defer)

### M1: Entity Bounding Box
**Impact:** Collision detection, combat accuracy
**Estimated Effort:** 3-5 days
**Dependencies:** Entities

**Tasks:**
- [ ] Add `Entity.bounding_box` property
- [ ] `Entity.is_point_inside(x, y, z)` method
- [ ] `Entity.intersects(other)` method
- [ ] Calculate hitbox based on width/height
- [ ] Update hitbox when entity moves
- [ ] Tests for bounding box

**Acceptance Criteria:**
- Bounding box calculations are accurate
- Collision detection works
- Can detect when bot is within entity's hitbox

---

### M2: Raycasting/Line of Sight
**Impact:** Combat accuracy, targeting
**Estimated Effort:** 1-2 weeks
**Dependencies:** World, Protocol

**Tasks:**
- [ ] `bot.canSee(target)` method (raycast check)
- [ ] Raycast implementation
- [ ] Support for transparency (glass, leaves)
- [ ] Support for solidity (blocks that block LOS)
- [ ] Distance measurement to obstacle
- [ ] Tests for line of sight

**Acceptance Criteria:**
- Can check if bot can see target
- Raycast is reasonably fast (within 50ms)
- Handles transparent and solid blocks

---

### M3: NBT Item Integration
**Impact:** Enchanted items don't show effects
**Estimated Effort:** 1 week
**Dependencies:** NBT, Inventory

**Tasks:**
- [ ] Parse NBT from item components
- [ ] Expose `item.nbt` property
- [ ] Display enchantment effects
- [   Enchantment name, level
- -   Attribute modifiers
- - Custom name
- [ ] Update inventory display
- [ ] Tests for NBT integration

**Acceptance Criteria:**
- Enchanted items show effects in UI
- Attribute modifiers are applied
- Custom names work

---

### M4: Command System
**Impact:** No command parsing, can't respond to chat commands
**Estimated Effort:** 2 weeks
**Dependencies:** Chat, Message Signing

**Tasks:**
- [ ] `bot.on('chat')` event handler
- [ ] Command parser (prefix-based: !help, !tp, !inv)
- [ ] Built-in commands:
  - [ ] !follow <player>
  - [ ] !stop
  - ] !goto <x> <y> <z>
  - [ ] !attack <entity>
  - [ ] !inventory
- [ ] !status
- [ ] !eat
- [ ] Command aliases (short form)
- [ ] Help system
- [ ] Permission system (owner-only commands)
- [ ] Tests for command system

**Acceptance:**
- Bot responds to commands like `!follow player`
- Commands can be chained: `!follow player; !goto 100 64 200`
- Help system works
- Permissions work (e.g., only owner can !stop bot)

---

### M5: Block Helpers
**Impact:** Missing common block operations
**Estimated Effort:** 1 week
**Dependencies:** World

**Tasks:**
- [ ] `bot.canDigBlock(block)` method
- [ ] `bot.canPlaceBlock(block)` method
- [ ] `bot.canSeeBlock(x, y, z)` method
- [ ] `bot.getNearbyBlocks(position)` method
- [ ] `bot.isSolidBlock(block)` method
- [ ] `bot.isLiquidBlock(block)` method
- [ ] `bot.isTransparentBlock(block)` method
- [ ] Block helper updates:
  - [ ] Gravity-affected blocks
  - [ ] Water/lava damage
  [ ] Soul sand speed penalty
- [ ] Tests for block helpers

**Acceptance:**
- Can check if block is diggable
- Can check if bot can place block
- Block helpers correctly identify block types

---

### M6: Performance Monitoring
**Impact:** Cannot optimize without metrics
**Estimated Effort:** 1 week
**Dependencies:** Core

**Tasks:**
- [ ] Add TPS tracking
- [ ] Add ping monitoring
- [ ] Add memory usage tracking
- [ ] Add packet rate monitoring
- [ ] Add FPS calculation
- [ ] Performance metrics API
- [ ] Tests for performance monitoring

**Acceptance:**
- Can track bot performance metrics
- API provides useful debugging info

---

## � LOW Priority (Nice to Have)

### L1: Advanced Recipe Support
**Impact:** Can only do simple recipes
**Estimated Effort:** 2 weeks
**Dependencies:** Crafting, Inventory

**Tasks:**
- [ ] Multi-step recipe support
- [ ] Recipe tree support
- [ ] Recipe requirements validation
- [ ] Auto-recipe selection
- [ ] Missing ingredients detection
- [ ] Tests for advanced recipes

**Acceptance:**
- Bot can craft complex multi-step recipes
- Recipe selection is smart
- Validates requirements correctly

---

### L2: Debugging Tools
**Impact:** Hard to debug complex behaviors
**Estimated Effort:** 1 week
**Dependencies:** Core

**Tasks:**
- [ ] Add packet logger
- [ ] Add entity state inspector
- [ ] Add world state inspector
- [ ] Add event trace tool
- [ ] Debug console REPL
- [ ] Tests for debugging tools

**Acceptance:**
- Can inspect bot state at any time
- Event trace shows full history
- Debug REPL for testing

---

### L3: Example Bots
**Impact:** Users need working examples
**Estimated Effort:** 2 weeks
**Dependencies:** All major modules

**Tasks:**
- [ ] **Combat Bot** - Fight enemies, use shields, potions
  - [ ] Targeting (weakest → strongest)
  - [ ] Inventory management (auto-equip best gear)
  - [ ] Health potions when low
- [ ] Tactical retreat
- [ ] Tests for combat bot
- [ ] **Farming Bot** - Auto-farm crops
  - [ ] Find and harvest crops
  - [ ] Replant crops
  - [ ] Store items in chests
  [ ] Tests for farming bot
- [ ] **Mining Bot** - Mine efficiently
  - [ ] Use pathfinding
  - [ ] Avoid lava/danger
  [ ] Collect all ore
- - [ ] Return to drop location
- [ ] Sort items in chests
- [ ] Tests for mining bot
- [ ] **Guard Bot** - Protect area
  - [ ] Patrol around defined zone
  [ [ ] Alert on intruders
  [ ] Attack hostiles
- [ ] Tests for guard bot
- [ ] **Builder Bot** - Place blocks by plan
  - ] Read blueprint file
- [ ] Place blocks efficiently
  [ ] Remove blocks if wrong
- [ ] Tests for builder bot

**Acceptance:**
- Each example bot is fully functional
- Examples show common use cases
- All examples have tests

---

### L4: Plugin System
**Impact:** Cannot extend functionality easily
**Estimated Effort:** 3 weeks
**Dependencies:** All major modules

**Tasks:**
- [ ] Plugin loading system
- [ ] Plugin API
- [ ] Built-in plugins:
  - [ ] 3rd party plugins support
- [ ] Plugin configuration
  - [ ] Plugin permissions
- [ ] Plugin marketplace (future)
- [ ] Plugin examples
- [ ] Tests for plugin system

**Acceptance:**
- Users can install 3rd party plugins
- Plugin API is well-documented
- Examples demonstrate plugin development

---

### L5: Persistence
**Impact:** Bot state lost on disconnect
**Estimated Effort:** 1-2 weeks
**Dependencies:** All modules

**Tasks:**
- [ ] Save bot state to file
- [ ] Load bot state from file
- [ ] Save position, inventory, equipment
- [ ] Save active tasks
- [ ] Auto-save on disconnect
- [ ] Tests for persistence

**Acceptance Criteria:**
- Bot saves state properly
- Bot can resume from saved state
- Auto-save works reliably

---

### L6: Remote Control API
**Impact:** Cannot control bot remotely
**Estimated Effort:** 2 weeks
**Dependencies:** WebSocket, Events

**Tasks:**
- [ ] WebSocket server
- [ ] Remote control protocol
- [ ] Command execution
- [ ] State synchronization
- [ ] Event streaming
- [ ] Authentication
- [ ] Tests for remote control

**Acceptance Criteria:**
- WebSocket server accepts connections
- Can send commands to bot
- Bot state is synced to clients
- Multiple clients can connect

---

### L7: WebSocket Chat Support
**Impact:** Can't use external chat systems
**Estimated Effort:** 1 week
**Dependencies:** Chat, WebSocket

**Tasks:**
- [ ] WebSocket client support
- [ ] Connect to chat servers (Discord, IRC, etc.)
- [ ] Bridge bot chat to external servers
- [ ] Message forwarding
- [ ] Command processing from external
- [ ] Authentication with external servers
- [ ] Tests for WebSocket chat

**Acceptance: Criteria:**
- Can connect to Discord/IRC
- Bot messages are forwarded
- External commands can be executed

---

## ⬜ OPTIONAL Future Enhancements

### O1: Multiple Bot Support
**Estimated Effort:** 2 weeks
- Dependencies:** Protocol

**Tasks:**
- [ ] Multiple bot instances in one process
- [ ] Bot coordination system
- [ ] Shared state between bots
- [ ] Load balancing for servers
- [ ] Tests for multi-bot support

---

### O2: Statistics & Analytics
**Estimated Effort:** 1 week
**Dependencies:** Core

**Tasks:**
- [ ] Statistics collection module
- [ ] Actions logging
- [ ] Metrics calculation (kills, blocks mined, etc.)
- [ ] Performance metrics
- [ ] Export statistics to file/DB
- [ ] Tests for statistics

---

### O3: Machine Learning
**Estimated Effort:** 4+ weeks
**Dependencies:** All modules

**Tasks:**
- [ ] Collect training data
- [ ] ML model for pathfinding (learn efficient routes)
- [ ] ML model for combat (optimal attacks)
- [ ] ML model for resource gathering
- [ ] Model training pipeline
- [ ] Integration with AI system
- [ ] Tests for ML features

---

### O4: Graphical Interface
**Estimated Effort:** 3-4 weeks
**Dependencies:** All modules, WebSocket

**Tasks:**
- [ ] Web UI for bot control
- [ ] Real-time bot view (map view, inventory)
- [ ] Command center
- [ ] Log viewer
- [ ] Statistics dashboard
- [ ] Tests for web UI

---

## Dependencies Graph

```
Pathfinding → Movement, World
AI System → Pathfinding, Sensors, Movement, Combat
Villager Trading → Inventory, NBT, Protocol
Anvil/Enchanting → Inventory, NBT, Protocol
Command System → Chat, Protocol
Remote Control → WebSocket, Events
Persistence → All modules
```

---

## Implementation Order Recommendation

### Phase 1: Critical Foundation (2-3 weeks)
1. ✅ Pathfinding (C1)
2. ✅ Message Signing (C2)
3. ✅ Window Management (C3)

### Phase 2: High Priority Features (3-4 weeks)
4. Entity Interaction API (H1)
5. Villager Trading (H2)
6. AI System Integration (H4)
7. Advanced Inventory Features (H5, H6)

### Phase 3: Medium Priority (2-3 weeks)
8. Combat Target Selection (H3)
9. Entity Bounding Box (M1)
10. Command System (M4)
11. Performance Monitoring (M6)

### Phase 4: Low Priority (4+ weeks)
12. NBT Item Integration (M3)
13. Block Helpers (M5)
14. Debugging Tools (L2)
15. Example Bots (L1)

### Phase 5: Optional (ongoing)
16. Plugin System (L5)
17. Persistence (L6)
18. Remote Control API (L7)
19. WebSocket Chat Support (L8)
20. Multiple Bot Support (O1)
21. Statistics & Analytics (O2)

---

## Testing Coverage

### Current Status: 14/14 tests passing (100%)

```
✅ test_1_protocol_core.py
✅ test_2_game_plugin.py
✅ test_3_health_plugin.py
✅ test_4_entities_plugin.py
✅ test_5_blocks_plugin.py
✅ test_6_integration.py
✅ test_7_digging.py
✅ test_8_inventory.py
✅ test_9_click_modes.py
✅ test_10_nbt_components_recipes.py
✅ test_11_entities.py
✅ test_12_blocks.py
✅ test_13_digging.py
✅ test_14_entity_interactions.py
```

### Needed Tests (after feature implementation):

**Pathfinding:**
- [ ] test_pathfinding_basic.py - Simple A* navigation
- [ ] test_pathfinding_complex.py - Around obstacles
- [ ] test_pathfollowing.py - Follow entity with path

**Message Signing:**
- [ ] test_chat_signing.py - Signed chat
- [ ] test_chat_offline.py - Offline mode

**Window Management:**
- [ ] test_window_basic.py - Open/close
- [ ] test_window_shiftclick.py - Shift-click
- [ ] test_window_multiple.py - Multiple windows

**Villager Trading:**
- [ ] test_villager_basic.py - Open window
- [ ] test_villager_trade.py - Execute trade
- [ ] test_villager_emerald.py - Complex trades

**Combat Targeting:**
- [ ] test_combat_targeting.py - Target selection
- [ ] test_combat_retreat.py - Combat states

**AI System:**
- [ ] test_ai_follow_avoid.py - Follow + avoid threats
- [ ] test_ai_tasks.py - Task execution

---

## Progress Tracking

### Current Status:
- Core Protocol: 100%
- Entities: 100% (interaction API needed)
- Movement: 60% (pathfinding missing)
- World/Blocks: 95%
- Health: 100%
- Inventory: 70% (window mgmt needed)
- Crafting: 70%
- Combat: 60% (targeting needed)
- Chat: 30% (signing + receive needed)
- NBT: 95%
- Components: 90%
- Recipes: 70%
- Advanced Inv: 0%
- Vehicles: 60%
- Villager Trade: 0%
- AI System: 0% (design only)

**Overall: ~68%**

### Target: 100% feature parity with mineflayer

---

## Success Criteria

MinePyt achieves 100% feature parity when:

✅ All core modules work (protocol, entities, movement, world)
✅ Pathfinding implemented and integrated
✅ Chat works on online servers
✅ Window management complete
✅ Villager trading works
✅ AI system is functional and integrated
✅ All example bots are functional
✅ 100+ tests passing

**Estimated Time to 100%:**
- Phase 1 (Critical): 2-3 weeks
- Phase 2 (High): 3-4 weeks
- Phase 3 (Medium): 2-3 weeks
- Phase 4 (Low): 4+ weeks
- Phase 5 (Optional): Ongoing

**Total: 11-18 weeks from current state (68% → 100%)**
