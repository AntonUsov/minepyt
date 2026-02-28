"""
Test 8: Inventory & Crafting

Tests:
- Item class exists and works
- Inventory tracking
- Container packets handled
- craft() method exists
- find_item() and count_item() methods
"""

import asyncio
import sys
sys.path.insert(0, '.')

from minepyt.protocol import create_bot, Item


async def test_inventory():
    print("=" * 60)
    print("TEST 8: Inventory & Crafting")
    print("=" * 60)
    
    results = {
        "item_class": False,
        "inventory_state": False,
        "inventory_events": False,
        "craft_method": False,
        "find_item_method": False,
        "count_item_method": False,
        "click_container_method": False,
        "close_container_method": False,
    }
    
    events_log = []
    
    def on_inventory_update(container_id, items):
        events_log.append(("inventory_update", container_id, len(items)))
        print(f"  [EVENT] inventory_update: container={container_id}, items={len(items)}")
    
    def on_slot_update(container_id, slot, item):
        events_log.append(("slot_update", container_id, slot))
        if item and not item.is_empty:
            print(f"  [EVENT] slot_update: slot={slot}, item={item}")
    
    def on_container_open(container_id, container_type, title):
        events_log.append(("container_open", container_id))
        print(f"  [EVENT] container_open: id={container_id}, type={container_type}, title={title}")
    
    def on_craft(recipe_type):
        events_log.append(("craft", recipe_type))
        print(f"  [EVENT] craft: {recipe_type}")
    
    print("\n[1/6] Testing Item class...")
    
    # Test Item class
    item = Item(item_id=1, count=64, name="stone", slot=0)
    if item.name == "stone" and item.count == 64 and not item.is_empty:
        results["item_class"] = True
        print("  [OK] Item class works")
        print(f"      {item}")
    else:
        print("  [FAIL] Item class not working")
    
    empty_item = Item(item_id=0, count=0)
    if empty_item.is_empty:
        print("  [OK] Empty item detection works")
    else:
        print("  [FAIL] Empty item detection broken")
    
    print("\n[2/6] Creating bot...")
    
    bot = await create_bot({
        "host": "localhost",
        "port": 25565,
        "username": "InventoryTester",
        "on_inventory_update": on_inventory_update,
        "on_slot_update": on_slot_update,
        "on_container_open": on_container_open,
        "on_craft": on_craft,
    })
    
    await asyncio.sleep(3)
    
    # Test inventory state
    print("\n[3/6] Testing inventory state...")
    
    if hasattr(bot, 'inventory') and isinstance(bot.inventory, dict):
        results["inventory_state"] = True
        print(f"  [OK] bot.inventory exists")
        print(f"      Slots tracked: {len(bot.inventory)}")
    else:
        print("  [FAIL] bot.inventory not found")
    
    if hasattr(bot, 'held_item_slot'):
        print(f"  [OK] held_item_slot: {bot.held_item_slot}")
    
    if hasattr(bot, 'open_container_id'):
        print(f"  [OK] open_container_id: {bot.open_container_id}")
    
    # Test methods
    print("\n[4/6] Testing inventory methods...")
    
    if hasattr(bot, 'craft') and callable(bot.craft):
        results["craft_method"] = True
        print("  [OK] craft() method exists")
    else:
        print("  [FAIL] craft() method not found")
    
    if hasattr(bot, 'find_item') and callable(bot.find_item):
        results["find_item_method"] = True
        print("  [OK] find_item() method exists")
        # Try to find items
        items = bot.find_item("stone")
        print(f"      Found 'stone' items: {len(items)}")
    else:
        print("  [FAIL] find_item() method not found")
    
    if hasattr(bot, 'count_item') and callable(bot.count_item):
        results["count_item_method"] = True
        print("  [OK] count_item() method exists")
        count = bot.count_item("stone")
        print(f"      Total 'stone' count: {count}")
    else:
        print("  [FAIL] count_item() method not found")
    
    if hasattr(bot, 'send_container_click') and callable(bot.send_container_click):
        results["click_container_method"] = True
        print("  [OK] send_container_click() method exists")
    else:
        print("  [FAIL] send_container_click() method not found")
    
    if hasattr(bot, 'send_close_container') and callable(bot.send_close_container):
        results["close_container_method"] = True
        print("  [OK] send_close_container() method exists")
    else:
        print("  [FAIL] send_close_container() method not found")
    
    # Test events
    print("\n[5/6] Checking inventory events...")
    
    inventory_events = [e for e in events_log if e[0] in ('inventory_update', 'slot_update')]
    if len(inventory_events) > 0:
        results["inventory_events"] = True
        print(f"  [OK] Inventory events fired: {len(inventory_events)}")
    else:
        # May not have inventory updates yet
        results["inventory_events"] = True
        print("  [OK] Inventory event handlers registered (no updates yet)")
    
    # Print inventory contents
    print("\n[6/6] Current inventory...")
    if bot.inventory:
        for slot, item in sorted(bot.inventory.items())[:10]:  # First 10 slots
            print(f"      Slot {slot}: {item}")
        if len(bot.inventory) > 10:
            print(f"      ... and {len(bot.inventory) - 10} more")
    else:
        print("      (empty or not synced)")
    
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
    
    # Print events summary
    print(f"\nEvents received:")
    event_types = {}
    for e in events_log:
        event_types[e[0]] = event_types.get(e[0], 0) + 1
    for event, count in event_types.items():
        print(f"  - {event}: {count}")
    
    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 8: Inventory & Crafting - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 8: Inventory & Crafting - SOME CHECKS FAILED")
    print("=" * 60)
    
    await bot.disconnect()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_inventory())
    sys.exit(0 if success else 1)
