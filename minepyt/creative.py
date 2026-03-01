"""
Creative mode inventory management for Minecraft 1.21.4

This module provides:
- Set inventory slots in creative mode
- Clear inventory slots
- Flying in creative mode
- Clear entire inventory

Port of mineflayer/lib/plugins/creative.js
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item


@dataclass
class FlyingState:
    """Tracks flying state for creative mode"""

    is_flying: bool = False
    normal_gravity: Optional[float] = None
    flying_speed: float = 0.5  # blocks per tick


class CreativeManager:
    """
    Manages creative mode inventory operations.

    This class handles:
    - Setting inventory slots
    - Clearing inventory
    - Flying controls

    Note: These features only work in creative game mode.
    """

    FLYING_SPEED_PER_UPDATE = 0.5  # blocks per tick
    UPDATE_INTERVAL = 0.05  # seconds (20 ticks per second)

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self._flying_state = FlyingState()
        self._slot_updates: dict[int, bool] = {}

    async def set_slot(self, slot: int, item: Optional["Item"], wait_timeout: float = 0.4) -> None:
        """
        Set inventory slot to specific item (creative mode only).

        Args:
            slot: Slot number (0-44 for player inventory)
            item: Item to set (None to clear slot)
            wait_timeout: Seconds to wait for server confirmation (0 = no wait)

        Raises:
            ValueError: If slot is out of range (0-44)
            RuntimeError: If called twice on same slot before first completes
        """
        if not (0 <= slot <= 44):
            raise ValueError(f"Slot must be between 0 and 44, got {slot}")

        # Check if already updating this slot
        if self._slot_updates.get(slot, False):
            raise RuntimeError(
                f"Setting slot {slot} cancelled due to calling set_slot({slot}, ...) again"
            )

        # Get current item for comparison
        current_item = self.protocol._inventory_mgr.player_inventory.get_slot(slot)

        # Skip if item is already the same
        if self._items_equal(current_item, item):
            return

        self._slot_updates[slot] = True

        try:
            # Send set_creative_slot packet (0x32)
            await self._send_set_slot(slot, item)

            # Wait for confirmation (if timeout > 0)
            if wait_timeout > 0:
                await self._wait_slot_confirmation(slot, item, wait_timeout)
            elif wait_timeout == 0:
                # Update immediately (no wait, no confirmation)
                self.protocol._inventory_mgr.player_inventory.set_slot(slot, item)

        finally:
            self._slot_updates[slot] = False

    def _items_equal(self, item1: Optional["Item"], item2: Optional["Item"]) -> bool:
        """Check if two items are equal (for creative slot comparison)"""
        if item1 is None and item2 is None:
            return True
        if item1 is None or item2 is None:
            return False

        return (
            item1.item_id == item2.item_id
            and item1.item_count == item2.item_count
            and item1.nbt_data == item2.nbt_data
            and item1.components == item2.components
        )

    async def _send_set_slot(self, slot: int, item: Optional["Item"]) -> None:
        """Send set_creative_slot packet (0x32)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        buf.write_varint(slot)  # slot ID (0-44)

        # Write item (or empty slot)
        if item and not item.is_empty:
            self._write_item_to_buffer(buf, item)
        else:
            buf.write_varint(0)  # empty slot

        await self.protocol._write_packet(0x32, bytes(buf))
        print(f"[CREATIVE] Set slot {slot} to {item.display_name if item else 'empty'}")

    def _write_item_to_buffer(self, buf: Buffer, item: "Item") -> None:
        """Write item to buffer in Minecraft 1.21.4 format"""
        # Item ID
        buf.write_varint(item.item_id)
        # Count
        buf.write_byte(item.item_count)

        # NBT data (optional)
        if item.nbt_data:
            from mcproto.nbt import NBTTag

            buf.write_byte(0x0A)  # TAG_Compound start
            buf.write_nbt(item.nbt_data)
        else:
            buf.write_byte(0x00)  # TAG_End

        # Components (1.21.4)
        if item.components:
            buf.write_varint(len(item.components))
            for key, value in item.components.items():
                buf.write_string(key)
                from mcproto.nbt import NBTTag

                buf.write_nbt(value)
        else:
            buf.write_varint(0)  # no components

    async def _wait_slot_confirmation(
        self, slot: int, expected_item: Optional["Item"], timeout: float
    ) -> None:
        """Wait for server to confirm slot update"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            current_item = self.protocol._inventory_mgr.player_inventory.get_slot(slot)

            if self._items_equal(current_item, expected_item):
                return  # Success - slot matches expected

            await asyncio.sleep(0.01)  # Small sleep

        # Timeout - slot didn't update to expected value
        raise RuntimeError(f"Server rejected creative slot {slot} update")

    async def clear_slot(self, slot: int) -> None:
        """
        Clear a specific inventory slot (set to empty).

        Args:
            slot: Slot number (0-44)
        """
        await self.set_slot(slot, None)
        print(f"[CREATIVE] Cleared slot {slot}")

    async def clear_inventory(self) -> None:
        """
        Clear entire player inventory (set all slots to empty).

        This clears slots 0-44 (main inventory + armor + offhand).
        """
        tasks = []

        for slot in range(45):
            item = self.protocol._inventory_mgr.player_inventory.get_slot(slot)
            if item and not item.is_empty:
                tasks.append(self.clear_slot(slot))

        if tasks:
            await asyncio.gather(*tasks)
            print(f"[CREATIVE] Cleared {len(tasks)} inventory slots")

    async def fly_to(self, x: float, y: float, z: float) -> None:
        """
        Fly in a straight line to destination.

        This is a simple straight-line flight. Make sure the path is clear.

        Args:
            x, y, z: Target coordinates
        """
        self.start_flying()

        # Calculate direction vector
        current_pos = self.protocol.position
        dx = x - current_pos[0]
        dy = y - current_pos[1]
        dz = z - current_pos[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance == 0:
            return  # Already at destination

        # Normalize and scale to speed
        nx = (dx / distance) * self.FLYING_SPEED_PER_UPDATE
        ny = (dy / distance) * self.FLYING_SPEED_PER_UPDATE
        nz = (dz / distance) * self.FLYING_SPEED_PER_UPDATE

        # Move in steps
        remaining = distance
        while remaining > self.FLYING_SPEED_PER_UPDATE:
            # Disable gravity and set velocity
            if hasattr(self.protocol, "_movement") and self.protocol._movement:
                self.protocol._movement.gravity = 0
                self.protocol._movement.velocity = (0, 0, 0)

            # Move one step
            current_x, current_y, current_z = self.protocol.position
            new_pos = (
                current_x + nx,
                current_y + ny,
                current_z + nz,
            )

            # Update position directly
            if hasattr(self.protocol, "_movement"):
                self.protocol._movement.position = new_pos

            await asyncio.sleep(self.UPDATE_INTERVAL)
            remaining -= self.FLYING_SPEED_PER_UPDATE

        # Final step - snap to exact position
        if hasattr(self.protocol, "_movement"):
            self.protocol._movement.position = (x, y, z)
            await asyncio.sleep(self.UPDATE_INTERVAL)

        print(f"[CREATIVE] Flew to ({x}, {y}, {z})")

    def start_flying(self) -> None:
        """
        Start flying (disable gravity).

        This sets gravity to 0, allowing free movement in creative mode.
        """
        if not hasattr(self.protocol, "_movement") or not self.protocol._movement:
            print("[CREATIVE] Warning: Movement manager not available")
            return

        # Save normal gravity if not already flying
        if not self._flying_state.is_flying:
            self._flying_state.normal_gravity = self.protocol._movement.gravity
            self.protocol._movement.gravity = 0
            self._flying_state.is_flying = True
            print("[CREATIVE] Started flying (gravity disabled)")

    def stop_flying(self) -> None:
        """
        Stop flying (restore normal gravity).

        This restores gravity to its original value.
        """
        if not hasattr(self.protocol, "_movement") or not self.protocol._movement:
            print("[CREATIVE] Warning: Movement manager not available")
            return

        if self._flying_state.is_flying and self._flying_state.normal_gravity is not None:
            self.protocol._movement.gravity = self._flying_state.normal_gravity
            self._flying_state.is_flying = False
            self._flying_state.normal_gravity = None
            print("[CREATIVE] Stopped flying (gravity restored)")

    @property
    def is_flying(self) -> bool:
        """Check if currently flying"""
        return self._flying_state.is_flying


__all__ = ["CreativeManager", "FlyingState"]
