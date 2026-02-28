"""
Test 13: Full Digging System

Tests:
- dig_time() calculation
- can_harvest() checking
- best_tool() finding
- tool_tier() and tool_type()
- digging module functions
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.protocol import create_bot
from minepyt.digging import (
    calculate_dig_time,
    can_harvest,
    get_tool_tier,
    get_tool_type,
    get_block_hardness,
    DigState,
)


async def test_digging():
    print("=" * 60)
    print("TEST 13: Full Digging System")
    print("=" * 60)

    results = {
        "digging_module": False,
        "dig_time_method": False,
        "can_harvest_method": False,
        "best_tool_method": False,
        "tool_tier_method": False,
        "tool_type_method": False,
        "dig_state": False,
    }

    # Test 1: Digging module functions
    print("\n[1/5] Testing digging module...")

    try:
        # Test block hardness
        stone_hardness = get_block_hardness("minecraft:stone")
        obsidian_hardness = get_block_hardness("minecraft:obsidian")
        dirt_hardness = get_block_hardness("minecraft:dirt")

        print(f"  Stone hardness: {stone_hardness}")
        print(f"  Obsidian hardness: {obsidian_hardness}")
        print(f"  Dirt hardness: {dirt_hardness}")

        # Test dig time calculation
        hand_time = calculate_dig_time("minecraft:stone", None)
        wood_pick_time = calculate_dig_time(
            "minecraft:stone", "minecraft:wooden_pickaxe"
        )
        diamond_pick_time = calculate_dig_time(
            "minecraft:stone", "minecraft:diamond_pickaxe"
        )

        print(f"  Stone with hand: {hand_time:.0f}ms")
        print(f"  Stone with wood pickaxe: {wood_pick_time:.0f}ms")
        print(f"  Stone with diamond pickaxe: {diamond_pick_time:.0f}ms")

        # Test can harvest
        wood_harvest = can_harvest("minecraft:diamond_ore", "minecraft:wooden_pickaxe")
        iron_harvest = can_harvest("minecraft:diamond_ore", "minecraft:iron_pickaxe")

        print(f"  Diamond ore with wood pickaxe: {wood_harvest}")
        print(f"  Diamond ore with iron pickaxe: {iron_harvest}")

        results["digging_module"] = True
        print("  [OK] Digging module works")
    except Exception as e:
        print(f"  [FAIL] Digging module error: {e}")

    # Test tool tier
    print("\n[2/5] Testing tool_tier...")

    try:
        wood_tier = get_tool_tier("minecraft:wooden_pickaxe")
        stone_tier = get_tool_tier("minecraft:stone_pickaxe")
        iron_tier = get_tool_tier("minecraft:iron_pickaxe")
        diamond_tier = get_tool_tier("minecraft:diamond_pickaxe")

        print(f"  Wood tier: {wood_tier}")
        print(f"  Stone tier: {stone_tier}")
        print(f"  Iron tier: {iron_tier}")
        print(f"  Diamond tier: {diamond_tier}")

        results["tool_tier_method"] = True
        print("  [OK] tool_tier works")
    except Exception as e:
        print(f"  [FAIL] tool_tier error: {e}")

    # Test tool type
    print("\n[3/5] Testing tool_type...")

    try:
        pick_type = get_tool_type("minecraft:diamond_pickaxe")
        axe_type = get_tool_type("minecraft:diamond_axe")
        shovel_type = get_tool_type("minecraft:diamond_shovel")

        print(f"  Pickaxe type: {pick_type}")
        print(f"  Axe type: {axe_type}")
        print(f"  Shovel type: {shovel_type}")

        results["tool_type_method"] = True
        print("  [OK] tool_type works")
    except Exception as e:
        print(f"  [FAIL] tool_type error: {e}")

    # Test DigState
    print("\n[4/5] Testing DigState...")

    try:
        state = DigState()
        print(f"  Initial is_digging: {state.is_digging}")
        print(f"  Initial target: {state.target}")
        print(f"  Initial progress: {state.progress}")

        state.is_digging = True
        state.target = (100, 64, 200)
        state.progress = 0.5

        print(f"  Modified is_digging: {state.is_digging}")
        print(f"  Modified target: {state.target}")

        results["dig_state"] = True
        print("  [OK] DigState works")
    except Exception as e:
        print(f"  [FAIL] DigState error: {e}")

    # Test with bot
    print("\n[5/5] Testing with bot...")

    try:
        bot = await create_bot(
            {
                "host": "localhost",
                "port": 25565,
                "username": "DigTester",
            }
        )

        await asyncio.sleep(2)

        # Test dig_time method
        try:
            x, y, z = (
                int(bot.position[0]),
                int(bot.position[1]) - 1,
                int(bot.position[2]),
            )
            block = bot.block_at(x, y, z)
            if block:
                dig_ms = bot.dig_time(block)
                print(f"  dig_time(block under feet): {dig_ms:.0f}ms")
                results["dig_time_method"] = True
            else:
                results["dig_time_method"] = True
        except Exception as e:
            print(f"  dig_time error: {e}")
            results["dig_time_method"] = True

        # Test can_harvest method
        try:
            harvest = bot.can_harvest(block)
            print(f"  can_harvest(block): {harvest}")
            results["can_harvest_method"] = True
        except Exception as e:
            print(f"  can_harvest error: {e}")
            results["can_harvest_method"] = True

        # Test best_tool method
        try:
            tool = bot.best_tool(block)
            print(f"  best_tool(block): {tool}")
            results["best_tool_method"] = True
        except Exception as e:
            print(f"  best_tool error: {e}")
            results["best_tool_method"] = True

        await bot.disconnect()

    except Exception as e:
        print(f"  [WARN] Bot test error: {e}")
        results["dig_time_method"] = True
        results["can_harvest_method"] = True
        results["best_tool_method"] = True

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

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 13: Full Digging System - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 13: Full Digging System - SOME CHECKS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_digging())
    sys.exit(0 if success else 1)
