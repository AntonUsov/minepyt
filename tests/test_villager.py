"""
Test villager trading functionality

This test demonstrates:
- Finding nearby villagers
- Opening villager trading windows
- Viewing available trades
- Executing trades
"""

import asyncio
from minepyt.protocol import create_bot


async def test_villager_trading():
    """Test villager trading functionality"""
    print("Creating bot...")

    def on_spawn():
        print(f"Bot spawned at {bot.position}")

    def on_chat(text, json_data, overlay):
        print(f"[CHAT] {text}")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": "VillagerTrader",
            "on_spawn": on_spawn,
            "on_chat": on_chat,
        }
    )

    print("Waiting for spawn...")
    await asyncio.sleep(5)

    # Find nearest villager
    print("\nSearching for villagers...")
    villager = bot.nearest_villager(max_distance=16.0)

    if not villager:
        print("No villager found nearby!")
        await bot.disconnect()
        return

    print(f"Found villager at {villager.position}")

    # Open villager trading window
    print("\nOpening villager trading window...")
    try:
        villager_window = await bot.open_villager(villager)
        print(f"Opened trading window with {len(villager_window.trades)} trades")

        # Display all available trades
        print("\n=== Available Trades ===")
        for i, trade in enumerate(villager_window.trades):
            if trade.is_available:
                input1_name = trade.input_item1.name if trade.input_item1 else "Empty"
                input1_count = trade.input_item1.item_count if trade.input_item1 else 0
                input2_name = trade.input_item2.name if trade.input_item2 else ""
                input2_count = trade.input_item2.item_count if trade.input_item2 else 0
                output_name = trade.output_item.name if trade.output_item else "Empty"
                output_count = trade.output_item.item_count if trade.output_item else 0

                trade_str = f"{i}: "
                trade_str += f"{input1_count} {input1_name}"
                if trade.has_item2:
                    trade_str += f" + {input2_count} {input2_name}"
                trade_str += f" -> {output_count} {output_name}"
                trade_str += f" (Uses: {trade.nb_trade_uses}/{trade.maximum_nb_trade_uses})"
                print(trade_str)

        # Try to execute a simple trade (first available trade)
        if villager_window.trades:
            first_trade = villager_window.trades[0]
            if first_trade.is_available:
                print(f"\nAttempting to execute trade 0...")
                print(
                    f"Trade: {first_trade.input_item1.item_count} {first_trade.input_item1.name} -> {first_trade.output_item.item_count} {first_trade.output_item.name}"
                )

                try:
                    await bot.trade(villager_window, 0, 1)
                    print("Trade executed successfully!")
                except RuntimeError as e:
                    print(f"Trade failed: {e}")
            else:
                print("First trade is not available")
        else:
            print("No trades available")

        # Close the villager window
        await villager_window.close()
        print("\nClosed villager window")

    except Exception as e:
        print(f"Error during villager trading: {e}")
        import traceback

        traceback.print_exc()

    # Stay connected for a bit
    print("\nStaying connected for 10 seconds...")
    await asyncio.sleep(10)

    # Disconnect
    await bot.disconnect()
    print("\nDisconnected!")


if __name__ == "__main__":
    asyncio.run(test_villager_trading())
