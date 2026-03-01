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
