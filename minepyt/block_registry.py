"""
Block registry - maps block state IDs to names
Simplified version with common blocks
"""

from typing import Dict, Optional


# Common block state IDs (these vary by version, these are approximate for 1.21.x)
# A full implementation would load these from the server's registry
BLOCK_NAMES: Dict[int, str] = {
    0: "air",
    1: "stone",
    2: "granite",
    3: "polished_granite",
    4: "diorite",
    5: "polished_diorite",
    6: "andesite",
    7: "polished_andesite",
    8: "deepslate",
    9: "cobbled_deepslate",
    10: "polished_deepslate",
    11: "calcite",
    12: "tuff",
    13: "dripstone_block",
    14: "grass_block",
    15: "dirt",
    16: "coarse_dirt",
    17: "podzol",
    18: "rooted_dirt",
    19: "mud",
    20: "cobblestone",
    21: "oak_planks",
    22: "spruce_planks",
    23: "birch_planks",
    24: "jungle_planks",
    25: "acacia_planks",
    26: "dark_oak_planks",
    27: "mangrove_planks",
    28: "cherry_planks",
    29: "bamboo_planks",
    30: "oak_sapling",
    31: "spruce_sapling",
    32: "birch_sapling",
    33: "jungle_sapling",
    34: "acacia_sapling",
    35: "dark_oak_sapling",
    36: "mangrove_propagule",
    37: "cherry_sapling",
    38: "bedrock",
    39: "water",
    40: "lava",
    41: "sand",
    42: "red_sand",
    43: "gravel",
    44: "gold_ore",
    45: "deepslate_gold_ore",
    46: "iron_ore",
    47: "deepslate_iron_ore",
    48: "coal_ore",
    49: "deepslate_coal_ore",
    50: "nether_gold_ore",
    51: "oak_log",
    52: "spruce_log",
    53: "birch_log",
    54: "jungle_log",
    55: "acacia_log",
    56: "dark_oak_log",
    57: "mangrove_log",
    58: "cherry_log",
    59: "stripped_oak_log",
    60: "glass",
    61: "lapis_ore",
    62: "deepslate_lapis_ore",
    63: "lapis_block",
    64: "dispenser",
    65: "sandstone",
    66: "chiseled_sandstone",
    67: "cut_sandstone",
    68: "note_block",
    69: "powered_rail",
    70: "detector_rail",
    71: "sticky_piston",
    72: "cobweb",
    73: "grass",
    74: "fern",
    75: "dead_bush",
    76: "seagrass",
    77: "sea_pickle",
    78: "piston",
    79: "piston_head",
    80: "white_wool",
    81: "orange_wool",
    82: "magenta_wool",
    83: "light_blue_wool",
    84: "yellow_wool",
    85: "lime_wool",
    86: "pink_wool",
    87: "gray_wool",
    88: "light_gray_wool",
    89: "cyan_wool",
    90: "purple_wool",
    91: "blue_wool",
    92: "brown_wool",
    93: "green_wool",
    94: "red_wool",
    95: "black_wool",
    96: "dandelion",
    97: "poppy",
    98: "blue_orchid",
    99: "allium",
    100: "azure_bluet",
    101: "red_tulip",
    102: "orange_tulip",
    103: "white_tulip",
    104: "pink_tulip",
    105: "oxeye_daisy",
    106: "cornflower",
    107: "lily_of_the_valley",
    108: "wither_rose",
    109: "torch",
    110: "wall_torch",
    111: "soul_torch",
    112: "soul_wall_torch",
    113: "crafting_table",
    114: "oak_fence",
    115: "spruce_fence",
    116: "birch_fence",
    117: "jungle_fence",
    118: "acacia_fence",
    119: "dark_oak_fence",
    120: "mangrove_fence",
    121: "cherry_fence",
    122: "oak_fence_gate",
    123: "spruce_fence_gate",
    124: "birch_fence_gate",
    125: "jungle_fence_gate",
    126: "acacia_fence_gate",
    127: "dark_oak_fence_gate",
    128: "furnace",
    129: "oak_door",
    130: "ladder",
    131: "rail",
    132: "cobblestone_stairs",
    133: "oak_stairs",
    134: "spruce_stairs",
    135: "birch_stairs",
    136: "jungle_stairs",
    137: "acacia_stairs",
    138: "dark_oak_stairs",
    139: "mangrove_stairs",
    140: "cherry_stairs",
    141: "chest",
    142: "diamond_ore",
    143: "deepslate_diamond_ore",
    144: "diamond_block",
    145: "crafting_table",
    146: "farmland",
    147: "furnace",
    148: "oak_sign",
    149: "spruce_sign",
    150: "birch_sign",
    151: "oak_door",
    152: "ladder",
    153: "rail",
    154: "cobblestone_stairs",
    155: "lever",
    156: "stone_pressure_plate",
    157: "oak_pressure_plate",
    158: "spruce_pressure_plate",
    159: "birch_pressure_plate",
    160: "jungle_pressure_plate",
    161: "acacia_pressure_plate",
    162: "dark_oak_pressure_plate",
    163: "mangrove_pressure_plate",
    164: "cherry_pressure_plate",
    165: "redstone_ore",
    166: "deepslate_redstone_ore",
    167: "redstone_torch",
    168: "redstone_wall_torch",
    169: "stone_button",
    170: "snow",
    171: "ice",
    172: "snow_block",
    173: "cactus",
    174: "clay",
    175: "jukebox",
    176: "oak_trapdoor",
    177: "spruce_trapdoor",
    178: "birch_trapdoor",
    179: "jungle_trapdoor",
    180: "acacia_trapdoor",
    181: "dark_oak_trapdoor",
    182: "mangrove_trapdoor",
    183: "cherry_trapdoor",
    184: "infested_stone",
    185: "infested_cobblestone",
    186: "infested_stone_bricks",
    187: "infested_mossy_stone_bricks",
    188: "infested_cracked_stone_bricks",
    189: "infested_chiseled_stone_bricks",
    190: "infested_deepslate",
    191: "stone_bricks",
    192: "mossy_stone_bricks",
    193: "cracked_stone_bricks",
    194: "chiseled_stone_bricks",
    195: "quartz_block",
    196: "smooth_quartz",
    197: "quartz_pillar",
    198: "chiseled_quartz_block",
    199: "tnt",
    200: "bookshelf",
    201: "mossy_cobblestone",
    202: "obsidian",
    203: "torch",
    204: "end_portal_frame",
    205: "end_stone",
    206: "dragon_egg",
    207: "spawner",
    208: "oak_stairs",
    209: "chest",
    210: "diamond_block",
    211: "netherrack",
    212: "soul_sand",
    213: "soul_soil",
    214: "basalt",
    215: "polished_basalt",
    216: "glowstone",
    217: "nether_portal",
    218: "carved_pumpkin",
    219: "jack_o_lantern",
    220: "cake",
    221: "repeater",
    222: "comparator",
    223: "composter",
    224: "target",
    225: "bee_nest",
    226: "beehive",
    227: "honey_block",
    228: "honeycomb_block",
    229: "lodestone",
    230: "netherite_block",
    231: "ancient_debris",
    232: "crying_obsidian",
    233: "blackstone",
    234: "basalt",
    235: "polished_basalt",
    236: "polished_blackstone",
    237: "chiseled_polished_blackstone",
    238: "polished_blackstone_bricks",
    239: "cracked_polished_blackstone_bricks",
    240: "gilded_blackstone",
    241: "amethyst_block",
    242: "budding_amethyst",
    243: "small_amethyst_bud",
    244: "medium_amethyst_bud",
    245: "large_amethyst_bud",
    246: "amethyst_cluster",
    247: "tuff",
    248: "calcite",
    249: "oxidized_copper",
    250: "weathered_copper",
    251: "exposed_copper",
    252: "copper_block",
    253: "cut_copper",
    254: "sculk",
    255: "sculk_sensor",
}

# Reverse mapping for lookups
_NAME_TO_ID: Dict[str, int] = {v: k for k, v in BLOCK_NAMES.items()}


def get_block_name(state_id: int) -> str:
    """
    Get block name from state ID.

    Args:
        state_id: Block state ID

    Returns:
        Block name (e.g., "stone", "dirt", "air")
    """
    return BLOCK_NAMES.get(state_id, f"unknown_{state_id}")


def get_block_id(name: str) -> Optional[int]:
    """
    Get block state ID from name.

    Args:
        name: Block name (e.g., "stone", "dirt")

    Returns:
        Block state ID or None if not found
    """
    return _NAME_TO_ID.get(name)


def is_air(state_id: int) -> bool:
    """Check if block is air"""
    return state_id == 0 or state_id in (39, 40)  # air, water, lava


def is_solid(state_id: int) -> bool:
    """Check if block is solid (simplified)"""
    return state_id not in (0, 39, 40, 72)  # not air, water, lava, cobweb


def is_transparent(state_id: int) -> bool:
    """Check if block is transparent (simplified)"""
    return state_id in (
        0,
        39,
        40,
        60,
        109,
        110,
        111,
        112,
    )  # air, water, lava, glass, torches


# Block class for convenient block info access
class Block:
    """Represents a block with its properties"""

    def __init__(self, state_id: int, position: tuple = None):
        self.state_id = state_id
        self.name = get_block_name(state_id)
        self.position = position or (0, 0, 0)

    @property
    def is_air(self) -> bool:
        return is_air(self.state_id)

    @property
    def is_solid(self) -> bool:
        return is_solid(self.state_id)

    @property
    def is_transparent(self) -> bool:
        return is_transparent(self.state_id)

    def __repr__(self) -> str:
        return f"Block({self.name}, pos={self.position})"

    def __str__(self) -> str:
        return self.name
