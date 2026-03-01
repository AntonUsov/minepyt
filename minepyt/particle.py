"""
Particle tracking for Minecraft 1.21.4

This module provides:
- Track particles from server
- Particle type and data parsing

Particles are sent via WorldParticles packet (0x29).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


@dataclass
class Particle:
    """
    Represents a particle effect.

    Attributes:
        particle_id: Particle type ID
        position: (x, y, z) position of particle
        long_distance: Whether particle is long-distance visible
        data: Optional particle-specific data
    """

    particle_id: int = 0
    position: tuple = (0, 0, 0)
    long_distance: bool = False
    offset: Optional[tuple] = None  # For block break particles
    data: Optional[dict] = None


class ParticleManager:
    """
    Manages particle tracking.

    This class handles:
    - Particle event emission
    - Particle data parsing

    Particle packets:
    - WorldParticles (0x29): Particle spawn
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Register for particle packets
        protocol.on("world_particles", self._on_world_particles)

    def _on_world_particles(self, packet_data: dict) -> None:
        """
        Handle world particles packet (0x29).

        Args:
            packet_data: Decoded packet data
        """
        particle_id = packet_data.get("particle_id", 0)
        long_distance = packet_data.get("long_distance", False)

        # Position (scaled by 8)
        x = packet_data.get("x", 0) / 8
        y = packet_data.get("y", 0) / 8
        z = packet_data.get("z", 0) / 8

        # Offset (for block break particles)
        offset = None
        if "offset_x" in packet_data:
            offset = (
                packet_data.get("offset_x", 0) / 8,
                packet_data.get("offset_y", 0) / 8,
                packet_data.get("offset_z", 0) / 8,
            )

        # Particle-specific data
        data = {}
        if "item_stack" in packet_data:
            data["item_stack"] = packet_data["item_stack"]
        if "block_state" in packet_data:
            data["block_state"] = packet_data["block_state"]

        particle = Particle(
            particle_id=particle_id,
            position=(x, y, z),
            long_distance=long_distance,
            offset=offset,
            data=data if data else None,
        )

        print(f"[PARTICLE] Particle {particle_id} at ({x:.1f}, {y:.1f}, {z:.1f})")
        self.protocol.emit("particle", particle)


__all__ = [
    "ParticleManager",
    "Particle",
]
