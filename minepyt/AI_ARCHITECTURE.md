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
│  │                           │                                │ │ │
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
└────────────────────────────┬────────────────────────────┘
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
        self.scan_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запустить сканирование"""
        if self.running:
            return
        
        self.running = True
        self.scan_task = asyncio.create_task(self._run_scan_loop())
    
    async def stop(self):
        """Остановить сканирование"""
        self.running = False
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
    
    async def _run_scan_loop(self):
        """Главный цикл сканирования"""
        while self.running:
            try:
                await asyncio.gather(
                    self._scan_threats(),
                    self._scan_terrain(),
                    self._scan_resources(),
                    self._scan_players(),
                    return_exceptions=True
                )
            except Exception as e:
                # Игнорируем ошибки, продолжаем работу
                pass
            
            await asyncio.sleep(self.scan_interval)
    
    async def _scan_threats(self):
        """Сканировать угрозы"""
        self.threats.clear()
        pos = self.bot.position
        
        if not pos:
            return
        
        # Сканируем мобов-врагов
        hostile_entities = self.bot.nearest_hostile(self.threat_scan_range)
        if hostile_entities:
            dist = hostile_entities.distance_to(pos)
            threat_level = 1.0 - (dist / self.threat_scan_range)
            self.threats.append(Threat(
                entity=hostile_entities,
                position=hostile_entities.position,
                threat_level=threat_level,
                threat_type=ThreatType.HOSTILE
            ))
        
        # Сканируем окружение на опасности
        self._check_environmental_threats(pos)
    
    def _check_environmental_threats(self, pos):
        """Проверить лаву, обрывы, огонь"""
        # TODO: Реализовать проверку блоков на опасности
        pass
    
    async def _scan_terrain(self):
        """Анализировать проходимость местности"""
        pos = self.bot.position
        
        if not pos:
            return
        
        # TODO: Реализовать сканирование местности
        pass
    
    async def _scan_resources(self):
        """Искать ресурсы (еда, дропы)"""
        self.interests.clear()
        
        # Ищем еду если голодны
        if self.bot.food < 15:
            animals = self.bot.find_entities(
                max_distance=self.resource_scan_range
            )
            
            for animal in animals[:5]:  # Ограничиваем
                dist = animal.distance_to(self.bot.position)
                priority = 0.7 - (dist / self.resource_scan_range)
                self.interests.append(Interest(
                    position=animal.position,
                    priority=priority,
                    interest_type="food",
                    entity=animal
                ))
        
        # Ищем дропы
        drops = self.bot.find_entities(types=["item"], max_distance=10)
        for drop in drops[:3]:
            dist = drop.distance_to(self.bot.position)
            priority = 0.3 - (dist / 10)
            self.interests.append(Interest(
                position=drop.position,
                priority=priority,
                interest_type="loot",
                entity=drop
            ))
    
    async def _scan_players(self):
        """Отслеживать игроков"""
        # TODO: Реализовать отслеживание игроков
        pass
    
    def get_highest_threat(self) -> Optional[Threat]:
        """Получить самую опасную угрозу"""
        if not self.threats:
            return None
        return max(self.threats, key=lambda t: t.threat_level)
    
    def get_nearest_interest(self, interest_type: str = "") -> Optional[Interest]:
        """Получить ближайший интересный объект"""
        filtered = self.interests
        if interest_type:
            filtered = [i for i in self.interests if i.interest_type == interest_type]
        
        if not filtered:
            return None
        
        pos = self.bot.position
        if not pos:
            return filtered[0]
        
        # Сортируем по расстоянию
        filtered.sort(key=lambda i: math.sqrt(
            (i.position[0] - pos[0])**2 +
            (i.position[2] - pos[2])**2
        ))
        
        return filtered[0]
    
    def get_terrain_at(self, x: int, z: int) -> Optional[TerrainInfo]:
        """Получить информацию о местности"""
        return self.terrain.get((x, z))
```

---

### 2. Decision Making (Слои движения)

**Файл:** `minepyt/ai/movement.py`

**Назначение:** Объединение множественных векторов движения в один.

**Слои:**

```
Layer 4: GOAL          - Глобальная цель (следование за игроком, goto)
Layer 3: TACTICAL      - Тактика (убежать от крипера, атаковать врага)
Layer 2: LOCAL_AVOID   - Локальное уклонение (ямы, лава)
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
│  └───────────────────────────────────────────────────────┘   │
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
│  └───────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  Layer 1: PHYSICS                                      │   │
│  │  "Куда вообще можно идти?"                           │   │
│  │                                                       │   │
│  │  Проверяет 8 направлений:                              │   │
│  │  ■ ■ ■ ■                                         │   │
│  │  ■ ■ ■                                            │   │
│  │  ■ ■ ■                                            │   │
│  │                                                       │   │
│  │  Для каждого направления:                                │   │
│  │  - Можно туда идти? (проверить блоки)               │   │
│  │  - Там опасно? (лава, край мира)                  │   │
│  │  - На какой высоте? (прыжок?)                        │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                           │                                 │   │
│                           ▼                                 │   │
│                  ┌─────────────────────┐                       │   │
│                  │ Movement Blender │                       │   │
│                  │                 │                       │   │
│                  │  Смешивает все    │                       │   │
│                  │  векторы с      │                       │   │
│                  │  весами         │                       │   │
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
        self.goal_type: str = "idle"  # "follow", "goto", "flee", "attack"
        self.goal_entity: Optional[Any] = None
        
        # Параметры
        self.goal_weight = 0.5      # Вес цели
        self.tactical_weight = 0.8    # Вес тактики
        self.avoid_weight = 0.7      # Вес уклонения
        self.physics_weight = 0.3    # Вес физики
    
    # ==================== LAYER 4: GOAL ====================
    
    def calculate_goal_vector(self) -> Optional[MovementVector]:
        """
        Слой 4: Глобальная цель.
        "Куда я в конечном счёте хочу попасть?"
        """
        if not self.primary_goal:
            return None
        
        pos = self.bot.position
        if not pos:
            return None
        
        dx = self.primary_goal[0] - pos[0]
        dy = self.primary_goal[1] - pos[1]
        dz = self.primary_goal[2] - pos[2]
        
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 1.0:
            return None  # Уже у цели
        
        # Нормализуем
        dx, dy, dz = dx/dist, dy/dist, dz/dist
        
        return MovementVector(
            layer=MovementLayer.GOAL,
            direction=(dx, dy, dz),
            weight=self.goal_weight,
            reason=f"goal:{self.goal_type}"
        )
    
    # ==================== LAYER 3: TACTICAL ====================
    
    def calculate_tactical_vector(self) -> Optional[MovementVector]:
        """
        Слой 3: Тактические решения.
        "Есть ли срочные угрозы или возможности?"
        """
        threats = self.sensors.threats
        
        if not threats:
            return None
        
        # Ищем самую опасную угрозу
        threat = max(threats, key=lambda t: t.threat_level)
        
        if threat.threat_level < 0.5:
            return None  # Угроз нет
        
        # Обработка угрозы
        if threat.threat_type == 1:  # HOSTILE
            entity = threat.entity
            if entity:
                dist = entity.distance_to(self.bot.position)
                
                if dist < 6 and self.bot.health > 10:
                    # Идём к врагу (атака)
                    dx = entity.x - self.bot.position[0]
                    dy = (entity.y + entity.height/2) - self.bot.position[1]
                    dz = entity.z - self.bot.position[2]
                    
                    length = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if length > 0:
                        dx, dy, dz = dx/length, dy/length, dz/length
                    
                    return MovementVector(
                        layer=MovementLayer.TACTICAL,
                        direction=(dx, dy, dz),
                        weight=self.tactical_weight,
                        reason="attack:hostile"
                    )
        
        return None
    
    # ==================== LAYER 2: LOCAL AVOID ====================
    
    def calculate_local_avoid_vector(self) -> Optional[MovementVector]:
        """
        Слой 2: Локальное уклонение.
        "Не упасть бы в яму/лаву!"
        """
        threats = self.sensors.threats
        dangerous_threats = [t for t in threats if t.threat_type in (2, 3, 4, 5)]
        
        if not dangerous_threats:
            return None
        
        pos = self.bot.position
        avoid_x, avoid_z = 0.0, 0.0
        avoid_strength = 0.0
        
        for threat in dangerous_threats:
            dx = pos[0] - threat.position[0]
            dz = pos[2] - threat.position[2]
            dist = math.sqrt(dx*dx + dz*dz)
            
            if dist < 5:
                # Вектор ОТ угрозы
                strength = (5.0 - dist) / 5.0 * threat.threat_level
                if dist > 0:
                    avoid_x += dx / dist * strength
                    avoid_z += dz / dist * strength
                avoid_strength = max(avoid_strength, strength)
        
        if avoid_strength > 0.1:
            # Нормализуем
            length = math.sqrt(avoid_x*avoid_x + avoid_z*avoid_z)
            if length > 0:
                avoid_x /= length
                avoid_z /= length
            
            return MovementVector(
                layer=MovementLayer.LOCAL_AVOID,
                direction=(avoid_x, 0.0, avoid_z),
                weight=avoid_strength,
                reason="avoid:danger"
            )
        
        return None
    
    # ==================== LAYER 1: PHYSICS ====================
    
    def calculate_physics_vector(self) -> MovementVector:
        """
        Слой 1: Физика.
        "Куда вообще можно идти?"
        """
        pos = self.bot.position
        if not pos:
            return MovementVector(
                layer=MovementLayer.PHYSICS,
                direction=(0.0, 0.0, 0.0),
                weight=0.0,
                reason="no_position"
            )
        
        # TODO: Получать информацию о местности из sensors
        # Сейчас - просто идём вперёд/назад/влево/вправо
        
        # Возвращаем вектор в направлении цели или текущего направления
        if self.primary_goal:
            # К цели
            dx = self.primary_goal[0] - pos[0]
            dz = self.primary_goal[2] - pos[2]
        else:
            # Текущее направление (из yaw)
            yaw_rad = math.radians(-self.bot.yaw)
            dx = math.sin(yaw_rad)
            dz = math.cos(yaw_rad)
        
        return MovementVector(
            layer=MovementLayer.PHYSICS,
            direction=(dx, 0.0, dz),
            weight=self.physics_weight,
            reason="physics:walkable"
        )
    
    # ==================== BLEND ALL LAYERS ====================
    
    def calculate_final_vector(self) -> Tuple[float, float, float]:
        """
        Объединяет все слои в финальный вектор движения.
        
        Returns: (dx, dy, dz)
        """
        vectors = []
        
        # Собираем векторы со всех слоёв
        physics = self.calculate_physics_vector()
        vectors.append(physics)
        
        local = self.calculate_local_avoid_vector()
        if local:
            vectors.append(local)
        
        tactical = self.calculate_tactical_vector()
        if tactical:
            vectors.append(tactical)
        
        goal = self.calculate_goal_vector()
        if goal:
            vectors.append(goal)
        
        # Сортируем по слою (высший приоритет = высший слой)
        vectors.sort(key=lambda v: -v.layer)
        
        # Блендим с весами
        final_dx, final_dy, final_dz = 0.0, 0.0, 0.0
        total_weight = 0.0
        
        for vec in vectors:
            final_dx += vec.direction[0] * vec.weight
            final_dy += vec.direction[1] * vec.weight
            final_dz += vec.direction[2] * vec.weight
            total_weight += vec.weight
        
        if total_weight > 0:
            final_dx /= total_weight
            final_dy /= total_weight
            final_dz /= total_weight
        
        # Нормализуем горизонтальную составляющую
        h_length = math.sqrt(final_dx*final_dx + final_dz*final_dz)
        if h_length > 0:
            final_dx /= h_length
            final_dz /= h_length
        
        return (final_dx, final_dy, final_dz)
    
    # ==================== GOAL MANAGEMENT ====================
    
    def set_follow_player(self, player_name: str):
        """Следовать за игроком"""
        self.goal_type = "follow"
        self.goal_entity = player_name
        self.primary_goal = None  # Обновляется каждый тик
    
    def set_goto(self, x: float, y: float, z: float):
        """Идти к точке"""
        self.goal_type = "goto"
        self.goal_entity = None
        self.primary_goal = (x, y, z)
    
    def set_flee(self, from_position: Tuple[float, float, float]):
        """Убегать от точки"""
        self.goal_type = "flee"
        pos = self.bot.position
        if not pos:
            return
        
        dx = pos[0] - from_position[0]
        dz = pos[2] - from_position[2]
        dist = math.sqrt(dx*dx + dz*dz)
        if dist > 0:
            dx, dz = dx/dist, dz/dist
            self.primary_goal = (pos[0] + dx * 20, pos[1], pos[2] + dz * 20)
    
    def clear_goal(self):
        """Остановиться"""
        self.goal_type = "idle"
        self.goal_entity = None
        self.primary_goal = None
    
    def update_goal_position(self):
        """Обновить позицию цели (для follow mode)"""
        if self.goal_type == "follow" and self.goal_entity:
            player = self.bot.find_player(self.goal_entity)
            if player:
                self.primary_goal = player.position
            else:
                self.primary_goal = None
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
    
    def __init__(self, bot):
        self.bot = bot
        
        # Параметры движения
        self.move_speed = 0.3  # блоков за тик
        self.jump_cooldown = 0.1
        self.last_jump = 0.0
    
    async def execute_movement(self, dx: float, dy: float, dz: float):
        """
        Выполнить движение по вектору.
        """
        pos = self.bot.position
        if not pos:
            return
        
        # Вычисляем yaw
        yaw = math.degrees(math.atan2(-dx, dz)) % 360
        
        # Прыжок если нужно
        now = asyncio.get_event_loop().time()
        if dy > 0.5 and (now - self.last_jump > self.jump_cooldown):
            await self.bot.jump()
            self.last_jump = now
        
        # Движение
        new_x = pos[0] + dx * self.move_speed
        new_y = pos[1]
        new_z = pos[2] + dz * self.move_speed
        
        await self.bot.set_position_and_look(new_x, new_y, new_z, yaw)
    
    async def execute_stop(self):
        """Остановить движение"""
        # TODO: Отправить пакет остановки
        pass
    
    async def execute_look(self, x: float, y: float, z: float):
        """Посмотреть на точку"""
        pos = self.bot.position
        if not pos:
            return
        
        dx = x - pos[0]
        dy = y - pos[1]
        dz = z - pos[2]
        
        yaw = math.degrees(math.atan2(-dx, dz))
        pitch = -math.degrees(math.atan2(dy, math.sqrt(dx*dx + dz*dz)))
        
        await self.bot.set_pitch_and_yaw(pitch, yaw)
    
    async def execute_attack(self, entity):
        """Атаковать сущность"""
        await self.bot.attack(entity)
    
    async def execute_interact(self, entity):
        """Взаимодействовать с сущностью"""
        await self.bot.interact(entity)
    
    async def execute_dig(self, x: int, y: int, z: int):
        """Копать блок"""
        await self.bot.dig(x, y, z)
    
    async def execute_place(self, x: int, y: int, z: int, block_name: str):
        """Поставить блок"""
        # TODO: Реализовать
        pass
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
│   ├── actors.py                # Actor System
│   │   ├── Actor (abstract)
│   │   ├── ActorSystem
│   │   ├── SurvivalActor
│   │   ├── CombatActor
│   │   ├── SocialActor
│   │   ├── TaskActor
│   │   └── WorldActor
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
✅ Слои движения легко добавляются
✅ Новые задачи легко создаются
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
- [x] Создать структуру директорий `ai/`
- [x] Реализовать `sensors.py` (базовая версия)
- [x] Реализовать `movement.py` (базовая версия)
- [x] Реализовать `executor.py`
- [x] Создать `SmartBot` класс

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

## Future Enhancements (Запланированные улучшения)

### 1. Machine Learning Layer (ML-слой прогнозирования)

**Приоритет:** 🟢 Низкий (высокая сложность, высокая польза)

**Описание:** Добавить слой ML между Tactical и Goal для предсказания поведения мобов и игроков.

**Компоненты:**

```
Layer 3.5: PREDICTION
├── MobBehaviorPredictor     # Предсказание траектории мобов
├── PlayerMovementPredictor  # Предсказание движения игроков
├── ArrowTrajectoryPredictor # Предсказание траектории стрел
└── ExplosionTimingPredictor # Предсказание взрыва крипера
```

**Интерфейс:**

```python
class PredictionLayer:
    """
    ML-слой прогнозирования.
    Предсказывает будущее состояние мира на основе истории.
    """
    
    def __init__(self):
        self.mob_models: Dict[str, MobModel] = {}
        self.player_models: Dict[str, PlayerModel] = {}
        self.history_window = 100  # тиков истории для анализа
    
    def predict_mob_trajectory(self, mob: Entity, ticks: int = 20) -> List[Position]:
        """Предсказать позицию моба через N тиков"""
        pass
    
    def predict_player_action(self, player: Entity) -> PlayerAction:
        """Предсказать следующее действие игрока"""
        pass
    
    def predict_arrow_hit(self, arrow: Entity) -> Optional[Position]:
        """Предсказать попадание стрелы"""
        pass
    
    def get_prediction_vector(self) -> MovementVector:
        """Вернуть вектор уклонения на основе предсказаний"""
        pass
```

**Польза:**
- Бот уклоняется от стрел ДО выстрела скелета
- Бот убегает от крипера до взрыва
- Бот предсказывает движение игрока для перехвата

**Файлы:**
- `minepyt/ai/prediction/__init__.py`
- `minepyt/ai/prediction/mob_predictor.py`
- `minepyt/ai/prediction/player_predictor.py`
- `minepyt/ai/prediction/projectile_predictor.py`

---

### 2. Risk Assessment Module (Модуль оценки рисков)

**Приоритет:** 🟡 Средний

**Описание:** Отдельный модуль для количественной оценки риска каждого действия.

**Компоненты:**

```
RiskAssessor
├── ThreatEvaluator      # Оценка угроз
├── EnvironmentAnalyzer  # Анализ окружения
├── ResourceCalculator   # Расчёт стоимости ресурсов
└── SurvivalProbability  # Вероятность выживания
```

**Интерфейс:**

```python
@dataclass
class RiskReport:
    """Отчёт о риске действия"""
    action: Action
    death_probability: float      # 0.0 - 1.0
    resource_cost: int            # потеря ресурсов
    time_cost: float              # время в секундах
    reputation_impact: float      # влияние на репутацию
    alternatives: List[Action]    # более безопасные альтернативы
    recommended: bool             # рекомендуется ли это действие

class RiskAssessor:
    """
    Модуль оценки рисков.
    Анализирует каждое действие перед выполнением.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.risk_threshold = 0.5  # максимальный допустимый риск
    
    def assess_action(self, action: Action) -> RiskReport:
        """Оценить риск конкретного действия"""
        death_prob = self._calculate_death_probability(action)
        resource_cost = self._calculate_resource_cost(action)
        alternatives = self._find_safer_alternatives(action)
        
        return RiskReport(
            action=action,
            death_probability=death_prob,
            resource_cost=resource_cost,
            time_cost=action.estimated_time,
            reputation_impact=self._calculate_reputation_impact(action),
            alternatives=alternatives,
            recommended=death_prob < self.risk_threshold
        )
    
    def assess_position(self, position: Position) -> PositionRisk:
        """Оценить опасность позиции"""
        threats = self._scan_threats(position)
        escape_routes = self._find_escape_routes(position)
        cover_available = self._check_cover(position)
        
        return PositionRisk(
            position=position,
            threat_level=sum(t.danger for t in threats),
            escape_routes=escape_routes,
            cover_available=cover_available
        )
    
    def should_flee(self) -> bool:
        """Нужно ли убегать?"""
        return self._current_danger > self.flee_threshold
```

**Польза:**
- Бот не лезет в ситуации с >50% вероятностью смерти
- Автоматический поиск более безопасных альтернатив
- Количественная оценка для принятия решений

**Файлы:**
- `minepyt/ai/risk/__init__.py`
- `minepyt/ai/risk/assessor.py`
- `minepyt/ai/risk/threats.py`
- `minepyt/ai/risk/environment.py`

---

### 3. Inter-Bot Communication Protocol (Протокол связи ботов)

**Приоритет:** 🟢 Низкий

**Описание:** Протокол для координации нескольких ботов.

**Компоненты:**

```
BotCommunication
├── MessageRouter       # Маршрутизация сообщений
├── ChannelManager      # Управление каналами
├── EncryptionLayer     # Шифрование (опционально)
└── ProtocolHandler     # Обработка протокола
```

**Типы сообщений:**

```python
class BotMessageType(Enum):
    # Координация
    NEED_HELP = "need_help"           # Запрос помощи
    RESOURCE_FOUND = "resource_found" # Найден ресурс
    DANGER_ZONE = "danger_zone"       # Опасная зона
    TASK_STATUS = "task_status"       # Статус задачи
    
    # Ролевая система
    ROLE_ASSIGNMENT = "role"          # Назначение роли
    FORMATION = "formation"           # Построение
    
    # Торговля
    TRADE_REQUEST = "trade"           # Запрос обмена
    ITEM_TRANSFER = "item_transfer"   # Передача предметов

class BotMessage:
    sender_id: str
    message_type: BotMessageType
    priority: int  # 0=низкий, 1=нормальный, 2=высокий, 3=критический
    data: Dict[str, Any]
    timestamp: float
    expires_at: Optional[float]
```

**Интерфейс:**

```python
class BotCommunication:
    """
    Система связи между ботами.
    Поддерживает чат и WebSocket.
    """
    
    def __init__(self, bot, encryption_key: Optional[str] = None):
        self.bot = bot
        self.encryption_key = encryption_key
        self.known_bots: Dict[str, BotInfo] = {}
        self.message_handlers: Dict[BotMessageType, Callable] = {}
    
    async def broadcast(self, message: BotMessage):
        """Широковещательная рассылка всем ботам"""
        if self.encryption_key:
            message = self._encrypt(message)
        await self._send_chat(message)
    
    async def send_to(self, bot_id: str, message: BotMessage):
        """Отправить конкретному боту"""
        pass
    
    async def request_help(self, position: Position, threat_type: str):
        """Запросить помощь"""
        message = BotMessage(
            sender_id=self.bot.username,
            message_type=BotMessageType.NEED_HELP,
            priority=3,  # критический
            data={
                "position": position,
                "threat": threat_type,
                "urgency": "high"
            }
        )
        await self.broadcast(message)
    
    def on_message(self, msg_type: BotMessageType):
        """Декоратор для обработки сообщений"""
        def decorator(func):
            self.message_handlers[msg_type] = func
            return func
        return decorator
```

**Пример использования:**

```python
# Бот 1 обнаружил крипер
await comm.request_help(bot.position, "creeper")

# Бот 2 обрабатывает
@comm.on_message(BotMessageType.NEED_HELP)
async def handle_help(message: BotMessage):
    if message.data["threat"] == "creeper":
        await bot.goto(message.data["position"])
        await attack_creeper()
```

**Файлы:**
- `minepyt/ai/communication/__init__.py`
- `minepyt/ai/communication/protocol.py`
- `minepyt/ai/communication/router.py`
- `minepyt/ai/communication/encryption.py`

---

### 4. Visual Debugging System (Система визуальной отладки)

**Приоритет:** 🟡 Средний

**Описание:** Визуализация в реальном времени того, что "видит" и "думает" бот.

**Компоненты:**

```
DebugVisualizer
├── WebSocketServer     # Сервер для веб-интерфейса
├── StateSerializer     # Сериализация состояния
├── HistoryRecorder     # Запись истории
└── ReplaySystem        # Система повторов
```

**Интерфейс:**

```python
class DebugVisualizer:
    """
    Система визуальной отладки.
    WebSocket сервер для веб-интерфейса.
    """
    
    def __init__(self, bot, port: int = 8080):
        self.bot = bot
        self.port = port
        self.clients: Set[WebSocket] = set()
        self.history: List[DebugSnapshot] = []
        self.max_history = 10000
    
    async def start(self):
        """Запустить сервер отладки"""
        await websockets.serve(self._handle_client, "localhost", self.port)
    
    async def broadcast_state(self):
        """Отправить текущее состояние всем клиентам"""
        snapshot = self._create_snapshot()
        self.history.append(snapshot)
        
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        for client in self.clients:
            await client.send(json.dumps(snapshot))
    
    def _create_snapshot(self) -> DebugSnapshot:
        """Создать снимок состояния"""
        return {
            "timestamp": time.time(),
            "position": self.bot.position,
            "health": self.bot.health,
            "food": self.bot.food,
            
            # Векторы движения
            "vectors": {
                "goal": self.bot.ai.movement.goal_vector,
                "tactical": self.bot.ai.movement.tactical_vector,
                "avoid": self.bot.ai.movement.avoid_vector,
                "physics": self.bot.ai.movement.physics_vector,
                "final": self.bot.ai.movement.final_vector,
            },
            
            # Угрозы
            "threats": [
                {"type": t.type, "position": t.position, "danger": t.danger}
                for t in self.bot.ai.sensors.threats
            ],
            
            # Интересы
            "interests": [
                {"type": i.type, "position": i.position, "priority": i.priority}
                for i in self.bot.ai.sensors.interests
            ],
            
            # Текущая цель
            "goal": {
                "type": self.bot.ai.movement.goal_type,
                "target": self.bot.ai.movement.goal_entity,
            },
            
            # Решения
            "decisions": self.bot.ai.decision_history[-10:],
        }
```

**Веб-интерфейс показывает:**
- 3D карта с позицией бота
- Векторы движения (все слои)
- Обнаруженные угрозы (красные маркеры)
- Интересные объекты (зелёные маркеры)
- Текущую цель (жёлтый маркер)
- История решений (timeline)
- Графики health/food/overtime

**Файлы:**
- `minepyt/ai/debug/__init__.py`
- `minepyt/ai/debug/visualizer.py`
- `minepyt/ai/debug/web_interface/` (HTML/JS)

---

### 5. Hierarchical Task Network (HTN) для сложных задач

**Приоритет:** 🟢 Низкий

**Описание:** HTN планировщик для многошаговых задач с автоматической декомпозицией.

**Компоненты:**

```
HTNPlanner
├── TaskDecomposer      # Декомпозиция задач
├── MethodSelector      # Выбор методов
├── PreconditionChecker # Проверка условий
└── PlanExecutor        # Исполнение плана
```

**Структура:**

```python
class TaskType(Enum):
    PRIMITIVE = "primitive"  # Атомарное действие
    COMPOUND = "compound"    # Составная задача

@dataclass
class HTNTask:
    name: str
    task_type: TaskType
    preconditions: List[Condition]
    effects: List[Effect]
    
    # Для compound задач
    methods: List['HTNMethod'] = field(default_factory=list)
    
    # Для primitive задач
    action: Optional[Callable] = None

@dataclass
class HTNMethod:
    name: str
    preconditions: List[Condition]
    subtasks: List[HTNTask]

class HTNPlanner:
    """
    HTN планировщик.
    Декомпозирует сложные задачи на простые действия.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.task_library: Dict[str, HTNTask] = {}
        self._register_default_tasks()
    
    def decompose(self, task: HTNTask, state: WorldState) -> List[HTNTask]:
        """
        Рекурсивная декомпозиция задачи.
        Возвращает список примитивных действий.
        """
        if task.task_type == TaskType.PRIMITIVE:
            return [task]
        
        # Выбрать подходящий метод
        method = self._select_method(task, state)
        if not method:
            raise PlanningError(f"No applicable method for {task.name}")
        
        # Рекурсивно декомпозировать подзадачи
        result = []
        for subtask in method.subtasks:
            result.extend(self.decompose(subtask, state))
        
        return result
    
    def plan(self, goal: str) -> List[HTNTask]:
        """Создать план для достижения цели"""
        task = self.task_library[goal]
        state = self._get_current_state()
        return self.decompose(task, state)
    
    def _register_default_tasks(self):
        """Регистрация стандартных задач"""
        
        # "Построить дом" → составная задача
        self.task_library["build_house"] = HTNTask(
            name="build_house",
            task_type=TaskType.COMPOUND,
            methods=[
                HTNMethod(
                    name="standard_house",
                    preconditions=[HasResources()], HasSpace()],
                    subtasks=[
                        HTNTask(name="gather_materials"),
                        HTNTask(name="clear_area"),
                        HTNTask(name="build_foundation"),
                        HTNTask(name="build_walls"),
                        HTNTask(name="build_roof"),
                        HTNTask(name="add_doors_windows"),
                    ]
                )
            ]
        )
        
        # "Собрать материалы" → составная задача
        self.task_library["gather_materials"] = HTNTask(
            name="gather_materials",
            task_type=TaskType.COMPOUND,
            methods=[
                HTNMethod(
                    name="wooden_house",
                    preconditions=[],
                    subtasks=[
                        HTNTask(name="find_tree"),
                        HTNTask(name="chop_tree"),
                        HTNTask(name="craft_planks"),
                    ]
                )
            ]
        )
        
        # Примитивные задачи
        self.task_library["find_tree"] = HTNTask(
            name="find_tree",
            task_type=TaskType.PRIMITIVE,
            action=lambda: self.bot.find_nearest("minecraft:oak_log")
        )
```

**Пример использования:**

```python
# Создать план "построить дом"
planner = HTNPlanner(bot)
plan = planner.plan("build_house")

# План автоматически разложится на:
# 1. find_tree
# 2. chop_tree
# 3. craft_planks
# 4. clear_area
# 5. build_foundation
# 6. build_walls
# 7. build_roof
# 8. add_doors_windows

# Выполнить план
for task in plan:
    await task.action()
```

**Файлы:**
- `minepyt/ai/htn/__init__.py`
- `minepyt/ai/htn/planner.py`
- `minepyt/ai/htn/tasks.py`
- `minepyt/ai/htn/methods.py`
- `minepyt/ai/htn/world_state.py`

---

## Приоритет реализации Future Enhancements

| Фаза | Идея | Сложность | Польза | ETA |
|------|------|-----------|--------|-----|
| Фаза 7 | Visual Debugging | 🟡 Средняя | 🔴 Высокая | 2-3 дня |
| Фаза 7 | Risk Assessment | 🟡 Средняя | 🟡 Средняя | 2-3 дня |
| Фаза 8 | Inter-Bot Comm | 🟡 Средняя | 🟡 Средняя | 3-5 дней |
| Фаза 9 | HTN Planner | 🔴 Высокая | 🔴 Высокая | 5-7 дней |
| Фаза 10 | ML Layer | 🔴 Высокая | 🔴 Высокая | 7-14 дней |

**Рекомендуемый порядок:**
1. Visual Debugging — упростит отладку всех остальных
2. Risk Assessment — улучшит базовое поведение
3. Inter-Bot Comm — для координации ботов
4. HTN Planner — для сложных задач
5. ML Layer — для продвинутого ИИ
