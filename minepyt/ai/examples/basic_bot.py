"""
Basic Bot Example

Пример простого бота без AI системы.
Только базовый API из protocol.py.
"""

import asyncio
from ..protocol import create_bot


async def main():
    print("=" * 50)
    print("MinePyt Basic Bot Example")
    print("=" * 50)
    print()

    # Создаём бота
    bot = await create_bot({"host": "localhost", "port": 25565, "username": "BasicBot"})

    print(f"Connected as {bot.username}")
    print(f"Position: {bot.position}")
    print(f"Health: {bot.health}/{bot.max_health}")
    print(f"Food: {bot.food}/20")
    print()

    # Простые команды
    await asyncio.sleep(2)

    # Скажем в чат
    await bot.chat("Hello from BasicBot!")

    # Подождём немного
    await asyncio.sleep(3)

    # Посмотрим на блоки вокруг
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            block = bot.block_at(
                int(bot.position[0] + dx), int(bot.position[1]), int(bot.position[2] + dz)
            )
            if block and not block.is_air:
                print(f"Block at ({dx}, 0, {dz}): {block.name}")

    print()
    print("Staying connected for 30 seconds...")
    await bot.stay_alive(duration=30.0)

    print()
    print("Disconnecting...")
    await bot.disconnect()

    print("Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
