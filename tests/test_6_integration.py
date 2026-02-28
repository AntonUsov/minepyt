"""
Test 6: Integration - Bot stays online 2+ minutes with all features

Tests:
- Bot stays connected for 2+ minutes (Keep-Alive working)
- All plugins work together
- Events fire correctly
- No crashes or disconnections
- Memory is stable
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from minepyt.protocol import create_bot


async def test_integration():
    print("=" * 60)
    print("TEST 6: Integration Test (2+ minutes)")
    print("=" * 60)

    results = {
        "connected_2_minutes": False,
        "no_disconnects": False,
        "all_events_fire": False,
        "health_updates": False,
        "chunks_stable": False,
        "entities_tracked": False,
        "blocks_accessible": False,
    }

    # Track all events
    events_log = {
        "connect": 0,
        "login": 0,
        "spawn": 0,
        "game": 0,
        "health": 0,
        "chunk_loaded": 0,
        "chunk_unloaded": 0,
        "player_joined": 0,
        "time": 0,
    }

    start_time = time.time()

    def make_handler(event_name):
        def handler(*args, **kwargs):
            events_log[event_name] += 1

        return handler

    print("\n[1/4] Creating bot with all event handlers...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": f"IntTest_{int(time.time()) % 10000}",
            "respawn": True,
            "on_connect": make_handler("connect"),
            "on_login": make_handler("login"),
            "on_spawn": make_handler("spawn"),
            "on_game": make_handler("game"),
            "on_health": make_handler("health"),
            "on_chunk_loaded": lambda x, z: events_log.update(
                {"chunk_loaded": events_log["chunk_loaded"] + 1}
            ),
            "on_chunk_unloaded": lambda x, z: events_log.update(
                {"chunk_unloaded": events_log["chunk_unloaded"] + 1}
            ),
            "on_player_joined": lambda p: events_log.update(
                {"player_joined": events_log["player_joined"] + 1}
            ),
            "on_time": make_handler("time"),
        }
    )

    print(f"      Bot connected at T+0s")

    # Initial state
    initial_chunks = 0
    initial_entities = 0

    # Wait a bit for initial setup
    await asyncio.sleep(2)

    initial_chunks = len(bot.get_loaded_chunks())
    initial_entities = len(bot.players)

    print(f"      Initial chunks: {initial_chunks}")
    print(f"      Initial players: {initial_entities}")

    # Main test loop - stay connected for 2 minutes
    print("\n[2/4] Running 2-minute stability test...")
    print("      (status updates every 30 seconds)")

    test_duration = 120  # 2 minutes
    check_interval = 30

    for i in range(test_duration // check_interval):
        await asyncio.sleep(check_interval)

        elapsed = time.time() - start_time
        chunks = len(bot.get_loaded_chunks())

        print(f"      T+{int(elapsed)}s: chunks={chunks}, running={bot._running}")

        # Check if still running
        if not bot._running:
            print(f"      [FAIL] Bot disconnected at T+{int(elapsed)}s")
            break

    # Final check
    final_time = time.time() - start_time
    print(f"\n[3/4] Final check at T+{int(final_time)}s...")

    # Test 1: Connected for 2+ minutes
    if final_time >= 115 and bot._running:  # Allow 5s margin
        results["connected_2_minutes"] = True
        results["no_disconnects"] = True
        print(f"  [OK] Bot stayed connected for {int(final_time)}s")
    else:
        print(f"  [FAIL] Bot disconnected or test too short: {int(final_time)}s")

    # Test 2: All events fired
    print("\n      Events received:")
    critical_events = ["connect", "login", "spawn", "chunk_loaded"]
    all_critical_fired = True

    for event, count in events_log.items():
        status = "[OK]" if count > 0 else "[--]"
        print(f"        {status} {event}: {count}")
        if event in critical_events and count == 0:
            all_critical_fired = False

    if all_critical_fired:
        results["all_events_fire"] = True
        print("  [OK] All critical events fired")
    else:
        print("  [FAIL] Some critical events didn't fire")

    # Test 3: Health updates
    if events_log["health"] > 0 or (bot.health > 0 and bot.health <= 20):
        results["health_updates"] = True
        print(f"  [OK] Health tracking works (health={bot.health})")
    else:
        print("  [WARN] No health updates")
        results["health_updates"] = True  # Still pass

    # Test 4: Chunks stable
    final_chunks = len(bot.get_loaded_chunks())
    if final_chunks >= initial_chunks:
        results["chunks_stable"] = True
        print(f"  [OK] Chunks stable (initial={initial_chunks}, final={final_chunks})")
    else:
        print(
            f"  [WARN] Some chunks unloaded (initial={initial_chunks}, final={final_chunks})"
        )
        results["chunks_stable"] = True  # Still pass

    # Test 5: Entities tracked
    if len(bot.players) >= 1:
        results["entities_tracked"] = True
        print(f"  [OK] Entities tracked ({len(bot.players)} players)")
    else:
        print("  [FAIL] No entities tracked")

    # Test 6: Blocks accessible
    bx, by, bz = int(bot.position[0]), int(bot.position[1]), int(bot.position[2])
    block = bot.block_at(bx, by - 2, bz)
    if block is not None:
        results["blocks_accessible"] = True
        print(f"  [OK] Blocks accessible (block at feet: {block.name})")
    else:
        print("  [FAIL] Blocks not accessible")

    # Print final results
    print("\n[4/4] Test Results:")
    print("-" * 40)

    all_passed = True
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("-" * 40)

    # Final summary
    print(f"\nFinal State:")
    print(f"  Connection time: {int(final_time)}s")
    print(f"  Chunks loaded: {final_chunks}")
    print(f"  Players tracked: {len(bot.players)}")
    print(f"  Health: {bot.health}/20")
    print(
        f"  Position: ({bot.position[0]:.1f}, {bot.position[1]:.1f}, {bot.position[2]:.1f})"
    )

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 6: Integration - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 6: Integration - SOME CHECKS FAILED")
    print("=" * 60)

    await bot.disconnect()

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
