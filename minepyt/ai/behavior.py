"""
Behavior Trees - Decision Making System

Модуль behaviour trees для логики принятия решений.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any, Callable
from enum import Enum


class NodeStatus(Enum):
    """Статус выполнения узла"""

    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BTNode(ABC):
    """Базовый узел Behavior Tree"""

    def __init__(self, name: str):
        self.name = name
        self.children: List["BTNode"] = []

    @abstractmethod
    async def tick(self, bot, blackboard) -> NodeStatus:
        pass


class Selector(BTNode):
    """ИЛИ - пробует детей по порядку, пока один не succeeded"""

    async def tick(self, bot, blackboard) -> NodeStatus:
        for child in self.children:
            status = await child.tick(bot, blackboard)
            if status in (NodeStatus.SUCCESS, NodeStatus.RUNNING):
                return status
        return NodeStatus.FAILURE


class Sequence(BTNode):
    """И - выполняет всех детей по порядку, fail если любой failed"""

    async def tick(self, bot, blackboard) -> NodeStatus:
        for child in self.children:
            status = await child.tick(bot, blackboard)
            if status in (NodeStatus.FAILURE, NodeStatus.RUNNING):
                return status
        return NodeStatus.SUCCESS


class Parallel(BTNode):
    """Выполняет всех детей одновременно"""

    def __init__(self, name: str, success_policy: str = "all"):
        super().__init__(name)
        self.success_policy = success_policy  # "all" | "any"

    async def tick(self, bot, blackboard) -> NodeStatus:
        tasks = [child.tick(bot, blackboard) for child in self.children]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if r == NodeStatus.SUCCESS)
        running = sum(1 for r in results if r == NodeStatus.RUNNING)

        if running > 0:
            return NodeStatus.RUNNING

        if self.success_policy == "all":
            return NodeStatus.SUCCESS if successes == len(results) else NodeStatus.FAILURE
        else:
            return NodeStatus.SUCCESS if successes > 0 else NodeStatus.FAILURE


class Condition(BTNode):
    """Условие - проверяет состояние"""

    def __init__(self, name: str, check_fn: Callable, invert: bool = False):
        super().__init__(name)
        self.check_fn = check_fn
        self.invert = invert

    async def tick(self, bot, blackboard) -> NodeStatus:
        result = await check_fn(bot, blackboard)
        if self.invert:
            result = not result
        return NodeStatus.SUCCESS if result else NodeStatus.FAILURE


class Action(BTNode):
    """Действие - выполняет команду"""

    def __init__(self, name: str, action_fn: Callable):
        super().__init__(name)
        self.action_fn = action_fn
        self._running_task: Optional[asyncio.Task] = None

    async def tick(self, bot, blackboard) -> NodeStatus:
        if self._running_task and not self._running_task.done():
            return NodeStatus.RUNNING

        self._running_task = asyncio.create_task(self.action_fn(bot, blackboard))
        return NodeStatus.RUNNING


class Decorator(BTNode):
    """Декоратор - модифицирует поведение ребёнка"""

    def __init__(self, name: str, child: BTNode = None):
        super().__init__(name)
        if child:
            self.children = [child]
