"""
Test 10: NBT, Components, and Recipes

Tests:
- NBT parsing (all tag types)
- Item components (enchantments, attributes, etc.)
- Recipe system (registry, matching)
"""

import asyncio
import sys

sys.path.insert(0, ".")

from minepyt.nbt import (
    NbtCompound,
    NbtByte,
    NbtShort,
    NbtInt,
    NbtLong,
    NbtFloat,
    NbtDouble,
    NbtString,
    NbtList,
    NbtReader,
    TagType,
    parse_nbt,
)
from minepyt.components import (
    ItemComponents,
    Enchantment,
    AttributeModifier,
    TextComponent,
    ComponentType,
)
from minepyt.recipes import (
    RecipeRegistry,
    RecipeMatcher,
    Recipe,
    ShapedRecipe,
    ShapelessRecipe,
    SmeltingRecipe,
    Ingredient,
    RecipeResult,
)


def test_nbt():
    """Test NBT parsing"""
    print("=" * 60)
    print("TEST 10.1: NBT Parser")
    print("=" * 60)

    results = {}

    # Test tag types
    print("\n[1/5] Testing NBT tag types...")

    byte_tag = NbtByte(value=127)
    assert byte_tag.as_value() == 127
    print("  [OK] NbtByte")

    int_tag = NbtInt(value=12345)
    assert int_tag.as_value() == 12345
    print("  [OK] NbtInt")

    string_tag = NbtString(value="Hello")
    assert string_tag.as_value() == "Hello"
    print("  [OK] NbtString")

    # Test compound
    print("\n[2/5] Testing NbtCompound...")

    compound = NbtCompound(
        tags={
            "name": NbtString(value="test"),
            "count": NbtInt(value=10),
            "active": NbtByte(value=1),
        }
    )

    assert compound.get_string("name") == "test"
    assert compound.get_int("count") == 10
    assert compound.get_byte("active") == 1
    print("  [OK] NbtCompound get methods")

    # Test list
    print("\n[3/5] Testing NbtList...")

    list_tag = NbtList(
        value=[NbtString(value="a"), NbtString(value="b"), NbtString(value="c")]
    )

    assert len(list_tag) == 3
    assert list_tag[0].as_value() == "a"
    print("  [OK] NbtList")

    # Test nested compound
    print("\n[4/5] Testing nested structures...")

    nested = NbtCompound(
        tags={
            "display": NbtCompound(
                tags={
                    "Name": NbtString(value="Custom Item"),
                    "Lore": NbtList(
                        value=[NbtString(value="Line 1"), NbtString(value="Line 2")]
                    ),
                }
            ),
            "Damage": NbtInt(value=100),
        }
    )

    display = nested.get_compound("display")
    assert display is not None
    assert display.get_string("Name") == "Custom Item"
    print("  [OK] Nested compounds")

    # Test binary parsing
    print("\n[5/5] Testing binary parsing...")

    # Create simple NBT data
    # TAG_Compound("test"): { TAG_String("hello"): "world" }
    nbt_data = bytes(
        [
            0x0A,  # TAG_Compound
            0x00,
            0x04,  # Name length
            ord("t"),
            ord("e"),
            ord("s"),
            ord("t"),  # Name "test"
            0x08,  # TAG_String
            0x00,
            0x05,  # Name length
            ord("h"),
            ord("e"),
            ord("l"),
            ord("l"),
            ord("o"),  # Name "hello"
            0x00,
            0x05,  # Value length
            ord("w"),
            ord("o"),
            ord("r"),
            ord("l"),
            ord("d"),  # Value "world"
            0x00,  # TAG_End
        ]
    )

    reader = NbtReader(nbt_data)
    parsed = reader.read_root()

    assert "hello" in parsed
    assert parsed.get_string("hello") == "world"
    print("  [OK] Binary parsing")

    print("\n" + "-" * 40)
    print("[PASS] NBT Parser - ALL CHECKS PASSED")
    return True


def test_components():
    """Test item components"""
    print("\n" + "=" * 60)
    print("TEST 10.2: Item Components")
    print("=" * 60)

    # Test component types
    print("\n[1/5] Testing ComponentType enum...")

    assert ComponentType.CUSTOM_NAME == 5
    assert ComponentType.ENCHANTMENTS == 9
    assert ComponentType.LORE == 7
    print("  [OK] ComponentType enum")

    # Test Enchantment
    print("\n[2/5] Testing Enchantment class...")

    ench = Enchantment(id="minecraft:sharpness", level=5)
    assert ench.id == "minecraft:sharpness"
    assert ench.level == 5
    print(f"  [OK] Enchantment: {ench}")

    # Test TextComponent
    print("\n[3/5] Testing TextComponent class...")

    text = TextComponent(text="Hello", color="red", bold=True)
    assert text.to_plain_text() == "Hello"
    print(f"  [OK] TextComponent: {text.to_plain_text()}")

    # Test ItemComponents
    print("\n[4/5] Testing ItemComponents class...")

    components = ItemComponents(
        max_stack_size=64,
        damage=100,
        max_damage=500,
        enchantments=[
            Enchantment(id="minecraft:sharpness", level=5),
            Enchantment(id="minecraft:unbreaking", level=3),
        ],
    )

    assert components.max_stack_size == 64
    assert components.damage == 100
    assert len(components.enchantments) == 2
    assert components.has_enchantment("minecraft:sharpness")
    assert components.get_enchantment_level("minecraft:sharpness") == 5
    assert not components.has_enchantment("minecraft:protection")
    print(f"  [OK] ItemComponents: {components}")

    # Test durability
    print("\n[5/5] Testing durability calculation...")

    assert components.durability == 400  # 500 - 100
    print(f"  [OK] Durability: {components.durability}/{components.max_damage}")

    print("\n" + "-" * 40)
    print("[PASS] Item Components - ALL CHECKS PASSED")
    return True


def test_recipes():
    """Test recipe system"""
    print("\n" + "=" * 60)
    print("TEST 10.3: Recipe System")
    print("=" * 60)

    # Test Ingredient
    print("\n[1/5] Testing Ingredient class...")

    ing1 = Ingredient(item="minecraft:oak_planks")
    assert ing1.matches("minecraft:oak_planks")
    assert not ing1.matches("minecraft:stone")
    print("  [OK] Ingredient with item")

    ing2 = Ingredient(
        alternatives=[
            Ingredient(item="minecraft:oak_planks"),
            Ingredient(item="minecraft:birch_planks"),
        ]
    )
    assert ing2.matches("minecraft:oak_planks")
    assert ing2.matches("minecraft:birch_planks")
    print("  [OK] Ingredient with alternatives")

    # Test RecipeResult
    print("\n[2/5] Testing RecipeResult class...")

    result = RecipeResult(item_id="minecraft:crafting_table", count=1)
    assert result.item_id == "minecraft:crafting_table"
    print(f"  [OK] RecipeResult: {result}")

    # Test ShapedRecipe
    print("\n[3/5] Testing ShapedRecipe class...")

    shaped = ShapedRecipe(
        id="minecraft:crafting_table",
        recipe_type="minecraft:crafting_shaped",
        result=RecipeResult(item_id="minecraft:crafting_table", count=1),
        width=2,
        height=2,
        ingredients=[
            Ingredient(item="minecraft:oak_planks"),
            Ingredient(item="minecraft:oak_planks"),
            Ingredient(item="minecraft:oak_planks"),
            Ingredient(item="minecraft:oak_planks"),
        ],
    )
    print(f"  [OK] ShapedRecipe: {shaped}")

    # Test ShapelessRecipe
    print("\n[4/5] Testing ShapelessRecipe class...")

    shapeless = ShapelessRecipe(
        id="minecraft:stick",
        recipe_type="minecraft:crafting_shapeless",
        result=RecipeResult(item_id="minecraft:stick", count=4),
        ingredients=[
            Ingredient(item="minecraft:oak_planks"),
            Ingredient(item="minecraft:oak_planks"),
        ],
    )
    print(f"  [OK] ShapelessRecipe: {shapeless}")

    # Test RecipeRegistry
    print("\n[5/5] Testing RecipeRegistry and RecipeMatcher...")

    registry = RecipeRegistry()
    registry.add(shaped)
    registry.add(shapeless)

    assert len(registry) == 2
    assert registry.get("minecraft:crafting_table") is not None
    assert len(registry.find_by_output("minecraft:stick")) == 1
    print(f"  [OK] RecipeRegistry: {len(registry)} recipes")

    # Test RecipeMatcher
    matcher = RecipeMatcher(registry)

    # Mock inventory with oak_planks
    class MockItem:
        def __init__(self, name, count):
            self.name = name
            self.count = count
            self.is_empty = count == 0

    inventory = {
        0: MockItem("minecraft:oak_planks", 64),
    }

    craftable = matcher.find_craftable(inventory)
    assert len(craftable) >= 1
    print(f"  [OK] RecipeMatcher: {len(craftable)} craftable recipes")

    print("\n" + "-" * 40)
    print("[PASS] Recipe System - ALL CHECKS PASSED")
    return True


async def test_integration():
    """Test integration with bot"""
    print("\n" + "=" * 60)
    print("TEST 10.4: Integration with Bot")
    print("=" * 60)

    from minepyt.protocol import create_bot

    print("\n[1/3] Creating bot...")

    bot = await create_bot(
        {
            "host": "localhost",
            "port": 25565,
            "username": f"ComponentTester_{int(asyncio.get_event_loop().time()) % 10000}",
        }
    )

    await asyncio.sleep(3)

    # Check recipe registry
    print("\n[2/3] Checking recipe registry...")

    if hasattr(bot, "recipes") and bot.recipes is not None:
        print(f"  [OK] RecipeRegistry: {len(bot.recipes)} recipes")
    else:
        print("  [WARN] RecipeRegistry not initialized")

    # Check recipe matcher
    if hasattr(bot, "recipe_matcher") and bot.recipe_matcher is not None:
        print(f"  [OK] RecipeMatcher available")
    else:
        print("  [WARN] RecipeMatcher not initialized")

    # Check item components
    print("\n[3/3] Checking item component support...")

    from minepyt.protocol import Item
    from minepyt.components import ItemComponents

    test_item = Item(
        item_id=1,
        count=1,
        name="minecraft:stone",
        components=ItemComponents(max_stack_size=64),
    )

    assert test_item.components is not None
    assert test_item.components.max_stack_size == 64
    print(f"  [OK] Item with components: {test_item}")

    print("\n" + "-" * 40)
    print("[PASS] Integration - ALL CHECKS PASSED")

    await bot.disconnect()
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("TEST 10: NBT, Components, and Recipes")
    print("=" * 60)

    all_passed = True

    # Run unit tests
    try:
        if not test_nbt():
            all_passed = False
    except Exception as e:
        print(f"[FAIL] NBT test error: {e}")
        all_passed = False

    try:
        if not test_components():
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Components test error: {e}")
        all_passed = False

    try:
        if not test_recipes():
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Recipes test error: {e}")
        all_passed = False

    # Run integration test
    try:
        if not asyncio.run(test_integration()):
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Integration test error: {e}")
        all_passed = False

    # Final verdict
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] TEST 10: ALL CHECKS PASSED")
    else:
        print("[FAIL] TEST 10: SOME CHECKS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
