"""
Movement and physics system for Minecraft 1.21.4

This module provides:
- Control states (forward, back, left, right, jump, sprint, sneak)
- Position and rotation tracking
- Physics tick system
- Movement packets

Port of mineflayer/lib/plugins/physics.js
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class PlayerAction(IntEnum):
    """Player action IDs for Entity Action packet (1.21.4)"""

    START_SNEAKING = 0
    STOP_SNEAKING = 1
    LEAVE_BED = 2
    START_SPRINTING = 3
    STOP_SPRINTING = 4
    START_HORSE_JUMP = 5
    STOP_HORSE_JUMP = 6
    OPEN_VEHICLE_INVENTORY = 7
    START_ELYTRA_FLYING = 8


@dataclass
class ControlState:
    """Player movement control states"""

    forward: bool = False
    back: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False
    sprint: bool = False
    sneak: bool = False


@dataclass
class LastSentPosition:
    """Last sent position to server"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    on_ground: bool = False
    time: float = 0.0


class MovementManager:
    """
    Manages player movement and physics.

    This class handles:
    - Control state management
    - Position/rotation updates
    - Physics tick loop
    - Movement packet sending
    """

    # Physics constants
    PHYSICS_INTERVAL_MS = 50  # 50ms = 20 ticks per second
    PHYSICS_TIMESTEP = 0.05  # 50ms in seconds
    YAW_SPEED = 150.0  # Degrees per second
    PITCH_SPEED = 150.0  # Degrees per second
    MAX_CATCHUP_TICKS = 4

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Control states
        self.control = ControlState()

        # Position tracking
        self.last_sent = LastSentPosition()
        self.last_sent_yaw: Optional[float] = None
        self.last_sent_pitch: Optional[float] = None

        # Physics state
        self.physics_enabled = True
        self._physics_task: Optional[asyncio.Task] = None
        self._running = False
        self._jump_queued = False
        self._jump_ticks = 0

        # Velocity (for physics simulation)
        self.velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)

        # Movement speed
        self.walk_speed = 4.3  # blocks per second
        self.sprint_speed = 5.6  # blocks per second
        self.sneak_speed = 1.3  # blocks per second
        self.jump_velocity = 0.42  # blocks per tick

    def set_control_state(self, control: str, state: bool) -> None:
        """Set a control state (forward, back, left, right, jump, sprint, sneak)"""
        if not hasattr(self.control, control):
            raise ValueError(f"Invalid control: {control}")

        old_state = getattr(self.control, control)
        if old_state == state:
            return

        setattr(self.control, control, state)

        if control == "jump" and state:
            self._jump_queued = True
        elif control == "sprint":
            self._send_sprint(state)
        elif control == "sneak":
            self._send_sneak(state)

    def get_control_state(self, control: str) -> bool:
        """Get a control state"""
        if not hasattr(self.control, control):
            raise ValueError(f"Invalid control: {control}")
        return getattr(self.control, control)

    def clear_control_states(self) -> None:
        """Clear all control states"""
        for control in ["forward", "back", "left", "right", "jump", "sprint", "sneak"]:
            self.set_control_state(control, False)

    def _send_sprint(self, sprinting: bool) -> None:
        """Send sprint entity action"""
        action = PlayerAction.START_SPRINTING if sprinting else PlayerAction.STOP_SPRINTING
        asyncio.create_task(self._send_entity_action(action))

    def _send_sneak(self, sneaking: bool) -> None:
        """Send sneak entity action"""
        action = PlayerAction.START_SNEAKING if sneaking else PlayerAction.STOP_SNEAKING
        asyncio.create_task(self._send_entity_action(action))

    async def _send_entity_action(self, action: PlayerAction) -> None:
        """Send Entity Action packet (0x1B for 1.21.4)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        buf.write_varint(self.protocol.entity_id or 0)
        buf.write_varint(action)
        buf.write_varint(0)  # jump boost

        await self.protocol._write_packet(0x1B, bytes(buf))

    async def send_position(self) -> None:
        """Send player position packet (0x1D for 1.21.4 - MOVE_PLAYER_POS_ROT)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        pos = self.protocol.position
        yaw = self.protocol.yaw
        pitch = self.protocol.pitch

        buf = Buffer()
        buf.write_value(StructFormat.DOUBLE, pos[0])
        buf.write_value(StructFormat.DOUBLE, pos[1])
        buf.write_value(StructFormat.DOUBLE, pos[2])
        buf.write_value(StructFormat.FLOAT, yaw)
        buf.write_value(StructFormat.FLOAT, pitch)
        # 1.21.4: flags byte (on_ground bit + has_horizontal_collision bit)
        flags = 0x01 if self.protocol.on_ground else 0x00
        buf.write_value(StructFormat.BYTE, flags)

        await self.protocol._write_packet(0x1D, bytes(buf))

        # Update last sent
        self.last_sent.x = pos[0]
        self.last_sent.y = pos[1]
        self.last_sent.z = pos[2]
        self.last_sent.yaw = yaw
        self.last_sent.pitch = pitch
        self.last_sent.on_ground = self.protocol.on_ground
        self.last_sent.time = time.time()

    async def send_position_only(self) -> None:
        """Send player position only (0x20 for 1.21.4 - MOVE_PLAYER_POS)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        pos = self.protocol.position

        buf = Buffer()
        buf.write_value(StructFormat.DOUBLE, pos[0])
        buf.write_value(StructFormat.DOUBLE, pos[1])
        buf.write_value(StructFormat.DOUBLE, pos[2])
        flags = 0x01 if self.protocol.on_ground else 0x00
        buf.write_value(StructFormat.BYTE, flags)

        await self.protocol._write_packet(0x20, bytes(buf))

        self.last_sent.x = pos[0]
        self.last_sent.y = pos[1]
        self.last_sent.z = pos[2]
        self.last_sent.on_ground = self.protocol.on_ground
        self.last_sent.time = time.time()

    async def send_look_only(self) -> None:
        """Send player look only (0x21 for 1.21.4 - MOVE_PLAYER_ROT)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        buf.write_value(StructFormat.FLOAT, self.protocol.yaw)
        buf.write_value(StructFormat.FLOAT, self.protocol.pitch)
        flags = 0x01 if self.protocol.on_ground else 0x00
        buf.write_value(StructFormat.BYTE, flags)

        await self.protocol._write_packet(0x21, bytes(buf))

        self.last_sent.yaw = self.protocol.yaw
        self.last_sent.pitch = self.protocol.pitch
        self.last_sent.on_ground = self.protocol.on_ground

    async def send_flying(self) -> None:
        """Send flying/on_ground packet (0x1E for 1.21.4 - MOVE_PLAYER_STATUS_ONLY)"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        buf = Buffer()
        flags = 0x01 if self.protocol.on_ground else 0x00
        buf.write_value(StructFormat.BYTE, flags)

        await self.protocol._write_packet(0x1E, bytes(buf))

        self.last_sent.on_ground = self.protocol.on_ground

    def _delta_yaw(self, yaw1: float, yaw2: float) -> float:
        """Calculate delta yaw normalized to [-PI, PI]"""
        d_yaw = (yaw1 - yaw2) % 360.0
        if d_yaw < -180:
            d_yaw += 360.0
        elif d_yaw > 180:
            d_yaw -= 360.0
        return d_yaw

    async def update_position(self) -> None:
        """Update and send position to server"""
        if not self.protocol.is_alive:
            return

        now = time.time()

        # Smooth yaw/pitch transitions
        if self.last_sent_yaw is None:
            self.last_sent_yaw = self.protocol.yaw
        if self.last_sent_pitch is None:
            self.last_sent_pitch = self.protocol.pitch

        d_yaw = self._delta_yaw(self.protocol.yaw, self.last_sent_yaw)
        d_pitch = self.protocol.pitch - self.last_sent_pitch

        max_delta_yaw = self.PHYSICS_TIMESTEP * self.YAW_SPEED
        max_delta_pitch = self.PHYSICS_TIMESTEP * self.PITCH_SPEED

        self.last_sent_yaw += self._clamp(-max_delta_yaw, d_yaw, max_delta_yaw)
        self.last_sent_pitch += self._clamp(-max_delta_pitch, d_pitch, max_delta_pitch)

        pos = self.protocol.position

        # Check if position or look updated
        position_updated = (
            self.last_sent.x != pos[0]
            or self.last_sent.y != pos[1]
            or self.last_sent.z != pos[2]
            or (now - self.last_sent.time) >= 1.0  # Send every second
        )
        look_updated = (
            self.last_sent.yaw != self.protocol.yaw or self.last_sent.pitch != self.protocol.pitch
        )

        if position_updated and look_updated:
            await self.send_position()
        elif position_updated:
            await self.send_position_only()
        elif look_updated:
            await self.send_look_only()
        elif self.protocol.on_ground != self.last_sent.on_ground:
            await self.send_flying()

        self.last_sent.on_ground = self.protocol.on_ground

    @staticmethod
    def _clamp(min_val: float, val: float, max_val: float) -> float:
        """Clamp a value between min and max"""
        return max(min_val, min(val, max_val))

    async def tick_physics(self) -> None:
        """Run one physics tick"""
        if not self.physics_enabled:
            return

        # Apply control states to movement
        await self._apply_movement()

        # Apply gravity
        await self._apply_gravity()

        # Send position update
        await self.update_position()

        # Emit physics tick event
        self.protocol.emit("physicsTick")

    async def _apply_movement(self) -> None:
        """Apply control states to movement"""
        if not self.protocol.position:
            return

        # Calculate movement speed
        if self.control.sprint:
            speed = self.sprint_speed
        elif self.control.sneak:
            speed = self.sneak_speed
        else:
            speed = self.walk_speed

        # Convert to blocks per tick
        speed_per_tick = speed * self.PHYSICS_TIMESTEP

        # Calculate movement direction based on yaw
        yaw_rad = math.radians(self.protocol.yaw)

        dx = 0.0
        dz = 0.0

        if self.control.forward:
            dx -= math.sin(yaw_rad) * speed_per_tick
            dz += math.cos(yaw_rad) * speed_per_tick
        if self.control.back:
            dx += math.sin(yaw_rad) * speed_per_tick
            dz -= math.cos(yaw_rad) * speed_per_tick
        if self.control.left:
            dx -= math.cos(yaw_rad) * speed_per_tick
            dz -= math.sin(yaw_rad) * speed_per_tick
        if self.control.right:
            dx += math.cos(yaw_rad) * speed_per_tick
            dz += math.sin(yaw_rad) * speed_per_tick

        # Apply jump
        if self.control.jump and self.protocol.on_ground:
            self.velocity = (self.velocity[0], self.jump_velocity, self.velocity[2])
            self.protocol.on_ground = False

        # Apply velocity
        x, y, z = self.protocol.position
        vx, vy, vz = self.velocity

        new_x = x + dx + vx * self.PHYSICS_TIMESTEP
        new_y = y + vy
        new_z = z + dz + vz * self.PHYSICS_TIMESTEP

        self.protocol.position = (new_x, new_y, new_z)

    async def _apply_gravity(self) -> None:
        """Apply gravity to velocity"""
        if not self.protocol.on_ground:
            # Gravity acceleration (blocks per tick squared)
            gravity = 0.08
            air_resistance = 0.02

            vx, vy, vz = self.velocity
            vy -= gravity
            vx *= 1 - air_resistance
            vz *= 1 - air_resistance

            self.velocity = (vx, vy, vz)

            # Simple ground check (y = 0 for now, should check actual blocks)
            x, y, z = self.protocol.position
            if y <= -60:  # Minimum Y for 1.18+
                self.protocol.position = (x, -60, z)
                self.velocity = (0, 0, 0)
                self.protocol.on_ground = True
        else:
            self.velocity = (0, 0, 0)

    async def _physics_loop(self) -> None:
        """Main physics loop"""
        last_time = time.time()
        time_accumulator = 0.0

        while self._running:
            now = time.time()
            delta = now - last_time
            last_time = now

            time_accumulator += delta
            catchup_ticks = 0

            while time_accumulator >= self.PHYSICS_TIMESTEP:
                await self.tick_physics()
                time_accumulator -= self.PHYSICS_TIMESTEP
                catchup_ticks += 1
                if catchup_ticks >= self.MAX_CATCHUP_TICKS:
                    break

            await asyncio.sleep(self.PHYSICS_TIMESTEP / 2)

    def start(self) -> None:
        """Start the physics loop"""
        if self._running:
            return

        self._running = True
        self.last_sent_yaw = self.protocol.yaw
        self.last_sent_pitch = self.protocol.pitch
        self._physics_task = asyncio.create_task(self._physics_loop())

    def stop(self) -> None:
        """Stop the physics loop"""
        self._running = False
        if self._physics_task:
            self._physics_task.cancel()
            self._physics_task = None

    # === High-level movement API ===

    async def look(self, yaw: float, pitch: float, force: bool = False) -> None:
        """
        Look at a specific yaw and pitch.

        Args:
            yaw: Yaw in degrees
            pitch: Pitch in degrees
            force: If True, instantly set look (may trigger anticheat)
        """
        # Round to vanilla sensitivity
        sensitivity = 0.15  # 100% sensitivity
        yaw_change = round((yaw - self.protocol.yaw) / sensitivity) * sensitivity
        pitch_change = round((pitch - self.protocol.pitch) / sensitivity) * sensitivity

        if yaw_change == 0 and pitch_change == 0:
            return

        self.protocol.yaw += yaw_change
        self.protocol.pitch += pitch_change

        # Clamp pitch
        self.protocol.pitch = max(-90, min(90, self.protocol.pitch))

        if force:
            self.last_sent_yaw = yaw
            self.last_sent_pitch = pitch

        await self.update_position()

    async def look_at(self, x: float, y: float, z: float) -> None:
        """Look at a specific position in the world"""
        if not self.protocol.position:
            return

        dx = x - self.protocol.position[0]
        dy = y - self.protocol.position[1]
        dz = z - self.protocol.position[2]

        # Calculate yaw (rotation around Y axis)
        yaw = math.degrees(math.atan2(-dx, dz))

        # Calculate pitch (rotation around X axis)
        dist = math.sqrt(dx * dx + dz * dz)
        pitch = math.degrees(math.atan2(-dy, dist))

        await self.look(yaw, pitch)

    async def move_to(self, x: float, z: float, timeout: float = 30.0) -> bool:
        """
        Move to a position (simple straight-line movement).

        Args:
            x: Target X coordinate
            z: Target Z coordinate
            timeout: Maximum time to try

        Returns:
            True if reached destination
        """
        start_time = time.time()
        tolerance = 1.0  # blocks

        self.set_control_state("forward", True)

        try:
            while self._running and (time.time() - start_time) < timeout:
                if not self.protocol.position:
                    await asyncio.sleep(0.1)
                    continue

                # Look at target
                await self.look_at(x, self.protocol.position[1], z)

                # Check distance
                dx = x - self.protocol.position[0]
                dz = z - self.protocol.position[2]
                dist = math.sqrt(dx * dx + dz * dz)

                if dist < tolerance:
                    return True

                await asyncio.sleep(0.05)

            return False
        finally:
            self.set_control_state("forward", False)

    async def jump(self) -> None:
        """Make the bot jump"""
        if self.protocol.on_ground:
            self.set_control_state("jump", True)
            await asyncio.sleep(0.1)
            self.set_control_state("jump", False)


__all__ = [
    "MovementManager",
    "ControlState",
    "LastSentPosition",
    "PlayerAction",
]
