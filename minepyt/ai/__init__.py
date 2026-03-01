"""
MinePyt AI Module

Модуль умной системы для Minecraft ботов.

Архитектура:
- Perception (sensors.py) - "глаза" бота
- Decision Making (movement.py) - "мозг" движения
- Action Execution (executor.py) - "руки" бота
- Actors (actors.py) - независимые агенты
- Behavior Trees (behavior.py) - логика принятия решений
- Tasks (tasks.py) - долгосрочные задачи
"""

from .sensors import SensorArray, Threat, Interest, TerrainInfo
from .movement import MovementBrain, MovementLayer, MovementVector
from .actors import Actor, ActorSystem
from .behavior import BTNode, Selector, Sequence, Parallel, Condition, Action, Decorator, NodeStatus
from .executor import ActionExecutor

__all__ = [
    # Perception
    "SensorArray",
    "Threat",
    "Interest",
    "TerrainInfo",
    # Decision Making
    "MovementBrain",
    "MovementLayer",
    "MovementVector",
    # Actors
    "Actor",
    "ActorSystem",
    # Behavior Trees
    "BTNode",
    "Selector",
    "Sequence",
    "Parallel",
    "Condition",
    "Action",
    "Decorator",
    "NodeStatus",
    # Execution
    "ActionExecutor",
]
