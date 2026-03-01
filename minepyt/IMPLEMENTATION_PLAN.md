# ПОЛНЫЙ ПЛАН ДОРАБОТКИ MINEPYT
## Детальная разбивка с подзадачами
**Версия:** 2.0
**Дата:** 2026-03-01
**Цель:** Довести Minepyt до 100% функционала Mineflayer

---

# ЭКЗАМЕНАЦИОННАЯ ВЕРСИЯ

## Текущий прогресс: 60-65%

### Что УЖЕ ЕСТЬ в Minepyt:
- ✅ NBT Parser (все 12 типов тегов)
- ✅ Components (1.21.4 item components)
- ✅ Recipe System (Shaped, Shapeless, Smelting, Stonecutting)
- ✅ Entity Manager (поиск, фильтры, nearest_* методы)
- ✅ Digging Helpers (hardness, tool tiers, can_harvest)
- ✅ Block Helpers (findBlock, blocksInRadius, blockAtFace)
- ✅ Protocol States (HANDSHAKING → LOGIN → CONFIGURATION → PLAY)
- ✅ Game State Tracking (game mode, dimension, difficulty, time)
- ✅ Health System (health, food, saturation, auto-respawn)
- ✅ Basic Inventory (slots, held_item, click modes)
- ✅ Chunk Parsing (полная система чанков)

### Чего НЕТ (критично):
- ❌ Bot.connect() - NotImplementedError (БОТ НЕ МОЖЕТ ПОДКЛЮЧИТЬСЯ!)
- ❌ Chat.send() - pass (НЕ РАБОТАЕТ)
- ❌ Movement System - АБСОЛЮТНО НЕТ
- ❌ Combat System - АБСОЛЮТНО НЕТ
- ❌ Advanced Inventory (containers, drag mode) - НЕТ
- ❌ Advanced Crafting (smithing, enchantment) - НЕТ
- ❌ Vehicle System - НЕТ
- ❌ Block Interaction (place_block) - НЕТ

---

# ПРИОРИТЕТ 1: CONNECTION LAYER (БЛОКИРУЮЩИЙ)

## Задача 1.1: Реализовать Bot.connect()

### Подзадача 1.1.1: Создать connection module
**Файл:** `minepyt/protocol/connection.py`

**Что сделать:**
```python
class MinecraftConnection:
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.connection = None
        self.state = ProtocolState.HANDSHAKING
        
    async def connect(self):
        # 1. TCP connect
        # 2. Send handshake
        # 3. Send login start
        # 4. Wait for login success
        # 5. Transition to CONFIGURATION
        # 6. Send client info
        # 7. Wait for finish configuration
        # 8. Transition to PLAY
```

**Зависимости:**
- mcproto.connection.TCPAsyncConnection
- mcproto.buffer.Buffer

**Оценка:** 8-10 часов

**Тесты:**
- test_connection_basic.py
- test_handshake.py
- test_login_flow.py

---

### Подзадача 1.1.2: Реализовать handshake packet
**Файл:** `minepyt/protocol/packets/serverbound/handshake.py`

**Пакет:** 0x00 (Handshake)

**Структура:**
```python
async def send_handshake(self, next_state=2):
    buf = Buffer()
    buf.write_varint(PROTOCOL_VERSION)  # 769 for 1.21.4
    buf.write_utf(self.host)
    buf.write_value(StructFormat.USHORT, self.port)
    buf.write_varint(next_state)  # 2 = login
    
    await self._write_packet(0x00, bytes(buf))
```

**Оценка:** 2-3 часа

---

### Подзадача 1.1.3: Реализовать login sequence
**Файл:** `minepyt/protocol/packets/serverbound/login.py`

**Пакеты:**
- 0x00: Login Start
- 0x03: Login Acknowledged (→ Configuration state)

**Методы:**
```python
async def send_login_start(self):
    buf = Buffer()
    buf.write_utf(self.username)
    # UUID (16 bytes of zeros for offline mode)
    uuid_obj = UUID(bytes=b"\x00" * 16)
    uuid_obj.serialize_to(buf)
    await self._write_packet(0x00, bytes(buf))

async def send_login_acknowledged(self):
    await self._write_packet(0x03, b"")
    self.state = ProtocolState.CONFIGURATION
```

**Оценка:** 3-4 часа

---

### Подзадача 1.1.4: Реализовать configuration state
**Файл:** `minepyt/protocol/packets/serverbound/configuration.py`

**Пакеты:**
- 0x00: Client Information
- 0x07: Known Packs
- 0x03: Acknowledge Finish Configuration

**Методы:**
```python
async def send_client_information(self):
    buf = Buffer()
    buf.write_utf("en_GB")  # locale
    buf.write_value(StructFormat.BYTE, 10)  # view distance
    buf.write_varint(0)  # chat mode
    buf.write_value(StructFormat.BOOL, True)  # chat colors
    buf.write_value(StructFormat.BYTE, 0x7F)  # displayed skin parts
    buf.write_varint(1)  # main hand
    buf.write_value(StructFormat.BOOL, False)  # enable text filtering
    buf.write_value(StructFormat.BOOL, True)  # allow server listings
    buf.write_varint(0)  # particle status
    await self._write_packet(0x00, bytes(buf))
```

**Оценка:** 4-5 часов

---

### Подзадача 1.1.5: Реализовать Keep-Alive handling
**Файл:** `minepyt/protocol/handlers/keep_alive.py`

**Пакеты:**
- Clientbound: 0x27 (Keep Alive)
- Serverbound: 0x0F (Keep Alive Response)

**Handler:**
```python
async def handle_keep_alive(self, packet):
    keep_alive_id = packet.read_value(StructFormat.LONGLONG)
    await self.send_keep_alive(keep_alive_id)
```

**Оценка:** 2-3 часа

---

### Подзадача 1.1.6: Интегрировать в Bot class
**Файл:** `minepyt/loader.py`

**Изменения:**
```python
class Bot:
    async def connect(self):
        # Create connection
        self._protocol = MinecraftProtocol(
            self.host, self.port, self.username
        )
        
        # Connect
        await self._protocol.connect()
        
        # Wait for spawn
        await self.wait_for_spawn()
```

**Оценка:** 3-4 часа

---

## Итого по Connection Layer:
- **Общее время:** 22-29 часов (~3-4 дня)
- **Приоритет:** BLOCKER
- **Результат:** Бот может подключиться и оставаться онлайн

---

# ПРИОРИТЕТ 2: MOVEMENT SYSTEM

## Задача 2.1: Создать movement module

### Подзадача 2.1.1: Создать movement controls
**Файл:** `minepyt/movement/controls.py`

**Методы:**
```python
class MovementControls:
    async def walk(self, direction, duration_ms=1000):
        """Walk in direction for duration"""
        
    async def jump(self):
        """Jump once"""
        
    async def sprint(self, enable=True):
        """Enable/disable sprinting"""
        
    async def sneak(self, enable=True):
        """Enable/disable sneaking"""
```

**Оценка:** 6-8 часов

---

### Подзадача 2.1.2: Реализовать position packets
**Файл:** `minepyt/protocol/packets/serverbound/play/movement.py`

**Пакеты:**
- 0x1B: Player Position
- 0x1D: Player Position & Rotation
- 0x1E: Player Rotation

**Методы:**
```python
async def send_player_position(self, x, y, z, on_ground=True):
    buf = Buffer()
    buf.write_value(StructFormat.DOUBLE, x)
    buf.write_value(StructFormat.DOUBLE, y)
    buf.write_value(StructFormat.DOUBLE, z)
    buf.write_value(StructFormat.BYTE, 0x01 if on_ground else 0x00)
    await self._write_packet(0x1B, bytes(buf))

async def send_player_position_and_rotation(self, x, y, z, yaw, pitch, on_ground=True):
    buf = Buffer()
    buf.write_value(StructFormat.DOUBLE, x)
    buf.write_value(StructFormat.DOUBLE, y)
    buf.write_value(StructFormat.DOUBLE, z)
    buf.write_value(StructFormat.FLOAT, yaw)
    buf.write_value(StructFormat.FLOAT, pitch)
    buf.write_value(StructFormat.BYTE, 0x01 if on_ground else 0x00)
    await self._write_packet(0x1D, bytes(buf))
```

**Оценка:** 4-5 часов

---

### Подзадача 2.1.3: Создать physics engine
**Файл:** `minepyt/movement/physics.py`

**Функциональность:**
```python
class PhysicsEngine:
    def apply_gravity(self, entity, dt):
        """Apply gravity to entity"""
        # Gravity: -0.08 blocks/tick
        # Terminal velocity: -3.0 blocks/tick
        
    def check_collision(self, entity, new_pos):
        """Check if entity collides with blocks"""
        # Bounding box collision
        # Return True if collision
        
    def update_position(self, entity, dt):
        """Update entity position based on velocity"""
```

**Оценка:** 15-20 часов

---

### Подзадача 2.1.4: Реализовать collision detection
**Файл:** `minepyt/movement/collision.py`

**Методы:**
```python
class CollisionDetector:
    def check_block_collision(self, bbox, world):
        """Check bounding box against world blocks"""
        
    def get_surrounding_blocks(self, position, radius=2):
        """Get blocks around position for collision check"""
        
    def resolve_collision(self, entity, movement_vector):
        """Resolve collision and return valid movement"""
```

**Оценка:** 12-15 часов

---

### Подзадача 2.1.5: Создать movement loop
**Файл:** `minepyt/movement/loop.py`

**Функциональность:**
```python
async def movement_loop(self):
    """Main movement update loop (20 ticks/second)"""
    while self._running:
        # Update physics
        # Check collisions
        # Send position update
        # Wait 50ms (1 tick)
        await asyncio.sleep(0.05)
```

**Оценка:** 5-7 часов

---

## Итого по Movement System:
- **Общее время:** 42-55 часов (~5-7 дней)
- **Приоритет:** HIGH
- **Результат:** Бот может двигаться, прыгать, приседать

---

# ПРИОРИТЕТ 3: COMBAT SYSTEM

## Задача 3.1: Создать combat module

### Подзадача 3.1.1: Реализовать attack method
**Файл:** `minepyt/combat/attack.py`

**Методы:**
```python
async def attack(self, entity_id):
    """Attack entity by ID"""
    # 1. Send arm animation
    await self.swing_arm()
    # 2. Send use entity packet
    await self.send_use_entity(entity_id, mouse=1)  # 1 = attack

async def attack_entity(self, entity):
    """Attack entity object"""
    await self.attack(entity.entity_id)
```

**Оценка:** 4-5 часов

---

### Подзадача 3.1.2: Реализовать use entity packet
**Файл:** `minepyt/protocol/packets/serverbound/play/use_entity.py`

**Пакет:** 0x0E (Use Entity)

**Методы:**
```python
async def send_use_entity(self, target_id, mouse=0, sneaking=False):
    """
    mouse: 0 = interact, 1 = attack, 2 = interact at
    """
    buf = Buffer()
    buf.write_varint(target_id)
    buf.write_varint(mouse)
    buf.write_value(StructFormat.BOOL, sneaking)
    await self._write_packet(0x0E, bytes(buf))
```

**Оценка:** 3-4 часа

---

### Подзадача 3.1.3: Реализовать arm animation
**Файл:** `minepyt/protocol/packets/serverbound/play/animation.py`

**Пакет:** 0x0B (Arm Animation)

**Методы:**
```python
async def swing_arm(self, hand='right'):
    """Swing arm animation"""
    buf = Buffer()
    buf.write_varint(0 if hand == 'right' else 1)
    await self._write_packet(0x0B, bytes(buf))
```

**Оценка:** 1-2 часа

---

### Подзадача 3.1.4: Реализовать damage handler
**Файл:** `minepyt/protocol/handlers/entity_damage.py`

**Пакет:** 0x47 (Entity Damage)

**Handler:**
```python
async def handle_entity_damage(self, packet):
    entity_id = packet.read_varint()
    source_cause_id = packet.read_varint()
    
    entity = self.entity_manager.get(entity_id)
    source = self.entity_manager.get(source_cause_id - 1)
    
    self.emit('entityHurt', entity, source)
```

**Оценка:** 2-3 часа

---

### Подзадача 3.1.5: Создать PvP helpers
**Файл:** `minepyt/combat/pvp.py`

**Методы:**
```python
def get_attack_cooldown(self):
    """Calculate attack cooldown based on held item"""
    
def can_attack(self, target):
    """Check if bot can attack target (distance, cooldown)"""
    
async def auto_attack(self, target, max_distance=4.0):
    """Automatically attack target while in range"""
```

**Оценка:** 5-7 часов

---

## Итого по Combat System:
- **Общее время:** 15-21 час (~2-3 дня)
- **Приоритет:** HIGH
- **Результат:** Бот может атаковать, наносить урон

---

# ПРИОРИТЕТ 4: ADVANCED INVENTORY

## Задача 4.1: Container management

### Подзадача 4.1.1: Реализовать container open/close
**Файл:** `minepyt/inventory/containers.py`

**Методы:**
```python
async def open_container(self, position):
    """Open container at position"""
    # Send use item on block packet
    # Wait for Open Screen packet (0x3B)
    
async def close_container(self):
    """Close current container"""
    await self.send_close_container()
```

**Оценка:** 4-5 часов

---

### Подзадача 4.1.2: Реализовать drag mode
**Файл:** `minepyt/inventory/drag_mode.py`

**Методы:**
```python
async def start_drag(self, button=0):
    """Start drag operation (QUICK_CRAFT mode)"""
    
async def drag_to_slot(self, slot):
    """Drag cursor to slot"""
    
async def end_drag(self):
    """End drag operation"""
```

**Оценка:** 6-8 часов

---

### Подзадача 4.1.3: Реализовать cursor tracking
**Файл:** `minepyt/inventory/cursor.py`

**Функциональность:**
```python
class CursorTracker:
    def __init__(self):
        self.cursor_item = None
        
    def update_from_click(self, slot, item, mode):
        """Update cursor based on click"""
        if mode == ClickMode.PICKUP:
            # Swap cursor with slot
            pass
        elif mode == ClickMode.QUICK_MOVE:
            # Shift-click (no cursor change)
            pass
```

**Оценка:** 3-4 часа

---

### Подзадача 4.1.4: Реализовать container events
**Файл:** `minepyt/inventory/events.py`

**Events:**
- container_open
- container_close
- slot_update
- inventory_update

**Оценка:** 2-3 часа

---

## Итого по Advanced Inventory:
- **Общее время:** 15-20 часов (~2-3 дня)
- **Приоритет:** MEDIUM
- **Результат:** Полное управление контейнерами

---

# ПРИОРИТЕТ 5: CHAT SYSTEM

## Задача 5.1: Исправить chat sending

### Подзадача 5.1.1: Реализовать chat send
**Файл:** `minepyt/chat/sender.py`

**Методы:**
```python
async def chat(self, message):
    """Send chat message"""
    if len(message) > 256:
        message = message[:256]
    
    buf = Buffer()
    buf.write_utf(message)
    buf.write_value(StructFormat.LONGLONG, 0)  # timestamp
    buf.write_value(StructFormat.LONGLONG, 0)  # salt
    buf.write_value(StructFormat.BOOL, False)  # no signature
    buf.write_varint(0)  # message count
    buf.write_value(StructFormat.BYTE, 0)  # bitset
    buf.write_value(StructFormat.BYTE, 0)
    buf.write_value(StructFormat.BYTE, 0)
    
    await self._write_packet(0x07, bytes(buf))
```

**Оценка:** 3-4 часа

---

### Подзадача 5.1.2: Реализовать whisper
**Файл:** `minepyt/chat/whisper.py`

**Методы:**
```python
async def whisper(self, username, message):
    """Send private message"""
    await self.chat(f"/msg {username} {message}")
```

**Оценка:** 1-2 часа

---

### Подзадача 5.1.3: Улучшить chat parsing
**Файл:** `minepyt/chat/parser.py`

**Функциональность:**
- Parse JSON chat components
- Extract text, colors, formatting
- Handle translations

**Оценка:** 4-5 часов

---

## Итого по Chat System:
- **Общее время:** 8-11 часов (~1-2 дня)
- **Приоритет:** MEDIUM
- **Результат:** Рабочий чат

---

# ПРИОРИТЕТ 6: BLOCK INTERACTION

## Задача 6.1: Place block

### Подзадача 6.1.1: Реализовать place_block
**Файл:** `minepyt/blocks/placement.py`

**Методы:**
```python
async def place_block(self, x, y, z, face=1, hand=0):
    """Place block at position"""
    # Packet: Use Item On (0x1E)
    buf = Buffer()
    buf.write_varint(hand)  # 0 = main hand
    # Position encoding
    pos_long = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)
    buf.write_value(StructFormat.LONG, pos_long)
    buf.write_varint(face)
    buf.write_value(StructFormat.FLOAT, 0.5)  # cursor X
    buf.write_value(StructFormat.FLOAT, 0.5)  # cursor Y
    buf.write_value(StructFormat.FLOAT, 0.5)  # cursor Z
    buf.write_value(StructFormat.BOOL, False)  # inside block
    buf.write_varint(self._sequence)
    
    await self._write_packet(0x1E, bytes(buf))
```

**Оценка:** 4-5 часов

---

### Подзадача 6.1.2: Реализовать raycasting
**Файл:** `minepyt/blocks/raycast.py`

**Методы:**
```python
def raycast(self, start_pos, direction, max_distance):
    """Cast ray and return first block hit"""
    
def can_see_block(self, block_pos):
    """Check if block is in line of sight"""
```

**Оценка:** 8-10 часов

---

### Подзадача 6.1.3: Реализовать block actions
**Файл:** `minepyt/blocks/actions.py`

**Методы:**
```python
async def activate_block(self, position):
    """Activate block (button, lever, door)"""
    
async def open_block(self, position):
    """Open block (chest, furnace)"""
```

**Оценка:** 3-4 часа

---

## Итого по Block Interaction:
- **Общее время:** 15-19 часов (~2-3 дня)
- **Приоритет:** MEDIUM
- **Результат:** Бот может ставить блоки

---

# ПРИОРИТЕТ 7: ADVANCED CRAFTING

## Задача 7.1: Smithing recipes

### Подзадача 7.1.1: Создать smithing.py
**Файл:** `minepyt/crafting/smithing.py`

**Классы:**
```python
@dataclass
class SmithingTransformRecipe(Recipe):
    template: Ingredient
    base: Ingredient
    addition: Ingredient

@dataclass
class SmithingTrimRecipe(Recipe):
    template: Ingredient
    base: Ingredient
    material: Ingredient
```

**Оценка:** 6-8 часов

---

### Подзадача 7.1.2: Создать special.py
**Файл:** `minepyt/crafting/special.py`

**Классы:**
- DyeArmorRecipe
- CloneBookRecipe
- MapCloningRecipe
- Banner recipes

**Оценка:** 5-7 часов

---

### Подзадача 7.1.3: Создать enchantment_table.py
**Файл:** `minepyt/crafting/enchantment_table.py`

**Методы:**
```python
async def open_enchantment_table(self, position):
    """Open enchantment table"""
    
async def enchant_item(self, slot, enchantment_id):
    """Enchant item in slot"""
```

**Оценка:** 10-12 часов

---

### Подзадача 7.1.4: Создать auto_craft
**Файл:** `minepyt/crafting/auto_craft.py`

**Методы:**
```python
async def auto_craft(self, item_name, count=1):
    """Automatically craft item"""
    # 1. Find recipe
    # 2. Check ingredients
    # 3. Move ingredients to grid
    # 4. Click output
    # 5. Repeat
```

**Оценка:** 8-10 часов

---

## Итого по Advanced Crafting:
- **Общее время:** 29-37 часов (~4-5 дней)
- **Приоритет:** LOW
- **Результат:** Полный крафтинг

---

# ИТОГОВАЯ ОЦЕНКА

## Суммарное время по приоритетам:

| Приоритет | Задачи | Часы | Дни (8ч/день) |
|-----------|---------|------|--------------|
| **P1: Connection** | 6 | 22-29 | 3-4 дня |
| **P2: Movement** | 5 | 42-55 | 5-7 дней |
| **P3: Combat** | 5 | 15-21 | 2-3 дня |
| **P4: Inventory** | 4 | 15-20 | 2-3 дня |
| **P5: Chat** | 3 | 8-11 | 1-2 дня |
| **P6: Block Interaction** | 3 | 15-19 | 2-3 дня |
| **P7: Advanced Crafting** | 4 | 29-37 | 4-5 дней |

**ИТОГО:**
- **Минимум:** 146 часов (~18 дней)
- **Максимум:** 192 часа (~24 дня)
- **Реалистично:** 170 часов (~21 день)

---

# РЕКОМЕНДАЦИИ ПО РЕАЛИЗАЦИИ

## 1. Порядок выполнения
1. ✅ Connection Layer (P1) - без этого бот не работает
2. ✅ Movement (P2) - базовая функциональность
3. ✅ Combat (P3) - полезно для бота
4. ✅ Chat (P5) - важное взаимодействие
5. ✅ Block Interaction (P6) - полезно
6. ⚠️ Inventory (P4) - улучшение
7. ⚠️ Advanced Crafting (P7) - опционально

## 2. Тестирование
- Каждый модуль = отдельный тест
- Интеграционные тесты после каждого приоритета
- Цель: 80%+ coverage

## 3. Архитектура
- Создать `protocol/packets/` структуру
- Разбить protocol.py на модули
- Добавить type hints везде
- Документировать каждый метод

---

# ФИНАЛЬНЫЙ РЕЗУЛЬТАТ

**Minepyt 2.0 будет иметь:**
- ✅ Полный Protocol & Connection (100%)
- ✅ Полный Movement & Physics (30%+)
- ✅ Полный Combat System (25%+)
- ✅ Рабочий Chat System (70%+)
- ✅ Полный Block Interaction (95%+)
- ✅ Advanced Inventory (75%+)
- ✅ Advanced Crafting (85%+)
- ✅ Entity System с движением (95%+)

**Общий прогресс:** 95-100% функционала Mineflayer

**Время до завершения:** 3-4 недели интенсивной работы

---

**Конец плана**