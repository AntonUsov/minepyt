"""
Pathfinding module for minepyt - Python port of mineflayer-pathfinder

This module provides:
- A* pathfinding algorithm
- Movement generation with block breaking/placing
- Goal system (14 goal types)
- Physics simulation
- Entity detection and avoidance

Based on: https://github.com/PrismarineJS/mineflayer-pathfinder
"""

from .move import Move, BlockOperation
from .heap import BinaryHeap
from .goals import (
    Goal,
    GoalBlock,
    GoalNear,
    GoalXZ,
    GoalNearXZ,
    GoalY,
    GoalGetToBlock,
    GoalLookAtBlock,
    GoalPlaceBlock,
    GoalCompositeAny,
    GoalCompositeAll,
    GoalInvert,
    GoalFollow,
)
from .movements import Movements
from .astar import AStar, AStarIterable, PathResult
from .physics import Physics
from .pathfinder import Pathfinder


# Compatibility wrapper for old API
class PathfinderManager:
    """
    Compatibility wrapper that provides the old PathfinderManager API.
    
    This allows existing code using the old API to work with the new
    pathfinding module without changes.
    """
    
    def __init__(self, protocol):
        """
        Initialize pathfinder manager.
        
        Args:
            protocol: MinecraftProtocol instance
        """
        self.protocol = protocol
        self._pathfinder = Pathfinder(protocol)
        
        # Settings for compatibility
        self._max_distance = 64
        self._allow_jump = True
        self._allow_fall = True
        self._allow_climb = True
        self._allow_swim = True
        self._max_fall_height = 3
    
    async def goto(self, x: float, y: float, z: float, max_distance: int = 64) -> bool:
        """
        Navigate to a position.
        
        Args:
            x, y, z: Target coordinates
            max_distance: Maximum pathfinding distance
            
        Returns:
            True if reached, False if failed
        """
        self._max_distance = max_distance
        goal = GoalBlock(int(x), int(y), int(z))
        return await self._pathfinder.goto(goal)
    
    async def goto_block(self, block, max_distance: int = 64) -> bool:
        """Navigate to a block"""
        pos = block.position
        goal = GoalNear(int(pos[0]), int(pos[1]), int(pos[2]), 1)
        return await self._pathfinder.goto(goal)
    
    async def goto_entity(self, entity, max_distance: int = 64) -> bool:
        """Navigate to an entity"""
        pos = entity.position
        goal = GoalNear(int(pos[0]), int(pos[1]), int(pos[2]), 2)
        return await self._pathfinder.goto(goal)
    
    def find_path(self, goal_pos):
        """Find a path without moving (returns list of positions)"""
        # Simple path result for compatibility
        from .astar import PathResult
        goal = GoalBlock(int(goal_pos[0]), int(goal_pos[1]), int(goal_pos[2]))
        result = self._pathfinder.get_path_to(self._pathfinder.movements, goal)
        return result
    
    def stop(self):
        """Stop current navigation"""
        self._pathfinder.stop()
    
    def set_settings(
        self,
        allow_jump: bool = True,
        allow_fall: bool = True,
        allow_climb: bool = True,
        allow_swim: bool = True,
        max_fall_height: int = 3,
    ):
        """Update pathfinder settings"""
        self._allow_jump = allow_jump
        self._allow_fall = allow_fall
        self._allow_climb = allow_climb
        self._allow_swim = allow_swim
        self._max_fall_height = max_fall_height
        
        # Apply to movements
        movements = self._pathfinder.movements
        if movements:
            movements.can_jump = allow_jump
            movements.allow_falling = allow_fall
            movements.max_fall_height = max_fall_height
            movements.allow_swim = allow_swim
            movements.allow_climb = allow_climb
    
    @property
    def pathfinder(self):
        """Access to the underlying Pathfinder instance"""
        return self._pathfinder

__all__ = [
    # Core
    "Move",
    "BlockOperation",
    "BinaryHeap",
    "AStar",
    "AStar",
    "AStarIterable",
    # Goals
    "Goal",
    "GoalBlock",
    "GoalNear",
    "GoalXZ",
    "GoalNearXZ",
    "GoalY",
    "GoalGetToBlock",
    "GoalLookAtBlock",
    "GoalPlaceBlock",
    "GoalCompositeAny",
    "GoalCompositeAll",
    "GoalInvert",
    "GoalFollow",
    # Systems
    "Movements",
    "Physics",
    "Pathfinder",
    "Pathfinder",
    "PathfinderManager",
]
