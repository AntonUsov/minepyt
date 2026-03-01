"""
Spawn point tracking for Minecraft 1.21.4

This module provides:
- Track spawn position
- Spawn point type (bed, respawn anchor, world spawn)

Spawn point is tracked via PlayerPositionLook packet (0x3E).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class SpawnPointType(IntEnum):
    """Spawn point types"""

    WORLD_SPAWN = 0
    BED = 1
    RESPAWN_ANCHOR = 2
    PORTAL = 3


@dataclass
class SpawnPoint:
    """
    Represents a spawn point.

    Attributes:
        position: Spawn position (x, y, z)
        type: Type of spawn point
        is_silent: Whether spawn was silent (no message)
    """

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    type: SpawnPointType = SpawnPointType.WORLD_SPAWN
    is_silent: bool = False


class SpawnPointManager:
    """
    Manages spawn point tracking.

    This class handles:
    - Spawn position tracking
    - Spawn point type detection
    - Respawn handling

    Spawn point is tracked via PlayerPositionLook (0x3E) packet.
    When position equals previous position, it's a respawn.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self._last_position: Optional[Tuple[float, float, float]] = None
        self.spawn_point: Optional[SpawnPoint] = None

        # Register for player position updates
        protocol.on("position", self._on_position)

    @property
    def current_spawn_point(self) -> Optional[SpawnPoint]:
        """Get current spawn point"""
        return self.spawn_point

    def _on_position(self, position: Tuple[float, float, float]) -> None:
        """
        Handle player position update.

        Args:
            position: New player position (x, y, z, yaw, pitch, on_ground)
        """
        x, y, z = position[:3]

        # Check if position equals last position (indicates respawn)
        if self._last_position:
            dx = abs(x - self._last_position[0])
            dy = abs(y - self._last_position[1])
            dz = abs(z - self._last_position[2])

            # If position is same (or very close), it's a respawn
            if dx < 0.01 and dy < 0.01 and dz < 0.01:
                # Determine spawn type based on surrounding blocks
                spawn_type = self._detect_spawn_type(position)

                self.spawn_point = SpawnPoint(
                    position=(x, y, z),
                    type=spawn_type,
                    is_silent=True,
                )

                print(f"[SPAWN_POINT] Respawned at ({x:.1f}, {y:.1f}, {z:.1f}) - Type: {spawn_type.name}")
                self.protocol.emit("spawn", self.spawn_point)

        self._last_position = (x, y, z)

    def _detect_spawn_type(self, position) -> SpawnPointType:
        """
        Detect spawn point type based on position context.

        Args:
            position: Full position data (x, y, z, yaw, pitch, on_ground)

        Returns:
            SpawnPointType
        """
        # Check if sleeping (bed spawn)
        if hasattr(self.protocol, "_manager") and hasattr(self.protocol._manager, "bed"):
            if self.protocol._manager.bed.is_sleeping:
                return SpawnPointType.BED

        # Check if near respawn anchor (would need world checking)
        # For simplicity, default to world spawn
        return SpawnPointType.WORLD_SPAWN

    def respawn(self) -> None:
        """
        Trigger respawn.

        This sends a respawn request to server.
        """
        print("[SPAWN_POINT] Requesting respawn...")
        # Respawn is handled by server via ClientCommand (0x0D)
        # For now, we'll disconnect and reconnect
        from .kick import KickManager

        if hasattr(self.protocol, "_manager") and hasattr(self.protocol._manager, "kick"):
            asyncio.create_task(self.protocol._manager.quit("Respawning"))

        print("[SPAWN_POINT] Disconnecting to respawn...")


__all__ = [
    "SpawnPointManager",
    "SpawnPoint",
    "SpawnPointType",
]
