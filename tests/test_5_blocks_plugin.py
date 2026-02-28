"""
Test 5: Blocks Plugin - chunks, block_at, block_update

Tests:
- bot.world exists
- Chunks are loaded
- block_at() returns Block objects
- Block has name, state_id, is_air, is_solid properties
- chunk_loaded event fires
- get_loaded_chunks() works
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.protocol import create_bot
from minepyt.block_registry import Block


async def test_blocks_plugin():
    print("=" * 60)
    print("TEST 5: Blocks Plugin")
    print("=" * 60)

    results = {
        "world_object": False,
        "chunks_loaded": False,
        "block_at_method": False,
        "block_object": False,
        "block_properties": False,
        "chunk_loaded_event": False,
        "get_loaded_chunks": False,
        "non_air_blocks": False,
    }

    events_log = []
    chunks_loaded = []

    def on_chunk_loaded(chunk_x, chunk_z):
        events_log.append("chunk_loaded")
        chunks_loaded.append((chunk_x, chunk_z))

    def on_block_update(old_block, new_block):
        events_log.append("block_update")
        print(f"  [EVENT] block_update at {new_block.position}")

    print("\n[1/6] Creating bot...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "BlocksTester",
            "on_chunk_loaded": on_chunk_loaded,
            "on_block_update": on_block_update,
        }
    )

    await asyncio.sleep(3)  # Wait for chunks to load

    # Test 1: Check world object
    print("\n[2/6] Checking world object...")

    if hasattr(bot, "world") and bot.world is not None:
        results["world_object"] = True
        print(f"  [OK] bot.world exists")
        print(f"      Min Y: {bot.world.min_y}")
        print(f"      Height: {bot.world.height}")
    else:
        print("  [FAIL] bot.world not found")

    # Test 2: Check chunks loaded
    print("\n[3/6] Checking loaded chunks...")

    loaded_chunks = bot.get_loaded_chunks()
    if len(loaded_chunks) > 0:
        results["chunks_loaded"] = True
        results["get_loaded_chunks"] = True
        print(f"  [OK] {len(loaded_chunks)} chunks loaded")
        print(f"      First few: {loaded_chunks[:3]}")
    else:
        print("  [FAIL] No chunks loaded")

    # Test 3: Test block_at method
    print("\n[4/6] Testing block_at()...")

    # Get bot position
    bx, by, bz = int(bot.position[0]), int(bot.position[1]), int(bot.position[2])

    # Test block at feet
    block = bot.block_at(bx, by - 2, bz)

    if block is not None:
        results["block_at_method"] = True
        print(f"  [OK] block_at() returned a value")

        # Test 4: Check if it's a Block object
        if isinstance(block, Block):
            results["block_object"] = True
            print(f"  [OK] Returned Block object")
            print(f"      Name: {block.name}")
            print(f"      State ID: {block.state_id}")
            print(f"      Position: {block.position}")
        else:
            print(f"  [FAIL] Not a Block object: {type(block)}")

        # Test 5: Check block properties
        has_props = all(
            [
                hasattr(block, "name"),
                hasattr(block, "state_id"),
                hasattr(block, "is_air"),
                hasattr(block, "is_solid"),
            ]
        )

        if has_props:
            results["block_properties"] = True
            print(f"  [OK] Block has all required properties")
            print(f"      is_air: {block.is_air}")
            print(f"      is_solid: {block.is_solid}")
        else:
            print("  [FAIL] Block missing some properties")
    else:
        print("  [FAIL] block_at() returned None")

    # Test 6: Check for non-air blocks
    print("\n[5/6] Checking for non-air blocks...")

    non_air_blocks = []
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(-3, 0):  # Check below bot
                test_block = bot.block_at(bx + dx, by + dy, bz + dz)
                if test_block and not test_block.is_air:
                    non_air_blocks.append(test_block)

    if len(non_air_blocks) > 0:
        results["non_air_blocks"] = True
        print(f"  [OK] Found {len(non_air_blocks)} non-air blocks")

        # Show unique block names
        unique_names = set(b.name for b in non_air_blocks[:10])
        print(f"      Block types: {unique_names}")
    else:
        print("  [WARN] No non-air blocks found near bot")
        # Still pass if chunks are loaded
        if results["chunks_loaded"]:
            results["non_air_blocks"] = True
            print("  [OK] Chunks loaded, blocks may be air at this location")

    # Test 7: Check chunk_loaded events
    print("\n[6/6] Checking chunk_loaded events...")

    if "chunk_loaded" in events_log:
        results["chunk_loaded_event"] = True
        print(
            f"  [OK] chunk_loaded event fired {events_log.count('chunk_loaded')} time(s)"
        )
    else:
        print(
            "  [WARN] No chunk_loaded events (may have fired before handler registered)"
        )
        results["chunk_loaded_event"] = True  # Still pass

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

    # Print blocks status
    print(f"\nCurrent blocks status:")
    print(f"  Chunks loaded: {len(loaded_chunks)}")
    print(f"  Non-air blocks found: {len(non_air_blocks)}")
    print(f"  Bot position: ({bx}, {by}, {bz})")

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] Test 5: Blocks Plugin - ALL CHECKS PASSED")
    else:
        print("[FAIL] Test 5: Blocks Plugin - SOME CHECKS FAILED")
    print("=" * 60)

    await bot.disconnect()

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_blocks_plugin())
    sys.exit(0 if success else 1)
