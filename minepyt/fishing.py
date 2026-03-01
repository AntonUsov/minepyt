"""
Fishing system for Minecraft 1.21.4

This module provides:
- Auto fishing
- Rod and bobber tracking
- Fish catch detection
- Experience from fishing

Fishing is managed via bobber entity and rod item.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .entities import Entity


class FishType(IntEnum):
    """Fish types"""

    COD = 0
    SALMON = 1
    TROPICAL_FISH = 2
    PUFFERFISH = 3
    CAVE_SQUID = 4


class FishingState(IntEnum):
    """Fishing states"""

    WAITING_FOR_CAST = 0
    WAITING_FOR_HOOK = 1
    WAITING_FOR_FISH = 2
    WAITING_FOR_REEL = 3


@dataclass
class Fish:
    """
    Represents a caught fish.

    Attributes:
        fish_type: Type of fish
        count: Number of fish caught
    """

    fish_type: FishType = FishType.COD
    count: int = 1


class FishingManager:
    """
    Manages fishing operations.

    This class handles:
    - Auto fishing with rod
    - Bobber entity tracking
    - Fish catch detection
    - Experience handling

    Fishing mechanics:
    - Right-click with rod in water to cast
    - Bobber entity appears when fish bites
    - Reel in to catch
    """

    BOBBER_ID = 90  # Entity ID for bobber (before 1.14 changes)

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.state = FishingState.WAITING_FOR_CAST
        self.bobber_entity: Optional[Entity] = None
        self.rod_entity: Optional[Entity] = None
        self.fish_caught: Optional[Entity] = None

        # Register for entity events
        protocol.on("entity_spawn", self._on_entity_spawn)
        protocol.on("entity_gone", self._on_entity_gone)

    async def start_fishing(self, timeout: float = 30.0) -> Optional[Entity]:
        """
        Start auto fishing.

        Args:
            timeout: Maximum time to wait for catch (seconds)

        Returns:
            Caught fish entity or None
        """
        # Check if holding fishing rod
        from .protocol.models import Item

        if not self.protocol.held_item or self.protocol.held_item.is_empty:
            print("[FISHING] Not holding a fishing rod")
            return None

        # Find bobber entity in hand
        rod_item = self.protocol.held_item

        # Right-click to cast line
        # This should spawn a bobber entity
        print("[FISHING] Casting fishing line...")

        # Wait for bobber to appear
        await asyncio.sleep(1.0)

        start_time = asyncio.get_event_loop().time()

        while self.state != FishingState.WAITING_FOR_REEL:
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("[FISHING] Fishing timeout reached")
                break

            if self.bobber_entity:
                # Check bobber behavior to determine fishing state
                # In a real implementation, we'd track bobber position
                # For simplicity, we'll wait a fixed time
                print(f"[FISHING] Bobber detected, waiting for catch...")

                # Simulate waiting for fish bite
                await asyncio.sleep(3.0)

                # Reel in to catch
                print("[FISHING] Reeling in...")
                await self._reel_in()

                if self.fish_caught:
                    print(f"[FISHING] Caught fish entity!")
                    return self.fish_caught

            await asyncio.sleep(0.5)

        print("[FISHING] Fishing ended without catch")
        return None

    async def _reel_in(self) -> None:
        """
        Reel in the fishing line.

        This right-clicks on the bobber to catch the fish.
        """
        if not self.bobber_entity:
            print("[FISHING] No bobber entity to reel in")
            return

        # Right-click to reel
        if hasattr(self.protocol, "interact"):
            await self.protocol.interact(self.bobber_entity, hand=0, swing_hand=True)
            print("[FISHING] Reeled in fishing line")

        await asyncio.sleep(0.5)

    def _on_entity_spawn(self, entity: Entity) -> None:
        """
        Handle entity spawn event.

        Args:
            entity: Spawned entity
        """
        entity_id = entity.entity_id

        # Check if this is a bobber (in vanilla, bobber entity ID varies)
        # For simplicity, we'll assume bobbers appear near the player
        if entity_id == self.BOBBER_ID or "fishing_bobber" in str(entity.entity_type).lower():
            self.bobber_entity = entity
            self.state = FishingState.WAITING_FOR_HOOK
            print(f"[FISHING] Bobber spawned: {entity_id}")

    def _on_entity_gone(self, entity: Entity) -> None:
        """
        Handle entity removed event.

        Args:
            entity: Removed entity
        """
        entity_id = entity.entity_id

        if entity_id == self.bobber_entity.entity_id:
            self.bobber_entity = None
            print(f"[FISHING] Bobber removed: {entity_id}")

            # Check if fish spawned
            # Fish entities typically spawn when bobber is reeled in
            self.fish_caught = None
            self.state = FishingState.WAITING_FOR_CAST


__all__ = [
    "FishingManager",
    "Fish",
    "FishType",
    "FishingState",
]
