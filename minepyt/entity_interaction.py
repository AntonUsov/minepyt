"""
Entity breeding and taming for Minecraft 1.21.4

This module provides:
- Breed entities (animals, villagers, etc.)
- Tame entities (wolves, cats, horses, etc.)
- Check breedability and tamability

Breeding and taming are done through right-click (interact) with specific items.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .entities import Entity


class BreedableStatus(IntEnum):
    """Breeding status of an entity"""

    CAN_BREED = 0  # Ready to breed
    IN_LOVE = 1  # Already in love mode
    TOO_YOUNG = 2  # Too young to breed
    WRONG_ITEM = 3  # Wrong breeding item
    NOT_BREEDABLE = 4  # Entity cannot breed


class TamableStatus(IntEnum):
    """Taming status of an entity"""

    CAN_TAME = 0  # Can be tamed
    ALREADY_TAMED = 1  # Already tamed
    WRONG_ITEM = 2  # Wrong taming item
    NOT_TAMABLE = 3  # Entity cannot be tamed


class EntityInteractionManager:
    """
    Manages entity breeding and taming.

    This class handles:
    - Breeding entities with food
    - Taming animals
    - Checking breed/tame requirements
    """

    # Breeding items for common animals
    BREEDING_ITEMS = {
        # Passive animals
        "minecraft:cow": ["minecraft:wheat"],
        "minecraft:sheep": ["minecraft:wheat"],
        "minecraft:pig": ["minecraft:carrot", "minecraft:potato", "minecraft:beetroot"],
        "minecraft:chicken": [
            "minecraft:wheat_seeds",
            "minecraft:melon_seeds",
            "minecraft:pumpkin_seeds",
        ],
        "minecraft:rabbit": ["minecraft:dandelion", "minecraft:carrot", "minecraft:golden_carrot"],
        # Villagers
        "minecraft:villager": [
            "minecraft:bread",
            "minecraft:carrot",
            "minecraft:potato",
            "minecraft:beetroot",
        ],
        "minecraft:villager_v2": [
            "minecraft:bread",
            "minecraft:carrot",
            "minecraft:potato",
            "minecraft:beetroot",
        ],
        # Others
        "minecraft:horse": ["minecraft:golden_apple", "minecraft:golden_carrot"],
        "minecraft:donkey": ["minecraft:golden_apple", "minecraft:golden_carrot"],
        "minecraft:mule": ["minecraft:golden_apple", "minecraft:golden_carrot"],
        "minecraft:llama": ["minecraft:hay_block"],
        "minecraft:fox": ["minecraft:sweet_berries", "minecraft:glow_berries"],
        "minecraft:panda": ["minecraft:bamboo"],
        "minecraft:turtle": ["minecraft:seagrass"],
        "minecraft:axolotl": ["minecraft:bucket_of_tropical_fish"],
        "minecraft:frog": ["minecraft:slimeball"],
        "minecraft:goat": ["minecraft:wheat"],
        "minecraft:camel": ["minecraft:cactus"],
        "minecraft:sniffer": ["minecraft:torchflower_seeds"],
        "minecraft:armadillo": ["minecraft:spider_eye"],
    }

    # Taming items for tamable animals
    TAMING_ITEMS = {
        "minecraft:wolf": ["minecraft:bone"],
        "minecraft:cat": ["minecraft:cod", "minecraft:salmon"],
        "minecraft:parrot": [
            "minecraft:wheat_seeds",
            "minecraft:melon_seeds",
            "minecraft:pumpkin_seeds",
            "minecraft:beetroot_seeds",
        ],
        "minecraft:horse": [
            "minecraft:wheat",
            "minecraft:sugar",
            "minecraft:apple",
            "minecraft:golden_apple",
            "minecraft:golden_carrot",
        ],
        "minecraft:donkey": [
            "minecraft:wheat",
            "minecraft:sugar",
            "minecraft:apple",
            "minecraft:golden_apple",
            "minecraft:golden_carrot",
        ],
        "minecraft:mule": [
            "minecraft:wheat",
            "minecraft:sugar",
            "minecraft:apple",
            "minecraft:golden_apple",
            "minecraft:golden_carrot",
        ],
        "minecraft:llama": ["minecraft:wheat", "minecraft:hay_block"],
    }

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

    def can_breed(self, entity: "Entity") -> BreedableStatus:
        """
        Check if an entity can breed.

        Args:
            entity: Entity to check

        Returns:
            BreedableStatus indicating breeding capability
        """
        # Check if entity is dead
        if entity.is_dead:
            return BreedableStatus.NOT_BREEDABLE

        # Check if entity is in love mode
        if hasattr(entity, "in_love") and entity.in_love:
            return BreedableStatus.IN_LOVE

        # Check if entity is too young
        if hasattr(entity, "age") and entity.age < 0:
            return BreedableStatus.TOO_YOUNG

        # Check if entity type is breedable
        if not hasattr(entity, "mob_type"):
            return BreedableStatus.NOT_BREEDABLE

        entity_type_name = self._get_entity_type_name(entity)
        if entity_type_name not in self.BREEDING_ITEMS:
            return BreedableStatus.NOT_BREEDABLE

        # Check if holding correct breeding item
        held_item = self.protocol.held_item
        if held_item is None or held_item.is_empty:
            return BreedableStatus.WRONG_ITEM

        required_items = self.BREEDING_ITEMS[entity_type_name]
        if held_item.name not in required_items:
            return BreedableStatus.WRONG_ITEM

        return BreedableStatus.CAN_BREED

    async def breed(self, entity: "Entity") -> bool:
        """
        Breed an entity by feeding it.

        Args:
            entity: Entity to breed

        Returns:
            True if breeding initiated, False if failed

        Raises:
            RuntimeError: If entity cannot breed
        """
        status = self.can_breed(entity)

        if status != BreedableStatus.CAN_BREED:
            status_messages = {
                BreedableStatus.IN_LOVE: "Entity is already in love mode",
                BreedableStatus.TOO_YOUNG: "Entity is too young to breed",
                BreedableStatus.WRONG_ITEM: "Wrong breeding item in hand",
                BreedableStatus.NOT_BREEDABLE: "Entity cannot be bred",
            }
            raise RuntimeError(status_messages.get(status, "Unknown breeding status"))

        # Feed the entity (interact)
        success = await self.protocol.interact(entity, hand=0, swing_hand=True)

        if success:
            print(f"[BREED] Fed {entity} with {self.protocol.held_item.name}")
            self.protocol.emit("entity_breed", entity)

        return success

    def can_tame(self, entity: "Entity") -> TamableStatus:
        """
        Check if an entity can be tamed.

        Args:
            entity: Entity to check

        Returns:
            TamableStatus indicating taming capability
        """
        # Check if entity is dead
        if entity.is_dead:
            return TamableStatus.NOT_TAMABLE

        # Check if already tamed
        if hasattr(entity, "is_tamed") and entity.is_tamed:
            return TamableStatus.ALREADY_TAMED

        # Check if entity type is tamable
        if not hasattr(entity, "mob_type"):
            return TamableStatus.NOT_TAMABLE

        entity_type_name = self._get_entity_type_name(entity)
        if entity_type_name not in self.TAMING_ITEMS:
            return TamableStatus.NOT_TAMABLE

        # Check if holding correct taming item
        held_item = self.protocol.held_item
        if held_item is None or held_item.is_empty:
            return TamableStatus.WRONG_ITEM

        required_items = self.TAMING_ITEMS[entity_type_name]
        if held_item.name not in required_items:
            return TamableStatus.WRONG_ITEM

        return TamableStatus.CAN_TAME

    async def tame(self, entity: "Entity") -> bool:
        """
        Tame an entity by feeding it.

        Note: Taming is a process that may require multiple interactions.
        Wolves show hearts when taming succeeds.

        Args:
            entity: Entity to tame

        Returns:
            True if taming attempted, False if failed

        Raises:
            RuntimeError: If entity cannot be tamed
        """
        status = self.can_tame(entity)

        if status != TamableStatus.CAN_TAME:
            status_messages = {
                TamableStatus.ALREADY_TAMED: "Entity is already tamed",
                TamableStatus.WRONG_ITEM: "Wrong taming item in hand",
                TamableStatus.NOT_TAMABLE: "Entity cannot be tamed",
            }
            raise RuntimeError(status_messages.get(status, "Unknown taming status"))

        # Feed the entity (interact)
        success = await self.protocol.interact(entity, hand=0, swing_hand=True)

        if success:
            print(f"[TAME] Attempted to tame {entity} with {self.protocol.held_item.name}")
            self.protocol.emit("entity_tame", entity)

        return success

    def get_breeding_items(self, entity: "Entity") -> list[str]:
        """
        Get list of items that can breed this entity.

        Args:
            entity: Entity to check

        Returns:
            List of item names (e.g., ["minecraft:wheat"])
        """
        entity_type_name = self._get_entity_type_name(entity)
        return self.BREEDING_ITEMS.get(entity_type_name, [])

    def get_taming_items(self, entity: "Entity") -> list[str]:
        """
        Get list of items that can tame this entity.

        Args:
            entity: Entity to check

        Returns:
            List of item names (e.g., ["minecraft:bone"])
        """
        entity_type_name = self._get_entity_type_name(entity)
        return self.TAMING_ITEMS.get(entity_type_name, [])

    def _get_entity_type_name(self, entity: "Entity") -> str:
        """
        Get entity type name for breeding/taming lookups.

        This uses mob_type if available, otherwise falls back to entity_name.
        """
        if hasattr(entity, "entity_name") and entity.entity_name:
            return entity.entity_name

        if hasattr(entity, "mob_type"):
            from .entities import MobType

            try:
                # Try to get entity name from MobType
                return entity.mob_type.name.lower().replace("_", "minecraft:")
            except (AttributeError, ValueError):
                pass

        # Fallback: use entity type string
        return str(type(entity).__name__).lower()


__all__ = [
    "EntityInteractionManager",
    "BreedableStatus",
    "TamableStatus",
]
