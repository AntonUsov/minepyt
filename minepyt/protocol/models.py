"""
Data models for Minecraft protocol
"""

# Import from parent - use try/except for both import styles
try:
    from minepyt.components import ItemComponents, Enchantment
except ImportError:
    from ..components import ItemComponents, Enchantment

from typing import Optional, List


GAME_MODE_NAMES = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}


def parse_game_mode(game_mode_bits: int) -> str:
    """Parse game mode from bits"""
    if game_mode_bits < 0 or game_mode_bits > 0b11:
        return "survival"
    return GAME_MODE_NAMES.get(game_mode_bits & 0b11, "survival")


class Game:
    """Represents the current game state"""

    def __init__(self):
        self.level_type: str = "default"
        self.hardcore: bool = False
        self.game_mode: str = "survival"
        self.dimension: str = "overworld"
        self.difficulty: str = "normal"
        self.max_players: int = 20
        self.server_view_distance: int = 10
        self.enable_respawn_screen: bool = True
        self.server_brand: Optional[str] = None
        self.min_y: int = 0
        self.height: int = 256
        self.time: int = 0
        self.age: int = 0

    def __repr__(self):
        return f"Game(mode={self.game_mode}, dim={self.dimension}, time={self.time})"


class Item:
    """
    Represents an item in inventory.

    Supports 1.21.4 item components including:
    - Enchantments
    - Attribute modifiers
    - Custom names and lore
    - Durability (damage)
    """

    def __init__(
        self,
        item_id: int = 0,
        count: int = 0,
        name: str = "",
        slot: int = -1,
        components: Optional[ItemComponents] = None,
    ):
        self.item_id: int = item_id  # 0 = empty
        self.count: int = count
        self.name: str = name or self._get_name_from_id(item_id)
        self.slot: int = slot
        self.components: Optional[ItemComponents] = components

    def _get_name_from_id(self, item_id: int) -> str:
        """Get item name from ID (simplified mapping)"""
        item_names = {
            1: "minecraft:stone",
            4: "minecraft:cobblestone",
            5: "minecraft:oak_planks",
            14: "minecraft:oak_log",
            17: "minecraft:oak_sapling",
            24: "minecraft:stick",
            25: "minecraft:crafting_table",
            31: "minecraft:oak_stick",
            34: "minecraft:iron_ingot",
            35: "minecraft:gold_ingot",
            45: "minecraft:diamond",
            265: "minecraft:iron_pickaxe",
            266: "minecraft:iron_sword",
            267: "minecraft:iron_shovel",
            268: "minecraft:iron_axe",
            280: "minecraft:oak_boat",
            296: "minecraft:planks",
            325: "minecraft:coal",
            326: "minecraft:charcoal",
            356: "minecraft:oak_chest_boat",
        }
        return item_names.get(item_id, f"minecraft:item_{item_id}")

    @property
    def is_empty(self) -> bool:
        return self.item_id == 0 or self.count == 0

    @property
    def has_enchantments(self) -> bool:
        """Check if item has enchantments"""
        return self.components is not None and len(self.components.enchantments) > 0

    @property
    def enchantments(self) -> List[Enchantment]:
        """Get enchantments list"""
        if self.components:
            return self.components.enchantments
        return []

    @property
    def damage(self) -> int:
        """Get current damage (durability used)"""
        if self.components:
            return self.components.damage or 0
        return 0

    @property
    def max_damage(self) -> int:
        """Get max damage (durability)"""
        if self.components:
            return self.components.max_damage or 0
        return 0

    @property
    def durability(self) -> int:
        """Get remaining durability"""
        return max(0, self.max_damage - self.damage)

    @property
    def custom_name(self) -> str:
        """Get custom name if set"""
        if self.components and self.components.custom_name:
            return self.components.custom_name.to_plain_text()
        return ""

    def get_enchantment_level(self, ench_id: str) -> int:
        """Get level of specific enchantment"""
        if self.components:
            return self.components.get_enchantment_level(ench_id)
        return 0

    def __repr__(self) -> str:
        if self.is_empty:
            return "Item(empty)"
        parts = [self.name, f"x{self.count}"]
        if self.slot >= 0:
            parts.append(f"slot={self.slot}")
        if self.has_enchantments:
            parts.append(f"enchants={len(self.enchantments)}")
        return f"Item({', '.join(parts)})"

    def __str__(self) -> str:
        if self.is_empty:
            return "empty"
        return f"{self.name} x{self.count}"


__all__ = ["Game", "Item", "parse_game_mode", "GAME_MODE_NAMES"]
