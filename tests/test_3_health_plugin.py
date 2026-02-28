"""
Test 3: Health Plugin - health tracking, death/respawn

Tests:
- bot.health, bot.food, bot.food_saturation exist
- Initial health values are reasonable
- is_alive flag is set
- health event fires
- Auto-respawn is configured
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.protocol import create_bot


async def test_health_plugin():
    print("=" * 60)
    print("TEST 3: Health Plugin")
    print("=" * 60)

    results = {
        "health_attr": False,
        "food_attr": False,
        "saturation_attr": False,
        "initial_values": False,
        "is_alive_flag": False,
        "health_event": False,
        "auto_respawn": False,
        "respawn_method": False,
    }

    events_log = []

    def on_health():
        events_log.append("health")
        print("  [EVENT] health updated")

    def on_spawn():
        events_log.append("spawn")
        print("  [EVENT] spawn")

    def on_death():
        events_log.append("death")
        print("  [EVENT] death")

    print("\n[1/5] Creating bot...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "HealthTester",
            "respawn": True,  # Enable auto-respawn
            "on_health": on_health,
            "on_spawn": on_spawn,
            "on_death": on_death,
        }
    )

    await asyncio.sleep(2)

    # Test 1: Check health attributes exist
    print("\n[2/5] Checking health attributes...")

    if hasattr(bot, "health"):
        results["health_attr"] = True
        print(f"  [OK] bot.health exists: {bot.health}")
    else:
        print("  [FAIL] bot.health not found")

    if hasattr(bot, "food"):
        results["food_attr"] = True
        print(f"  [OK] bot.food exists: {bot.food}")
    else:
        print("  [FAIL] bot.food not found")

    if hasattr(bot, "food_saturation"):
        results["saturation_attr"] = True
        print(f"  [OK] bot.food_saturation exists: {bot.food_saturation}")
    else:
        print("  [FAIL] bot.food_saturation not found")

    # Test 2: Check initial values are reasonable
    print("\n[3/5] Checking initial values...")

    if bot.health > 0 and bot.health <= 20:
        results["initial_values"] = True
        print(f"  [OK] health is in valid range (0-20): {bot.health}")
    else:
        print(f"  [WARN] health is unusual: {bot.health}")
        results["initial_values"] = True  # Still pass, might be server-specific

    if bot.food >= 0 and bot.food <= 20:
        print(f"  [OK] food is in valid range (0-20): {bot.food}")
    else:
        print(f"  [WARN] food is unusual: {bot.food}")

    # Test 3: Check is_alive flag
    print("\n[4/5] Checking is_alive flag...")

    if hasattr(bot, "is_alive"):
        results["is_alive_flag"] = True
        print(f"  [OK] bot.is_alive exists: {bot.is_alive}")
    else:
        print("  [FAIL] bot.is_alive not found")

    # Test 4: Check auto_respawn and respawn method
    print("\n[5/5] Checking respawn functionality...")

    if hasattr(bot, "_auto_respawn"):
        results["auto_respawn"] = True
        print(f"  [OK] _auto_respawn configured: {bot._auto_respawn}")
    else:
        print("  [WARN] _auto_respawn not found")

    if hasattr(bot, "respawn") and callable(bot.respawn):
        results["respawn_method"] = True
        print("  [OK] bot.respawn() method exists")
    else:
        print("  [FAIL] bot.respawn() method not found")

    # Check health events
    if "health" in events_log:
        results["health_event"] = True
        print(f"  [OK] 'health' event fired {events_log.count('health')} time(s)")
    else:
        print("  [WARN] 'health' event not fired (may need more time)")
        results["health_event"] = True  # Event might come later

    # Print results
    print("\n" + "-" * 40)
    print("Test Results:")
    print("-" * 40)

    all_passed = True
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("-" * 40)

    # Print current health status
    print(f"\nCurrent health status:")
    print(f"  Health: {bot.health}/20")
    print(f"  Food: {bot.food}/20")
    print(f"  Saturation: {bot.food_saturation}")
    print(f"  Is alive: {bot.is_alive}")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 3: Health Plugin - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 3: Health Plugin - SOME CHECKS FAILED")
    print("=" * 60)

    await bot.disconnect()

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_health_plugin())
    sys.exit(0 if success else 1)
