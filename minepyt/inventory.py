"""
Inventory system for Minecraft 1.21.4

This module provides:
- Equipment slot management
- Container/window handling
- Item transfer methods
- Toss/drop functionality
- Click operations

Port of mineflayer/lib/plugins/inventory.js
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item


class EquipmentSlot(IntEnum):
    """Equipment slot indices for player inventory"""

    HEAD = 5  # Helmet
    CHEST = 6  # Chestplate
    LEGS = 7  # Leggings
    FEET = 8  # Boots
    OFF_HAND = 45  # Shield/totem

    # Hotbar slots (36-44)
    HOTBAR_START = 36
    HOTBAR_END = 44

    # Inventory slots (9-35)
    INVENTORY_START = 9
    INVENTORY_END = 35

    # Crafting area
    CRAFTING_OUTPUT = 0
    CRAFTING_INPUT_START = 1
    CRAFTING_INPUT_END = 4


class WindowType(IntEnum):
    """Window/container types"""

    PLAYER = 0
    CHEST = 1
    CRAFTING = 2
    FURNACE = 3
    DISPENSER = 4
    ENCHANTMENT = 5
    BREWING = 6
    VILLAGER = 7
    BEACON = 8
    ANVIL = 9
    HOPPER = 10
    SHULKER = 11


@dataclass
class Window:
    """Represents an open container/window"""

    window_id: int
    window_type: WindowType
    title: str
    slots: Dict[int, "Item"] = field(default_factory=dict)
    inventory_start: int = 0
    inventory_end: int = 0

    def get_slot(self, slot: int) -> Optional["Item"]:
        """Get item at slot"""
        return self.slots.get(slot)

    def set_slot(self, slot: int, item: Optional["Item"]) -> None:
        """Set item at slot"""
        if item is None and slot in self.slots:
            del self.slots[slot]
        elif item:
            self.slots[slot] = item

    def find_item(self, item_id: int, start: int = 0, end: int = 80) -> Optional["Item"]:
        """Find first item with matching ID in range"""
        for slot in range(start, end + 1):
            item = self.slots.get(slot)
            if item and item.item_id == item_id:
                return item
        return None

    def find_all_items(self, item_id: int, start: int = 0, end: int = 80) -> List["Item"]:
        """Find all items with matching ID in range"""
        items = []
        for slot in range(start, end + 1):
            item = self.slots.get(slot)
            if item and item.item_id == item_id:
                items.append(item)
        return items

    def first_empty_slot(self, start: int = 0, end: int = 80) -> Optional[int]:
        """Find first empty slot in range"""
        for slot in range(start, end + 1):
            if slot not in self.slots or self.slots[slot].is_empty:
                return slot
        return None

    def empty_slot_count(self, start: int = 0, end: int = 80) -> int:
        """Count empty slots in range"""
        count = 0
        for slot in range(start, end + 1):
            if slot not in self.slots or self.slots[slot].is_empty:
                count += 1
        return count


class InventoryManager:
    """
    Manages inventory and container functionality.

    This class handles:
    - Equipment management
    - Container/window operations
    - Item transfers
    - Click operations
    - Toss/drop functionality
    """

    # Slot ranges
    QUICK_BAR_START = 36
    QUICK_BAR_END = 44

    INVENTORY_START = 9
    INVENTORY_END = 44

    # Timeouts
    WINDOW_TIMEOUT = 5.0  # seconds
    CONSUME_TIMEOUT = 2.5  # seconds

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Player inventory (always window ID 0)
        self.player_inventory = Window(
            window_id=0,
            window_type=WindowType.PLAYER,
            title="Inventory",
            inventory_start=9,
            inventory_end=44,
        )

        # Currently open window
        self.current_window: Optional[Window] = None

        # Selected hotbar slot (0-8)
        self.quick_bar_slot: int = 0

        # Item held by cursor
        self.cursor_item: Optional["Item"] = None

        # Sequence number for clicks
        self._sequence: int = 0

        # State ID for 1.17+
        self._state_id: int = -1

    @property
    def held_item(self) -> Optional["Item"]:
        """Get currently held item (in selected hotbar slot)"""
        slot = self.QUICK_BAR_START + self.quick_bar_slot
        return self.player_inventory.get_slot(slot)

    @property
    def equipment(self) -> Dict[str, Optional["Item"]]:
        """Get all equipped items"""
        return {
            "head": self.player_inventory.get_slot(EquipmentSlot.HEAD),
            "chest": self.player_inventory.get_slot(EquipmentSlot.CHEST),
            "legs": self.player_inventory.get_slot(EquipmentSlot.LEGS),
            "feet": self.player_inventory.get_slot(EquipmentSlot.FEET),
            "off_hand": self.player_inventory.get_slot(EquipmentSlot.OFF_HAND),
            "main_hand": self.held_item,
        }

    # === Hotbar Management ===

    async def set_quick_bar_slot(self, slot: int) -> None:
        """
        Set the selected hotbar slot.

        Args:
            slot: Slot index (0-8)
        """
        if slot < 0 or slot > 8:
            raise ValueError("Hotbar slot must be 0-8")

        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        buf.write_varint(slot)
        await self.protocol._write_packet(0x2C, bytes(buf))

        old_slot = self.quick_bar_slot
        self.quick_bar_slot = slot

        old_item = self.player_inventory.get_slot(self.QUICK_BAR_START + old_slot)
        new_item = self.held_item

        if old_item != new_item:
            self.protocol.emit("heldItemChanged", new_item)

    # === Click Operations ===

    async def click_window(
        self, slot: int, button: int, mode: int, item: Optional["Item"] = None
    ) -> None:
        """
        Click on a slot in the current window.

        Args:
            slot: Slot to click (-999 for outside window)
            button: Mouse button (0=left, 1=right, 2=middle)
            mode: Click mode (0=pickup, 1=quick_move, 2=swap, etc.)
            item: Item being clicked (for verification)
        """
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        window_id = self.current_window.window_id if self.current_window else 0

        self._sequence += 1

        buf = Buffer()
        buf.write_varint(window_id)
        buf.write_varint(self._sequence)
        buf.write_varint(slot)
        buf.write_value(StructFormat.BYTE, button)
        buf.write_varint(mode)

        # Write clicked item
        if item and not item.is_empty:
            buf.write_varint(item.item_id)
            buf.write_value(StructFormat.BYTE, item.count)
            # Write components (simplified)
            buf.write_varint(0)  # added components
            buf.write_varint(0)  # removed components
        else:
            buf.write_varint(0)  # empty slot

        await self.protocol._write_packet(0x0F, bytes(buf))

    async def left_click(self, slot: int, window_id: int = 0) -> None:
        """Left click on a slot (pickup/put down)"""
        await self.click_window(slot, 0, 0, self.cursor_item)

    async def right_click(self, slot: int, window_id: int = 0) -> None:
        """Right click on a slot (pickup half/place one)"""
        await self.click_window(slot, 1, 0, self.cursor_item)

    async def shift_click(self, slot: int, window_id: int = 0) -> None:
        """Shift-click on a slot (quick move)"""
        await self.click_window(slot, 0, 1, None)

    async def drop_slot(self, slot: int, drop_stack: bool = False, window_id: int = 0) -> None:
        """Drop item from slot"""
        button = 1 if drop_stack else 0
        await self.click_window(slot, button, 4, None)

    async def swap_hotbar(self, slot: int, hotbar_slot: int, window_id: int = 0) -> None:
        """Swap inventory slot with hotbar slot"""
        await self.click_window(slot, hotbar_slot, 2, None)

    # === Container Management ===

    async def close_window(self, window_id: Optional[int] = None) -> None:
        """Close the current window"""
        from mcproto.buffer import Buffer

        if window_id is None:
            window_id = self.current_window.window_id if self.current_window else 0

        buf = Buffer()
        buf.write_varint(window_id)
        await self.protocol._write_packet(0x0E, bytes(buf))

        if self.current_window and self.current_window.window_id == window_id:
            self.protocol.emit("windowClose", self.current_window)
            self.current_window = None

    # === Item Transfer ===

    async def transfer(
        self,
        item_type: int,
        count: int,
        source_start: int,
        source_end: int,
        dest_start: int,
        dest_end: int,
        window: Optional[Window] = None,
    ) -> int:
        """
        Transfer items between slot ranges.

        Args:
            item_type: Item ID to transfer
            count: Number of items to transfer
            source_start: Source slot range start
            source_end: Source slot range end
            dest_start: Destination slot range start
            dest_end: Destination slot range end
            window: Window to use (None = player inventory)

        Returns:
            Number of items actually transferred
        """
        window = window or self.player_inventory
        transferred = 0

        while transferred < count:
            # Find source item
            source_item = window.find_item(item_type, source_start, source_end)
            if not source_item:
                break

            # Find destination slot
            dest_slot = window.first_empty_slot(dest_start, dest_end)
            if dest_slot is None:
                break

            # Calculate how many to move
            to_move = min(count - transferred, source_item.count)

            # Click source to pick up
            await self.left_click(source_item.slot)

            # Click destination to put down
            for _ in range(to_move):
                await self.right_click(dest_slot)

            # Click source again to put back remainder
            await self.left_click(source_item.slot)

            transferred += to_move

        return transferred

    async def withdraw(self, item_type: int, count: int, metadata: Optional[int] = None) -> int:
        """
        Withdraw items from current window to player inventory.

        Args:
            item_type: Item ID to withdraw
            count: Number to withdraw
            metadata: Item metadata (optional)

        Returns:
            Number of items withdrawn
        """
        if not self.current_window:
            raise RuntimeError("No window open")

        return await self.transfer(
            item_type=item_type,
            count=count,
            source_start=0,
            source_end=self.current_window.inventory_start - 1,
            dest_start=self.INVENTORY_START,
            dest_end=self.INVENTORY_END,
            window=self.current_window,
        )

    async def deposit(self, item_type: int, count: int, metadata: Optional[int] = None) -> int:
        """
        Deposit items from player inventory to current window.

        Args:
            item_type: Item ID to deposit
            count: Number to deposit
            metadata: Item metadata (optional)

        Returns:
            Number of items deposited
        """
        if not self.current_window:
            raise RuntimeError("No window open")

        return await self.transfer(
            item_type=item_type,
            count=count,
            source_start=self.current_window.inventory_start,
            source_end=self.current_window.inventory_end,
            dest_start=0,
            dest_end=self.current_window.inventory_start - 1,
            window=self.current_window,
        )

    async def deposit_item(self, item_id: int, count: int, dest_slot: int = 0) -> int:
        """
        Deposit items from player inventory to a specific slot in the current window.

        This is used for villager trading where specific slots (0, 1) need to be filled.

        Args:
            item_id: Item ID to deposit
            count: Number of items to deposit
            dest_slot: Destination slot (for villager: 0 or 1)

        Returns:
            Number of items actually deposited
        """
        if not self.current_window:
            raise RuntimeError("No window open")

        deposited = 0

        while deposited < count:
            # Find source item in player inventory
            source_item = self.player_inventory.find_item(
                item_id, self.INVENTORY_START, self.INVENTORY_END
            )
            if not source_item:
                # Also check off-hand slot
                source_item = self.player_inventory.find_item(item_id, 45, 45)
                if not source_item:
                    break

            # Calculate how many to move
            remaining = count - deposited
            to_move = min(remaining, source_item.item_count)

            # Click source to pick up items
            await self.left_click(source_item.slot)

            # Check if cursor has item
            if not self.cursor_item:
                break

            # Calculate how many to put down
            # Check if destination slot has same item
            dest_item = self.current_window.get_slot(dest_slot)
            if dest_item and dest_item.item_id == item_id:
                # Merge with existing item
                space = dest_item.item_stack_size - dest_item.item_count
                to_put = min(to_move, space)
            else:
                # Place in empty slot or replace
                to_put = to_move

            # Click destination to put down items
            for _ in range(to_put):
                await self.right_click(dest_slot)

            # Put back any remaining items
            if self.cursor_item and self.cursor_item.item_count > 0:
                await self.left_click(source_item.slot)

            deposited += to_move

        return deposited
    # === Toss/Drop ===

    async def toss(self, item_type: int, count: int = 1) -> bool:
        """
        Toss (drop) items from inventory.

        Args:
            item_type: Item ID to toss
            count: Number to toss

        Returns:
            True if items were tossed
        """
        item = self.player_inventory.find_item(item_type, self.INVENTORY_START, self.INVENTORY_END)

        if not item:
            return False

        # Pick up the item
        await self.left_click(item.slot)

        # Click outside inventory to drop
        await self.click_window(-999, 0, 0, self.cursor_item)

        self.cursor_item = None
        return True

    async def toss_stack(self, slot: int) -> None:
        """Toss entire stack from slot"""
        await self.drop_slot(slot, drop_stack=True)

    async def toss_all(self, item_type: int) -> int:
        """
        Toss all items of a type.

        Args:
            item_type: Item ID to toss

        Returns:
            Number of stacks tossed
        """
        tossed = 0
        while await self.toss(item_type, 64):
            tossed += 1
        return tossed

    # === Equipment ===

    async def equip(self, slot: EquipmentSlot, item: "Item") -> bool:
        """
        Equip an item to a slot.

        Args:
            slot: Equipment slot (HEAD, CHEST, LEGS, FEET, OFF_HAND)
            item: Item to equip

        Returns:
            True if equipped successfully
        """
        if item.slot == -1:
            return False

        # Swap item with equipment slot
        await self.swap_hotbar(item.slot, 0)  # Move to hotbar 0
        await self.set_quick_bar_slot(0)

        # Open inventory to access equipment slots
        # (Equipment slots are only accessible when inventory is open)

        return True

    async def put_away(self, slot: int) -> None:
        """
        Move items from current window slot to player inventory.

        This is used for villager trading to take output items.

        Args:
            slot: Source slot in current window
        """
        if not self.current_window:
            raise RuntimeError("No window open")

        # Get the item from the slot
        item = self.current_window.get_slot(slot)
        if not item or item.is_empty:
            return

        # Click the slot to pick up item
        await self.left_click(slot)

        # Find an empty slot in player inventory
        empty_slot = self.player_inventory.first_empty_slot(
            self.INVENTORY_START, self.INVENTORY_END
        )
        if empty_slot is None:
            # Check if we can merge with existing item
            existing = self.player_inventory.find_item(
                item.item_id, self.INVENTORY_START, self.INVENTORY_END
            )
            if existing:
                empty_slot = existing.slot
            else:
                # No space, put back
                await self.left_click(slot)
                return

        # Click the empty slot to put down item
        for _ in range(item.item_count):
            await self.right_click(empty_slot)

    # === Utility ===

    def count_item(self, item_type: int) -> int:
        """Count total items of a type in inventory"""
        total = 0
        for slot, item in self.player_inventory.slots.items():
            if item.item_id == item_type:
                total += item.count
        return total

    def items_by_type(self, item_type: int) -> List["Item"]:
        """Get all items of a type"""
        return self.player_inventory.find_all_items(
            item_type, self.INVENTORY_START, self.INVENTORY_END
        )

    def free_slots(self) -> int:
        """Get count of free inventory slots"""
        return self.player_inventory.empty_slot_count(self.INVENTORY_START, self.INVENTORY_END)


__all__ = [
    "InventoryManager",
    "Window",
    "WindowType",
    "EquipmentSlot",
]
