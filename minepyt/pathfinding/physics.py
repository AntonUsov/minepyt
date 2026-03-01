"""
Physics simulation for pathfinding

Based on mineflayer-pathfinder/lib/physics.js

This module simulates player physics to determine:
- Can the bot move in a straight line?
- Can the bot jump/sprint to the next position?
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

if TYPE_CHECKING:
    from ..protocol.connection import MinecraftProtocol
    from .move import Move


@dataclass
class SimulatedState:
    """Simulated player state for physics"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0
    on_ground: bool = True
    in_water: bool = False
    in_lava: bool = False

    # Control states
    forward: bool = False
    back: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False
    sprint: bool = False
    sneak: bool = False

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


class Physics:
    """
    Physics simulation for pathfinding.

    Uses simplified physics to predict movement possibilities.
    """

    # Physics constants
    GRAVITY = 0.08
    JUMP_VELOCITY = 0.42
    WALK_SPEED = 0.1
    SPRINT_SPEED = 0.13
    PLAYER_HEIGHT = 1.8
    PLAYER_WIDTH = 0.6

    def __init__(self, bot: "MinecraftProtocol"):
        self.bot = bot

    def get_state(self) -> SimulatedState:
        """Get current bot state"""
        pos = self.bot.position
        return SimulatedState(
            x=pos[0],
            y=pos[1],
            z=pos[2],
            yaw=getattr(self.bot, "yaw", 0.0),
            pitch=getattr(self.bot, "pitch", 0.0),
            on_ground=getattr(self.bot, "on_ground", True),
            in_water=getattr(self.bot, "in_water", False),
            in_lava=getattr(self.bot, "in_lava", False),
        )

    def simulate_until(
        self,
        goal: Callable[[SimulatedState], bool],
        controller: Callable[[SimulatedState, int], None] = lambda s, t: None,
        ticks: int = 1,
        state: Optional[SimulatedState] = None,
    ) -> SimulatedState:
        """
        Simulate physics until goal is reached or ticks exhausted.

        Args:
            goal: Function that returns True when goal is reached
            controller: Function that sets control states each tick
            ticks: Maximum ticks to simulate
            state: Starting state (uses current bot state if None)

        Returns:
            Final simulated state
        """
        if state is None:
            state = self.get_state()

        for tick in range(ticks):
            # Apply controller
            controller(state, tick)

            # Simplified physics simulation
            self._simulate_tick(state)

            # Check goal
            if goal(state):
                return state

            # Check for lava (failure)
            if state.in_lava:
                return state

        return state

    def _simulate_tick(self, state: SimulatedState) -> None:
        """Simulate one physics tick"""
        # Apply gravity
        if not state.on_ground and not state.in_water:
            state.velocity_y -= self.GRAVITY

        # Apply jump
        if state.jump and state.on_ground:
            state.velocity_y = self.JUMP_VELOCITY
            state.on_ground = False

        # Calculate movement speed
        speed = self.SPRINT_SPEED if state.sprint else self.WALK_SPEED

        # Apply movement based on yaw
        if state.forward:
            state.velocity_x = -math.sin(state.yaw) * speed
            state.velocity_z = -math.cos(state.yaw) * speed
        elif state.back:
            state.velocity_x = math.sin(state.yaw) * speed
            state.velocity_z = math.cos(state.yaw) * speed
        else:
            state.velocity_x *= 0.5
            state.velocity_z *= 0.5

        # Apply strafe
        if state.left:
            state.velocity_x += math.cos(state.yaw) * speed * 0.5
            state.velocity_z -= math.sin(state.yaw) * speed * 0.5
        elif state.right:
            state.velocity_x -= math.cos(state.yaw) * speed * 0.5
            state.velocity_z += math.sin(state.yaw) * speed * 0.5

        # Apply velocity
        state.x += state.velocity_x
        state.y += state.velocity_y
        state.z += state.velocity_z

        # Check ground collision (simplified)
        if state.velocity_y < 0:
            # Would need actual block collision detection here
            # For now, assume ground at integer Y
            if state.y <= math.floor(state.y):
                state.y = math.floor(state.y)
                state.velocity_y = 0
                state.on_ground = True

    def can_straight_line(self, path: List[Move], sprint: bool = False) -> bool:
        """
        Check if bot can move in a straight line to path[0].

        Args:
            path: List of path nodes
            sprint: Whether to simulate sprinting

        Returns:
            True if straight-line movement is possible
        """
        if not path:
            return False

        target = path[0]
        state = self.get_state()

        def reached(s: SimulatedState) -> bool:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            return (dx * dx + dz * dz) <= 0.15 * 0.15 and abs(s.y - target.y) < 0.001

        def controller(s: SimulatedState, tick: int) -> None:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            s.yaw = math.atan2(-dx, -dz)
            s.forward = True
            s.sprint = sprint

        # Try walking
        result = self.simulate_until(reached, controller, 200)
        if reached(result):
            return True

        # Try jumping
        if sprint:
            return self.can_sprint_jump(path, 0)
        else:
            return self.can_walk_jump(path, 0)

    def can_straight_line_between(
        self, n1: Tuple[float, float, float], n2: Tuple[float, float, float]
    ) -> bool:
        """
        Check if bot can move in a straight line between two points.

        Args:
            n1: Starting position
            n2: Target position

        Returns:
            True if straight-line movement is possible
        """
        state = SimulatedState(x=n1[0], y=n1[1], z=n1[2], on_ground=True)

        def reached(s: SimulatedState) -> bool:
            dx = n2[0] - s.x
            dy = n2[1] - s.y
            dz = n2[2] - s.z
            return (dx * dx + dz * dz) <= 0.15 * 0.15 and abs(dy) < 0.001

        def controller(s: SimulatedState, tick: int) -> None:
            dx = n2[0] - s.x
            dz = n2[1] - s.z
            s.yaw = math.atan2(-dx, -dz)
            s.forward = True
            s.sprint = True

        distance = math.sqrt((n2[0] - n1[0]) ** 2 + (n2[1] - n1[1]) ** 2 + (n2[2] - n1[2]) ** 2)

        result = self.simulate_until(reached, controller, int(5 * distance))
        return reached(result)

    def can_sprint_jump(self, path: List[Move], jump_after: int = 0) -> bool:
        """
        Check if bot can reach path[0] with sprint-jumping.

        Args:
            path: List of path nodes
            jump_after: Number of ticks before jumping

        Returns:
            True if sprint-jump is possible
        """
        if not path:
            return False

        target = path[0]
        state = self.get_state()

        def reached(s: SimulatedState) -> bool:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            return abs(dx) <= 0.35 and abs(dz) <= 0.35 and abs(s.y - target.y) < 1

        def controller(s: SimulatedState, tick: int) -> None:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            s.yaw = math.atan2(-dx, -dz)
            s.forward = True
            s.sprint = True
            s.jump = tick >= jump_after

        result = self.simulate_until(reached, controller, 20)
        return reached(result)

    def can_walk_jump(self, path: List[Move], jump_after: int = 0) -> bool:
        """
        Check if bot can reach path[0] with walk-jumping.

        Args:
            path: List of path nodes
            jump_after: Number of ticks before jumping

        Returns:
            True if walk-jump is possible
        """
        if not path:
            return False

        target = path[0]
        state = self.get_state()

        def reached(s: SimulatedState) -> bool:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            return abs(dx) <= 0.35 and abs(dz) <= 0.35 and abs(s.y - target.y) < 1

        def controller(s: SimulatedState, tick: int) -> None:
            dx = target.x + 0.5 - s.x
            dz = target.z + 0.5 - s.z
            s.yaw = math.atan2(-dx, -dz)
            s.forward = True
            s.sprint = False
            s.jump = tick >= jump_after

        result = self.simulate_until(reached, controller, 20)
        return reached(result)


# Need to import dataclass
from dataclasses import dataclass
