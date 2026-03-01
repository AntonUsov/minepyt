"""
Actors - Actor System

Модуль системы акторов - независимых агентов с behaviour trees.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable, Set
from datetime import datetime
from .sensors import SensorArray


@dataclass
class Message:
    """Сообщение между акторами"""

    sender: str
    type: str
    payload: Any
    priority: int = 0
    timestamp: datetime = None
    reply_to: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Blackboard:
    """
    Разделяемое состояние между всеми акторами.
    Акторы читают и пишут сюда.
    """

    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.subscribers: Dict[str, List[Callable]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        # TODO: Уведомлять подписчиков

    async def acquire(self, key: str) -> asyncio.Lock:
        """Получить лок для атомарной операции"""
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

    def subscribe(self, key: str, callback: Callable):
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)


class Actor(ABC):
    """
    Актор - независимый агент со своим mailbox и behavior tree.
    """

    def __init__(self, name: str, bot, blackboard: Blackboard):
        self.name = name
        self.bot = bot
        self.blackboard = blackboard
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.running = True

        # Параметры
        self.tick_interval = 0.1  # Частота тиков behavior tree

    async def receive(self, timeout: float = None) -> Optional[Message]:
        try:
            if timeout:
                return await asyncio.wait_for(self.mailbox.get(), timeout=timeout)
            return await self.mailbox.get()
        except asyncio.TimeoutError:
            return None

    async def send(self, msg: Message):
        await self.mailbox.put(msg)

    async def run(self):
        """Главный цикл актора"""
        while self.running:
            # Обрабатываем сообщения (неблокирующе)
            msg = await self.receive(timeout=0.01)
            if msg:
                await self.handle_message(msg)

            # Тикаем behavior tree
            # TODO: Выполнить behavior tree

            await asyncio.sleep(self.tick_interval)

    @abstractmethod
    async def handle_message(self, msg: Message):
        """Обработать входящее сообщение"""
        pass


class ActorSystem:
    """
    Управляет всеми акторами и их взаимодействием.
    """

    def __init__(self, bot):
        self.bot = bot
        self.blackboard = Blackboard()
        self.actors: Dict[str, Actor] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    def spawn(self, actor: Actor):
        self.actors[actor.name] = actor
        self.tasks[actor.name] = asyncio.create_task(actor.run())

    async def broadcast(self, msg_type: str, payload: Any, exclude: Set[str] = None):
        """Отправить сообщение всем акторам"""
        exclude = exclude or set()
        for name, actor in self.actors.items():
            if name not in exclude:
                await actor.send(Message(sender="system", type=msg_type, payload=payload))

    async def send_to(self, target: str, msg_type: str, payload: Any, sender: str = "system"):
        """Отправить сообщение конкретному актору"""
        if target in self.actors:
            await self.actors[target].send(Message(sender=sender, type=msg_type, payload=payload))

    async def stop_all(self):
        for actor in self.actors.values():
            actor.running = False
        for task in self.tasks.values():
            task.cancel()


class SimpleActor(Actor):
    """Простой актор для тестирования"""

    def __init__(self, name: str, bot, blackboard: Blackboard):
        super().__init__(name, bot, blackboard)

    async def handle_message(self, msg: Message):
        if msg.type == "ping":
            print(f"[{self.name}] Received ping")
            # TODO: Отправить pong
