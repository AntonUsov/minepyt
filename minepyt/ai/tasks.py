"""
Tasks - Long-term Tasks

Модуль долгосрочных задач для бота.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from datetime import datetime
from .actors import Blackboard


@dataclass
class BotTask:
    """
    Долгосрочная задача с состоянием.
    Может быть прервана и возобновлена.
    """

    id: str
    name: str
    description: str
    priority: int = 0
    status: str = "pending"  # "pending", "running", "paused", "completed", "cancelled"
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Состояние задачи (сериализуется для возобновления)
    state: dict = field(default_factory=dict)

    # Условия
    preconditions: List[Callable] = field(default_factory=list)
    can_interrupt: Callable = lambda b, bb: True
    can_continue: Callable = lambda b, bb: True

    @abstractmethod
    async def step(self, bot, blackboard) -> str:
        """
        Выполнить один шаг задачи.
        Returns: "running", "completed", "failed"
        """
        pass

    def pause(self):
        self.status = "paused"

    def resume(self):
        self.status = "running"

    def cancel(self):
        self.status = "cancelled"


class SimpleTask(BotTask):
    """Простая задача для тестирования"""

    def __init__(self, task_id: str, name: str, description: str):
        super().__init__(id=task_id, name=name, description=description)
        self._steps = 0

    async def step(self, bot, blackboard) -> str:
        self._steps += 1
        print(f"[Task {self.name}] Step {self._steps}")

        if self._steps >= 5:
            return "completed"

        await asyncio.sleep(1)
        return "running"


class GatherResourceTask(BotTask):
    """Задача сбора ресурсов"""

    def __init__(self, task_id: str, resource_type: str, target_amount: int = 10):
        super().__init__(
            id=task_id,
            name=f"Gather {resource_type}",
            description=f"Collect {target_amount} {resource_type}",
        )
        self.resource_type = resource_type
        self.target_amount = target_amount
        self.collected = 0

    async def step(self, bot, blackboard) -> str:
        # TODO: Реализовать логику сбора
        self.collected += 1

        if self.collected >= self.target_amount:
            return "completed"

        return "running"
