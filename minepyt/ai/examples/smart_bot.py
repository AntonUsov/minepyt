"""
Smart Bot Example

Пример умного бота с AI системой:
- Layered Movement
- Actor System
- Behavior Trees
"""

import asyncio
from ..protocol import create_bot
from ..ai.sensors import SensorArray
from ..ai.movement import MovementBrain
from ..ai.actors import ActorSystem, SimpleActor
from ..ai.executor import ActionExecutor


class SmartBot:
    """
    Умный бот с полной AI архитектурой.
    """

    def __init__(self, config: dict):
        # Создаём базовый протокол
        self.protocol = create_bot(config)
        self.bot = self.protocol

        # Создаём AI компоненты
        self.sensors = SensorArray(self.bot)
        self.movement = MovementBrain(self.bot, self.sensors)
        self.executor = ActionExecutor(self.bot)
        self.actors = ActorSystem(self.bot)

        # Запускаем AI систему
        self.running = False

    async def connect(self):
        """Подключиться к серверу"""
        await self.bot.connect()
        self.running = True

        # Запускаем AI
        self.ai_task = asyncio.create_task(self._run_ai_loop())

    async def disconnect(self):
        """Отключиться от сервера"""
        self.running = False
        if self.ai_task:
            self.ai_task.cancel()

        await self.bot.disconnect()

    async def _run_ai_loop(self):
        """Главный AI цикл"""
        while self.running:
            # 1. Сканируем мир (сенсоры работают фоном)
            # self.sensors уже работает непрерывно

            # 2. Обновляем позицию цели (если follow mode)
            self.movement.update_goal_position()

            # 3. Вычисляем финальный вектор движения
            dx, dy, dz = self.movement.calculate_final_vector()

            # 4. Выполняем движение
            if abs(dx) > 0.01 or abs(dz) > 0.01:
                await self.executor.execute_movement(dx, dy, dz)

            # 5. Проверяем боя
            # TODO: Реализовать логику боя

            await asyncio.sleep(0.05)  # 20 тиков/сек

    # ==================== PUBLIC API ====================

    async def chat(self, message: str):
        """Сказать в чат"""
        await self.bot.chat(message)

    async def follow_player(self, player_name: str):
        """Следовать за игроком"""
        self.movement.set_follow_player(player_name)
        await self.chat(f"Following {player_name}...")

    async def stop_following(self):
        """Перестать следовать"""
        self.movement.clear_goal()
        await self.chat("Stopped following")

    async def go_to(self, x: float, y: float, z: float):
        """Идти к точке"""
        self.movement.set_goto(x, y, z)
        await self.chat(f"Going to ({x}, {y}, {z})")

    async def stay_alive(self, duration: float = 60.0):
        """Оставаться онлайн N секунд"""
        await asyncio.sleep(duration)


# ==================== EXAMPLE USAGE ====================


async def example_follow_player():
    """Пример: Следовать за игроком"""
    bot = SmartBot({"host": "localhost", "port": 25565, "username": "SmartBot"})

    await bot.connect()
    await bot.follow_player("__heksus__")

    # Бот работает автоматически
    await asyncio.sleep(60.0)

    await bot.disconnect()


async def example_simple_movement():
    """Пример: Простой бот без следования"""
    bot = SmartBot({"host": "localhost", "port": 25565, "username": "WanderBot"})

    await bot.connect()
    await bot.chat("I will wander around...")

    # Бот просто будет двигаться (нет цели)
    await asyncio.sleep(60.0)

    await bot.disconnect()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "follow":
            asyncio.run(example_follow_player())
        elif mode == "wander":
            asyncio.run(example_simple_movement())
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python smart_bot.py [follow|wander]")
    else:
        print("No mode specified")
        print("Usage: python smart_bot.py [follow|wander]")
        print("Example: python smart_bot.py follow")
