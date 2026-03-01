"""
Debug Snapshot Models

Модели данных для снимков состояния бота.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import time


class ThreatType(Enum):
    """Типы угроз"""

    HOSTILE_MOB = "hostile_mob"
    PROJECTILE = "projectile"
    EXPLOSION = "explosion"
    FALL = "fall"
    LAVA = "lava"
    WATER = "water"
    PLAYER = "player"


class InterestType(Enum):
    """Типы интересов"""

    RESOURCE = "resource"
    FOOD = "food"
    PLAYER = "player"
    VILLAGER = "villager"
    CHEST = "chest"
    SAFE_ZONE = "safe_zone"


class GoalType(Enum):
    """Типы целей"""

    FOLLOW = "follow"
    GOTO = "goto"
    FLEE = "flee"
    IDLE = "idle"
    ATTACK = "attack"
    COLLECT = "collect"
    ESCORT = "escort"


@dataclass
class VectorInfo:
    """Информация о векторе движения"""

    dx: float
    dy: float
    dz: float
    weight: float = 1.0
    source: str = ""  # "goal", "tactical", "avoid", "physics"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dx": round(self.dx, 4),
            "dy": round(self.dy, 4),
            "dz": round(self.dz, 4),
            "weight": round(self.weight, 4),
            "source": self.source,
        }

    def length(self) -> float:
        return (self.dx**2 + self.dy**2 + self.dz**2) ** 0.5


@dataclass
class ThreatInfo:
    """Информация об угрозе"""

    threat_type: str
    entity_type: Optional[str] = None
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    distance: float = 0.0
    danger: float = 0.0  # 0.0 - 1.0
    direction: Optional[Tuple[float, float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.threat_type,
            "entityType": self.entity_type,
            "position": list(self.position),
            "distance": round(self.distance, 2),
            "danger": round(self.danger, 3),
            "direction": list(self.direction) if self.direction else None,
        }


@dataclass
class InterestInfo:
    """Информация об интересном объекте"""

    interest_type: str
    entity_type: Optional[str] = None
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    distance: float = 0.0
    priority: float = 0.0  # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.interest_type,
            "entityType": self.entity_type,
            "position": list(self.position),
            "distance": round(self.distance, 2),
            "priority": round(self.priority, 3),
        }


@dataclass
class GoalInfo:
    """Информация о текущей цели"""

    goal_type: str = "idle"
    target_name: Optional[str] = None
    target_position: Optional[Tuple[float, float, float]] = None
    progress: float = 0.0  # 0.0 - 1.0
    eta_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.goal_type,
            "targetName": self.target_name,
            "targetPosition": list(self.target_position) if self.target_position else None,
            "progress": round(self.progress, 3),
            "etaSeconds": self.eta_seconds,
        }


@dataclass
class HealthInfo:
    """Информация о здоровье"""

    health: float = 20.0
    max_health: float = 20.0
    food: int = 20
    max_food: int = 20
    saturation: float = 5.0
    oxygen: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health": round(self.health, 1),
            "maxHealth": self.max_health,
            "healthPercent": round(self.health / self.max_health * 100, 1),
            "food": self.food,
            "maxFood": self.max_food,
            "foodPercent": round(self.food / self.max_food * 100, 1),
            "saturation": round(self.saturation, 1),
            "oxygen": self.oxygen,
        }


@dataclass
class PositionInfo:
    """Информация о позиции"""

    x: float = 0.0
    y: float = 64.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    on_ground: bool = True
    in_water: bool = False
    in_lava: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "z": round(self.z, 2),
            "yaw": round(self.yaw, 1),
            "pitch": round(self.pitch, 1),
            "velocity": [round(v, 3) for v in self.velocity],
            "onGround": self.on_ground,
            "inWater": self.in_water,
            "inLava": self.in_lava,
            "block": (int(self.x), int(self.y), int(self.z)),
        }


@dataclass
class InventoryInfo:
    """Информация об инвентаре"""

    held_slot: int = 0
    held_item: Optional[str] = None
    held_item_count: int = 0
    total_items: int = 0
    free_slots: int = 36
    armor: Dict[str, Optional[str]] = field(
        default_factory=lambda: {
            "head": None,
            "chest": None,
            "legs": None,
            "feet": None,
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heldSlot": self.held_slot,
            "heldItem": self.held_item,
            "heldItemCount": self.held_item_count,
            "totalItems": self.total_items,
            "freeSlots": self.free_slots,
            "armor": self.armor,
        }


@dataclass
class DecisionRecord:
    """Запись о принятом решении"""

    timestamp: float
    action: str
    reason: str
    result: str  # "success", "failed", "cancelled", "pending"
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "reason": self.reason,
            "result": self.result,
            "durationMs": self.duration_ms,
        }


@dataclass
class DebugSnapshot:
    """
    Полный снимок состояния бота для отладки.
    Сериализуется в JSON для отправки через WebSocket.
    """

    # Метаданные
    timestamp: float = field(default_factory=time.time)
    bot_name: str = "Bot"
    tick: int = 0
    fps: float = 20.0

    # Позиция и здоровье
    position: PositionInfo = field(default_factory=PositionInfo)
    health: HealthInfo = field(default_factory=HealthInfo)
    inventory: InventoryInfo = field(default_factory=InventoryInfo)

    # AI состояние
    vectors: Dict[str, VectorInfo] = field(default_factory=dict)
    threats: List[ThreatInfo] = field(default_factory=list)
    interests: List[InterestInfo] = field(default_factory=list)
    goal: GoalInfo = field(default_factory=GoalInfo)

    # История
    recent_decisions: List[DecisionRecord] = field(default_factory=list)

    # Метрики
    tick_time_ms: float = 0.0
    ai_time_ms: float = 0.0
    network_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для JSON"""
        return {
            "meta": {
                "timestamp": self.timestamp,
                "botName": self.bot_name,
                "tick": self.tick,
                "fps": round(self.fps, 1),
            },
            "position": self.position.to_dict(),
            "health": self.health.to_dict(),
            "inventory": self.inventory.to_dict(),
            "ai": {
                "vectors": {k: v.to_dict() for k, v in self.vectors.items()},
                "threats": [t.to_dict() for t in self.threats],
                "interests": [i.to_dict() for i in self.interests],
                "goal": self.goal.to_dict(),
            },
            "history": {
                "decisions": [d.to_dict() for d in self.recent_decisions[-20:]],
            },
            "metrics": {
                "tickTimeMs": round(self.tick_time_ms, 2),
                "aiTimeMs": round(self.ai_time_ms, 2),
                "networkTimeMs": round(self.network_time_ms, 2),
            },
        }

    def to_json(self) -> str:
        """Сериализация в JSON строку"""
        import json

        return json.dumps(self.to_dict())
