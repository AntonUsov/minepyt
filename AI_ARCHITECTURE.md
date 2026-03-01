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

---

## Future Enhancements

### Обзор будущих улучшений

Этот раздел описывает планируемые расширения архитектуры AI системы.

### Приоритеты реализации

1. **Visual Debugging** (Фаза 7, Средняя) - упростит отладку и разработку
2. **Risk Assessment** (Фаза 7, Средняя) - улучшит поведение бота
3. **Inter-Bot Communication** (Фаза 8, Средняя) - координация ботов
4. **HTN Planner** (Фаза 9, Высокая) - сложные иерархические задачи
5. **ML Prediction Layer** (Фаза 10, Высокая) - продвинутый ИИ с машинным обучением

---

### 4. Visual Debugging System (Flask)

**Фаза:** 7  
**Приоритет:** Средний  
**Сложность:** Средняя  
**Время реализации:** ~16 часов

#### Назначение

Веб-интерфейс для визуализации работы AI системы бота в реальном времени. Позволяет видеть:
- Состояние всех слоёв движения
- Данные сенсоров
- Позицию бота на карте
- Логи событий
- Производительность

#### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Debug Server                     │
│                    (minepyt/ai/debug/)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │               WebSocket Real-time API                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │  │
│  │  │ Sensors  │  │Movement  │  │Events    │         │  │
│  │  │ Stream   │  │Stream    │  │Stream    │         │  │
│  │  └──────────┘  └──────────┘  └──────────┘         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │              REST API (Query State)                         │  │
│  │  GET  /api/state      - Полное состояние бота                │  │
│  │  GET  /api/layers     - Состояние слоёв движения             │  │
│  │  GET  /api/sensors    - Данные сенсоров                     │  │
│  │  GET  /api/logs       - Логи событий                        │  │
│  │  GET  /api/perf       - Производительность                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │              Static Web UI (HTML/JS)                         │  │
│  │  /               - Главная страница                         │  │
│  │  /map            - Карта местности                          │  │
│  │  /layers         - Визуализация слоёв                       │  │
│  │  /sensors        - Данные сенсоров                          │  │
│  │  /logs           - Логи событий                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │   Bot (SmartBot)   │
                   └────────────────────┘
```

#### Структура файлов

```
minepyt/ai/debug/
├── __init__.py
├── app.py                    # Flask приложение
├── socket_handler.py         # WebSocket обработчики
├── api.py                    # REST API эндпоинты
├── state_collector.py        # Сбор состояния с бота
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       ├── layers.js
│       ├── map.js
│       └── sensors.js
└── templates/
    ├── index.html            # Главная страница
    ├── layers.html           # Визуализация слоёв
    ├── map.html              # Карта
    ├── sensors.html          # Данные сенсоров
    └── logs.html             # Логи
```

#### API Интерфейсы

##### WebSocket потоки

```python
# minepyt/ai/debug/socket_handler.py

class WebSocketManager:
    """Управление WebSocket подключениями"""
    
    async def broadcast_layers(self, state: Dict):
        """Отправка состояния слоёв"""
        await self.websocket.send_json({
            "type": "layers_update",
            "data": {
                "layer4_goal": state.get("goal_vector"),
                "layer3_tactical": state.get("tactical_vectors"),
                "layer2_avoid": state.get("avoid_vectors"),
                "layer1_physics": state.get("physics_vector"),
                "final_vector": state.get("final_vector")
            }
        })
    
    async def broadcast_sensors(self, sensors: SensorArray):
        """Отправка данных сенсоров"""
        await self.websocket.send_json({
            "type": "sensors_update",
            "data": {
                "threats": [self._serialize_threat(t) for t in sensors.threats],
                "interests": [self._serialize_interest(i) for i in sensors.interests],
                "terrain": sensors.terrain
            }
        })
    
    async def broadcast_position(self, x, y, z, yaw, pitch):
        """Отправка позиции бота"""
        await self.websocket.send_json({
            "type": "position_update",
            "data": {"x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch}
        })
    
    async def broadcast_event(self, event_type: str, data: Dict):
        """Отправка события"""
        await self.websocket.send_json({
            "type": "event",
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        })
```

##### REST API

```python
# minepyt/ai/debug/api.py

from flask import jsonify, request

@app.route('/api/state')
def get_state():
    """Полное состояние бота"""
    return jsonify({
        "position": collector.get_position(),
        "health": collector.get_health(),
        "hunger": collector.get_hunger(),
        "current_task": collector.get_current_task(),
        "inventory": collector.get_inventory()
    })

@app.route('/api/layers')
def get_layers():
    """Состояние слоёв движения"""
    return jsonify(collector.get_layers_state())

@app.route('/api/sensors')
def get_sensors():
    """Данные сенсоров"""
    return jsonify(collector.get_sensors_data())

@app.route('/api/logs')
def get_logs():
    """Логи событий"""
    limit = request.args.get('limit', 100, type=int)
    return jsonify(collector.get_logs(limit))

@app.route('/api/perf')
def get_performance():
    """Производительность"""
    return jsonify(collector.get_performance_stats())
```

#### Сбор состояния с бота

```python
# minepyt/ai/debug/state_collector.py

class StateCollector:
    """Сбор состояния бота для визуализации"""
    
    def __init__(self, bot: SmartBot):
        self.bot = bot
        self.ws_manager: WebSocketManager = None
        self.log_buffer: List[Dict] = []
        self.max_log_size = 1000
    
    def set_websocket_manager(self, manager: WebSocketManager):
        """Установить WebSocket менеджер"""
        self.ws_manager = manager
    
    def on_layers_update(self, layer_state: Dict):
        """Вызывается при обновлении слоёв"""
        if self.ws_manager:
            asyncio.create_task(self.ws_manager.broadcast_layers(layer_state))
    
    def on_sensors_update(self, sensors: SensorArray):
        """Вызывается при обновлении сенсоров"""
        if self.ws_manager:
            asyncio.create_task(self.ws_manager.broadcast_sensors(sensors))
    
    def on_position_update(self, x, y, z, yaw, pitch):
        """Вызывается при изменении позиции"""
        if self.ws_manager:
            asyncio.create_task(self.ws_manager.broadcast_position(x, y, z, yaw, pitch))
    
    def log_event(self, event_type: str, data: Dict):
        """Записать событие"""
        entry = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        self.log_buffer.append(entry)
        
        # Лимит буфера
        if len(self.log_buffer) > self.max_log_size:
            self.log_buffer.pop(0)
        
        # Отправить по WebSocket
        if self.ws_manager:
            asyncio.create_task(self.ws_manager.broadcast_event(event_type, data))
```

#### Flask приложение

```python
# minepyt/ai/debug/app.py

from flask import Flask, render_template
from flask_socketio import SocketIO

class DebugServer:
    """Flask сервер для отладки"""
    
    def __init__(self, bot: SmartBot, host='0.0.0.0', port=5000):
        self.bot = bot
        self.host = host
        self.port = port
        
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.state_collector = StateCollector(bot)
        self.ws_manager = WebSocketManager()
        self.state_collector.set_websocket_manager(self.ws_manager)
        
        self._setup_routes()
        self._setup_socketio()
    
    def _setup_routes(self):
        """Настройка роутов"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/layers')
        def layers():
            return render_template('layers.html')
        
        @self.app.route('/map')
        def map_view():
            return render_template('map.html')
        
        @self.app.route('/sensors')
        def sensors():
            return render_template('sensors.html')
        
        @self.app.route('/logs')
        def logs():
            return render_template('logs.html')
    
    def _setup_socketio(self):
        """Настройка WebSocket"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected: {request.sid}")
            # Отправить начальное состояние
            self.socketio.emit('initial_state', self.state_collector.get_full_state())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"Client disconnected: {request.sid}")
    
    def run(self, debug=True):
        """Запустить сервер"""
        print(f"Debug server running on http://{self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)
```

#### Интеграция с SmartBot

```python
# minepyt/ai/__init__.py

from .debug import DebugServer

class SmartBot:
    """Умный бот с AI"""
    
    def __init__(self, config):
        # ... существующая инициализация ...
        
        # Debug сервер
        self.debug_server = None
        if config.get('debug_server', False):
            self.debug_server = DebugServer(
                self,
                host=config.get('debug_host', '0.0.0.0'),
                port=config.get('debug_port', 5000)
            )
    
    def start_debug_server(self):
        """Запустить debug сервер"""
        if self.debug_server:
            self.debug_server.run()
```

#### Визуализация слоёв (HTML/JS)

```html
<!-- minepyt/ai/debug/templates/layers.html -->

<!DOCTYPE html>
<html>
<head>
    <title>Movement Layers</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>Movement Layers Visualization</h1>
        
        <div class="layers-container">
            <div class="layer" id="layer4">
                <h3>Layer 4: GOAL</h3>
                <div class="vector-display" id="goal-vector"></div>
            </div>
            
            <div class="layer" id="layer3">
                <h3>Layer 3: TACTICAL</h3>
                <div class="vector-list" id="tactical-vectors"></div>
            </div>
            
            <div class="layer" id="layer2">
                <h3>Layer 2: LOCAL_AVOID</h3>
                <div class="vector-list" id="avoid-vectors"></div>
            </div>
            
            <div class="layer" id="layer1">
                <h3>Layer 1: PHYSICS</h3>
                <div class="vector-display" id="physics-vector"></div>
            </div>
            
            <div class="final-result" id="final-vector">
                <h2>Final Vector</h2>
                <div class="vector-display" id="final-vector-display"></div>
            </div>
        </div>
        
        <canvas id="vector-canvas" width="400" height="400"></canvas>
    </div>
    
    <script src="/static/js/layers.js"></script>
</body>
</html>
```

```javascript
// minepyt/ai/debug/static/js/layers.js

const socket = io();
const canvas = document.getElementById('vector-canvas');
const ctx = canvas.getContext('2d');

socket.on('layers_update', (data) => {
    updateLayerDisplay('goal-vector', data.data.layer4_goal);
    updateLayerDisplay('physics-vector', data.data.layer1_physics);
    updateVectorList('tactical-vectors', data.data.layer3_tactical);
    updateVectorList('avoid-vectors', data.data.layer2_avoid);
    updateLayerDisplay('final-vector-display', data.data.final_vector);
    
    drawVectors(data.data);
});

function updateLayerDisplay(elementId, vector) {
    const el = document.getElementById(elementId);
    if (vector) {
        el.textContent = `X: ${vector.dx.toFixed(3)}, Y: ${vector.dy.toFixed(3)}, Z: ${vector.dz.toFixed(3)}`;
    }
}

function drawVectors(data) {
    // Очистить canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const scale = 100;
    
    // Нарисовать все векторы
    drawArrow(centerX, centerY, data.layer4_goal, '#00ff00', 'GOAL');
    drawArrows(centerX, centerY, data.layer3_tactical, '#ffff00', 'TACTICAL');
    drawArrows(centerX, centerY, data.layer2_avoid, '#ff0000', 'AVOID');
    drawArrow(centerX, centerY, data.layer1_physics, '#00ffff', 'PHYSICS');
    drawArrow(centerX, centerY, data.final_vector, '#ffffff', 'FINAL', 3);
}

function drawArrow(cx, cy, vector, color, label, width=2) {
    if (!vector) return;
    
    const endX = cx + vector.dx * scale;
    const endY = cy + vector.dz * scale;  // Используем dz как Y
    
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.moveTo(cx, cy);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    ctx.fillStyle = color;
    ctx.font = '12px Arial';
    ctx.fillText(label, endX + 5, endY);
}
```

#### Пример использования

```python
from minepyt.ai import SmartBot

async def main():
    bot = await SmartBot({
        "host": "localhost",
        "port": 25565,
        "username": "SmartBot",
        "debug_server": True,   # Включить debug сервер
        "debug_host": "0.0.0.0",
        "debug_port": 5000
    })
    
    # Запустить debug сервер в отдельном потоке
    import threading
    server_thread = threading.Thread(target=bot.start_debug_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Бот работает
    await bot.stay_alive(duration=300.0)

asyncio.run(main())
```

#### Зависимости

```
Flask==3.0.0
flask-socketio==5.3.6
python-socketio==5.11.0
```

#### Этапы реализации

1. **Базовый Flask сервер** (4 часа)
   - Создать структуру файлов
   - Настроить Flask приложение
   - Базовые HTML шаблоны

2. **WebSocket стриминг** (4 часа)
   - WebSocket менеджер
   - Интеграция с SmartBot
   - Потоки данных (слои, сенсоры, позиция)

3. **REST API** (2 часа)
   - API эндпоинты
   - StateCollector

4. **Визуализация слоёв** (3 часа)
   - Canvas отрисовка векторов
   - Real-time обновления

5. **Карта и сенсоры** (2 часа)
   - 2D карта местности
   - Отображение угроз и интересов

6. **Логи и события** (1 час)
   - Логирование событий
   - Веб интерфейс логов

---

### 1. ML Prediction Layer

**Фаза:** 10  
**Приоритет:** Низкий  
**Сложность:** Высокая  
**Время реализации:** ~40 часов

#### Назначение

Использование машинного обучения для предсказания действий:
- Поведение врагов
- Оптимальные маршруты
- Результаты действий

#### Компоненты

```
MLPredictionLayer
├── EnemyBehaviorPredictor    # Предсказание поведения врагов
├── RouteOptimizer             # Оптимизация маршрутов
├── ActionOutcomePredictor    # Предсказание результатов действий
└── ModelTrainer              # Обучение моделей
```

---

### 2. Risk Assessment Module

**Фаза:** 7  
**Приоритет:** Средний  
**Сложность:** Средняя  
**Время реализации:** ~20 часов

#### Назначение

Модуль оценки рисков для принятия решений:
- Оценка угрозы
- Расчет вероятности успеха
- Выбор наименее рискованного действия

#### Компоненты

```
RiskAssessor
├── ThreatEvaluator           # Оценка угроз
├── ProbabilityCalculator     # Расчет вероятностей
└── RiskOptimizer             # Оптимизация по риску
```

---

### 3. Inter-Bot Communication

**Фаза:** 8  
**Приоритет:** Средний  
**Сложность:** Средняя  
**Время реализации:** ~24 часа

#### Назначение

Координация нескольких ботов:
- Обмен информацией
- Распределение задач
- Синхронизация действий

#### Компоненты

```
BotNetwork
├── DiscoveryProtocol         # Обнаружение ботов
├── MessageBus                # Шина сообщений
├── TaskDistributor          # Распределитель задач
└── StateSynchronizer        # Синхронизация состояния
```

---

### 5. HTN Planner

**Фаза:** 9  
**Приоритет:** Низкий  
**Сложность:** Высокая  
**Время реализации:** ~32 часа

#### Назначение

Hierarchical Task Network планировщик для сложных задач:
- Иерархическое разложение задач
- Методы (methods) для задач
- Планирование с ограничениями

#### Компоненты

```
HTNPlanner
├── TaskDecomposer           # Разложение задач
├── MethodSelector           # Выбор методов
├── Planner                  # Планировщик
└── HTNLibrary              # Библиотека задач и методов
```

---

### Общий порядок реализации

**Phase 7 (Immediate value):**
1. Visual Debugging System → упростит отладку всех компонентов
2. Risk Assessment Module → улучшит поведение в опасных ситуациях

**Phase 8 (Coordination):**
3. Inter-Bot Communication → координация ботов

**Phase 9 (Advanced planning):**
4. HTN Planner → сложные многошаговые задачи

**Phase 10 (Advanced AI):**
5. ML Prediction Layer → машинное обучение для предсказаний

