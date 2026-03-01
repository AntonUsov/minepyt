"""
Executor - Action Execution System

Модуль исполнения действий - отправка пакетов в Minecraft.
"""

import asyncio
import math
from typing import Tuple


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
        pitch = -math.degrees(math.atan2(dy, math.sqrt(dx * dx + dz * dz)))

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
