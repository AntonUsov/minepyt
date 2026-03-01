"""
Move class - represents a node in the pathfinding graph

Based on mineflayer-pathfinder/lib/move.js
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class BlockOperation:
    """Represents a block to break or place during movement"""

    x: int
    y: int
    z: int
    dx: int = 0  # Direction for placement
    dy: int = 0
    dz: int = 0
    jump: bool = False  # Jump while placing
    use_one: bool = False  # Use block (for doors/gates)
    return_pos: Optional[Tuple[int, int, int]] = None  # Position to return to after placing

    @property
    def position(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.z)

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "dx": self.dx,
            "dy": self.dy,
            "dz": self.dz,
            "jump": self.jump,
            "useOne": self.use_one,
            "returnPos": self.return_pos,
        }


@dataclass
class Move:
    """
    A movement node in the pathfinding graph.

    Attributes:
        x, y, z: Block coordinates
        remaining_blocks: Number of scaffolding blocks available
        cost: Total cost to reach this move from start
        to_break: List of blocks that need to be broken
        to_place: List of blocks that need to be placed
        parkour: Whether this is a parkour jump
    """

    x: int
    y: int
    z: int
    remaining_blocks: int = 0
    cost: float = 0.0
    to_break: List[BlockOperation] = field(default_factory=list)
    to_place: List[BlockOperation] = field(default_factory=list)
    parkour: bool = False

    def __post_init__(self):
        # Ensure coordinates are integers
        self.x = int(self.x)
        self.y = int(self.y)
        self.z = int(self.z)
        # Create hash for fast lookup
        self._hash = f"{self.x},{self.y},{self.z}"

    @property
    def hash(self) -> str:
        """Unique identifier for this move"""
        return self._hash

    @property
    def position(self) -> Tuple[int, int, int]:
        """Get position as tuple"""
        return (self.x, self.y, self.z)

    def offset(self, dx: int, dy: int, dz: int) -> "Move":
        """Create a new move offset by given values"""
        return Move(
            self.x + dx,
            self.y + dy,
            self.z + dz,
            self.remaining_blocks,
            self.cost,
            self.to_break.copy(),
            self.to_place.copy(),
            self.parkour,
        )

    def distance_to(self, other: "Move") -> float:
        """Calculate distance to another move"""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def distance_xz(self, other: "Move") -> float:
        """Calculate horizontal distance to another move"""
        dx = abs(self.x - other.x)
        dz = abs(self.z - other.z)
        return abs(dx - dz) + min(dx, dz) * (2**0.5)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def __lt__(self, other: "Move") -> bool:
        return self.cost < other.cost

    def __repr__(self) -> str:
        return f"Move({self.x}, {self.y}, {self.z}, cost={self.cost:.1f})"


def distance_xz(dx: float, dz: float) -> float:
    """Calculate horizontal distance using octile distance"""
    dx = abs(dx)
    dz = abs(dz)
    return abs(dx - dz) + min(dx, dz) * (2**0.5)
