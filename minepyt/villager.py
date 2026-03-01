"""
Villager trading system for Minecraft 1.21.4

This module provides:
- Villager trading interface
- Trade execution and validation
- Merchant window handling
- Villager interaction methods

Port of mineflayer/lib/plugins/villager.js
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item


@dataclass
class Trade:
    """
    Represents a single trade offered by a villager

    Attributes:
        input_item1: First item required for trade (emeralds, etc.)
        input_item2: Optional second item required for trade
        output_item: Item received from trade
        has_item2: Whether a second input item is required
        trade_disabled: Whether this trade is disabled
        nb_trade_uses: Number of times this trade has been used
        maximum_nb_trade_uses: Maximum times this trade can be used
        real_price: Adjusted price based on demand/reputation
        demand: Demand multiplier for price (optional)
        special_price: Special price modifier (optional)
        price_multiplier: Price multiplier (optional)
    """

    input_item1: Optional["Item"] = None
    input_item2: Optional["Item"] = None
    output_item: Optional["Item"] = None
    has_item2: bool = False
    trade_disabled: bool = False
    nb_trade_uses: int = 0
    maximum_nb_trade_uses: int = 12
    real_price: int = 0
    demand: int = 0
    special_price: int = 0
    price_multiplier: float = 0.0

    @property
    def inputs(self) -> List["Item"]:
        """Get all input items for this trade"""
        items = []
        if self.input_item1 and not self.input_item1.is_empty:
            items.append(self.input_item1)
        if self.input_item2 and not self.input_item2.is_empty:
            items.append(self.input_item2)
        return items

    @property
    def outputs(self) -> List["Item"]:
        """Get all output items for this trade"""
        items = []
        if self.output_item and not self.output_item.is_empty:
            items.append(self.output_item)
        return items

    @property
    def remaining_uses(self) -> int:
        """Get remaining uses for this trade"""
        return max(0, self.maximum_nb_trade_uses - self.nb_trade_uses)

    @property
    def is_available(self) -> bool:
        """Check if this trade is available"""
        return (
            not self.trade_disabled
            and self.remaining_uses > 0
            and self.output_item is not None
            and not self.output_item.is_empty
        )


class VillagerWindow:
    """
    Represents an open villager trading window

    This is a specialized window type (WindowType.VILLAGER = 7) with 3 slots:
    - Slot 0: First input item slot
    - Slot 1: Second input item slot
    - Slot 2: Output item slot
    """

    def __init__(self, window_id: int, villager_entity: Any, protocol: "MinecraftProtocol"):
        self.window_id = window_id
        self.villager_entity = villager_entity
        self.protocol = protocol
        self.trades: List[Trade] = []
        self.selected_trade: Optional[Trade] = None
        self.ready: bool = False
        self._closed: bool = False

        # Villager slots
        self.slots: Dict[int, Optional["Item"]] = {0: None, 1: None, 2: None}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        """Register event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        """Register one-time event handler"""

        def wrapper(*args, **kwargs):
            self.remove_handler(event, wrapper)
            return handler(*args, **kwargs)

        self.on(event, wrapper)

    def remove_handler(self, event: str, handler: Callable) -> None:
        """Remove event handler"""
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event][:]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    print(f"Error in villager event handler for '{event}': {e}")

    def update_slot(self, slot: int, item: Optional["Item"]) -> None:
        """Update a slot in the villager window"""
        if 0 <= slot <= 2:
            self.slots[slot] = item
            self.emit("updateSlot", slot, item)
        else:
            self.emit("updateSlot", slot, item)

    def set_trades(self, trades: List[Trade]) -> None:
        """Set the available trades for this villager"""
        self.trades = trades
        if not self.ready:
            self.ready = True
            self.emit("ready")

    async def close(self) -> None:
        """Close the villager window"""
        if not self._closed:
            self._closed = True
            self.emit("close")

            # Close the container window
            if self.protocol and self.protocol._inventory_mgr:
                await self.protocol._inventory_mgr.close_window()


class VillagerManager:
    """
    Manager for villager trading operations

    This class handles:
    - Opening villager trading windows
    - Executing trades
    - Managing trade state
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self._villager_window: Optional[VillagerWindow] = None

    async def open_villager(self, villager_entity: Any) -> VillagerWindow:
        """
        Open a villager trading window

        Args:
            villager_entity: The villager entity to trade with

        Returns:
            VillagerWindow instance

        Raises:
            ValueError: If entity is not a villager
            TimeoutError: If window doesn't open in time
        """
        from .entities import MobType

        # Validate entity type
        if villager_entity.mob_type != MobType.VILLAGER:
            raise ValueError(f"Expected villager entity, got mob_type={villager_entity.mob_type}")

        # Open the entity container
        await self.protocol._inventory_mgr.open_entity(villager_entity)

        # Wait for villager window to be ready
        if self._villager_window:
            await self._wait_for_ready(self._villager_window)

        return self._villager_window

    async def _wait_for_ready(self, villager_window: VillagerWindow, timeout: float = 5.0) -> None:
        """Wait for villager window to be ready with trades"""
        if villager_window.ready:
            return

        future = asyncio.get_event_loop().create_future()

        def on_ready():
            if not future.done():
                future.set_result(True)

        villager_window.once("ready", on_ready)

        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Villager window not ready after {timeout}s")

    async def trade(
        self, villager_window: VillagerWindow, trade_index: int, count: Optional[int] = None
    ) -> None:
        """
        Execute a trade with a villager

        Args:
            villager_window: Open villager trading window
            trade_index: Index of trade in villager_window.trades
            count: Number of times to execute trade (default: max available)

        Raises:
            ValueError: If trade is invalid or unavailable
            RuntimeError: If bot doesn't have required items
        """
        # Validate trade index
        if trade_index < 0 or trade_index >= len(villager_window.trades):
            raise ValueError(f"Invalid trade index: {trade_index}")

        trade = villager_window.trades[trade_index]
        villager_window.selected_trade = trade

        # Check trade availability
        if not trade.is_available:
            raise ValueError(f"Trade {trade_index} is not available")

        # Set default count to maximum remaining uses
        if count is None:
            count = trade.remaining_uses

        if count <= 0:
            raise ValueError(f"Invalid trade count: {count}")

        if count > trade.remaining_uses:
            raise ValueError(
                f"Trade only has {trade.remaining_uses} uses remaining, requested {count}"
            )

        # Validate item requirements
        await self._validate_trade_items(villager_window, trade, count)

        # Execute the trade count times
        for _ in range(count):
            await self._execute_single_trade(villager_window, trade)

            # Update trade state
            trade.nb_trade_uses += 1
            if trade.remaining_uses == 0:
                trade.trade_disabled = True

    async def _validate_trade_items(
        self, villager_window: VillagerWindow, trade: Trade, count: int
    ) -> None:
        """
        Validate that the bot has enough items for the trade

        Raises:
            RuntimeError: If required items are not available
        """
        inv_mgr = self.protocol._inventory_mgr

        # Check first input item
        if trade.input_item1 and not trade.input_item1.is_empty:
            required = trade.real_price * count
            available = self._count_item(trade.input_item1.item_id, trade.input_item1.item_count)
            if available < required:
                raise RuntimeError(
                    f"Not enough {trade.input_item1.name}: need {required}, have {available}"
                )

        # Check second input item
        if trade.input_item2 and not trade.input_item2.is_empty:
            required = trade.input_item2.item_count * count
            available = self._count_item(trade.input_item2.item_id, trade.input_item2.item_count)
            if available < required:
                raise RuntimeError(
                    f"Not enough {trade.input_item2.name}: need {required}, have {available}"
                )

    def _count_item(self, item_id: int, item_count: int = 1) -> int:
        """
        Count items in player inventory

        Args:
            item_id: Item type ID to count
            item_count: Count per stack (for reference)

        Returns:
            Total count of matching items
        """
        inv_mgr = self.protocol._inventory_mgr
        total = 0

        # Check all inventory slots (9-44, excluding crafting and armor)
        for slot in range(9, 45):
            item = inv_mgr.player_inventory.get_slot(slot)
            if item and item.item_id == item_id:
                total += item.item_count

        # Check off-hand slot (45)
        item = inv_mgr.player_inventory.get_slot(45)
        if item and item.item_id == item_id:
            total += item.item_count

        return total

    async def _execute_single_trade(self, villager_window: VillagerWindow, trade: Trade) -> None:
        """
        Execute a single trade operation

        This involves:
        1. Depositing required items into villager slots
        2. Selecting the trade
        3. Waiting for output
        4. Moving output to inventory
        """
        inv_mgr = self.protocol._inventory_mgr

        # Deposit required items into villager slots
        await self._deposit_trade_items(villager_window, trade)

        # Select the trade (send Select Merchant Trade packet)
        await self._select_trade(villager_window, trade)

        # Wait for output item to appear
        await self._wait_for_trade_output(villager_window)

        # Move output item to player inventory
        await inv_mgr.put_away(2)

    async def _deposit_trade_items(self, villager_window: VillagerWindow, trade: Trade) -> None:
        """
        Deposit required items into villager trading slots

        Args:
            villager_window: Open villager window
            trade: Trade to execute
        """
        inv_mgr = self.protocol._inventory_mgr

        # Deposit first input item
        if trade.input_item1 and not trade.input_item1.is_empty:
            amount_needed = trade.real_price
            amount_in_slot = villager_window.slots[0].item_count if villager_window.slots[0] else 0
            amount_to_deposit = max(0, amount_needed - amount_in_slot)

            if amount_to_deposit > 0:
                await inv_mgr.deposit_item(
                    item_id=trade.input_item1.item_id,
                    count=amount_to_deposit,
                    dest_slot=0,
                )

        # Deposit second input item
        if trade.input_item2 and not trade.input_item2.is_empty:
            amount_needed = trade.input_item2.item_count
            amount_in_slot = villager_window.slots[1].item_count if villager_window.slots[1] else 0
            amount_to_deposit = max(0, amount_needed - amount_in_slot)

            if amount_to_deposit > 0:
                await inv_mgr.deposit_item(
                    item_id=trade.input_item2.item_id,
                    count=amount_to_deposit,
                    dest_slot=1,
                )

    async def _select_trade(self, villager_window: VillagerWindow, trade: Trade) -> None:
        """
        Send Select Merchant Trade packet to server

        Args:
            villager_window: Open villager window
            trade: Trade to select
        """
        # Find trade index
        trade_index = villager_window.trades.index(trade)

        # Send Select Merchant Trade packet (0x25)
        buf = self.protocol._create_packet_buffer()
        buf.write_varint(villager_window.window_id)
        buf.write_varint(trade_index)

        await self.protocol._send_serverbound_packet(0x25, buf)

    async def _wait_for_trade_output(
        self, villager_window: VillagerWindow, timeout: float = 5.0
    ) -> None:
        """
        Wait for trade output to appear in slot 2

        Args:
            villager_window: Open villager window
            timeout: Maximum wait time in seconds
        """
        future = asyncio.get_event_loop().create_future()

        def on_slot_update(slot: int, item: Optional["Item"]):
            if slot == 2 and item and not item.is_empty:
                if not future.done():
                    future.set_result(item)

        villager_window.on("updateSlot", on_slot_update)

        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Trade output not received after {timeout}s")
        finally:
            villager_window.remove_handler("updateSlot", on_slot_update)

    def handle_merchant_offers(self, window_id: int, trades: List[Trade]) -> None:
        """
        Handle Merchant Offers packet from server

        This packet (0x24) contains all available trades from a villager.

        Args:
            window_id: Window ID the trades are for
            trades: List of available trades
        """
        if self._villager_window and self._villager_window.window_id == window_id:
            self._villager_window.set_trades(trades)

    def set_villager_window(self, villager_window: Optional[VillagerWindow]) -> None:
        """Set the current villager window"""
        self._villager_window = villager_window
