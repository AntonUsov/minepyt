"""
Advanced inventory systems for Minecraft 1.21.4

This module provides:
- Anvil operations (combine, rename, repair)
- Enchanting table operations
- Brewing stand operations (future)
- Creative inventory (future)

Port of mineflayer/lib/plugins/anvil.js and enchantment_table.js
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item
    from .block_registry import Block
    from .inventory import Window


class AnvilSlot(IntEnum):
    """Anvil slot indices"""

    INPUT_1 = 0  # Left item (to repair/combine)
    INPUT_2 = 1  # Right item (sacrifice)
    OUTPUT = 2  # Result


class EnchantingSlot(IntEnum):
    """Enchanting table slot indices"""

    ITEM = 0  # Item to enchant
    LAPIS = 1  # Lapis lazuli


@dataclass
class EnchantmentOption:
    """Represents an enchantment option at enchanting table"""

    slot: int  # 0, 1, or 2
    level: int = -1  # Required levels
    enchant_id: int = -1  # Enchantment ID (hidden until click)
    enchant_level: int = -1  # Enchantment level (hidden until click)


@dataclass
class AnvilResult:
    """Result of an anvil operation"""

    success: bool
    item: Optional["Item"] = None
    xp_cost: int = 0
    message: str = ""


class AnvilManager:
    """
    Manages anvil operations.

    Anvil slots:
    - 0: Input item (to repair/combine/rename)
    - 1: Sacrifice item (second item for combining)
    - 2: Output (result)
    """

    MAX_NAME_LENGTH = 35

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self._anvil_window: Optional["Window"] = None

    async def open(self, block: "Block") -> "Window":
        """
        Open an anvil.

        Args:
            block: Anvil block

        Returns:
            Anvil window
        """
        # Activate the anvil block
        await self.protocol.activate_block(block)

        # Wait for window open event
        # For now, we'll assume the window is tracked
        await asyncio.sleep(0.2)

        if self.protocol._inventory_mgr.current_window:
            self._anvil_window = self.protocol._inventory_mgr.current_window
            return self._anvil_window

        raise RuntimeError("Failed to open anvil")

    async def combine(
        self, item1: "Item", item2: "Item", name: Optional[str] = None
    ) -> AnvilResult:
        """
        Combine two items in the anvil.

        Args:
            item1: First item (main)
            item2: Second item (sacrifice)
            name: Optional new name

        Returns:
            AnvilResult with the combined item
        """
        if not self._anvil_window:
            raise RuntimeError("Anvil not open")

        if name and len(name) > self.MAX_NAME_LENGTH:
            return AnvilResult(
                success=False, message=f"Name too long (max {self.MAX_NAME_LENGTH} chars)"
            )

        # Calculate XP cost (simplified)
        xp_cost = self._calculate_combine_cost(item1, item2)

        # Check if player has enough XP
        if self.protocol.game.game_mode != "creative":
            # Would need to track XP levels
            pass

        # Put items in anvil
        await self._put_item(AnvilSlot.INPUT_1, item1)
        await self._put_item(AnvilSlot.INPUT_2, item2)

        # Send name if provided
        if name:
            await self._send_name(name)

        # Wait for output to be ready
        await asyncio.sleep(0.3)

        # Take output
        result_item = self._anvil_window.get_slot(AnvilSlot.OUTPUT)

        if result_item and not result_item.is_empty:
            await self._take_output()
            return AnvilResult(
                success=True,
                item=result_item,
                xp_cost=xp_cost,
                message="Items combined successfully",
            )

        return AnvilResult(success=False, message="Could not combine items")

    async def rename(self, item: "Item", name: str) -> AnvilResult:
        """
        Rename an item in the anvil.

        Args:
            item: Item to rename
            name: New name

        Returns:
            AnvilResult with the renamed item
        """
        if not self._anvil_window:
            raise RuntimeError("Anvil not open")

        if len(name) > self.MAX_NAME_LENGTH:
            return AnvilResult(
                success=False, message=f"Name too long (max {self.MAX_NAME_LENGTH} chars)"
            )

        # Put item in anvil
        await self._put_item(AnvilSlot.INPUT_1, item)

        # Send name character by character (like vanilla)
        await self._send_name(name)

        # Wait for output
        await asyncio.sleep(0.3)

        # Take output
        result_item = self._anvil_window.get_slot(AnvilSlot.OUTPUT)

        if result_item and not result_item.is_empty:
            await self._take_output()
            return AnvilResult(
                success=True,
                item=result_item,
                xp_cost=1,  # Renaming costs 1 level
                message="Item renamed successfully",
            )

        return AnvilResult(success=False, message="Could not rename item")

    async def repair(self, item: "Item", material: "Item") -> AnvilResult:
        """
        Repair an item using material.

        Args:
            item: Item to repair
            material: Repair material (same type as item)

        Returns:
            AnvilResult with the repaired item
        """
        return await self.combine(item, material)

    def _calculate_combine_cost(self, item1: "Item", item2: "Item") -> int:
        """Calculate XP cost for combining items (simplified)"""
        # Real calculation is more complex
        cost = 1

        # Add cost for enchantments
        if item1.has_enchantments:
            cost += len(item1.enchantments)
        if item2.has_enchantments:
            cost += len(item2.enchantments)

        # Add cost for renaming
        # Add cost for repair
        # etc.

        return min(cost, 39)  # Max cost is 39 levels

    async def _put_item(self, slot: int, item: "Item") -> None:
        """Put an item in an anvil slot"""
        # Move item from inventory to anvil slot
        if item.slot >= 0:
            # Click the item in inventory to pick it up
            await self.protocol.left_click(item.slot)
            # Click the anvil slot to put it down
            await self.protocol.left_click(slot)

    async def _send_name(self, name: str) -> None:
        """Send item name to server (character by character)"""
        from mcproto.buffer import Buffer

        # Send name packet (0x0C for 1.21.4)
        buf = Buffer()
        buf.write_utf(name)
        await self.protocol._write_packet(0x0C, bytes(buf))

    async def _take_output(self) -> None:
        """Take the output item from anvil"""
        await self.protocol.left_click(AnvilSlot.OUTPUT)
        # Put in inventory
        empty_slot = self.protocol._inventory_mgr.player_inventory.first_empty_slot(
            self.protocol._inventory_mgr.INVENTORY_START, self.protocol._inventory_mgr.INVENTORY_END
        )
        if empty_slot is not None:
            await self.protocol.left_click(empty_slot)

    async def close(self) -> None:
        """Close the anvil"""
        if self._anvil_window:
            await self.protocol._inventory_mgr.close_window(self._anvil_window.window_id)
            self._anvil_window = None


class EnchantingManager:
    """
    Manages enchanting table operations.

    Enchanting slots:
    - 0: Item to enchant
    - 1: Lapis lazuli (consumed)

    Enchantment options:
    - 3 options with different level requirements
    - Actual enchantments are hidden until selected
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self._enchant_window: Optional["Window"] = None
        self.enchantments: List[EnchantmentOption] = []
        self.xpseed: int = -1
        self._ready: bool = False

    async def open(self, block: "Block") -> "Window":
        """
        Open an enchanting table.

        Args:
            block: Enchanting table block

        Returns:
            Enchanting window
        """
        if block.name != "enchanting_table":
            raise ValueError("Block must be an enchanting_table")

        # Activate the enchanting table
        await self.protocol.activate_block(block)

        # Wait for window open
        await asyncio.sleep(0.2)

        if self.protocol._inventory_mgr.current_window:
            self._enchant_window = self.protocol._inventory_mgr.current_window
            self._reset_options()
            return self._enchant_window

        raise RuntimeError("Failed to open enchanting table")

    def _reset_options(self) -> None:
        """Reset enchantment options"""
        self.enchantments = [
            EnchantmentOption(slot=0),
            EnchantmentOption(slot=1),
            EnchantmentOption(slot=2),
        ]
        self.xpseed = -1
        self._ready = False

    def update_property(self, property_id: int, value: int) -> None:
        """
        Update enchantment property from server packet.

        Args:
            property_id: Property type (0-9)
            value: Property value
        """
        if property_id < 3:
            # Enchantment level requirement
            self.enchantments[property_id].level = value
        elif property_id == 3:
            # XP seed
            self.xpseed = value
        elif property_id < 7:
            # Expected enchantment ID (hidden)
            slot = property_id - 4
            self.enchantments[slot].enchant_id = value
        elif property_id < 10:
            # Expected enchantment level (hidden)
            slot = property_id - 7
            self.enchantments[slot].enchant_level = value

        # Check if ready
        if all(e.level >= 0 for e in self.enchantments):
            if not self._ready:
                self._ready = True
                self.protocol.emit("enchantingReady")
        else:
            self._ready = False

    @property
    def target_item(self) -> Optional["Item"]:
        """Get the item currently in the enchanting table"""
        if self._enchant_window:
            return self._enchant_window.get_slot(EnchantingSlot.ITEM)
        return None

    async def put_item(self, item: "Item") -> None:
        """Put an item in the enchanting table"""
        if not self._enchant_window:
            raise RuntimeError("Enchanting table not open")

        if item.slot >= 0:
            # Pick up item
            await self.protocol.left_click(item.slot)
            # Put in enchanting slot
            await self.protocol.left_click(EnchantingSlot.ITEM)

    async def put_lapis(self, lapis: "Item") -> None:
        """Put lapis lazuli in the enchanting table"""
        if not self._enchant_window:
            raise RuntimeError("Enchanting table not open")

        if lapis.slot >= 0:
            # Pick up lapis
            await self.protocol.left_click(lapis.slot)
            # Put in lapis slot
            await self.protocol.left_click(EnchantingSlot.LAPIS)

    async def enchant(self, choice: int) -> Optional["Item"]:
        """
        Perform an enchantment.

        Args:
            choice: Enchantment slot (0, 1, or 2)

        Returns:
            Enchanted item
        """
        if not self._enchant_window:
            raise RuntimeError("Enchanting table not open")

        if choice < 0 or choice > 2:
            raise ValueError("Choice must be 0, 1, or 2")

        # Wait for ready if not ready
        if not self._ready:
            # Wait for ready event
            await asyncio.sleep(0.5)

        if self.enchantments[choice].level < 0:
            raise RuntimeError(f"Enchantment option {choice} not available")

        # Check XP level
        if self.protocol.game.game_mode != "creative":
            # Would need to track XP levels
            pass

        # Send enchant packet (0x0D for 1.21.4)
        from mcproto.buffer import Buffer

        buf = Buffer()
        buf.write_varint(self._enchant_window.window_id)
        buf.write_varint(choice)
        await self.protocol._write_packet(0x0D, bytes(buf))

        # Wait for result
        await asyncio.sleep(0.3)

        # Get enchanted item
        return self.target_item

    async def take_item(self) -> Optional["Item"]:
        """Take the item from the enchanting table"""
        if not self._enchant_window:
            raise RuntimeError("Enchanting table not open")

        item = self.target_item
        if item:
            # Pick up from enchanting slot
            await self.protocol.left_click(EnchantingSlot.ITEM)
            # Put in inventory
            empty_slot = self.protocol._inventory_mgr.player_inventory.first_empty_slot(
                self.protocol._inventory_mgr.INVENTORY_START,
                self.protocol._inventory_mgr.INVENTORY_END,
            )
            if empty_slot is not None:
                await self.protocol.left_click(empty_slot)

        return item

    async def close(self) -> None:
        """Close the enchanting table"""
        if self._enchant_window:
            await self.protocol._inventory_mgr.close_window(self._enchant_window.window_id)
            self._enchant_window = None


class AdvancedInventory:
    """
    High-level interface for advanced inventory operations.

    Provides easy access to:
    - Anvil (combine, rename, repair)
    - Enchanting table
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.anvil = AnvilManager(protocol)
        self.enchanting = EnchantingManager(protocol)

    async def open_anvil(self, block: "Block") -> AnvilManager:
        """Open an anvil and return manager"""
        await self.anvil.open(block)
        return self.anvil

    async def open_enchanting_table(self, block: "Block") -> EnchantingManager:
        """Open an enchanting table and return manager"""
        await self.enchanting.open(block)
        return self.enchanting

    async def close_all(self) -> None:
        """Close all open windows"""
        await self.anvil.close()
        await self.enchanting.close()


__all__ = [
    "AdvancedInventory",
    "AnvilManager",
    "EnchantingManager",
    "AnvilResult",
    "EnchantmentOption",
    "AnvilSlot",
    "EnchantingSlot",
]
