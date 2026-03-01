"""
Pathfinding system for Minecraft 1.21.4

This module provides:
- A* pathfinding algorithm
- Movement cost calculation
- Block traversability checks
- Path smoothing and optimization

Port of mineflayer-pathfinder concepts
"""

from __future__ import annotations

import asyncio
import heapq
import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .block_registry import Block


class MovementType(IntEnum):
    """Types of movement between blocks"""

    WALK = 0  # Normal walk
    JUMP = 1  # Jump up 1 block
    FALL = 2  # Fall down 1+ blocks
    CLIMB = 3  # Climb ladder/vine
    SWIM = 4  # Swim through water
    DIAGONAL = 5  # Diagonal movement


@dataclass
class PathNode:
    """A node in the pathfinding graph"""

    x: int
    y: int
    z: int
    g_cost: float = 0.0  # Cost from start
    h_cost: float = 0.0  # Heuristic cost to goal
    f_cost: float = 0.0  # Total cost (g + h)
    parent: Optional["PathNode"] = None
    movement_type: MovementType = MovementType.WALK

    def __lt__(self, other: "PathNode") -> bool:
        return self.f_cost < other.f_cost

    @property
    def position(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.z)

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathNode):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z


@dataclass
class Path:
    """A calculated path from start to goal"""

    nodes: List[PathNode] = field(default_factory=list)
    status: str = "incomplete"  # "complete", "partial", "no_path"
    total_cost: float = 0.0

    @property
    def length(self) -> int:
        return len(self.nodes)

    @property
    def is_complete(self) -> bool:
        return self.status == "complete"

    def get_positions(self) -> List[Tuple[int, int, int]]:
        """Get all positions in the path"""
        return [node.position for node in self.nodes]

    def get_next_node(self, current_pos: Tuple[float, float, float]) -> Optional[PathNode]:
        """Get the next node to move to from current position"""
        if not self.nodes:
            return None

        cx, cy, cz = current_pos
        current_int = (int(cx), int(cy), int(cz))

        for i, node in enumerate(self.nodes):
            if node.position == current_int and i + 1 < len(self.nodes):
                return self.nodes[i + 1]

        # Return first node if not yet on path
        return self.nodes[0]


@dataclass
class PathfinderSettings:
    """Settings for pathfinding"""

    max_distance: int = 64  # Maximum search distance
    max_nodes: int = 50000  # Maximum nodes to explore
    allow_jump: bool = True  # Allow jumping
    allow_fall: bool = True  # Allow falling
    allow_climb: bool = True  # Allow climbing ladders/vines
    allow_swim: bool = True  # Allow swimming
    max_fall_height: int = 3  # Maximum safe fall height
    jump_cost: float = 2.0  # Additional cost for jumping
    climb_cost: float = 2.0  # Additional cost for climbing
    swim_cost: float = 3.0  # Additional cost for swimming
    diagonal_cost: float = 1.414  # Cost multiplier for diagonal movement
    timeout_ms: int = 5000  # Timeout for pathfinding


class Pathfinder:
    """
    A* pathfinding for Minecraft.

    Features:
    - 3D A* algorithm with heuristic
    - Block traversability checks
    - Jump, fall, climb, swim support
    - Path optimization
    """

    # Cardinal and diagonal directions
    CARDINAL_DIRS = [
        (1, 0, 0),  # East
        (-1, 0, 0),  # West
        (0, 0, 1),  # South
        (0, 0, -1),  # North
    ]

    DIAGONAL_DIRS = [
        (1, 0, 1),  # SE
        (1, 0, -1),  # NE
        (-1, 0, 1),  # SW
        (-1, 0, -1),  # NW
    ]

    VERTICAL_DIRS = [
        (0, 1, 0),  # Up (jump)
        (0, -1, 0),  # Down (fall)
    ]

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.settings = PathfinderSettings()
        self._current_path: Optional[Path] = None
        self._is_moving: bool = False
        self._move_task: Optional[asyncio.Task] = None

    def is_block_solid(self, x: int, y: int, z: int) -> bool:
        """Check if a block is solid (can stand on)"""
        try:
            block = self.protocol.block_at(x, y, z)
            if block is None:
                return False
            from ..block_registry import is_solid

            return is_solid(block)
        except Exception:
            return False

    def is_block_passable(self, x: int, y: int, z: int) -> bool:
        """Check if a block can be walked through"""
        try:
            block = self.protocol.block_at(x, y, z)
            if block is None:
                return True
            from ..block_registry import is_air, is_transparent

            return is_air(block) or is_transparent(block)
        except Exception:
            return True

    def is_block_climbable(self, x: int, y: int, z: int) -> bool:
        """Check if a block is climbable (ladder, vine, etc.)"""
        try:
            block = self.protocol.block_at(x, y, z)
            if block is None:
                return False
            return block.name in (
                "ladder",
                "vine",
                "scaffolding",
                "weeping_vines",
                "twisting_vines",
            )
        except Exception:
            return False

    def is_block_water(self, x: int, y: int, z: int) -> bool:
        """Check if a block is water"""
        try:
            block = self.protocol.block_at(x, y, z)
            if block is None:
                return False
            return "water" in block.name
        except Exception:
            return False

    def can_stand_at(self, x: int, y: int, z: int) -> bool:
        """Check if an entity can stand at a position"""
        # Need solid ground
        if not self.is_block_solid(x, y - 1, z):
            # Can also stand on climbable blocks
            if not self.is_block_climbable(x, y - 1, z):
                return False

        # Need space for body (2 blocks)
        if not self.is_block_passable(x, y, z):
            return False
        if not self.is_block_passable(x, y + 1, z):
            return False

        return True

    def can_walk_from_to(
        self, from_pos: Tuple[int, int, int], to_pos: Tuple[int, int, int]
    ) -> Tuple[bool, MovementType, float]:
        """
        Check if we can walk from one position to another.

        Returns:
            (can_move, movement_type, cost)
        """
        fx, fy, fz = from_pos
        tx, ty, tz = to_pos

        dx = tx - fx
        dy = ty - fy
        dz = tz - fz

        # Same position
        if dx == 0 and dy == 0 and dz == 0:
            return False, MovementType.WALK, 0

        # Calculate horizontal distance
        horizontal_dist = math.sqrt(dx * dx + dz * dz)

        # Vertical movement
        if dy > 0:
            # Jumping up
            if dy > 1:
                return False, MovementType.JUMP, 0  # Can't jump more than 1 block
            if not self.settings.allow_jump:
                return False, MovementType.JUMP, 0
            if not self.can_stand_at(tx, ty, tz):
                return False, MovementType.JUMP, 0
            cost = horizontal_dist + self.settings.jump_cost
            return True, MovementType.JUMP, cost

        elif dy < 0:
            # Falling down
            fall_height = -dy
            if fall_height > self.settings.max_fall_height:
                return False, MovementType.FALL, 0
            if not self.settings.allow_fall:
                return False, MovementType.FALL, 0
            if not self.can_stand_at(tx, ty, tz):
                return False, MovementType.FALL, 0
            cost = horizontal_dist + fall_height * 0.5  # Falling is cheap
            return True, MovementType.FALL, cost

        else:
            # Same level
            if not self.can_stand_at(tx, ty, tz):
                # Check for climbing
                if self.settings.allow_climb and self.is_block_climbable(tx, ty, tz):
                    return True, MovementType.CLIMB, self.settings.climb_cost
                # Check for swimming
                if self.settings.allow_swim and self.is_block_water(tx, ty, tz):
                    return True, MovementType.SWIM, self.settings.swim_cost
                return False, MovementType.WALK, 0

            # Diagonal movement
            if horizontal_dist > 1:
                # Check corner cutting
                if not self.is_block_passable(fx + dx, fy, fz) or not self.is_block_passable(
                    fx, fy, fz + dz
                ):
                    return False, MovementType.WALK, 0
                return True, MovementType.DIAGONAL, horizontal_dist * self.settings.diagonal_cost

            return True, MovementType.WALK, horizontal_dist

    def heuristic(self, pos: Tuple[int, int, int], goal: Tuple[int, int, int]) -> float:
        """Calculate heuristic cost (3D Euclidean distance)"""
        dx = abs(pos[0] - goal[0])
        dy = abs(pos[1] - goal[1])
        dz = abs(pos[2] - goal[2])
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def get_neighbors(
        self, node: PathNode
    ) -> List[Tuple[Tuple[int, int, int], MovementType, float]]:
        """Get all valid neighboring positions"""
        neighbors = []
        x, y, z = node.x, node.y, node.z

        # Cardinal directions
        for dx, dy, dz in self.CARDINAL_DIRS:
            new_pos = (x + dx, y + dy, z + dz)
            can_move, move_type, cost = self.can_walk_from_to((x, y, z), new_pos)
            if can_move:
                neighbors.append((new_pos, move_type, cost))

        # Diagonal directions
        for dx, dy, dz in self.DIAGONAL_DIRS:
            new_pos = (x + dx, y + dy, z + dz)
            can_move, move_type, cost = self.can_walk_from_to((x, y, z), new_pos)
            if can_move:
                neighbors.append((new_pos, move_type, cost))

        # Jump up
        if self.settings.allow_jump:
            for dx, dz in [(d[0], d[2]) for d in self.CARDINAL_DIRS]:
                new_pos = (x + dx, y + 1, z + dz)
                can_move, move_type, cost = self.can_walk_from_to((x, y, z), new_pos)
                if can_move:
                    neighbors.append((new_pos, move_type, cost))

        # Fall down
        if self.settings.allow_fall:
            for dx, dz in [(d[0], d[2]) for d in self.CARDINAL_DIRS]:
                for fall in range(1, self.settings.max_fall_height + 1):
                    new_pos = (x + dx, y - fall, z + dz)
                    can_move, move_type, cost = self.can_walk_from_to((x, y, z), new_pos)
                    if can_move:
                        neighbors.append((new_pos, move_type, cost))
                        break  # Can only fall to first valid landing

        return neighbors

    def find_path(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        settings: Optional[PathfinderSettings] = None,
    ) -> Path:
        """
        Find a path from start to goal using A*.

        Args:
            start: Starting position (can be float)
            goal: Goal position (can be float)
            settings: Optional pathfinder settings override

        Returns:
            Path object with nodes and status
        """
        if settings:
            self.settings = settings

        # Convert to int positions
        start_int = (int(start[0]), int(start[1]), int(start[2]))
        goal_int = (int(goal[0]), int(goal[1]), int(goal[2]))

        # Check if goal is reachable
        if not self.can_stand_at(*goal_int):
            # Try to find a nearby reachable position
            for dy in range(-2, 3):
                for dx in range(-1, 2):
                    for dz in range(-1, 2):
                        if self.can_stand_at(goal_int[0] + dx, goal_int[1] + dy, goal_int[2] + dz):
                            goal_int = (goal_int[0] + dx, goal_int[1] + dy, goal_int[2] + dz)
                            break

        # Initialize
        start_node = PathNode(
            x=start_int[0],
            y=start_int[1],
            z=start_int[2],
            g_cost=0,
            h_cost=self.heuristic(start_int, goal_int),
        )
        start_node.f_cost = start_node.h_cost

        open_set: List[PathNode] = [start_node]
        closed_set: Set[Tuple[int, int, int]] = set()
        all_nodes: Dict[Tuple[int, int, int], PathNode] = {start_int: start_node}

        nodes_explored = 0

        while open_set and nodes_explored < self.settings.max_nodes:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)

            # Check if we reached the goal
            if current.position == goal_int:
                return self._reconstruct_path(current)

            # Skip if already processed
            if current.position in closed_set:
                continue

            closed_set.add(current.position)
            nodes_explored += 1

            # Check distance limit
            if self.heuristic(current.position, goal_int) > self.settings.max_distance:
                continue

            # Explore neighbors
            for neighbor_pos, move_type, move_cost in self.get_neighbors(current):
                if neighbor_pos in closed_set:
                    continue

                g_cost = current.g_cost + move_cost
                h_cost = self.heuristic(neighbor_pos, goal_int)
                f_cost = g_cost + h_cost

                # Check if this path is better
                if neighbor_pos in all_nodes:
                    existing = all_nodes[neighbor_pos]
                    if g_cost < existing.g_cost:
                        existing.g_cost = g_cost
                        existing.h_cost = h_cost
                        existing.f_cost = f_cost
                        existing.parent = current
                        existing.movement_type = move_type
                        heapq.heapify(open_set)  # Re-heapify
                else:
                    neighbor = PathNode(
                        x=neighbor_pos[0],
                        y=neighbor_pos[1],
                        z=neighbor_pos[2],
                        g_cost=g_cost,
                        h_cost=h_cost,
                        f_cost=f_cost,
                        parent=current,
                        movement_type=move_type,
                    )
                    all_nodes[neighbor_pos] = neighbor
                    heapq.heappush(open_set, neighbor)

        # No path found - return partial path if possible
        if all_nodes:
            closest = min(all_nodes.values(), key=lambda n: n.h_cost)
            if closest.h_cost < start_node.h_cost:
                partial_path = self._reconstruct_path(closest)
                partial_path.status = "partial"
                return partial_path

        return Path(status="no_path")

    def _reconstruct_path(self, end_node: PathNode) -> Path:
        """Reconstruct path from end node to start"""
        nodes = []
        current: Optional[PathNode] = end_node
        total_cost = 0.0

        while current is not None:
            nodes.append(current)
            total_cost += current.g_cost
            current = current.parent

        nodes.reverse()

        return Path(nodes=nodes, status="complete", total_cost=total_cost)

    async def goto(
        self, goal: Tuple[float, float, float], settings: Optional[PathfinderSettings] = None
    ) -> bool:
        """
        Move to a goal position using pathfinding.

        Args:
            goal: Target position
            settings: Optional pathfinder settings

        Returns:
            True if reached goal, False if failed
        """
        if settings:
            self.settings = settings

        # Find path
        path = self.find_path(self.protocol.position, goal, settings)

        if not path.is_complete:
            print(f"[PATHFINDER] No complete path found. Status: {path.status}")
            return False

        print(f"[PATHFINDER] Path found with {path.length} nodes")

        # Follow path
        self._is_moving = True
        self._current_path = path

        try:
            for i, node in enumerate(path.nodes):
                if not self._is_moving:
                    return False

                # Move to node
                target = (node.x + 0.5, node.y, node.z + 0.5)  # Center of block

                # Use movement manager
                if hasattr(self.protocol, "_movement") and self.protocol._movement:
                    await self.protocol._movement.move_to(target, timeout=5.0)
                else:
                    # Fallback: direct position setting (not recommended)
                    await asyncio.sleep(0.1)

                # Check if we're close enough
                dx = abs(self.protocol.position[0] - target[0])
                dz = abs(self.protocol.position[2] - target[2])

                if dx > 1.5 or dz > 1.5:
                    # Recalculate path
                    print(f"[PATHFINDER] Off path, recalculating...")
                    path = self.find_path(self.protocol.position, goal, settings)
                    if not path.is_complete:
                        return False

            return True

        except asyncio.CancelledError:
            return False
        finally:
            self._is_moving = False
            self._current_path = None

    def stop(self) -> None:
        """Stop current movement"""
        self._is_moving = False
        if self._move_task:
            self._move_task.cancel()
            self._move_task = None


class PathfinderManager:
    """
    High-level pathfinding manager that integrates with MinecraftProtocol.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.pathfinder = Pathfinder(protocol)
        self.settings = PathfinderSettings()

    async def goto(self, x: float, y: float, z: float, max_distance: int = 64) -> bool:
        """
        Navigate to a position.

        Args:
            x, y, z: Target coordinates
            max_distance: Maximum pathfinding distance

        Returns:
            True if reached, False if failed
        """
        self.settings.max_distance = max_distance
        return await self.pathfinder.goto((x, y, z), self.settings)

    async def goto_block(self, block: "Block", max_distance: int = 64) -> bool:
        """Navigate to a block"""
        pos = block.position
        return await self.goto(pos[0], pos[1], pos[2], max_distance)

    async def goto_entity(self, entity, max_distance: int = 64) -> bool:
        """Navigate to an entity"""
        pos = entity.position
        return await self.goto(pos[0], pos[1], pos[2], max_distance)

    def find_path(self, goal: Tuple[float, float, float]) -> Path:
        """Find a path without moving"""
        return self.pathfinder.find_path(self.protocol.position, goal, self.settings)

    def stop(self) -> None:
        """Stop current navigation"""
        self.pathfinder.stop()

    def set_settings(
        self,
        allow_jump: bool = True,
        allow_fall: bool = True,
        allow_climb: bool = True,
        allow_swim: bool = True,
        max_fall_height: int = 3,
    ) -> None:
        """Update pathfinder settings"""
        self.settings.allow_jump = allow_jump
        self.settings.allow_fall = allow_fall
        self.settings.allow_climb = allow_climb
        self.settings.allow_swim = allow_swim
        self.settings.max_fall_height = max_fall_height


__all__ = [
    "Pathfinder",
    "PathfinderManager",
    "PathfinderSettings",
    "Path",
    "PathNode",
    "MovementType",
]
