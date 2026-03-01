"""
Test connection with the refactored protocol module.

This script tests:
1. Bot creation
2. Connection to server
3. Login flow
4. Stay alive for a few seconds
5. Graceful disconnect
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt import Bot, create_bot, MinecraftProtocol
from minepyt.protocol import create_bot as create_bot_async


async def test_connection():
    print("=" * 60)
    print("Testing refactored protocol module")
    print("=" * 60)

    # Test 1: Create bot using sync API
    print("\n[1/4] Testing Bot creation (sync API)...")
    bot = create_bot({"host": "localhost", "port": 25565, "username": "RefactorTestBot"})
    print(f"  Bot created: {bot.username}")
    print(f"  Host: {bot.host}:{bot.port}")

    # Test 2: Connect
    print("\n[2/4] Testing connection...")
    try:
        await bot.connect()
        print("  [OK] Connection initiated")
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        print("  Make sure a Minecraft 1.21.4 server is running on localhost:25565")
        return False

    # Test 3: Wait for spawn
    print("\n[3/4] Waiting for spawn (5 seconds)...")
    spawned = await bot.wait_for_spawn(timeout=5.0)
    if spawned:
        print(f"  [OK] Bot spawned at position: {bot.position}")
    else:
        print("  [WARN] Spawn timeout - bot may still be connecting")

    # Stay alive for a few seconds
    print("\n[4/4] Testing stay_alive (3 seconds)...")
    await bot.stay_alive(duration=3.0)
    print("  [OK] Stayed alive")

    # Disconnect
    print("\nDisconnecting...")
    bot.quit("Test complete")
    await asyncio.sleep(0.5)

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    return True


async def test_protocol_directly():
    """Test using MinecraftProtocol directly"""
    print("\n" + "=" * 60)
    print("Testing MinecraftProtocol directly")
    print("=" * 60)

    events = []

    def log_event(name):
        events.append(name)
        print(f"  [EVENT] {name}")

    try:
        bot = await create_bot_async(
            {
                "host": "localhost",
                "port": 25565,
                "username": "DirectProtocolTest",
                "on_spawn": lambda: log_event("spawn"),
                "on_login": lambda: log_event("login"),
                "on_connect": lambda: log_event("connect"),
                "on_kicked": lambda r: log_event(f"kicked: {r}"),
                "on_end": lambda: log_event("end"),
            }
        )

        print(f"  Connected! UUID: {bot.uuid}")
        print(f"  State: {bot.state.name}")

        # Stay for 3 seconds
        await bot.stay_alive(duration=3.0)

        # Disconnect
        await bot.disconnect()

        print(f"  Events received: {events}")
        return True

    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Test Bot class (high-level API)")
    print("2. Test MinecraftProtocol directly (low-level API)")
    print("3. Run both tests")

    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        success = asyncio.run(test_connection())
    elif choice == "2":
        success = asyncio.run(test_protocol_directly())
    else:
        success1 = asyncio.run(test_connection())
        success2 = asyncio.run(test_protocol_directly())
        success = success1 and success2

    sys.exit(0 if success else 1)
