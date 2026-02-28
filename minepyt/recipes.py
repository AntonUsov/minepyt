"""
Recipe system for Minecraft 1.21.4

Handles:
- Recipe types (crafting_shaped, crafting_shapeless, smelting, etc.)
- Recipe parsing from Declare Recipes packet (0x42)
- Recipe matching (finding recipes by ingredients)
- Auto-crafting support

Recipe types:
- minecraft:crafting_shaped    - Shaped crafting (3x3 grid)
- minecraft:crafting_shapeless - Shapeless crafting
- minecraft:smelting           - Furnace
- minecraft:blasting           - Blast furnace
- minecraft:smoking            - Smoker
- minecraft:campfire_cooking   - Campfire
- minecraft:stonecutting       - Stonecutter
- minecraft:smithing_transform - Smithing table
- minecraft:smithing_trim      - Armor trim
- minecraft:smithing_repair    - Equipment repair
- minecraft:special_*          - Special recipes (banners, etc.)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import IntEnum


class RecipeType(IntEnum):
    """Recipe type identifiers"""

    CRAFTING_SHAPED = 0
    CRAFTING_SHAPELESS = 1
    CRAFTING_SPECIAL_ARMORDYE = 2
    CRAFTING_SPECIAL_BOOKCLONING = 3
    CRAFTING_SPECIAL_MAPCLONING = 4
    CRAFTING_SPECIAL_MAPEXTENDING = 5
    CRAFTING_SPECIAL_FIREWORK_ROCKET = 6
    CRAFTING_SPECIAL_FIREWORK_STAR = 7
    CRAFTING_SPECIAL_FIREWORK_STAR_FADE = 8
    CRAFTING_SPECIAL_TIPPEDARROW = 9
    CRAFTING_SPECIAL_BANNERDUPLICATE = 10
    CRAFTING_SPECIAL_BANNERADDPATTERN = 11
    CRAFTING_SPECIAL_SHIELDDECORATION = 12
    CRAFTING_SPECIAL_SHULKERBOXCOLORING = 13
    CRAFTING_SPECIAL_SUSPICIOUSSTEW = 14
    CRAFTING_SPECIAL_REPAIRITEM = 15
    SMELTING = 16
    BLASTING = 17
    SMOKING = 18
    CAMPFIRE_COOKING = 19
    STONECUTTING = 20
    SMITHING_TRANSFORM = 21
    SMITHING_TRIM = 22
    SMITHING_REPAIR = 23
    CRAFTING_DECORATED_POT = 24


@dataclass
class Ingredient:
    """
    Recipe ingredient - can be an item, tag, or list of alternatives.

    Examples:
    - Item: {"item": "minecraft:oak_planks"}
    - Tag: {"tag": "minecraft:planks"}
    - Alternative: [{"item": "minecraft:oak_planks"}, {"item": "minecraft:birch_planks"}]
    """

    item: Optional[str] = None  # Exact item ID
    tag: Optional[str] = None  # Item tag (group of items)
    alternatives: Optional[List["Ingredient"]] = None  # Any of these
    count: int = 1

    def matches(self, item_id: str, tags: Optional[Set[str]] = None) -> bool:
        """
        Check if an item matches this ingredient.

        Args:
            item_id: Item ID to check
            tags: Set of tags the item belongs to

        Returns:
            True if item matches
        """
        # Direct item match
        if self.item and item_id == self.item:
            return True

        # Tag match
        if self.tag and tags and self.tag in tags:
            return True

        # Alternative match
        if self.alternatives:
            return any(alt.matches(item_id, tags) for alt in self.alternatives)

        return False

    def __repr__(self) -> str:
        if self.item:
            return f"Item({self.item})"
        if self.tag:
            return f"Tag({self.tag})"
        if self.alternatives:
            return f"Any({len(self.alternatives)})"
        return "Ingredient(empty)"


@dataclass
class RecipeResult:
    """Recipe output item"""

    item_id: str
    count: int = 1
    components: Optional[Dict] = None  # Item components

    def __repr__(self) -> str:
        if self.count > 1:
            return f"{self.item_id} x{self.count}"
        return self.item_id


@dataclass
class Recipe:
    """
    Base recipe class.

    Common fields:
    - id: Recipe identifier (e.g., "minecraft:oak_planks")
    - group: Recipe group for recipe book
    - category: Recipe book category
    - result: Output item
    """

    id: str
    recipe_type: str
    result: RecipeResult
    group: Optional[str] = None
    category: Optional[str] = None

    def can_craft(self, inventory: Dict[int, Any]) -> bool:
        """Check if recipe can be crafted with given inventory"""
        raise NotImplementedError


@dataclass
class ShapedRecipe(Recipe):
    """
    Shaped crafting recipe (3x3 grid).

    Example: oak_planks from oak_log
    Pattern: ["#"] where # = oak_log
    Result: 4 oak_planks
    """

    width: int = 1
    height: int = 1
    pattern: List[str] = field(default_factory=list)
    key: Dict[str, Ingredient] = field(default_factory=dict)
    ingredients: List[Ingredient] = field(default_factory=list)

    def can_craft(self, inventory: Dict[int, Any]) -> bool:
        """Check if recipe can be crafted"""
        # Count available items
        available = {}
        for item in inventory.values():
            if item and not item.is_empty:
                key = item.name
                available[key] = available.get(key, 0) + item.count

        # Check each ingredient
        needed = {}
        for ing in self.ingredients:
            if ing.item:
                needed[ing.item] = needed.get(ing.item, 0) + ing.count

        for item, count in needed.items():
            if available.get(item, 0) < count:
                return False

        return True

    def __repr__(self) -> str:
        return f"ShapedRecipe({self.id} -> {self.result})"


@dataclass
class ShapelessRecipe(Recipe):
    """
    Shapeless crafting recipe.

    Example: crafting_table from oak_planks
    Ingredients: 4 oak_planks (any position)
    Result: 1 crafting_table
    """

    ingredients: List[Ingredient] = field(default_factory=list)

    def can_craft(self, inventory: Dict[int, Any]) -> bool:
        """Check if recipe can be crafted"""
        available = {}
        for item in inventory.values():
            if item and not item.is_empty:
                key = item.name
                available[key] = available.get(key, 0) + item.count

        needed = {}
        for ing in self.ingredients:
            if ing.item:
                needed[ing.item] = needed.get(ing.item, 0) + ing.count

        for item, count in needed.items():
            if available.get(item, 0) < count:
                return False

        return True

    def __repr__(self) -> str:
        return f"ShapelessRecipe({self.id} -> {self.result})"


@dataclass
class SmeltingRecipe(Recipe):
    """
    Smelting recipe (furnace, blast furnace, smoker, campfire).

    Example: iron_ingot from iron_ore
    Ingredient: iron_ore
    Result: iron_ingot
    Experience: 0.7
    Cooking time: 200 ticks (10 seconds)
    """

    ingredient: Ingredient = field(default_factory=Ingredient)
    experience: float = 0.0
    cooking_time: int = 200  # Ticks

    def can_craft(self, inventory: Dict[int, Any]) -> bool:
        """Check if recipe can be smelted"""
        for item in inventory.values():
            if item and not item.is_empty:
                if self.ingredient.matches(item.name):
                    return True
        return False

    def __repr__(self) -> str:
        return f"SmeltingRecipe({self.id} -> {self.result})"


@dataclass
class StonecuttingRecipe(Recipe):
    """
    Stonecutting recipe.

    Example: stone_bricks from stone
    Ingredient: stone
    Result: stone_bricks
    """

    ingredient: Ingredient = field(default_factory=Ingredient)

    def can_craft(self, inventory: Dict[int, Any]) -> bool:
        for item in inventory.values():
            if item and not item.is_empty:
                if self.ingredient.matches(item.name):
                    return True
        return False

    def __repr__(self) -> str:
        return f"StonecuttingRecipe({self.id} -> {self.result})"


@dataclass
class SmithingRecipe(Recipe):
    """
    Smithing table recipe.

    Example: netherite_sword from diamond_sword
    Template: netherite_upgrade_smithing_template
    Base: diamond_sword
    Addition: netherite_ingot
    Result: netherite_sword
    """

    template: Optional[Ingredient] = None
    base: Optional[Ingredient] = None
    addition: Optional[Ingredient] = None

    def __repr__(self) -> str:
        return f"SmithingRecipe({self.id} -> {self.result})"


class RecipeRegistry:
    """
    Registry for all known recipes.

    Recipes are received from server via Declare Recipes packet (0x42).
    """

    def __init__(self):
        self.recipes: Dict[str, Recipe] = {}  # id -> Recipe
        self._by_output: Dict[str, List[Recipe]] = {}  # output_item -> [Recipe]
        self._by_type: Dict[str, List[Recipe]] = {}  # type -> [Recipe]

    def add(self, recipe: Recipe) -> None:
        """Add a recipe to the registry"""
        self.recipes[recipe.id] = recipe

        # Index by output
        output_id = recipe.result.item_id
        if output_id not in self._by_output:
            self._by_output[output_id] = []
        self._by_output[output_id].append(recipe)

        # Index by type
        recipe_type = recipe.recipe_type
        if recipe_type not in self._by_type:
            self._by_type[recipe_type] = []
        self._by_type[recipe_type].append(recipe)

    def get(self, recipe_id: str) -> Optional[Recipe]:
        """Get recipe by ID"""
        return self.recipes.get(recipe_id)

    def find_by_output(self, item_id: str) -> List[Recipe]:
        """Find all recipes that produce an item"""
        return self._by_output.get(item_id, [])

    def find_by_type(self, recipe_type: str) -> List[Recipe]:
        """Find all recipes of a type"""
        return self._by_type.get(recipe_type, [])

    def get_crafting_recipes(self) -> List[Recipe]:
        """Get all crafting recipes (shaped + shapeless)"""
        recipes = []
        recipes.extend(self._by_type.get("minecraft:crafting_shaped", []))
        recipes.extend(self._by_type.get("minecraft:crafting_shapeless", []))
        return recipes

    def get_smelting_recipes(self) -> List[Recipe]:
        """Get all smelting recipes"""
        recipes = []
        recipes.extend(self._by_type.get("minecraft:smelting", []))
        recipes.extend(self._by_type.get("minecraft:blasting", []))
        recipes.extend(self._by_type.get("minecraft:smoking", []))
        recipes.extend(self._by_type.get("minecraft:campfire_cooking", []))
        return recipes

    def __len__(self) -> int:
        return len(self.recipes)

    def __iter__(self):
        return iter(self.recipes.values())


class RecipeMatcher:
    """
    Matches available items to recipes.

    Finds recipes that can be crafted with current inventory.
    """

    def __init__(self, registry: RecipeRegistry):
        self.registry = registry

    def find_craftable(self, inventory: Dict[int, Any]) -> List[Recipe]:
        """
        Find all recipes that can be crafted with inventory.

        Args:
            inventory: Slot -> Item mapping

        Returns:
            List of craftable recipes
        """
        craftable = []
        for recipe in self.registry.get_crafting_recipes():
            if recipe.can_craft(inventory):
                craftable.append(recipe)
        return craftable

    def find_for_output(self, item_id: str, inventory: Dict[int, Any]) -> List[Recipe]:
        """
        Find recipes that produce a specific item and are craftable.

        Args:
            item_id: Desired output item
            inventory: Current inventory

        Returns:
            List of matching craftable recipes
        """
        recipes = self.registry.find_by_output(item_id)
        return [r for r in recipes if r.can_craft(inventory)]

    def get_missing_ingredients(
        self, recipe: Recipe, inventory: Dict[int, Any]
    ) -> List[Tuple[Ingredient, int]]:
        """
        Get ingredients missing to craft a recipe.

        Args:
            recipe: Recipe to check
            inventory: Current inventory

        Returns:
            List of (ingredient, missing_count) tuples
        """
        available = {}
        for item in inventory.values():
            if item and not item.is_empty:
                key = item.name
                available[key] = available.get(key, 0) + item.count

        missing = []

        # Get ingredients based on recipe type
        ingredients = []
        if isinstance(recipe, (ShapedRecipe, ShapelessRecipe)):
            ingredients = recipe.ingredients
        elif isinstance(recipe, SmeltingRecipe):
            ingredients = [recipe.ingredient]
        elif isinstance(recipe, StonecuttingRecipe):
            ingredients = [recipe.ingredient]

        for ing in ingredients:
            if ing.item:
                have = available.get(ing.item, 0)
                need = ing.count
                if have < need:
                    missing.append((ing, need - have))

        return missing

    def count_craftable(self, recipe: Recipe, inventory: Dict[int, Any]) -> int:
        """
        Count how many times a recipe can be crafted.

        Args:
            recipe: Recipe to check
            inventory: Current inventory

        Returns:
            Number of times craftable
        """
        available = {}
        for item in inventory.values():
            if item and not item.is_empty:
                key = item.name
                available[key] = available.get(key, 0) + item.count

        # Get ingredients
        ingredients = []
        if isinstance(recipe, (ShapedRecipe, ShapelessRecipe)):
            ingredients = recipe.ingredients
        elif isinstance(recipe, SmeltingRecipe):
            ingredients = [recipe.ingredient]
        elif isinstance(recipe, StonecuttingRecipe):
            ingredients = [recipe.ingredient]

        if not ingredients:
            return 0

        # Calculate max crafts per ingredient
        max_crafts = float("inf")
        for ing in ingredients:
            if ing.item and ing.count > 0:
                have = available.get(ing.item, 0)
                crafts = have // ing.count
                max_crafts = min(max_crafts, crafts)

        return max_crafts if max_crafts != float("inf") else 0


# Recipe parsing utilities


def parse_ingredient(data: bytes, offset: int) -> Tuple[Ingredient, int]:
    """
    Parse ingredient from Declare Recipes packet.

    Format:
    - VarInt: number of alternatives (0 = empty slot allowed)
    - For each alternative:
      - String: item ID
    """
    # Read number of alternatives
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    count = result

    if count == 0:
        return Ingredient(), offset

    if count == 1:
        # Single item
        item_id, offset = parse_string(data, offset)
        return Ingredient(item=item_id), offset

    # Multiple alternatives
    alternatives = []
    for _ in range(count):
        item_id, offset = parse_string(data, offset)
        alternatives.append(Ingredient(item=item_id))

    return Ingredient(alternatives=alternatives), offset


def parse_string(data: bytes, offset: int) -> Tuple[str, int]:
    """Parse length-prefixed string"""
    # Read varint length
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    length = result

    # Read string
    value = data[offset : offset + length].decode("utf-8")
    offset += length

    return value, offset


def parse_recipe_header(data: bytes, offset: int) -> Tuple[str, str, int]:
    """
    Parse recipe header (common fields).

    Returns:
        (recipe_id, recipe_type, new_offset)
    """
    recipe_id, offset = parse_string(data, offset)
    recipe_type, offset = parse_string(data, offset)

    return recipe_id, recipe_type, offset
