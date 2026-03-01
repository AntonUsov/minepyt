"""
Block interaction system for Minecraft 1.21.4

This module provides:
- Place blocks
- Open containers
- Use items on blocks
- Activate blocks (buttons, levers, etc.)

Port of mineflayer/lib/plugins/block_actions.js
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .block_registry import Block
    from .protocol.models import Item


class BlockFace(IntEnum):
    """Block face directions for placement/interaction"""

    BOTTOM = 0  # -Y
    TOP = 1  # +Y
    NORTH = 2  # -Z
    SOUTH = 3  # +Z
    WEST = 4  # -X
    EAST = 5  # +X


@dataclass
class BlockInteraction:
    """Represents a block interaction result"""

    success: bool
    block: Optional["Block"] = None
    position: Optional[Tuple[int, int, int]] = None
    message: str = ""


class BlockInteractionManager:
    """
    Manages block interactions.

    This class handles:
    - Block placement
    - Container opening
    - Block activation (buttons, levers)
    - Item use on blocks
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Track last placed block position
        self._last_placed: Optional[Tuple[int, int, int]] = None

    async def place_block(
        self, reference_block: "Block", face: BlockFace = BlockFace.TOP, sneak: bool = False
    ) -> BlockInteraction:
        """
        Place a block against another block.

        Args:
            reference_block: Block to place against
            face: Face to place on
            sneak: Whether to sneak (prevents opening containers)

        Returns:
            BlockInteraction with result
        """
        if not self.protocol.held_item:
            return BlockInteraction(success=False, message="No item in hand to place")

        # Look at the reference block
        pos = reference_block.position
        await self.protocol.look_at(pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5)

        # Send block placement packet
        await self._send_block_placement(pos, face, sneak)

        # Calculate placed block position
        dx, dy, dz = self._face_to_offset(face)
        placed_pos = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
        self._last_placed = placed_pos

        return BlockInteraction(
            success=True, position=placed_pos, message=f"Placed block at {placed_pos}"
        )

    async def place_block_at(self, x: int, y: int, z: int, sneak: bool = False) -> BlockInteraction:
        """
        Place a block at a specific position.

        Finds a neighboring block to place against.
        """
        # Try each face to find a valid reference block
        for face in [
            BlockFace.BOTTOM,
            BlockFace.NORTH,
            BlockFace.SOUTH,
            BlockFace.WEST,
            BlockFace.EAST,
            BlockFace.TOP,
        ]:
            dx, dy, dz = self._face_to_offset(face)
            ref_pos = (x - dx, y - dy, z - dz)

            ref_block = self.protocol.block_at(*ref_pos)
            if ref_block and not ref_block.is_air:
                return await self.place_block(ref_block, face, sneak)

        return BlockInteraction(success=False, message="No valid reference block found")

    async def activate_block(
        self,
        block: "Block",
        direction: BlockFace = BlockFace.TOP,
        cursor_pos: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    ) -> bool:
        """
        Activate a block (button, lever, door, etc.).

        Args:
            block: Block to activate
            direction: Face to click on
            cursor_pos: Cursor position on block (0-1)

        Returns:
            True if activation was sent
        """
        pos = block.position

        # Look at block
        await self.protocol.look_at(
            pos[0] + cursor_pos[0], pos[1] + cursor_pos[1], pos[2] + cursor_pos[2]
        )

        # Send block placement packet (also used for activation)
        await self._send_block_placement(pos, direction, sneak=False)

        return True

    async def open_container(self, block: "Block") -> bool:
        """
        Open a container block (chest, furnace, etc.).

        Args:
            block: Container block to open

        Returns:
            True if opened successfully
        """
        # Sneak prevents placing blocks if hand has block
        return await self.activate_block(block, sneak=False)

    async def use_item_on_block(
        self,
        block: "Block",
        direction: BlockFace = BlockFace.TOP,
        cursor_pos: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    ) -> bool:
        """
        Use held item on a block.

        Args:
            block: Block to use item on
            direction: Face to use on
            cursor_pos: Cursor position on block

        Returns:
            True if action was sent
        """
        pos = block.position

        # Look at block
        await self.protocol.look_at(
            pos[0] + cursor_pos[0], pos[1] + cursor_pos[1], pos[2] + cursor_pos[2]
        )

        # Send use item packet
        await self._send_block_placement(pos, direction, sneak=False)

        return True

    async def _send_block_placement(
        self, pos: Tuple[int, int, int], face: BlockFace, sneak: bool = False
    ) -> None:
        """Send Player Block Placement packet (0x36 for 1.21.4)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        # Pack position into long
        pos_long = ((pos[0] & 0x3FFFFFF) << 38) | ((pos[1] & 0xFFF) << 26) | (pos[2] & 0x3FFFFFF)

        buf = Buffer()
        buf.write_varint(0)  # hand: main hand
        buf.write_value(StructFormat.LONG, pos_long)
        buf.write_varint(face)
        buf.write_value(StructFormat.FLOAT, 0.5)  # cursor X
        buf.write_value(StructFormat.FLOAT, 0.5)  # cursor Y
        buf.write_value(StructFormat.FLOAT, 0.5)  # cursor Z
        buf.write_value(StructFormat.BOOL, sneak)  # inside block
        buf.write_varint(0)  # sequence

        await self.protocol._write_packet(0x36, bytes(buf))

    @staticmethod
    def _face_to_offset(face: BlockFace) -> Tuple[int, int, int]:
        """Convert face to block offset"""
        offsets = {
            BlockFace.BOTTOM: (0, -1, 0),
            BlockFace.TOP: (0, 1, 0),
            BlockFace.NORTH: (0, 0, -1),
            BlockFace.SOUTH: (0, 0, 1),
            BlockFace.WEST: (-1, 0, 0),
            BlockFace.EAST: (1, 0, 0),
        }
        return offsets[face]

    # === High-level block operations ===

    async def dig_and_place(
        self, dig_pos: Tuple[int, int, int], place_pos: Tuple[int, int, int]
    ) -> bool:
        """
        Dig a block and place another in a different location.

        Args:
            dig_pos: Position to dig
            place_pos: Position to place at

        Returns:
            True if successful
        """
        # Dig the block
        success = await self.protocol.dig(*dig_pos)
        if not success:
            return False

        # Wait for inventory update
        await asyncio.sleep(0.2)

        # Place at new location
        result = await self.place_block_at(*place_pos)
        return result.success

    async def build_column(self, x: int, z: int, start_y: int, height: int) -> int:
        """
        Build a column of blocks.

        Args:
            x, z: Column position
            start_y: Starting Y level
            height: Number of blocks to place

        Returns:
            Number of blocks placed
        """
        placed = 0

        for y in range(start_y, start_y + height):
            result = await self.place_block_at(x, y, z)
            if result.success:
                placed += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            else:
                break

        return placed

    async def fill_area(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> int:
        """
        Fill an area with blocks.

        Args:
            x1, y1, z1: Start corner
            x2, y2, z2: End corner

        Returns:
            Number of blocks placed
        """
        placed = 0

        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    result = await self.place_block_at(x, y, z)
                    if result.success:
                        placed += 1
                        await asyncio.sleep(0.05)

        return placed


__all__ = [
    "BlockInteractionManager",
    "BlockInteraction",
    "BlockFace",
]
