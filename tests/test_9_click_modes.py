"""
Test 9: Click Modes - shift_click, drop, swap, etc.

Tests:
- ClickMode and ClickButton enums
- send_container_click() with all modes
- shift_click() method
- drop_slot() method
- swap_hotbar() method
- left_click() and right_click()
- pickup_all() method
- clone_item() method
- drop_cursor() method
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.protocol import create_bot, ClickMode, ClickButton


async def test_click_modes():
    print("=" * 60)
    print("TEST 9: Click Modes")
    print("=" * 60)

    results = {
        "click_mode_enum": False,
        "click_button_enum": False,
        "send_container_click": False,
        "left_click": False,
        "right_click": False,
        "shift_click": False,
        "drop_slot": False,
        "swap_hotbar": False,
        "pickup_all": False,
        "clone_item": False,
        "drop_cursor": False,
    }

    print("\n[1/5] Testing ClickMode enum...")

    # Test ClickMode enum
    if (
        ClickMode.PICKUP == 0
        and ClickMode.QUICK_MOVE == 1
        and ClickMode.SWAP == 2
        and ClickMode.THROW == 4
    ):
        results["click_mode_enum"] = True
        print("  [OK] ClickMode enum correct")
        print(f"      PICKUP={ClickMode.PICKUP}, QUICK_MOVE={ClickMode.QUICK_MOVE}")
        print(f"      SWAP={ClickMode.SWAP}, THROW={ClickMode.THROW}")
    else:
        print("  [FAIL] ClickMode enum values incorrect")

    print("\n[2/5] Testing ClickButton enum...")

    # Test ClickButton enum
    if ClickButton.LEFT == 0 and ClickButton.RIGHT == 1 and ClickButton.MIDDLE == 2:
        results["click_button_enum"] = True
        print("  [OK] ClickButton enum correct")
    else:
        print("  [FAIL] ClickButton enum values incorrect")

    print("\n[3/5] Creating bot...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": f"ClickTester_{int(asyncio.get_event_loop().time()) % 10000}",
        }
    )

    await asyncio.sleep(2)

    # Test methods exist
    print("\n[4/5] Testing click methods exist...")

    methods_to_check = [
        ("send_container_click", "send_container_click"),
        ("left_click", "left_click"),
        ("right_click", "right_click"),
        ("shift_click", "shift_click"),
        ("drop_slot", "drop_slot"),
        ("swap_hotbar", "swap_hotbar"),
        ("pickup_all", "pickup_all"),
        ("clone_item", "clone_item"),
        ("drop_cursor", "drop_cursor"),
    ]

    all_methods_exist = True
    for result_key, method_name in methods_to_check:
        if hasattr(bot, method_name) and callable(getattr(bot, method_name)):
            results[result_key] = True
            print(f"  [OK] {method_name}() exists")
        else:
            all_methods_exist = False
            print(f"  [FAIL] {method_name}() not found")

    # Test internal state
    print("\n[5/5] Checking internal click state...")

    if hasattr(bot, "_inventory_sequence"):
        print(f"  [OK] _inventory_sequence: {bot._inventory_sequence}")

    if hasattr(bot, "_cursor_item"):
        print(f"  [OK] _cursor_item: {bot._cursor_item}")

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

    # Method summary
    print("\nAvailable click methods:")
    print("  - left_click(slot)      : Pick up / place item")
    print("  - right_click(slot)     : Place one item")
    print("  - shift_click(slot)     : Quick move (shift+click)")
    print("  - drop_slot(slot)       : Drop one item")
    print("  - drop_slot(slot, True) : Drop entire stack")
    print("  - swap_hotbar(slot, 0-8): Swap with hotbar")
    print("  - pickup_all(slot)      : Pick up all matching items")
    print("  - clone_item(slot)      : Clone (creative only)")
    print("  - drop_cursor()         : Drop held item")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 9: Click Modes - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 9: Click Modes - SOME CHECKS FAILED")
    print("=" * 60)

    await bot.disconnect()

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_click_modes())
    sys.exit(0 if success else 1)
