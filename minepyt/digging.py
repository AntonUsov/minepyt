"""
Digging helper module for minepyt.

Provides:
- Block hardness values
- Tool tier system
- Dig time calculation
- Harvest checking
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


class ToolTier:
    """Tool tier levels (mining level)."""

    WOOD = 0
    GOLD = 0  # Gold mines at wood level
    STONE = 1
    IRON = 2
    DIAMOND = 3
    NETHERITE = 4


class ToolType:
    """Tool types for mining."""

    PICKAXE = "pickaxe"
    AXE = "axe"
    SHOVEL = "shovel"
    HOE = "hoe"
    SWORD = "sword"
    HAND = "hand"


# Block hardness values (time to break with hand = hardness * 1.5s)
BLOCK_HARDNESS: Dict[str, float] = {
    # Unbreakable
    "minecraft:bedrock": -1.0,
    "minecraft:barrier": -1.0,
    "minecraft:structure_void": -1.0,
    "minecraft:end_portal_frame": -1.0,
    "minecraft:reinforced_deepslate": -1.0,
    # Instant break (0.0)
    "minecraft:air": 0.0,
    "minecraft:grass": 0.0,
    "minecraft:tall_grass": 0.0,
    "minecraft:fern": 0.0,
    "minecraft:dead_bush": 0.0,
    "minecraft:dandelion": 0.0,
    "minecraft:poppy": 0.0,
    "minecraft:snow": 0.0,
    "minecraft:sugar_cane": 0.0,
    "minecraft:torch": 0.0,
    "minecraft:redstone_torch": 0.0,
    "minecraft:redstone_wire": 0.0,
    "minecraft:lever": 0.0,
    "minecraft:tripwire": 0.0,
    # Very soft (0.5)
    "minecraft:dirt": 0.5,
    "minecraft:coarse_dirt": 0.5,
    "minecraft:grass_block": 0.6,
    "minecraft:podzol": 0.5,
    "minecraft:mycelium": 0.6,
    "minecraft:sand": 0.5,
    "minecraft:red_sand": 0.5,
    "minecraft:gravel": 0.6,
    "minecraft:clay": 0.6,
    "minecraft:soul_sand": 0.5,
    "minecraft:soul_soil": 0.5,
    "minecraft:farmland": 0.6,
    "minecraft:dirt_path": 0.65,
    # Soft (1.0-1.5)
    "minecraft:cobblestone": 2.0,
    "minecraft:mossy_cobblestone": 2.0,
    "minecraft:stone": 1.5,
    "minecraft:granite": 1.5,
    "minecraft:diorite": 1.5,
    "minecraft:andesite": 1.5,
    "minecraft:stone_bricks": 1.5,
    "minecraft:sandstone": 0.8,
    "minecraft:red_sandstone": 0.8,
    "minecraft:netherrack": 0.4,
    "minecraft:basalt": 1.25,
    "minecraft:blackstone": 1.5,
    "minecraft:deepslate": 3.0,
    "minecraft:cobbled_deepslate": 3.5,
    # Medium (2.0-3.0)
    "minecraft:oak_planks": 2.0,
    "minecraft:spruce_planks": 2.0,
    "minecraft:birch_planks": 2.0,
    "minecraft:jungle_planks": 2.0,
    "minecraft:acacia_planks": 2.0,
    "minecraft:dark_oak_planks": 2.0,
    "minecraft:oak_log": 2.0,
    "minecraft:spruce_log": 2.0,
    "minecraft:birch_log": 2.0,
    "minecraft:jungle_log": 2.0,
    "minecraft:acacia_log": 2.0,
    "minecraft:dark_oak_log": 2.0,
    "minecraft:crimson_stem": 2.0,
    "minecraft:warped_stem": 2.0,
    "minecraft:crafting_table": 2.5,
    "minecraft:furnace": 3.5,
    "minecraft:blast_furnace": 3.5,
    "minecraft:smoker": 3.5,
    "minecraft:chest": 2.5,
    "minecraft:trapped_chest": 2.5,
    "minecraft:barrel": 2.5,
    "minecraft:bookshelf": 1.5,
    # Hard (3.0-5.0)
    "minecraft:iron_ore": 3.0,
    "minecraft:deepslate_iron_ore": 4.5,
    "minecraft:coal_ore": 3.0,
    "minecraft:deepslate_coal_ore": 4.5,
    "minecraft:copper_ore": 3.0,
    "minecraft:deepslate_copper_ore": 4.5,
    "minecraft:gold_ore": 3.0,
    "minecraft:deepslate_gold_ore": 4.5,
    "minecraft:redstone_ore": 3.0,
    "minecraft:deepslate_redstone_ore": 4.5,
    "minecraft:lapis_ore": 3.0,
    "minecraft:deepslate_lapis_ore": 4.5,
    "minecraft:iron_block": 5.0,
    "minecraft:gold_block": 3.0,
    "minecraft:copper_block": 3.0,
    "minecraft:bricks": 2.0,
    # Very hard (5.0+)
    "minecraft:diamond_ore": 3.0,
    "minecraft:deepslate_diamond_ore": 4.5,
    "minecraft:emerald_ore": 3.0,
    "minecraft:deepslate_emerald_ore": 4.5,
    "minecraft:diamond_block": 5.0,
    "minecraft:emerald_block": 5.0,
    "minecraft:nether_quartz_ore": 3.0,
    "minecraft:nether_gold_ore": 3.0,
    "minecraft:ancient_debris": 30.0,
    # Extremely hard
    "minecraft:obsidian": 50.0,
    "minecraft:crying_obsidian": 50.0,
    "minecraft:respawn_anchor": 50.0,
    "minecraft:ender_chest": 22.5,
    # Leaves (instant with hoe)
    "minecraft:oak_leaves": 0.2,
    "minecraft:spruce_leaves": 0.2,
    "minecraft:birch_leaves": 0.2,
    "minecraft:jungle_leaves": 0.2,
    "minecraft:acacia_leaves": 0.2,
    "minecraft:dark_oak_leaves": 0.2,
    # Glass (instant break)
    "minecraft:glass": 0.3,
    "minecraft:white_stained_glass": 0.3,
    "minecraft:glass_pane": 0.3,
    # Wool
    "minecraft:white_wool": 0.8,
    "minecraft:orange_wool": 0.8,
    # Ice
    "minecraft:ice": 0.5,
    "minecraft:packed_ice": 0.5,
    "minecraft:blue_ice": 2.8,
}

# Mining level required for blocks
BLOCK_MINING_LEVEL: Dict[str, int] = {
    "minecraft:iron_ore": ToolTier.STONE,
    "minecraft:deepslate_iron_ore": ToolTier.STONE,
    "minecraft:copper_ore": ToolTier.STONE,
    "minecraft:deepslate_copper_ore": ToolTier.STONE,
    "minecraft:coal_ore": ToolTier.WOOD,
    "minecraft:deepslate_coal_ore": ToolTier.WOOD,
    "minecraft:lapis_ore": ToolTier.STONE,
    "minecraft:deepslate_lapis_ore": ToolTier.STONE,
    "minecraft:gold_ore": ToolTier.IRON,
    "minecraft:deepslate_gold_ore": ToolTier.IRON,
    "minecraft:redstone_ore": ToolTier.IRON,
    "minecraft:deepslate_redstone_ore": ToolTier.IRON,
    "minecraft:diamond_ore": ToolTier.IRON,
    "minecraft:deepslate_diamond_ore": ToolTier.IRON,
    "minecraft:emerald_ore": ToolTier.IRON,
    "minecraft:deepslate_emerald_ore": ToolTier.IRON,
    "minecraft:gold_block": ToolTier.IRON,
    "minecraft:diamond_block": ToolTier.IRON,
    "minecraft:emerald_block": ToolTier.IRON,
    "minecraft:obsidian": ToolTier.DIAMOND,
    "minecraft:crying_obsidian": ToolTier.DIAMOND,
    "minecraft:respawn_anchor": ToolTier.DIAMOND,
    "minecraft:ancient_debris": ToolTier.DIAMOND,
}

# Tool speed multipliers
TOOL_SPEED: Dict[str, Dict[int, float]] = {
    "pickaxe": {
        ToolTier.WOOD: 2.0,
        ToolTier.GOLD: 12.0,
        ToolTier.STONE: 4.0,
        ToolTier.IRON: 6.0,
        ToolTier.DIAMOND: 8.0,
        ToolTier.NETHERITE: 9.0,
    },
    "axe": {
        ToolTier.WOOD: 2.0,
        ToolTier.GOLD: 12.0,
        ToolTier.STONE: 4.0,
        ToolTier.IRON: 6.0,
        ToolTier.DIAMOND: 8.0,
        ToolTier.NETHERITE: 9.0,
    },
    "shovel": {
        ToolTier.WOOD: 2.0,
        ToolTier.GOLD: 12.0,
        ToolTier.STONE: 4.0,
        ToolTier.IRON: 6.0,
        ToolTier.DIAMOND: 8.0,
        ToolTier.NETHERITE: 9.0,
    },
    "hoe": {
        ToolTier.WOOD: 1.0,
        ToolTier.GOLD: 1.0,
        ToolTier.STONE: 2.0,
        ToolTier.IRON: 3.0,
        ToolTier.DIAMOND: 4.0,
        ToolTier.NETHERITE: 5.0,
    },
}

# Which tool works best on which blocks
BLOCK_TOOL: Dict[str, str] = {
    "minecraft:stone": ToolType.PICKAXE,
    "minecraft:cobblestone": ToolType.PICKAXE,
    "minecraft:stone_bricks": ToolType.PICKAXE,
    "minecraft:iron_ore": ToolType.PICKAXE,
    "minecraft:deepslate_iron_ore": ToolType.PICKAXE,
    "minecraft:gold_ore": ToolType.PICKAXE,
    "minecraft:deepslate_gold_ore": ToolType.PICKAXE,
    "minecraft:diamond_ore": ToolType.PICKAXE,
    "minecraft:deepslate_diamond_ore": ToolType.PICKAXE,
    "minecraft:copper_ore": ToolType.PICKAXE,
    "minecraft:deepslate_copper_ore": ToolType.PICKAXE,
    "minecraft:coal_ore": ToolType.PICKAXE,
    "minecraft:deepslate_coal_ore": ToolType.PICKAXE,
    "minecraft:redstone_ore": ToolType.PICKAXE,
    "minecraft:deepslate_redstone_ore": ToolType.PICKAXE,
    "minecraft:emerald_ore": ToolType.PICKAXE,
    "minecraft:deepslate_emerald_ore": ToolType.PICKAXE,
    "minecraft:lapis_ore": ToolType.PICKAXE,
    "minecraft:deepslate_lapis_ore": ToolType.PICKAXE,
    "minecraft:obsidian": ToolType.PICKAXE,
    "minecraft:ancient_debris": ToolType.PICKAXE,
    "minecraft:netherrack": ToolType.PICKAXE,
    "minecraft:basalt": ToolType.PICKAXE,
    "minecraft:blackstone": ToolType.PICKAXE,
    "minecraft:deepslate": ToolType.PICKAXE,
    "minecraft:cobbled_deepslate": ToolType.PICKAXE,
    "minecraft:sandstone": ToolType.PICKAXE,
    "minecraft:red_sandstone": ToolType.PICKAXE,
    "minecraft:dirt": ToolType.SHOVEL,
    "minecraft:grass_block": ToolType.SHOVEL,
    "minecraft:sand": ToolType.SHOVEL,
    "minecraft:red_sand": ToolType.SHOVEL,
    "minecraft:gravel": ToolType.SHOVEL,
    "minecraft:clay": ToolType.SHOVEL,
    "minecraft:soul_sand": ToolType.SHOVEL,
    "minecraft:soul_soil": ToolType.SHOVEL,
    "minecraft:snow": ToolType.SHOVEL,
    "minecraft:snow_block": ToolType.SHOVEL,
    "minecraft:mycelium": ToolType.SHOVEL,
    "minecraft:podzol": ToolType.SHOVEL,
    "minecraft:farmland": ToolType.SHOVEL,
    "minecraft:dirt_path": ToolType.SHOVEL,
    "minecraft:oak_log": ToolType.AXE,
    "minecraft:spruce_log": ToolType.AXE,
    "minecraft:birch_log": ToolType.AXE,
    "minecraft:jungle_log": ToolType.AXE,
    "minecraft:acacia_log": ToolType.AXE,
    "minecraft:dark_oak_log": ToolType.AXE,
    "minecraft:crimson_stem": ToolType.AXE,
    "minecraft:warped_stem": ToolType.AXE,
    "minecraft:oak_planks": ToolType.AXE,
    "minecraft:spruce_planks": ToolType.AXE,
    "minecraft:birch_planks": ToolType.AXE,
    "minecraft:jungle_planks": ToolType.AXE,
    "minecraft:acacia_planks": ToolType.AXE,
    "minecraft:dark_oak_planks": ToolType.AXE,
    "minecraft:crafting_table": ToolType.AXE,
    "minecraft:chest": ToolType.AXE,
    "minecraft:bookshelf": ToolType.AXE,
    "minecraft:oak_leaves": ToolType.HOE,
    "minecraft:spruce_leaves": ToolType.HOE,
    "minecraft:birch_leaves": ToolType.HOE,
    "minecraft:jungle_leaves": ToolType.HOE,
    "minecraft:acacia_leaves": ToolType.HOE,
    "minecraft:dark_oak_leaves": ToolType.HOE,
}


@dataclass
class DigState:
    """Current digging state."""

    is_digging: bool = False
    target: Optional[Tuple[int, int, int]] = None
    start_time: float = 0.0
    end_time: float = 0.0
    progress: float = 0.0
    block: Optional[Any] = None


def get_block_hardness(block_name: str) -> float:
    """Get block hardness value. Default 1.0 if unknown."""
    return BLOCK_HARDNESS.get(block_name, 1.0)


def get_block_tool(block_name: str) -> Optional[str]:
    """Get the best tool type for a block."""
    return BLOCK_TOOL.get(block_name)


def get_block_mining_level(block_name: str) -> int:
    """Get minimum mining level required for block."""
    return BLOCK_MINING_LEVEL.get(block_name, -1)


def get_tool_tier(item_name: str) -> int:
    """Get tool tier from item name."""
    if not item_name:
        return -1

    item_name = item_name.lower()

    if "netherite" in item_name:
        return ToolTier.NETHERITE
    elif "diamond" in item_name:
        return ToolTier.DIAMOND
    elif "iron" in item_name:
        return ToolTier.IRON
    elif "stone" in item_name:
        return ToolTier.STONE
    elif "golden" in item_name or "gold" in item_name:
        return ToolTier.GOLD
    elif "wooden" in item_name or "wood" in item_name:
        return ToolTier.WOOD

    return -1


def get_tool_type(item_name: str) -> Optional[str]:
    """Get tool type from item name."""
    if not item_name:
        return None

    item_name = item_name.lower()

    if "pickaxe" in item_name:
        return ToolType.PICKAXE
    elif "axe" in item_name and "pickaxe" not in item_name:
        return ToolType.AXE
    elif "shovel" in item_name:
        return ToolType.SHOVEL
    elif "hoe" in item_name:
        return ToolType.HOE
    elif "sword" in item_name:
        return ToolType.SWORD

    return None


def get_tool_speed(tool_type: str, tool_tier: int) -> float:
    """Get tool speed multiplier."""
    if tool_type not in TOOL_SPEED:
        return 1.0
    return TOOL_SPEED[tool_type].get(tool_tier, 1.0)


def can_harvest(block_name: str, tool_name: Optional[str] = None) -> bool:
    """Check if a block can be harvested with the given tool."""
    required_level = get_block_mining_level(block_name)

    if required_level < 0:
        return True

    if not tool_name:
        return False

    tool_tier = get_tool_tier(tool_name)
    tool_type = get_tool_type(tool_name)

    required_tool = get_block_tool(block_name)
    if required_tool and tool_type != required_tool:
        return False

    return tool_tier >= required_level


def calculate_dig_time(
    block_name: str,
    tool_name: Optional[str] = None,
    efficiency: int = 0,
    haste: int = 0,
    underwater: bool = False,
    on_ground: bool = True,
    aqua_affinity: bool = False,
) -> float:
    """Calculate time to dig a block in milliseconds."""
    hardness = get_block_hardness(block_name)

    if hardness < 0:
        return float("inf")

    if hardness == 0:
        return 0.0

    time = hardness * 1.5

    can_harvest_block = can_harvest(block_name, tool_name)

    tool_type = get_tool_type(tool_name) if tool_name else None
    tool_tier = get_tool_tier(tool_name) if tool_name else -1

    if tool_type and tool_tier >= 0:
        block_tool = get_block_tool(block_name)

        if block_tool == tool_type:
            speed = get_tool_speed(tool_type, tool_tier)
            time /= speed

            if efficiency > 0 and can_harvest_block:
                time /= efficiency**2 + 1
        elif block_tool:
            time *= 5.0
        else:
            speed = get_tool_speed(tool_type, tool_tier)
            time /= speed
    else:
        if get_block_tool(block_name):
            time *= 5.0

    if not can_harvest_block:
        time *= 5.0

    if haste > 0:
        time *= 1.0 - 0.2 * haste

    if underwater and not aqua_affinity:
        time *= 5.0

    if not on_ground:
        time *= 5.0

    return time * 1000.0


def get_best_tool_for_block(block_name: str, available_tools: list) -> Optional[str]:
    """Find the best tool for mining a block."""
    required_tool = get_block_tool(block_name)
    required_level = get_block_mining_level(block_name)

    best_tool = None
    best_speed = 0

    for tool in available_tools:
        tool_type = get_tool_type(tool)
        tool_tier_val = get_tool_tier(tool)

        if required_tool and tool_type != required_tool:
            continue

        if tool_tier_val < required_level:
            continue

        speed = get_tool_speed(tool_type, tool_tier_val) if tool_type else 1

        if speed > best_speed:
            best_speed = speed
            best_tool = tool

    return best_tool
