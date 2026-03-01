"""
Combat system for Minecraft 1.21.4

This module provides:
- Attack with cooldown (1.9+ combat)
- Swing arm animation
- Damage tracking
- Entity health monitoring

Port of mineflayer/lib/plugins/entities.js combat functions
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class AttackType(IntEnum):
    """Interact packet types for 1.21.4"""

    INTERACT = 0  # Right-click on entity
    ATTACK = 1  # Left-click (attack)
    INTERACT_AT = 2  # Right-click at specific position


@dataclass
class CombatState:
    """Tracks combat-related state"""

    last_attack_time: float = 0.0
    attack_cooldown: float = 0.6  # Base cooldown in seconds (1.9+ combat)
    attack_speed_bonus: float = 0.0

    # Stats
    total_attacks: int = 0
    total_damage_dealt: float = 0.0


class CombatManager:
    """
    Manages combat functionality.

    This class handles:
    - Attack cooldown (1.9+ combat system)
    - Attack packets
    - Swing arm animation
    - Damage tracking
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.state = CombatState()

    def get_attack_cooldown_progress(self) -> float:
        """
        Get current attack cooldown progress (0.0 to 1.0).

        In 1.9+ combat, attacks deal reduced damage if cooldown is not full.
        """
        elapsed = time.time() - self.state.last_attack_time
        cooldown = self.state.attack_cooldown - self.state.attack_speed_bonus
        cooldown = max(0.25, cooldown)  # Minimum 0.25 seconds

        progress = min(1.0, elapsed / cooldown)
        return progress

    def is_attack_ready(self) -> bool:
        """Check if attack cooldown has finished"""
        return self.get_attack_cooldown_progress() >= 1.0

    async def attack(self, entity, swing: bool = True) -> bool:
        """
        Attack an entity.

        Args:
            entity: Entity object or entity ID
            swing: Whether to swing arm animation

        Returns:
            True if attack was sent
        """
        # Get entity
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.protocol.entity_manager.get(entity_id)

        if entity_obj is None:
            print(f"[COMBAT] Entity {entity_id} not found")
            return False

        if entity_obj.is_dead:
            print(f"[COMBAT] Entity {entity_id} is dead")
            return False

        # Check distance (max 6 blocks for attack)
        if self.protocol.position:
            dist = entity_obj.distance_to(self.protocol.position)
            if dist > 6.0:
                print(f"[COMBAT] Entity {entity_id} too far: {dist:.1f} blocks")
                return False

        # Check cooldown
        cooldown_progress = self.get_attack_cooldown_progress()
        if cooldown_progress < 1.0:
            # Attack will deal reduced damage, but we still send it
            pass

        # Look at entity
        await self.protocol.look_at(
            entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z
        )

        # Send attack packet
        await self._send_interact(entity_id, AttackType.ATTACK)

        # Swing arm
        if swing:
            await self.swing_arm()

        # Update state
        self.state.last_attack_time = time.time()
        self.state.total_attacks += 1

        # Calculate potential damage (simplified)
        base_damage = 1.0  # Fist damage
        damage = base_damage * cooldown_progress
        self.state.total_damage_dealt += damage

        self.protocol.emit("entity_attack", entity_obj)

        return True

    async def interact(self, entity, hand: int = 0, swing: bool = True) -> bool:
        """
        Interact with an entity (right-click).

        Args:
            entity: Entity object or entity ID
            hand: 0=main hand, 1=off hand
            swing: Whether to swing arm animation

        Returns:
            True if interaction was sent
        """
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.protocol.entity_manager.get(entity_id)

        if entity_obj is None:
            return False

        # Look at entity
        await self.protocol.look_at(
            entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z
        )

        # Send interact packet
        await self._send_interact(entity_id, AttackType.INTERACT, hand=hand)

        if swing:
            await self.swing_arm()

        self.protocol.emit("entity_interact", entity_obj)
        return True

    async def use_on(
        self,
        entity,
        target_x: float = 0.5,
        target_y: float = 0.5,
        target_z: float = 0.5,
        hand: int = 0,
        swing: bool = True,
    ) -> bool:
        """
        Interact at a specific position on an entity.

        Used for entities with multiple interactable parts
        (e.g., armor stand, item frame).
        """
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.protocol.entity_manager.get(entity_id)

        if entity_obj is None:
            return False

        # Calculate world coordinates
        world_x = entity_obj.x + (target_x - 0.5) * entity_obj.width
        world_y = entity_obj.y + target_y * entity_obj.height
        world_z = entity_obj.z + (target_z - 0.5) * entity_obj.width

        # Look at position
        await self.protocol.look_at(world_x, world_y, world_z)

        # Send interact_at packet
        await self._send_interact(
            entity_id,
            AttackType.INTERACT_AT,
            target_x=world_x,
            target_y=world_y,
            target_z=world_z,
            hand=hand,
        )

        if swing:
            await self.swing_arm()

        self.protocol.emit("entity_use_on", entity_obj, (target_x, target_y, target_z))
        return True

    async def _send_interact(
        self,
        entity_id: int,
        interact_type: AttackType,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        hand: int = 0,
        sneaking: bool = False,
    ) -> None:
        """Send Interact packet (0x10 serverbound for 1.21.4)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        buf.write_varint(entity_id)
        buf.write_varint(interact_type)

        if interact_type == AttackType.INTERACT_AT:
            buf.write_value(StructFormat.FLOAT, target_x)
            buf.write_value(StructFormat.FLOAT, target_y)
            buf.write_value(StructFormat.FLOAT, target_z)
            buf.write_varint(hand)
        elif interact_type == AttackType.INTERACT:
            buf.write_varint(hand)

        buf.write_value(StructFormat.BOOL, sneaking)

        await self.protocol._write_packet(0x10, bytes(buf))

    async def swing_arm(self, hand: int = 0) -> None:
        """
        Send arm swing animation.

        Args:
            hand: 0=main hand, 1=off hand
        """
        from mcproto.buffer import Buffer

        buf = Buffer()
        buf.write_varint(hand)
        await self.protocol._write_packet(0x35, bytes(buf))

    async def attack_loop(self, entity, max_attacks: int = 10, stop_on_death: bool = True) -> int:
        """
        Attack an entity repeatedly until dead or max attacks reached.

        Args:
            entity: Entity to attack
            max_attacks: Maximum number of attacks
            stop_on_death: Stop when entity dies

        Returns:
            Number of attacks performed
        """
        attacks = 0

        while attacks < max_attacks:
            # Get fresh entity reference
            if hasattr(entity, "entity_id"):
                entity_id = entity.entity_id
            else:
                entity_id = int(entity)

            entity_obj = self.protocol.entity_manager.get(entity_id)

            if entity_obj is None:
                print("[COMBAT] Entity gone")
                break

            if stop_on_death and entity_obj.is_dead:
                print("[COMBAT] Entity dead")
                break

            # Wait for cooldown
            while not self.is_attack_ready():
                await asyncio.sleep(0.05)

            # Attack
            success = await self.attack(entity_obj)
            if success:
                attacks += 1

            await asyncio.sleep(0.1)

        return attacks


__all__ = [
    "CombatManager",
    "CombatState",
    "AttackType",
]
