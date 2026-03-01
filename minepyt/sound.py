"""
Sound effect tracking for Minecraft 1.21.4

This module provides:
- Track sound effects from server
- Sound position and volume tracking

Sounds are sent via SoundEffect (0x5D) and NamedSoundEffect (0x6D) packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


@dataclass
class SoundEffect:
    """
    Represents a sound effect.

    Attributes:
        sound_id: Sound ID or sound name
        category: Sound category
        position: (x, y, z) position (divided by 8)
        volume: Sound volume (0.0 to 1.0)
        pitch: Sound pitch (0.5 to 2.0)
        seed: Random seed for sound variation
    """

    sound_id: Optional[int] = None
    sound_name: Optional[str] = None
    category: int = 0
    position: tuple = (0, 0, 0)
    volume: float = 1.0
    pitch: float = 1.0
    seed: int = 0


class SoundManager:
    """
    Manages sound effect tracking.

    This class handles:
    - Sound effect event emission
    - Sound data parsing

    Sound packets:
    - SoundEffect (0x5D): Sound by ID
    - NamedSoundEffect (0x6D): Sound by name
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Register for sound packets
        protocol.on("sound_effect", self._on_sound_effect)
        protocol.on("named_sound_effect", self._on_named_sound_effect)

    def _on_sound_effect(self, packet_data: dict) -> None:
        """
        Handle sound effect packet (0x5D).

        Args:
            packet_data: Decoded packet data
        """
        sound_id = packet_data.get("sound_id", 0)
        category = packet_data.get("sound_category", 0)

        # Position (divided by 8)
        x = packet_data.get("x", 0) / 8
        y = packet_data.get("y", 0) / 8
        z = packet_data.get("z", 0) / 8

        volume = packet_data.get("volume", 1.0)
        pitch = packet_data.get("pitch", 1.0)
        seed = packet_data.get("seed", 0)

        sound = SoundEffect(
            sound_id=sound_id,
            category=category,
            position=(x, y, z),
            volume=volume,
            pitch=pitch,
            seed=seed,
        )

        print(
            f"[SOUND] Sound ID {sound_id} at ({x:.1f}, {y:.1f}, {z:.1f}) vol={volume:.2f} pitch={pitch:.2f}"
        )
        self.protocol.emit("sound_effect_heard", sound_id, category, (x, y, z), volume, pitch)

    def _on_named_sound_effect(self, packet_data: dict) -> None:
        """
        Handle named sound effect packet (0x6D).

        Args:
            packet_data: Decoded packet data
        """
        sound_name = packet_data.get("sound_name")
        if sound_name is None:
            return

        # Check if this is an ItemSoundHolder (with data)
        if "sound" in packet_data:
            sound_data = packet_data["sound"]
            if isinstance(sound_data, dict) and "sound_name" in sound_data:
                sound_name = sound_data["sound_name"]
            else:
                # Using sound ID directly
                print(f"[SOUND] Named sound with ID: {sound_name}")
                sound_id = None
        else:
            # Plain sound name
            sound_id = None

        category = packet_data.get("sound_category", 0)

        # Position (divided by 8)
        x = packet_data.get("x", 0) / 8
        y = packet_data.get("y", 0) / 8
        z = packet_data.get("z", 0) / 8

        volume = packet_data.get("volume", 1.0)
        pitch = packet_data.get("pitch", 1.0)
        seed = packet_data.get("seed", 0)

        sound = SoundEffect(
            sound_id=sound_id,
            sound_name=sound_name,
            category=category,
            position=(x, y, z),
            volume=volume,
            pitch=pitch,
            seed=seed,
        )

        name_or_id = sound_name if sound_name else f"ID {sound_id}"
        print(
            f"[SOUND] Sound {name_or_id} at ({x:.1f}, {y:.1f}, {z:.1f}) vol={volume:.2f} pitch={pitch:.2f}"
        )
        self.protocol.emit(
            "sound_effect_heard",
            sound_name if sound_name else sound_id,
            category,
            (x, y, z),
            volume,
            pitch,
        )


__all__ = [
    "SoundManager",
    "SoundEffect",
]
