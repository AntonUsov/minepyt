"""
Main protocol connection class for Minecraft 1.21.4

This module provides the MinecraftProtocol class which combines:
- Connection management
- Packet I/O
- Event system
- Handler mixins for each protocol state
"""

from __future__ import annotations

import asyncio
import math
import struct
import zlib
from typing import Any, Callable, Dict, List, Optional, Tuple

from mcproto.buffer import Buffer
from mcproto.connection import TCPAsyncConnection
from mcproto.protocol.base_io import StructFormat
from mcproto.types.uuid import UUID

from .states import ProtocolState
from .enums import DigStatus, ClickMode, ClickButton
from .models import Game, Item, parse_game_mode
from .handlers.login import LoginHandler
from .handlers.configuration import ConfigurationHandler
from .handlers.play import PlayHandler

# Import from parent modules - use try/except for both import styles
try:
    from minepyt.chunk_utils import (
        World, ChunkColumn, ChunkSection, BufferReader,
        parse_paletted_container, parse_chunk_section, parse_nbt,
    )
    from minepyt.block_registry import Block, get_block_name, is_air, is_solid, is_transparent
    from minepyt.nbt import NbtCompound, NbtReader, parse_nbt as parse_nbt_data
    from minepyt.components import ItemComponents, ComponentReader, Enchantment, parse_components
    from minepyt.recipes import (
        RecipeRegistry, RecipeMatcher, Recipe, ShapedRecipe, ShapelessRecipe,
        SmeltingRecipe, StonecuttingRecipe, Ingredient, RecipeResult,
    )
    from minepyt.entities import (
        Entity, EntityType, EntityKind, EntityEquipment,
        MobType, ObjectType, EntityManager, classify_mob, get_mob_name, get_object_name,
    )
except ImportError:
    from ..chunk_utils import (
        World, ChunkColumn, ChunkSection, BufferReader,
        parse_paletted_container, parse_chunk_section, parse_nbt,
    )
    from ..block_registry import Block, get_block_name, is_air, is_solid, is_transparent
    from ..nbt import NbtCompound, NbtReader, parse_nbt as parse_nbt_data
    from ..components import ItemComponents, ComponentReader, Enchantment, parse_components
    from ..recipes import (
        RecipeRegistry, RecipeMatcher, Recipe, ShapedRecipe, ShapelessRecipe,
        SmeltingRecipe, StonecuttingRecipe, Ingredient, RecipeResult,
    )
    from ..entities import (
        Entity, EntityType, EntityKind, EntityEquipment,
        MobType, ObjectType, EntityManager, classify_mob, get_mob_name, get_object_name,
    )


class MinecraftProtocol(LoginHandler, ConfigurationHandler, PlayHandler):
    """
    Low-level Minecraft protocol implementation for 1.21.4

    This class combines all packet handlers through multiple inheritance
    and provides the core connection management functionality.
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
        self.players: Dict[str, Dict] = {}
        self.entities: Dict[int, Any] = {}
        self.entity_manager: EntityManager = EntityManager()
        self.entity: Optional[Dict] = None

        # World state (plugin: blocks)
        self.world: World = World(min_y=0, height=256)
        self._chunks_loaded: int = 0

        # Digging state
        self._dig_sequence: int = 0
        self._is_digging: bool = False
        self._dig_target: Optional[Tuple[int, int, int]] = None
        self._dig_task: Optional[asyncio.Task] = None
        self._break_animations: Dict[int, Dict] = {}

        # Inventory state
        self.inventory: Dict[int, Item] = {}
        self.held_item_slot: int = 0
        self.open_container_id: Optional[int] = None
        self._inventory_sequence: int = 0
        self._cursor_item: Optional[Item] = None

        # Recipe system
        self.recipes: RecipeRegistry = RecipeRegistry()
        self.recipe_matcher: RecipeMatcher = RecipeMatcher(self.recipes)
        
        # Movement system
        try:
            from minepyt.movement import MovementManager
        except ImportError:
            from ..movement import MovementManager
        self._movement: MovementManager = MovementManager(self)
        
        # Combat system
        try:
            from minepyt.combat import CombatManager
        except ImportError:
            from ..combat import CombatManager
        self._combat: CombatManager = CombatManager(self)
        
        # Chat system
        try:
            from minepyt.chat import ChatManager
        except ImportError:
            from ..chat import ChatManager
        self._chat: ChatManager = ChatManager(self)
        
        # Inventory system
        try:
            from minepyt.inventory import InventoryManager
        except ImportError:
            from ..inventory import InventoryManager
        self._inventory_mgr: InventoryManager = InventoryManager(self)
        
        # Block interaction system
        try:
            from minepyt.block_interaction import BlockInteractionManager
        except ImportError:
            from ..block_interaction import BlockInteractionManager
        self._block_interaction: BlockInteractionManager = BlockInteractionManager(self)

        # Advanced inventory system (anvil, enchanting)
        try:
            from minepyt.advanced_inventory import AdvancedInventory
            from minepyt.villager import VillagerManager
        except ImportError:
            from ..advanced_inventory import AdvancedInventory
            from ..villager import VillagerManager
        self._advanced_inv: AdvancedInventory = AdvancedInventory(self)
        self._villager_mgr: VillagerManager = VillagerManager(self)

        # Pathfinding system
        try:
            from minepyt.pathfinding import PathfinderManager
        except ImportError:
            from ..pathfinding import PathfinderManager
        self._pathfinder: PathfinderManager = PathfinderManager(self)

        # Vehicle system
        try:
            from minepyt.vehicles import VehicleManager
        except ImportError:
            from ..vehicles import VehicleManager
        self._vehicle_mgr: VehicleManager = VehicleManager(self)

        # Creative mode system
        try:
            from minepyt.creative import CreativeManager
        except ImportError:
                from ..creative import CreativeManager
        self._creative: CreativeManager = CreativeManager(self)

        # Brewing stand system
        try:
            from minepyt.brewing import BrewingManager
        except ImportError:
            from ..brewing import BrewingManager
        self._brewing: BrewingManager = BrewingManager(self)

        # Entity interaction system (breeding, taming)
        try:
            from minepyt.entity_interaction import EntityInteractionManager
        except ImportError:
            from ..entity_interaction import EntityInteractionManager
        self._entity_interaction: EntityInteractionManager = EntityInteractionManager(self)

        # Boss bar tracking system
        try:
            from minepyt.boss_bar import BossBarManager
        except ImportError:
            from ..boss_bar import BossBarManager
        self._boss_bar: BossBarManager = BossBarManager(self)

        # Scoreboard tracking system
        try:
            from minepyt.scoreboard import ScoreboardManager
        except ImportError:
            from ..scoreboard import ScoreboardManager
        self._scoreboard_mgr: ScoreboardManager = ScoreboardManager(self)

        # Tablist tracking
        try:
            from minepyt.tablist import TabListManager
        except ImportError:
            from ..tablist import TabListManager
        self._tablist: TabListManager = TabListManager(self)

        # Title tracking
        try:
            from minepyt.title import TitleManager
        except ImportError:
            from ..title import TitleManager
        self._title: TitleManager = TitleManager(self)

        # Team tracking
        try:
            from minepyt.team import TeamManager
        except ImportError:
            from ..team import TeamManager
        self._team: TeamManager = TeamManager(self)

        # Particle tracking
        try:
            from minepyt.particle import ParticleManager
        except ImportError:
            from ..particle import ParticleManager
        self._particle: ParticleManager = ParticleManager(self)

        # Sound tracking
        try:
            from minepyt.sound import SoundManager
        except ImportError:
            from ..sound import SoundManager
        self._sound: SoundManager = SoundManager(self)

        # Book editing
        try:
            from minepyt.book import BookManager
        except ImportError:
            from ..book import BookManager
        self._book: BookManager = BookManager(self)

        # Bed tracking system
        try:
            from minepyt.bed import BedManager
        except ImportError:
            from ..bed import BedManager
        self._bed_mgr: BedManager = BedManager(self)

        # Kick disconnect system
        try:
            from minepyt.kick import KickManager
        except ImportError:
            from ..kick import KickManager
        self._kick: KickManager = KickManager(self)

        # Explosion tracking system
        try:
            from minepyt.explosion import ExplosionManager
        except ImportError:
            from ..explosion import ExplosionManager
        self._explosion: ExplosionManager = ExplosionManager(self)

        # Fishing system
        try:
            from minepyt.fishing import FishingManager
        except ImportError:
            from ..fishing import FishingManager
        self._fishing: FishingManager = FishingManager(self)

        # Weather (rain) tracking system
        try:
            from minepyt.rain import WeatherManager
        except ImportError:
            from ..rain import WeatherManager
        self._weather: WeatherManager = WeatherManager(self)

        # Resource pack tracking system
        try:
            from minepyt.resource_pack import ResourcePackManager
        except ImportError:
            from ..resource_pack import ResourcePackManager
        self._resource_pack: ResourcePackManager = ResourcePackManager(self)

        # Client settings system
        try:
            from minepyt.settings import SettingsManager
        except ImportError:
            from ..settings import SettingsManager
        self._settings: SettingsManager = SettingsManager(self)

        # Spawn point tracking system
        try:
            from minepyt.spawn_point import SpawnPointManager
        except ImportError:
            from ..spawn_point import SpawnPointManager
        self._spawn_point: SpawnPointManager = SpawnPointManager(self)

        # Time tracking system
        try:
            from minepyt.time import TimeManager
        except ImportError:
            from ..time import TimeManager
        self._time_mgr: TimeManager = TimeManager(self)

        # Experience tracking system
        try:
            from minepyt.experience import ExperienceManager
        except ImportError:
            from ..experience import ExperienceManager
        self._experience: ExperienceManager = ExperienceManager(self)

        # Game state tracking system
        try:
            from minepyt.game import GameStateManager
        except ImportError:
            from ..game import GameStateManager
        self._game_state: GameStateManager = GameStateManager(self)

        # Ray tracing system
        try:
            from minepyt.ray_trace import RayTraceManager
        except ImportError:
            from ..ray_trace import RayTraceManager
        self._ray_trace: RayTraceManager = RayTraceManager(self)

    # === Event System ===

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

    # === Packet I/O ===

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

    # === Serverbound Packet Senders ===

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

        await self._write_packet(0x00, bytes(buf))

    async def send_known_packs(self) -> None:
        """Send known packs (required in 1.21+)"""
        buf = Buffer()
        buf.write_varint(0)  # No known packs
        await self._write_packet(0x07, bytes(buf))

    async def send_acknowledge_finish_configuration(self) -> None:
        """Send acknowledge finish configuration (transitions to Play state)"""
        await self._write_packet(0x03, bytes(Buffer()))
        self.state = ProtocolState.PLAY
        print("Transitioned to PLAY state")

    async def send_keep_alive(self, keep_alive_id: int) -> None:
        """Respond to keep alive packet (0x1A for 1.21.4)"""
        buf = Buffer()
        buf.write_value(StructFormat.LONGLONG, keep_alive_id)
        await self._write_packet(0x1A, bytes(buf))

    async def send_player_position(self) -> None:
        """Send player position and rotation (MOVE_PLAYER_POS_ROT = 0x1D for 1.21.4)"""
        buf = Buffer()
        buf.write_value(StructFormat.DOUBLE, self.position[0])
        buf.write_value(StructFormat.DOUBLE, self.position[1])
        buf.write_value(StructFormat.DOUBLE, self.position[2])
        buf.write_value(StructFormat.FLOAT, self.yaw)
        buf.write_value(StructFormat.FLOAT, self.pitch)
        buf.write_value(StructFormat.BYTE, 0x01 if self.on_ground else 0x00)

        await self._write_packet(0x1D, bytes(buf))

    async def respawn(self) -> None:
        """Send respawn request to server (Client Command = 0x0D for 1.21.4)"""
        if self.is_alive:
            return
        buf = Buffer()
        buf.write_varint(0)  # Action: Perform respawn
        await self._write_packet(0x0D, bytes(buf))
        print("[HEALTH] Respawn requested")

    async def chat(self, message: str) -> None:
        """Send a chat message"""
        await self._chat.send(message)
    
    async def whisper(self, username: str, message: str) -> None:
        """Send a whisper (private message) to a player"""
        await self._chat.whisper(username, message)
    
    async def command(self, command: str) -> None:
        """Send a command"""
        await self._chat.command(command)
    
    def add_chat_pattern(self, name: str, pattern, repeat: bool = True, parse: bool = False) -> int:
        """Add a chat pattern to match"""
        return self._chat.add_pattern(name, pattern, repeat, parse)
    
    def remove_chat_pattern(self, pattern_id: int) -> None:
        """Remove a chat pattern"""
        self._chat.remove_pattern(pattern_id)

    # === World Helpers ===

    def block_at(self, x: int, y: int, z: int) -> Block:
        """Get block at world coordinates as a Block object"""
        block_state = self.world.get_block_state(x, y, z)
        return Block(state_id=block_state, position=(x, y, z))

    def get_loaded_chunks(self) -> List[Tuple[int, int]]:
        """Get list of loaded chunk coordinates"""
        return self.world.get_loaded_chunks()

    # === Digging ===

    async def send_player_digging(
        self, status: DigStatus, x: int, y: int, z: int, face: int = 1
    ) -> None:
        """Send player digging packet (0x24 for 1.21.4)"""
        self._dig_sequence += 1
        pos_long = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)

        buf = Buffer()
        buf.write_varint(status)
        buf.write_value(StructFormat.LONG, pos_long)
        buf.write_value(StructFormat.BYTE, face)
        buf.write_varint(self._dig_sequence)

        await self._write_packet(0x24, bytes(buf))

    def _get_dig_time(self, block: Block) -> float:
        """Calculate time to dig a block in seconds."""
        if self.game.game_mode == "creative":
            return 0.0
        if block.is_air:
            return 0.0

        base_hardness = 1.5
        hardness_map = {
            "dirt": 0.5,
            "grass_block": 0.6,
            "stone": 1.5,
            "cobblestone": 2.0,
            "sand": 0.5,
            "gravel": 0.6,
            "oak_log": 2.0,
            "oak_planks": 2.0,
            "glass": 0.3,
            "sandstone": 0.8,
        }
        hardness = hardness_map.get(block.name, base_hardness)
        dig_time = hardness * 1.5
        return dig_time

    async def dig(self, x: int, y: int, z: int, face: int = 1) -> bool:
        """Dig a block at the specified position."""
        if self._is_digging:
            print(f"[DIG] Already digging at {self._dig_target}")
            return False

        block = self.block_at(x, y, z)

        if block.is_air:
            print(f"[DIG] Block at ({x}, {y}, {z}) is air, nothing to dig")
            return False

        if self.game.game_mode in ("adventure", "spectator"):
            print(f"[DIG] Cannot dig in {self.game.game_mode} mode")
            return False

        self._is_digging = True
        self._dig_target = (x, y, z)

        print(f"[DIG] Starting to dig {block.name} at ({x}, {y}, {z})")
        self.emit("dig_start", block)

        await self.send_player_digging(DigStatus.START_DIGGING, x, y, z, face)

        dig_time = self._get_dig_time(block)

        if dig_time > 0:
            try:
                await asyncio.sleep(dig_time)
            except asyncio.CancelledError:
                await self.send_player_digging(DigStatus.CANCEL_DIGGING, x, y, z, face)
                self._is_digging = False
                self.emit("dig_abort", block)
                return False

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

        if self._dig_task:
            self._dig_task.cancel()
            try:
                await self._dig_task
            except asyncio.CancelledError:
                pass

        await self.send_player_digging(DigStatus.CANCEL_DIGGING, x, y, z, 1)

        print(f"[DIG] Cancelled digging at ({x}, {y}, {z})")
        self.emit("dig_abort", block)

        self._is_digging = False
        self._dig_target = None

    # === Entity Interaction ===

    async def send_interact(
        self,
        entity_id: int,
        interact_type: int = 0,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        hand: int = 0,
        sneaking: bool = False,
    ) -> None:
        """Send Interact packet (0x10 serverbound for 1.21.4)"""
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

        buf.write_value(StructFormat.BOOL, sneaking)

        await self._write_packet(0x10, bytes(buf))

    async def attack(self, entity, swing_hand: bool = True) -> bool:
        """Attack an entity."""
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)

        if entity_obj is None:
            print(f"[ATTACK] Entity {entity_id} not found")
            return False

        if entity_obj.is_dead:
            print(f"[ATTACK] Entity {entity_id} is dead")
            return False

        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[ATTACK] Entity {entity_id} too far: {dist:.1f} blocks")
                return False

        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)
        await self.send_interact(entity_id, interact_type=1)

        if swing_hand:
            await self.send_arm_swing()

        print(f"[ATTACK] Attacked {entity_obj} (id={entity_id})")
        self.emit("entity_attack", entity_obj)

        return True

    async def interact(self, entity, hand: int = 0, swing_hand: bool = True) -> bool:
        """Interact with an entity (right-click)."""
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)

        if entity_obj is None:
            print(f"[INTERACT] Entity {entity_id} not found")
            return False

        if entity_obj.is_dead:
            print(f"[INTERACT] Entity {entity_id} is dead")
            return False

        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[INTERACT] Entity {entity_id} too far: {dist:.1f} blocks")
                return False

        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)
        await self.send_interact(entity_id, interact_type=0, hand=hand)

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
        swing_hand: bool = True,
    ) -> bool:
        """Interact at a specific position on an entity."""
        if hasattr(entity, "entity_id"):
            entity_id = entity.entity_id
            entity_obj = entity
        else:
            entity_id = int(entity)
            entity_obj = self.entity_manager.get(entity_id)

        if entity_obj is None:
            print(f"[USE_ON] Entity {entity_id} not found")
            return False

        if entity_obj.is_dead:
            print(f"[USE_ON] Entity {entity_id} is dead")
            return False

        if self.position:
            dist = entity_obj.distance_to(self.position)
            if dist > 6.0:
                print(f"[USE_ON] Entity {entity_id} too far: {dist:.1f} blocks")
                return False

        await self.look_at(entity_obj.x, entity_obj.y + entity_obj.height / 2, entity_obj.z)

        world_x = entity_obj.x + (target_x - 0.5) * entity_obj.width
        world_y = entity_obj.y + target_y * entity_obj.height
        world_z = entity_obj.z + (target_z - 0.5) * entity_obj.width

        await self.send_interact(
            entity_id,
            interact_type=2,
            target_x=world_x,
            target_y=world_y,
            target_z=world_z,
            hand=hand,
        )

        if swing_hand:
            await self.send_arm_swing()

        print(
            f"[USE_ON] Used on {entity_obj} (id={entity_id}) at ({target_x}, {target_y}, {target_z})"
        )
        self.emit("entity_use_on", entity_obj, (target_x, target_y, target_z))

        return True

    async def send_arm_swing(self, hand: int = 0) -> None:
        """Send arm swing animation (0x35 serverbound for 1.21.4)"""
        buf = Buffer()
        buf.write_varint(hand)
        await self._write_packet(0x35, bytes(buf))

    # === Combat ===
    
    def get_attack_cooldown(self) -> float:
        """Get current attack cooldown progress (0.0 to 1.0)"""
        return self._combat.get_attack_cooldown_progress()
    
    def is_attack_ready(self) -> bool:
        """Check if attack cooldown has finished"""
        return self._combat.is_attack_ready()
    
    async def attack_loop(self, entity, max_attacks: int = 10, stop_on_death: bool = True) -> int:
        """Attack an entity repeatedly until dead or max attacks reached"""
        return await self._combat.attack_loop(entity, max_attacks, stop_on_death)

    async def look_at(self, x: float, y: float, z: float) -> None:
        """Look at a specific position."""
        if not self.position:
            return

        dx = x - self.position[0]
        dy = y - self.position[1]
        dz = z - self.position[2]

        dist = math.sqrt(dx * dx + dz * dz)
        yaw = math.degrees(math.atan2(-dx, dz))
        pitch = math.degrees(math.atan2(-dy, dist))

        self.yaw = yaw
        self.pitch = pitch

        await self.send_player_position()

    # === Movement ===
    
    def set_control_state(self, control: str, state: bool) -> None:
        """Set a movement control state (forward, back, left, right, jump, sprint, sneak)"""
        self._movement.set_control_state(control, state)
    
    def get_control_state(self, control: str) -> bool:
        """Get a movement control state"""
        return self._movement.get_control_state(control)
    
    def clear_control_states(self) -> None:
        """Clear all movement control states"""
        self._movement.clear_control_states()
    
    async def move_to(self, x: float, z: float, timeout: float = 30.0) -> bool:
        """
        Move to a position (simple straight-line movement).
        
        Args:
            x: Target X coordinate
            z: Target Z coordinate
            timeout: Maximum time to try
            
        Returns:
            True if reached destination
        """
        return await self._movement.move_to(x, z, timeout)
    
    async def jump(self) -> None:
        """Make the bot jump"""
        await self._movement.jump()
    
    def start_physics(self) -> None:
        """Start the physics simulation loop"""
        self._movement.start()
    
    def stop_physics(self) -> None:
        """Stop the physics simulation loop"""
        self._movement.stop()

    # === Inventory ===

    def _parse_slot(self, buf: Buffer) -> Optional[Item]:
        """Parse a slot from buffer for 1.21.4."""
        try:
            from minepyt.components import ComponentType
        except ImportError:
            from ..components import ComponentType

        item_id = buf.read_varint()

        if item_id == 0:
            return Item(item_id=0, count=0)

        count = buf.read_value(StructFormat.BYTE)
        added_count = buf.read_varint()
        removed_count = buf.read_varint()

        components = ItemComponents()

        for _ in range(added_count):
            component_type = buf.read_varint()
            self._parse_component(buf, component_type, components)

        for _ in range(removed_count):
            buf.read_varint()

        return Item(item_id=item_id, count=count, components=components)

    def _parse_component(
        self, buf: Buffer, component_type: int, components: ItemComponents
    ) -> None:
        """Parse a single component by type."""
        try:
            from minepyt.components import ComponentType
        except ImportError:
            from ..components import ComponentType

        try:
            comp_type = ComponentType(component_type)
        except ValueError:
            return

        if comp_type == ComponentType.MAX_STACK_SIZE:
            components.max_stack_size = buf.read_varint()
        elif comp_type == ComponentType.MAX_DAMAGE:
            components.max_damage = buf.read_varint()
        elif comp_type == ComponentType.DAMAGE:
            components.damage = buf.read_varint()
        elif comp_type == ComponentType.UNBREAKABLE:
            components.unbreakable = True
        # ... more component types can be added

    def _parse_metadata_value(self, buf: Buffer, type_id: int) -> Any:
        """Parse an entity metadata value by type."""
        if type_id == 0:  # Byte
            return buf.read_value(StructFormat.BYTE)
        elif type_id == 1:  # VarInt
            return buf.read_varint()
        elif type_id == 2:  # VarLong
            return buf.read_value(StructFormat.LONG)
        elif type_id == 3:  # Float
            return buf.read_value(StructFormat.FLOAT)
        elif type_id == 4:  # String
            return buf.read_utf()
        elif type_id == 5:  # Chat
            return buf.read_utf()
        elif type_id == 6:  # Optional Chat
            if buf.read_value(StructFormat.BOOL):
                return buf.read_utf()
            return None
        elif type_id == 7:  # Slot
            return self._parse_slot(buf)
        elif type_id == 8:  # Boolean
            return buf.read_value(StructFormat.BOOL)
        elif type_id == 9:  # Rotation
            return (
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
                buf.read_value(StructFormat.FLOAT),
            )
        elif type_id == 10:  # Position
            pos = buf.read_value(StructFormat.LONG)
            x = pos >> 38
            y = (pos >> 26) & 0xFFF
            z = pos << 38 >> 38
            return (x, y, z)
        elif type_id == 11:  # Optional Position
            if buf.read_value(StructFormat.BOOL):
                pos = buf.read_value(StructFormat.LONG)
                x = pos >> 38
                y = (pos >> 26) & 0xFFF
                z = pos << 38 >> 38
                return (x, y, z)
            return None
        elif type_id == 12:  # Direction
            return buf.read_varint()
        elif type_id == 13:  # Optional UUID
            if buf.read_value(StructFormat.BOOL):
                return buf.read(16)
            return None
        elif type_id == 14:  # Block State
            return buf.read_varint()
        elif type_id == 15:  # Optional Block State
            if buf.read_value(StructFormat.BOOL):
                return buf.read_varint()
            return None
        elif type_id == 16:  # NBT
            return parse_nbt_data(buf)
        elif type_id == 17:  # Particle
            particle_id = buf.read_varint()
            # Skip particle data
            return particle_id
        elif type_id == 18:  # Villager Data
            buf.read_varint()  # type
            buf.read_varint()  # profession
            buf.read_varint()  # level
            return None
        elif type_id == 19:  # Optional VarInt
            if buf.read_value(StructFormat.BOOL):
                return buf.read_varint()
            return None
        elif type_id == 20:  # Pose
            return buf.read_varint()
        elif type_id == 21:  # Cat Variant
            return buf.read_varint()
        elif type_id == 22:  # Frog Variant
            return buf.read_varint()
        elif type_id == 23:  # Optional Global Position
            if buf.read_value(StructFormat.BOOL):
                buf.read_varint()  # dimension
                pos = buf.read_value(StructFormat.LONG)
                return pos
            return None
        elif type_id == 24:  # Painting Variant
            return buf.read_varint()
        else:
            return None

    # === Entity Helpers ===

    def nearest_entity(
        self, entity_type: Optional[str] = None, max_distance: float = 16.0
    ) -> Optional[Entity]:
        """Find nearest entity of specified type."""
        if not self.position:
            return None
        return self.entity_manager.find_nearest(
            self.position, entity_type=entity_type, max_distance=max_distance
        )

    def nearest_player(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find nearest player."""
        return self.nearest_entity(entity_type="player", max_distance=max_distance)

    def nearest_hostile(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find nearest hostile mob."""
        return self.entity_manager.find_nearest_hostile(self.position, max_distance)

    def nearest_passive(self, max_distance: float = 16.0) -> Optional[Entity]:
        """Find nearest passive mob."""
        return self.entity_manager.find_nearest_passive(self.position, max_distance)

    def entities_at_position(
        self, position: Tuple[float, float, float], radius: float = 1.0
    ) -> List[Entity]:
        """Get all entities at a position within radius."""
        return self.entity_manager.find_in_radius(position, radius)

    # === Block Finding ===

    def findBlock(self, block_type: str, options: Optional[Dict] = None) -> Optional[Block]:
        """Find nearest block of specified type."""
        options = options or {}
        max_distance = options.get("max_distance", 16)
        matching = options.get("matching", None)
        point = options.get("point", self.position)

        if not point:
            return None

        return self.world.find_block(
            point[0], point[1], point[2], block_type=block_type, max_distance=max_distance
        )

    def findBlocks(self, block_type: str, options: Optional[Dict] = None) -> List[Block]:
        """Find all blocks of specified type."""
        options = options or {}
        max_distance = options.get("max_distance", 16)
        count = options.get("count", 64)
        point = options.get("point", self.position)

        if not point:
            return []

        return self.world.find_blocks(
            point[0],
            point[1],
            point[2],
            block_type=block_type,
            max_distance=max_distance,
            limit=count,
        )

    # === Inventory Operations ===

    async def send_set_held_slot(self, slot: int) -> None:
        """Send Set Held Item packet (0x2C for 1.21.4)"""
        if slot < 0 or slot > 8:
            raise ValueError("Hotbar slot must be 0-8")

        buf = Buffer()
        buf.write_varint(slot)
        await self._write_packet(0x2C, bytes(buf))

        self.held_item_slot = slot
        print(f"[INVENTORY] Held slot changed to {slot}")

    async def send_close_container(self, container_id: Optional[int] = None) -> None:
        """Send Close Container packet (0x0E for 1.21.4)"""
        if container_id is None:
            container_id = self.open_container_id

        if container_id is None:
            return

        buf = Buffer()
        buf.write_varint(container_id)
        await self._write_packet(0x0E, bytes(buf))

        self.open_container_id = None
        self.emit("container_close", container_id)

    async def send_container_click(
        self, container_id: int, slot: int, button: int, mode: int, item: Optional[Item] = None
    ) -> None:
        """Send Container Click packet (0x0F for 1.21.4)"""
        self._inventory_sequence += 1

        buf = Buffer()
        buf.write_varint(container_id)
        buf.write_varint(self._inventory_sequence)
        buf.write_varint(slot)
        buf.write_value(StructFormat.BYTE, button)
        buf.write_varint(mode)

        # Write clicked item
        if item and not item.is_empty:
            buf.write_varint(item.item_id)
            buf.write_value(StructFormat.BYTE, item.count)
            # Write components (simplified)
            buf.write_varint(0)  # added components
            buf.write_varint(0)  # removed components
        else:
            buf.write_varint(0)  # empty slot

        await self._write_packet(0x0F, bytes(buf))

    async def left_click(self, slot: int, container_id: int = 0) -> None:
        """Left click on a slot."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP,
            item=self._cursor_item,
        )

    async def right_click(self, slot: int, container_id: int = 0) -> None:
        """Right click on a slot."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.RIGHT,
            mode=ClickMode.PICKUP,
            item=self._cursor_item,
        )

    async def shift_click(self, slot: int, container_id: int = 0) -> None:
        """Shift-click on a slot."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.QUICK_MOVE,
            item=None,
        )

    async def drop_slot(self, slot: int, drop_stack: bool = False, container_id: int = 0) -> None:
        """Drop item from slot."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.RIGHT if drop_stack else ClickButton.LEFT,
            mode=ClickMode.THROW,
            item=None,
        )

    async def swap_hotbar(self, slot: int, hotbar_slot: int, container_id: int = 0) -> None:
        """Swap slot with hotbar."""
        await self.send_container_click(
            container_id=container_id, slot=slot, button=hotbar_slot, mode=ClickMode.SWAP, item=None
        )

    async def pickup_all(self, slot: int, container_id: int = 0) -> None:
        """Pickup all items of same type."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP_ALL,
            item=self._cursor_item,
        )

    async def clone_item(self, slot: int, container_id: int = 0) -> None:
        """Clone item (creative only)."""
        await self.send_container_click(
            container_id=container_id,
            slot=slot,
            button=ClickButton.MIDDLE,
            mode=ClickMode.CLONE,
            item=None,
        )

    async def drop_cursor(self) -> None:
        """Drop item on cursor."""
        await self.send_container_click(
            container_id=0,
            slot=-999,
            button=ClickButton.LEFT,
            mode=ClickMode.PICKUP,
            item=self._cursor_item,
        )
        self._cursor_item = None

    # === Advanced Inventory ===
    
    @property
    def held_item(self) -> Optional[Item]:
        """Get currently held item"""
        return self._inventory_mgr.held_item
    
    @property
    def equipment(self) -> Dict[str, Optional[Item]]:
        """Get all equipped items"""
        return self._inventory_mgr.equipment
    
    async def set_quick_bar_slot(self, slot: int) -> None:
        """Set the selected hotbar slot (0-8)"""
        await self._inventory_mgr.set_quick_bar_slot(slot)
    
    async def toss(self, item_type: int, count: int = 1) -> bool:
        """Toss (drop) items from inventory"""
        return await self._inventory_mgr.toss(item_type, count)
    
    async def toss_all(self, item_type: int) -> int:
        """Toss all items of a type"""
        return await self._inventory_mgr.toss_all(item_type)
    
    def count_item(self, item_type: int) -> int:
        """Count total items of a type in inventory"""
        return self._inventory_mgr.count_item(item_type)
    
    def find_inventory_item(self, item_type: int) -> Optional[Item]:
        """Find first item of a type in inventory"""
        return self._inventory_mgr.player_inventory.find_item(
            item_type,
            self._inventory_mgr.INVENTORY_START,
            self._inventory_mgr.INVENTORY_END
        )
    
    def free_inventory_slots(self) -> int:
        """Get count of free inventory slots"""
        return self._inventory_mgr.free_slots()

    # === Block Interaction ===
    
    async def place_block(self, block: 'Block', face: int = 1, sneak: bool = False):
        """
        Place a block against another block.
        
        Args:
            block: Reference block to place against
            face: Block face (0=bottom, 1=top, 2=north, 3=south, 4=west, 5=east)
            sneak: Whether to sneak
            
        Returns:
            BlockInteraction result
        """
        from .block_interaction import BlockFace
        return await self._block_interaction.place_block(block, BlockFace(face), sneak)
    
    async def place_block_at(self, x: int, y: int, z: int, sneak: bool = False):
        """Place a block at a specific position"""
        return await self._block_interaction.place_block_at(x, y, z, sneak)
    
    async def activate_block(self, block: 'Block'):
        """Activate a block (button, lever, door, etc.)"""
        return await self._block_interaction.activate_block(block)
    
    async def open_container(self, block: 'Block') -> bool:
        """Open a container block (chest, furnace, etc.)"""
        return await self._block_interaction.open_container(block)

    # === Advanced Inventory (Anvil & Enchanting) ===
    
    @property
    def advanced_inventory(self) -> 'AdvancedInventory':
        """Get the advanced inventory manager"""
        return self._advanced_inv
    
    @property
    def anvil(self) -> 'AnvilManager':
        """Get the anvil manager"""
        return self._advanced_inv.anvil
    
    @property
    def enchanting(self) -> 'EnchantingManager':
        """Get the enchanting manager"""
        return self._advanced_inv.enchanting
    
    async def open_anvil(self, block: 'Block') -> 'AnvilManager':
        """
        Open an anvil and return the anvil manager.
        
        Args:
            block: Anvil block to open
            
        Returns:
            AnvilManager instance for combining, renaming, repairing items
        """
        return await self._advanced_inv.open_anvil(block)
    
    async def open_enchanting_table(self, block: 'Block') -> 'EnchantingManager':
        """
        Open an enchanting table and return the manager.
        
        Args:
            block: Enchanting table block to open
            
        Returns:
            EnchantingManager instance for enchanting items
        """
        return await self._advanced_inv.open_enchanting_table(block)

    # === Villager Trading ===

    async def open_villager(self, villager_entity) -> 'VillagerWindow':
        """
        Open a villager trading window.

        Args:
            villager_entity: Villager entity to trade with

        Returns:
            VillagerWindow instance for trading

        Raises:
            ValueError: If entity is not a villager
            TimeoutError: If window doesn't open in time
        """
        return await self._villager_mgr.open_villager(villager_entity)

    async def trade(self, villager_window: 'VillagerWindow', trade_index: int, count: Optional[int] = None) -> None:
        """
        Execute a trade with a villager.

        Args:
            villager_window: Open villager trading window
            trade_index: Index of trade in villager_window.trades
            count: Number of times to execute trade (default: max available)

        Raises:
            ValueError: If trade is invalid or unavailable
            RuntimeError: If bot doesn't have required items
        """
        await self._villager_mgr.trade(villager_window, trade_index, count)

    def nearest_villager(self, max_distance: float = 16.0) -> Optional['Entity']:
        """
        Find nearest villager entity.

        Args:
            max_distance: Maximum search distance

        Returns:
            Villager entity or None if not found
        """
        from ..entities import MobType

        nearest = None
        min_dist = max_distance

        for entity in self.entities.values():
            if hasattr(entity, 'mob_type') and entity.mob_type == MobType.VILLAGER:
                dist = self.distance_to(entity)
                if dist < min_dist:
                    min_dist = dist
                    nearest = entity

        return nearest


    # === Creative Mode ===

    @property
    def creative(self) -> 'CreativeManager':
        """Get the creative mode manager"""
        return self._creative

    async def set_creative_slot(self, slot: int, item: Optional['Item'], wait_timeout: float = 0.4) -> None:
        """
        Set inventory slot to specific item (creative mode only).

        Args:
            slot: Slot number (0-44 for player inventory)
            item: Item to set (None to clear slot)
            wait_timeout: Seconds to wait for confirmation (0 = no wait)

        Raises:
            ValueError: If slot is out of range
            RuntimeError: If called twice on same slot before first completes
        """
        await self._creative.set_slot(slot, item, wait_timeout)

    async def clear_creative_slot(self, slot: int) -> None:
        """
        Clear a specific inventory slot (creative mode only).

        Args:
            slot: Slot number (0-44)
        """
        await self._creative.clear_slot(slot)

    async def clear_creative_inventory(self) -> None:
        """
        Clear entire player inventory (creative mode only).
        """
        await self._creative.clear_inventory()

    async def fly_to(self, x: float, y: float, z: float) -> None:
        """
        Fly in a straight line to destination (creative mode only).

        Args:
            x, y, z: Target coordinates
        """
        await self._creative.fly_to(x, y, z)

    def start_flying(self) -> None:
        """
        Start flying - disable gravity (creative mode only).
        """
        self._creative.start_flying()

    def stop_flying(self) -> None:
        """
        Stop flying - restore gravity (creative mode only).
        """
        self._creative.stop_flying()

    @property
    def is_flying(self) -> bool:
        """Check if currently flying"""
        return self._creative.is_flying


    # === Brewing Stand ===

    async def open_brewing_stand(self, block) -> 'BrewingWindow':
        """
        Open a brewing stand.

        Args:
            block: Brewing stand block to open

        Returns:
            BrewingWindow object

        Raises:
            RuntimeError: If window is not a brewing stand
        """
        return await self._brewing.open_brewing_stand(block)


    # === Entity Breeding & Taming ===

    def can_breed(self, entity) -> 'BreedableStatus':
        """
        Check if an entity can breed.

        Args:
            entity: Entity to check

        Returns:
            BreedableStatus indicating breeding capability
        """
        return self._entity_interaction.can_breed(entity)

    async def breed(self, entity) -> bool:
        """
        Breed an entity by feeding it.

        Args:
            entity: Entity to breed

        Returns:
            True if breeding initiated, False if failed

        Raises:
            RuntimeError: If entity cannot breed
        """
        return await self._entity_interaction.breed(entity)

    def can_tame(self, entity) -> 'TamableStatus':
        """
        Check if an entity can be tamed.

        Args:
            entity: Entity to check

        Returns:
            TamableStatus indicating taming capability
        """
        return self._entity_interaction.can_tame(entity)

    async def tame(self, entity) -> bool:
        """
        Tame an entity by feeding it.

        Args:
            entity: Entity to tame

        Returns:
            True if taming attempted, False if failed

        Raises:
            RuntimeError: If entity cannot be tamed
        """
        return await self._entity_interaction.tame(entity)

    def get_breeding_items(self, entity) -> list[str]:
        """
        Get list of items that can breed this entity.

        Args:
            entity: Entity to check

        Returns:
            List of item names
        """
        return self._entity_interaction.get_breeding_items(entity)

    def get_taming_items(self, entity) -> list[str]:
        """
        Get list of items that can tame this entity.

        Args:
            entity: Entity to check

        Returns:
            List of item names
        """
        return self._entity_interaction.get_taming_items(entity)


    # === Boss Bar Tracking ===

    @property
    def boss_bars(self) -> 'BossBarManager':
        """Get the boss bar manager"""
        return self._boss_bar

    def get_boss_bar(self, uuid):
        """
        Get boss bar by UUID.

        Args:
            uuid: Boss bar UUID

        Returns:
            BossBar or None if not found
        """
        return self._boss_bar.get_boss_bar(uuid)

    def get_all_boss_bars(self) -> list:
        """
        Get all active boss bars.

        Returns:
            List of all BossBar objects
        """
        return self._boss_bar.get_all_boss_bars()


    # === Scoreboard Tracking ===

    @property
    def scoreboards(self) -> dict:
        """Get all scoreboards dictionary"""
        return self._scoreboard_mgr.scoreboards

    def get_scoreboard(self, name: str):
        """
        Get scoreboard by objective name.

        Args:
            name: Objective name

        Returns:
            Scoreboard or None if not found
        """
        return self._scoreboard_mgr.get_scoreboard(name)

    def get_all_scoreboards(self) -> list:
        """
        Get all scoreboards.

        Returns:
            List of all Scoreboard objects
        """
        return self._scoreboard_mgr.get_all_scoreboards()

    def get_scoreboard_position(self, position):
        """
        Get scoreboard at a display position.

        Args:
            position: ScoreboardPosition (0=list, 1=sidebar, 2=below_name)

        Returns:
            Scoreboard at position or None
        """
        return self._scoreboard_mgr.get_display_position(position)

        return self._scoreboard_mgr.get_display_position(position)

    # === Tablist Tracking ===

    @property
    def tablist(self) -> 'TabList':
        """Get tablist manager"""
        return self._tablist

    def get_player(self, uuid: str):
        """
        Get player by UUID from tablist.

        Args:
            uuid: Player UUID

        Returns:
            Player data or None if not found
        """
        return self._tablist.get_player(uuid)

    # === Title Tracking ===

    @property
    def title(self) -> 'TitleManager':
        """Get title manager"""
        return self._title

    # === Team Tracking ===

    @property
    def teams(self) -> dict:
        """Get all teams dictionary"""
        return self._team.teams

    def get_team(self, name: str):
        """
        Get team by name.

        Args:
            name: Team name

        Returns:
            Team or None if not found
        """
        return self._team.get_team(name)

    def get_player_team(self, uuid: str):
        """
        Get team for a player.

        Args:
            uuid: Player UUID

        Returns:
            Team or None if player not in a team
        """
        return self._team.get_player_team(uuid)

    # === Particle Tracking ===

    @property
    def particle(self) -> 'ParticleManager':
        """Get particle manager"""
        return self._particle

    # === Sound Tracking ===

    @property
    def sound(self) -> 'SoundManager':
        """Get sound manager"""
        return self._sound

    # === Bed Tracking ===
    @property
    def bed(self) -> 'BedManager':
        """Get bed manager"""
        return self._bed_mgr

    # === Kick Tracking ===
    @property
    def kick_manager(self) -> 'KickManager':
        """Get kick manager"""
        return self._kick

    # === Explosion Tracking ===
    @property
    def explosion_manager(self) -> 'ExplosionManager':
        """Get explosion manager"""
        return self._explosion

    # === Fishing ===
    @property
    def fishing(self) -> 'FishingManager':
        """Get fishing manager"""
        return self._fishing

    # === Weather Tracking ===
    @property
    def weather(self) -> 'WeatherManager':
        """Get weather manager"""
        return self._weather

    # === Resource Pack Tracking ===
    @property
    def resource_pack(self) -> 'ResourcePackManager':
        """Get resource pack manager"""
        return self._resource_pack

    # === Settings Tracking ===
    @property
    def client_settings(self) -> 'SettingsManager':
        """Get client settings manager"""
        return self._settings

    # === Spawn Point Tracking ===
    @property
    def spawn_point(self) -> 'SpawnPointManager':
        """Get spawn point manager"""
        return self._spawn_point

    # === Time Tracking ===
    @property
    def game_time(self) -> 'TimeManager':
        """Get game time manager"""
        return self._time_mgr

    # === Experience Tracking ===
    @property
    def experience(self) -> 'ExperienceManager':
        """Get experience manager"""
        return self._experience

    # === Game State Tracking ===
    @property
    def game_state(self) -> 'GameStateManager':
        """Get game state manager"""
        return self._game_state

    # === Ray Trace Tracking ===
    @property
    def ray_trace(self) -> 'RayTraceManager':
        """Get ray trace manager"""
        return self._ray_trace
    # === Book Editing ===

    @property
    def book(self) -> 'BookManager':
        """Get book manager"""
        return self._book

    async def edit_book(self, slot: int, pages=None, title=None, author=None, signing=False):
        """
        Edit a book in inventory.

        Args:
            slot: Book slot (0-44)
            pages: List of page strings (JSON components)
            title: Book title
            author: Book author
            signing: Whether to sign the book
        """
        await self._book.edit_book(slot, pages, title, author, signing)

    async def read_book(self, slot: int):
        """
        Read book data from inventory slot.

        Args:
            slot: Book slot (0-44)

        Returns:
            Book object or None if not a book
        """
        return await self._book.read_book(slot)

    # === Pathfinding ===
    
    @property
    def pathfinder(self) -> 'PathfinderManager':
        """Get the pathfinder manager"""
        return self._pathfinder
    
    async def goto(self, x: float, y: float, z: float, max_distance: int = 64) -> bool:
        """
        Navigate to a position using pathfinding.
        
        Args:
            x, y, z: Target coordinates
            max_distance: Maximum pathfinding distance
            
        Returns:
            True if reached, False if failed
        """
        return await self._pathfinder.goto(x, y, z, max_distance)
    
    async def goto_block(self, block: 'Block', max_distance: int = 64) -> bool:
        """Navigate to a block using pathfinding"""
        return await self._pathfinder.goto_block(block, max_distance)
    
    async def goto_entity(self, entity, max_distance: int = 64) -> bool:
        """Navigate to an entity using pathfinding"""
        return await self._pathfinder.goto_entity(entity, max_distance)
    
    def stop_pathfinding(self) -> None:
        """Stop current pathfinding movement"""

    # === Vehicles ===
    
    @property
    def vehicle(self) -> 'VehicleManager':
        """Get the vehicle manager"""
        return self._vehicle_mgr
    
    @property
    def is_riding(self) -> bool:
        """Check if bot is riding a vehicle"""
        return self._vehicle_mgr.is_riding
    
    async def mount(self, entity) -> bool:
        """
        Mount (ride) an entity.
        
        Args:
            entity: Entity to mount (boat, minecart, horse, etc.)
            
        Returns:
            True if successfully mounted
        """
        return await self._vehicle_mgr.mount(entity)
    
    async def dismount(self) -> bool:
        """
        Dismount from current vehicle.
        
        Returns:
            True if successfully dismounted
        """
        return await self._vehicle_mgr.dismount()
    
    async def move_boat(self, forward: bool = False, backward: bool = False, 
                        left: bool = False, right: bool = False) -> None:
        """Control boat movement"""
        await self._vehicle_mgr.move_boat(forward, backward, left, right)
    
    async def move_horse(self, forward: bool = False, backward: bool = False,
                         left: bool = False, right: bool = False,
                         jump: bool = False, sprint: bool = False) -> None:
        """Control horse movement"""
        await self._vehicle_mgr.move_horse(forward, backward, left, right, jump, sprint)
    
    async def horse_jump(self, power: float = 1.0) -> None:
        """Make the horse jump"""
        await self._vehicle_mgr.horse_jump(power)

    # === Connection Management ===

    async def _receive_loop(self) -> None:
        """Main packet receiving loop"""
        while self._running:
            try:
                packet_id, buf = await self._read_packet()

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

    async def connect(self) -> None:
        """Connect to the server"""
        print(f"Connecting to {self.host}:{self.port}...")

        self.connection = await TCPAsyncConnection.make_client((self.host, self.port), timeout=10.0)

        print("TCP connection established")
        self.emit("connect")

        await self.send_handshake(next_state=2)
        print("Handshake sent")

        await self.send_login_start()
        print("Login start sent")

        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # Start physics after spawn (will be started when spawn event fires)

    async def disconnect(self) -> None:
        """Disconnect from the server"""
        self._running = False
        
        # Stop physics
        self.stop_physics()

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
        "chat",
        "player_joined",
        "entity_spawn",
        "entity_gone",
        "entity_metadata",
        "entity_attack",
        "entity_interact",
        "entity_use_on",
    ]:
        handler = options.get(f"on_{event}")
        if handler:
            bot.on(event, handler)

    await bot.connect()
    return bot


__all__ = ["MinecraftProtocol", "create_bot"]
