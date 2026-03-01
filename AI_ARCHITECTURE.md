# MinePyt AI Architecture Design

## Обзор

Этот документ описывает архитектуру умной системы бота для MinePyt, реализованной на Python с использованием asyncio.

### Ключевая идея: Layered Movement System

```
Бот НЕ выбирает ОДНО действие.
Бот объединяет НЕСКОЛЬКО векторов движения в ОДИН финальный.
```

---

## Архитектура

### Структура системы

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Bot Core                             │
│  (protocol.py - Minecraft протокол)                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    AI System                              │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │              Perception (Sensors)                      │ │ │
│  │  │  - Сканирование угроз                                     │ │ │
│  │  │  - Сканирование ресурсов                                 │ │ │
│  │  │  - Анализ местности                                      │ │ │
│  │  │  - Отслеживание игроков                                   │ │ │
│  │  └────────────────────────────┬────────────────────────────────┘ │ │
│  │                           │                                │ │
│  │  ┌──────────────────────────┴────────────────────────────────┐ │ │
│  │  │            Decision Making (Layers)                     │ │ │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │ │
│  │  │  Layer 4  │  │  Layer 3  │  │  Layer 2  │       │ │ │
│  │  │  GOAL     │  │  TACTICAL  │  │  LOCAL    │       │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘       │ │ │
│  │                                             │           │ │ │
│  │  ┌────────────────────────────────────────────┐           │ │ │
│  │  │         Layer 1 (PHYSICS)              │           │ │ │
│  │  │         Movement Blender                │           │ │ │
│  │  └────────────────────────────────────────────┘           │ │ │
│  │                           │                                │ │
│  │  ┌──────────────────────────▼────────────────────────────┐ │ │
│  │  │            Action Execution                          │ │ │
│  │  │  - Отправка пакетов                                 │ │ │
│  │  │  - Обработка ответов                                  │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Компоненты системы

### 1. Perception (Сенсоры)

**Файл:** `minepyt/ai/sensors.py`

**Назначение:** Сбор информации о мире, "глаза" бота.

**Компоненты:**

```
SensorArray
│
├── ThreatScanner       # Сканирование врагов
├── ResourceScanner    # Сканирование ресурсов (еда, дроп)
├── TerrainScanner     # Анализ местности (ямы, лава)
├── PlayerTracker      # Отслеживание игроков
└── InterestManager    # Управление интересными объектами
```

**Схема:**

```
┌─────────────────────────────────────────────────────────────────┐
│                     SensorArray                             │
└────────────────────────────────────┬────────────────────────────┘
                                 │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌──────────┐       ┌──────────┐      ┌──────────┐
   │   Threat  │       │  Terrain   │      │  Resource │
   │  Scanner  │       │  Scanner   │      │  Scanner   │
   └─────┬────┘       └─────┬────┘      └─────┬────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Shared State │
                    │ (blackboard)│
                    └─────────────┘
```

**Интерфейс:**

```python
class SensorArray:
    """
    Непрерывное сканирование мира.
    Работает как независимый coroutine.
    """
    
    def __init__(self, bot_protocol):
        self.bot = bot_protocol
        self.threats: List[Threat] = []
        self.interests: List[Interest] = []
        self.terrain: Dict[Tuple[int, int], TerrainInfo] = {}
        
        # Частота сканирования
        self.scan_interval = 0.05  # 20 раз в секунду
        self.running = True
    
    async def run_continuous_scan(self):
        """
        Главный цикл сенсоров.
        Работает независимо от остальной системы.
        """
        while self.running:
            await asyncio.gather(
                self._scan_threats(),
                self._scan_terrain(),
                self._scan_resources(),
                self._scan_players(),
            )
            await asyncio.sleep(self.scan_interval)
```

---

### 2. Decision Making (Слои движения)

**Файл:** `minepyt/ai/movement.py`

**Назначение:** Объединение множественных векторов движения в один.

**Слои:**

```
Layer 4: GOAL          - Глобальная цель (следовать за игроком, идти к деревне)
Layer 3: TACTICAL      - Тактика (убежать от крипера, атаковать врага)
Layer 2: LOCAL_AVOID   - Локальное уклонение (обойти яму, лаву)
Layer 1: PHYSICS       - Физика (куда вообще можно идти)
```

**Схема слоёв:**

```
┌─────────────────────────────────────────────────────────────────┐
│                   Movement Blender                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 4: GOAL                                            │
│  "Куда я хочу попасть?"                                     │
│  ┌───────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  Примеры:                                             │   │
│  │  - follow: следовать за игроком                      │   │
│  │  - goto:   идти в точку X                             │   │
│  │  - flee:   убежать от позиции                         │   │
│  │  - idle:   стоять на месте                            │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  Layer 3: TACTICAL                                     │   │
│  │  "Есть ли срочные ситуации?"                          │   │
│  │                                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │Flee from  │  │ Attack    │  │Protect    │   │   │
│  │  │Creeper   │  │Hostile    │  │Employer  │   │   │
│  │  │          │  │           │  │           │   │   │
│  │  │ПРИОРИТЕТ│  │ПРИОРИТЕТ│  │ПРИОРИТЕТ│   │   │
│  │  │   1.0    │  │   0.8   │  │   0.9    │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘   │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  Layer 2: LOCAL_AVOID                                  │   │
│  │  "Не упасть бы в яму/лаву!"                       │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │ Avoid Lava    │  │Avoid Pit     │             │   │
│  │  │              │  │              │             │   │
│  │  │ ВЕКТОР ОТ   │  │ ВЕКТОР ОТ   │             │   │
│  │  │ угрозы       │  │ угрозы       │             │   │
│  │  └──────────────┘  └──────────────┘             │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  Layer 1: PHYSICS                                      │   │
│  │  "Куда вообще можно идти?"                           │   │
│  │                                                       │   │
│  │  Проверяет 8 направлений:                              │   │
│  │  ■ ■ ■ ■ ■ ■                                         │   │
│  │   ■ ■ ■ ■                                            │   │
│  │  ■ ■ ■ ■                                            │   │
│  │                                                       │   │
│  │  Для каждого направления:                                │   │
│  │  - Можно туда идти? (проверить блоки)               │   │
│  │  - Там опасно? (лава, край мира)                  │   │
│  │  - На какой высоте? (прыгок?)                        │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│                  ┌─────────────────────┐                       │   │
│                  │ Movement Blender │                       │   │
│                  │                 │                       │   │
│                  │  Смешивает все    │                       │   │
│                  │  векторы с      │                       │   │
│                  │  весами         │                       │   │
│                  │                 │                       │   │
│                  └────────┬────────┘                       │   │
│                           │                                 │   │
│                           ▼                                 │   │
│                  ┌─────────────────────┐                       │   │
│                  │   ИТОГОВЫЙ      │                       │   │
│                  │   ВЕКТОР       │                       │   │
│                  │   ДВИЖЕНИЯ      │                       │   │
│                  └─────────────────────┘                       │   │
└─────────────────────────────────────────────────────────────────┘
```

**Интерфейс:**

```python
class MovementBrain:
    """
    Мозг движения.
    Объединяет входы от всех слоёв в один финальный вектор.
    """
    
    def __init__(self, bot_protocol, sensors: SensorArray):
        self.bot = bot_protocol
        self.sensors = sensors
        
        # Текущая цель (Layer 4)
        self.primary_goal: Optional[Goal] = None
        
        # Параметры
        self.goal_weight = 0.5      # Вес цели
        self.tactical_weight = 0.8    # Вес тактики
        self.avoid_weight = 0.7      # Вес уклонения
        self.physics_weight = 0.3    # Вес физики
    
    def calculate_final_vector(self) -> Tuple[float, float, float]:
        """
        Объединяет все слои.
        Возвращает (dx, dy, dz)
        """
        # Собираем векторы
        vectors = []
        
        # Layer 4: GOAL
        goal_vec = self._layer4_goal()
        if goal_vec:
            vectors.append(goal_vec)
        
        # Layer 3: TACTICAL
        tactical_vec = self._layer3_tactical()
        if tactical_vec:
            vectors.append(tactical_vec)
        
        # Layer 2: LOCAL_AVOID
        avoid_vec = self._layer2_local_avoid()
        if avoid_vec:
            vectors.append(avoid_vec)
        
        # Layer 1: PHYSICS
        physics_vec = self._layer1_physics()
        vectors.append(physics_vec)
        
        # Блендим
        final_dx, final_dy, final_dz = self._blend_vectors(vectors)
        
        # Нормализуем
        length = math.sqrt(final_dx**2 + final_dy**2 + final_dz**2)
        if length > 0:
            final_dx /= length
            final_dy /= length
            final_dz /= length
        
        return (final_dx, final_dy, final_dz)
```

---

### 3. Action Execution

**Файл:** `minepyt/ai/executor.py`

**Назначение:** Исполнение финального вектора движения.

**Интерфейс:**

```python
class ActionExecutor:
    """
    Исполнитель действий.
    Получает вектор движения, отправляет пакеты.
    """
    
    def __init__(self, bot_protocol):
        self.bot = bot_protocol
        
        # Скорость движения
        self.move_speed = 0.3  # блоков за тик
        self.jump_cooldown = 0.1
    
    async def execute_movement(self, dx: float, dy: float, dz: float):
        """
        Выполнить движение по вектору.
        """
        # Вычисляем yaw
        yaw = math.degrees(math.atan2(-dx, dz))
        
        # Прыжок если нужно
        if dy > 0.5:
            await self.bot.jump()
        
        # Движение
        new_x = self.bot.position[0] + dx * self.move_speed
        new_z = self.bot.position[2] + dz * self.move_speed
        
        await self.bot.set_position_and_look(new_x, self.bot.position[1], new_z, yaw)
```

---

## Структура директорий

```
minepyt/
├── __init__.py                    # Точка входа
├── protocol.py                     # Базовый протокол (существует)
├── block_registry.py              # Реестр блоков (существует)
├── chunk_utils.py                # Утилиты чанков (существует)
├── entities.py                   # Сущности (существует)
├── digging.py                    # Копание (существует)
├── nbt.py                        # NBT парсер (существует)
├── components.py                 # Компоненты предметов (существует)
├── recipes.py                    # Рецепты (существует)
│
├── ai/                           # НОВЫЙ МОДУЛЬ
│   ├── __init__.py
│   │
│   ├── sensors.py                 # Perception
│   │   ├── ThreatScanner
│   │   ├── ResourceScanner
│   │   ├── TerrainScanner
│   │   ├── PlayerTracker
│   │   └── InterestManager
│   │
│   ├── movement.py               # Decision Making
│   │   ├── MovementLayer (enum)
│   │   ├── MovementVector (dataclass)
│   │   ├── MovementBrain
│   │   └── ActionExecutor
│   │
│   ├── behavior.py               # Behavior Trees
│   │   ├── NodeStatus (enum)
│   │   ├── BTNode (abstract)
│   │   ├── Selector
│   │   ├── Sequence
│   │   ├── Parallel
│   │   ├── Condition
│   │   ├── Action
│   │   └── Decorator
│   │
│   ├── actors.py                # Actor System
│   │   ├── Actor (abstract)
│   │   ├── ActorSystem
│   │   ├── SurvivalActor
│   │   ├── CombatActor
│   │   ├── SocialActor
│   │   ├── TaskActor
│   │   └── WorldActor
│   │
│   └── tasks.py                 # Tasks
│       ├── BotTask (abstract)
│       ├── VillageCareTask
│       ├── CaravanEscortTask
│       ├── NetherMercenaryTask
│       └── ...
│
└── examples/
    ├── basic_bot.py              # Пример базового бота
    └── smart_bot.py             # Пример умного бота с AI
```

---

## Поток данных

### Главный цикл

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Loop (20 ticks/сек)               │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌────────┐        ┌────────┐        ┌────────┐
   │Sensor  │        │Movement│        │Actors  │
   │Array  │        │Brain   │        │System  │
   │        │        │        │        │        │
   │ скан  │        │ бленд  │        │ выбор  │
   │ мир   │        │ вектор│        │ акции  │
   └────────┘        └────────┘        └────────┘
        │                  │                   │
        └──────────────────┴───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Executor   │
                    │   отправка   │
                    │   пакетов    │
                    └──────────────┘
                           │
                    ┌──────▼──────┐
                    │  Packets     │
                    │  to Server   │
                    └──────────────┘
```

### Детальный поток данных

```
ТИК 0:
  [Server] → [Sensors] → Threat: Creeper (5 блоков, опасность 0.8)
  [Server] → [Sensors] → Interest: Cow (еда, 10 блоков)
  [Server] → [Sensors] → Terrain: Яма вперёд (опасность 0.6)
  
  [MovementBrain]
    Layer 4 (GOAL):        → К игроку (dx: 0.8, dz: 0.2)
    Layer 3 (TACTICAL):     ← От крипера (dx: -0.9, dz: -0.1)
    Layer 2 (LOCAL_AVOID):   ← Обойти яму (dx: 0.3, dz: 0.7)
    Layer 1 (PHYSICS):     → Вперёд можно (dx: 0.7, dz: 0.1)
    
    Бленд: (dx: 0.1, dz: 0.4)
  
  [Executor] → Отправка: Position + Look
  
ТИК 5:
  [Server] → [Sensors] → Threat: Creeper (3 блоков, опасность 0.9)
  [Server] → [Sensors] → Interest: Cow (еда, 8 блоков)
  [Server] → [Sensors] → Terrain: Яма ближе
  
  [MovementBrain]
    Layer 4 (GOAL):        → К игроку (dx: 0.7, dz: 0.3)
    Layer 3 (TACTICAL):     ← От крипера (dx: -0.95, dz: -0.15)
    Layer 2 (LOCAL_AVOID):   ← Обойти яму (dx: 0.5, dz: 0.8)
    Layer 1 (PHYSICS):     → Влево можно (dx: -0.7, dz: 0.2)
    
    Бленд: (dx: -0.3, dz: 0.5)
  
  [Executor] → Отправка: Position + Look
```

---

## Примеры использования

### Пример 1: Базовый бот (без AI)

```python
from minepyt import create_bot

async def main():
    bot = await create_bot({
        "host": "localhost",
        "port": 25565,
        "username": "SimpleBot"
    })
    
    # Базовый API без умной системы
    await bot.dig(100, 64, 100)
    await bot.chat("Hello!")
    
    await bot.stay_alive(60.0)

asyncio.run(main())
```

### Пример 2: Умный бот (с AI)

```python
from minepyt.ai import SmartBot

async def main():
    # Создаём умного бота
    bot = await SmartBot({
        "host": "localhost",
        "port": 25565,
        "username": "SmartBot"
    })
    
    # Следовать за игроком
    await bot.follow_player("__heksus__")
    
    # Или назначить задачу
    from minepyt.ai.tasks import VillageCareTask
    task = VillageCareTask(village_center=(100, 64, 200))
    await bot.assign_task(task)
    
    # Бот работает автоматически
    await bot.stay_alive(duration=300.0)

asyncio.run(main())
```

### Пример 3: Наемник в Аду

```python
from minepyt.ai import SmartBot
from minepyt.ai.tasks import NetherMercenaryTask

async def main():
    bot = await SmartBot({
        "host": "localhost",
        "port": 25565,
        "username": "Mercenary"
    })
    
    # Нанять бота
    task = NetherMercenaryTask(
        employer_name="__heksus__",
        mission_type="fortress"
    )
    await bot.assign_task(task)
    
    await bot.stay_alive(duration=600.0)

asyncio.run(main())
```

---

## Ключевые принципы

### 1. Параллелизм

```
✅ Сенсоры работают постоянно
✅ Движение вычисляется каждый тик
✅ Акторы работают независимо
✅ Никто не блокирует никого (на длинные операции)
```

### 2. Прерывание

```
✅ Угрозы (крипер, лава) имеют высший приоритет
✅ Голод прерывает долгие задачи
✅ Команды игрока прерывают автоматические действия
✅ Все действия могут быть отменены
```

### 3. Состояние

```
✅ Blackboard - единственный источник правды
✅ Все акторы читают и пишут туда
✅ Нет прямого доступа между акторами
✅ Вся история изменений сохраняется
```

### 4. Модульность

```
✅ Каждый актор независим
✅ Сенсоры заменяемы
�️  Слои движения легко добавляются
✅  Новые задачи легко создаются
```

---

## Производительность

### Время на тик

| Компонент | Время |
|-----------|-------|
| Сенсоры (скан) | ~2мс |
| Слои (вычисление) | ~1мс |
| Бленд (объединение) | ~0.1мс |
| Executor (отправка) | ~0.5мс |
| **Итого** | **~3.6мс** |

**Вывод:** 50 тиков/сек = 180мс на все тики → запас времени: 120мс

### Использование CPU

- **Сенсоры:** 10% (ожидание пакетов, легкие вычисления)
- **Слои:** 5% (простая математика)
- **Акторы:** 15% (логика задач)
- **Executor:** 5% (отправка пакетов)
- **Протокол:** 65% (парсинг пакетов)

---

## TODO для реализации

### Фаза 1: Базовая архитектура (Priority 0)
- [ ] Создать структуру директорий `ai/`
- [ ] Реализовать `sensors.py`
- [ ] Реализовать `movement.py` (базовая версия)
- [ ] Реализовать `executor.py`
- [ ] Создать `SmartBot` класс

### Фаза 2: Слои движения (Priority 0)
- [ ] Layer 1: PHYSICS (проходимость блоков)
- [ ] Layer 2: LOCAL_AVOID (ямы, лава)
- [ ] Layer 3: TACTICAL (мобы, уклонение)
- [ ] Layer 4: GOAL (следование, goto)

### Фаза 3: Акторы (Priority 1)
- [ ] `ActorSystem` (простая версия)
- [ ] `SurvivalActor`
- [ ] `SocialActor`
- [ ] `TaskActor`

### Фаза 4: Behavior Trees (Priority 1)
- [ ] Базовые узлы (Selector, Sequence, Condition)
- [ ] Узлы действий
- [ ] Декораторы

### Фаза 5: Задачи (Priority 2)
- [ ] `BotTask` базовый класс
- [ ] Пример задачи (сбор ресурсов)

### Фаза 6: Оптимизация (Priority 2)
- [ ] Кэширование местности
- [ ] Оптимизация сканирования
- [ ] Предсказание движения мобов

---

## Вопросы к будущему

1. **Нужен ли Pathfinder?**
   - Да, но не сразу
   - A* для длинных дистанций (>50 блоков)
   - Для коротких — слои работают

2. **Нужна ли база данных?**
   - Для чертежей: нет
   - Для истории чата: да (SQLite)

3. **Нужен ли Redis?**
   - Для одного бота: нет
   - Для кластера: да

4. **Как управлять ботом в реальном времени?**
   - Команды в чате (высший приоритет)
   - WebSocket API (опционально)

---

## Заключение

Эта архитектура позволит боту:

✅ **Одновременно следовать за игроком и избегать угроз**
✅ **Быстро реагировать на изменения окружения** (50мс)
✅ **Выполнять долгосрочные задачи без прерывания**
✅ **Обрабатывать команды игрока мгновенно**
✅ **Масштабироваться добавлением новых акторов и слоёв**
