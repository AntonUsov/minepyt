"""
Sensors - Perception System

Модуль сенсоров для Minecraft бота.
"Глаза и уши" бота - сканирование мира.

Компоненты:
- ThreatScanner: обнаружение врагов и опасностей
- ResourceScanner: поиск еды и ресурсов
- TerrainScanner: анализ местности (ямы, лава)
- PlayerTracker: отслеживание игроков
- InterestManager: управление интересными объектами
"""

import asyncio
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
from enum import IntEnum


class ThreatType(IntEnum):
    """Типы угроз"""

    HOSTILE = 1
    LAVA = 2
    VOID = 3
    FIRE = 4
    FALL_DAMAGE = 5


@dataclass
class Threat:
    """Обнаруженная угроза"""

    entity: Optional[Any] = None
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    threat_level: float = 0.0
    threat_type: ThreatType = ThreatType.HOSTILE
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Interest:
    """Что-то интересное"""

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    priority: float = 0.0
    interest_type: str = ""
    entity: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TerrainInfo:
    """Информация о местности"""

    floor_y: int = 0
    walkable: bool = False
    danger: float = 0.0
    jumpable: bool = False
    swimable: bool = False


class SensorArray:
    """
    Массив сенсоров - непрерывное сканирование мира.

    Работает как независимый coroutine, сканирует мир
    с заданной частотой и обновляет shared state.
    """

    def __init__(self, bot):
        self.bot = bot

        # Состояние сенсоров
        self.threats: List[Threat] = []
        self.interests: List[Interest] = []
        self.terrain_map: Dict[Tuple[int, int], TerrainInfo] = {}

        # Параметры
        self.scan_interval = 0.05  # 20 сканирований в секунду
        self.threat_scan_range = 32
        self.resource_scan_range = 64
        self.terrain_scan_range = 16

        # Управление
        self.running = False
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
                    return_exceptions=True,
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
            self.threats.append(
                Threat(
                    entity=hostile_entities,
                    position=hostile_entities.position,
                    threat_level=threat_level,
                    threat_type=ThreatType.HOSTILE,
                )
            )

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
            animals = self.bot.find_entities(max_distance=self.resource_scan_range)

            for animal in animals[:5]:  # Ограничиваем
                dist = animal.distance_to(self.bot.position)
                priority = 0.7 - (dist / self.resource_scan_range)
                self.interests.append(
                    Interest(
                        position=animal.position,
                        priority=priority,
                        interest_type="food",
                        entity=animal,
                    )
                )

        # Ищем дропы
        drops = self.bot.find_entities(types=["item"], max_distance=10)
        for drop in drops[:3]:
            dist = drop.distance_to(self.bot.position)
            priority = 0.3 - (dist / 10)
            self.interests.append(
                Interest(
                    position=drop.position, priority=priority, interest_type="loot", entity=drop
                )
            )

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
        filtered.sort(
            key=lambda i: math.sqrt((i.position[0] - pos[0]) ** 2 + (i.position[2] - pos[2]) ** 2)
        )

        return filtered[0]

    def get_terrain_at(self, x: int, z: int) -> Optional[TerrainInfo]:
        """Получить информацию о местности"""
        return self.terrain_map.get((x, z))
