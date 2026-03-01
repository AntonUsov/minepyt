"""
Movement - Layered Movement System

Модуль управления движением с системой слоёв.

Архитектура:
Layer 4: GOAL          - Глобальная цель (следование за игроком, goto)
Layer 3: TACTICAL      - Тактика (убежать от крипера, атаковать врага)
Layer 2: LOCAL_AVOID   - Локальное уклонение (ямы, лава)
Layer 1: PHYSICS       - Физика (куда вообще можно идти)

Все слои объединяются в один финальный вектор.
"""

import asyncio
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Callable
from datetime import datetime
from enum import IntEnum
from .sensors import SensorArray, Threat


class MovementLayer(IntEnum):
    """Слои движения"""

    PHYSICS = 1  # Базовая физика (коллизии)
    LOCAL_AVOID = 2  # Локальное уклонение (ямы, лава)
    TACTICAL = 3  # Тактика (мобы, укрытия)
    GOAL = 4  # Глобальная цель (следование за игроком)


@dataclass
class MovementVector:
    """Вектор движения от одного слоя"""

    layer: MovementLayer = MovementLayer.PHYSICS
    direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # dx, dy, dz
    weight: float = 0.0
    reason: str = ""

    def blend_with(self, other: "MovementVector") -> "MovementVector":
        """
        Смешать два вектора.

        Чем выше weight, тем больше влияния.
        Чем выше layer, тем выше приоритет.
        """
        total_weight = self.weight + other.weight

        # Смешиваем направления
        new_direction = (
            (self.direction[0] * self.weight + other.direction[0] * other.weight) / total_weight,
            (self.direction[1] * self.weight + other.direction[1] * other.weight) / total_weight,
            (self.direction[2] * self.weight + other.direction[2] * other.weight) / total_weight,
        )

        # Возвращаем вектор с высшим слоем
        return MovementVector(
            layer=max(self.layer, other.layer),
            direction=new_direction,
            weight=total_weight / 2.0,
            reason=f"{self.reason} + {other.reason}",
        )


class MovementBrain:
    """
    Мозг движения - объединяет все слои в один вектор.
    """

    def __init__(self, bot, sensors: SensorArray):
        self.bot = bot
        self.sensors = sensors

        # Текущая цель (Layer 4)
        self.primary_goal: Optional[Tuple[float, float, float]] = None
        self.goal_type: str = "idle"  # "follow", "goto", "flee", "attack"
        self.goal_entity: Optional[Any] = None

        # Параметры слоёв
        self.layer_weights = {
            MovementLayer.GOAL: 0.5,
            MovementLayer.TACTICAL: 0.8,
            MovementLayer.LOCAL_AVOID: 0.7,
            MovementLayer.PHYSICS: 0.3,
        }

        # Состояние
        self.is_moving = False
        self.last_position: Optional[Tuple[float, float, float]] = None

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

        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 1.0:
            return None  # Уже у цели

        # Нормализуем
        dx, dy, dz = dx / dist, dy / dist, dz / dist

        return MovementVector(
            layer=MovementLayer.GOAL,
            direction=(dx, dy, dz),
            weight=self.layer_weights[MovementLayer.GOAL],
            reason=f"goal:{self.goal_type}",
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
                    dy = (entity.y + entity.height / 2) - self.bot.position[1]
                    dz = entity.z - self.bot.position[2]

                    length = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if length > 0:
                        dx, dy, dz = dx / length, dy / length, dz / length

                    return MovementVector(
                        layer=MovementLayer.TACTICAL,
                        direction=(dx, dy, dz),
                        weight=self.layer_weights[MovementLayer.TACTICAL],
                        reason="attack:hostile",
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
            dist = math.sqrt(dx * dx + dz * dz)

            if dist < 5:
                # Вектор ОТ угрозы
                strength = (5.0 - dist) / 5.0 * threat.threat_level
                if dist > 0:
                    avoid_x += dx / dist * strength
                    avoid_z += dz / dist * strength
                avoid_strength = max(avoid_strength, strength)

        if avoid_strength > 0.1:
            # Нормализуем
            length = math.sqrt(avoid_x * avoid_x + avoid_z * avoid_z)
            if length > 0:
                avoid_x /= length
                avoid_z /= length

            return MovementVector(
                layer=MovementLayer.LOCAL_AVOID,
                direction=(avoid_x, 0.0, avoid_z),
                weight=avoid_strength,
                reason="avoid:danger",
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
                reason="no_position",
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
            weight=self.layer_weights[MovementLayer.PHYSICS],
            reason="physics:walkable",
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
        h_length = math.sqrt(final_dx * final_dx + final_dz * final_dz)
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
        dist = math.sqrt(dx * dx + dz * dz)
        if dist > 0:
            dx, dz = dx / dist, dz / dist
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
