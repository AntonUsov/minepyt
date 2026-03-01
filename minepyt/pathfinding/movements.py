"""
Movements class - generates possible moves for pathfinding

Based on mineflayer-pathfinder/lib/movements.js

This module handles:
- Block property checking (physical, safe, liquid, etc.)
- Movement generation (forward, jump, diagonal, drop, parkour)
- Block breaking and placing during path
- Entity collision detection
- Scaffolding blocks management
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from ..protocol.connection import MinecraftProtocol

from .move import Move, BlockOperation


# Direction vectors
CARDINAL_DIRECTIONS = [
    {"x": -1, "z": 0},  # West
    {"x": 1, "z": 0},  # East
    {"x": 0, "z": -1},  # North
    {"x": 0, "z": 1},  # South
]

DIAGONAL_DIRECTIONS = [
    {"x": -1, "z": -1},  # NW
    {"x": -1, "z": 1},  # SW
    {"x": 1, "z": -1},  # NE
    {"x": 1, "z": 1},  # SE
]


@dataclass
class BlockProperties:
    """Properties of a block relevant for pathfinding"""

    position: Tuple[int, int, int]
    type: int
    name: str = ""
    replaceable: bool = False
    can_fall: bool = False
    safe: bool = False
    physical: bool = False
    liquid: bool = False
    climbable: bool = False
    height: float = 0.0
    openable: bool = False
    shapes: List[List[float]] = field(default_factory=list)


class Movements:
    """
    Configures and generates possible movements for pathfinding.

    This class determines:
    - What blocks can be broken
    - What blocks can be placed
    - Movement costs
    - Which movements are allowed
    """

    def __init__(self, bot: "MinecraftProtocol"):
        self.bot = bot

        # Movement permissions
        self.can_dig: bool = True
        self.allow_1by1_towers: bool = True
        self.allow_free_motion: bool = False
        self.allow_parkour: bool = True
        self.allow_sprinting: bool = True
        self.allow_entity_detection: bool = True
        self.can_open_doors: bool = False

        # Movement costs
        self.dig_cost: float = 1.0
        self.place_cost: float = 1.0
        self.liquid_cost: float = 1.0
        self.entity_cost: float = 1.0

        # Safety settings
        self.dont_create_flow: bool = True
        self.dont_mine_under_falling_block: bool = True
        self.max_drop_down: int = 4
        self.infinite_liquid_dropdown_distance: bool = True

        # Block sets (will be populated from registry)
        self.entities_to_avoid: Set[str] = set()
        self.passable_entities: Set[str] = set()
        self.interactable_blocks: Set[str] = set()
        self.blocks_cant_break: Set[int] = set()
        self.blocks_to_avoid: Set[int] = set()
        self.liquids: Set[int] = set()
        self.gravity_blocks: Set[int] = set()
        self.climbables: Set[int] = set()
        self.replaceables: Set[int] = set()
        self.empty_blocks: Set[int] = set()
        self.fences: Set[int] = set()
        self.carpets: Set[int] = set()
        self.openable: Set[int] = set()

        # Scaffolding blocks (items that can be placed)
        self.scaffolding_blocks: List[int] = []

        # Exclusion areas (functions that return extra cost)
        self.exclusion_areas_step: List[Callable[[Any], float]] = []
        self.exclusion_areas_break: List[Callable[[Any], float]] = []
        self.exclusion_areas_place: List[Callable[[Any], float]] = []

        # Entity collision tracking
        self.entity_intersections: Dict[str, int] = {}

        # Initialize block sets
        self._init_block_sets()

    def _init_block_sets(self) -> None:
        """Initialize block sets from bot registry"""
        # Try to load interactable blocks
        try:
            interactable_path = Path(__file__).parent / "interactable.json"
            if interactable_path.exists():
                self.interactable_blocks = set(json.loads(interactable_path.read_text()))
        except Exception:
            pass

        # Default interactable blocks
        if not self.interactable_blocks:
            self.interactable_blocks = {
                "chest",
                "furnace",
                "crafting_table",
                "anvil",
                "enchanting_table",
                "brewing_stand",
                "beacon",
                "hopper",
                "dropper",
                "dispenser",
                "trapped_chest",
                "barrel",
                "blast_furnace",
                "smoker",
                "loom",
                "cartography_table",
                "fletching_table",
                "smithing_table",
                "grindstone",
                "stonecutter",
                "shulker_box",
            }

        # Passable entities
        self.passable_entities = {
            "item",
            "xp_orb",
            "area_effect_cloud",
            "painting",
            "leash_knot",
            "armor_stand",
            "firework_rocket",
            "spectral_arrow",
            "shulker_bullet",
            "fishing_bobber",
        }

        # Try to get block IDs from registry
        try:
            # This would need the actual bot registry
            # For now, use common defaults
            pass
        except Exception:
            pass

    def exclusion_place(self, block: Any) -> float:
        """Calculate extra cost for placing at a block"""
        weight = 0.0
        for area_fn in self.exclusion_areas_place:
            weight += area_fn(block)
        return weight

    def exclusion_step(self, block: Any) -> float:
        """Calculate extra cost for stepping on a block"""
        weight = 0.0
        for area_fn in self.exclusion_areas_step:
            weight += area_fn(block)
        return weight

    def exclusion_break(self, block: Any) -> float:
        """Calculate extra cost for breaking a block"""
        weight = 0.0
        for area_fn in self.exclusion_areas_break:
            weight += area_fn(block)
        return weight

    def count_scaffolding_items(self) -> int:
        """Count total scaffolding items in inventory"""
        count = 0
        try:
            for item in self.bot.inventory.values():
                if hasattr(item, "item_id") and item.item_id in self.scaffolding_blocks:
                    count += getattr(item, "count", 1)
        except Exception:
            pass
        return count

    def get_scaffolding_item(self) -> Optional[Any]:
        """Get first scaffolding item from inventory"""
        try:
            for item in self.bot.inventory.values():
                if hasattr(item, "item_id") and item.item_id in self.scaffolding_blocks:
                    return item
        except Exception:
            pass
        return None

    def clear_collision_index(self) -> None:
        """Clear entity collision tracking"""
        self.entity_intersections = {}

    def update_collision_index(self) -> None:
        """Update entity collision tracking from current entities"""
        if not self.allow_entity_detection:
            return

        try:
            for entity in self.bot.entities.values():
                if entity == self.bot.entity:
                    continue

                entity_name = getattr(entity, "name", "")
                avoided = entity_name in self.entities_to_avoid
                passable = entity_name in self.passable_entities

                if avoided or not passable:
                    # Get entity bounding box
                    width = getattr(entity, "width", 0.6)
                    height = getattr(entity, "height", 1.8)
                    pos = getattr(entity, "position", (0, 0, 0))

                    radius = width / 2.0
                    min_y = int(pos[1])
                    max_y = int(pos[1] + height) + 1
                    min_x = int(pos[0] - radius)
                    max_x = int(pos[0] + radius) + 1
                    min_z = int(pos[2] - radius)
                    max_z = int(pos[2] + radius) + 1

                    cost = 100 if avoided else 1

                    for y in range(min_y, max_y):
                        for x in range(min_x, max_x):
                            for z in range(min_z, max_z):
                                key = f"{x},{y},{z}"
                                self.entity_intersections[key] = (
                                    self.entity_intersections.get(key, 0) + cost
                                )
        except Exception:
            pass

    def get_num_entities_at(
        self, pos: Optional[Tuple[int, int, int]], dx: int, dy: int, dz: int
    ) -> int:
        """Get number of entities at position"""
        if not self.allow_entity_detection or not pos:
            return 0
        key = f"{pos[0] + dx},{pos[1] + dy},{pos[2] + dz}"
        return self.entity_intersections.get(key, 0)

    def get_block(
        self, pos: Optional[Tuple[int, int, int]], dx: int, dy: int, dz: int
    ) -> BlockProperties:
        """Get block properties at position with offset"""
        if not pos:
            return BlockProperties(
                position=(0, 0, 0),
                type=0,
                replaceable=False,
                can_fall=False,
                safe=False,
                physical=False,
                liquid=False,
                climbable=False,
                height=dy,
                openable=False,
            )

        x, y, z = pos[0] + dx, pos[1] + dy, pos[2] + dz

        try:
            block = self.bot.block_at(x, y, z)
            if block is None:
                return BlockProperties(
                    position=(x, y, z),
                    type=0,
                    name="air",
                    replaceable=True,
                    safe=True,
                    physical=False,
                    liquid=False,
                    climbable=False,
                    height=y,
                )

            block_type = getattr(block, "type", 0) or getattr(block, "id", 0)
            block_name = getattr(block, "name", "unknown")

            # Determine properties
            climbable = block_type in self.climbables or block_name in ("ladder", "vine")
            liquid = block_type in self.liquids or "water" in block_name or "lava" in block_name
            safe = (
                block_name in ("air", "cave_air", "void_air")
                or climbable
                or block_type in self.carpets
            )
            safe = safe and block_type not in self.blocks_to_avoid
            physical = (
                block_name not in ("air", "cave_air", "void_air") and block_type not in self.fences
            )
            replaceable = (
                block_name in ("air", "cave_air", "void_air", "water", "lava") and not physical
            )
            can_fall = block_type in self.gravity_blocks or block_name in (
                "sand",
                "gravel",
                "concrete_powder",
            )
            openable = block_type in self.openable

            # Calculate height from shapes
            height = y
            shapes = getattr(block, "shapes", [])
            if shapes:
                for shape in shapes:
                    if len(shape) >= 6:
                        height = max(height, y + shape[4])

            return BlockProperties(
                position=(x, y, z),
                type=block_type,
                name=block_name,
                replaceable=replaceable,
                can_fall=can_fall,
                safe=safe,
                physical=physical,
                liquid=liquid,
                climbable=climbable,
                height=height,
                openable=openable,
                shapes=shapes,
            )
        except Exception:
            return BlockProperties(
                position=(x, y, z),
                type=0,
                name="unknown",
                replaceable=True,
                safe=True,
                physical=False,
                liquid=False,
                climbable=False,
                height=y,
            )

    def safe_to_break(self, block: BlockProperties) -> bool:
        """Check if a block can be safely broken"""
        if not self.can_dig:
            return False

        pos = block.position

        if self.dont_create_flow:
            # Don't break if adjacent to liquid
            if self.get_block(pos, 0, 1, 0).liquid:
                return False
            if self.get_block(pos, -1, 0, 0).liquid:
                return False
            if self.get_block(pos, 1, 0, 0).liquid:
                return False
            if self.get_block(pos, 0, 0, -1).liquid:
                return False
            if self.get_block(pos, 0, 0, 1).liquid:
                return False

        if self.dont_mine_under_falling_block:
            # Don't break if falling block above
            above = self.get_block(pos, 0, 1, 0)
            if above.can_fall or self.get_num_entities_at(pos, 0, 1, 0) > 0:
                return False

        return block.type not in self.blocks_cant_break and self.exclusion_break(block) < 100

    def safe_or_break(self, block: BlockProperties, to_break: List[BlockOperation]) -> float:
        """
        Check if block is safe or add to break list.
        Returns cost (100 if can't break).
        """
        cost = 0.0
        cost += self.exclusion_step(block)
        cost += self.get_num_entities_at(block.position, 0, 0, 0) * self.entity_cost

        if block.safe:
            return cost

        if not self.safe_to_break(block):
            return 100  # Can't break, can't move

        to_break.append(
            BlockOperation(x=block.position[0], y=block.position[1], z=block.position[2])
        )

        # Add entity cost for falling entities
        if block.physical:
            cost += self.get_num_entities_at(block.position, 0, 1, 0) * self.entity_cost

        # Calculate dig time cost (simplified)
        dig_time = 100  # Default dig time in ms
        labor_cost = (1 + 3 * dig_time / 1000) * self.dig_cost
        cost += labor_cost

        return cost

    def get_move_jump_up(self, node: Move, dir: dict, neighbors: List[Move]) -> None:
        """Generate jump-up move in cardinal direction"""
        dx, dz = dir["x"], dir["z"]

        block_a = self.get_block(node.position, 0, 2, 0)
        block_h = self.get_block(node.position, dx, 2, dz)
        block_b = self.get_block(node.position, dx, 1, dz)
        block_c = self.get_block(node.position, dx, 0, dz)

        cost = 2.0  # move + jump cost
        to_break: List[BlockOperation] = []
        to_place: List[BlockOperation] = []

        # Check for entities that would fall
        if block_a.physical and self.get_num_entities_at(block_a.position, 0, 1, 0) > 0:
            return
        if block_h.physical and self.get_num_entities_at(block_h.position, 0, 1, 0) > 0:
            return
        if block_b.physical and not block_h.physical and not block_c.physical:
            if self.get_num_entities_at(block_b.position, 0, 1, 0) > 0:
                return

        # Need to place blocks?
        if not block_c.physical:
            if node.remaining_blocks == 0:
                return

            if self.get_num_entities_at(block_c.position, 0, 0, 0) > 0:
                return

            block_d = self.get_block(node.position, dx, -1, dz)
            if not block_d.physical:
                if node.remaining_blocks == 1:
                    return

                if self.get_num_entities_at(block_d.position, 0, 0, 0) > 0:
                    return

                if not block_d.replaceable:
                    if not self.safe_to_break(block_d):
                        return
                    cost += self.exclusion_break(block_d)
                    to_break.append(
                        BlockOperation(
                            x=block_d.position[0], y=block_d.position[1], z=block_d.position[2]
                        )
                    )

                cost += self.exclusion_place(block_d)
                to_place.append(
                    BlockOperation(
                        x=node.x,
                        y=node.y - 1,
                        z=node.z,
                        dx=dx,
                        dy=0,
                        dz=dz,
                        return_pos=(node.x, node.y, node.z),
                    )
                )
                cost += self.place_cost

            if not block_c.replaceable:
                if not self.safe_to_break(block_c):
                    return
                cost += self.exclusion_break(block_c)
                to_break.append(
                    BlockOperation(
                        x=block_c.position[0], y=block_c.position[1], z=block_c.position[2]
                    )
                )

            cost += self.exclusion_place(block_c)
            to_place.append(
                BlockOperation(x=node.x + dx, y=node.y - 1, z=node.z + dz, dx=0, dy=1, dz=0)
            )
            cost += self.place_cost
            block_c.height += 1

        # Check jump height
        block_0 = self.get_block(node.position, 0, -1, 0)
        if block_c.height - block_0.height > 1.2:
            return

        # Check blocks to break
        cost += self.safe_or_break(block_a, to_break)
        if cost > 100:
            return
        cost += self.safe_or_break(block_h, to_break)
        if cost > 100:
            return
        cost += self.safe_or_break(block_b, to_break)
        if cost > 100:
            return

        neighbors.append(
            Move(
                block_b.position[0],
                block_b.position[1],
                block_b.position[2],
                node.remaining_blocks - len(to_place),
                cost,
                to_break,
                to_place,
            )
        )

    def get_move_forward(self, node: Move, dir: dict, neighbors: List[Move]) -> None:
        """Generate forward move in cardinal direction"""
        dx, dz = dir["x"], dir["z"]

        block_b = self.get_block(node.position, dx, 1, dz)
        block_c = self.get_block(node.position, dx, 0, dz)
        block_d = self.get_block(node.position, dx, -1, dz)

        cost = 1.0  # move cost
        cost += self.exclusion_step(block_c)

        to_break: List[BlockOperation] = []
        to_place: List[BlockOperation] = []

        # Need to place block below?
        if not block_d.physical and not block_c.liquid:
            if node.remaining_blocks == 0:
                return

            if self.get_num_entities_at(block_d.position, 0, 0, 0) > 0:
                return

            if not block_d.replaceable:
                if not self.safe_to_break(block_d):
                    return
                cost += self.exclusion_break(block_d)
                to_break.append(
                    BlockOperation(
                        x=block_d.position[0], y=block_d.position[1], z=block_d.position[2]
                    )
                )

            cost += self.exclusion_place(block_d)
            to_place.append(BlockOperation(x=node.x, y=node.y - 1, z=node.z, dx=dx, dy=0, dz=dz))
            cost += self.place_cost

        cost += self.safe_or_break(block_b, to_break)
        if cost > 100:
            return

        # Check for openable blocks (doors, gates)
        if self.can_open_doors and block_c.openable and block_c.shapes:
            to_place.append(BlockOperation(x=node.x + dx, y=node.y, z=node.z + dz, use_one=True))
        else:
            cost += self.safe_or_break(block_c, to_break)
            if cost > 100:
                return

        # Extra cost for moving through liquid
        current_block = self.get_block(node.position, 0, 0, 0)
        if current_block.liquid:
            cost += self.liquid_cost

        neighbors.append(
            Move(
                block_c.position[0],
                block_c.position[1],
                block_c.position[2],
                node.remaining_blocks - len(to_place),
                cost,
                to_break,
                to_place,
            )
        )

    def get_move_diagonal(self, node: Move, dir: dict, neighbors: List[Move]) -> None:
        """Generate diagonal move"""
        dx, dz = dir["x"], dir["z"]

        cost = math.sqrt(2)  # diagonal cost
        to_break: List[BlockOperation] = []

        block_c = self.get_block(node.position, dx, 0, dz)
        y = 1 if block_c.physical else 0

        block_0 = self.get_block(node.position, 0, -1, 0)

        # Check two possible paths around corner
        cost1 = 0.0
        to_break1: List[BlockOperation] = []
        block_b1 = self.get_block(node.position, 0, y + 1, dz)
        block_c1 = self.get_block(node.position, 0, y, dz)
        block_d1 = self.get_block(node.position, 0, y - 1, dz)
        cost1 += self.safe_or_break(block_b1, to_break1)
        cost1 += self.safe_or_break(block_c1, to_break1)
        if block_d1.height - block_0.height > 1.2:
            cost1 += self.safe_or_break(block_d1, to_break1)

        cost2 = 0.0
        to_break2: List[BlockOperation] = []
        block_b2 = self.get_block(node.position, dx, y + 1, 0)
        block_c2 = self.get_block(node.position, dx, y, 0)
        block_d2 = self.get_block(node.position, dx, y - 1, 0)
        cost2 += self.safe_or_break(block_b2, to_break2)
        cost2 += self.safe_or_break(block_c2, to_break2)
        if block_d2.height - block_0.height > 1.2:
            cost2 += self.safe_or_break(block_d2, to_break2)

        if cost1 < cost2:
            cost += cost1
            to_break.extend(to_break1)
        else:
            cost += cost2
            to_break.extend(to_break2)

        if cost > 100:
            return

        cost += self.safe_or_break(self.get_block(node.position, dx, y, dz), to_break)
        if cost > 100:
            return
        cost += self.safe_or_break(self.get_block(node.position, dx, y + 1, dz), to_break)
        if cost > 100:
            return

        current_block = self.get_block(node.position, 0, 0, 0)
        if current_block.liquid:
            cost += self.liquid_cost

        block_d = self.get_block(node.position, dx, -1, dz)

        if y == 1:  # Jump up
            if block_c.height - block_0.height > 1.2:
                return
            cost += self.safe_or_break(self.get_block(node.position, 0, 2, 0), to_break)
            if cost > 100:
                return
            cost += 1
            neighbors.append(
                Move(
                    block_c.position[0],
                    block_c.position[1] + 1,
                    block_c.position[2],
                    node.remaining_blocks,
                    cost,
                    to_break,
                )
            )
        elif block_d.physical or block_c.liquid:
            neighbors.append(
                Move(
                    block_c.position[0],
                    block_c.position[1],
                    block_c.position[2],
                    node.remaining_blocks,
                    cost,
                    to_break,
                )
            )
        elif self.get_block(node.position, dx, -2, dz).physical or block_d.liquid:
            if not block_d.safe:
                return
            cost += self.get_num_entities_at(block_c.position, 0, -1, 0) * self.entity_cost
            neighbors.append(
                Move(
                    block_c.position[0],
                    block_c.position[1] - 1,
                    block_c.position[2],
                    node.remaining_blocks,
                    cost,
                    to_break,
                )
            )

    def get_landing_block(self, node: Move, dir: dict) -> Optional[BlockProperties]:
        """Find landing block for drop-down"""
        dx, dz = dir["x"], dir["z"]

        block_land = self.get_block(node.position, dx, -2, dz)
        min_y = -64  # Minecraft minimum Y

        while block_land.position and block_land.position[1] > min_y:
            if block_land.liquid and block_land.safe:
                return block_land
            if block_land.physical:
                if node.y - block_land.position[1] <= self.max_drop_down:
                    return self.get_block(block_land.position, 0, 1, 0)
                return None
            if not block_land.safe:
                return None
            block_land = self.get_block(block_land.position, 0, -1, 0)

        return None

    def get_move_drop_down(self, node: Move, dir: dict, neighbors: List[Move]) -> None:
        """Generate drop-down move"""
        dx, dz = dir["x"], dir["z"]

        block_b = self.get_block(node.position, dx, 1, dz)
        block_c = self.get_block(node.position, dx, 0, dz)
        block_d = self.get_block(node.position, dx, -1, dz)

        cost = 1.0
        to_break: List[BlockOperation] = []
        to_place: List[BlockOperation] = []

        block_land = self.get_landing_block(node, dir)
        if not block_land:
            return

        if not self.infinite_liquid_dropdown_distance:
            if (node.y - block_land.position[1]) > self.max_drop_down:
                return

        cost += self.safe_or_break(block_b, to_break)
        if cost > 100:
            return
        cost += self.safe_or_break(block_c, to_break)
        if cost > 100:
            return
        cost += self.safe_or_break(block_d, to_break)
        if cost > 100:
            return

        if block_c.liquid:
            return  # Don't go underwater

        cost += self.get_num_entities_at(block_land.position, 0, 0, 0) * self.entity_cost

        neighbors.append(
            Move(
                block_land.position[0],
                block_land.position[1],
                block_land.position[2],
                node.remaining_blocks - len(to_place),
                cost,
                to_break,
                to_place,
            )
        )

    def get_move_down(self, node: Move, neighbors: List[Move]) -> None:
        """Generate move straight down"""
        block_0 = self.get_block(node.position, 0, -1, 0)

        cost = 1.0
        to_break: List[BlockOperation] = []
        to_place: List[BlockOperation] = []

        block_land = self.get_landing_block(node, {"x": 0, "z": 0})
        if not block_land:
            return

        cost += self.safe_or_break(block_0, to_break)
        if cost > 100:
            return

        current_block = self.get_block(node.position, 0, 0, 0)
        if current_block.liquid:
            return  # Don't go underwater

        cost += self.get_num_entities_at(block_land.position, 0, 0, 0) * self.entity_cost

        neighbors.append(
            Move(
                block_land.position[0],
                block_land.position[1],
                block_land.position[2],
                node.remaining_blocks - len(to_place),
                cost,
                to_break,
                to_place,
            )
        )

    def get_move_up(self, node: Move, neighbors: List[Move]) -> None:
        """Generate move straight up (climb or tower)"""
        block_1 = self.get_block(node.position, 0, 0, 0)
        if block_1.liquid:
            return
        if self.get_num_entities_at(node.position, 0, 0, 0) > 0:
            return

        block_2 = self.get_block(node.position, 0, 2, 0)

        cost = 1.0
        to_break: List[BlockOperation] = []
        to_place: List[BlockOperation] = []

        cost += self.safe_or_break(block_2, to_break)
        if cost > 100:
            return

        if not block_1.climbable:
            if not self.allow_1by1_towers or node.remaining_blocks == 0:
                return

            if not block_1.replaceable:
                if not self.safe_to_break(block_1):
                    return
                to_break.append(BlockOperation(x=node.x, y=node.y, z=node.z))

            block_0 = self.get_block(node.position, 0, -1, 0)
            if block_0.physical and block_0.height - node.y < -0.2:
                return  # Can't jump-place from half block

            cost += self.exclusion_place(block_1)
            to_place.append(
                BlockOperation(x=node.x, y=node.y - 1, z=node.z, dx=0, dy=1, dz=0, jump=True)
            )
            cost += self.place_cost

        if cost > 100:
            return

        neighbors.append(
            Move(
                node.x,
                node.y + 1,
                node.z,
                node.remaining_blocks - len(to_place),
                cost,
                to_break,
                to_place,
            )
        )

    def get_move_parkour_forward(self, node: Move, dir: dict, neighbors: List[Move]) -> None:
        """Generate parkour jump over gap"""
        if not self.allow_parkour:
            return

        dx, dz = dir["x"], dir["z"]

        block_0 = self.get_block(node.position, 0, -1, 0)
        block_1 = self.get_block(node.position, dx, -1, dz)

        if block_1.physical and block_1.height >= block_0.height:
            return
        if not self.get_block(node.position, dx, 0, dz).safe:
            return
        if not self.get_block(node.position, dx, 1, dz).safe:
            return

        current_block = self.get_block(node.position, 0, 0, 0)
        if current_block.liquid:
            return  # Can't jump from water

        cost = 1.0

        cost += self.get_num_entities_at(node.position, dx, 0, dz) * self.entity_cost

        # Check ceiling clearance
        ceiling_clear = (
            self.get_block(node.position, 0, 2, 0).safe
            and self.get_block(node.position, dx, 2, dz).safe
        )

        # Check floor clearance for down path
        floor_cleared = not self.get_block(node.position, dx, -2, dz).physical

        max_d = 4 if self.allow_sprinting else 2

        for d in range(2, max_d + 1):
            pdx = dx * d
            pdz = dz * d

            block_a = self.get_block(node.position, pdx, 2, pdz)
            block_b = self.get_block(node.position, pdx, 1, pdz)
            block_c = self.get_block(node.position, pdx, 0, pdz)
            block_d = self.get_block(node.position, pdx, -1, pdz)

            if block_c.safe:
                cost += self.get_num_entities_at(block_c.position, 0, 0, 0) * self.entity_cost

            if ceiling_clear and block_b.safe and block_c.safe and block_d.physical:
                # Forward landing
                cost += self.exclusion_step(block_b)
                neighbors.append(
                    Move(
                        block_c.position[0],
                        block_c.position[1],
                        block_c.position[2],
                        node.remaining_blocks,
                        cost,
                        [],
                        [],
                        parkour=True,
                    )
                )
                break
            elif ceiling_clear and block_b.safe and block_c.physical:
                # Jump up landing
                if block_a.safe and d != 4:
                    cost += self.exclusion_step(block_a)
                    if block_c.height - block_0.height > 1.2:
                        break
                    cost += self.get_num_entities_at(block_b.position, 0, 0, 0) * self.entity_cost
                    neighbors.append(
                        Move(
                            block_b.position[0],
                            block_b.position[1],
                            block_b.position[2],
                            node.remaining_blocks,
                            cost,
                            [],
                            [],
                            parkour=True,
                        )
                    )
                    break
            elif (
                (ceiling_clear or d == 2)
                and block_b.safe
                and block_c.safe
                and block_d.safe
                and floor_cleared
            ):
                # Drop down landing
                block_e = self.get_block(node.position, pdx, -2, pdz)
                if block_e.physical:
                    cost += self.exclusion_step(block_d)
                    cost += self.get_num_entities_at(block_d.position, 0, 0, 0) * self.entity_cost
                    neighbors.append(
                        Move(
                            block_d.position[0],
                            block_d.position[1],
                            block_d.position[2],
                            node.remaining_blocks,
                            cost,
                            [],
                            [],
                            parkour=True,
                        )
                    )
                floor_cleared = floor_cleared and not block_e.physical
            elif not block_b.safe or not block_c.safe:
                break

            ceiling_clear = ceiling_clear and block_a.safe

    def get_neighbors(self, node: Move) -> List[Move]:
        """Generate all valid neighbor moves from a node"""
        neighbors: List[Move] = []

        # Cardinal directions
        for direction in CARDINAL_DIRECTIONS:
            self.get_move_forward(node, direction, neighbors)
            self.get_move_jump_up(node, direction, neighbors)
            self.get_move_drop_down(node, direction, neighbors)
            if self.allow_parkour:
                self.get_move_parkour_forward(node, direction, neighbors)

        # Diagonal directions
        for direction in DIAGONAL_DIRECTIONS:
            self.get_move_diagonal(node, direction, neighbors)

        # Vertical moves
        self.get_move_down(node, neighbors)
        self.get_move_up(node, neighbors)

        return neighbors
