"""
Entity system for Minecraft 1.21.4

Handles all entity types:
- Players (other players in game)
- Mobs (hostile, neutral, passive)
- Objects (items, arrows, boats, minecarts, etc.)
- Global entities (lightning, etc.)

Protocol packets handled:
- 0x01: Spawn Entity (objects)
- 0x02: Spawn Experience Orb
- 0x03: Entity Animation
- 0x19: Entity Event
- 0x1F: Entity Position (relative)
- 0x20: Entity Position and Rotation
- 0x21: Entity Rotation
- 0x3A: Remove Entities
- 0x3E: Remove Entities (batch)
- 0x3F: Teleport Entity
- 0x48: Entity Equipment
- 0x4A: Set Entity Metadata
- 0x4B: Set Entity Link (vehicle/rider)
- 0x56: Entity Update Attributes
- 0x5A: Player Spawn
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, IntEnum
import struct


class EntityType(str, Enum):
    """Entity type categories"""

    PLAYER = "player"
    MOB = "mob"
    OBJECT = "object"
    GLOBAL = "global"
    OTHER = "other"


class EntityKind(str, Enum):
    """Entity behavior kind"""

    PLAYER = "player"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    PASSIVE = "passive"


class MobType(IntEnum):
    """Mob type IDs (entity type in Spawn Entity packet)"""

    # Hostile
    CREEPER = 0
    SKELETON = 1
    SPIDER = 2
    GIANT = 3
    ZOMBIE = 4
    SLIME = 5
    GHAST = 6
    ZOMBIFIED_PIGLIN = 7
    ENDERMAN = 8
    CAVE_SPIDER = 9
    SILVERFISH = 10
    BLAZE = 11
    MAGMA_CUBE = 12
    WITHER = 13
    BAT = 14
    WITCH = 15
    ENDERMITE = 16
    GUARDIAN = 17
    SHULKER = 18
    WITHER_SKELETON = 30
    STRAY = 31
    HUSK = 32
    ZOMBIE_VILLAGER = 33
    SKELETON_HORSE = 34
    ZOMBIE_HORSE = 35
    ELDER_GUARDIAN = 36
    STRIDER = 37
    DROWNED = 38
    PHANTOM = 39
    RAVAGER = 45
    PILLAGER = 46
    VINDICATOR = 47
    EVOKER = 48
    VEX = 49
    WARDEN = 69

    # Passive
    PIG = 19
    SHEEP = 20
    COW = 21
    CHICKEN = 22
    SQUID = 23
    WOLF = 24
    MOOSHROOM = 25
    SNOW_GOLEM = 26
    OCELOT = 27
    IRON_GOLEM = 28
    HORSE = 29
    RABBIT = 40
    POLAR_BEAR = 41
    LLAMA = 42
    PARROT = 43
    VILLAGER = 44
    TURTLE = 58
    COD = 59
    SALMON = 60
    PUFFERFISH = 61
    TROPICAL_FISH = 62
    DOLPHIN = 63
    DONKEY = 64
    MULE = 65
    FOX = 66
    PANDA = 67
    BEE = 70
    HOGLIN = 71
    PIGLIN = 72
    AXOLOTL = 73
    GOAT = 74
    FROG = 75
    TADPOLE = 76
    ALLAY = 77
    CAMEL = 78
    SNIFFER = 79


class ObjectType(IntEnum):
    """Object type IDs for Spawn Entity packet"""

    AREA_EFFECT_CLOUD = 0
    ARMOR_STAND = 1
    BLOCK_DISPLAY = 2
    BOAT = 3
    CHEST_BOAT = 4
    CHEST_MINECART = 5
    COMMAND_BLOCK_MINECART = 6
    ENDER_PEARL = 7
    EYE_OF_ENDER = 8
    FALLING_BLOCK = 9
    FIREWORK_ROCKET = 10
    FURNACE_MINECART = 11
    HOPPER_MINECART = 12
    ITEM = 13
    ITEM_DISPLAY = 14
    ITEM_FRAME = 15
    LEASH_KNOT = 16
    LIGHTNING_BOLT = 17
    LLAMA_SPIT = 18
    MINECART = 19
    PAINTING = 20
    PRIMED_TNT = 21
    SHULKER_BULLET = 22
    SPAWNER_MINECART = 23
    TEXT_DISPLAY = 24
    TRIDENT = 25
    TNT_MINECART = 26
    ARROW = 27
    SPECTRAL_ARROW = 28
    DRAGON_FIREBALL = 29
    EGG = 30
    EVOKER_FANGS = 31
    EXPERIENCE_BOTTLE = 32
    FIREBALL = 33
    FISHING_BOBBER = 34
    LARGE_FIREBALL = 35
    LLAMA_SPIT_2 = 36
    POTION = 37
    SHULKER_BULLET_2 = 38
    SMALL_FIREBALL = 39
    SNOWBALL = 40
    WITHER_SKULL = 41
    WIND_CHARGE = 42
    BREEZE_WIND_CHARGE = 43
    INTERACTION = 44
    GLOW_ITEM_FRAME = 45
    MARKER = 46
    OAK_BOAT = 47
    OAK_CHEST_BOAT = 48
    # More boat types...


# Mob categories for classification
HOSTILE_MOBS = {
    MobType.CREEPER,
    MobType.SKELETON,
    MobType.SPIDER,
    MobType.ZOMBIE,
    MobType.SLIME,
    MobType.GHAST,
    MobType.ENDERMAN,
    MobType.CAVE_SPIDER,
    MobType.SILVERFISH,
    MobType.BLAZE,
    MobType.MAGMA_CUBE,
    MobType.WITHER,
    MobType.WITCH,
    MobType.ENDERMITE,
    MobType.GUARDIAN,
    MobType.SHULKER,
    MobType.WITHER_SKELETON,
    MobType.STRAY,
    MobType.HUSK,
    MobType.ELDER_GUARDIAN,
    MobType.DROWNED,
    MobType.PHANTOM,
    MobType.RAVAGER,
    MobType.PILLAGER,
    MobType.VINDICATOR,
    MobType.EVOKER,
    MobType.VEX,
    MobType.WARDEN,
}

PASSIVE_MOBS = {
    MobType.PIG,
    MobType.SHEEP,
    MobType.COW,
    MobType.CHICKEN,
    MobType.SQUID,
    MobType.WOLF,
    MobType.MOOSHROOM,
    MobType.SNOW_GOLEM,
    MobType.OCELOT,
    MobType.IRON_GOLEM,
    MobType.HORSE,
    MobType.RABBIT,
    MobType.POLAR_BEAR,
    MobType.LLAMA,
    MobType.PARROT,
    MobType.VILLAGER,
    MobType.TURTLE,
    MobType.COD,
    MobType.SALMON,
    MobType.PUFFERFISH,
    MobType.TROPICAL_FISH,
    MobType.DOLPHIN,
    MobType.DONKEY,
    MobType.MULE,
    MobType.FOX,
    MobType.PANDA,
    MobType.BEE,
    MobType.AXOLOTL,
    MobType.GOAT,
    MobType.FROG,
    MobType.TADPOLE,
    MobType.ALLAY,
    MobType.CAMEL,
    MobType.SNIFFER,
}

NEUTRAL_MOBS = {
    MobType.ZOMBIFIED_PIGLIN,
    MobType.BAT,
    MobType.STRIDER,
    MobType.HOGLIN,
    MobType.PIGLIN,
    MobType.SKELETON_HORSE,
    MobType.ZOMBIE_HORSE,
    MobType.ZOMBIE_VILLAGER,
}


@dataclass
class EntityEquipment:
    """Equipment slots for an entity"""

    main_hand: Optional[Any] = None  # Item
    off_hand: Optional[Any] = None
    head: Optional[Any] = None
    chest: Optional[Any] = None
    legs: Optional[Any] = None
    feet: Optional[Any] = None

    def get_slot(self, slot: int) -> Optional[Any]:
        """Get equipment by slot index"""
        slots = [
            self.main_hand,
            self.off_hand,
            self.feet,
            self.legs,
            self.chest,
            self.head,
        ]
        if 0 <= slot < len(slots):
            return slots[slot]
        return None

    def set_slot(self, slot: int, item: Optional[Any]) -> None:
        """Set equipment by slot index"""
        if slot == 0:
            self.main_hand = item
        elif slot == 1:
            self.off_hand = item
        elif slot == 2:
            self.feet = item
        elif slot == 3:
            self.legs = item
        elif slot == 4:
            self.chest = item
        elif slot == 5:
            self.head = item


@dataclass
class Entity:
    """
    Represents any entity in the Minecraft world.

    Entities include:
    - Players (other players, not the bot)
    - Mobs (zombies, cows, etc.)
    - Objects (items, arrows, boats, etc.)
    - Global entities (lightning)
    """

    entity_id: int
    entity_type: EntityType = EntityType.OTHER
    kind: EntityKind = EntityKind.PASSIVE

    # Identification
    uuid: Optional[str] = None
    name: str = ""
    custom_name: Optional[str] = None

    # Position and movement
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    yaw: float = 0.0
    pitch: float = 0.0
    head_yaw: float = 0.0
    on_ground: bool = True

    # Dimensions
    height: float = 1.0
    width: float = 0.6
    eye_height: float = 0.5

    # State
    health: float = 20.0
    max_health: float = 20.0
    is_dead: bool = False

    # Equipment (for players and mobs)
    equipment: EntityEquipment = field(default_factory=EntityEquipment)

    # Metadata
    metadata: Dict[int, Any] = field(default_factory=dict)

    # Vehicle/rider
    vehicle: Optional["Entity"] = None
    passengers: List["Entity"] = field(default_factory=list)

    # Object-specific
    object_type: Optional[int] = None  # For objects
    object_data: int = 0

    # Mob-specific
    mob_type: Optional[MobType] = None

    # Player-specific
    username: Optional[str] = None
    ping: int = 0
    gamemode: str = "survival"

    # Raw data
    raw: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.entity_type == EntityType.PLAYER:
            return f"Player({self.username or self.name}, id={self.entity_id})"
        elif self.entity_type == EntityType.MOB:
            return f"Mob({self.name or self.mob_type}, id={self.entity_id})"
        elif self.entity_type == EntityType.OBJECT:
            return f"Object({self.name}, id={self.entity_id})"
        return f"Entity(type={self.entity_type}, id={self.entity_id})"

    def __str__(self) -> str:
        return self.name or f"Entity({self.entity_id})"

    # Position helpers

    @property
    def x(self) -> float:
        return self.position[0]

    @property
    def y(self) -> float:
        return self.position[1]

    @property
    def z(self) -> float:
        return self.position[2]

    def distance_to(self, other: Union["Entity", Tuple[float, float, float]]) -> float:
        """
        Calculate distance to another entity or position.

        Args:
            other: Entity or (x, y, z) tuple

        Returns:
            Euclidean distance
        """
        if isinstance(other, Entity):
            ox, oy, oz = other.position
        else:
            ox, oy, oz = other

        dx = self.x - ox
        dy = self.y - oy
        dz = self.z - oz
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def distance_to_2d(self, other: Union["Entity", Tuple[float, float]]) -> float:
        """Calculate 2D (horizontal) distance"""
        if isinstance(other, Entity):
            ox, oz = other.x, other.z
        else:
            ox, oz = other[0], other[1]

        dx = self.x - ox
        dz = self.z - oz
        return math.sqrt(dx * dx + dz * dz)

    # State helpers

    @property
    def is_hostile(self) -> bool:
        """Check if entity is hostile"""
        return self.kind == EntityKind.HOSTILE

    @property
    def is_passive(self) -> bool:
        """Check if entity is passive"""
        return self.kind == EntityKind.PASSIVE

    @property
    def is_neutral(self) -> bool:
        """Check if entity is neutral"""
        return self.kind == EntityKind.NEUTRAL

    @property
    def is_player(self) -> bool:
        """Check if entity is a player"""
        return self.entity_type == EntityType.PLAYER

    @property
    def is_mob(self) -> bool:
        """Check if entity is a mob"""
        return self.entity_type == EntityType.MOB

    @property
    def is_object(self) -> bool:
        """Check if entity is an object"""
        return self.entity_type == EntityType.OBJECT

    @property
    def is_item(self) -> bool:
        """Check if entity is a dropped item"""
        return self.object_type == ObjectType.ITEM

    @property
    def is_vehicle(self) -> bool:
        """Check if entity can be ridden"""
        return len(self.passengers) > 0 or self.object_type in (
            ObjectType.BOAT,
            ObjectType.CHEST_BOAT,
            ObjectType.MINECART,
            ObjectType.CHEST_MINECART,
            ObjectType.FURNACE_MINECART,
            ObjectType.HOPPER_MINECART,
            ObjectType.TNT_MINECART,
        )

    # Equipment helpers

    @property
    def held_item(self) -> Optional[Any]:
        """Get item in main hand"""
        return self.equipment.main_hand

    def get_equipment(self, slot: str) -> Optional[Any]:
        """Get equipment by slot name"""
        return getattr(self.equipment, slot, None)
    
    # Bounding box helpers
    
    @property
    def bounding_box(self) -> Tuple[float, float, float, float, float, float]:
        """
        Get entity bounding box as (min_x, min_y, min_z, max_x, max_y, max_z).
        
        The bounding box is centered on the entity's position with the
        entity's feet at position.y.
        """
        half_width = self.width / 2
        return (
            self.x - half_width,  # min_x
            self.y,               # min_y (feet)
            self.z - half_width,  # min_z
            self.x + half_width,  # max_x
            self.y + self.height, # max_y (head)
            self.z + half_width,  # max_z
        )
    
    def is_point_inside(self, x: float, y: float, z: float) -> bool:
        """
        Check if a point is inside this entity's bounding box.
        
        Args:
            x, y, z: World coordinates
            
        Returns:
            True if point is inside bounding box
        """
        min_x, min_y, min_z, max_x, max_y, max_z = self.bounding_box
        return (
            min_x <= x <= max_x and
            min_y <= y <= max_y and
            min_z <= z <= max_z
        )
    
    def intersects(self, other: "Entity") -> bool:
        """
        Check if this entity's bounding box intersects with another.
        
        Args:
            other: Another entity
            
        Returns:
            True if bounding boxes intersect
        """
        a_min_x, a_min_y, a_min_z, a_max_x, a_max_y, a_max_z = self.bounding_box
        b_min_x, b_min_y, b_min_z, b_max_x, b_max_y, b_max_z = other.bounding_box
        
        return (
            a_min_x < b_max_x and a_max_x > b_min_x and
            a_min_y < b_max_y and a_max_y > b_min_y and
            a_min_z < b_max_z and a_max_z > b_min_z
        )
    
    def get_eye_position(self) -> Tuple[float, float, float]:
        """
        Get the position of the entity's eyes.
        
        Returns:
            (x, y, z) of eye position
        """
        return (self.x, self.y + self.eye_height, self.z)
    
    def get_look_vector(self) -> Tuple[float, float, float]:
        """
        Get the direction the entity is looking.
        
        Returns:
            Normalized (dx, dy, dz) look vector
        """
        # Convert yaw/pitch to radians
        yaw_rad = math.radians(-self.yaw)
        pitch_rad = math.radians(-self.pitch)
        
        # Calculate direction vector
        dx = math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = math.sin(pitch_rad)
        dz = math.cos(yaw_rad) * math.cos(pitch_rad)
        
        return (dx, dy, dz)
    
    def can_see(self, other: "Entity") -> bool:
        """
        Check if this entity can see another (line of sight).
        
        Note: This is a simplified check that doesn't account for blocks.
        
        Args:
            other: Target entity
            
        Returns:
            True if within view distance and roughly facing
        """
        # Check distance
        dist = self.distance_to(other)
        if dist > 128:  # Max view distance
            return False
        
        # Check if facing (simplified - within 90 degree cone)
        dx = other.x - self.x
        dy = other.y + other.height / 2 - (self.y + self.eye_height)
        dz = other.z - self.z
        
        # Normalize target direction
        target_dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if target_dist == 0:
            return True
        
        target_dir = (dx/target_dist, dy/target_dist, dz/target_dist)
        look_dir = self.get_look_vector()
        
        # Dot product to check angle
        dot = (
            look_dir[0] * target_dir[0] +
            look_dir[1] * target_dir[1] +
            look_dir[2] * target_dir[2]
        )
        
        # cos(90°) = 0, so positive means within 90 degree cone
        return dot > 0

class EntityManager:
    """
    Manages all entities in the world.

    Provides:
    - Entity storage and lookup
    - Entity spawning and removal
    - Entity search methods
    """

    def __init__(self):
        self.entities: Dict[int, Entity] = {}  # entity_id -> Entity
        self.players_by_uuid: Dict[str, Entity] = {}  # uuid -> Entity (players only)

    def add(self, entity: Entity) -> None:
        """Add an entity to the manager"""
        self.entities[entity.entity_id] = entity
        if entity.uuid and entity.entity_type == EntityType.PLAYER:
            self.players_by_uuid[entity.uuid] = entity

    def remove(self, entity_id: int) -> Optional[Entity]:
        """Remove and return an entity by ID"""
        entity = self.entities.pop(entity_id, None)
        if entity and entity.uuid and entity.uuid in self.players_by_uuid:
            del self.players_by_uuid[entity.uuid]
        return entity

    def get(self, entity_id: int) -> Optional[Entity]:
        """Get entity by ID"""
        return self.entities.get(entity_id)

    def get_by_uuid(self, uuid: str) -> Optional[Entity]:
        """Get player entity by UUID"""
        return self.players_by_uuid.get(uuid)

    def get_all(self) -> List[Entity]:
        """Get all entities"""
        return list(self.entities.values())

    def get_players(self) -> List[Entity]:
        """Get all player entities"""
        return [e for e in self.entities.values() if e.entity_type == EntityType.PLAYER]

    def get_mobs(self) -> List[Entity]:
        """Get all mob entities"""
        return [e for e in self.entities.values() if e.entity_type == EntityType.MOB]

    def get_objects(self) -> List[Entity]:
        """Get all object entities"""
        return [e for e in self.entities.values() if e.entity_type == EntityType.OBJECT]

    def get_hostile(self) -> List[Entity]:
        """Get all hostile entities"""
        return [e for e in self.entities.values() if e.is_hostile]

    def get_passive(self) -> List[Entity]:
        """Get all passive entities"""
        return [e for e in self.entities.values() if e.is_passive]

    def nearest(
        self,
        position: Tuple[float, float, float],
        entity_type: Optional[EntityType] = None,
        kind: Optional[EntityKind] = None,
        max_distance: float = float("inf"),
        filter_func: Optional[Callable[[Entity], bool]] = None,
    ) -> Optional[Entity]:
        """
        Find the nearest entity to a position.

        Args:
            position: Reference position
            entity_type: Filter by entity type
            kind: Filter by entity kind
            max_distance: Maximum distance to search
            filter_func: Custom filter function

        Returns:
            Nearest entity or None
        """
        nearest = None
        nearest_dist = max_distance

        for entity in self.entities.values():
            # Apply filters
            if entity_type and entity.entity_type != entity_type:
                continue
            if kind and entity.kind != kind:
                continue
            if filter_func and not filter_func(entity):
                continue

            dist = entity.distance_to(position)
            if dist < nearest_dist:
                nearest = entity
                nearest_dist = dist

        return nearest

    def nearest_player(
        self, position: Tuple[float, float, float], max_distance: float = float("inf")
    ) -> Optional[Entity]:
        """Find nearest player"""
        return self.nearest(
            position, entity_type=EntityType.PLAYER, max_distance=max_distance
        )

    def nearest_hostile(
        self, position: Tuple[float, float, float], max_distance: float = float("inf")
    ) -> Optional[Entity]:
        """Find nearest hostile mob"""
        return self.nearest(
            position, kind=EntityKind.HOSTILE, max_distance=max_distance
        )

    def nearest_passive(
        self, position: Tuple[float, float, float], max_distance: float = float("inf")
    ) -> Optional[Entity]:
        """Find nearest passive mob"""
        return self.nearest(
            position, kind=EntityKind.PASSIVE, max_distance=max_distance
        )

    def in_range(
        self,
        position: Tuple[float, float, float],
        distance: float,
        entity_type: Optional[EntityType] = None,
    ) -> List[Entity]:
        """
        Find all entities within range of a position.

        Args:
            position: Center position
            distance: Maximum distance
            entity_type: Optional entity type filter

        Returns:
            List of entities in range
        """
        result = []
        for entity in self.entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if entity.distance_to(position) <= distance:
                result.append(entity)
        return result

    def clear(self) -> None:
        """Remove all entities"""
        self.entities.clear()
        self.players_by_uuid.clear()

    def __len__(self) -> int:
        return len(self.entities)

    def __iter__(self):
        return iter(self.entities.values())

    def __contains__(self, entity_id: int) -> bool:
        return entity_id in self.entities


# Utility functions


def classify_mob(mob_type: MobType) -> EntityKind:
    """Classify a mob as hostile, neutral, or passive"""
    if mob_type in HOSTILE_MOBS:
        return EntityKind.HOSTILE
    elif mob_type in PASSIVE_MOBS:
        return EntityKind.PASSIVE
    elif mob_type in NEUTRAL_MOBS:
        return EntityKind.NEUTRAL
    return EntityKind.PASSIVE


def get_mob_name(mob_type: MobType) -> str:
    """Get human-readable mob name"""
    names = {
        MobType.CREEPER: "Creeper",
        MobType.SKELETON: "Skeleton",
        MobType.SPIDER: "Spider",
        MobType.ZOMBIE: "Zombie",
        MobType.SLIME: "Slime",
        MobType.GHAST: "Ghast",
        MobType.ENDERMAN: "Enderman",
        MobType.BLAZE: "Blaze",
        MobType.WITHER: "Wither",
        MobType.BAT: "Bat",
        MobType.WITCH: "Witch",
        MobType.PIG: "Pig",
        MobType.SHEEP: "Sheep",
        MobType.COW: "Cow",
        MobType.CHICKEN: "Chicken",
        MobType.SQUID: "Squid",
        MobType.WOLF: "Wolf",
        MobType.HORSE: "Horse",
        MobType.VILLAGER: "Villager",
        MobType.PARROT: "Parrot",
        MobType.LLAMA: "Llama",
        MobType.FOX: "Fox",
        MobType.PANDA: "Panda",
        MobType.BEE: "Bee",
        MobType.AXOLOTL: "Axolotl",
        MobType.GOAT: "Goat",
        MobType.FROG: "Frog",
        MobType.WARDEN: "Warden",
        # Add more as needed
    }
    return names.get(mob_type, mob_type.name.replace("_", " ").title())


def get_object_name(object_type: ObjectType) -> str:
    """Get human-readable object name"""
    return object_type.name.replace("_", " ").title()
