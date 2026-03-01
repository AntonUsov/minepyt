"""
Goals system for pathfinding

Based on mineflayer-pathfinder/lib/goals.js

This module provides various goal types for the pathfinder:
- GoalBlock: Reach a specific block
- GoalNear: Get within range of a position
- GoalXZ: Reach X/Z coordinates (any Y)
- GoalFollow: Follow an entity
- Composite goals: Combine multiple goals
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from ..protocol.connection import MinecraftProtocol
    from ..entities import Entity

from .move import Move, distance_xz


class Goal(ABC):
    """
    Abstract base class for pathfinding goals.
    
    A goal defines:
    - heuristic(node): Estimated distance to goal (must be admissible)
    - is_end(node): Whether the node satisfies the goal
    - has_changed(): Whether the goal has changed (path needs recalc)
    - is_valid(): Whether the goal is still achievable
    """
    
    @abstractmethod
    def heuristic(self, node: Move) -> float:
        """
        Calculate heuristic cost from node to goal.
        Must never overestimate (admissible heuristic).
        """
        return 0
    
    @abstractmethod
    def is_end(self, node: Move) -> bool:
        """Check if node satisfies the goal"""
        return True
    
    def has_changed(self) -> bool:
        """Check if goal has changed (path should be recalculated)"""
        return False
    
    def is_valid(self) -> bool:
        """Check if goal is still valid"""
        return True


class GoalBlock(Goal):
    """Reach a specific block at foot level"""
    
    def __init__(self, x: int, y: int, z: int):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
    
    def heuristic(self, node: Move) -> float:
        dx = self.x - node.x
        dy = self.y - node.y
        dz = self.z - node.z
        return distance_xz(dx, dz) + abs(dy)
    
    def is_end(self, node: Move) -> bool:
        return node.x == self.x and node.y == self.y and node.z == self.z
    
    def __repr__(self) -> str:
        return f"GoalBlock({self.x}, {self.y}, {self.z})"


class GoalNear(Goal):
    """Get within a certain radius of a position"""
    
    def __init__(self, x: int, y: int, z: int, range: int):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
        self.range_sq = range * range
    
    def heuristic(self, node: Move) -> float:
        dx = self.x - node.x
        dy = self.y - node.y
        dz = self.z - node.z
        return distance_xz(dx, dz) + abs(dy)
    
    def is_end(self, node: Move) -> bool:
        dx = self.x - node.x
        dy = self.y - node.y
        dz = self.z - node.z
        return (dx * dx + dy * dy + dz * dz) <= self.range_sq
    
    def __repr__(self) -> str:
        return f"GoalNear({self.x}, {self.y}, {self.z}, range={int(self.range_sq**0.5)})"


class GoalXZ(Goal):
    """Reach X/Z coordinates (any Y level)"""
    
    def __init__(self, x: int, z: int):
        self.x = int(x)
        self.z = int(z)
    
    def heuristic(self, node: Move) -> float:
        dx = self.x - node.x
        dz = self.z - node.z
        return distance_xz(dx, dz)
    
    def is_end(self, node: Move) -> bool:
        return node.x == self.x and node.z == self.z
    
    def __repr__(self) -> str:
        return f"GoalXZ({self.x}, {self.z})"


class GoalNearXZ(Goal):
    """Get within range of X/Z coordinates (any Y)"""
    
    def __init__(self, x: int, z: int, range: int):
        self.x = int(x)
        self.z = int(z)
        self.range_sq = range * range
    
    def heuristic(self, node: Move) -> float:
        dx = self.x - node.x
        dz = self.z - node.z
        return distance_xz(dx, dz)
    
    def is_end(self, node: Move) -> bool:
        dx = self.x - node.x
        dz = self.z - node.z
        return (dx * dx + dz * dz) <= self.range_sq
    
    def __repr__(self) -> str:
        return f"GoalNearXZ({self.x}, {self.z}, range={int(self.range_sq**0.5)})"


class GoalY(Goal):
    """Reach a specific Y level"""
    
    def __init__(self, y: int):
        self.y = int(y)
    
    def heuristic(self, node: Move) -> float:
        return abs(self.y - node.y)
    
    def is_end(self, node: Move) -> bool:
        return node.y == self.y
    
    def __repr__(self) -> str:
        return f"GoalY({self.y})"


class GoalGetToBlock(Goal):
    """Get directly adjacent to a block (useful for chests, furnaces, etc.)"""
    
    def __init__(self, x: int, y: int, z: int):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
    
    def heuristic(self, node: Move) -> float:
        dx = node.x - self.x
        dy = node.y - self.y
        dz = node.z - self.z
        return distance_xz(dx, dz) + abs(dy if dy >= 0 else dy + 1)
    
    def is_end(self, node: Move) -> bool:
        dx = node.x - self.x
        dy = node.y - self.y
        dz = node.z - self.z
        # Manhattan distance of 1 (adjacent)
        return abs(dx) + abs(dy if dy >= 0 else dy + 1) + abs(dz) == 1
    
    def __repr__(self) -> str:
        return f"GoalGetToBlock({self.x}, {self.y}, {self.z})"


class GoalLookAtBlock(Goal):
    """Get to a position where a block face is visible"""
    
    def __init__(self, x: int, y: int, z: int, reach: float = 4.5, entity_height: float = 1.6):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
        self.reach = reach
        self.entity_height = entity_height
    
    def heuristic(self, node: Move) -> float:
        dx = node.x - self.x
        dy = node.y - self.y
        dz = node.z - self.z
        return distance_xz(dx, dz) + abs(dy if dy >= 0 else dy + 1)
    
    def is_end(self, node: Move) -> bool:
        # Calculate distance from player head to block center
        head_x = node.x + 0.5
        head_y = node.y + self.entity_height
        head_z = node.z + 0.5
        
        block_center_y = self.y + 0.5
        
        dx = head_x - (self.x + 0.5)
        dy = head_y - block_center_y
        dz = head_z - (self.z + 0.5)
        
        distance = (dx * dx + dy * dy + dz * dz) ** 0.5
        
        if distance > self.reach:
            return False
        
        # Check if any face is visible (simplified)
        visible_faces = []
        
        if abs(dy) > 0.5:
            visible_faces.append('y')
        if abs(dx) > 0.5:
            visible_faces.append('x')
        if abs(dz) > 0.5:
            visible_faces.append('z')
        
        return len(visible_faces) > 0
    
    def __repr__(self) -> str:
        return f"GoalLookAtBlock({self.x}, {self.y}, {self.z})"


class GoalPlaceBlock(Goal):
    """Position to place a block at a location"""
    
    def __init__(self, x: int, y: int, z: int, 
                 reach: float = 5.0, 
                 faces: Optional[List[Tuple[int, int, int]]] = None,
                 facing: Optional[str] = None,
                 los: bool = True):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)
        self.reach = reach
        self.los = los  # Line of sight required
        
        if faces is None:
            self.faces = [
                (0, -1, 0), (0, 1, 0),  # bottom, top
                (0, 0, -1), (0, 0, 1),  # north, south
                (-1, 0, 0), (1, 0, 0),  # west, east
            ]
        else:
            self.faces = faces
        
        self.facing = facing
    
    def heuristic(self, node: Move) -> float:
        dx = node.x - self.x
        dy = node.y - self.y
        dz = node.z - self.z
        return distance_xz(dx, dz) + abs(dy if dy >= 0 else dy + 1)
    
    def is_end(self, node: Move) -> bool:
        # Check if standing in the block position
        dx = node.x - self.x
        dy = node.y - self.y
        dz = node.z - self.z
        
        if abs(dx) + abs(dy if dy >= 0 else dy + 1) + abs(dz) < 1:
            return False  # Standing in the block
        
        # Check if any face is within reach
        head_x = node.x + 0.5
        head_y = node.y + 1.6
        head_z = node.z + 0.5
        
        for face in self.faces:
            # Calculate face position
            face_x = self.x + 0.5 + face[0] * 0.5
            face_y = self.y + 0.5 + face[1] * 0.5
            face_z = self.z + 0.5 + face[2] * 0.5
            
            distance = ((head_x - face_x) ** 2 + 
                       (head_y - face_y) ** 2 + 
                       (head_z - face_z) ** 2) ** 0.5
            
            if distance <= self.reach:
                return True
        
        return False
    
    def __repr__(self) -> str:
        return f"GoalPlaceBlock({self.x}, {self.y}, {self.z})"


class GoalFollow(Goal):
    """Follow an entity"""
    
    def __init__(self, entity: 'Entity', range: int):
        self.entity = entity
        self.range = range
        self.range_sq = range * range
        
        # Track last known position
        pos = entity.position if hasattr(entity, 'position') else (0, 0, 0)
        self.x = int(pos[0])
        self.y = int(pos[1])
        self.z = int(pos[2])
    
    def heuristic(self, node: Move) -> float:
        dx = self.x - node.x
        dy = self.y - node.y
        dz = self.z - node.z
        return distance_xz(dx, dz) + abs(dy)
    
    def is_end(self, node: Move) -> bool:
        dx = self.x - node.x
        dy = self.y - node.y
        dz = self.z - node.z
        return (dx * dx + dy * dy + dz * dz) <= self.range_sq
    
    def has_changed(self) -> bool:
        """Check if entity has moved significantly"""
        if not self.entity:
            return False
        
        pos = self.entity.position if hasattr(self.entity, 'position') else None
        if not pos:
            return False
        
        dx = self.x - int(pos[0])
        dy = self.y - int(pos[1])
        dz = self.z - int(pos[2])
        
        if (dx * dx + dy * dy + dz * dz) > self.range_sq:
            self.x = int(pos[0])
            self.y = int(pos[1])
            self.z = int(pos[2])
            return True
        
        return False
    
    def is_valid(self) -> bool:
        """Check if entity still exists"""
        return self.entity is not None
    
    def __repr__(self) -> str:
        return f"GoalFollow(entity={self.entity}, range={self.range})"


class GoalCompositeAny(Goal):
    """Any one of multiple goals must be satisfied"""
    
    def __init__(self, goals: Optional[List[Goal]] = None):
        self.goals = goals or []
    
    def push(self, goal: Goal) -> None:
        self.goals.append(goal)
    
    def heuristic(self, node: Move) -> float:
        if not self.goals:
            return 0
        return min(g.heuristic(node) for g in self.goals)
    
    def is_end(self, node: Move) -> bool:
        return any(g.is_end(node) for g in self.goals)
    
    def has_changed(self) -> bool:
        return any(g.has_changed() for g in self.goals)
    
    def is_valid(self) -> bool:
        return all(g.is_valid() for g in self.goals)
    
    def __repr__(self) -> str:
        return f"GoalCompositeAny({len(self.goals)} goals)"


class GoalCompositeAll(Goal):
    """All goals must be satisfied"""
    
    def __init__(self, goals: Optional[List[Goal]] = None):
        self.goals = goals or []
    
    def push(self, goal: Goal) -> None:
        self.goals.append(goal)
    
    def heuristic(self, node: Move) -> float:
        if not self.goals:
            return 0
        return max(g.heuristic(node) for g in self.goals)
    
    def is_end(self, node: Move) -> bool:
        return all(g.is_end(node) for g in self.goals)
    
    def has_changed(self) -> bool:
        return any(g.has_changed() for g in self.goals)
    
    def is_valid(self) -> bool:
        return all(g.is_valid() for g in self.goals)
    
    def __repr__(self) -> str:
        return f"GoalCompositeAll({len(self.goals)} goals)"


class GoalInvert(Goal):
    """Invert a goal (satisfied when original goal is NOT satisfied)"""
    
    def __init__(self, goal: Goal):
        self.goal = goal
    
    def heuristic(self, node: Move) -> float:
        return -self.goal.heuristic(node)
    
    def is_end(self, node: Move) -> bool:
        return not self.goal.is_end(node)
    
    def has_changed(self) -> bool:
        return self.goal.has_changed()
    
    def is_valid(self) -> bool:
        return self.goal.is_valid()
    
    def __repr__(self) -> str:
        return f"GoalInvert({self.goal})"
