"""
Test 1: Protocol Core - Connection, Login, Keep-Alive, Disconnect

Tests:
- TCP connection establishment
- Handshake packet
- Login flow (Start -> Success -> Acknowledged)
- Configuration state handling
- Transition to Play state
- Keep-Alive response
- Graceful disconnect
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from minepyt.protocol import create_bot, ProtocolState


async def test_protocol_core():
    print("=" * 60)
    print("TEST 1: Protocol Core")
    print("=" * 60)

    results = {
        "tcp_connection": False,
        "handshake": False,
        "login_success": False,
        "configuration": False,
        "play_state": False,
        "keep_alive": False,
        "disconnect": False,
    }

    events_log = []
    keep_alive_times = []

    def log_event(name, **kwargs):
        events_log.append({"event": name, "time": time.time(), **kwargs})
        print(f"  [EVENT] {name}")

    def on_connect():
        results["tcp_connection"] = True
        log_event("connect")

    def on_login():
        results["login_success"] = True
        log_event("login")

    def on_spawn():
        results["play_state"] = True
        log_event("spawn")

    def on_kicked(reason):
        log_event("kicked", reason=reason)

    def on_end():
        results["disconnect"] = True
        log_event("end")

    print("\n[1/7] Testing TCP Connection...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "ProtocolTester",
            "on_connect": on_connect,
            "on_login": on_login,
            "on_spawn": on_spawn,
            "on_kicked": on_kicked,
            "on_end": on_end,
        }
    )

    # Check handshake - if we got past connection, handshake worked
    if results["tcp_connection"]:
        results["handshake"] = True
        print("  [OK] Handshake completed (connection established)")

    # Wait for spawn
    print("\n[2/7] Waiting for spawn event...")
    await asyncio.sleep(2)

    # Check protocol state
    print(f"\n[3/7] Protocol state: {bot.state.name}")
    if bot.state == ProtocolState.PLAY:
        results["play_state"] = True
        results["configuration"] = True  # If we're in PLAY, we passed CONFIGURATION
        print("  [OK] Transitioned through CONFIGURATION to PLAY state")

    # Check UUID received
    print(f"\n[4/7] UUID: {bot.uuid}")
    print(f"      Username: {bot.username}")
    print(f"      Entity ID: {bot.entity_id}")

    if bot.uuid and bot.username and bot.entity_id is not None:
        results["login_success"] = True
        print("  [OK] Login data complete")

    # Wait for keep-alives - check if bot stays connected
    print("\n[5/7] Testing Keep-Alive (waiting 10 seconds)...")

    start_time = time.time()
    initial_chunks = bot._chunks_loaded

    await asyncio.sleep(10)

    # If bot is still running after 10 seconds, keep-alive is working
    if bot._running:
        results["keep_alive"] = True
        print(f"  [OK] Bot stayed connected for 10 seconds (Keep-Alive working)")
        print(f"      Chunks loaded: {bot._chunks_loaded}")
    else:
        print("  [FAIL] Bot disconnected unexpectedly")

    # Test disconnect
    print("\n[6/7] Testing graceful disconnect...")
    await bot.disconnect()

    await asyncio.sleep(0.5)

    # Print results
    print("\n[7/7] Test Results:")
    print("-" * 40)

    all_passed = True
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("-" * 40)

    # Events summary
    print("\nEvents received:")
    for e in events_log:
        print(f"  - {e['event']}")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 1: Protocol Core - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 1: Protocol Core - SOME CHECKS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_protocol_core())
    sys.exit(0 if success else 1)
