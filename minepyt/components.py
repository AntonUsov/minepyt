"""
Item Components for Minecraft 1.21.4

In 1.20.5+, Minecraft replaced item NBT with Data Components.
Each component is a typed data structure attached to an item.

Component format in slots:
- VarInt: number of components added
- VarInt: number of components removed
- For each added component:
  - VarInt: component type ID
  - Component-specific data
- For each removed component:
  - VarInt: component type ID

Common components:
- custom_name: Text component for custom name
- lore: List of text components
- enchantments: List of enchantments
- attribute_modifiers: List of attribute modifiers
- unbreakable: Boolean
- damage: Integer
- max_damage: Integer
- rarity: Enum
- hide_tooltip: Boolean
- etc.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import IntEnum

from .nbt import NbtCompound, NbtReader, parse_nbt


class ComponentType(IntEnum):
    """Data component types for 1.21.4 (partial list)"""

    # Core
    CUSTOM_DATA = 0  # NBT compound
    MAX_STACK_SIZE = 1  # VarInt
    MAX_DAMAGE = 2  # VarInt
    DAMAGE = 3  # VarInt
    UNBREAKABLE = 4  # Boolean + optional boolean show_in_tooltip

    # Appearance
    CUSTOM_NAME = 5  # Text component
    ITEM_NAME = 6  # Text component
    LORE = 7  # List of text components
    RARITY = 8  # Enum (common, uncommon, rare, epic)
    ENCHANTMENTS = 9  # Enchantment list
    CAN_PLACE_ON = 10  # Block predicate list
    CAN_BREAK = 11  # Block predicate list
    ATTRIBUTE_MODIFIERS = 12  # Attribute modifier list
    CUSTOM_MODEL_DATA = 13  # Int

    # Effects
    POTION_CONTENTS = 14  # Potion data
    SUSPICIOUS_STEW = 15  # Effect list
    WRITTEN_BOOK = 16  # Book data
    WRITABLE_BOOK = 17  # Book pages
    MAP_ID = 18  # Int

    # Tools
    TOOL = 19  # Tool data
    WEAPON = 20  # Weapon data
    FOOD = 21  # Food data
    JUKEBOX_PLAYABLE = 22  # Jukebox song

    # Misc
    HIDE_TOOLTIP = 23  # Boolean
    HIDE_ADDITIONAL_TOOLTIP = 24
    HIDE_ARMOR_TRIM = 25
    HIDE_DYE = 26
    FIRE_RESISTANT = 27
    GLIDER = 28
    ENCHANTMENT_GLINT_OVERRIDE = 29
    CREATIVE_SLOT_LOCK = 30

    # Blocks
    BLOCK_STATE = 31  # Block state properties
    BUCKET_ENTITY_DATA = 32
    BLOCK_ENTITY_DATA = 33

    # Entities
    ENTITY_DATA = 34
    BEE_ENTITY_DATA = 35
    PROFILE = 36
    MAP_DECORATIONS = 37

    # Armor
    TRIM = 38  # Armor trim
    DYED_COLOR = 39  # Color int

    # Debug
    DEBUG_STICK_STATE = 40
    RECIPES = 41
    LODESTONE_TRACKER = 42
    FIREWORKS = 43
    FIREWORK_EXPLOSION = 44

    # Banners
    BANNER_PATTERNS = 45
    BANNER_BASE_COLOR = 46

    # Potions
    POTION_DURATION_SCALE = 47

    # Bundles
    BUNDLE_CONTENTS = 48

    # Locks
    LOCK = 49
    CONTAINER_LOOT = 50
    CONTAINER = 51


@dataclass
class TextComponent:
    """Minecraft text component"""

    text: str = ""
    color: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underlined: Optional[bool] = None
    strikethrough: Optional[bool] = None
    obfuscated: Optional[bool] = None
    extra: Optional[List["TextComponent"]] = None

    def to_plain_text(self) -> str:
        """Get plain text without formatting"""
        result = self.text
        if self.extra:
            for extra in self.extra:
                result += extra.to_plain_text()
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "TextComponent":
        """Create from JSON dict"""
        return cls(
            text=data.get("text", ""),
            color=data.get("color"),
            bold=data.get("bold"),
            italic=data.get("italic"),
            underlined=data.get("underlined"),
            strikethrough=data.get("strikethrough"),
            obfuscated=data.get("obfuscated"),
            extra=[cls.from_dict(e) for e in data.get("extra", [])]
            if "extra" in data
            else None,
        )


@dataclass
class Enchantment:
    """Enchantment data"""

    id: str  # e.g., "minecraft:sharpness"
    level: int

    def __repr__(self) -> str:
        return f"Enchantment({self.id}, lvl={self.level})"


@dataclass
class AttributeModifier:
    """Attribute modifier data"""

    attribute: str  # e.g., "minecraft:generic.attack_damage"
    name: str
    amount: float
    operation: int  # 0=add, 1=multiply_base, 2=multiply_total
    slot: Optional[str] = None  # e.g., "mainhand", "head", etc.

    def __repr__(self) -> str:
        return f"AttributeModifier({self.attribute}, {self.amount})"


@dataclass
class ItemComponents:
    """
    Container for item data components (1.21.4).

    This replaces the old NBT-based item data system.
    """

    # Core
    custom_data: Optional[NbtCompound] = None
    max_stack_size: int = 64
    max_damage: Optional[int] = None
    damage: Optional[int] = None
    unbreakable: bool = False

    # Appearance
    custom_name: Optional[TextComponent] = None
    item_name: Optional[TextComponent] = None
    lore: Optional[List[TextComponent]] = None
    rarity: Optional[str] = None

    # Enchantments
    enchantments: List[Enchantment] = field(default_factory=list)

    # Predicates
    can_place_on: Optional[List[str]] = None
    can_break: Optional[List[str]] = None

    # Attributes
    attribute_modifiers: List[AttributeModifier] = field(default_factory=list)

    # Misc
    custom_model_data: Optional[int] = None
    hide_tooltip: bool = False
    hide_additional_tooltip: bool = False
    fire_resistant: bool = False
    glider: bool = False

    # Type-specific
    food: Optional[Dict] = None
    tool: Optional[Dict] = None
    potion_contents: Optional[Dict] = None
    written_book: Optional[Dict] = None

    # Raw storage for unknown components
    _raw: Dict[int, Any] = field(default_factory=dict)

    def has_enchantment(self, ench_id: str) -> bool:
        """Check if item has specific enchantment"""
        return any(e.id == ench_id for e in self.enchantments)

    def get_enchantment_level(self, ench_id: str) -> int:
        """Get level of specific enchantment, 0 if not present"""
        for e in self.enchantments:
            if e.id == ench_id:
                return e.level
        return 0

    def get_display_name(self) -> str:
        """Get display name (custom or empty)"""
        if self.custom_name:
            return self.custom_name.to_plain_text()
        return ""

    def get_lore_lines(self) -> List[str]:
        """Get lore as plain text lines"""
        if not self.lore:
            return []
        return [line.to_plain_text() for line in self.lore]
    
    @property
    def durability(self) -> int:
        """Get remaining durability (max_damage - damage)"""
        if self.max_damage is None or self.damage is None:
            return 0
        return max(0, self.max_damage - self.damage)

    def __repr__(self) -> str:
        parts = []
        if self.enchantments:
            parts.append(f"enchants={len(self.enchantments)}")
        if self.custom_name:
            parts.append(f"name='{self.get_display_name()}'")
        if self.damage is not None:
            parts.append(f"damage={self.damage}")
        if self.unbreakable:
            parts.append("unbreakable")

        if parts:
            return f"ItemComponents({', '.join(parts)})"
        return "ItemComponents()"


class ComponentReader:
    """Reader for item components from buffer"""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read_byte(self) -> int:
        value = self.data[self.offset]
        self.offset += 1
        return value

    def read_varint(self) -> int:
        """Read varint"""
        result = 0
        shift = 0
        while True:
            if self.offset >= len(self.data):
                raise ValueError("Unexpected end of data")
            byte = self.data[self.offset]
            self.offset += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result

    def read_string(self) -> str:
        """Read length-prefixed UTF-8 string"""
        length = self.read_varint()
        value = self.data[self.offset : self.offset + length].decode("utf-8")
        self.offset += length
        return value

    def read_int(self) -> int:
        """Read big-endian int"""
        value = struct.unpack(">i", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def read_float(self) -> float:
        """Read big-endian float"""
        value = struct.unpack(">f", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def read_double(self) -> float:
        """Read big-endian double"""
        value = struct.unpack(">d", self.data[self.offset : self.offset + 8])[0]
        self.offset += 8
        return value

    def read_boolean(self) -> bool:
        return self.read_byte() != 0

    def read_text_component(self) -> TextComponent:
        """Read text component from JSON string"""
        import json

        json_str = self.read_string()
        try:
            data = json.loads(json_str)
            if isinstance(data, str):
                return TextComponent(text=data)
            return TextComponent.from_dict(data)
        except:
            return TextComponent(text=json_str)

    def read_enchantment_list(self) -> List[Enchantment]:
        """Read list of enchantments"""
        count = self.read_varint()
        enchantments = []
        for _ in range(count):
            ench_id = self.read_string()
            level = self.read_varint()
            enchantments.append(Enchantment(id=ench_id, level=level))
        return enchantments

    def read_attribute_modifiers(self) -> List[AttributeModifier]:
        """Read list of attribute modifiers"""
        count = self.read_varint()
        modifiers = []
        for _ in range(count):
            attr_id = self.read_string()
            name = self.read_string()
            amount = self.read_double()
            operation = self.read_varint()
            slot = self.read_string() if self.read_boolean() else None
            modifiers.append(
                AttributeModifier(
                    attribute=attr_id,
                    name=name,
                    amount=amount,
                    operation=operation,
                    slot=slot,
                )
            )
        return modifiers

    def read_components(self) -> ItemComponents:
        """
        Read all components from current position.

        Format:
        - VarInt: components_added_count
        - VarInt: components_removed_count
        - For each added: component data
        - For each removed: VarInt component_id
        """
        components = ItemComponents()

        added_count = self.read_varint()
        removed_count = self.read_varint()

        # Read added components
        for _ in range(added_count):
            component_id = self.read_varint()
            self._read_component(component_id, components)

        # Skip removed components (just IDs)
        for _ in range(removed_count):
            self.read_varint()

        return components

    def _read_component(self, component_id: int, components: ItemComponents):
        """Read a single component by type"""
        try:
            comp_type = ComponentType(component_id)
        except ValueError:
            # Unknown component, store raw
            components._raw[component_id] = self._skip_unknown_component()
            return

        if comp_type == ComponentType.CUSTOM_DATA:
            # NBT compound
            nbt_data = self._read_nbt()
            components.custom_data = nbt_data

        elif comp_type == ComponentType.MAX_STACK_SIZE:
            components.max_stack_size = self.read_varint()

        elif comp_type == ComponentType.MAX_DAMAGE:
            components.max_damage = self.read_varint()

        elif comp_type == ComponentType.DAMAGE:
            components.damage = self.read_varint()

        elif comp_type == ComponentType.UNBREAKABLE:
            components.unbreakable = True
            if self.remaining() > 0:
                self.read_boolean()  # show_in_tooltip

        elif comp_type == ComponentType.CUSTOM_NAME:
            components.custom_name = self.read_text_component()

        elif comp_type == ComponentType.ITEM_NAME:
            components.item_name = self.read_text_component()

        elif comp_type == ComponentType.LORE:
            count = self.read_varint()
            components.lore = [self.read_text_component() for _ in range(count)]

        elif comp_type == ComponentType.RARITY:
            components.rarity = self.read_string()

        elif comp_type == ComponentType.ENCHANTMENTS:
            components.enchantments = self.read_enchantment_list()

        elif comp_type == ComponentType.ATTRIBUTE_MODIFIERS:
            components.attribute_modifiers = self.read_attribute_modifiers()

        elif comp_type == ComponentType.CUSTOM_MODEL_DATA:
            components.custom_model_data = self.read_int()

        elif comp_type == ComponentType.HIDE_TOOLTIP:
            components.hide_tooltip = True

        elif comp_type == ComponentType.HIDE_ADDITIONAL_TOOLTIP:
            components.hide_additional_tooltip = True

        elif comp_type == ComponentType.FIRE_RESISTANT:
            components.fire_resistant = True

        elif comp_type == ComponentType.GLIDER:
            components.glider = True

        else:
            # Unknown component type, try to skip
            components._raw[component_id] = self._skip_unknown_component()

    def _read_nbt(self) -> Optional[NbtCompound]:
        """Read NBT compound"""
        # NBT is prefixed with type byte
        tag_type = self.read_byte()
        if tag_type == 0:  # TAG_END
            return None

        # Read name length (we skip the name for root)
        name_length = struct.unpack(">H", self.data[self.offset : self.offset + 2])[0]
        self.offset += 2 + name_length

        # Now read the compound
        if tag_type == 10:  # TAG_COMPOUND
            reader = NbtReader(self.data)
            reader.offset = self.offset
            compound = reader.read_tag(tag_type, read_name=False)[1]
            self.offset = reader.offset
            return compound

        return None

    def _skip_unknown_component(self) -> Any:
        """Try to skip an unknown component - best effort"""
        # This is a simplified skip - real implementation would need
        # to know the exact format of each component type
        return None


def parse_components(data: bytes) -> ItemComponents:
    """
    Parse item components from raw bytes.

    Args:
        data: Raw component data

    Returns:
        Parsed ItemComponents object
    """
    if not data:
        return ItemComponents()

    reader = ComponentReader(data)
    return reader.read_components()
