"""
NBT (Named Binary Tag) parser for Minecraft 1.21.4

NBT is a tree structure format used by Minecraft for:
- Item data (enchantments, attributes, custom names)
- Block entities (chests, signs, furnaces)
- Player data
- World data

Tag types:
- TAG_End (0): End of compound
- TAG_Byte (1): Signed 8-bit integer
- TAG_Short (2): Signed 16-bit integer
- TAG_Int (3): Signed 32-bit integer
- TAG_Long (4): Signed 64-bit integer
- TAG_Float (5): 32-bit IEEE float
- TAG_Double (6): 64-bit IEEE double
- TAG_Byte_Array (7): Array of signed bytes
- TAG_String (8): UTF-8 string
- TAG_List (9): List of tags (same type)
- TAG_Compound (10): Key-value map of tags
- TAG_Int_Array (11): Array of signed 32-bit integers
- TAG_Long_Array (12): Array of signed 64-bit integers
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import IntEnum


class TagType(IntEnum):
    """NBT tag types"""

    END = 0
    BYTE = 1
    SHORT = 2
    INT = 3
    LONG = 4
    FLOAT = 5
    DOUBLE = 6
    BYTE_ARRAY = 7
    STRING = 8
    LIST = 9
    COMPOUND = 10
    INT_ARRAY = 11
    LONG_ARRAY = 12


@dataclass
class NbtTag:
    """Base class for NBT tags"""

    tag_type: TagType

    def as_value(self) -> Any:
        """Get the value of this tag"""
        raise NotImplementedError


@dataclass
class NbtEnd(NbtTag):
    """End tag (marks end of compound)"""

    tag_type: TagType = TagType.END

    def as_value(self) -> None:
        return None


@dataclass
class NbtByte(NbtTag):
    """Signed 8-bit integer"""

    value: int = 0
    tag_type: TagType = TagType.BYTE

    def as_value(self) -> int:
        return self.value


@dataclass
class NbtShort(NbtTag):
    """Signed 16-bit integer"""

    value: int = 0
    tag_type: TagType = TagType.SHORT

    def as_value(self) -> int:
        return self.value


@dataclass
class NbtInt(NbtTag):
    """Signed 32-bit integer"""

    value: int = 0
    tag_type: TagType = TagType.INT

    def as_value(self) -> int:
        return self.value


@dataclass
class NbtLong(NbtTag):
    """Signed 64-bit integer"""

    value: int = 0
    tag_type: TagType = TagType.LONG

    def as_value(self) -> int:
        return self.value


@dataclass
class NbtFloat(NbtTag):
    """32-bit IEEE float"""

    value: float = 0.0
    tag_type: TagType = TagType.FLOAT

    def as_value(self) -> float:
        return self.value


@dataclass
class NbtDouble(NbtTag):
    """64-bit IEEE double"""

    value: float = 0.0
    tag_type: TagType = TagType.DOUBLE

    def as_value(self) -> float:
        return self.value


@dataclass
class NbtByteArray(NbtTag):
    """Array of signed bytes"""

    value: bytes = field(default_factory=bytes)
    tag_type: TagType = TagType.BYTE_ARRAY

    def as_value(self) -> bytes:
        return self.value


@dataclass
class NbtString(NbtTag):
    """UTF-8 string"""

    value: str = ""
    tag_type: TagType = TagType.STRING

    def as_value(self) -> str:
        return self.value


@dataclass
class NbtList(NbtTag):
    """List of tags (all same type)"""

    value: List[NbtTag] = field(default_factory=list)
    list_type: TagType = TagType.END
    tag_type: TagType = TagType.LIST

    def as_value(self) -> List[Any]:
        return [tag.as_value() for tag in self.value]

    def __iter__(self):
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self, index: int) -> NbtTag:
        return self.value[index]


@dataclass
class NbtCompound(NbtTag):
    """Key-value map of tags"""

    tags: Dict[str, NbtTag] = field(default_factory=dict)
    tag_type: TagType = TagType.COMPOUND

    def as_value(self) -> Dict[str, Any]:
        return {k: v.as_value() for k, v in self.tags.items()}

    def get(self, name: str, default: Any = None) -> Optional[NbtTag]:
        """Get a tag by name"""
        return self.tags.get(name, default)

    def get_byte(self, name: str, default: int = 0) -> int:
        """Get byte value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtByte):
            return tag.value
        return default

    def get_short(self, name: str, default: int = 0) -> int:
        """Get short value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtShort):
            return tag.value
        return default

    def get_int(self, name: str, default: int = 0) -> int:
        """Get int value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtInt):
            return tag.value
        return default

    def get_long(self, name: str, default: int = 0) -> int:
        """Get long value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtLong):
            return tag.value
        return default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get float value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtFloat):
            return tag.value
        return default

    def get_double(self, name: str, default: float = 0.0) -> float:
        """Get double value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtDouble):
            return tag.value
        return default

    def get_string(self, name: str, default: str = "") -> str:
        """Get string value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtString):
            return tag.value
        return default

    def get_list(self, name: str) -> Optional[NbtList]:
        """Get list tag"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtList):
            return tag
        return None

    def get_compound(self, name: str) -> Optional["NbtCompound"]:
        """Get compound tag"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtCompound):
            return tag
        return None

    def get_int_array(self, name: str) -> Optional[List[int]]:
        """Get int array value"""
        tag = self.tags.get(name)
        if isinstance(tag, NbtIntArray):
            return tag.value
        return None

    def __contains__(self, name: str) -> bool:
        return name in self.tags

    def __getitem__(self, name: str) -> NbtTag:
        return self.tags[name]

    def __iter__(self):
        return iter(self.tags.items())


@dataclass
class NbtIntArray(NbtTag):
    """Array of signed 32-bit integers"""

    value: List[int] = field(default_factory=list)
    tag_type: TagType = TagType.INT_ARRAY

    def as_value(self) -> List[int]:
        return self.value


@dataclass
class NbtLongArray(NbtTag):
    """Array of signed 64-bit integers"""

    value: List[int] = field(default_factory=list)
    tag_type: TagType = TagType.LONG_ARRAY

    def as_value(self) -> List[int]:
        return self.value


class NbtReader:
    """Reader for NBT data from bytes"""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def remaining(self) -> int:
        """Get remaining bytes"""
        return len(self.data) - self.offset

    def read_byte(self) -> int:
        """Read signed byte"""
        if self.offset >= len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = self.data[self.offset]
        self.offset += 1
        if value > 127:
            value -= 256
        return value

    def read_ubyte(self) -> int:
        """Read unsigned byte"""
        if self.offset >= len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = self.data[self.offset]
        self.offset += 1
        return value

    def read_short(self) -> int:
        """Read signed short (big-endian)"""
        if self.offset + 2 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">h", self.data[self.offset : self.offset + 2])[0]
        self.offset += 2
        return value

    def read_ushort(self) -> int:
        """Read unsigned short (big-endian)"""
        if self.offset + 2 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">H", self.data[self.offset : self.offset + 2])[0]
        self.offset += 2
        return value

    def read_int(self) -> int:
        """Read signed int (big-endian)"""
        if self.offset + 4 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">i", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def read_long(self) -> int:
        """Read signed long (big-endian)"""
        if self.offset + 8 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">q", self.data[self.offset : self.offset + 8])[0]
        self.offset += 8
        return value

    def read_float(self) -> float:
        """Read float (big-endian)"""
        if self.offset + 4 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">f", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def read_double(self) -> float:
        """Read double (big-endian)"""
        if self.offset + 8 > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = struct.unpack(">d", self.data[self.offset : self.offset + 8])[0]
        self.offset += 8
        return value

    def read_string(self) -> str:
        """Read UTF-8 string (length-prefixed)"""
        length = self.read_ushort()
        if self.offset + length > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = self.data[self.offset : self.offset + length].decode("utf-8")
        self.offset += length
        return value

    def read_bytes(self, length: int) -> bytes:
        """Read raw bytes"""
        if self.offset + length > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = self.data[self.offset : self.offset + length]
        self.offset += length
        return value

    def read_tag(self, tag_type: TagType, read_name: bool = True) -> tuple:
        """
        Read a tag.

        Args:
            tag_type: Type of tag to read
            read_name: Whether to read the tag name (False for list items)

        Returns:
            Tuple of (name, tag) or (None, tag) if read_name is False
        """
        name = None
        if read_name:
            name = self.read_string()

        if tag_type == TagType.BYTE:
            return name, NbtByte(value=self.read_byte())

        elif tag_type == TagType.SHORT:
            return name, NbtShort(value=self.read_short())

        elif tag_type == TagType.INT:
            return name, NbtInt(value=self.read_int())

        elif tag_type == TagType.LONG:
            return name, NbtLong(value=self.read_long())

        elif tag_type == TagType.FLOAT:
            return name, NbtFloat(value=self.read_float())

        elif tag_type == TagType.DOUBLE:
            return name, NbtDouble(value=self.read_double())

        elif tag_type == TagType.BYTE_ARRAY:
            length = self.read_int()
            data = self.read_bytes(length)
            return name, NbtByteArray(value=data)

        elif tag_type == TagType.STRING:
            return name, NbtString(value=self.read_string())

        elif tag_type == TagType.LIST:
            list_type = TagType(self.read_byte())
            length = self.read_int()
            items = []
            for _ in range(length):
                _, tag = self.read_tag(list_type, read_name=False)
                items.append(tag)
            return name, NbtList(value=items, list_type=list_type)

        elif tag_type == TagType.COMPOUND:
            compound = NbtCompound()
            while True:
                child_type = TagType(self.read_byte())
                if child_type == TagType.END:
                    break
                child_name, child_tag = self.read_tag(child_type, read_name=True)
                compound.tags[child_name] = child_tag
            return name, compound

        elif tag_type == TagType.INT_ARRAY:
            length = self.read_int()
            values = [self.read_int() for _ in range(length)]
            return name, NbtIntArray(value=values)

        elif tag_type == TagType.LONG_ARRAY:
            length = self.read_int()
            values = [self.read_long() for _ in range(length)]
            return name, NbtLongArray(value=values)

        else:
            raise ValueError(f"Unknown tag type: {tag_type}")

    def read_root(self) -> NbtCompound:
        """
        Read the root compound tag.

        Returns:
            The root NbtCompound
        """
        tag_type = TagType(self.read_byte())
        if tag_type != TagType.COMPOUND:
            raise ValueError(f"Expected compound root, got {tag_type}")
        _, tag = self.read_tag(tag_type, read_name=True)
        return tag


def parse_nbt(data: bytes) -> Optional[NbtCompound]:
    """
    Parse NBT data.

    Args:
        data: Raw NBT bytes

    Returns:
        Parsed NbtCompound or None if empty
    """
    if not data:
        return None

    reader = NbtReader(data)
    return reader.read_root()


# Convenience functions for common NBT structures


def parse_enchantments(
    nbt: NbtCompound, list_name: str = "Enchantments"
) -> List[Dict[str, Any]]:
    """
    Parse enchantment list from NBT.

    Args:
        nbt: Item NBT compound
        list_name: Name of enchantment list

    Returns:
        List of enchantment dicts with 'id' and 'lvl' keys
    """
    enchantments = []
    ench_list = nbt.get_list(list_name)
    if not ench_list:
        return enchantments

    for ench_tag in ench_list:
        if isinstance(ench_tag, NbtCompound):
            ench_id = ench_tag.get_string("id")
            ench_lvl = ench_tag.get_int("lvl")
            enchantments.append({"id": ench_id, "level": ench_lvl})

    return enchantments


def parse_attribute_modifiers(nbt: NbtCompound) -> List[Dict[str, Any]]:
    """
    Parse attribute modifiers from NBT.

    Args:
        nbt: Item NBT compound

    Returns:
        List of attribute modifier dicts
    """
    modifiers = []
    attr_list = nbt.get_list("AttributeModifiers")
    if not attr_list:
        return modifiers

    for attr_tag in attr_list:
        if isinstance(attr_tag, NbtCompound):
            modifiers.append(
                {
                    "attribute": attr_tag.get_string("AttributeName"),
                    "name": attr_tag.get_string("Name"),
                    "amount": attr_tag.get_double("Amount"),
                    "operation": attr_tag.get_int("Operation"),
                    "slot": attr_tag.get_string("Slot") if "Slot" in attr_tag else None,
                }
            )

    return modifiers


def parse_display(nbt: NbtCompound) -> Optional[Dict[str, Any]]:
    """
    Parse display data from NBT (custom name, lore, etc.)

    Args:
        nbt: Item NBT compound

    Returns:
        Display dict or None
    """
    display = nbt.get_compound("display")
    if not display:
        return None

    result = {}

    if "Name" in display:
        result["name"] = display.get_string("Name")

    if "Lore" in display:
        lore_list = display.get_list("Lore")
        if lore_list:
            result["lore"] = [line.as_value() for line in lore_list]

    return result
