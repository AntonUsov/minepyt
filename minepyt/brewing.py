"""
Brewing stand operations for Minecraft 1.21.4

This module provides:
- Open brewing stand
- Manage brewing process
- Track fuel and progress
- Input/output handling

Port of mineflayer/lib/plugins/furnace.js (adapted for brewing)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item


@dataclass
class BrewingState:
    """Tracks brewing state"""

    fuel: int = 0  # Current fuel (0-20)
    total_fuel: int = 0  # Max fuel
    fuel_ticks: float = 0  # Fuel remaining in seconds

    progress: int = 0  # Current progress (0-400)
    total_progress: int = 0  # Max progress
    progress_ticks: float = 0  # Progress remaining in seconds


class BrewingWindow:
    """
    Represents an open brewing stand.

    Slot layout:
    - Slot 0: Input (ingredient slot - nether wart, redstone, glowstone, etc.)
    - Slot 1: Fuel (blaze powder)
    - Slot 2, 3, 4: Output potions

    Properties are tracked via 'craft_progress_bar' packets.
    """

    def __init__(
        self,
        window_id: int,
        window_type: str,
        title: str,
        protocol: "MinecraftProtocol",
    ):
        self.window_id = window_id
        self.window_type = window_type
        self.title = title
        self.protocol = protocol

        # Slot tracking
        self.slots: dict[int, Optional["Item"]] = {}

        # Inventory slot ranges (player inventory slots)
        self.inventory_start = 0
        self.inventory_end = 44

        # Brewing state
        self.state = BrewingState()

        # Property handlers map (property -> handler function)
        self._property_handlers = {
            0: self._on_current_fuel,
            1: self._on_total_fuel,
            2: self._on_current_progress,
            3: self._on_total_progress,
        }

        # Register for window property updates
        protocol.on("craft_progress_bar", self._on_window_property)

        # Cleanup on close
        self._closed = False

    async def close(self) -> None:
        """Close the brewing window"""
        if not self._closed:
            from .inventory import InventoryManager

            # Send close window packet
            buf = InventoryManager._write_close_packet(self.window_id)
            await self.protocol._write_packet(0x0E, bytes(buf))

            # Unregister listeners
            self.protocol.remove_listener("craft_progress_bar", self._on_window_property)

            self._closed = True
            print(f"[BREWING] Closed window {self.window_id}")

    def _on_window_property(self, window_id: int, property_id: int, value: int) -> None:
        """Handle window property update from server"""
        if window_id != self.window_id:
            return

        handler = self._property_handlers.get(property_id)
        if handler:
            handler(value)
            self.protocol.emit("brewing_update", self)

    def _on_current_fuel(self, value: int) -> None:
        """Update current fuel level (property 0)"""
        self.state.fuel = value
        if self.state.total_fuel > 0:
            self.state.fuel = int((value / self.state.total_fuel) * 20)
            self.state.fuel_ticks = (value / self.state.total_fuel) * self.state.fuel_ticks
        else:
            self.state.fuel = 0
            self.state.fuel_ticks = 0

    def _on_total_fuel(self, value: int) -> None:
        """Update total fuel (property 1)"""
        self.state.total_fuel = value
        self.state.fuel_ticks = value * 0.05  # ticks to seconds

    def _on_current_progress(self, value: int) -> None:
        """Update current progress (property 2)"""
        self.state.progress = value
        if self.state.total_progress > 0:
            self.state.progress = int((value / self.state.total_progress) * 400)
            self.state.progress_ticks = self.state.progress_ticks * (
                1 - value / self.state.total_progress
            )
        else:
            self.state.progress = 0
            self.state.progress_ticks = 0

    def _on_total_progress(self, value: int) -> None:
        """Update total progress (property 3)"""
        self.state.total_progress = value
        self.state.progress_ticks = value * 0.05  # ticks to seconds

    # Slot accessors

    @property
    def input_item(self) -> Optional["Item"]:
        """Get input item (slot 0)"""
        return self.slots.get(0)

    @property
    def fuel_item(self) -> Optional["Item"]:
        """Get fuel item (slot 1 - blaze powder)"""
        return self.slots.get(1)

    @property
    def output_potions(self) -> list[Optional["Item"]]:
        """Get output potions (slots 2, 3, 4)"""
        return [self.slots.get(i) for i in range(2, 5)]

    # Item operations

    async def take_input(self) -> Optional["Item"]:
        """Take input item from slot 0"""
        return await self._take_slot(0)

    async def take_fuel(self) -> Optional["Item"]:
        """Take fuel item from slot 1"""
        return await self._take_slot(1)

    async def take_output(self, index: int = 0) -> Optional["Item"]:
        """
        Take output potion from brewing stand.

        Args:
            index: Which output slot (0, 1, or 2 for slots 2, 3, 4)

        Returns:
            The potion item or None if slot is empty
        """
        output_slot = 2 + index
        if output_slot > 4:
            raise ValueError(f"Invalid output index {index}, must be 0-2")
        return await self._take_slot(output_slot)

    async def _take_slot(self, slot: int) -> Optional["Item"]:
        """Take item from a brewing stand slot"""
        item = self.slots.get(slot)
        if item and not item.is_empty:
            # Click to pick up
            await self.protocol._inventory_mgr.click_window(
                slot=slot,
                button=0,
                mode=0,
                item=item,
            )

            # Put away in player inventory
            await self.protocol._inventory_mgr.put_away(item.slot)
            return item
        return None

    async def put_input(self, item: "Item") -> None:
        """Put item into input slot (slot 0)"""
        await self._put_slot(0, item)

    async def put_fuel(self, item: "Item") -> None:
        """Put fuel item (blaze powder) into slot 1"""
        await self._put_slot(1, item)

    async def _put_slot(self, dest_slot: int, item: "Item") -> None:
        """
        Put item into a brewing stand slot.

        Args:
            dest_slot: Destination slot in brewing stand (0-4)
            item: Item to put
        """
        # Find item in player inventory
        inv_mgr = self.protocol._inventory_mgr
        source_slot = inv_mgr.player_inventory.find_item(item.item_id)

        if not source_slot:
            raise RuntimeError(f"Item {item.item_id} not found in inventory")

        # Transfer from inventory to brewing stand
        await inv_mgr.transfer(
            source_start=source_slot.slot,
            source_end=source_slot.slot + 1,
            dest_start=dest_slot,
            dest_end=dest_slot + 1,
            window=self,
        )
        print(f"[BREWING] Put item into slot {dest_slot}")

    # State queries

    @property
    def is_brewing(self) -> bool:
        """Check if currently brewing"""
        return self.state.progress > 0 and self.state.progress < 400

    @property
    def has_fuel(self) -> bool:
        """Check if has fuel"""
        return self.state.fuel > 0

    @property
    def can_brew(self) -> bool:
        """Check if can start brewing (has input and fuel)"""
        has_input = self.input_item and not self.input_item.is_empty
        has_fuel = self.fuel_item and not self.fuel_item.is_empty
        return has_input and has_fuel


class BrewingManager:
    """
    Manages brewing stand operations.

    This class handles:
    - Opening brewing stands
    - Managing brewing process
    - Tracking fuel and progress
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

    async def open_brewing_stand(self, block) -> BrewingWindow:
        """
        Open a brewing stand.

        Args:
            block: Brewing stand block to open

        Returns:
            BrewingWindow object

        Raises:
            RuntimeError: If window is not a brewing stand
        """
        # Open the block (uses block interaction)
        from .block_interaction import BlockInteractionManager

        await self.protocol._block_interaction.open_container(block)

        # Wait for window to open
        await asyncio.sleep(0.1)

        # Get current window
        current_window = self.protocol._inventory_mgr.current_window

        if current_window is None:
            raise RuntimeError("Failed to open brewing stand")

        # Verify it's a brewing stand
        from .inventory import WindowType

        if current_window.window_type != WindowType.BREWING:
            raise RuntimeError(f"Expected brewing stand, got {current_window.window_type}")

        # Create brewing window wrapper
        brewing_window = BrewingWindow(
            window_id=current_window.window_id,
            window_type=current_window.window_type,
            title=current_window.title,
            protocol=self.protocol,
        )

        print(f"[BREWING] Opened brewing stand (window {current_window.window_id})")
        return brewing_window


__all__ = ["BrewingWindow", "BrewingManager", "BrewingState"]
