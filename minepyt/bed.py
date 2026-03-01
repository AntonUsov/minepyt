"""
Bed tracking for Minecraft 1.21.4

This module provides:
- Track sleeping state
- Find nearest bed
- Wake up from bed

Beds are tracked via entity metadata (player is sleeping).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .entities import Entity


class BedColor(IntEnum):
    """Bed colors"""

    WHITE = 0
    ORANGE = 1
    MAGENTA = 2
    LIGHT_BLUE = 3
    YELLOW = 4
    LIME = 5
    PINK = 6
    GRAY = 7
    LIGHT_GRAY = 8
    CYAN = 9
    PURPLE = 10
    BLUE = 11
    BROWN = 12
    GREEN = 13
    RED = 14
    BLACK = 15


@dataclass
class Bed:
    """
    Represents a bed block.

    Attributes:
        position: Bed position (x, y, z)
        color: Bed color
        block: Block object reference
    """

    position: tuple = (0, 0, 0)
    color: BedColor = BedColor.WHITE
    block: Optional[object] = None


class BedManager:
    """
    Manages bed tracking.

    This class handles:
    - Tracking sleep state
    - Finding nearest bed
    - Wake up events

    Sleep is tracked via entity metadata key 1 (is_sleeping).
    """

    # Bed block IDs (for different colors)
    BED_BLOCKS = {
        BedColor.WHITE: "minecraft:white_bed",
        BedColor.ORANGE: "minecraft:orange_bed",
        BedColor.MAGENTA: "minecraft:magenta_bed",
        BedColor.LIGHT_BLUE: "minecraft:light_blue_bed",
        BedColor.YELLOW: "minecraft:yellow_bed",
        BedColor.LIME: "minecraft:lime_bed",
        BedColor.PINK: "minecraft:pink_bed",
        BedColor.GRAY: "minecraft:gray_bed",
        BedColor.LIGHT_GRAY: "minecraft:light_gray_bed",
        BedColor.CYAN: "minecraft:cyan_bed",
        BedColor.PURPLE: "minecraft:purple_bed",
        BedColor.BLUE: "minecraft:blue_bed",
        BedColor.BROWN: "minecraft:brown_bed",
        BedColor.GREEN: "minecraft:green_bed",
        BedColor.RED: "minecraft:red_bed",
        BedColor.BLACK: "minecraft:black_bed",
    }

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.is_sleeping: bool = False
        self.bed_position: Optional[tuple] = None

        # Register for sleep events
        protocol.on("sleep", self._on_sleep)
        protocol.on("wake", self._on_wake)

    @property
    def bed(self) -> Optional[Bed]:
        """Get current bed"""
        if self.bed_position is None:
            return None

        return Bed(position=self.bed_position)

    def is_bed_block(self, block_name: str) -> bool:
        """
        Check if a block is a bed.

        Args:
            block_name: Block name

        Returns:
            True if block is a bed
        """
        return block_name.endswith("_bed")

    def find_nearest_bed(self, max_distance: float = 64.0) -> Optional[Bed]:
        """
        Find nearest bed block.

        Args:
            max_distance: Maximum search distance in blocks

        Returns:
            Nearest Bed or None if not found
        """
        # Get loaded chunks
        world = self.protocol.world if hasattr(self.protocol, "world") else None
        if not world:
            return None

        nearest = None
        min_dist = max_distance

        # Search in loaded chunks
        for chunk in world.get_loaded_chunks():
            for block_pos, block in chunk.get_blocks():
                # Check if block is a bed
                if block and self.is_bed_block(block.name):
                    # Get center position
                    bx, by, bz = block_pos
                    dist = math.sqrt(
                        (bx - self.protocol.position[0]) ** 2
                        + (by - self.protocol.position[1]) ** 2
                        + (bz - self.protocol.position[2]) ** 2
                    )

                    if dist < min_dist:
                        min_dist = dist
                        nearest = Bed(
                            position=block_pos,
                            color=self._get_bed_color(block.name),
                            block=block,
                        )

        return nearest

    def _get_bed_color(self, bed_name: str) -> BedColor:
        """
        Get bed color from block name.

        Args:
            bed_name: Bed block name (e.g., "minecraft:white_bed")

        Returns:
            BedColor enum value
        """
        # Extract color prefix (everything before "_bed")
        if "_bed" in bed_name:
            color_name = bed_name.split("_bed")[0].replace("minecraft:", "")
            # Map to BedColor enum
            color_map = {
                "white": BedColor.WHITE,
                "orange": BedColor.ORANGE,
                "magenta": BedColor.MAGENTA,
                "light_blue": BedColor.LIGHT_BLUE,
                "yellow": BedColor.YELLOW,
                "lime": BedColor.LIME,
                "pink": BedColor.PINK,
                "gray": BedColor.GRAY,
                "light_gray": BedColor.LIGHT_GRAY,
                "cyan": BedColor.CYAN,
                "purple": BedColor.PURPLE,
                "blue": BedColor.BLUE,
                "brown": BedColor.BROWN,
                "green": BedColor.GREEN,
                "red": BedColor.RED,
                "black": BedColor.BLACK,
            }
            return color_map.get(color_name.lower(), BedColor.WHITE)
        return BedColor.WHITE

    def _on_sleep(self, position: tuple) -> None:
        """
        Handle sleep event.

        Args:
            position: Bed position (x, y, z)
        """
        self.is_sleeping = True
        self.bed_position = position
        print(f"[BED] Started sleeping at {position}")
        self.protocol.emit("sleep", position)

    def _on_wake(self) -> None:
        """
        Handle wake event.

        Args:
            None (no data)
        """
        self.is_sleeping = False
        self.bed_position = None
        print("[BED] Woke up")
        self.protocol.emit("wake")

    async def sleep_in_bed(self, bed: Bed) -> bool:
        """
        Sleep in a bed.

        Args:
            bed: Bed to sleep in

        Returns:
            True if successful, False if failed
        """
        if bed.block is None:
            print("[BED] Error: Bed block not specified")
            return False

        # Check distance
        dist = math.sqrt(
            (bed.position[0] - self.protocol.position[0]) ** 2
            + (bed.position[1] - self.protocol.position[1]) ** 2
            + (bed.position[2] - self.protocol.position[2]) ** 2
        )

        if dist > 5.0:
            print(f"[BED] Too far from bed: {dist:.1f} blocks")
            return False

        # Click on bed to sleep
        from .block_interaction import BlockInteractionManager

        if hasattr(self.protocol, "_block_interaction"):
            await self.protocol.interact(bed.block)
            print(f"[BED] Attempting to sleep in {bed.block.name}")
            return True

        print("[BED] Error: Block interaction manager not available")
        return False


__all__ = [
    "BedManager",
    "Bed",
    "BedColor",
]
