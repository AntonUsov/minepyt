"""
Explosion tracking for Minecraft 1.21.4

This module provides:
- Track explosion events
- Calculate explosion exposure
- Entity damage from explosions

Explosions are sent via SoundEffect (0x5D) and/or WorldParticles (0x29).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .entities import Entity


class ExplosionType(IntEnum):
    """Explosion types"""

    BLOCK_BREAK = 0
    ENTITY = 1


@dataclass
class Explosion:
    """
    Represents an explosion event.

    Attributes:
        position: Explosion position (x, y, z)
        power: Explosion power (affects damage and push force)
        source_entity_id: Optional entity ID that caused explosion
        explosion_type: Type of explosion
        block_break: Whether blocks are broken
        records: List of block positions broken
    """

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    power: float = 0.0
    source_entity_id: Optional[int] = None
    explosion_type: ExplosionType = ExplosionType.BLOCK_BREAK
    block_break: bool = False
    records: list = None


class ExplosionManager:
    """
    Manages explosion tracking.

    This class handles:
    - Explosion event tracking
    - Exposure calculation
    - Entity damage from explosions

    Explosions are tracked via:
    - SoundEffect (0x5D) with sound categories 7 (block break) and 8 (entity explode)
    - WorldParticles (0x29) with particle ID types
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Register for explosion events
        protocol.on("explosion", self._on_explosion)

    def _on_explosion(self, explosion: Explosion) -> None:
        """
        Handle explosion event.

        Args:
            explosion: Explosion event object
        """
        print(f"[EXPLOSION] Explosion at {explosion.position}, power: {explosion.power:.2f}")

        # Calculate exposure for bot
        bot_pos = self.protocol.position
        dist = math.sqrt(
            (explosion.position[0] - bot_pos[0]) ** 2
            + (explosion.position[1] - bot_pos[1]) ** 2
            + (explosion.position[2] - bot_pos[2]) ** 2
        )

        # Exposure = power / (distance + 1)
        exposure = explosion.power / (dist + 1) if dist >= 0 else explosion.power

        print(f"[EXPLOSION] Distance: {dist:.1f}, Exposure: {exposure:.4f}")

        # Check if bot should take damage
        max_health = 20  # Max health

        if exposure > 1.0 and hasattr(self.protocol, "health"):
            damage = exposure * (max_health - 1.0)  # Scale damage

            current_health = self.protocol.health
            new_health = max(0, current_health - damage)

            if new_health < current_health:
                print(f"[EXPLOSION] Taking {damage:.2f} damage ({new_health:.2f}/{max_health})")
                # Health update will be handled by health plugin

        self.protocol.emit("explosion", explosion)


__all__ = [
    "ExplosionManager",
    "Explosion",
    "ExplosionType",
]
