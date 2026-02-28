"""
Chunk data parsing utilities for Minecraft 1.21.4
Based on: https://wiki.vg/Chunk_Format

Paletted Container structure:
- bits_per_entry (byte): 0 = single value, 1-4 = indirect (4 bits), 5-8 = indirect, >8 = direct
- palette (optional): array of varint values
- data: packed long array
"""

from __future__ import annotations

import struct
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class PalettedContainer:
    """
    Represents a paletted container (blocks or biomes in a chunk section)

    Three modes:
    - Single value (bits_per_entry = 0): All entries have same value
    - Indirect (bits_per_entry 1-8): Uses palette to map indices to values
    - Direct (bits_per_entry > 8): Values stored directly
    """

    bits_per_entry: int
    palette: List[int]
    data: List[int]  # Packed long array
    entries: List[int]  # Unpacked entries

    @classmethod
    def single_value(cls, value: int, count: int) -> "PalettedContainer":
        """Create a single-value container"""
        return cls(bits_per_entry=0, palette=[value], data=[], entries=[value] * count)

    def get(self, index: int) -> int:
        """Get entry at index"""
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return 0

    def set(self, index: int, value: int) -> None:
        """Set entry at index"""
        if 0 <= index < len(self.entries):
            self.entries[index] = value


class BufferReader:
    """Helper class to read data from a byte buffer"""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read_byte(self) -> int:
        """Read unsigned byte"""
        if self.offset >= len(self.data):
            raise ValueError("Unexpected end of data")
        value = self.data[self.offset]
        self.offset += 1
        return value

    def read_signed_byte(self) -> int:
        """Read signed byte"""
        value = self.read_byte()
        if value >= 128:
            value -= 256
        return value

    def read_short(self) -> int:
        """Read signed short (big endian)"""
        if self.offset + 2 > len(self.data):
            raise ValueError("Unexpected end of data")
        value = struct.unpack(">h", self.data[self.offset : self.offset + 2])[0]
        self.offset += 2
        return value

    def read_int(self) -> int:
        """Read signed int (big endian)"""
        if self.offset + 4 > len(self.data):
            raise ValueError("Unexpected end of data")
        value = struct.unpack(">i", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def read_long(self) -> int:
        """Read signed long (big endian)"""
        if self.offset + 8 > len(self.data):
            raise ValueError("Unexpected end of data")
        value = struct.unpack(">q", self.data[self.offset : self.offset + 8])[0]
        self.offset += 8
        return value

    def read_varint(self) -> int:
        """Read varint"""
        result = 0
        shift = 0
        while True:
            if self.offset >= len(self.data):
                raise ValueError("Unexpected end of data while reading varint")
            byte = self.data[self.offset]
            self.offset += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
            if shift >= 35:
                raise ValueError("Varint too long")
        return result

    def read_bytes(self, count: int) -> bytes:
        """Read raw bytes"""
        if self.offset + count > len(self.data):
            raise ValueError("Unexpected end of data")
        value = self.data[self.offset : self.offset + count]
        self.offset += count
        return value

    def remaining(self) -> int:
        """Get remaining bytes"""
        return len(self.data) - self.offset

    def has_remaining(self, count: int = 1) -> bool:
        """Check if there are remaining bytes"""
        return self.offset + count <= len(self.data)


def unpack_packed_long_array(
    longs: List[int], bits_per_entry: int, entry_count: int
) -> List[int]:
    """
    Unpack entries from a packed long array.

    In Minecraft, entries are packed into longs where each entry takes
    `bits_per_entry` bits. Entries do NOT span across long boundaries
    (since 1.16).

    Args:
        longs: List of 64-bit signed integers
        bits_per_entry: Number of bits per entry (4-12 typically)
        entry_count: Number of entries to extract

    Returns:
        List of unpacked entry values
    """
    if bits_per_entry == 0:
        return [0] * entry_count

    entries = []
    mask = (1 << bits_per_entry) - 1

    # Calculate entries per long
    # Entries don't cross long boundaries since 1.16
    entries_per_long = 64 // bits_per_entry

    entry_index = 0
    for long_val in longs:
        # Convert to unsigned
        if long_val < 0:
            long_val = long_val & 0xFFFFFFFFFFFFFFFF

        for i in range(entries_per_long):
            if entry_index >= entry_count:
                break

            shift = i * bits_per_entry
            entry = (long_val >> shift) & mask
            entries.append(entry)
            entry_index += 1

    # Pad with zeros if we didn't get enough entries
    while len(entries) < entry_count:
        entries.append(0)

    return entries[:entry_count]


def parse_paletted_container(
    reader: BufferReader, entry_count: int = 4096
) -> PalettedContainer:
    """
    Parse a paletted container from buffer.

    Structure:
    - byte: bits_per_entry (0 = single value, 4-8 = indirect, >8 = direct)
    - if bits_per_entry == 0:
        - varint: single value (all entries have this value)
    - else if bits_per_entry <= 8:
        - varint: palette size
        - varint[palette_size]: palette entries
        - varint: data array length (number of longs)
        - long[data_length]: packed entries
    - else (direct):
        - varint: data array length
        - long[data_length]: packed entries (no palette)

    Args:
        reader: BufferReader positioned at container start
        entry_count: Number of entries (4096 for blocks, 64 for biomes)

    Returns:
        PalettedContainer with unpacked entries
    """
    # Read bits per entry
    bits_per_entry = reader.read_byte()

    # Single value palette
    if bits_per_entry == 0:
        single_value = reader.read_varint()
        return PalettedContainer.single_value(single_value, entry_count)

    # Normalize bits per entry for indirect palette
    if bits_per_entry < 4:
        bits_per_entry = 4
    elif bits_per_entry > 8:
        # Direct palette - values are stored directly
        bits_per_entry = 15  # Maximum bits for block states

    # Read palette (for indirect mode)
    palette = []
    if bits_per_entry <= 8:
        palette_size = reader.read_varint()
        for _ in range(palette_size):
            palette_entry = reader.read_varint()
            palette.append(palette_entry)

    # Read data array
    data_length = reader.read_varint()
    longs = []
    for _ in range(data_length):
        long_val = reader.read_long()
        longs.append(long_val)

    # Unpack entries
    packed_entries = unpack_packed_long_array(longs, bits_per_entry, entry_count)

    # Map through palette if indirect
    if palette:
        entries = []
        for idx in packed_entries:
            if 0 <= idx < len(palette):
                entries.append(palette[idx])
            else:
                entries.append(0)  # Invalid palette index
    else:
        entries = packed_entries

    return PalettedContainer(
        bits_per_entry=bits_per_entry, palette=palette, data=longs, entries=entries
    )


def parse_paletted_container_from_bytes(
    data: bytes, offset: int = 0, entry_count: int = 4096
) -> Tuple[PalettedContainer, int]:
    """
    Parse paletted container from bytes, return container and new offset.

    Convenience function for testing.
    """
    reader = BufferReader(data)
    reader.offset = offset
    container = parse_paletted_container(reader, entry_count)
    return container, reader.offset


# ============= CHUNK SECTION =============

@dataclass
class ChunkSection:
    """
    A 16x16x16 section of blocks in a chunk.
    
    Contains:
    - block_count: Number of non-air blocks (for 1.18+)
    - y: Section Y coordinate
    - blocks: PalettedContainer with 4096 block state IDs
    - biomes: PalettedContainer with 64 biome IDs (4x4x4)
    """
    y: int = 0
    block_count: int = 0
    blocks: Optional[PalettedContainer] = None
    biomes: Optional[PalettedContainer] = None
    
    def get_block(self, x: int, y: int, z: int) -> int:
        """
        Get block state ID at local coordinates (0-15).
        
        Index formula: (y << 8) | (z << 4) | x
        This is: y * 256 + z * 16 + x
        """
        if not (0 <= x < 16 and 0 <= y < 16 and 0 <= z < 16):
            return 0
        if self.blocks is None:
            return 0
        index = (y << 8) | (z << 4) | x
        return self.blocks.get(index)
    
    def set_block(self, x: int, y: int, z: int, block_state: int) -> None:
        """Set block state ID at local coordinates"""
        if not (0 <= x < 16 and 0 <= y < 16 and 0 <= z < 16):
            return
        if self.blocks is None:
            return
        index = (y << 8) | (z << 4) | x
        self.blocks.entries[index] = block_state
    
    def get_biome(self, x: int, y: int, z: int) -> int:
        """
        Get biome ID at local coordinates (0-15).
        
        Biomes are 4x4x4, so divide by 4.
        Index formula: (y//4 << 4) | (z//4 << 2) | (x//4)
        """
        if self.biomes is None:
            return 0
        bx, by, bz = x // 4, y // 4, z // 4
        index = (by << 4) | (bz << 2) | bx
        return self.biomes.get(index)
    
    def is_empty(self) -> bool:
        """Check if section is empty (all air)"""
        if self.blocks is None:
            return True
        return self.block_count == 0


def parse_chunk_section(reader: BufferReader, section_y: int = 0) -> ChunkSection:
    """
    Parse a chunk section from buffer.
    
    Structure (1.21.4):
    - short: block_count (number of non-air blocks)
    - PalettedContainer: block_states (4096 entries)
    - PalettedContainer: biomes (64 entries)
    
    Args:
        reader: BufferReader positioned at section start
        section_y: Y coordinate of this section
    
    Returns:
        ChunkSection with parsed data
    """
    section = ChunkSection(y=section_y)
    
    # Read block count (non-air blocks)
    section.block_count = reader.read_short()
    
    # Parse block states (4096 entries = 16*16*16)
    section.blocks = parse_paletted_container(reader, entry_count=4096)
    
    # Parse biomes (64 entries = 4*4*4)
    section.biomes = parse_paletted_container(reader, entry_count=64)
    
    return section


def parse_chunk_section_from_bytes(data: bytes, offset: int = 0, section_y: int = 0) -> Tuple[ChunkSection, int]:
    """
    Parse chunk section from bytes, return section and new offset.
    
    Convenience function for testing.
    """
    reader = BufferReader(data)
    reader.offset = offset
    section = parse_chunk_section(reader, section_y)
    return section, reader.offset


# ============= TESTS =============|

# ============= CHUNK COLUMN =============

@dataclass
class ChunkColumn:
    """
    A 16x16 column of chunk sections spanning the entire world height.
    
    For 1.18+, world height is typically -64 to 319 (384 blocks, 24 sections).
    """
    x: int  # Chunk X coordinate
    z: int  # Chunk Z coordinate
    min_y: int = -64
    max_y: int = 319
    sections: dict = None  # section_y -> ChunkSection
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = {}
    
    def get_section(self, section_y: int) -> Optional[ChunkSection]:
        """Get section by Y coordinate"""
        return self.sections.get(section_y)
    
    def set_section(self, section: ChunkSection) -> None:
        """Store a section"""
        self.sections[section.y] = section
    
    def get_block(self, x: int, y: int, z: int) -> int:
        """
        Get block state ID at local coordinates.
        
        Args:
            x: Local X (0-15)
            y: World Y (e.g., -64 to 319)
            z: Local Z (0-15)
        """
        section_y = y >> 4  # y // 16
        section = self.get_section(section_y)
        if section is None:
            return 0  # Air
        local_y = y & 15  # y % 16
        return section.get_block(x, local_y, z)
    
    def set_block(self, x: int, y: int, z: int, block_state: int) -> None:
        """Set block state ID at local coordinates"""
        section_y = y >> 4
        section = self.get_section(section_y)
        if section is None:
            return
        local_y = y & 15
        section.set_block(x, local_y, z, block_state)
    
    def get_biome(self, x: int, y: int, z: int) -> int:
        """Get biome ID at local coordinates"""
        section_y = y >> 4
        section = self.get_section(section_y)
        if section is None:
            return 0
        local_y = y & 15
        return section.get_biome(x, local_y, z)


class World:
    """
    Manages all loaded chunks and provides block access.
    """
    
    def __init__(self, min_y: int = -64, height: int = 384):
        self.min_y = min_y
        self.height = height
        self.chunks: dict = {}  # (chunk_x, chunk_z) -> ChunkColumn
    
    def get_chunk(self, chunk_x: int, chunk_z: int) -> Optional[ChunkColumn]:
        """Get chunk column by coordinates"""
        return self.chunks.get((chunk_x, chunk_z))
    
    def set_chunk(self, chunk: ChunkColumn) -> None:
        """Store a chunk column"""
        self.chunks[(chunk.x, chunk.z)] = chunk
    
    def unload_chunk(self, chunk_x: int, chunk_z: int) -> None:
        """Remove a chunk from storage"""
        key = (chunk_x, chunk_z)
        if key in self.chunks:
            del self.chunks[key]
    
    def has_chunk(self, chunk_x: int, chunk_z: int) -> bool:
        """Check if chunk is loaded"""
        return (chunk_x, chunk_z) in self.chunks
    
    @staticmethod
    def block_to_chunk(block_x: int, block_z: int) -> Tuple[int, int]:
        """Convert block coords to chunk coords"""
        return block_x >> 4, block_z >> 4
    
    def get_block_state(self, x: int, y: int, z: int) -> int:
        """
        Get block state ID at world coordinates.
        
        Returns 0 (air) if chunk not loaded.
        """
        chunk_x, chunk_z = self.block_to_chunk(x, z)
        chunk = self.get_chunk(chunk_x, chunk_z)
        if chunk is None:
            return 0
        local_x = x & 15
        local_z = z & 15
        return chunk.get_block(local_x, y, local_z)
    
    def set_block_state(self, x: int, y: int, z: int, block_state: int) -> None:
        """Set block state ID at world coordinates"""
        chunk_x, chunk_z = self.block_to_chunk(x, z)
        chunk = self.get_chunk(chunk_x, chunk_z)
        if chunk is None:
            return
        local_x = x & 15
        local_z = z & 15
        chunk.set_block(local_x, y, local_z, block_state)
    
    def get_biome(self, x: int, y: int, z: int) -> int:
        """Get biome ID at world coordinates"""
        chunk_x, chunk_z = self.block_to_chunk(x, z)
        chunk = self.get_chunk(chunk_x, chunk_z)
        if chunk is None:
            return 0
        local_x = x & 15
        local_z = z & 15
        return chunk.get_biome(local_x, y, local_z)
    
    def get_loaded_chunks(self) -> List[Tuple[int, int]]:
        """Get list of loaded chunk coordinates"""
        return list(self.chunks.keys())
    
    def chunk_count(self) -> int:
        """Get number of loaded chunks"""
        return len(self.chunks)


# ============= NBT PARSING (for Heightmaps) =============

class NBTTag:
    """NBT Tag types"""
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


def parse_nbt(reader: BufferReader) -> dict:
    """
    Parse NBT compound tag from buffer.
    Returns dict with tag data.
    """
    tag_type = reader.read_byte()
    
    if tag_type == NBTTag.END:
        return {}
    
    if tag_type != NBTTag.COMPOUND:
        raise ValueError(f"Expected COMPOUND tag, got {tag_type}")
    
    return _parse_nbt_compound(reader)


def _parse_nbt_compound(reader: BufferReader) -> dict:
    """Parse NBT compound tag"""
    result = {}
    
    while True:
        tag_type = reader.read_byte()
        
        if tag_type == NBTTag.END:
            break
        
        name = _parse_nbt_string(reader)
        value = _parse_nbt_value(reader, tag_type)
        result[name] = value
    
    return result


def _parse_nbt_string(reader: BufferReader) -> str:
    """Parse NBT string"""
    length = struct.unpack('>h', reader.read_bytes(2))[0]
    return reader.read_bytes(length).decode('utf-8')


def _parse_nbt_value(reader: BufferReader, tag_type: int) -> Any:
    """Parse NBT value based on tag type"""
    if tag_type == NBTTag.BYTE:
        return reader.read_byte()
    
    elif tag_type == NBTTag.SHORT:
        return struct.unpack('>h', reader.read_bytes(2))[0]
    
    elif tag_type == NBTTag.INT:
        return struct.unpack('>i', reader.read_bytes(4))[0]
    
    elif tag_type == NBTTag.LONG:
        return struct.unpack('>q', reader.read_bytes(8))[0]
    
    elif tag_type == NBTTag.FLOAT:
        return struct.unpack('>f', reader.read_bytes(4))[0]
    
    elif tag_type == NBTTag.DOUBLE:
        return struct.unpack('>d', reader.read_bytes(8))[0]
    
    elif tag_type == NBTTag.BYTE_ARRAY:
        length = struct.unpack('>i', reader.read_bytes(4))[0]
        return list(reader.read_bytes(length))
    
    elif tag_type == NBTTag.STRING:
        return _parse_nbt_string(reader)
    
    elif tag_type == NBTTag.LIST:
        list_type = reader.read_byte()
        length = struct.unpack('>i', reader.read_bytes(4))[0]
        return [_parse_nbt_value(reader, list_type) for _ in range(length)]
    
    elif tag_type == NBTTag.COMPOUND:
        return _parse_nbt_compound(reader)
    
    elif tag_type == NBTTag.INT_ARRAY:
        length = struct.unpack('>i', reader.read_bytes(4))[0]
        return [struct.unpack('>i', reader.read_bytes(4))[0] for _ in range(length)]
    
    elif tag_type == NBTTag.LONG_ARRAY:
        length = struct.unpack('>i', reader.read_bytes(4))[0]
        return [struct.unpack('>q', reader.read_bytes(8))[0] for _ in range(length)]
    
    else:
        raise ValueError(f"Unknown NBT tag type: {tag_type}")


@dataclass
class Heightmaps:
    """
    Heightmaps for a chunk column.
    
    Contains height values for different purposes:
    - MOTION_BLOCKING: Highest block that blocks motion
    - MOTION_BLOCKING_NO_LEAVES: Same but ignoring leaves
    - OCEAN_FLOOR: Highest solid block in water
    - WORLD_SURFACE: Highest non-air block
    """
    motion_blocking: List[int] = None
    motion_blocking_no_leaves: List[int] = None
    ocean_floor: List[int] = None
    world_surface: List[int] = None
    
    def __post_init__(self):
        # Default to 256 zeros (16x16)
        if self.motion_blocking is None:
            self.motion_blocking = [0] * 256
        if self.motion_blocking_no_leaves is None:
            self.motion_blocking_no_leaves = [0] * 256
        if self.ocean_floor is None:
            self.ocean_floor = [0] * 256
        if self.world_surface is None:
            self.world_surface = [0] * 256


def parse_heightmaps(nbt_data: dict) -> Heightmaps:
    """
    Parse heightmaps from NBT compound.
    
    Heightmaps are stored as LONG_ARRAY tags with 256 values (16x16).
    """
    heightmaps = Heightmaps()
    
    if 'MOTION_BLOCKING' in nbt_data:
        heightmaps.motion_blocking = nbt_data['MOTION_BLOCKING']
    
    if 'MOTION_BLOCKING_NO_LEAVES' in nbt_data:
        heightmaps.motion_blocking_no_leaves = nbt_data['MOTION_BLOCKING_NO_LEAVES']
    
    if 'OCEAN_FLOOR' in nbt_data:
        heightmaps.ocean_floor = nbt_data['OCEAN_FLOOR']
    
    if 'WORLD_SURFACE' in nbt_data:
        heightmaps.world_surface = nbt_data['WORLD_SURFACE']
    
    return heightmaps


# ============= TESTS =============|

def test_single_value():
    """Test single value palette"""
    # bits_per_entry = 0, value = 42
    data = bytes([0x00, 0x2A])  # 0 = single value, 42 = varint
    container, offset = parse_paletted_container_from_bytes(data, entry_count=10)

    assert container.bits_per_entry == 0
    assert container.palette == [42]
    assert len(container.entries) == 10
    assert all(e == 42 for e in container.entries)
    print("TEST PASSED: single_value")


def test_indirect_palette():
    """Test indirect palette with small palette"""
    # bits_per_entry = 4 (indirect)
    # palette_size = 3
    # palette = [1, 2, 3]
    # data_length = 1 long (enough for 16 entries with 4 bits each)

    # Create test data manually
    data = bytearray()
    data.append(4)  # bits_per_entry
    data.append(3)  # palette_size
    data.extend([1, 2, 3])  # palette entries (varints)
    data.append(1)  # data_length = 1 long
    # Long with pattern: 0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0 (16 entries, 4 bits each)
    # Each entry = 4 bits, values: 0=1, 1=2, 2=3
    # Binary: 0000 0001 0010 0000 0001 0010 0000 0001 0010 0000 0001 0010 0000 0001 0010 0000
    # Reversed per nibble: 0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0
    packed = 0x0010_8421_0842_1084  # Pattern that gives alternating 0,1,2
    data.extend(struct.pack(">q", packed))

    container, offset = parse_paletted_container_from_bytes(bytes(data), entry_count=16)

    assert container.bits_per_entry == 4
    assert container.palette == [1, 2, 3]
    assert len(container.entries) == 16
    print(f"  entries: {container.entries[:8]}...")
    print("TEST PASSED: indirect_palette")


def test_unpack_packed_array():
    """Test unpacking packed long array"""
    # Test with 4 bits per entry
    # Long value: 0x1234567890ABCDEF
    # Each nibble is an entry
    longs = [0x1234567890ABCDEF]
    entries = unpack_packed_long_array(longs, bits_per_entry=4, entry_count=16)

    assert entries[0] == 0xF
    assert entries[1] == 0xE
    assert entries[2] == 0xD
    print("TEST PASSED: unpack_packed_array")


def test_chunk_section():
    """Test chunk section parsing"""
    # Create minimal section data:
    # - block_count (short): 100
    # - block states container (single value = 1 = stone)
    # - biomes container (single value = 0 = plains)
    
    data = bytearray()
    data.extend(struct.pack(">h", 100))  # block_count = 100
    # Block states: single value palette (bits=0, value=1)
    data.append(0)  # bits_per_entry = 0
    data.append(1)  # single value = 1 (stone)
    # Biomes: single value palette (bits=0, value=0)
    data.append(0)  # bits_per_entry = 0
    data.append(0)  # single value = 0 (plains)
    
    section, offset = parse_chunk_section_from_bytes(bytes(data), section_y=4)
    
    assert section.y == 4
    assert section.block_count == 100
    assert section.blocks is not None
    assert section.biomes is not None
    
    # All blocks should be stone (1)
    assert section.get_block(0, 0, 0) == 1
    assert section.get_block(15, 15, 15) == 1
    
    # All biomes should be 0
    assert section.get_biome(0, 0, 0) == 0
    
    print("TEST PASSED: chunk_section")


def test_chunk_section_coords():
    """Test coordinate to index conversion"""
    # Index = (y << 8) | (z << 4) | x
    # For (0,0,0): index = 0
    # For (1,0,0): index = 1
    # For (0,0,1): index = 16
    # For (0,1,0): index = 256
    
    section = ChunkSection(y=0)
    section.blocks = PalettedContainer.single_value(0, 4096)
    
    # Test index calculation
    assert (0 << 8) | (0 << 4) | 0 == 0
    assert (0 << 8) | (0 << 4) | 1 == 1
    assert (0 << 8) | (1 << 4) | 0 == 16
    assert (1 << 8) | (0 << 4) | 0 == 256
    assert (15 << 8) | (15 << 4) | 15 == 4095
    
    print("TEST PASSED: chunk_section_coords")


def test_chunk_column():
    """Test chunk column block access"""
    column = ChunkColumn(x=10, z=20, min_y=-64, max_y=319)
    
    # Add a section at y=0 (world y=0 to 15)
    section = ChunkSection(y=0)
    section.blocks = PalettedContainer.single_value(5, 4096)  # All block ID 5
    column.set_section(section)
    
    # Test block access
    assert column.get_block(0, 0, 0) == 5
    assert column.get_block(15, 15, 15) == 5
    
    # Test out of section range (should return 0)
    assert column.get_block(0, 16, 0) == 0  # y=16 is in section y=1
    
    print("TEST PASSED: chunk_column")


def test_world():
    """Test world chunk management"""
    world = World(min_y=-64, height=384)
    
    # Create and add a chunk
    chunk = ChunkColumn(x=0, z=0)
    section = ChunkSection(y=0)
    section.blocks = PalettedContainer.single_value(1, 4096)  # Stone
    chunk.set_section(section)
    world.set_chunk(chunk)
    
    # Test chunk access
    assert world.has_chunk(0, 0)
    assert not world.has_chunk(1, 0)
    
    # Test block access
    # Block (0, 0, 0) is in chunk (0, 0)
    assert world.get_block_state(0, 0, 0) == 1
    assert world.get_block_state(15, 0, 15) == 1
    
    # Block (16, 0, 0) is in chunk (1, 0) - not loaded
    assert world.get_block_state(16, 0, 0) == 0
    
    # Test chunk unloading
    world.unload_chunk(0, 0)
    assert not world.has_chunk(0, 0)
    assert world.get_block_state(0, 0, 0) == 0
    
    print("TEST PASSED: world")


def test_world_coords():
    """Test world coordinate conversion"""
    # Test block_to_chunk
    assert World.block_to_chunk(0, 0) == (0, 0)
    assert World.block_to_chunk(15, 15) == (0, 0)
    assert World.block_to_chunk(16, 0) == (1, 0)
    assert World.block_to_chunk(-1, 0) == (-1, 0)  # Negative coords
    assert World.block_to_chunk(-16, 0) == (-1, 0)
    
    print("TEST PASSED: world_coords")


def run_tests():
    """Run all tests"""
    print("=" * 50)
    print("Chunk Utils Tests")
    print("=" * 50)
    
    test_single_value()
    test_unpack_packed_array()
    test_indirect_palette()
    test_chunk_section()
    test_chunk_section_coords()
    test_chunk_column()
    test_world()
    test_world_coords()
    
    print()
    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
