"""
Vehicle system for Minecraft 1.21.4

This module provides:
- Entity mounting/dismounting
- Vehicle control (boats, minecarts, horses)
- Vehicle state tracking

Based on mineflayer vehicle concepts
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .entities import Entity


class VehicleType(IntEnum):
    """Types of rideable entities"""

    BOAT = 0
    MINECART = 1
    HORSE = 2
    DONKEY = 3
    MULE = 4
    PIG = 5
    STRIDER = 6
    CAMEL = 7
    OTHER = 99


@dataclass
class VehicleState:
    """State of a vehicle"""

    entity_id: int
    vehicle_type: VehicleType
    is_mounted: bool = False
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    yaw: float = 0.0
    pitch: float = 0.0
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class BoatControl:
    """Control state for boats"""

    forward: bool = False
    backward: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False  # Used for some vehicles


@dataclass
class HorseControl:
    """Control state for horses"""

    forward: bool = False
    backward: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False
    sprint: bool = False


class VehicleManager:
    """
    Manages vehicle interactions.

    Features:
    - Mount/dismount entities
    - Vehicle control
    - Vehicle state tracking
    """

    # Entity types that are rideable
    RIDEABLE_TYPES = {
        "boat": VehicleType.BOAT,
        "oak_boat": VehicleType.BOAT,
        "spruce_boat": VehicleType.BOAT,
        "birch_boat": VehicleType.BOAT,
        "jungle_boat": VehicleType.BOAT,
        "acacia_boat": VehicleType.BOAT,
        "dark_oak_boat": VehicleType.BOAT,
        "mangrove_boat": VehicleType.BOAT,
        "cherry_boat": VehicleType.BOAT,
        "bamboo_raft": VehicleType.BOAT,
        "minecart": VehicleType.MINECART,
        "chest_minecart": VehicleType.MINECART,
        "furnace_minecart": VehicleType.MINECART,
        "hopper_minecart": VehicleType.MINECART,
        "tnt_minecart": VehicleType.MINECART,
        "rail": VehicleType.MINECART,
        "command_block_minecart": VehicleType.MINECART,
        "spawner_minecart": VehicleType.MINECART,
        "horse": VehicleType.HORSE,
        "donkey": VehicleType.DONKEY,
        "mule": VehicleType.MULE,
        "pig": VehicleType.PIG,
        "strider": VehicleType.STRIDER,
        "camel": VehicleType.CAMEL,
    }

    # Entity action packet values for 1.21.4
    # Entity Action packet (0x1B serverbound)
    ACTION_START_SNEAKING = 0
    ACTION_STOP_SNEAKING = 1
    ACTION_LEAVE_BED = 2
    ACTION_START_SPRINTING = 3
    ACTION_STOP_SPRINTING = 4
    ACTION_START_JUMP_HORSE = 5
    ACTION_STOP_JUMP_HORSE = 6
    ACTION_OPEN_HORSE_INVENTORY = 7
    ACTION_START_FLYING_ELYTRA = 8

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self._current_vehicle: Optional[VehicleState] = None
        self._boat_control: BoatControl = BoatControl()
        self._horse_control: HorseControl = HorseControl()
        self._vehicle_entities: Dict[int, VehicleState] = {}
        self._control_task: Optional[asyncio.Task] = None
        self._is_controlling: bool = False

    @property
    def is_riding(self) -> bool:
        """Check if bot is currently riding a vehicle"""
        return self._current_vehicle is not None and self._current_vehicle.is_mounted

    @property
    def current_vehicle(self) -> Optional[VehicleState]:
        """Get the current vehicle state"""
        return self._current_vehicle

    def get_vehicle_type(self, entity: "Entity") -> VehicleType:
        """Determine the vehicle type from an entity"""
        entity_name = getattr(entity, "name", "").lower()

        for name, vtype in self.RIDEABLE_TYPES.items():
            if name in entity_name:
                return vtype

        return VehicleType.OTHER

    def is_rideable(self, entity: "Entity") -> bool:
        """Check if an entity can be ridden"""
        return self.get_vehicle_type(entity) != VehicleType.OTHER

    async def mount(self, entity: "Entity") -> bool:
        """
        Mount (ride) an entity.

        Args:
            entity: Entity to mount

        Returns:
            True if successfully mounted
        """
        if self.is_riding:
            print("[VEHICLE] Already riding a vehicle")
            return False

        if not self.is_rideable(entity):
            print(f"[VEHICLE] Entity {entity.name} is not rideable")
            return False

        # Interact with entity to mount
        # Serverbound Interact Entity packet (0x10 for 1.21.4)
        from mcproto.buffer import Buffer

        buf = Buffer()
        buf.write_varint(entity.entity_id)  # Entity ID
        buf.write_varint(0)  # Action: INTERACT (0)
        buf.write_value(">f", 0.0)  # Target X (not used for interact)
        buf.write_value(">f", 0.0)  # Target Y (not used for interact)
        buf.write_value(">f", 0.0)  # Target Z (not used for interact)
        buf.write_bool(False)  # Hand not used for mount

        await self.protocol._write_packet(0x10, bytes(buf))

        # Wait for mount confirmation
        await asyncio.sleep(0.5)

        # Create vehicle state
        vehicle_type = self.get_vehicle_type(entity)
        position = getattr(entity, "position", (0.0, 0.0, 0.0))

        self._current_vehicle = VehicleState(
            entity_id=entity.entity_id,
            vehicle_type=vehicle_type,
            is_mounted=True,
            position=position,
        )

        print(f"[VEHICLE] Mounted {entity.name} (type: {vehicle_type.name})")
        return True

    async def dismount(self) -> bool:
        """
        Dismount from current vehicle.

        Returns:
            True if successfully dismounted
        """
        if not self.is_riding:
            print("[VEHICLE] Not riding any vehicle")
            return False

        # Stop any control loop
        self._is_controlling = False
        if self._control_task:
            self._control_task.cancel()
            try:
                await self._control_task
            except asyncio.CancelledError:
                pass
            self._control_task = None

        # Send sneak to dismount
        from mcproto.buffer import Buffer

        # Start sneaking
        buf = Buffer()
        buf.write_varint(self.protocol.entity_id)  # Player entity ID
        buf.write_varint(self.ACTION_START_SNEAKING)  # Action
        buf.write_varint(0)  # Jump boost (not used)
        await self.protocol._write_packet(0x1B, bytes(buf))

        await asyncio.sleep(0.1)

        # Stop sneaking
        buf = Buffer()
        buf.write_varint(self.protocol.entity_id)
        buf.write_varint(self.ACTION_STOP_SNEAKING)
        buf.write_varint(0)
        await self.protocol._write_packet(0x1B, bytes(buf))

        self._current_vehicle = None
        print("[VEHICLE] Dismounted")
        return True

    async def send_vehicle_input(
        self, forward: float = 0.0, sideways: float = 0.0, jump: bool = False
    ) -> None:
        """
        Send vehicle input packet (0x1C for 1.21.4).

        Args:
            forward: Forward movement (-1 to 1)
            sideways: Sideways movement (-1 to 1)
            jump: Whether jumping
        """
        from mcproto.buffer import Buffer

        flags = 0
        if jump:
            flags |= 0x01

        buf = Buffer()
        buf.write_value(">f", sideways)  # Sideways
        buf.write_value(">f", forward)  # Forward
        buf.write_bool(jump)  # Jump flag

        await self.protocol._write_packet(0x1C, bytes(buf))

    async def move_boat(
        self, forward: bool = False, backward: bool = False, left: bool = False, right: bool = False
    ) -> None:
        """
        Control boat movement.

        Args:
            forward: Move forward
            backward: Move backward
            left: Turn left
            right: Turn right
        """
        if not self.is_riding:
            return

        if self._current_vehicle.vehicle_type != VehicleType.BOAT:
            print("[VEHICLE] Current vehicle is not a boat")
            return

        # Calculate input values
        forward_val = 1.0 if forward else (-1.0 if backward else 0.0)
        sideways_val = 1.0 if left else (-1.0 if right else 0.0)

        await self.send_vehicle_input(forward_val, sideways_val)

    async def move_horse(
        self,
        forward: bool = False,
        backward: bool = False,
        left: bool = False,
        right: bool = False,
        jump: bool = False,
        sprint: bool = False,
    ) -> None:
        """
        Control horse movement.

        Args:
            forward: Move forward
            backward: Move backward
            left: Turn left
            right: Turn right
            jump: Jump (if horse has jump charge)
            sprint: Sprint/Gallop
        """
        if not self.is_riding:
            return

        if self._current_vehicle.vehicle_type not in (
            VehicleType.HORSE,
            VehicleType.DONKEY,
            VehicleType.MULE,
        ):
            print("[VEHICLE] Current vehicle is not a horse/donkey/mule")
            return

        # Calculate input values
        forward_val = 1.0 if forward else (-1.0 if backward else 0.0)
        sideways_val = 1.0 if left else (-1.0 if right else 0.0)

        await self.send_vehicle_input(forward_val, sideways_val, jump)

        # Send sprint action if needed
        if sprint and forward:
            from mcproto.buffer import Buffer

            buf = Buffer()
            buf.write_varint(self.protocol.entity_id)
            buf.write_varint(self.ACTION_START_SPRINTING)
            buf.write_varint(0)
            await self.protocol._write_packet(0x1B, bytes(buf))

    async def horse_jump(self, power: float = 1.0) -> None:
        """
        Make the horse jump with specified power.

        Args:
            power: Jump power (0.0 to 1.0)
        """
        if not self.is_riding:
            return

        # Start horse jump
        from mcproto.buffer import Buffer

        buf = Buffer()
        buf.write_varint(self.protocol.entity_id)
        buf.write_varint(self.ACTION_START_JUMP_HORSE)
        buf.write_varint(int(power * 100))  # Jump boost (0-100)
        await self.protocol._write_packet(0x1B, bytes(buf))

    async def open_horse_inventory(self) -> None:
        """Open the horse's inventory (if it has one)"""
        if not self.is_riding:
            return

        if self._current_vehicle.vehicle_type not in (
            VehicleType.HORSE,
            VehicleType.DONKEY,
            VehicleType.MULE,
        ):
            print("[VEHICLE] Current vehicle doesn't have inventory")
            return

        from mcproto.buffer import Buffer

        buf = Buffer()
        buf.write_varint(self.protocol.entity_id)
        buf.write_varint(self.ACTION_OPEN_HORSE_INVENTORY)
        buf.write_varint(0)
        await self.protocol._write_packet(0x1B, bytes(buf))

    async def steer_minecart(self, forward: bool = False, backward: bool = False) -> None:
        """
        Control minecart movement (powered minecart).

        Args:
            forward: Move forward
            backward: Move backward
        """
        if not self.is_riding:
            return

        if self._current_vehicle.vehicle_type != VehicleType.MINECART:
            print("[VEHICLE] Current vehicle is not a minecart")
            return

        # Minecarts on rails don't need steering, but furnace minecarts do
        forward_val = 1.0 if forward else (-1.0 if backward else 0.0)
        await self.send_vehicle_input(forward_val, 0.0)

    async def control_loop(self, interval: float = 0.05) -> None:
        """
        Run continuous vehicle control loop.

        Args:
            interval: Control update interval in seconds
        """
        self._is_controlling = True

        while self._is_controlling and self.is_riding:
            if self._current_vehicle.vehicle_type == VehicleType.BOAT:
                # Apply boat control
                await self.move_boat(
                    forward=self._boat_control.forward,
                    backward=self._boat_control.backward,
                    left=self._boat_control.left,
                    right=self._boat_control.right,
                )
            elif self._current_vehicle.vehicle_type in (
                VehicleType.HORSE,
                VehicleType.DONKEY,
                VehicleType.MULE,
            ):
                # Apply horse control
                await self.move_horse(
                    forward=self._horse_control.forward,
                    backward=self._horse_control.backward,
                    left=self._horse_control.left,
                    right=self._horse_control.right,
                    jump=self._horse_control.jump,
                    sprint=self._horse_control.sprint,
                )

            await asyncio.sleep(interval)

    def start_control(self) -> None:
        """Start the vehicle control loop"""
        if self._control_task is None or self._control_task.done():
            self._control_task = asyncio.create_task(self.control_loop())

    def stop_control(self) -> None:
        """Stop the vehicle control loop"""
        self._is_controlling = False
        if self._control_task:
            self._control_task.cancel()
            self._control_task = None

    def set_boat_control(
        self, forward: bool = False, backward: bool = False, left: bool = False, right: bool = False
    ) -> None:
        """Set boat control state"""
        self._boat_control.forward = forward
        self._boat_control.backward = backward
        self._boat_control.left = left
        self._boat_control.right = right

    def set_horse_control(
        self,
        forward: bool = False,
        backward: bool = False,
        left: bool = False,
        right: bool = False,
        jump: bool = False,
        sprint: bool = False,
    ) -> None:
        """Set horse control state"""
        self._horse_control.forward = forward
        self._horse_control.backward = backward
        self._horse_control.left = left
        self._horse_control.right = right
        self._horse_control.jump = jump
        self._horse_control.sprint = sprint

    def on_vehicle_move(
        self, entity_id: int, x: float, y: float, z: float, yaw: float, pitch: float
    ) -> None:
        """Handle vehicle movement update"""
        if self._current_vehicle and self._current_vehicle.entity_id == entity_id:
            self._current_vehicle.position = (x, y, z)
            self._current_vehicle.yaw = yaw
            self._current_vehicle.pitch = pitch
            self.protocol.emit("vehicleMove", self._current_vehicle)


__all__ = [
    "VehicleManager",
    "VehicleType",
    "VehicleState",
    "BoatControl",
    "HorseControl",
]
