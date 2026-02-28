"""
Minecraft protocol implementation for minepyt
Supports protocol version 769 (1.21.4)
"""

from __future__ import annotations

import asyncio
import struct
import zlib
import math
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple

from mcproto.buffer import Buffer
from mcproto.connection import TCPAsyncConnection
from mcproto.protocol.base_io import StructFormat
from mcproto.types.uuid import UUID

from .chunk_utils import (
    World, ChunkColumn, ChunkSection, BufferReader,
    parse_paletted_container, parse_chunk_section, parse_nbt
)
from .block_registry import Block, get_block_name, is_air, is_solid, is_transparent
from .nbt import NbtCompound, NbtReader, parse_nbt as parse_nbt_data
from .components import ItemComponents, ComponentReader, Enchantment, parse_components
from .recipes import (
    RecipeRegistry, RecipeMatcher, Recipe, ShapedRecipe, ShapelessRecipe,
    SmeltingRecipe, StonecuttingRecipe, Ingredient, RecipeResult
)
from .entities import (
    Entity, EntityType, EntityKind, EntityEquipment,
    MobType, ObjectType, EntityManager,
    classify_mob, get_mob_name, get_object_name
)


class Game:
    """Represents the current game state"""
    
    def __init__(self):
        self.level_type: str = 'default'
        self.hardcore: bool = False
        self.game_mode: str = 'survival'
        self.dimension: str = 'overworld'
        self.difficulty: str = 'normal'
        self.max_players: int = 20
        self.server_view_distance: int = 10
        self.enable_respawn_screen: bool = True
        self.server_brand: Optional[str] = None
        self.min_y: int = 0
        self.height: int = 256
        self.time: int = 0
        self.age: int = 0
    
    def __repr__(self):
        return (f"Game(mode={self.game_mode}, dim={self.dimension}, time={self.time})")


class Item:
    """
    Represents an item in inventory.
    
    Supports 1.21.4 item components including:
    - Enchantments
    - Attribute modifiers
    - Custom names and lore
    - Durability (damage)
    """
    
    def __init__(self, item_id: int = 0, count: int = 0, 
                 name: str = "", slot: int = -1,
                 components: Optional[ItemComponents] = None):
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


GAME_MODE_NAMES = {
    0: 'survival',
    1: 'creative',
    2: 'adventure',
    3: 'spectator'
}


def parse_game_mode(game_mode_bits: int) -> str:
    """Parse game mode from bits"""
    if game_mode_bits < 0 or game_mode_bits > 0b11:
        return 'survival'
    return GAME_MODE_NAMES.get(game_mode_bits & 0b11, 'survival')


class ProtocolState(IntEnum):
    """Minecraft protocol states"""
    HANDSHAKING = 0
    STATUS = 1
    LOGIN = 2
    CONFIGURATION = 3  # Added in 1.20.2
    PLAY = 4


class DigStatus(IntEnum):
    """Player digging action status"""
    START_DIGGING = 0
    CANCEL_DIGGING = 1
    FINISH_DIGGING = 2
    DROP_ITEM_STACK = 3
    DROP_ITEM = 4
    RELEASE_USE_ITEM = 5
    SWAP_ITEM_IN_HAND = 6


class ClickMode(IntEnum):
    """Container click modes for 1.21.4"""
    PICKUP = 0           # Click / Pickup (mouse button 0=left, 1=right)
    QUICK_MOVE = 1       # Shift+Click - move item to other inventory
    SWAP = 2             # Swap with hotbar slot (button = hotbar slot 0-8)
    CLONE = 3            # Clone item (middle click, creative only)
    THROW = 4            # Drop item (button 0=one, 1=stack)
    QUICK_CRAFT = 5      # Drag items (painting mode)
    PICKUP_ALL = 6       # Double-click to pickup all of same type


class ClickButton(IntEnum):
    """Mouse buttons for container clicks"""
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


class MinecraftProtocol:
    """
    Low-level Minecraft protocol implementation for 1.21.4
    """

    PROTOCOL_VERSION = 769  # 1.21.4

    def __init__(self, host: str, port: int = 25565, username: str = "Player"):
        self.host = host
        self.port = port
        self.username = username
        self.connection: Optional[TCPAsyncConnection] = None
        self.state = ProtocolState.HANDSHAKING
        self.compression_threshold = -1

        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}

        # Bot state
        self.uuid: Optional[str] = None
        self.entity_id: Optional[int] = None
        self.game_mode: Optional[int] = None
        self.position: Tuple[float, float, float] = (0.0, 64.0, 0.0)
        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.on_ground: bool = True

        # Running state
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        
        # Game state (plugin: game)
        self.game = Game()
        
        # Health state (plugin: health)
        self.health: float = 20.0
        self.food: int = 20
        self.food_saturation: float = 5.0
        self.is_alive: bool = True
        self._auto_respawn: bool = True
        
        # Entities state (plugin: entities)
        self.players: Dict[str, Dict] = {}  # uuid -> player info (legacy)
        self.entities: Dict[int, Dict] = {}  # entity_id -> entity info (legacy dict for compat)
        self.entity_manager: EntityManager = EntityManager()  # Full entity system
        self.entity: Optional[Dict] = None  # bot's own entity (legacy dict for compat)
        # World state (plugin: blocks)
        self.world: World = World(min_y=0, height=256)
        self._chunks_loaded: int = 0
        
        # Digging state
        self._dig_sequence: int = 0
        self._is_digging: bool = False
        self._dig_target: Optional[Tuple[int, int, int]] = None
        self._dig_task: Optional[asyncio.Task] = None
        self._break_animations: Dict[int, Dict] = {}  # entity_id -> animation info
        
        # Inventory state
        self.inventory: Dict[int, Item] = {}  # slot -> Item
        self.held_item_slot: int = 0  # 0-8 for hotbar
        self.open_container_id: Optional[int] = None
        self._inventory_sequence: int = 0  # For container clicks
        self._cursor_item: Optional[Item] = None  # Item held by cursor
        
        # Recipe system
        self.recipes: RecipeRegistry = RecipeRegistry()
        self.recipe_matcher: RecipeMatcher = RecipeMatcher(self.recipes)
    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        def wrapper(*args, **kwargs):
            if handler in self._handlers.get(event, []):
                self._handlers[event].remove(wrapper)
            return handler(*args, **kwargs)

        self.on(event, wrapper)

    def emit(self, event: str, *args, **kwargs) -> None:
        for handler in self._handlers.get(event, [])[:]:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in handler for {event}: {e}")

    async def _write_packet(self, packet_id: int, data: bytes) -> None:
        """Write a packet to the connection"""
        if self.connection is None:
            raise RuntimeError("Not connected")

        packet_data = Buffer()
        packet_data.write_varint(packet_id)
        packet_data.write(data)

        # Apply compression if enabled
        if self.compression_threshold >= 0:
            if len(packet_data) >= self.compression_threshold:
                compressed = zlib.compress(bytes(packet_data))
                final_data = Buffer()
                final_data.write_varint(len(packet_data))
                final_data.write(compressed)
                packet_data = final_data
            else:
                final_data = Buffer()
                final_data.write_varint(0)
                final_data.write(packet_data)
                packet_data = final_data

        await self.connection.write_varint(len(packet_data))
        await self.connection.write(packet_data)

    async def _read_packet(self) -> Tuple[int, Buffer]:
        """Read a packet from the connection"""
        if self.connection is None:
            raise RuntimeError("Not connected")

        length = await self.connection.read_varint()
        data = await self.connection.read(length)
        buf = Buffer(data)

        if self.compression_threshold >= 0:
            uncompressed_length = buf.read_varint()
            if uncompressed_length > 0:
                compressed_data = bytes(buf.read(buf.remaining))
                decompressed = zlib.decompress(compressed_data)
                buf = Buffer(decompressed)

        packet_id = buf.read_varint()
        return packet_id, buf

    def _extract_text(self, data: Any) -> str:
        """Extract plain text from JSON text component"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            if 'text' in data:
                text = data['text']
            elif 'translate' in data:
                text = data['translate']
                if 'with' in data:
                    args = [self._extract_text(arg) for arg in data['with']]
                    try:
                        text = text % tuple(args)
                    except:
                        text = ' '.join([text] + args)
            else:
                text = ''
            
            # Process 'extra' field
            if 'extra' in data:
                for extra in data['extra']:
                    text += self._extract_text(extra)
            
            return text
        elif isinstance(data, list):
            return ''.join(self._extract_text(item) for item in data)
        else:
            return str(data)

    async def send_handshake(self, next_state: int = 2) -> None:
        """Send handshake packet"""
        buf = Buffer()
        buf.write_varint(self.PROTOCOL_VERSION)
        buf.write_utf(self.host)
        buf.write_value(StructFormat.USHORT, self.port)
        buf.write_varint(next_state)

        await self._write_packet(0x00, bytes(buf))

        if next_state == 1:
            self.state = ProtocolState.STATUS
        elif next_state == 2:
            self.state = ProtocolState.LOGIN

    async def send_login_start(self) -> None:
        """Send login start packet"""
        buf = Buffer()
        buf.write_utf(self.username)
        uuid_obj = UUID(bytes=b"\x00" * 16)
        uuid_obj.serialize_to(buf)

        await self._write_packet(0x00, bytes(buf))

    async def send_login_acknowledged(self) -> None:
        """Send login acknowledged packet (transitions to Configuration state)"""
        await self._write_packet(0x03, b"")
        self.state = ProtocolState.CONFIGURATION

    async def send_client_information(self) -> None:
        """Send client information (in Configuration state)"""
        buf = Buffer()
        buf.write_utf("en_GB")  # Locale
        buf.write_value(StructFormat.BYTE, 10)  # View distance
        buf.write_varint(0)  # Chat mode: enabled
        buf.write_value(StructFormat.BOOL, True)  # Chat colors
        buf.write_value(StructFormat.BYTE, 0x7F)  # Displayed skin parts (all)
        buf.write_varint(1)  # Main hand: right
        buf.write_value(StructFormat.BOOL, False)  # Enable text filtering
        buf.write_value(StructFormat.BOOL, True)  # Allow server listings
        buf.write_varint(0)  # Particle status: all

        await self._write_packet(0x00, bytes(buf))  # Client Information in config state
    async def send_known_packs(self) -> None:
        """Send known packs (required in 1.21+)"""
        buf = Buffer()
        buf.write_varint(0)  # No known packs
        await self._write_packet(0x07, bytes(buf))  # Serverbound Known Packs
    async def send_acknowledge_finish_configuration(self) -> None:
        """Send acknowledge finish configuration (transitions to Play state)"""
        await self._write_packet(0x03, bytes(Buffer()))  # Acknowledge Finish Configuration
        self.state = ProtocolState.PLAY
        print("Transitioned to PLAY state")
    async def send_keep_alive(self, keep_alive_id: int) -> None:
        """Respond to keep alive packet (0x1A for 1.21.4)"""
        buf = Buffer()
        buf.write_value(StructFormat.LONGLONG, keep_alive_id)  # LONG = 8 bytes
        await self._write_packet(0x1A, bytes(buf))

    async def send_player_position(self) -> None:
        """Send player position and rotation (MOVE_PLAYER_POS_ROT = 0x1D for 1.21.4)"""
        buf = Buffer()
        buf.write_value(StructFormat.DOUBLE, self.position[0])  # X
        buf.write_value(StructFormat.DOUBLE, self.position[1])  # Y
        buf.write_value(StructFormat.DOUBLE, self.position[2])  # Z
        buf.write_value(StructFormat.FLOAT, self.yaw)  # Yaw
        buf.write_value(StructFormat.FLOAT, self.pitch)  # Pitch
        buf.write_value(StructFormat.BYTE, 0x01 if self.on_ground else 0x00)  # Flags (BYTE)

        await self._write_packet(0x1D, bytes(buf))  # MOVE_PLAYER_POS_ROT

    async def respawn(self) -> None:
        """Send respawn request to server (Client Command = 0x0D for 1.21.4)"""
        if self.is_alive:
            return
        buf = Buffer()
        buf.write_varint(0)  # Action: Perform respawn
        await self._write_packet(0x0D, bytes(buf))
        print("[HEALTH] Respawn requested")

    async def chat(self, message: str) -> None:
        """Send a chat message (experimental for 1.21.4)
        
        Uses unsigned chat packet - may not work on all servers
        """
        if len(message) > 256:
            message = message[:256]
        
        buf = Buffer()
        buf.write_utf(message)
        buf.write_value(StructFormat.LONGLONG, 0)  # timestamp
        buf.write_value(StructFormat.LONGLONG, 0)  # salt
        buf.write_value(StructFormat.BOOL, False)  # no signature
        buf.write_varint(0)  # message count
        # FixedBitset(20) = 20 bits = 3 bytes
        buf.write_value(StructFormat.BYTE, 0)
        buf.write_value(StructFormat.BYTE, 0)
        buf.write_value(StructFormat.BYTE, 0)
        
        await self._write_packet(0x07, bytes(buf))
        print(f"[CHAT] Sent: {message}")

    def block_at(self, x: int, y: int, z: int) -> Block:
        """Get block at world coordinates as a Block object"""
        block_state = self.world.get_block_state(x, y, z)
        return Block(state_id=block_state, position=(x, y, z))

    def get_loaded_chunks(self) -> List[Tuple[int, int]]:
        """Get list of loaded chunk coordinates"""
        return self.world.get_loaded_chunks()
    
    async def send_player_digging(self, status: DigStatus, x: int, y: int, z: int, face: int = 1) -> None:
        """
        Send player digging packet (0x24 for 1.21.4)
        
        Args:
            status: DigStatus enum value
            x, y, z: Block position
            face: Direction (0=down, 1=up, 2=north, 3=south, 4=west, 5=east)
        """
        # Increment sequence
        self._dig_sequence += 1
        
        # Pack position into long: x (26 bits) | y (12 bits) | z (26 bits)
        pos_long = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)
        
        buf = Buffer()
        buf.write_varint(status)
        buf.write_value(StructFormat.LONG, pos_long)
        buf.write_value(StructFormat.BYTE, face)
        buf.write_varint(self._dig_sequence)
        
        await self._write_packet(0x24, bytes(buf))
    
    def _get_dig_time(self, block: Block) -> float:
        """
        Calculate time to dig a block in seconds.
        
        Simplified calculation - full implementation would consider:
        - Block hardness
        - Tool in hand and its efficiency
        - Enchantments (Efficiency, Unbreaking)
        - Effects (Haste, Mining Fatigue)
        - Player being in water/air
        """
        # Creative mode: instant
        if self.game.game_mode == 'creative':
            return 0.0
        
        # Air blocks: instant
        if block.is_air:
            return 0.0
        
        # Base dig time (simplified)
        # Real values would come from block registry hardness
        base_hardness = 1.5  # Default for stone-like blocks
        
        # Check if block is in known hardness table
        hardness_map = {
            'dirt': 0.5,
            'grass_block': 0.6,
            'stone': 1.5,
            'cobblestone': 2.0,
            'sand': 0.5,
            'gravel': 0.6,
            'oak_log': 2.0,
            'oak_planks': 2.0,
            'glass': 0.3,
            'sandstone': 0.8,
        }
        
        hardness = hardness_map.get(block.name, base_hardness)
        
        # Convert to seconds (multiplier from Minecraft source)
        dig_time = hardness * 1.5
        
        # Tool bonus (simplified - check if holding appropriate tool)
        # In full implementation, check inventory for tool type
        # For now, assume bare hands
        
        return dig_time
    
    async def dig(self, x: int, y: int, z: int, face: int = 1) -> bool:
        """
        Dig a block at the specified position.
        
        Args:
            x, y, z: Block position
            face: Direction bot is facing (1=up for simple digging)
            
        Returns:
            True if digging started successfully
        """
        # Check if already digging
        if self._is_digging:
            print(f"[DIG] Already digging at {self._dig_target}")
            return False
        
        # Get block info
        block = self.block_at(x, y, z)
        
        if block.is_air:
            print(f"[DIG] Block at ({x}, {y}, {z}) is air, nothing to dig")
            return False
        
        # Check game mode
        if self.game.game_mode == 'adventure':
            print("[DIG] Cannot dig in adventure mode")
            return False
        
        if self.game.game_mode == 'spectator':
            print("[DIG] Cannot dig in spectator mode")
            return False
        
        # Start digging
        self._is_digging = True
        self._dig_target = (x, y, z)
        
        print(f"[DIG] Starting to dig {block.name} at ({x}, {y}, {z})")
        self.emit("dig_start", block)
        
        # Send START_DIGGING packet
        await self.send_player_digging(DigStatus.START_DIGGING, x, y, z, face)
        
        # Calculate dig time
        dig_time = self._get_dig_time(block)
        
        if dig_time > 0:
            # Wait for dig time
            try:
                await asyncio.sleep(dig_time)
            except asyncio.CancelledError:
                # Digging was cancelled
                await self.send_player_digging(DigStatus.CANCEL_DIGGING, x, y, z, face)
                self._is_digging = False
                self.emit("dig_abort", block)
                return False
        
        # Send FINISH_DIGGING packet
        await self.send_player_digging(DigStatus.FINISH_DIGGING, x, y, z, face)
        
        print(f"[DIG] Finished digging {block.name}")
        self.emit("dig_end", block)
        
        self._is_digging = False
        self._dig_target = None
        
        return True
    
    async def stop_digging(self) -> None:
        """Cancel current digging action"""
        if not self._is_digging or self._dig_target is None:
            return
        
        x, y, z = self._dig_target
        block = self.block_at(x, y, z)
        
        # Cancel the dig task
        if self._dig_task:
            self._dig_task.cancel()
            try:
                await self._dig_task
            except asyncio.CancelledError:
                pass
        
        # Send cancel packet
        await self.send_player_digging(DigStatus.CANCEL_DIGGING, x, y, z, 1)
        
        print(f"[DIG] Cancelled digging at ({x}, {y}, {z})")
        self.emit("dig_abort", block)
        
        self._is_digging = False
        self._dig_target = None
    
    # ============= ENTITY INTERACTION METHODS =============
    
    async def send_interact(
        self,
        entity_id: int,
        interact_type: int = 0,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        hand: int = 0,
        sneaking: bool = False
    ) -> None:
        """
        Send Interact packet (0x10 serverbound for 1.21.4).
        
        Interact types:
        - 0: INTERACT (right-click on entity)
        - 1: ATTACK (left-click on entity)
        - 2: INTERACT_AT (right-click at specific position on entity)
        
        Args:
            entity_id: Target entity ID
            interact_type: 0=interact, 1=attack, 2=interact_at
            target_x, target_y, target_z: Target position (only for INTERACT_AT)
            hand: 0=main hand, 1=off hand (only for INTERACT and INTERACT_AT)
            sneaking: Whether player is sneaking
        """
        buf = Buffer()
        buf.write_varint(entity_id)
        buf.write_varint(interact_type)
        
        if interact_type == 2:  # INTERACT_AT
            buf.write_value(StructFormat.FLOAT, target_x)
            buf.write_value(StructFormat.FLOAT, target_y)
            buf.write_value(StructFormat.FLOAT, target_z)
            buf.write_varint(hand)
        elif interact_type == 0:  # INTERACT
            buf.write_varint(hand)
        # ATTACK (type 1) has no additional data
        
        # Sneaking flag (1.16+)
        buf.write_value(StructFormat.BOOL, sneaking)
        
        await self._write_packet(0x10, bytes(buf))
    
    async def attack(self, entity, swing_hand: bool = True) -> bool:
        """
        Attack an entity.
        
        Args:
            entity: Entity object or entity ID
            swing_hand: Whether to send arm swing animation
            
        Returns:
            True if attack was sent successfully
        """
        # Get entity ID
        if hasattr(entity, 'entity_id'):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)
        
        if entity_obj is None:
            print(f"[ATTACK] Entity {entity_id} not found")
            return False
        
        # Check if entity is still valid (not dead)
        if entity_obj.is_dead:
            print(f"[ATTACK] Entity {entity_id} is dead")
            return False
        
        # Check distance (max 6 blocks for attack)
        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[ATTACK] Entity {entity_id} too far: {dist:.1f} blocks")
                return False
        
        # Look at entity first
        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)
        
        # Send attack packet
        await self.send_interact(entity_id, interact_type=1)  # ATTACK = 1
        
        # Swing arm for animation
        if swing_hand:
            await self.send_arm_swing()
        
        print(f"[ATTACK] Attacked {entity_obj} (id={entity_id})")
        self.emit("entity_attack", entity_obj)
        
        return True
    
    async def interact(self, entity, hand: int = 0, swing_hand: bool = True) -> bool:
        """
        Interact with an entity (right-click).
        
        Args:
            entity: Entity object or entity ID
            hand: 0=main hand, 1=off hand
            swing_hand: Whether to send arm swing animation
            
        Returns:
            True if interaction was sent successfully
        """
        # Get entity ID
        if hasattr(entity, 'entity_id'):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)
        
        if entity_obj is None:
            print(f"[INTERACT] Entity {entity_id} not found")
            return False
        
        # Check if entity is still valid
        if entity_obj.is_dead:
            print(f"[INTERACT] Entity {entity_id} is dead")
            return False
        
        # Check distance (max 6 blocks for interact)
        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[INTERACT] Entity {entity_id} too far: {dist:.1f} blocks")
                return False
        
        # Look at entity first
        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)
        
        # Send interact packet
        await self.send_interact(entity_id, interact_type=0, hand=hand)  # INTERACT = 0
        
        # Swing arm for animation
        if swing_hand:
            await self.send_arm_swing()
        
        print(f"[INTERACT] Interacted with {entity_obj} (id={entity_id})")
        self.emit("entity_interact", entity_obj)
        
        return True
    
    async def use_on(
        self,
        entity,
        target_x: float = 0.5,
        target_y: float = 0.5,
        target_z: float = 0.5,
        hand: int = 0,
        swing_hand: bool = True
    ) -> bool:
        """
        Interact at a specific position on an entity.
        
        Used for entities with multiple interactable parts
        (e.g., armor stand, item frame).
        
        Args:
            entity: Entity object or entity ID
            target_x, target_y, target_z: Relative position on entity (0-1)
            hand: 0=main hand, 1=off hand
            swing_hand: Whether to send arm swing animation
            
        Returns:
            True if interaction was sent successfully
        """
        # Get entity ID
        if hasattr(entity, 'entity_id'):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)
        
        if entity_obj is None:
            print(f"[USE_ON] Entity {entity_id} not found")
            return False
        
        # Check if entity is still valid
        if entity_obj.is_dead:
            print(f"[USE_ON] Entity {entity_id} is dead")
            return False
        
        # Check distance
        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[USE_ON] Entity {entity_id} too far: {dist:.1f} blocks")
                return False
        
        # Look at entity first
        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)
        
        # Calculate world coordinates from relative position
        world_x = entity_obj.x + (target_x - 0.5) * entity_obj.width
        world_y = entity_obj.y + target_y * entity_obj.height
        world_z = entity_obj.z + (target_z - 0.5) * entity_obj.width
        
        # Send interact_at packet
        await self.send_interact(
            entity_id,
            interact_type=2,  # INTERACT_AT = 2
            target_x=world_x,
            target_y=world_y,
            target_z=world_z,
            hand=hand
        )
        
        # Swing arm for animation
        if swing_hand:
            await self.send_arm_swing()
        
        print(f"[USE_ON] Used on {entity_obj} (id={entity_id}) at ({target_x}, {target_y}, {target_z})")
        self.emit("entity_use_on", entity_obj, (target_x, target_y, target_z))
        
        return True
    
    async def send_arm_swing(self, hand: int = 0) -> None:
        """
        Send arm swing animation (0x35 serverbound for 1.21.4).
        
        Args:
            hand: 0=main hand, 1=off hand
        """
        buf = Buffer()
        buf.write_varint(hand)
        await self._write_packet(0x35, bytes(buf))
    
    async def look_at(self, x: float, y: float, z: float) -> None:
        """
        Look at a specific position.
        
        Args:
            x, y, z: World coordinates to look at
        """
        if not self.position:
            return
        
        # Calculate yaw and pitch
        dx = x - self.position[0]
        dy = y - self.position[1]
        dz = z - self.position[2]
        
        # Calculate distance (horizontal)
        dist = math.sqrt(dx * dx + dz * dz)
        
        # Calculate yaw (rotation around Y axis)
        # Minecraft uses degrees, with 0 = south, 90 = west
        yaw = math.degrees(math.atan2(-dx, dz))
        
        # Calculate pitch (rotation around X axis)
        # Positive = looking down
        pitch = math.degrees(math.atan2(-dy, dist))
        
        # Update internal state
        self.yaw = yaw
        self.pitch = pitch
        
        # Send look update
        await self.send_player_position()

    # ============= INVENTORY METHODS =============
    
    def _parse_slot(self, buf: Buffer) -> Optional[Item]:
        """
        Parse a slot from buffer for 1.21.4.
        
        Slot structure (1.20.5+):
        - VarInt: item_id (0 = empty slot)
        - if item_id != 0:
          - VarInt: count (component count format)
          - VarInt: added_components_count
          - VarInt: removed_components_count
          - For each added component:
            - VarInt: component_type
            - component_data (varies by type)
          - For each removed component:
            - VarInt: component_type
        """
        item_id = buf.read_varint()
        
        if item_id == 0:  # Empty slot
            return Item(item_id=0, count=0)
        
        # Read count (in 1.21.4, count is the first component or separate)
        count = buf.read_value(StructFormat.BYTE)
        
        # Read components
        added_count = buf.read_varint()
        removed_count = buf.read_varint()
        
        components = ItemComponents()
        
        # Parse added components
        for _ in range(added_count):
            component_type = buf.read_varint()
            self._parse_component(buf, component_type, components)
        
        # Skip removed components (just IDs)
        for _ in range(removed_count):
            buf.read_varint()
        
        return Item(item_id=item_id, count=count, components=components)
    
    def _parse_component(self, buf: Buffer, component_type: int, components: ItemComponents) -> None:
        """
        Parse a single component by type.
        
        Args:
            buf: Buffer to read from
            component_type: Component type ID
            components: ItemComponents to populate
        """
        from .components import ComponentType
        
        try:
            comp_type = ComponentType(component_type)
        except ValueError:
            # Unknown component, skip it
            return
        
        if comp_type == ComponentType.CUSTOM_DATA:
            # NBT compound - simplified skip
            pass  # TODO: Parse NBT
        
        elif comp_type == ComponentType.MAX_STACK_SIZE:
            components.max_stack_size = buf.read_varint()
        
        elif comp_type == ComponentType.MAX_DAMAGE:
            components.max_damage = buf.read_varint()
        
        elif comp_type == ComponentType.DAMAGE:
            components.damage = buf.read_varint()
        
        elif comp_type == ComponentType.UNBREAKABLE:
            components.unbreakable = True
            # Optional show_in_tooltip boolean
            if buf.remaining() > 0:
                buf.read_value(StructFormat.BOOL)
        
        elif comp_type == ComponentType.CUSTOM_NAME:
            import json
            json_str = buf.read_utf()
            try:
                data = json.loads(json_str)
                from .components import TextComponent
                if isinstance(data, str):
                    components.custom_name = TextComponent(text=data)
                else:
                    components.custom_name = TextComponent.from_dict(data)
            except:
                pass
        
        elif comp_type == ComponentType.LORE:
            import json
            from .components import TextComponent
            count = buf.read_varint()
            components.lore = []
            for _ in range(count):
                json_str = buf.read_utf()
                try:
                    data = json.loads(json_str)
                    if isinstance(data, str):
                        components.lore.append(TextComponent(text=data))
                    else:
                        components.lore.append(TextComponent.from_dict(data))
                except:
                    pass
        
        elif comp_type == ComponentType.ENCHANTMENTS:
            count = buf.read_varint()
            for _ in range(count):
                ench_id = buf.read_utf()
                level = buf.read_varint()
                components.enchantments.append(Enchantment(id=ench_id, level=level))
        
        elif comp_type == ComponentType.HIDE_TOOLTIP:
            components.hide_tooltip = True
        
        elif comp_type == ComponentType.FIRE_RESISTANT:
            components.fire_resistant = True
        
        # Other components can be added as needed
    
    def _parse_metadata_value(self, buf: Buffer, type_id: int) -> Any:
        """
        Parse an entity metadata value by type.
        
        Metadata types in 1.21.4:
        0=byte, 1=varint, 2=float, 3=string, 4=text_component,
        5=slot, 6=boolean, 7=rotation, 8=position, 9=optional_position,
        10=direction, 11=optional_uuid, 12=block_state, 13=optional_block_state,
        14=nbt, 15=particle, 16=particles, 17=silent, 18=pose,
        19=cat_variant, 20=frog_variant, 21=optional_global_pos,
        22=painting_variant, 23=sniffer_state, 24=vector3f, 25=quaternionf
        """
        if type_id == 0:  # byte
            return buf.read_value(StructFormat.BYTE)
        elif type_id == 1:  # varint
            return buf.read_varint()
        elif type_id == 2:  # float
            return buf.read_value(StructFormat.FLOAT)
        elif type_id == 3:  # string
            return buf.read_utf()
        elif type_id == 4:  # text_component (JSON)
            json_str = buf.read_utf()
            try:
                import json
                return json.loads(json_str)
            except:
                return json_str
        elif type_id == 5:  # slot (item)
            return self._parse_slot(buf)
        elif type_id == 6:  # boolean
            return buf.read_value(StructFormat.BOOL)
        elif type_id == 7:  # rotation (3 floats)
            return (
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT)
            )
        elif type_id == 8:  # position (x, y, z as long)
            pos_long = buf.read_value(StructFormat.LONG)
            x = pos_long >> 38
            y = (pos_long >> 26) & 0xFFF
            z = pos_long << 38 >> 38
            if x >= 2**25: x -= 2**26
            if y >= 2**11: y -= 2**12
            if z >= 2**25: z -= 2**26
            return (x, y, z)
        elif type_id == 9:  # optional_position
            has_pos = buf.read_value(StructFormat.BOOL)
            if has_pos:
                return self._parse_metadata_value(buf, 8)
            return None
        elif type_id == 10:  # direction (varint enum)
            return buf.read_varint()
        elif type_id == 11:  # optional_uuid
            has_uuid = buf.read_value(StructFormat.BOOL)
            if has_uuid:
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
            return None
        elif type_id == 12:  # block_state (varint)
            return buf.read_varint()
        elif type_id == 13:  # optional_block_state
            has_state = buf.read_value(StructFormat.BOOL)
            if has_state:
                return buf.read_varint()
            return None
        elif type_id == 14:  # nbt
            return parse_nbt_data(BufferReader(bytes(buf.read(buf.remaining))))
        elif type_id == 15:  # particle
            # Skip particle data (complex)
            buf.read_varint()  # particle id
            return None
        elif type_id == 16:  # particles (list)
            count = buf.read_varint()
            for _ in range(count):
                self._parse_metadata_value(buf, 15)  # Skip each particle
            return None
        elif type_id == 17:  # silent (boolean)
            return buf.read_value(StructFormat.BOOL)
        elif type_id == 18:  # pose (varint enum)
            return buf.read_varint()
        elif type_id == 19:  # cat_variant (varint)
            return buf.read_varint()
        elif type_id == 20:  # frog_variant (varint)
            return buf.read_varint()
        elif type_id == 21:  # optional_global_pos
            has_pos = buf.read_value(StructFormat.BOOL)
            if has_pos:
                buf.read_utf()  # dimension
                self._parse_metadata_value(buf, 8)  # position
            return None
        elif type_id == 22:  # painting_variant (varint)
            return buf.read_varint()
        elif type_id == 23:  # sniffer_state (varint)
            return buf.read_varint()
        elif type_id == 24:  # vector3f
            return (
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT)
            )
        elif type_id == 25:  # quaternionf
            return (
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT)
            )
        else:
            # Unknown type, return None
            return None
    
    # Entity helper methods
    
    def nearest_entity(self, entity_type: Optional[str] = None, 
                       max_distance: float = 16.0) -> Optional[Entity]:
        """
        Find the nearest entity to the bot.
        
        Args:
            entity_type: Optional filter ('player', 'mob', 'object', etc.)
            max_distance: Maximum distance to search
            
        Returns:
            Nearest Entity or None
        """
        from .entities import EntityType
        
        etype_map = {
            'player': EntityType.PLAYER,
            'mob': EntityType.MOB,
            'object': EntityType.OBJECT,
        }
        
        etype = etype_map.get(entity_type) if entity_type else None
        return self.entity_manager.nearest(self.position, entity_type=etype, max_distance=max_distance)
    
    def nearest_player(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find the nearest player to the bot."""
        return self.entity_manager.nearest_player(self.position, max_distance)
    
    def nearest_hostile(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find the nearest hostile mob to the bot."""
        return self.entity_manager.nearest_hostile(self.position, max_distance)
    
    def nearest_passive(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find the nearest passive mob to the bot."""
        return self.entity_manager.nearest_passive(self.position, max_distance)
    
    def entities_at_position(self, position: Tuple[float, float, float], 
                             distance: float = 1.0) -> List[Entity]:
        """Get all entities within a distance of a position."""
        return self.entity_manager.in_range(position, distance)

    # Block helper methods
    
    def findBlock(self, block_type: str, options: Optional[Dict] = None) -> List[Block]:
        """
        Find blocks matching a type in loaded chunks.
        
        Args:
            block_type: Block name (e.g., "minecraft:chest") or "chest"
            options: {
                maxDistance: max distance to search (default: 16)
                count: max number of blocks to return (default: 1)
                point: center point for search (default: bot position)
            }
        
        Returns:
            List of Block objects sorted by distance
        """
        import math
        options = options or {}
        max_distance = options.get('maxDistance', 16)
        count = options.get('count', 1)
        center = options.get('point', self.position)
        
        results = []
        
        # Normalize block type
        if not block_type.startswith('minecraft:'):
            block_type = f'minecraft:{block_type}'
        
        # Check all loaded chunks
        for chunk_key, chunk in self.world.chunks.items():
            chunk_x, chunk_z = chunk_key
            base_x = chunk_x * 16
            base_z = chunk_z * 16
            
            for section_y, section in chunk.sections.items():
                if not section or not section.blocks:
                    continue
                
                for local_x in range(16):
                    for local_y in range(16):
                        for local_z in range(16):
                            try:
                                idx = local_x + local_z * 16 + local_y * 256
                                block_id = section.blocks[idx]
                                if block_id == 0:
                                    continue
                                
                                world_x = base_x + local_x
                                world_y = (section_y * 16) + local_y
                                world_z = base_z + local_z
                                
                                # Check block type
                                block_name = get_block_name(block_id)
                                if block_name != block_type:
                                    continue
                                
                                # Check distance
                                dist = math.sqrt(
                                    (world_x - center[0])**2 +
                                    (world_y - center[1])**2 +
                                    (world_z - center[2])**2
                                )
                                
                                if dist <= max_distance:
                                    block = Block(state_id=block_id, position=(world_x, world_y, world_z))
                                    results.append((dist, block))
                            except:
                                pass
        
        # Sort by distance and return
        results.sort(key=lambda x: x[0])
        return [b for _, b in results[:count]]

    def findBlocks(self, block_type: str, options: Optional[Dict] = None) -> List[Block]:
        """Find multiple blocks matching type."""
        options = options or {}
        options['count'] = options.get('count', 10)
        return self.findBlock(block_type, options)

    def blocksInRadius(self, center: Tuple[float, float, float], 
                       radius: float, 
                       options: Optional[Dict] = None) -> List[Block]:
        """
        Get all blocks within radius of center.
        
        Args:
            center: (x, y, z) center point
            radius: search radius
            options: {except: list of block types to exclude}
        
        Returns:
            List of Block objects
        """
        import math
        options = options or {}
        exclude = options.get('except', [])
        
        results = []
        radius_sq = radius * radius
        cx, cy, cz = center
        
        # Calculate chunk bounds
        min_cx = int((cx - radius) // 16)
        max_cx = int((cx + radius) // 16)
        min_cz = int((cz - radius) // 16)
        max_cz = int((cz + radius) // 16)
        
        for chunk_x in range(min_cx, max_cx + 1):
            for chunk_z in range(min_cz, max_cz + 1):
                chunk = self.world.chunks.get((chunk_x, chunk_z))
                if not chunk:
                    continue
                
                base_x = chunk_x * 16
                base_z = chunk_z * 16
                
                for section_y, section in chunk.sections.items():
                    if not section or not section.blocks:
                        continue
                    
                    for local_x in range(16):
                        for local_y in range(16):
                            for local_z in range(16):
                                try:
                                    idx = local_x + local_z * 16 + local_y * 256
                                    block_id = section.blocks[idx]
                                    if block_id == 0:
                                        continue
                                    
                                    world_x = base_x + local_x
                                    world_y = (section_y * 16) + local_y
                                    world_z = base_z + local_z
                                    
                                    # Check distance
                                    dist_sq = (world_x - cx)**2 + (world_y - cy)**2 + (world_z - cz)**2
                                    if dist_sq > radius_sq:
                                        continue
                                    
                                    # Check exclude list
                                    block_name = get_block_name(block_id)
                                    if block_name in exclude:
                                        continue
                                    
                                    block = Block(state_id=block_id, position=(world_x, world_y, world_z))
                                    results.append(block)
                                except:
                                    pass
        
        return results

    def blockAtFace(self, position: Tuple[int, int, int], face: str) -> Optional[Block]:
        """
        Get block at position + face direction.
        
        Args:
            position: (x, y, z) block position
            face: 'up', 'down', 'north', 'south', 'east', 'west'
        
        Returns:
            Block object or None
        """
        faces = {
            'up': (0, 1, 0), 'top': (0, 1, 0),
            'down': (0, -1, 0), 'bottom': (0, -1, 0),
            'north': (0, 0, -1),
            'south': (0, 0, 1),
            'east': (1, 0, 0),
            'west': (-1, 0, 0),
        }
        
        if face not in faces:
            return None
        
        dx, dy, dz = faces[face]
        x, y, z = position
        return self.block_at(x + dx, y + dy, z + dz)

    def canDigBlock(self, position: Tuple[int, int, int]) -> bool:
        """
        Check if block can be dug.
        
        Args:
            position: (x, y, z) block position
        
        Returns:
            True if block can be dug
        """
        import math
        
        block = self.block_at(*position)
        if not block or block.state_id == 0:  # Air
            return False
        
        # Check distance (max reach ~5 blocks)
        bx, by, bz = position
        px, py, pz = self.position
        dist = math.sqrt((bx - px)**2 + (by - py)**2 + (bz - pz)**2)
        if dist > 5.0:
            return False
        
        # Check if breakable
        block_name = get_block_name(block.state_id)
        unbreakable = ['minecraft:bedrock', 'minecraft:barrier', 'minecraft:structure_void', 
                       'minecraft:end_portal_frame', 'minecraft:reinforced_deepslate']
        if block_name in unbreakable:
            return False
        
        return True

    def canSeeBlock(self, position: Tuple[int, int, int]) -> bool:
        """
        Check if there's a clear line of sight to block (simple raycast).
        
        Args:
            position: (x, y, z) block position
        
        Returns:
            True if block is visible
        """
        import math
        
        px, py, pz = self.position
        # Bot eye position (1.62 blocks above feet)
        start = (px, py + 1.62, pz)
        
        bx, by, bz = position
        # Block center
        end = (bx + 0.5, by + 0.5, bz + 0.5)
        
        # Direction
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist == 0:
            return True
        
        # Normalize
        dx /= dist
        dy /= dist
        dz /= dist
        
        # Step along ray (0.5 block resolution)
        steps = int(dist * 2)
        for i in range(1, steps):
            t = i / steps * dist
            check_x = int(start[0] + dx * t)
            check_y = int(start[1] + dy * t)
            check_z = int(start[2] + dz * t)
            
            # Skip target block
            if (check_x, check_y, check_z) == (bx, by, bz):
                continue
            
            block = self.block_at(check_x, check_y, check_z)
            if block and block.state_id != 0 and is_solid(block.state_id):
                return False
        return True

    # Digging helper methods
    
    def dig_time(self, block) -> float:
        """
        Calculate time to dig a block in milliseconds.
        
        Args:
            block: Block object or block name string
        
        Returns:
            Time in milliseconds, or infinity if unbreakable
        """
        from .digging import calculate_dig_time
        
        if hasattr(block, 'name'):
            block_name = block.name
        elif hasattr(block, 'state_id'):
            block_name = get_block_name(block.state_id)
        else:
            block_name = str(block)
        
        held_item = self.inventory.get(36 + self.held_item_slot)
        tool_name = held_item.name if held_item and not held_item.is_empty else None
        
        return calculate_dig_time(block_name, tool_name)

    def can_harvest(self, block, tool=None) -> bool:
        """
        Check if a block can be harvested (drop items when broken).
        
        Args:
            block: Block object or block name
            tool: Tool item (uses held item if None)
        
        Returns:
            True if block can be harvested
        """
        from .digging import can_harvest as check_harvest
        
        if hasattr(block, 'name'):
            block_name = block.name
        elif hasattr(block, 'state_id'):
            block_name = get_block_name(block.state_id)
        else:
            block_name = str(block)
        
        if tool is None:
            held_item = self.inventory.get(36 + self.held_item_slot)
            tool = held_item.name if held_item and not held_item.is_empty else None
        
        return check_harvest(block_name, tool)

    def best_tool(self, block) -> Optional[Item]:
        """
        Find the best tool in inventory for mining a block.
        
        Args:
            block: Block object or block name
        
        Returns:
            Best tool Item or None
        """
        from .digging import get_best_tool_for_block, get_tool_type
        
        if hasattr(block, 'name'):
            block_name = block.name
        elif hasattr(block, 'state_id'):
            block_name = get_block_name(block.state_id)
        else:
            block_name = str(block)
        
        tools = []
        for slot, item in self.inventory.items():
            if item and not item.is_empty:
                tool_type = get_tool_type(item.name)
                if tool_type:
                    tools.append(item.name)
        
        best = get_best_tool_for_block(block_name, tools)
        
        if best:
            for slot, item in self.inventory.items():
                if item and item.name == best:
                    return item
        
        return None

    def tool_tier(self, item) -> int:
        """
        Get the mining tier of a tool.
        
        Args:
            item: Item object or item name
        
        Returns:
            Tool tier (0=wood, 1=stone, 2=iron, 3=diamond, 4=netherite) or -1
        """
        from .digging import get_tool_tier as get_tier
        
        if hasattr(item, 'name'):
            return get_tier(item.name)
        return get_tier(str(item))

    def tool_type(self, item) -> Optional[str]:
        """
        Get the type of a tool.
        
        Args:
            item: Item object or item name
        
        Returns:
            Tool type ('pickaxe', 'axe', 'shovel', 'hoe') or None
        """
        from .digging import get_tool_type as get_type
        
        if hasattr(item, 'name'):
            return get_type(item.name)
        return get_type(str(item))

    async def send_set_held_slot(self, slot: int) -> None:
        """
        Set the held item slot (0x28 for 1.21.4)
        
        Args:
            slot: Hotbar slot (0-8)
        """
        if not 0 <= slot <= 8:
            return
        
        buf = Buffer()
        buf.write_value(StructFormat.SHORT, slot)
        await self._write_packet(0x28, bytes(buf))
        self.held_item_slot = slot
    
    async def send_close_container(self, container_id: Optional[int] = None) -> None:
        """
        Close container (0x12 for 1.21.4)
        
        Args:
            container_id: Container ID (uses open_container_id if None)
        """
        cid = container_id if container_id is not None else self.open_container_id
        if cid is None:
            return
        
        buf = Buffer()
        buf.write_value(StructFormat.BYTE, cid)
        await self._write_packet(0x12, bytes(buf))
        
        self.open_container_id = None
        self.emit("container_close", cid)
    
    async def send_container_click(
        self, 
        container_id: int,
        slot: int,
        button: int = 0,
        mode: int = 0,
        item: Optional[Item] = None,
        changes: Optional[List[Tuple[int, Item]]] = None
    ) -> None:
        """
        Click container slot (0x11 for 1.21.4)
        
        Args:
            container_id: Container window ID (0 = player inventory)
            slot: Slot index (-999 for cursor/outside)
            button: Mouse button (0=left, 1=right, 2=middle)
            mode: ClickMode enum value (PICKUP=0, QUICK_MOVE=1, SWAP=2, etc.)
            item: Item being held on cursor (for verification)
            changes: List of (slot, item) changes for QUICK_CRAFT mode
        """
        self._inventory_sequence += 1
        
        buf = Buffer()
        buf.write_value(StructFormat.BYTE, container_id)
        buf.write_value(StructFormat.SHORT, slot)
        buf.write_value(StructFormat.BYTE, button)
        buf.write_value(StructFormat.SHORT, mode)
        
        # Write changes array
        if changes:
            buf.write_varint(len(changes))
            for change_slot, change_item in changes:
                buf.write_value(StructFormat.SHORT, change_slot)
                if change_item and not change_item.is_empty:
                    buf.write_varint(change_item.item_id)
                    buf.write_value(StructFormat.BYTE, change_item.count)
                    buf.write_varint(0)  # No components
                else:
                    buf.write_varint(0)  # Empty
        else:
            buf.write_varint(0)  # No changes
        
        # Write clicked item (cursor item)
        if item and not item.is_empty:
            buf.write_varint(item.item_id)
            buf.write_value(StructFormat.BYTE, item.count)
            buf.write_varint(0)  # No components
        else:
            buf.write_varint(0)  # Empty item
        
        buf.write_varint(self._inventory_sequence)
        
        await self._write_packet(0x11, bytes(buf))
    
    async def craft(self, recipe_type: str = "inventory") -> bool:
        """
        Attempt to craft using the 2x2 inventory grid.
        
        This is a simplified implementation that:
        1. Assumes items are already in the correct slots
        2. Clicks the output slot to retrieve crafted item
        
        For complex crafting, use:
        - send_container_click() directly
        - Or implement a recipe matcher
        
        Args:
            recipe_type: "inventory" for 2x2 grid, "table" for 3x3
            
        Returns:
            True if crafting was initiated
        """
        # Output slot for inventory crafting is slot 0
        # Output slot for crafting table is slot 0
        output_slot = 0
        
        if self.open_container_id is not None:
            # Container is open (crafting table)
            container_id = self.open_container_id
        else:
            # Use player inventory
            # Inventory crafting grid slots are 1-4 (2x2)
            # Output is slot 0
            container_id = 0  # Player inventory
        
        print(f"[CRAFT] Clicking output slot {output_slot} in container {container_id}")
        
        # Click output slot to take crafted item
        await self.send_container_click(
            container_id=container_id,
            slot=output_slot,
            button=0,
            mode=0,
            item=None
        )
        
        self.emit("craft", recipe_type)
        return True
    
    def find_item(self, item_name: str) -> List[Item]:
        """
        Find all items matching a name in inventory.
        
        Args:
            item_name: Item name to search for
            
        Returns:
            List of matching Item objects
        """
        found = []
        for slot, item in self.inventory.items():
            if item.name == item_name or item.item_id == int(item_name) if item_name.isdigit() else False:
                found.append(item)
        return found
    
    def count_item(self, item_name: str) -> int:
        """
        Count total items of a type in inventory.
        
        Args:
            item_name: Item name to count
            
        Returns:
            Total count
        """
        total = 0
        for item in self.inventory.values():
            if item.name == item_name:
                total += item.count
        return total
    
    # ============= CONVENIENCE CLICK METHODS =============
    
    async def left_click(self, slot: int, container_id: int = 0) -> None:
        """
        Left click on a slot (pickup or place item).
        
        Args:
            slot: Slot index
            container_id: Container ID (0 = player inventory)
        """
        cursor_item = self._cursor_item
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP,
            item=cursor_item
        )
    
    async def right_click(self, slot: int, container_id: int = 0) -> None:
        """
        Right click on a slot (place one item).
        
        Args:
            slot: Slot index
            container_id: Container ID (0 = player inventory)
        """
        cursor_item = self._cursor_item
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.RIGHT,
            mode=ClickMode.PICKUP,
            item=cursor_item
        )
    
    async def shift_click(self, slot: int, container_id: int = 0) -> None:
        """
        Shift+click on a slot (quick move to other inventory).
        
        Moves item between player inventory and open container.
        - From inventory to container (if container open)
        - From container to inventory
        - In inventory: moves between hotbar and main inventory
        
        Args:
            slot: Slot index
            container_id: Container ID (0 = player inventory)
        """
        item = self.inventory.get(slot)
        if not item or item.is_empty:
            print(f"[CLICK] shift_click on empty slot {slot}")
            return
        
        print(f"[CLICK] shift_click slot {slot}: {item}")
        
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.QUICK_MOVE,
            item=item
        )
    
    async def drop_slot(self, slot: int, drop_stack: bool = False, container_id: int = 0) -> None:
        """
        Drop item from a slot.
        
        Args:
            slot: Slot index
            drop_stack: If True, drop entire stack. If False, drop one item.
            container_id: Container ID (0 = player inventory)
        """
        item = self.inventory.get(slot)
        if not item or item.is_empty:
            print(f"[CLICK] drop_slot on empty slot {slot}")
            return
        
        button = ClickButton.RIGHT if drop_stack else ClickButton.LEFT
        action = "stack" if drop_stack else "one"
        print(f"[CLICK] Dropping {action} from slot {slot}: {item}")
        
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=button,
            mode=ClickMode.THROW,
            item=item
        )
    
    async def swap_hotbar(self, slot: int, hotbar_slot: int, container_id: int = 0) -> None:
        """
        Swap item between slot and hotbar.
        
        Args:
            slot: Source slot index
            hotbar_slot: Hotbar slot (0-8)
            container_id: Container ID (0 = player inventory)
        """
        if not 0 <= hotbar_slot <= 8:
            print(f"[CLICK] Invalid hotbar slot: {hotbar_slot}")
            return
        
        item = self.inventory.get(slot)
        print(f"[CLICK] Swapping slot {slot} with hotbar {hotbar_slot}")
        
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=hotbar_slot,
            mode=ClickMode.SWAP,
            item=item
        )
    
    async def pickup_all(self, slot: int, container_id: int = 0) -> None:
        """
        Double-click to pickup all items of the same type.
        
        Picks up all matching items from inventory onto cursor.
        
        Args:
            slot: Slot index to start from
            container_id: Container ID (0 = player inventory)
        """
        item = self.inventory.get(slot)
        cursor_item = self._cursor_item
        
        print(f"[CLICK] Pickup all from slot {slot}")
        
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP_ALL,
            item=cursor_item
        )
    
    async def clone_item(self, slot: int, container_id: int = 0) -> None:
        """
        Clone item (middle click, creative mode only).
        
        Args:
            slot: Slot index
            container_id: Container ID (0 = player inventory)
        """
        if self.game.game_mode != 'creative':
            print("[CLICK] clone_item only works in creative mode")
            return
        
        item = self.inventory.get(slot)
        if not item or item.is_empty:
            return
        
        print(f"[CLICK] Cloning item at slot {slot}: {item}")
        
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.MIDDLE,
            mode=ClickMode.CLONE,
            item=item
        )
    
    async def drop_cursor(self) -> None:
        """
        Drop the item currently held by cursor.
        
        Clicks outside the inventory (slot -999).
        """
        if not self._cursor_item or self._cursor_item.is_empty:
            return
        
        print(f"[CLICK] Dropping cursor item: {self._cursor_item}")
        
        # Click outside inventory to drop
        await self.send_container_click(
            container_id=0,
            slot=-999,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP,
            item=self._cursor_item
        )
        self._cursor_item = None
    async def handle_login_packet(self, packet_id: int, buf: Buffer) -> None:
        """Handle login state packets"""
        if packet_id == 0x00:  # Disconnect
            reason = buf.read_utf()
            print(f"Disconnected during login: {reason}")
            self.emit("kicked", reason)
            self._running = False

        elif packet_id == 0x01:  # Encryption Request
            print("Server requested encryption (online mode)")
            self._running = False

        elif packet_id == 0x02:  # Login Success
            uuid_bytes = buf.read(16)
            uuid_int = int.from_bytes(uuid_bytes, "big")
            self.uuid = f"{uuid_int:032x}"
            self.uuid = f"{self.uuid[:8]}-{self.uuid[8:12]}-{self.uuid[12:16]}-{self.uuid[16:20]}-{self.uuid[20:]}"

            self.username = buf.read_utf()

            property_count = buf.read_varint()
            for _ in range(property_count):
                buf.read_utf()
                buf.read_utf()
                has_signature = buf.read_value(StructFormat.BOOL)
                if has_signature:
                    buf.read_utf()

            print(f"Login successful! UUID: {self.uuid}, Username: {self.username}")
            self.emit("login")

            await self.send_login_acknowledged()
            # Send client information after transitioning to configuration state
            await self.send_client_information()

        elif packet_id == 0x03:  # Set Compression
            self.compression_threshold = buf.read_varint()
            print(f"Compression enabled, threshold: {self.compression_threshold}")

        else:
            print(f"Unknown login packet: ID=0x{packet_id:02X}")

    async def handle_configuration_packet(self, packet_id: int, buf: Buffer) -> None:
        """Handle configuration state packets"""
        # Configuration state packets for 1.21.4
        if packet_id == 0x00:  # Cookie Request
            print("Configuration: Cookie Request")
            # Read the key and respond with empty cookie
            key = buf.read_utf()
            # Send Cookie Response (0x01) - has_cookie = False, no data
            resp_buf = Buffer()
            resp_buf.write_utf(key)  # Same key
            resp_buf.write_value(StructFormat.BOOL, False)  # has_cookie = False
            await self._write_packet(0x01, bytes(resp_buf))
            print(f"Configuration: Cookie Response sent for {key}")
            print("Configuration: Plugin Message")
        elif packet_id == 0x02:  # Disconnect
            reason = buf.read_utf()
            print(f"Disconnected during configuration: {reason}")
            self.emit("kicked", reason)
            self._running = False
        elif packet_id == 0x03:  # Finish Configuration
            print("Configuration: Finish Configuration received!")
            await self.send_acknowledge_finish_configuration()
        elif packet_id == 0x04:  # Keep Alive (config)
            keep_alive_id = buf.read_value(StructFormat.LONGLONG)  # LONG = 8 bytes
            # Respond with serverbound keep alive (0x04 in config)
            resp_buf = Buffer()
            resp_buf.write_value(StructFormat.LONGLONG, keep_alive_id)
            await self._write_packet(0x04, bytes(resp_buf))
            print("Configuration: Keep Alive responded")
        elif packet_id == 0x05:  # Ping
            ping_id = buf.read_value(StructFormat.INT)
            # Respond with pong (0x05 in config)
            resp_buf = Buffer()
            resp_buf.write_value(StructFormat.INT, ping_id)
            await self._write_packet(0x05, bytes(resp_buf))
            print("Configuration: Pong sent")
        elif packet_id == 0x07:  # Registry Data
            print("Configuration: Registry Data received")
        elif packet_id == 0x0C:  # Feature Flags
            print("Configuration: Feature Flags received")
        elif packet_id == 0x0D:  # Update Tags
            print("Configuration: Update Tags received")
        elif packet_id == 0x0E:  # Clientbound Known Packs
            print("Configuration: Known Packs received")
            # Send our known packs
            await self.send_known_packs()
        else:
            print(
                f"Configuration packet: ID=0x{packet_id:02X}, remaining={buf.remaining} bytes"
            )

    async def handle_play_packet(self, packet_id: int, buf: Buffer) -> None:
        """Handle play state packets"""
        if packet_id == 0x27:  # Keep Alive (clientbound) - 1.21.4
            keep_alive_id = buf.read_value(StructFormat.LONGLONG)  # LONG = 8 bytes
            await self.send_keep_alive(keep_alive_id)

        elif packet_id == 0x2C:  # Login (Join Game) - 1.21.4
            print("Received Join Game packet!")
            self.entity_id = buf.read_value(StructFormat.INT)
            is_hardcore = buf.read_value(StructFormat.BOOL)
            self.game.hardcore = is_hardcore

            dim_count = buf.read_varint()
            for _ in range(dim_count):
                buf.read_utf()

            self.game.max_players = buf.read_varint()
            self.game.server_view_distance = buf.read_varint()
            buf.read_varint()  # simulation distance
            buf.read_value(StructFormat.BOOL)  # reduced debug
            self.game.enable_respawn_screen = buf.read_value(StructFormat.BOOL)
            buf.read_value(StructFormat.BOOL)  # do limited crafting

            dimension_type = buf.read_varint()
            dimension_name = buf.read_utf()
            self.game.dimension = dimension_name.replace('minecraft:', '')
            
            buf.read_value(StructFormat.LONG)  # hashed seed

            game_mode_byte = buf.read_value(StructFormat.BYTE)
            self.game_mode = game_mode_byte
            self.game.game_mode = parse_game_mode(game_mode_byte)
            
            buf.read_value(StructFormat.BYTE)  # prev game mode
            is_debug = buf.read_value(StructFormat.BOOL)
            is_flat = buf.read_value(StructFormat.BOOL)
            
            self.game.level_type = 'flat' if is_flat else ('debug' if is_debug else 'default')

            has_death_loc = buf.read_value(StructFormat.BOOL)
            if has_death_loc:
                buf.read_utf()
                buf.read(8)

            buf.read_varint()  # portal cooldown
            buf.read_varint()  # sea level
            buf.read_value(StructFormat.BOOL)  # enforces secure chat

            print(f"Joined game! Entity ID: {self.entity_id}")
            print(f"[GAME] Mode: {self.game.game_mode}, Dimension: {self.game.dimension}, Hardcore: {self.game.hardcore}")
            
            # Create bot's own entity
            self.entity = {
                'id': self.entity_id,
                'type': 'player',
                'username': self.username,
                'uuid': self.uuid,
                'position': self.position,
                'yaw': self.yaw,
                'pitch': self.pitch,
                'on_ground': self.on_ground,
            }
            self.entities[self.entity_id] = self.entity
            
            self.emit("spawn")
            self.emit("login")
            self.emit("game")

        elif packet_id == 0x42:  # Synchronize Player Position - 1.21.4
            teleport_id = buf.read_varint()
            x = buf.read_value(StructFormat.DOUBLE)
            y = buf.read_value(StructFormat.DOUBLE)
            z = buf.read_value(StructFormat.DOUBLE)
            buf.read_value(StructFormat.DOUBLE)  # vx
            buf.read_value(StructFormat.DOUBLE)  # vy
            buf.read_value(StructFormat.DOUBLE)  # vz
            yaw = buf.read_value(StructFormat.FLOAT)
            pitch = buf.read_value(StructFormat.FLOAT)
            buf.read_value(StructFormat.INT)  # flags

            self.position = (x, y, z)
            self.yaw = yaw
            self.pitch = pitch

            print(f"Position synchronized: {self.position}")

            # Confirm teleportation
            confirm_buf = Buffer()
            confirm_buf.write_varint(teleport_id)
            await self._write_packet(0x00, bytes(confirm_buf))

            # Send player position
            await self.send_player_position()

        elif packet_id == 0x1A:  # Disconnect (play)
            reason = buf.read_utf()
            print(f"Disconnected: {reason}")
            self.emit("kicked", reason)
            self._running = False

        elif packet_id == 0x3D:  # Respawn - 1.21.4
            print("Received Respawn packet!")
            # Respawn packet has same structure as Join Game for dimension info
            dimension_type = buf.read_varint()
            dimension_name = buf.read_utf()
            
            # Update game state
            self.game.dimension = dimension_name.replace('minecraft:', '')
            
            # Skip rest of packet
            buf.read_value(StructFormat.LONG)  # hashed seed
            game_mode_byte = buf.read_value(StructFormat.BYTE)
            self.game.game_mode = parse_game_mode(game_mode_byte)
            self.game.hardcore = bool(game_mode_byte & 0b1000)
            
            buf.read_value(StructFormat.BYTE)  # prev game mode
            buf.read_value(StructFormat.BOOL)  # is debug
            buf.read_value(StructFormat.BOOL)  # is flat
            
            has_death_loc = buf.read_value(StructFormat.BOOL)
            if has_death_loc:
                buf.read_utf()
                buf.read(8)
            
            buf.read_varint()  # portal cooldown
            buf.read_varint()  # sea level
            
            print(f"[GAME] Respawned in {self.game.dimension}, mode: {self.game.game_mode}")
            self.emit("respawn")
            self.emit("game")

        elif packet_id == 0x4A:  # Game State Change - 1.21.4
            reason = buf.read_value(StructFormat.UBYTE)
            game_mode_float = buf.read_value(StructFormat.FLOAT)
            game_mode = int(game_mode_float)
            
            if reason == 3:  # Change game mode
                self.game.game_mode = parse_game_mode(game_mode)
                print(f"[GAME] Game mode changed to: {self.game.game_mode}")
                self.emit("game")
            elif reason == 4:  # Win game (credits)
                if game_mode == 1:
                    # Send client command to close credits (respawn)
                    cmd_buf = Buffer()
                    cmd_buf.write_varint(0)  # Perform respawn
                    await self._write_packet(0x0D, bytes(cmd_buf))  # Client Command

        elif packet_id == 0x4E:  # Update Time - 1.21.4
            world_age = buf.read_value(StructFormat.LONG)
            time_of_day = buf.read_value(StructFormat.LONG)
            
            self.game.age = world_age
            self.game.time = time_of_day
            self.emit("time")

        elif packet_id == 0x52:  # Update Health - 1.21.4
            health = buf.read_value(StructFormat.FLOAT)
            food = buf.read_varint()
            food_saturation = buf.read_value(StructFormat.FLOAT)
            
            old_health = self.health
            self.health = health
            self.food = food
            self.food_saturation = food_saturation
            
            self.emit("health")
            
            if health <= 0:
                # Player is dead
                if self.is_alive:
                    self.is_alive = False
                    print(f"[HEALTH] Death! Health: {health}")
                    self.emit("death")
                # Auto-respawn if configured (default: True)
                if self._auto_respawn:
                    await self.respawn()
            elif health > 0 and not self.is_alive:
                # Player respawned
                self.is_alive = True
                print(f"[HEALTH] Spawned! Health: {health}")
                self.emit("spawn")

        elif packet_id == 0x3F:  # Player Info Remove - 1.21.4
            # Remove players from the player list
            count = buf.read_varint()
            for _ in range(count):
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                if uuid in self.players:
                    del self.players[uuid]
                    print(f"[ENTITIES] Player removed: {uuid}")

        elif packet_id == 0x40:  # Player Info Update - 1.21.4
            # Actions bitset
            actions_byte = buf.read_value(StructFormat.BYTE)
            
            # Number of players
            count = buf.read_varint()
            
            for _ in range(count):
                # Read UUID
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                
                # Initialize player if not exists
                if uuid not in self.players:
                    self.players[uuid] = {'uuid': uuid}
                
                # Action 0x01: Add Player (name, properties)
                if actions_byte & 0x01:
                    name = buf.read_utf()
                    self.players[uuid]['username'] = name
                    
                    # Properties count
                    prop_count = buf.read_varint()
                    for _ in range(prop_count):
                        buf.read_utf()  # name
                        buf.read_utf()  # value
                        has_sig = buf.read_value(StructFormat.BOOL)
                        if has_sig:
                            buf.read_utf()  # signature
                    
                    print(f"[ENTITIES] Player added: {name}")
                    self.emit("player_joined", self.players[uuid])
                
                # Action 0x02: Initialize Chat
                if actions_byte & 0x02:
                    has_chat = buf.read_value(StructFormat.BOOL)
                    if has_chat:
                        buf.read_utf()  # chat session
                        buf.read_value(StructFormat.LONG)  # timestamp
                        buf.read_value(StructFormat.LONG)  # public key
                
                # Action 0x04: Update Game Mode
                if actions_byte & 0x04:
                    game_mode = buf.read_varint()
                    self.players[uuid]['game_mode'] = game_mode
                
                # Action 0x08: Update Listed
                if actions_byte & 0x08:
                    listed = buf.read_value(StructFormat.BOOL)
                    self.players[uuid]['listed'] = listed
                
                # Action 0x10: Update Latency
                if actions_byte & 0x10:
                    latency = buf.read_varint()
                    self.players[uuid]['latency'] = latency
                
                # Action 0x20: Update Display Name
                if actions_byte & 0x20:
                    has_display = buf.read_value(StructFormat.BOOL)
                    if has_display:
                        display_name = buf.read_utf()
                        self.players[uuid]['display_name'] = display_name

        elif packet_id == 0x73:  # System Chat - 1.21.4
            # Read chat message (JSON text component)
            chat_json = buf.read_utf()
            overlay = buf.read_value(StructFormat.BOOL)
            
            # Parse JSON to extract plain text (simplified)
            try:
                import json
                data = json.loads(chat_json)
                text = self._extract_text(data)
            except:
                text = chat_json
            
            print(f"[CHAT] Received: {text}")
            self.emit("chat", text, chat_json, overlay)

        elif packet_id == 0x28:  # Level Chunk With Light - 1.21.4
            # Chunk X and Z
            chunk_x = buf.read_value(StructFormat.INT)
            chunk_z = buf.read_value(StructFormat.INT)
            
            # Create chunk column
            chunk = ChunkColumn(x=chunk_x, z=chunk_z, 
                               min_y=self.game.min_y if hasattr(self, 'game') else -64,
                               max_y=(self.game.min_y + self.game.height - 1) if hasattr(self, 'game') else 319)
            
            # Parse heightmaps (NBT)
            chunk_data = bytes(buf.read(buf.remaining))
            reader = BufferReader(chunk_data)
            
            try:
                # Try to parse heightmaps NBT
                heightmaps = parse_nbt(reader)
            except:
                # If NBT parsing fails, reset to start
                reader.offset = 0
            
            # Read data size (varint) - can be 0 for 1.20.5+
            try:
                data_size = reader.read_varint()
                
                if data_size > 0:
                    # Parse chunk sections from the data
                    section_count = (chunk.max_y - chunk.min_y + 1) // 16
                    
                    for section_y in range(chunk.min_y >> 4, (chunk.max_y >> 4) + 1):
                        if reader.remaining() < 10:
                            break
                        
                        try:
                            section = parse_chunk_section(reader, section_y)
                            chunk.set_section(section)
                        except Exception as e:
                            # Skip failed sections
                            pass
            except Exception as e:
                pass  # Data parsing failed, keep empty chunk
            
            # Store in world
            self.world.set_chunk(chunk)
            self._chunks_loaded += 1
            
            # Count non-empty sections
            section_count = len([s for s in chunk.sections.values() if s and s.blocks])
            
            # Only log occasionally to avoid spam
            if self._chunks_loaded <= 5 or self._chunks_loaded % 20 == 0:
                print(f"[CHUNKS] Loaded chunk ({chunk_x}, {chunk_z}), sections: {section_count}, total: {self._chunks_loaded}")
            
            self.emit("chunk_loaded", chunk_x, chunk_z)

        elif packet_id == 0x25:  # Forget Level Chunk (Unload) - 1.21.4
            chunk_x = buf.read_value(StructFormat.INT)
            chunk_z = buf.read_value(StructFormat.INT)
            
            self.world.unload_chunk(chunk_x, chunk_z)
            print(f"[CHUNKS] Unloaded chunk ({chunk_x}, {chunk_z})")
            
            self.emit("chunk_unloaded", chunk_x, chunk_z)

        elif packet_id == 0x09:  # Block Update - 1.21.4
            # Read position (x, y, z as long)
            pos_long = buf.read_value(StructFormat.LONG)
            x = pos_long >> 38
            y = (pos_long >> 26) & 0xFFF
            z = pos_long << 38 >> 38
            # Handle negative values
            if x >= 2**25: x -= 2**26
            if y >= 2**11: y -= 2**12
            if z >= 2**25: z -= 2**26
            
            # Read block state ID
            block_id = buf.read_varint()
            
            # Get old block before update
            old_block = self.block_at(x, y, z)
            
            # Update world
            self.world.set_block_state(x, y, z, block_id)
            
            # Create new block object
            new_block = Block(state_id=block_id, position=(x, y, z))
            
            self.emit("block_update", old_block, new_block)

        elif packet_id == 0x06:  # Block Break Animation - 1.21.4
            # Sent when another player is breaking a block
            entity_id = buf.read_varint()
            pos_long = buf.read_value(StructFormat.LONG)
            x = pos_long >> 38
            y = (pos_long >> 26) & 0xFFF
            z = pos_long << 38 >> 38
            # Handle negative values
            if x >= 2**25: x -= 2**26
            if y >= 2**11: y -= 2**12
            if z >= 2**25: z -= 2**26
            
            stage = buf.read_value(StructFormat.BYTE)
            
            if stage >= 0:
                # Store/update animation
                self._break_animations[entity_id] = {
                    'position': (x, y, z),
                    'stage': stage,
                    'progress': stage / 9.0  # 0.0 to 1.0
                }
                self.emit("block_break_progress", entity_id, (x, y, z), stage)
                self.emit("block_break_stop", entity_id, (x, y, z))
        
        elif packet_id == 0x08:  # Block Action - 1.21.4
            try:
                pos_long = buf.read_value(StructFormat.LONG)
                x = pos_long >> 38
                y = (pos_long >> 26) & 0xFFF
                z = pos_long << 38 >> 38
                if x >= 2**25: x -= 2**26
                if y >= 2**11: y -= 2**12
                if z >= 2**25: z -= 2**26
                
                action_id = buf.read_value(StructFormat.UBYTE)
                action_param = buf.read_value(StructFormat.UBYTE)
                
                position = (x, y, z)
                block = self.block_at(x, y, z)
                
                # Action types: chest open/close, note block, piston, etc.
                self.emit("block_action", position, action_id, action_param, block)
            except Exception as e:
                pass
        
        elif packet_id == 0x07:  # Block Entity Data - 1.21.4 (PLAY state)
            try:
                pos_long = buf.read_value(StructFormat.LONG)
                x = pos_long >> 38
                y = (pos_long >> 26) & 0xFFF
                z = pos_long << 38 >> 38
                if x >= 2**25: x -= 2**26
                if y >= 2**11: y -= 2**12
                if z >= 2**25: z -= 2**26
                
                entity_type = buf.read_varint()
                
                # Parse NBT data
                nbt_data = None
                if buf.remaining() > 0:
                    try:
                        reader = BufferReader(bytes(buf.read(buf.remaining())))
                        nbt_data = parse_nbt_data(reader)
                    except:
                        pass
                
                position = (x, y, z)
                
                # Store in world
                if not hasattr(self.world, 'block_entities'):
                    self.world.block_entities = {}
                self.world.block_entities[position] = {
                    'type': entity_type,
                    'data': nbt_data
                }
                
                self.emit("block_entity_data", position, entity_type, nbt_data)
            except Exception as e:
                pass
        
        elif packet_id == 0x10:  # Multi Block Change - 1.21.4
            try:
                section_pos = buf.read_value(StructFormat.LONG)
                section_x = section_pos >> 42
                section_z = (section_pos << 22) >> 42
                section_y = (section_pos << 44) >> 44
                if section_x >= 2**21: section_x -= 2**22
                if section_z >= 2**21: section_z -= 2**22
                
                trust_edges = buf.read_value(StructFormat.BOOL)
                block_count = buf.read_varint()
                
                for _ in range(block_count):
                    pos_byte = buf.read_value(StructFormat.UBYTE)
                    local_x = (pos_byte >> 4) & 0x0F
                    local_z = pos_byte & 0x0F
                    local_y = (pos_byte >> 8) & 0x0F
                    
                    # World position
                    x = (section_x * 16) + local_x
                    y = (section_y * 16) + local_y
                    z = (section_z * 16) + local_z
                    
                    block_id = buf.read_varint()
                    
                    # Update world
                    old_block = self.block_at(x, y, z)
                    self.world.set_block_state(x, y, z, block_id)
                    
                    # Emit event
                    new_block = Block(state_id=block_id, position=(x, y, z))
                    self.emit("block_update", old_block, new_block)
                    
            except Exception as e:
                pass

        elif packet_id == 0x14:  # Set Container Content - 1.21.4
            # Full container content update
            container_id = buf.read_value(StructFormat.BYTE)
            state_id = buf.read_varint()
            slot_count = buf.read_varint()
            
            # Read all slots
            new_inventory = {}
            for slot_idx in range(slot_count):
                item = self._parse_slot(buf)
                if item and not item.is_empty:
                    item.slot = slot_idx
                    new_inventory[slot_idx] = item
            
            # Read cursor item
            cursor_item = self._parse_slot(buf)
            self._cursor_item = cursor_item if not cursor_item.is_empty else None
            
            # Update inventory
            if container_id == 0:  # Player inventory
                self.inventory = new_inventory
            
            self.emit("inventory_update", container_id, new_inventory)
            
            if container_id == 0:
                print(f"[INVENTORY] Updated {len(new_inventory)} slots")

        elif packet_id == 0x15:  # Set Container Slot - 1.21.4
            # Single slot update
            container_id = buf.read_value(StructFormat.BYTE)
            state_id = buf.read_varint()
            slot = buf.read_value(StructFormat.SHORT)
            
            item = self._parse_slot(buf)
            
            if container_id == 0:  # Player inventory
                if item and not item.is_empty:
                    item.slot = slot
                    self.inventory[slot] = item
                elif slot in self.inventory:
                    del self.inventory[slot]
            
            self.emit("slot_update", container_id, slot, item)

        elif packet_id == 0x3B:  # Open Screen - 1.21.4
            # Server wants to open a container screen
            container_id = buf.read_value(StructFormat.BYTE)
            container_type = buf.read_varint()
            title = buf.read_utf()
            
            self.open_container_id = container_id
            print(f"[INVENTORY] Opened container {container_id}: {title}")
            self.emit("container_open", container_id, container_type, title)

        elif packet_id == 0x42:  # Declare Recipes - 1.21.4
            # Server sends all available recipes
            recipe_count = buf.read_varint()
            print(f"[RECIPES] Received {recipe_count} recipes")
            
            for _ in range(recipe_count):
                try:
                    recipe = self._parse_recipe(buf)
                    if recipe:
                        self.recipes.add(recipe)
                except Exception as e:
                    # Skip malformed recipes
                    pass
            
            
            print(f"[RECIPES] Loaded {len(self.recipes)} recipes into registry")
            self.emit("recipes_loaded", len(self.recipes))


        # === Entity Packets ===
        
        elif packet_id == 0x01:  # Spawn Entity - 1.21.4
            try:
                # Spawns an object entity (item, arrow, boat, etc.)
                entity_id = buf.read_varint()
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                
                entity_type_id = buf.read_varint()  # Object type
                
                x = buf.read_value(StructFormat.DOUBLE)
                y = buf.read_value(StructFormat.DOUBLE)
                z = buf.read_value(StructFormat.DOUBLE)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                head_yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                
                data = buf.read_varint()  # Object-specific data
                velocity_x = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_y = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_z = buf.read_value(StructFormat.SHORT) / 8000.0
                
                # Create entity
                from .entities import Entity, EntityType, ObjectType, get_object_name
                entity = Entity(
                    entity_id=entity_id,
                    uuid=uuid,
                    entity_type=EntityType.OBJECT,
                    position=(x, y, z),
                    yaw=yaw,
                    pitch=pitch,
                    head_yaw=head_yaw,
                    velocity=(velocity_x, velocity_y, velocity_z),
                    object_type=entity_type_id,
                    object_data=data,
                    name=get_object_name(ObjectType(entity_type_id)) if entity_type_id in iter(ObjectType) else f"object_{entity_type_id}"
                )
                
                self.entity_manager.add(entity)
                self.entities[entity_id] = {
                    'id': entity_id,
                    'type': 'object',
                    'object_type': entity_type_id,
                    'position': (x, y, z),
                    'yaw': yaw,
                    'pitch': pitch,
                }
                
                print(f"[ENTITIES] Spawned object: {entity.name} (id={entity_id}, type={entity_type_id})")
                self.emit("entity_spawn", entity)
                self.emit("entity", entity)
            except Exception as e:
                pass  # Skip malformed entity packets
            
        elif packet_id == 0x02:  # Spawn Experience Orb - 1.21.4
            try:
                entity_id = buf.read_varint()
                x = buf.read_value(StructFormat.DOUBLE)
                y = buf.read_value(StructFormat.DOUBLE)
                z = buf.read_value(StructFormat.DOUBLE)
                count = buf.read_value(StructFormat.SHORT)
                
                from .entities import Entity, EntityType
                entity = Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.OBJECT,
                    position=(x, y, z),
                    object_type=ObjectType.EXPERIENCE_ORB if hasattr(ObjectType, 'EXPERIENCE_ORB') else -1,
                    name=f"Experience Orb ({count})"
                )
                entity.raw['count'] = count
                
                self.entity_manager.add(entity)
                self.entities[entity_id] = {
                    'id': entity_id,
                    'type': 'experience_orb',
                    'position': (x, y, z),
                    'count': count,
                }
                
                self.emit("entity_spawn", entity)
                self.emit("entity", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x5A:  # Spawn Player - 1.21.4
            try:
                # Spawns another player
                entity_id = buf.read_varint()
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                
                x = buf.read_value(StructFormat.DOUBLE)
                y = buf.read_value(StructFormat.DOUBLE)
                z = buf.read_value(StructFormat.DOUBLE)
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                
                # Skip velocity
                buf.read_value(StructFormat.SHORT)
                buf.read_value(StructFormat.SHORT)
                buf.read_value(StructFormat.SHORT)
                
                from .entities import Entity, EntityType, EntityKind
                
                # Get player info from player list
                player_info = self.players.get(uuid, {})
                username = player_info.get('username', f'Player_{entity_id}')
                
                entity = Entity(
                    entity_id=entity_id,
                    uuid=uuid,
                    entity_type=EntityType.PLAYER,
                    kind=EntityKind.PLAYER,
                    position=(x, y, z),
                    yaw=yaw,
                    pitch=pitch,
                    name=username,
                    username=username,
                    gamemode=player_info.get('game_mode', 'survival'),
                    ping=player_info.get('latency', 0)
                )
                
                self.entity_manager.add(entity)
                self.entities[entity_id] = {
                    'id': entity_id,
                    'type': 'player',
                    'uuid': uuid,
                    'username': username,
                    'position': (x, y, z),
                    'yaw': yaw,
                    'pitch': pitch,
                }
                
                print(f"[ENTITIES] Spawned player: {username} (id={entity_id})")
                self.emit("player_spawn", entity)
                self.emit("entity_spawn", entity)
                self.emit("entity", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x3E:  # Remove Entities - 1.21.4
            try:
                count = buf.read_varint()
                for _ in range(count):
                    entity_id = buf.read_varint()
                    entity = self.entity_manager.remove(entity_id)
                    if entity_id in self.entities:
                        del self.entities[entity_id]
                    if entity:
                        print(f"[ENTITIES] Removed: {entity.name} (id={entity_id})")
                        self.emit("entity_gone", entity)
                        self.emit("entity_remove", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x1F:  # Entity Position (relative) - 1.21.4
            try:
                entity_id = buf.read_varint()
                delta_x = buf.read_value(StructFormat.SHORT) / (128 * 32)
                delta_y = buf.read_value(StructFormat.SHORT) / (128 * 32)
                delta_z = buf.read_value(StructFormat.SHORT) / (128 * 32)
                on_ground = buf.read_value(StructFormat.BOOL)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    old_pos = entity.position
                    new_pos = (old_pos[0] + delta_x, old_pos[1] + delta_y, old_pos[2] + delta_z)
                    entity.position = new_pos
                    entity.on_ground = on_ground
                    
                    if entity_id in self.entities:
                        self.entities[entity_id]['position'] = new_pos
                    
                    self.emit("entity_moved", entity, old_pos, new_pos)
            except Exception as e:
                pass
            
        elif packet_id == 0x20:  # Entity Position and Rotation - 1.21.4
            try:
                entity_id = buf.read_varint()
                delta_x = buf.read_value(StructFormat.SHORT) / (128 * 32)
                delta_y = buf.read_value(StructFormat.SHORT) / (128 * 32)
                delta_z = buf.read_value(StructFormat.SHORT) / (128 * 32)
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                on_ground = buf.read_value(StructFormat.BOOL)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    old_pos = entity.position
                    new_pos = (old_pos[0] + delta_x, old_pos[1] + delta_y, old_pos[2] + delta_z)
                    entity.position = new_pos
                    entity.yaw = yaw
                    entity.pitch = pitch
                    entity.on_ground = on_ground
                    
                    if entity_id in self.entities:
                        self.entities[entity_id]['position'] = new_pos
                        self.entities[entity_id]['yaw'] = yaw
                        self.entities[entity_id]['pitch'] = pitch
                    
                    self.emit("entity_moved", entity, old_pos, new_pos)
            except Exception as e:
                pass
            
        elif packet_id == 0x21:  # Entity Rotation - 1.21.4
            try:
                entity_id = buf.read_varint()
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                on_ground = buf.read_value(StructFormat.BOOL)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    entity.yaw = yaw
                    entity.pitch = pitch
                    entity.on_ground = on_ground
                    
                    if entity_id in self.entities:
                        self.entities[entity_id]['yaw'] = yaw
                        self.entities[entity_id]['pitch'] = pitch
                    
                    self.emit("entity_rotated", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x3F:  # Teleport Entity - 1.21.4
            try:
                entity_id = buf.read_varint()
                x = buf.read_value(StructFormat.DOUBLE)
                y = buf.read_value(StructFormat.DOUBLE)
                z = buf.read_value(StructFormat.DOUBLE)
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                on_ground = buf.read_value(StructFormat.BOOL)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    old_pos = entity.position
                    new_pos = (x, y, z)
                    entity.position = new_pos
                    entity.yaw = yaw
                    entity.pitch = pitch
                    entity.on_ground = on_ground
                    
                    if entity_id in self.entities:
                        self.entities[entity_id]['position'] = new_pos
                        self.entities[entity_id]['yaw'] = yaw
                        self.entities[entity_id]['pitch'] = pitch
                    
                    self.emit("entity_teleported", entity, old_pos, new_pos)
            except Exception as e:
                pass
            
        elif packet_id == 0x48:  # Entity Equipment - 1.21.4
            try:
                entity_id = buf.read_varint()
                
                entity = self.entity_manager.get(entity_id)
                
                while True:
                    # Equipment entry
                    slot_byte = buf.read_value(StructFormat.BYTE)
                    slot = slot_byte & 0x7F  # Lower 7 bits
                    has_more = (slot_byte & 0x80) != 0  # Top bit indicates more entries
                    
                    item = self._parse_slot(buf)
                    
                    if entity and item:
                        entity.equipment.set_slot(slot, item)
                    
                    if not has_more:
                        break
                
                if entity:
                    self.emit("entity_equipment", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x4D:  # Set Entity Metadata - 1.21.4
            try:
                entity_id = buf.read_varint()
                
                entity = self.entity_manager.get(entity_id)
                
                # Read metadata entries
                while buf.remaining() > 0:
                    index = buf.read_value(StructFormat.UBYTE)
                    if index == 0xFF:  # End of metadata
                        break
                    
                    type_id = buf.read_varint()
                    
                    # Parse value based on type
                    value = self._parse_metadata_value(buf, type_id)
                    
                    if entity:
                        entity.metadata[index] = value
                        
                        # Handle special metadata
                        if index == 2:  # Custom name
                            entity.custom_name = value
                        elif index == 7:  # Health (for living entities)
                            if isinstance(value, float):
                                entity.health = value
                
                if entity:
                    self.emit("entity_metadata", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x4B:  # Set Entity Link (vehicle/rider) - 1.21.4
            try:
                attached_entity_id = buf.read_varint()
                holding_entity_id = buf.read_varint()
                
                attached = self.entity_manager.get(attached_entity_id)
                holding = self.entity_manager.get(holding_entity_id)
                
                if attached and holding:
                    attached.vehicle = holding
                    holding.passengers.append(attached)
                    self.emit("entity_link", attached, holding)
            except Exception as e:
                pass
            
        elif packet_id == 0x56:  # Entity Update Attributes - 1.21.4
            try:
                entity_id = buf.read_varint()
                
                entity = self.entity_manager.get(entity_id)
                
                attribute_count = buf.read_varint()
                for _ in range(attribute_count):
                    attribute_id = buf.read_varint()
                    value = buf.read_value(StructFormat.DOUBLE)
                    
                    modifier_count = buf.read_varint()
                    for _ in range(modifier_count):
                        buf.read(16)  # UUID
                        buf.read_value(StructFormat.DOUBLE)  # amount
                        buf.read_value(StructFormat.BYTE)  # operation
                    
                    if entity:
                        # Map common attributes
                        if attribute_id == 0:  # generic.max_health
                            entity.max_health = value
                        elif attribute_id == 1:  # generic.follow_range
                            entity.raw['follow_range'] = value
                        elif attribute_id == 2:  # generic.knockback_resistance
                            entity.raw['knockback_resistance'] = value
                        elif attribute_id == 3:  # generic.movement_speed
                            entity.raw['movement_speed'] = value
                
                if entity:
                    self.emit("entity_attributes", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x03:  # Entity Animation - 1.21.4
            try:
                entity_id = buf.read_varint()
                animation = buf.read_value(StructFormat.UBYTE)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    # Animation types: 0=swing_main_arm, 1=take_damage, 2=leave_bed, 3=swing_off_hand, 4=critical_effect
                    animation_names = ['swing_main_arm', 'take_damage', 'leave_bed', 'swing_off_hand', 'critical_effect']
                    anim_name = animation_names[animation] if animation < len(animation_names) else f'unknown_{animation}'
                    self.emit("entity_animation", entity, anim_name)
            except Exception as e:
                pass
            
        elif packet_id == 0x19:  # Entity Event - 1.21.4
            try:
                entity_id = buf.read_varint()
                event_status = buf.read_value(StructFormat.BYTE)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    # Event statuses: 2=hurt, 3=death, 6=tilt, 9=eat_grass, 10=angry, etc.
                    if event_status == 2:  # Hurt
                        entity.raw['hurt_timestamp'] = asyncio.get_event_loop().time()
                        self.emit("entity_hurt", entity)
                    elif event_status == 3:  # Death
                        entity.is_dead = True
                        self.emit("entity_death", entity)
                    
                    self.emit("entity_event", entity, event_status)
            except Exception as e:
                pass
            
        elif packet_id == 0x05:  # Spawn Mob - 1.21.4 (CRITICAL!)
            try:
                entity_id = buf.read_varint()
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                
                mob_type_id = buf.read_varint()
                
                x = buf.read_value(StructFormat.DOUBLE)
                y = buf.read_value(StructFormat.DOUBLE)
                z = buf.read_value(StructFormat.DOUBLE)
                yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                pitch = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                head_yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                
                velocity_x = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_y = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_z = buf.read_value(StructFormat.SHORT) / 8000.0
                
                from .entities import Entity, EntityType, EntityKind, MobType, classify_mob, get_mob_name
                
                # Try to get mob type
                try:
                    mob_type = MobType(mob_type_id)
                    kind = classify_mob(mob_type)
                    name = get_mob_name(mob_type)
                except ValueError:
                    mob_type = None
                    kind = EntityKind.PASSIVE
                    name = f"mob_{mob_type_id}"
                
                entity = Entity(
                    entity_id=entity_id,
                    uuid=uuid,
                    entity_type=EntityType.MOB,
                    kind=kind,
                    mob_type=mob_type,
                    position=(x, y, z),
                    yaw=yaw,
                    pitch=pitch,
                    head_yaw=head_yaw,
                    velocity=(velocity_x, velocity_y, velocity_z),
                    name=name
                )
                
                self.entity_manager.add(entity)
                self.entities[entity_id] = {
                    'id': entity_id,
                    'type': 'mob',
                    'mob_type': mob_type_id,
                    'position': (x, y, z),
                    'yaw': yaw,
                    'pitch': pitch,
                }
                
                print(f"[ENTITIES] Spawned mob: {name} (id={entity_id}, type={mob_type_id})")
                self.emit("entity_spawn", entity)
                self.emit("entity", entity)
                self.emit("mob_spawn", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x4C:  # Entity Velocity - 1.21.4
            try:
                entity_id = buf.read_varint()
                velocity_x = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_y = buf.read_value(StructFormat.SHORT) / 8000.0
                velocity_z = buf.read_value(StructFormat.SHORT) / 8000.0
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    entity.velocity = (velocity_x, velocity_y, velocity_z)
                    self.emit("entity_velocity", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x3D:  # Head Look - 1.21.4
            try:
                entity_id = buf.read_varint()
                head_yaw = buf.read_value(StructFormat.BYTE) * (360.0 / 256.0)
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    entity.head_yaw = head_yaw
                    self.emit("entity_head_look", entity)
            except Exception as e:
                pass
            
        elif packet_id == 0x47:  # Entity Damage - 1.21.4
            try:
                entity_id = buf.read_varint()
                source_type = buf.read_varint()
                source_cause_id = buf.read_varint()
                source_direct_id = buf.read_varint()
                
                entity = self.entity_manager.get(entity_id)
                if entity:
                    entity.raw['last_damage_source'] = source_type
                    entity.raw['last_damage_cause'] = source_cause_id
                    entity.raw['last_damage_timestamp'] = asyncio.get_event_loop().time()
                    self.emit("entity_damage", entity, source_type, source_cause_id, source_direct_id)
            except Exception as e:
                pass
            
        elif packet_id == 0x5B:  # Set Passengers - 1.21.4
            try:
                vehicle_id = buf.read_varint()
                passenger_count = buf.read_varint()
                
                passenger_ids = []
                for _ in range(passenger_count):
                    passenger_ids.append(buf.read_varint())
                
                vehicle = self.entity_manager.get(vehicle_id)
                if vehicle:
                    # Clear old passengers
                    vehicle.passengers.clear()
                    
                    # Add new passengers
                    for pid in passenger_ids:
                        passenger = self.entity_manager.get(pid)
                        if passenger:
                            passenger.vehicle = vehicle
                            vehicle.passengers.append(passenger)
                    
                    self.emit("entity_passengers", vehicle, passenger_ids)
            except Exception as e:
                pass
            
        elif packet_id == 0x0A:  # Spawn Painting - 1.21.4
            try:
                entity_id = buf.read_varint()
                uuid_bytes = buf.read(16)
                uuid_int = int.from_bytes(uuid_bytes, "big")
                uuid = f"{uuid_int:032x}"
                uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                
                motive = buf.read_varint()  # Painting type
                pos_long = buf.read_value(StructFormat.LONG)
                x = pos_long >> 38
                y = (pos_long >> 26) & 0xFFF
                z = pos_long << 38 >> 38
                if x >= 2**25: x -= 2**26
                if y >= 2**11: y -= 2**12
                if z >= 2**25: z -= 2**26
                direction = buf.read_value(StructFormat.BYTE)
                
                from .entities import Entity, EntityType
                entity = Entity(
                    entity_id=entity_id,
                    uuid=uuid,
                    entity_type=EntityType.OBJECT,
                    position=(x, y, z),
                    name=f"Painting ({motive})"
                )
                entity.raw['motive'] = motive
                entity.raw['direction'] = direction
                
                self.entity_manager.add(entity)
                self.entities[entity_id] = {
                    'id': entity_id,
                    'type': 'painting',
                    'position': (x, y, z),
                }
                
                self.emit("entity_spawn", entity)
                self.emit("entity", entity)
            except Exception as e:
                pass
        else:
            # Unknown packet - ignore
            pass
    
    def _parse_recipe(self, buf: Buffer) -> Optional[Recipe]:
        """
        Parse a recipe from Declare Recipes packet.
        
        Returns:
            Recipe object or None if parsing fails
        """
        recipe_id = buf.read_utf()
        recipe_type = buf.read_utf()
        
        if recipe_type == "minecraft:crafting_shaped":
            return self._parse_shaped_recipe(buf, recipe_id, recipe_type)
        elif recipe_type == "minecraft:crafting_shapeless":
            return self._parse_shapeless_recipe(buf, recipe_id, recipe_type)
        elif recipe_type in ("minecraft:smelting", "minecraft:blasting", 
                            "minecraft:smoking", "minecraft:campfire_cooking"):
            return self._parse_smelting_recipe(buf, recipe_id, recipe_type)
        elif recipe_type == "minecraft:stonecutting":
            return self._parse_stonecutting_recipe(buf, recipe_id, recipe_type)
        else:
            # Skip unknown recipe type
            return None
    
    def _parse_shaped_recipe(self, buf: Buffer, recipe_id: str, recipe_type: str) -> Optional[ShapedRecipe]:
        """Parse shaped crafting recipe"""
        width = buf.read_varint()
        height = buf.read_varint()
        group = buf.read_utf()
        category = buf.read_utf()
        
        # Parse ingredients
        ingredients = []
        for _ in range(width * height):
            ing_count = buf.read_varint()
            if ing_count == 0:
                ingredients.append(Ingredient())
            elif ing_count == 1:
                item = buf.read_utf()
                ingredients.append(Ingredient(item=item))
            else:
                alts = [Ingredient(item=buf.read_utf()) for _ in range(ing_count)]
                ingredients.append(Ingredient(alternatives=alts))
        
        # Parse result
        result = self._parse_recipe_result(buf)
        
        return ShapedRecipe(
            id=recipe_id,
            recipe_type=recipe_type,
            result=result,
            group=group if group else None,
            category=category if category else None,
            width=width,
            height=height,
            ingredients=ingredients
        )
    
    def _parse_shapeless_recipe(self, buf: Buffer, recipe_id: str, recipe_type: str) -> Optional[ShapelessRecipe]:
        """Parse shapeless crafting recipe"""
        group = buf.read_utf()
        category = buf.read_utf()
        
        # Parse ingredients
        ing_count = buf.read_varint()
        ingredients = []
        for _ in range(ing_count):
            alt_count = buf.read_varint()
            if alt_count == 0:
                ingredients.append(Ingredient())
            elif alt_count == 1:
                item = buf.read_utf()
                ingredients.append(Ingredient(item=item))
            else:
                alts = [Ingredient(item=buf.read_utf()) for _ in range(alt_count)]
                ingredients.append(Ingredient(alternatives=alts))
        
        # Parse result
        result = self._parse_recipe_result(buf)
        
        return ShapelessRecipe(
            id=recipe_id,
            recipe_type=recipe_type,
            result=result,
            group=group if group else None,
            category=category if category else None,
            ingredients=ingredients
        )
    
    def _parse_smelting_recipe(self, buf: Buffer, recipe_id: str, recipe_type: str) -> Optional[SmeltingRecipe]:
        """Parse smelting recipe"""
        group = buf.read_utf()
        category = buf.read_utf()
        
        # Parse ingredient
        alt_count = buf.read_varint()
        if alt_count == 0:
            ingredient = Ingredient()
        elif alt_count == 1:
            ingredient = Ingredient(item=buf.read_utf())
        else:
            alts = [Ingredient(item=buf.read_utf()) for _ in range(alt_count)]
            ingredient = Ingredient(alternatives=alts)
        
        # Parse result
        result = self._parse_recipe_result(buf)
        
        # Experience and cooking time
        experience = buf.read_value(StructFormat.FLOAT)
        cooking_time = buf.read_varint()
        
        return SmeltingRecipe(
            id=recipe_id,
            recipe_type=recipe_type,
            result=result,
            group=group if group else None,
            category=category if category else None,
            ingredient=ingredient,
            experience=experience,
            cooking_time=cooking_time
        )
    
    def _parse_stonecutting_recipe(self, buf: Buffer, recipe_id: str, recipe_type: str) -> Optional[StonecuttingRecipe]:
        """Parse stonecutting recipe"""
        group = buf.read_utf()
        
        # Parse ingredient
        alt_count = buf.read_varint()
        if alt_count == 0:
            ingredient = Ingredient()
        elif alt_count == 1:
            ingredient = Ingredient(item=buf.read_utf())
        else:
            alts = [Ingredient(item=buf.read_utf()) for _ in range(alt_count)]
            ingredient = Ingredient(alternatives=alts)
        
        # Parse result
        result = self._parse_recipe_result(buf)
        
        return StonecuttingRecipe(
            id=recipe_id,
            recipe_type=recipe_type,
            result=result,
            group=group if group else None,
            ingredient=ingredient
        )
    
    def _parse_recipe_result(self, buf: Buffer) -> RecipeResult:
        """Parse recipe result item"""
        from .recipes import RecipeResult
        
        result_count = buf.read_varint()
        result_item = buf.read_utf()
        
        # Skip result components if present
        # In 1.21.4, result may have components
        
        return RecipeResult(
            item_id=result_item,
            count=result_count
        )

    async def _receive_loop(self) -> None:
        """Main packet receiving loop"""
        while self._running:
            try:
                packet_id, buf = await self._read_packet()
                # Only log Keep Alive packets
                if packet_id == 0x27:
                    print(f"[KEEP-ALIVE] Received, responding...")

                if self.state == ProtocolState.LOGIN:
                    await self.handle_login_packet(packet_id, buf)
                elif self.state == ProtocolState.CONFIGURATION:
                    await self.handle_configuration_packet(packet_id, buf)
                elif self.state == ProtocolState.PLAY:
                    await self.handle_play_packet(packet_id, buf)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    import traceback
                    print(f"Error receiving packet: {e}")
                    traceback.print_exc()
                    self.emit("error", e)
                # Don't break - continue receiving packets

    async def connect(self) -> None:
        """Connect to the server"""
        print(f"Connecting to {self.host}:{self.port}...")

        self.connection = await TCPAsyncConnection.make_client(
            (self.host, self.port), timeout=10.0
        )

        print("TCP connection established")
        self.emit("connect")

        await self.send_handshake(next_state=2)
        print("Handshake sent")

        await self.send_login_start()
        print("Login start sent")

        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self) -> None:
        """Disconnect from the server"""
        self._running = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.connection:
            await self.connection.close()
            self.connection = None

        self.emit("end")

    async def stay_alive(self, duration: float = 120.0) -> float:
        """Stay connected for the specified duration"""
        start_time = asyncio.get_event_loop().time()

        while self._running:
            await asyncio.sleep(0.1)

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= duration:
                break

        return elapsed


async def create_bot(options: Dict[str, Any] = None) -> MinecraftProtocol:
    """Create and connect a bot"""
    options = options or {}

    host = options.get("host", "localhost")
    port = options.get("port", 25565)
    username = options.get("username", "Player")

    bot = MinecraftProtocol(host, port, username)
    
    # Set options
    bot._auto_respawn = options.get("respawn", True)

    for event in [
        "spawn",
        "login",
        "kicked",
        "error",
        "end",
        "connect",
        "game",
        "health",
        "death",
        "time",
        "respawn",
        "chunk_loaded",
        "chunk_unloaded",
        "block_update",
        "dig_start",
        "dig_end",
        "dig_abort",
        "block_break_progress",
        "block_break_stop",
        "inventory_update",
        "slot_update",
        "container_open",
        "container_close",
        "craft",
    ]:
        handler = options.get(f"on_{event}")
        if handler:
            bot.on(event, handler)

    await bot.connect()
    return bot
