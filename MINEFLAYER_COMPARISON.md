# Детальное сравнение Mineflayer vs Minepyt
# Создано: 2026-03-01
# Цель: Полный анализ функционала для создания плана доработки Minepyt

## Методология

1. Изучены файлы Mineflayer (JavaScript)
2. Изучены файлы Minepyt (Python)
3. Сравнение по функциональным категориям
4. Зафиксирование что ЕСТЬ в Mineflayer
5. Зафиксирование чего НЕТ в Minepyt
6. Создание детального плана доработки с мелкими подзадачами

---

# РАЗДЕЛ 1: Protocol & Connection

## Mineflayer - Что ЕСТЬ

### Основной файл: loader.js
- **bot.connect()** - Подключение к серверу
- **Протокольные состояния**: Handshaking → Login → Configuration → Play
- **Keep-Alive**: Автоматическое поддержание соединения
- **Компрессия**: zlib для пакетов
- **Packet I/O**: Чёткая система чтения/записи

### Пакеты (Clientbound - сервер→клиент)
Всё реализовано:
- ✅ Login (Join Game) - 0x2C
- ✅ Respawn - 0x3D
- ✅ Game State Change - 0x4A
- ✅ Update Time - 0x4E
- ✅ Update Health - 0x52
- ✅ Player Info Update - 0x40
- ✅ Player Info Remove - 0x3F
- ✅ System Chat - 0x73
- ✅ Level Chunk With Light - 0x28
- ✅ Forget Level Chunk - 0x25
- ✅ Block Update - 0x09
- ✅ Block Break Animation - 0x06
- ✅ Block Action - 0x08
- ✅ Block Entity Data - 0x07
- ✅ Multi Block Change - 0x10
- ✅ Spawn Entity - 0x01, 0x02, 0x05, 0x5A
- ✅ Spawn Experience Orb - 0x02
- ✅ Spawn Mob - 0x05
- ✅ Spawn Painting - 0x0A
- ✅ Spawn Player - 0x5A
- ✅ Entity Animation - 0x03
- ✅ Entity Position - 0x1F
- ✅ Entity Pos+Rot - 0x20
- ✅ Entity Rotation - 0x21
- ✅ Entity Velocity - 0x4C
- ✅ Entity Damage - 0x47
- ✅ Head Look - 0x3D
- ✅ Remove Entities - 0x3E
- ✅ Teleport Entity - 0x3F
- ✅ Entity Equipment - 0x48
- ✅ Set Entity Metadata - 0x4D
- ✅ Entity Link - 0x4B
- ✅ Entity Attributes - 0x56
- ✅ Set Passengers - 0x5B
- ✅ Entity Event - 0x19
- ✅ Set Container Content - 0x14
- ✅ Set Container Slot - 0x15
- ✅ Open Screen - 0x3B
- ✅ Declare Recipes - 0x42

### Пакеты (Serverbound - клиент→сервер)
Всё реализовано:
- ✅ Keep Alive - 0x0F
- ✅ Player Position - 0x1B
- ✅ Player Position & Rotation - 0x1D
- ✅ Player Digging - 0x1E
- ✅ Set Held Item - 0x28
- ✅ Click Container - 0x0F
- ✅ Close Container - 0x12
- ✅ Client Information - 0x00
- ✅ Acknowledge Block Change - 0x04
- ✅ Chat Message (unsigned) - 0x07
- ✅ Anvil (0x0D, 0x0B, 0x0F)
- ✅ Enchantment Table
- ✅ Steer Vehicle
- ✅ Craft Item Request
- ✅ Creative Inventory Action
- ✅ Use Item On - 0x1E
- ✅ Update Jigsaw Block

---

## Minepyt - Что ЕСТЬ (из PROJECT_STATUS.md + code review)

### Основные файлы
- **protocol.py** (~1400 строк) - монолит с ВСЕМ
- **entities.py** (~710 строк) - полная система
- **digging.py** (~480 строк) -helpers
- **recipes.py** (~550 строк) - система рецептов
- **nbt.py** (~580 строк) - полный парсер
- **components.py** (~510 строк) - 1.21.4 компоненты
- **block_registry.py**, **chunk_utils.py** - блоки и чанки

### Protocol States
- ✅ ProtocolState enum: HANDSHAKING, STATUS, LOGIN, CONFIGURATION, PLAY
- ✅ Handshake packet
- ✅ Login sequence
- ✅ Configuration state (1.20.5+)
- ✅ Play state
- ✅ Keep-Alive handling
- ✅ Compression

### Game State
- ✅ Game класс: mode, dimension, difficulty, time, respawn
- ✅ Events: login, game, respawn, time

### Entities
- ✅ Entity dataclass: position, velocity, equipment, metadata
- ✅ EntityManager: поиск, фильтры
- � EntityType enum: PLAYER, MOB, OBJECT
- ✅ Entity handlers: spawn, move, teleport, equipment, damage
- ✅ MobType enum: 50+ типов
- ✅ ObjectType enum: 40+ типов
- ✅ nearest_entity(), nearest_player(), nearest_hostile()

### Blocks/World
- ✅ World класс: чанки
- ✅ Block классы: state_id, position, helpers
- ✅ blockAt(), get_loaded_chunks()
- ✅ findBlock(), blocksInRadius(), blockAtFace()
- ✅ canDigBlock(), canSeeBlock()

### Digging
- ✅ dig(), stop_digging()
- ✅ DigStatus enum: START_DIGGING, CANCEL_DIGGING, FINISH_DIGGING
- ✅ calculate_dig_time() - учёт hardness, tool tiers
- ✅ can_harvest() - проверка инструмента
- ✅ best_tool() - поиск лучшего инструмента
- ✅ tool_tier(), tool_type()

### Inventory
- ✅ Item класс: item_id, count, name, components
- ✅ ItemComponents: enchantments, attributes, lore, durability
- ✅ ClickMode enum: PICKUP, QUICK_MOVE, SWAP, CLONE, THROW, QUICK_CRAFT, PICKUP_ALL
- ✅ ClickButton enum: LEFT, RIGHT, MIDDLE
- ✅ send_container_click(), send_set_held_slot(), send_close_container()
- ✅ Container tracking

### Crafting
- ✅ RecipeRegistry: хранилище рецептов
- ✅ ShapedRecipe, ShapelessRecipe
- ✅ SmeltingRecipe
- ✅ StonecuttingRecipe
- ✅ RecipeMatcher: find_craftable(), find_for_output()
- ✅ RecipeType enum: 24 типа рецептов

### NBT
- ✅ Все 12 типов тегов: Byte, Short, Int, Long, Float, Double, ByteArray, String, List, Compound, IntArray, LongArray
- ✅ NbtReader: чтение NBT данных
- ✅ NbtCompound, NbtList и все производные классы

### Components
- ✅ ItemComponents: enchantments, attributes, custom names, lore, damage, durability
- ✅ Enchantment, AttributeModifier классы
- ✅ TextComponent: текстовые компоненты
- ✅ ComponentType enum: 40+ типов компонентов

---

# РАЗДЕЛ 2: Entities (детальный анализ)

## Mineflayer - Полная реализация

### Плагин: entities.js (966 строк)

#### Entity Tracking
- ✅ **bot.entities** - словарь всех entities
- ✅ **bot.players** - словарь игроков
- ✅ **bot.entity** - bot's own entity
- ✅ **bot.findPlayer(filter)** - поиск игроков
- ✅ **bot.nearestEntity(match)** - ближайший entity
- ✅ **distanceTo()** - расчёт расстояния

#### Entity Spawning
- ✅ **named_entity_spawn** - спавн по имени
- ✅ **spawn_entity** - спавн мобов/объектов
- ✅ **spawn_entity_experience_orb** - опыторбы
- ✅ **Entity types**: player, mob, object, global

#### Entity Movement
- ✅ **entity_position** - позиция (fixed/double)
- ✅ **rel_entity_move** - относительное движение
- ✅ **entity_move_look** - поворот
- ✅ **entity_move_look** - движение+поворот
- ✅ **entity_teleport** - телепорт
- ✅ **Entity Velocity** - скорость

#### Equipment
- ✅ **entity_equipment** - экипировка
- ✅ **setEquipment()** - установка слотов

#### Metadata & Effects
- ✅ **entity_metadata** - метаданные
- ✅ **entity_status** - статус (crouch, sleeping, etc.)
- ✅ **entity_effect** - эффекты
- ✅ **remove_entity_effect** - удаление эффектов

#### Entity Attributes
- ✅ **entity_attributes** - атрибуты с модификаторами

#### Vehicle System
- ✅ **attach_entity** - посадить на транспорт
- ✅ **set_passengers** - пассажиры
- ✅ **mount/dismount** - управление транспортом

#### Combat
- ✅ **damage_event** - урон
- ✅ **swingArm()** - анимация руки
- ✅ **useOn()** - взаимодействие
- ✅ **attack(target)** - атака

#### Fireworks
- ✅ **BotUsedFireworkRocket** - обработка фейерверков
- ✅ **Entity flying** - элитры

#### Events (что эмитит entities.js)
- ✅ **entitySpawn** - при спавне
- ✅ **entityGone** - при удалении
- ✅ **entityMoved** - при движении
- ✅ **entityHurt** - при уроне
- ✅ **entityEquip** - при смене экипировки
- ✅ **entitySleep** - когда спит
- ✅ **entityWake** - когда проснулся
- ✅ **entityCrouch/Uncrouch** - при приседе
- ✅ **entityElytraFlew** - элитры
- ✅ **entityEffect** - эффекты
- ✅ **entityAttach/Detach** - транспорт
- ✅ **itemDrop** - дроп предмета
- **entityUpdate** - обновление метаданных
- **entityAttributes** - изменение атрибутов
- **playerCollect** - подбор предметов
- **playerJoined** - игрок зашёл
- **playerLeft** - игрок вышел
- **playerUpdated** - обновление игрока

---

## Minepyt - Чего НЕТ

### Entity Tracking
- ✅ **EntityManager есть** - поиск, фильтры
- ❌ **bot.findPlayer() нет** - нет метода в entities.py или API
- ❌ **bot.players словарь есть но не используется** - нет Player Info Update handlers
- ❌ **bot.entity атрибут** - есть но только для чтения
- ❌ **entity.velocity отслежка нет** - нет отправки velocity пакетов

### Entity Spawning
- ✅ **Spawn handlers в protocol.py есть** - 0x01, 0x02, 0x05, 0x5A
- ✅ **Entity классы есть** - MobType (50+), ObjectType (40+)
- ❌ **Spawn Experience Orb handler отсутствует**
- ❌ **Spawn Painting handler отсутствует**
- ❌ **named_entity_spawn отсутствует**

### Entity Movement
- ❌ **send_position() есть** - только отправка позиции
- ❌ **send_player_position() есть** - только отправка позиции+поворота
- ❌ **rel_entity_move handler отсутствует**
- ❌ **entity_move_look handler отсутствует**
- ❌ **entity_teleport handler отсутствует**
- ❌ **entity_velocity отправка отсутствует**

### Combat
- ❌ **attack() метод отсутствует**
- ❌ **useOn() метод отсутствует**
- ❌ **swingArm() отсутствует**
- ❌ **damage_event handler отсутствует**

### Vehicle System
- ❌ **mount/dismount методы отсутствуют**
- ❌ **attach_entity handler отсутствует**
- ❌ **set_passengers handler отсутствует**
- ❌ **send_steer_vehicle() отсутствует**
- ❌ **send_player_input() отсутствует**

### Events
- ✅ **entitySpawn** - есть
- ✅ **entityMoved** - есть
- ❌ **entityHurt** - нет
- ❌ **entityEquip** - нет
- ❌ **entitySleep** - нет
- ❌ **entityWake** - нет
- ❌ **entityCrouch** - нет
- ❌ **entityElytraFlew** - нет
- ❌ **entityEffect** - нет
- ❌ **entityAttach/Detach** - нет
- ❌ **itemDrop** - нет
- ❌ **playerCollect** - нет
- ❌ **playerJoined** - нет
- ❌ **playerLeft** - нет
- ❌ **playerUpdated** - нет

---

# ПЛАН ДОРАБОТКИ КОНКРЕТНЫЙ (Entity System)

### Приоритет 1: Entity Movement (КРИТИЧНО)

#### Подзадача 1.1: Реализовать entity movement packets
**Цель:** Отправка пакетов движения бота

**Что сделать:**
1.1. Создать `protocol/serverbound/play/movement.py`
1.2. Реализовать методы:
   ```python
   async def send_player_position(self, x, y, z, on_ground=True)
       """Отправить позицию бота"""
       
   async def send_player_position_and_rotation(self, x, y, z, yaw, pitch, on_ground=True)
       """Отправить позицию и поворот"""
       
   async def send_player_rotation(self, yaw, pitch)
       """Отправить только поворот"""
   ```

**Пакеты:**
- 0x1B: Player Position
- 0x1D: Player Position & Rotation

**Зависимости:**
- mcproto.Buffer
- ProtocolState.PLAY
- compression_threshold

**Пример использования:**
```python
await bot.send_player_position(100, 64, 200, on_ground=True)
await bot.send_player_position_and_rotation(100, 64, 200, 0.5, 1.2, on_ground=False)
```

**Проверка:**
- [ ] Создан файл `protocol/serverbound/play/movement.py`
- [ ] Методы реализованы
- [ ] Пакеты отправляются корректно
- [ ] Добавлены unit тесты

---

#### Подзадача 1.2: Реализовать entity velocity
**Цель:** Отправка скорости бота

**Что сделать:**
1.1. В `protocol/serverbound/play/movement.py` добавить:
   ```python
   async def send_entity_velocity(self, velocity_x, velocity_y, velocity_z)
       """Отправить скорость бота"""
   ```

**Пакет:** 0x1C (Entity Velocity)

**Проверка:**
- [ ] Метод добавлен
- [ ] Пакет 0x1C отправляется

---

#### Подзадача 1.3: Реализовать teleport entity
**Цель:** Отправка телепорта бота

**Что сделать:**
1.1. Создать handler для 0x3F
1.2. Реализовать метод отправки

**Пакет:** 0x3F (Teleport Entity)

**Проверка:**
- [ ] Handler создан
- [ ] Метод реализован

---

### Приоритет 2: Combat System (Важно)

#### Подзадача 2.1: Реализовать attack()
**Цель:** Атака сущностей

**Что сделать:**
2.1.1. Создать `protocol/serverbound/play/combat.py`
2.1.2. Реализовать:
   ```python
   async def attack(self, entity_id)
       """Атаковать сущность по ID"""
       
   async def attack_entity(self, entity)
       """Атаковать entity объект"""
   ```

**Пакеты:**
- 0x0E (Use Entity) - взаимодействие
- 0x0B (Arm Animation) - анимация руки
- 0x47 (Entity Damage) - нанесение урона

**Handler:**
- [ ] Создать 0x47 handler в protocol/clientbound/play/combat.py

**Пример использования:**
```python
zombie = bot.nearest_hostile()
if zombie:
    await bot.attack(zombie.entity_id)
```

**Проверка:**
- [ ] Файл `combat.py` создан
- [ ] Методы реализованы
- [ ] Handlers добавлены
- [ ] Пакеты отправляются

---

#### Подзадача 2.2: Реализовать swingArm()
**Цель:** Анимация атаки

**Что сделать:**
2.2.1. Добавить метод:
   ```python
   async def swing_arm(self, hand='right')
       """Анимация замаха рукой"""
   ```

**Пакет:** 0x0B (Arm Animation)

**Проверка:**
- [ ] Метод добавлен
- [ ] Пакет отправляется

---

#### Подзадача 2.3: Реализовать useOn()
**Цель:** Использование предмета

**Что сделать:**
2.3.1. Реализовать метод:
   ```python
   async def use_item_on(self, entity_id)
       """Использовать предмет на сущности"""
   ```

**Пакет:** 0x0E (Use Entity)

**Проверка:**
- [ ] Метод реализован
- [ ] Пакет отправляется

---

### Приоритет 3: Vehicle System

#### Подзадача 3.1: Реализовать mount/dismount
**Цель:** Управление транспортом

**Что сделать:**
3.1.1. Создать `protocol/serverbound/play/vehicle.py`
3.1.2. Реализовать методы:
   ```python
   async def mount(self, entity_id)
       """Сесться на транспорт"""
       
   async def dismount()
       """Слезть с транспорта"""
   ```

**Пакеты:**
- 0x17 (Steer Vehicle)
- 0x18 (Player Input)

**Handlers:**
- [ ] Создать 0x17 handler
- [ ] Создать 0x18 handler

**Пример использования:**
```python
boat = bot.nearest_entity(lambda e: e.object_type and 'boat')
if boat:
    await bot.mount(boat.entity_id)
```

**Проверка:**
- [ ] Файл создан
- [ ] Методы реализованы
- [ ] Handlers созданы

---

#### Подзадача 3.2: Реализовать player input
**Цель:** Управление транспортом

**Что сделать:**
3.2.1. Реализовать метод:
   ```python
   async def send_player_input(self, forward=False, backward=False, left=False, right=False, jump=False)
       """Отправить управление игроком"""
   ```

**Пакет:** 0x18 (Player Input)

**Проверка:**
- [ ] Метод реализован
- [ ] Пакет отправляется

---

### Приоритет 4: Entity Events (опционально)

#### Подзадача 4.1: Добавить недостающие entity handlers
**Цель:** Полный coverage entity events

**Что добавить:**
4.1.1. В entities.py добавить handlers:
   ```python
   def entity_hurt(self, source=None):
       """Обработка урона бота"""
   
   def entity_sleep(self):
       """Обработка сна"""
   
   def entity_wake(self):
       """Обработка пробуждения"""
   ```

**Handlers needed:**
- entity_hurt: 0x47
- entity_sleep: pose=2 (metadata)
- entity_wake: pose=2→0 (metadata)

**Проверка:**
- [ ] Handlers добавлены в entities.py
- [ ] Event system работает

---

#### Подзадача 4.2: Добавить equipment events
**Цель:** События экипировки

**Что добавить:**
4.2.1. Handler: entity_equipment (0x48)

**Проверка:**
- [ ] Handler создан
- [ ] События эмитится

---

#### Подзадача 4.3: Добавить effect events
**Цель:** События эффектов

**Что добавить:**
4.3.1. Handlers:
   - entity_effect (0x1F)
   - remove_entity_effect (0x24)

**Проверка:**
- [ ] Handlers созданы
- [ ] События эмитятся

---

### Приоритет 5: Player Info System

#### Подзадача 5.1: Реализовать Player Info Update handler
**Цель:** Обновление информации игрока

**Что сделать:**
5.1.1. Создать handler для 0x40
5.1.2. Парсить:
   - Display name
   - Ping
   - Gamemode
   - Latency
- Listed status

**Что добавить в bot:**
```python
bot.players = {}  # уже есть
bot.uuid_to_username = {}  # уже есть
```

**Проверка:**
- [ ] Handler создан
- [ ] Данные обновляются
- [ ] findPlayer() работает

---

#### Подзадача 5.2: Реализовать player collect/drop events
**Цель:** Подбор предметов

**Что сделать:**
5.2.1. Handlers:
   - 0x14 (Collect Item) - когда бот подбирает предмет
- 0x0F (Spawn Player) - когда игрок заходит
- 0x3F (Remove Entities) - когда игрок выходит

**Проверка:**
- [ ] Handlers созданы
- [ ] События эмитятся

---

### Приоритет 6: Missing Spawn Handlers

#### Подзадача 6.1: Добавить experience orb handler
**Цель:** Подбор опыта

**Что сделать:**
6.1.1. Handler: 0x02

**Что парсить:**
- Count
- Experience orb entity type

**Проверка:**
- [ ] Handler создан
- [ ] Entity создаётся корректно

---

#### Подзадача 6.2: Добав painting handler
**Цель:** Картины

**Что сделать:**
6.2.1. Handler: 0x0A (Spawn Painting)

**Что парсить:**
- Painting ID
- Title
- Position
- Direction

**Проверка:**
- [ ] Handler создан
- [ ] Entity создаётся корректно

---

### Приоритет 7: Block Interaction System

#### Подзадача 7.1: Реализовать place_block()
**Цель:** Установка блоков

**Что сделать:**
7.1.1. Создать `protocol/serverbound/play/block.py`
7.1.2. Реализовать:
   ```python
   async def place_block(self, x, y, z, face=1, hand=0)
       """Поставить блок"""
   
   async def place_block_at(self, x, y, z, face=1)
       """Поставить блок с определённой позиции"""
   ```

**Пакет:** 0x1D (Set Block)
- 0x05 (Block Update)

**Зависимости:**
- mcproto.Buffer
- ProtocolState.PLAY
- block_registry

**Проверка:**
- [ ] Файл создан
- [ ] Методы реализованы
- [ ] Пакеты отправляются

---

#### Подадача 7.2: Реализовать container interaction
**Цель:** Взаимодействие с контейнерами

**Что сделать:**
7.2.1. Реализовать:
   ```python
   async def open_container(self, position)
       """Открыть контейнер"""
   
   async def close_container(self)
       """Закрыть контейнер"""
   ```

**Пакеты:**
- 0x0F (Use Entity на блоке контейнера)
- 0x12 (Close Container)

**Проверка:**
- [ ] Методы реализованы
- [ ] Пакеты отправляются

---

### Приоритет 8: Chat System Enhancement

#### Подзадача 8.1: Улучшить chat signing
**Цель:** Подписанные сообщения для 1.19+

**Что сделать:**
8.1.1. Исследовать Mineflayer chat signing
8.1.2. Реализовать поддержку:
   - Session keys
   - Message signing
   - Chain linking

**Зависимости:**
- crypto библиотека

**Проверка:**
- [ ] Исследование завершено
- [ ] Реализация начата
- [ ] Тесты написаны

---

# СТАТУС ДОРАБОТОК

## Готово (ЕСТЬ в Minepyt):
- ✅ Protocol states
- ✅ Connection flow (base)
- ✅ Keep-Alive
- ✅ Packet handlers (частично)
- ✅ Game state
- ✅ Health
- ✅ Entity dataclass
- ✅ Entity Manager
- ✅ Blocks
- ✅ Digging helpers
- ✅ Inventory basics
- ✅ Crafting system
- ✅ NBT parser
- ✅ Components

## В работе (НУЖНО):
- [ ] Connection layer (NotImplemented)
- [ ] Chat sending (stub)

## Отсутствует (НЕЕСТЬ в Mineflayer):
- [ ] Entity movement (0%)
- [ ] Entity velocity (0%)
- [ ] Combat system (0%)
- [ ] Vehicle system (0%)
- [ ] Player info update handlers (0%)
- [ ] Entity events (15%)
- [ ] Place block (0%)
- [ ] Container interaction (0%)
- [ ] Advanced inventory operations (40%)
- [ ] Advanced crafting (30%)

---

# ОЦЕНКА ТЕКУЩЕГО СОСТОЯНИЯ

**Общий прогресс: ~60-65%**

**Основные блоки отсутствующие:**
1. **Movement/Physics** - 0%
2. **Combat** - 0%
3. **Vehicles** - 0%
4. **Entity interactions** - 30%

**Второстепенные:**
1. **Chat** - не работает подписи
2. **Inventory** - нет drag mode, creative, container sync

---

# ПЛАН РЕАЛИЗАЦИИ

## Фаза 1: Базовое движение (1-2 недели)
**Week 1:**
- [ ] Пакет 0x1B (Player Position)
- [ ] Пакет 0x1D (Position & Rotation)
- [ ] Пакет 0x1C (Entity Velocity)
- [ ] Tests для position

**Week 2:**
- [ ] Пакет 0x0E (Use Entity)
- [ ] Пакет 0x0B (Arm Animation)
- [ ] Tests для взаимодействия

## Фаза 2: Combat (1-2 недели)
**Week 3-4:**
- [ ] Пакет 0x47 (Entity Damage)
- [ ] Пакет 0x0B (Arm Animation)
- [ ] attack() метод
- [ ] use_item() метод
- [ ] Combat тесты

## Фаза 3: Entities advanced (1-2 недели)
**Week 5-6:**
- [ ] entity_handlers.py (все недостающие)
- [ ] Player info tracking
- [ ] Entity events (hurt, sleep, etc.)
- [ ] Experience orbs
- [ ] Paintings

## Фаза 4: Vehicles (1 неделя)
**Week 7:**
- [ ] Пакет 0x17 (Steer Vehicle)
- [ ] Пакет 0x18 (Player Input)
- [ ] mount(), dismount() методы
- [ ] Vehicle handlers

## Фаза 5: Inventory advanced (2-3 недели)
**Week 8-9:**
- [ ] Drag mode (QUICK_CRAFT)
- [ ] Container interaction
- [ ] Creative inventory
- [ ] Auto-sort
- [ ] Item drop/equip
- [ ] Inventory tests

## Фаза 6: Block interaction (1 неделя)
**Week 10:**
- [ ] place_block() метод
- [ ] Container open/close
- [ ] Block interaction tests

## Фаза 7: Advanced crafting (2 недели)
**Week 11-12:**
- [ ] Smithing recipes
- [ ] Special recipes
- [ ] Furnace types
- [ ] Auto-craft helper

## Фаза 8: Chat (1 неделя)
**Week 13:**
- [ ] Message signing
- [ ] Whisper
- [ ] Commands

---

# ВРЕМЕННАЯЯ

1. Mineflayer использует **пакетную архитектуру** - чёткое разделение по типам
2. Minepyt использует **монолит protocol.py** - 1400 строк в одном файле
3. Mineflayer имеет **40+ плагинов** - каждый = отдельная ответственность
4. Mineflayer = 10+ лет развития
5. Minepyt = молодой проект (несколько месяцев)

---

# ПУТЬ К 100%

Чтобы сравняться с Mineflayer по функционалу, Minepyt нужно:
1. ✅ Сохранить то что есть (NBT, Components, Recipes)
2. ⚡️ Улучшить архитектуру (разбить protocol.py)
3. ⚠️ Реализовать Movement
4. ⚠️ Реализовать Combat
5. ⚠️ Реализовать Vehicles
6. ⚠️ Реализовать Advanced Inventory
7. ⚠️ Реализовать Block Interactions
8. ⚠️ Улучшить Chat

**Примерное время до 100%:** 8-12 месяцев при работе 5-10 часов в неделю
