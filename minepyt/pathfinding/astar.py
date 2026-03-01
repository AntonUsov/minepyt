"""
A* pathfinding algorithm

Based on mineflayer-pathfinder/lib/astar.js

Features:
- Tick-based computation (doesn't block event loop)
- Timeout support
- Partial path support
- Search radius limiting
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set

if TYPE_CHECKING:
    from .goals import Goal
    from .movements import Movements

from .heap import BinaryHeap
from .move import Move


@dataclass
class PathNode:
    """Internal node for A* algorithm"""

    data: Move
    g: float = 0.0  # Cost from start
    h: float = 0.0  # Heuristic to goal
    f: float = 0.0  # Total cost (g + h)
    parent: Optional["PathNode"] = None

    def __lt__(self, other: "PathNode") -> bool:
        return self.f < other.f


@dataclass
class PathResult:
    """Result of pathfinding computation"""

    status: str  # 'success', 'partial', 'timeout', 'noPath'
    cost: float = 0.0
    time: float = 0.0  # milliseconds
    visited_nodes: int = 0
    generated_nodes: int = 0
    path: List[Move] = field(default_factory=list)
    context: Optional["AStar"] = None


def reconstruct_path(node: PathNode) -> List[Move]:
    """Reconstruct path from end node to start"""
    path = []
    current: Optional[PathNode] = node

    while current is not None:
        path.append(current.data)
        current = current.parent

    path.reverse()
    return path


class AStar:
    """
    A* pathfinding algorithm with tick-based computation.

    This allows pathfinding to be spread across multiple ticks,
    preventing the event loop from being blocked.
    """

    def __init__(
        self,
        start: Move,
        movements: "Movements",
        goal: "Goal",
        timeout: float = 5000,
        tick_timeout: float = 40,
        search_radius: int = -1,
    ):
        """
        Initialize A* pathfinding.

        Args:
            start: Starting position
            movements: Movements configuration
            goal: Goal to reach
            timeout: Maximum total time in ms
            tick_timeout: Maximum time per tick in ms
            search_radius: Maximum search distance (-1 for unlimited)
        """
        self.start_time = time.time() * 1000

        self.movements = movements
        self.goal = goal
        self.timeout = timeout
        self.tick_timeout = tick_timeout

        # Open and closed sets
        self.closed_data_set: Set[str] = set()
        self.open_heap = BinaryHeap[PathNode]()
        self.open_data_map: Dict[str, PathNode] = {}

        # Create start node
        start_node = PathNode(data=start, g=0, h=goal.heuristic(start))
        start_node.f = start_node.g + start_node.h

        self.open_heap.push(start_node)
        self.open_data_map[start.hash] = start_node
        self.best_node = start_node

        # Search radius
        self.max_cost = -1 if search_radius < 0 else start_node.h + search_radius

        # Track visited chunks for chunk loading detection
        self.visited_chunks: Set[str] = set()

    def make_result(self, status: str, node: PathNode) -> PathResult:
        """Create a path result"""
        return PathResult(
            status=status,
            cost=node.g,
            time=time.time() * 1000 - self.start_time,
            visited_nodes=len(self.closed_data_set),
            generated_nodes=len(self.closed_data_set) + self.open_heap.size(),
            path=reconstruct_path(node),
            context=self,
        )

    def compute(self) -> PathResult:
        """
        Compute path for one tick.

        Returns:
            PathResult with status:
            - 'success': Path found
            - 'partial': Partial path found, more computation needed
            - 'timeout': Time limit reached
            - 'noPath': No path exists
        """
        compute_start_time = time.time() * 1000

        while not self.open_heap.is_empty():
            # Check tick timeout
            if time.time() * 1000 - compute_start_time > self.tick_timeout:
                return self.make_result("partial", self.best_node)

            # Check total timeout
            if time.time() * 1000 - self.start_time > self.timeout:
                return self.make_result("timeout", self.best_node)

            # Get next node
            node = self.open_heap.pop()

            # Check if goal reached
            if self.goal.is_end(node.data):
                return self.make_result("success", node)

            # Move to closed set
            self.open_data_map.pop(node.data.hash, None)
            self.closed_data_set.add(node.data.hash)

            # Track visited chunk
            chunk_key = f"{node.data.x >> 4},{node.data.z >> 4}"
            self.visited_chunks.add(chunk_key)

            # Get neighbors
            neighbors = self.movements.get_neighbors(node.data)

            for neighbor_data in neighbors:
                # Skip closed nodes
                if neighbor_data.hash in self.closed_data_set:
                    continue

                # Calculate cost from this node
                g_from_this = node.g + neighbor_data.cost

                # Check search radius
                heuristic = self.goal.heuristic(neighbor_data)
                if self.max_cost > 0 and g_from_this + heuristic > self.max_cost:
                    continue

                # Check if already in open set
                neighbor_node = self.open_data_map.get(neighbor_data.hash)
                update = False

                if neighbor_node is None:
                    # New node
                    neighbor_node = PathNode()
                    self.open_data_map[neighbor_data.hash] = neighbor_node
                else:
                    # Existing node
                    if neighbor_node.g < g_from_this:
                        # This path is worse, skip
                        continue
                    update = True

                # Update node
                neighbor_node.data = neighbor_data
                neighbor_node.g = g_from_this
                neighbor_node.h = heuristic
                neighbor_node.f = g_from_this + heuristic
                neighbor_node.parent = node

                # Track best node
                if neighbor_node.h < self.best_node.h:
                    self.best_node = neighbor_node

                # Add to heap
                if update:
                    self.open_heap.update(neighbor_node)
                else:
                    self.open_heap.push(neighbor_node)

        # No path found
        return self.make_result("noPath", self.best_node)


class AStarIterable:
    """
    Generator-based A* that can be iterated for partial results.

    Usage:
        astar = AStarIterable(start, movements, goal)
        for result in astar:
            if result.status == 'success':
                # Path found
                break
            elif result.status == 'partial':
                # More computation needed
                continue
            else:
                # Failed
                break
    """

    def __init__(
        self,
        start: Move,
        movements: "Movements",
        goal: "Goal",
        timeout: float = 5000,
        tick_timeout: float = 40,
        search_radius: int = -1,
    ):
        self.astar = AStar(start, movements, goal, timeout, tick_timeout, search_radius)
        self.done = False

    def __iter__(self):
        return self

    def __next__(self) -> PathResult:
        if self.done:
            raise StopIteration

        result = self.astar.compute()

        if result.status in ("success", "timeout", "noPath"):
            self.done = True

        return result

    def compute_all(self) -> PathResult:
        """Compute until done and return final result"""
        result = None
        for result in self:
            pass
        return result
