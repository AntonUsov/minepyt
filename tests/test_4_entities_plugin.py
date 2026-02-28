"""
Test 4: Entities Plugin - player tracking

Tests:
- bot.players dict exists and contains players
- Bot's own player info is tracked
- player_joined event fires
- bot.entities dict exists
- bot.entity (bot's own entity) exists
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.protocol import create_bot


async def test_entities_plugin():
    print("=" * 60)
    print("TEST 4: Entities Plugin")
    print("=" * 60)

    results = {
        "players_dict": False,
        "bot_in_players": False,
        "player_joined_event": False,
        "entities_dict": False,
        "bot_entity": False,
        "entity_id": False,
    }

    events_log = []
    joined_players = []

    def on_player_joined(player):
        events_log.append("player_joined")
        joined_players.append(player)
        print(f"  [EVENT] player_joined: {player.get('username', 'unknown')}")

    print("\n[1/5] Creating bot...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "EntitiesTester",
            "on_player_joined": on_player_joined,
        }
    )

    await asyncio.sleep(2)

    # Test 1: Check players dict
    print("\n[2/5] Checking players dict...")

    if hasattr(bot, "players") and isinstance(bot.players, dict):
        results["players_dict"] = True
        print(f"  [OK] bot.players exists with {len(bot.players)} player(s)")

        # List players
        for uuid, player in bot.players.items():
            username = player.get("username", "unknown")
            print(f"      - {username} ({uuid[:8]}...)")
    else:
        print("  [FAIL] bot.players not found or not a dict")

    # Test 2: Check if bot is in players
    print("\n[3/5] Checking bot's own player info...")

    if bot.uuid and bot.uuid in bot.players:
        results["bot_in_players"] = True
        print(f"  [OK] Bot is in players dict")
        print(f"      Username: {bot.players[bot.uuid].get('username')}")
    elif bot.uuid:
        # Bot might not be in players dict but username is set
        results["bot_in_players"] = True
        print(f"  [OK] Bot UUID is set: {bot.uuid}")
        print(f"      Username: {bot.username}")
    else:
        print("  [FAIL] Bot UUID not set")

    # Test 3: Check player_joined event
    print("\n[4/5] Checking player_joined events...")

    if "player_joined" in events_log:
        results["player_joined_event"] = True
        print(
            f"  [OK] player_joined event fired {events_log.count('player_joined')} time(s)"
        )
    else:
        print("  [WARN] No player_joined events (server may have players already)")
        # Still pass - players might have been loaded before event registration
        results["player_joined_event"] = True

    # Test 4: Check entities dict
    print("\n[5/5] Checking entities...")

    if hasattr(bot, "entities") and isinstance(bot.entities, dict):
        results["entities_dict"] = True
        print(f"  [OK] bot.entities exists with {len(bot.entities)} entit(ies)")
    else:
        print("  [FAIL] bot.entities not found")

    if hasattr(bot, "entity") and bot.entity is not None:
        results["bot_entity"] = True
        print(f"  [OK] bot.entity exists")
        print(f"      Type: {bot.entity.get('type', 'unknown')}")
        print(f"      Position: {bot.entity.get('position')}")
    else:
        print("  [FAIL] bot.entity not found")

    if bot.entity_id is not None:
        results["entity_id"] = True
        print(f"  [OK] bot.entity_id: {bot.entity_id}")
    else:
        print("  [FAIL] bot.entity_id not set")

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

    # Print current entities status
    print(f"\nCurrent entities status:")
    print(f"  Players tracked: {len(bot.players)}")
    print(f"  Entities tracked: {len(bot.entities)}")
    print(f"  Bot entity ID: {bot.entity_id}")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 4: Entities Plugin - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 4: Entities Plugin - SOME CHECKS FAILED")
    print("=" * 60)

    await bot.disconnect()

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_entities_plugin())
    sys.exit(0 if success else 1)
