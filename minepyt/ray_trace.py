"""
Ray tracing (raycasting) for Minecraft 1.21.4

This module provides:
- Block line-of-sight checks
- Entity line-of-sight checks
- Raycast to find blocks/entities

Raycasting is used for checking if a block/entity is visible from a position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class HitResult(IntEnum):
    """Raycast hit result"""

    BLOCK = 0
    ENTITY = 1
    MISS = 2


@dataclass
class RaycastTarget:
    """
    Represents a raycast target.

    Attributes:
        type: Type of target (block, entity, or miss)
        position: Hit position (x, y, z)
        face: Block face direction
        entity: Entity object (if entity type)
        block: Block object (if block type)
    """

    type: HitResult = HitResult.MISS
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    face: int = 0  # Block face (0=down, 1=up, 2=north, 3=south, 4=west, 5=east)
    entity: Optional[object] = None
    block: Optional[object] = None


class RayTraceManager:
    """
    Manages raycasting operations.

    This class handles:
    - Block line-of-sight checks
    - Entity line-of-sight checks
    - Raycast for finding targets

    Raycasting is used via line-of-sight calculations.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

    def can_see_block(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        max_distance: float = 64.0,
    ) -> bool:
        """
        Check if a block at position is visible.

        Args:
            start: Start position
            end: End position to check visibility for
            max_distance: Maximum distance to check

        Returns:
            True if block is visible, False if obstructed
        """
        world = self.protocol.world if hasattr(self.protocol, "world") else None
        if not world:
            return False

        # Calculate direction vector
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > max_distance:
            return False

        # Normalize direction
        steps = int(distance / 1.0)  # Check every block
        step_x = dx / steps if steps > 0 else 0
        step_y = dy / steps if steps > 0 else 0
        step_z = dz / steps if steps > 0 else 0

        # Check each step
        for i in range(steps):
            check_x = int(start[0] + step_x * i)
            check_y = int(start[1] + step_y * i)
            check_z = int(start[2] + step_z * i)

            # Get block at position
            block = world.get_block(check_x, check_y, check_z)

            # Check if block is solid (not air)
            if block and block.name != "minecraft:air":
                return True

        return False

    def can_see_entity(
        self,
        position: Tuple[float, float, float],
        entity: object,
        max_distance: float = 64.0,
    ) -> bool:
        """
        Check if an entity is visible from position.

        Args:
            position: Start position
            entity: Entity to check visibility for
            max_distance: Maximum distance to check

        Returns:
            True if entity is visible, False if obstructed
        """
        world = self.protocol.world if hasattr(self.protocol, "world") else None
        if not world:
            return False

        # Calculate direction to entity
        ex, ey, ez = entity.position
        dx = ex - position[0]
        dy = ey - position[1]
        dz = ez - position[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > max_distance:
            return True  # Too far

        # Normalize direction
        steps = int(distance / 1.0)
        step_x = dx / steps if steps > 0 else 0
        step_y = dy / steps if steps > 0 else 0
        step_z = dz / steps if steps > 0 else 0

        # Check each step
        for i in range(steps):
            check_x = int(position[0] + step_x * i)
            check_y = int(position[1] + step_y * i)
            check_z = int(position[2] + step_z * i)

            # Get block at position
            block = world.get_block(check_x, check_y, check_z)

            # Check if block is solid (not air)
            if block and block.name != "minecraft:air":
                return False  # Blocked by solid block

        return True  # Not blocked

    def raycast_to_block(
        self,
        start: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 64.0,
    ) -> Optional[RaycastTarget]:
        """
        Raycast to find the first block in a direction.

        Args:
            start: Start position
            direction: Direction vector (normalized)
            max_distance: Maximum distance to raycast

        Returns:
            RaycastTarget object or None if nothing found
        """
        world = self.protocol.world if hasattr(self.protocol, "world") else None
        if not world:
            return None

        # Calculate step size
        step = 1.0  # Check every block

        # Normalize direction
        mag = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
        if mag == 0:
            return None

        step_x = (direction[0] / mag) * step
        step_y = direction[1] / mag * step
        step_z = direction[2] / mag * step

        # Raycast
        for i in range(int(max_distance)):
            check_x = int(start[0] + step_x * i)
            check_y = int(start[1] + step_y * i)
            check_z = int(start[2] + step_z * i)

            # Get block at position
            block = world.get_block(check_x, check_y, check_z)

            # Check if block is solid
            if block and block.name != "minecraft:air":
                # Calculate face based on direction
                return RaycastTarget(
                    type=HitResult.BLOCK,
                    position=(check_x, check_y, check_z),
                    face=self._get_face(direction, step_x, step_y, step_z),
                    block=block,
                )

        return None

    def raycast_to_entity(
        self,
        start: Tuple[float, float, float],
        entity: object,
        max_distance: float = 64.0,
    ) -> Optional[RaycastTarget]:
        """
        Raycast to find if entity is visible.

        Args:
            start: Start position
            entity: Entity to check
            max_distance: Maximum distance to raycast

        Returns:
            RaycastTarget object with entity type if visible
        """
        # Use can_see_entity for simplified check
        if self.can_see_entity(start, entity, max_distance):
            return RaycastTarget(
                type=HitResult.ENTITY,
                position=entity.position,
                entity=entity,
            )

        return None

    def _get_face(self, direction: Tuple[float, float, float], dx: float, dy: float, dz: float) -> int:
        """
        Determine block face from ray direction.

        Args:
            direction: Ray direction vector
            dx, dy, dz: Direction components
        """
        ax, ay, az = abs(dx), abs(dy), abs(dz)

        # Determine which axis has the largest component
        if ax >= ay and ax >= az:
            # X is dominant
            if ay >= az:
                return 4 if dy > 0 else 5  # North or South
            else:
                return 3 if dz > 0 else 2  # Up or Down
        elif ay >= az:
            # Y is dominant
            if ax >= az:
                return 1 if dx > 0 else 2  # West or East
            else:
                return 0 if dz > 0 else 1  # Up or Down
        else:
            # Z is dominant
            if ax >= ay:
                return 2 if dx > 0 else 3  # West or East
            else:
                return 1 if dy > 0 else 2  # Up or Down

        return 0  # Default (down)


__all__ = [
    "RayTraceManager",
    "RaycastTarget",
    "HitResult",
]
