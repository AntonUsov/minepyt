"""
Main Pathfinder class - integrates all pathfinding components

Based on mineflayer-pathfinder/index.js

This module provides:
- Goal management
- Path computation and monitoring
- Block breaking/placing during path
- Movement execution
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from ..protocol.connection import MinecraftProtocol
    from ..block_registry import Block
    from ..entities import Entity

from .astar import AStar, PathResult, AStarIterable
from .goals import Goal, GoalBlock
from .movements import Movements
from .move import Move
from .physics import Physics


class Pathfinder:
    """
    Main pathfinding controller for Minecraft bot.

    This class manages:
    - Current goal and movements configuration
    - Path computation using A*
    - Path execution and monitoring
    - Block breaking and placing during movement

    Usage:
        bot.pathfinder.setGoal(GoalBlock(100, 64, 200))
        bot.pathfinder.goto(GoalBlock(100, 64, 200))  # async
    """

    def __init__(self, bot: "MinecraftProtocol"):
        self.bot = bot

        # Configuration
        self.think_timeout: int = 5000  # ms - max total computation time
        self.tick_timeout: int = 40  # ms - max computation per tick
        self.search_radius: int = -1  # blocks - search limit (-1 = unlimited)
        self.enable_path_shortcut: bool = False
        self.los_when_placing_blocks: bool = True

        # State
        self._movements: Optional[Movements] = None
        self._goal: Optional[Goal] = None
        self._dynamic_goal: bool = False
        self._path: List[Move] = []
        self._path_updated: bool = False

        # Current action state
        self._digging: bool = False
        self._placing: bool = False
        self._placing_block: Optional[dict] = None
        self._last_node_time: float = time.time() * 1000
        self._returning_pos: Optional[Tuple[int, int, int]] = None
        self._stop_pathing: bool = False

        # Physics
        self._physics = Physics(bot)

        # A* context
        self._astar_context: Optional[AStar] = None
        self._astar_timed_out: bool = False

        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}

        # Initialize default movements
        self._init_movements()

    def _init_movements(self) -> None:
        """Initialize default movements configuration"""
        self._movements = Movements(self.bot)

    # === Properties ===

    @property
    def goal(self) -> Optional[Goal]:
        """Current goal"""
        return self._goal

    @property
    def movements(self) -> Movements:
        """Current movements configuration"""
        return self._movements

    # === Events ===

    def on(self, event: str, handler: Callable) -> None:
        """Register event handler"""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        """Register one-time event handler"""

        def wrapper(*args, **kwargs):
            if handler in self._handlers.get(event, []):
                self._handlers[event].remove(wrapper)
            return handler(*args, **kwargs)

        self.on(event, wrapper)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to handlers"""
        for handler in self._handlers.get(event, [])[:]:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in handler for {event}: {e}")

    # === Goal Management ===

    def set_goal(self, goal: Goal, dynamic: bool = False) -> None:
        """
        Set the pathfinding goal.

        Args:
            goal: Goal to reach
            dynamic: If True, goal can change (e.g., following entity)
        """
        self._goal = goal
        self._dynamic_goal = dynamic
        self.emit("goal_updated", goal, dynamic)
        self._reset_path("goal_updated")

    def set_movements(self, movements: Movements) -> None:
        """Set movements configuration"""
        self._movements = movements
        self._reset_path("movements_updated")

    # === Status ===

    def is_moving(self) -> bool:
        """Check if bot is currently moving"""
        return len(self._path) > 0

    def is_mining(self) -> bool:
        """Check if bot is currently mining"""
        return self._digging

    def is_building(self) -> bool:
        """Check if bot is currently placing blocks"""
        return self._placing

    def stop(self) -> None:
        """Stop pathfinding"""
        self._stop_pathing = True

    # === Path Computation ===

    def best_harvest_tool(self, block: "Block") -> Optional[Any]:
        """
        Find the best tool in inventory for harvesting a block.

        Args:
            block: Block to harvest

        Returns:
            Best tool item or None
        """
        try:
            available_tools = list(self.bot.inventory.values())
            effects = getattr(self.bot.entity, "effects", {}) if hasattr(self.bot, "entity") else {}

            fastest = float("inf")
            best_tool = None

            for tool in available_tools:
                if hasattr(block, "dig_time"):
                    # Calculate dig time
                    dig_time = block.dig_time(
                        getattr(tool, "item_id", None), False, False, False, {}, effects
                    )
                    if dig_time < fastest:
                        fastest = dig_time
                        best_tool = tool

            return best_tool
        except Exception:
            return None

    def get_path_to(
        self, movements: Movements, goal: Goal, timeout: Optional[int] = None
    ) -> PathResult:
        """
        Compute path from current position to goal.

        Args:
            movements: Movements configuration
            goal: Target goal
            timeout: Computation timeout (ms)

        Returns:
            PathResult with path and status
        """
        return self.get_path_from_to(movements, self.bot.position, goal, timeout=timeout)

    def get_path_from_to(
        self,
        movements: Movements,
        start_pos: Tuple[float, float, float],
        goal: Goal,
        timeout: Optional[int] = None,
        tick_timeout: Optional[int] = None,
        search_radius: Optional[int] = None,
        optimize_path: bool = True,
        reset_entity_intersects: bool = True,
    ) -> PathResult:
        """
        Compute path from start position to goal.

        Args:
            movements: Movements configuration
            start_pos: Starting position
            goal: Target goal
            timeout: Total computation timeout (ms)
            tick_timeout: Per-tick timeout (ms)
            search_radius: Maximum search distance
            optimize_path: Whether to optimize path
            reset_entity_intersects: Reset entity collision index

        Returns:
            PathResult with path and status
        """
        timeout = timeout or self.think_timeout
        tick_timeout = tick_timeout or self.tick_timeout
        search_radius = search_radius or self.search_radius

        # Create start move
        px, py, pz = int(start_pos[0]), int(start_pos[1]), int(start_pos[2])

        # Check if we need to offset for partial blocks
        block = self.bot.block_at(px, py, pz)
        dy = start_pos[1] - py
        offset = 0
        if block and dy > 0.001 and self.bot.on_ground:
            if block.type not in movements.empty_blocks:
                offset = 1

        start = Move(px, py + offset, pz, movements.count_scaffolding_items())

        # Update entity collisions
        if movements.allow_entity_detection:
            if reset_entity_intersects:
                movements.clear_collision_index()
            movements.update_collision_index()

        # Run A*
        astar = AStar(start, movements, goal, timeout, tick_timeout, search_radius)
        result = astar.compute()

        self._astar_context = astar

        # Optimize path
        if optimize_path and result.path:
            result.path = self._post_process_path(result.path)

        return result

    def _post_process_path(self, path: List[Move]) -> List[Move]:
        """Optimize path for smoother movement"""
        if not path:
            return path

        # Adjust positions for block shapes
        for move in path:
            if move.to_break or move.to_place:
                break

            block = self.bot.block_at(move.x, move.y, move.z)
            if block and hasattr(block, "shapes") and block.shapes:
                # Get top position from shapes
                max_height = move.y
                for shape in block.shapes:
                    if len(shape) >= 6:
                        max_height = max(max_height, move.y + shape[4])
                # Would update move position here if needed

        # Apply path shortcut if enabled
        if not self.enable_path_shortcut:
            return path

        if not self._movements or self._movements.exclusion_areas_step:
            return path

        # Create shortcuts for straight-line movement
        new_path = []
        last_node = self.bot.position

        for i, node in enumerate(path):
            if abs(node.y - last_node[1]) > 0.5:
                new_path.append(path[i - 1] if i > 0 else node)
                last_node = (path[i - 1].x, path[i - 1].y, path[i - 1].z) if i > 0 else last_node
            elif node.to_break or node.to_place:
                new_path.append(path[i - 1] if i > 0 else node)
                last_node = (path[i - 1].x, path[i - 1].y, path[i - 1].z) if i > 0 else last_node
            elif self._physics.can_straight_line_between(last_node, (node.x, node.y, node.z)):
                continue
            else:
                new_path.append(path[i - 1] if i > 0 else node)
                last_node = (path[i - 1].x, path[i - 1].y, path[i - 1].z) if i > 0 else last_node

        if path:
            new_path.append(path[-1])

        return new_path

    # === Path Management ===

    def _reset_path(self, reason: str, clear_states: bool = True) -> None:
        """Reset current path"""
        if not self._stop_pathing and self._path:
            self.emit("path_reset", reason)

        self._path = []

        if self._digging:
            self.bot.stop_digging()
            self._digging = False

        self._placing = False
        self._path_updated = False
        self._astar_context = None
        self._astar_timed_out = False

        if self._movements:
            self._movements.clear_collision_index()

        if clear_states:
            self.bot.clear_control_states()

        if self._stop_pathing:
            self._stop()

    def _stop(self) -> None:
        """Stop pathfinding completely"""
        self._stop_pathing = False
        self._goal = None
        self._path = []
        self.emit("path_stop")
        self._full_stop()

    def _full_stop(self) -> None:
        """Stop all movement and recenter"""
        self.bot.clear_control_states()

        # Force velocity to zero
        if hasattr(self.bot, "entity") and hasattr(self.bot.entity, "velocity"):
            self.bot.entity.velocity = (0, 0, 0)

        # Recenter on block
        pos = self.bot.position
        block_x = int(pos[0]) + 0.5
        block_z = int(pos[2]) + 0.5

        if abs(pos[0] - block_x) > 0.2:
            self.bot.position = (block_x, pos[1], pos[2])
        if abs(pos[2] - block_z) > 0.2:
            self.bot.position = (pos[0], pos[1], block_z)

    # === Async API ===

    async def goto(self, goal: Goal) -> bool:
        """
        Navigate to a goal asynchronously.

        Args:
            goal: Target goal

        Returns:
            True if goal reached, False if failed
        """
        self.set_goal(goal)

        # Create a future for the result
        future = asyncio.get_event_loop().create_future()

        def on_reached():
            if not future.done():
                future.set_result(True)

        def on_stop():
            if not future.done():
                future.set_result(False)

        def on_no_path(result):
            if result.status == "noPath" and not future.done():
                future.set_result(False)

        self.once("goal_reached", on_reached)
        self.once("path_stop", on_stop)
        self.on("path_update", on_no_path)

        try:
            result = await future
            return result
        finally:
            self._handlers.get("goal_reached", [])[:] = []
            self._handlers.get("path_stop", [])[:] = []
            self._handlers.get("path_update", [])[:] = []

    # === Monitoring ===

    def monitor_movement(self) -> None:
        """
        Called each physics tick to monitor and execute movement.

        This should be called from the bot's physics tick handler.
        """
        # Check for free motion (direct line to goal)
        if (
            self._movements
            and self._movements.allow_free_motion
            and self._goal
            and hasattr(self._goal, "entity")
        ):
            target = self._goal.entity
            if target and self._physics.can_straight_line(
                [Move(int(target.position[0]), int(target.position[1]), int(target.position[2]))]
            ):
                # Move directly towards entity
                pos = target.position
                self.bot.look_at(pos[0], pos[1] + 1.6, pos[2])

                # Check range
                dist_sq = (
                    (pos[0] - self.bot.position[0]) ** 2
                    + (pos[1] - self.bot.position[1]) ** 2
                    + (pos[2] - self.bot.position[2]) ** 2
                )

                if dist_sq > getattr(self._goal, "range_sq", 16):
                    self.bot.set_control_state("forward", True)
                else:
                    self.bot.clear_control_states()
                return

        # Check goal validity
        if self._goal:
            if not self._goal.is_valid():
                self._stop()
                return
            elif self._goal.has_changed():
                self._reset_path("goal_moved", False)

        # Continue A* computation if timed out
        if self._astar_context and self._astar_timed_out:
            result = self._astar_context.compute()
            result.path = self._post_process_path(result.path)
            self._path_from_player(result.path)
            self.emit("path_update", result)
            self._path = result.path
            self._astar_timed_out = result.status == "partial"

        # Handle returning position for LOS placing
        if self.los_when_placing_blocks and self._returning_pos:
            if not self._move_to_block(self._returning_pos):
                return
            self._returning_pos = None

        # No path - check if at goal
        if not self._path:
            self._last_node_time = time.time() * 1000

            if self._goal and self._movements:
                pos = self.bot.position
                floored = (int(pos[0]), int(pos[1]), int(pos[2]))

                if self._goal.is_end(Move(floored[0], floored[1], floored[2])):
                    if not self._dynamic_goal:
                        self.emit("goal_reached", self._goal)
                        self._goal = None
                        self._full_stop()
                elif not self._path_updated:
                    # Compute new path
                    result = self.get_path_to(self._movements, self._goal)
                    self.emit("path_update", result)
                    self._path = result.path
                    self._astar_timed_out = result.status == "partial"
                    self._path_updated = True
            return

        # Execute path
        self._execute_path()

    def _execute_path(self) -> None:
        """Execute current path"""
        if not self._path:
            return

        next_point = self._path[0]
        pos = self.bot.position

        # Handle digging
        if self._digging or next_point.to_break:
            self._handle_digging(next_point)
            return

        # Handle placing
        if self._placing or next_point.to_place:
            self._handle_placing(next_point)
            return

        # Check if arrived at next point
        dx = next_point.x + 0.5 - pos[0]
        dy = next_point.y - pos[1]
        dz = next_point.z + 0.5 - pos[2]

        if abs(dx) <= 0.35 and abs(dz) <= 0.35 and abs(dy) < 1:
            # Arrived at next point
            self._last_node_time = time.time() * 1000

            if self._stop_pathing:
                self._stop()
                return

            self._path.pop(0)

            if not self._path:
                # Path complete
                if not self._dynamic_goal and self._goal:
                    floored = (int(pos[0]), int(pos[1]), int(pos[2]))
                    if self._goal.is_end(Move(floored[0], floored[1], floored[2])):
                        self.emit("goal_reached", self._goal)
                        self._goal = None
                self._full_stop()
                return

            # Get next point
            next_point = self._path[0]
            if next_point.to_break or next_point.to_place:
                self._full_stop()
                return

            dx = next_point.x + 0.5 - pos[0]
            dz = next_point.z + 0.5 - pos[2]

        # Move towards next point
        self.bot.look(math.atan2(-dx, -dz), 0)
        self.bot.set_control_state("forward", True)
        self.bot.set_control_state("jump", False)

        # Determine movement type
        in_water = getattr(self.bot, "in_water", False)

        if in_water:
            self.bot.set_control_state("jump", True)
            self.bot.set_control_state("sprint", False)
        elif self._movements.allow_sprinting and self._physics.can_straight_line(self._path, True):
            self.bot.set_control_state("jump", False)
            self.bot.set_control_state("sprint", True)
        elif self._movements.allow_sprinting and self._physics.can_sprint_jump(self._path):
            self.bot.set_control_state("jump", True)
            self.bot.set_control_state("sprint", True)
        elif self._physics.can_straight_line(self._path):
            self.bot.set_control_state("jump", False)
            self.bot.set_control_state("sprint", False)
        elif self._physics.can_walk_jump(self._path):
            self.bot.set_control_state("jump", True)
            self.bot.set_control_state("sprint", False)
        else:
            self.bot.set_control_state("forward", False)
            self.bot.set_control_state("sprint", False)

        # Check for stuck
        if time.time() * 1000 - self._last_node_time > 3500:
            self._reset_path("stuck")

    def _handle_digging(self, next_point: Move) -> None:
        """Handle block breaking during path"""
        if not self._digging and self.bot.on_ground:
            if not next_point.to_break:
                return

            self._digging = True
            to_break = next_point.to_break.pop(0)

            block = self.bot.block_at(to_break.x, to_break.y, to_break.z)
            if not block:
                self._digging = False
                return

            tool = self.best_harvest_tool(block)
            self._full_stop()

            # Equip tool and dig
            async def dig_block():
                try:
                    if tool:
                        await self.bot.equip(tool, "hand")
                    await self.bot.dig(block)
                    self._last_node_time = time.time() * 1000
                except Exception:
                    self._reset_path("dig_error")
                finally:
                    self._digging = False

            asyncio.create_task(dig_block())

    def _handle_placing(self, next_point: Move) -> None:
        """Handle block placing during path"""
        if not self._placing:
            if not next_point.to_place:
                return

            self._placing = True
            self._placing_block = next_point.to_place.pop(0)
            self._full_stop()

        if not self._placing_block:
            self._placing = False
            return

        # Handle openable blocks (doors, gates)
        if self._placing_block.get("use_one"):
            block = self.bot.block_at(
                self._placing_block["x"], self._placing_block["y"], self._placing_block["z"]
            )
            if block:

                async def use_block():
                    try:
                        await self.bot.activate_block(block)
                    except Exception:
                        pass
                    self._placing_block = (
                        next_point.to_place.pop(0) if next_point.to_place else None
                    )

                asyncio.create_task(use_block())
            return

        # Get scaffolding block
        scaffolding = self._movements.get_scaffolding_item()
        if not scaffolding:
            self._reset_path("no_scaffolding_blocks")
            return

        # Handle LOS placing
        if (
            self.los_when_placing_blocks
            and self._placing_block["y"] == int(self.bot.position[1]) - 1
            and self._placing_block.get("dy", 0) == 0
        ):
            if not self._move_to_edge(
                (self._placing_block["x"], self._placing_block["y"], self._placing_block["z"]),
                (self._placing_block.get("dx", 0), 0, self._placing_block.get("dz", 0)),
            ):
                return

        # Place block
        can_place = True
        if self._placing_block.get("jump"):
            self.bot.set_control_state("jump", True)
            can_place = self._placing_block["y"] + 1 < self.bot.position[1]

        if can_place:

            async def place():
                try:
                    await self.bot.equip(scaffolding, "hand")

                    ref_block = self.bot.block_at(
                        self._placing_block["x"], self._placing_block["y"], self._placing_block["z"]
                    )

                    if ref_block:
                        await self.bot.place_block(
                            ref_block,
                            self._placing_block.get("dx", 0),
                            self._placing_block.get("dy", 0),
                            self._placing_block.get("dz", 0),
                        )

                        if self.los_when_placing_blocks and self._placing_block.get("return_pos"):
                            self._returning_pos = self._placing_block["return_pos"]
                except Exception:
                    self._reset_path("place_error")
                finally:
                    self.bot.set_control_state("sneak", False)
                    self._placing = False
                    self._last_node_time = time.time() * 1000

            asyncio.create_task(place())

    def _move_to_block(self, pos: Tuple[int, int, int]) -> bool:
        """Move to center of block"""
        target = (pos[0] + 0.5, pos[1], pos[2] + 0.5)
        bot_pos = self.bot.position

        dx = target[0] - bot_pos[0]
        dz = target[2] - bot_pos[2]

        if dx * dx + dz * dz > 0.2 * 0.2:
            self.bot.look_at(target[0], target[1], target[2])
            self.bot.set_control_state("forward", True)
            return False

        self.bot.set_control_state("forward", False)
        return True

    def _move_to_edge(self, ref_block: Tuple[int, int, int], edge: Tuple[int, int, int]) -> bool:
        """Move to edge of block for placing"""
        target = (ref_block[0] + edge[0] + 0.5, ref_block[1], ref_block[2] + edge[2] + 0.5)
        bot_pos = self.bot.position

        dx = target[0] - bot_pos[0]
        dz = target[2] - bot_pos[2]
        distance = (dx * dx + dz * dz) ** 0.5

        if distance > 0.4:
            # Look away from edge and back up
            yaw = math.atan2(-dx, -dz)
            self.bot.look(yaw, -1.421)
            self.bot.set_control_state("sneak", True)
            self.bot.set_control_state("back", True)
            return False

        self.bot.set_control_state("back", False)
        return True

    def _path_from_player(self, path: List[Move]) -> None:
        """Trim path from current player position"""
        if not path:
            return

        min_i = 0
        min_distance = 1000

        for i, node in enumerate(path):
            if node.to_break or node.to_place:
                break

            pos = self.bot.position
            dist = (node.x - pos[0]) ** 2 + (node.y - pos[1]) ** 2 + (node.z - pos[2]) ** 2

            if dist < min_distance:
                min_distance = dist
                min_i = i

        # Check if between nodes
        n1 = path[min_i]
        dx = n1.x + 0.5 - self.bot.position[0]
        dy = n1.y - self.bot.position[1]
        dz = n1.z + 0.5 - self.bot.position[2]
        reached = abs(dx) <= 0.35 and abs(dz) <= 0.35 and abs(dy) < 1

        if min_i + 1 < len(path) and not n1.to_break and not n1.to_place:
            n2 = path[min_i + 1]
            pos = self.bot.position
            d2 = (n2.x - pos[0]) ** 2 + (n2.y - pos[1]) ** 2 + (n2.z - pos[2]) ** 2
            d12 = (n2.x - n1.x) ** 2 + (n2.y - n1.y) ** 2 + (n2.z - n1.z) ** 2

            if d12 > d2 or reached:
                min_i += 1

        # Trim path
        if min_i > 0:
            path[:] = path[min_i:]
