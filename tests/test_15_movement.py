"""
Test 15: Movement System

Tests:
- Control states (forward, back, left, right, jump, sprint, sneak)
- Position updates
- Look at position
- Basic movement
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from minepyt.protocol import create_bot, ProtocolState


async def test_movement():
    print("=" * 60)
    print("TEST 15: Movement System")
    print("=" * 60)

    results = {
        "control_states": False,
        "look_at": False,
        "move_forward": False,
        "position_updates": False,
    }

    events_log = []

    def log_event(name, **kwargs):
        events_log.append({"event": name, "time": time.time(), **kwargs})
        print(f"  [EVENT] {name}")

    def on_spawn():
        log_event("spawn")

    def on_move():
        log_event("move")

    def on_physics_tick():
        log_event("physicsTick")

    print("\n[1/5] Creating bot...")
    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "MovementTester",
            "on_spawn": on_spawn,
            "on_physicsTick": on_physics_tick,
        }
    )

    # Wait for spawn
    print("\n[2/5] Waiting for spawn...")
    await asyncio.sleep(2)

    if bot.state == ProtocolState.PLAY:
        print(f"  [OK] Bot spawned at {bot.position}")

    # Test control states
    print("\n[3/5] Testing control states...")
    try:
        bot.set_control_state("forward", True)
        forward_state = bot.get_control_state("forward")
        bot.set_control_state("forward", False)

        bot.set_control_state("sprint", True)
        sprint_state = bot.get_control_state("sprint")
        bot.set_control_state("sprint", False)

        if forward_state and sprint_state:
            results["control_states"] = True
            print("  [OK] Control states work")
    except Exception as e:
        print(f"  [FAIL] Control states error: {e}")

    # Test look_at
    print("\n[4/5] Testing look_at...")
    try:
        initial_yaw = bot.yaw
        await bot.look_at(bot.position[0] + 10, bot.position[1], bot.position[2] + 10)
        if bot.yaw != initial_yaw:
            results["look_at"] = True
            print(f"  [OK] look_at works (yaw changed from {initial_yaw:.1f} to {bot.yaw:.1f})")
        else:
            print("  [WARN] look_at didn't change yaw")
    except Exception as e:
        print(f"  [FAIL] look_at error: {e}")

    # Test movement
    print("\n[5/5] Testing movement for 5 seconds...")
    try:
        initial_pos = bot.position
        bot.start_physics()
        bot.set_control_state("forward", True)

        await asyncio.sleep(5)

        bot.set_control_state("forward", False)
        bot.stop_physics()

        final_pos = bot.position

        dx = final_pos[0] - initial_pos[0]
        dz = final_pos[2] - initial_pos[2]
        dist_moved = (dx**2 + dz**2) ** 0.5

        if dist_moved > 0.5:  # Should have moved at least 0.5 blocks
            results["move_forward"] = True
            print(f"  [OK] Moved {dist_moved:.2f} blocks")
        else:
            print(f"  [WARN] Only moved {dist_moved:.2f} blocks (physics may not be working)")

        results["position_updates"] = True
    except Exception as e:
        print(f"  [FAIL] Movement error: {e}")

    # Disconnect
    print("\nDisconnecting...")
    await bot.disconnect()

    # Print results
    print("\n" + "-" * 40)
    all_passed = True
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("-" * 40)

    # Events summary
    print(f"\nPhysics ticks: {len([e for e in events_log if e['event'] == 'physicsTick'])}")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 15: Movement System - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 15: Movement System - SOME CHECKS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_movement())
    sys.exit(0 if success else 1)
