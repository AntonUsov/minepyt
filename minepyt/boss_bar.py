"""
Boss bar tracking for Minecraft 1.21.4

This module provides:
- Track boss bars (Wither, Ender Dragon, custom boss bars)
- Boss bar events (created, updated, deleted)
- Boss bar properties (title, health, color, style, flags)

Boss bars are sent via packet 0x0D in play state.
"""

from __future__ import annotations

import uuid as uuid_lib
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class BossBarColor(IntEnum):
    """Boss bar color options"""

    PINK = 0
    BLUE = 1
    RED = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    WHITE = 6


class BossBarStyle(IntEnum):
    """Boss bar style/division options"""

    NOTCHED_6 = 0  # 6 notches (like Ender Dragon)
    NOTCHED_10 = 1  # 10 notches
    NOTCHED_12 = 2  # 12 notches
    NOTCHED_20 = 3  # 20 notches
    PROGRESS = 4  # No notches, solid bar
    NOTCHED_6_NO_BG = 5  # 6 notches, no background


class BossBarFlag(IntEnum):
    """Boss bar rendering flags"""

    DARKEN_SKY = 0x01  # Darken sky behind boss bar
    DRAGON_BAR = 0x02  # Use dragon boss bar music/fog
    CREATE_FOG = 0x04  # Create boss fog


@dataclass
class BossBar:
    """
    Represents a boss bar.

    Attributes:
        uuid: Unique identifier for this boss bar
        title: Boss bar title (JSON text component)
        health: Current health (0.0 to 1.0)
        color: BossBarColor enum value
        style: BossBarStyle enum value
        flags: Bitmask of BossBarFlag values
        entity_uuid: Optional entity UUID to track (for mob tracking)
    """

    uuid: uuid_lib.UUID
    title: str
    health: float = 1.0
    color: BossBarColor = BossBarColor.PINK
    style: BossBarStyle = BossBarStyle.PROGRESS
    flags: int = 0
    entity_uuid: Optional[uuid_lib.UUID] = None

    @property
    def darken_sky(self) -> bool:
        """Check if sky should be darkened"""
        return bool(self.flags & BossBarFlag.DARKEN_SKY)

    @property
    def dragon_bar(self) -> bool:
        """Check if should use dragon bar effects"""
        return bool(self.flags & BossBarFlag.DRAGON_BAR)

    @property
    def create_fog(self) -> bool:
        """Check if should create boss fog"""
        return bool(self.flags & BossBarFlag.CREATE_FOG)

    def set_darken_sky(self, value: bool) -> None:
        """Set darken sky flag"""
        if value:
            self.flags |= BossBarFlag.DARKEN_SKY
        else:
            self.flags &= ~BossBarFlag.DARKEN_SKY

    def set_dragon_bar(self, value: bool) -> None:
        """Set dragon bar flag"""
        if value:
            self.flags |= BossBarFlag.DRAGON_BAR
        else:
            self.flags &= ~BossBarFlag.DRAGON_BAR

    def set_create_fog(self, value: bool) -> None:
        """Set create fog flag"""
        if value:
            self.flags |= BossBarFlag.CREATE_FOG
        else:
            self.flags &= ~BossBarFlag.CREATE_FOG


class BossBarManager:
    """
    Manages boss bar tracking.

    This class handles:
    - Boss bar creation updates
    - Boss bar removal
    - Boss bar property updates

    Boss bars are tracked via the 'boss' packet (0x0D).
    """

    BOSS_PACKET_ID = 0x0D

    # Boss bar action types
    ACTION_ADD = 0
    ACTION_REMOVE = 1
    ACTION_UPDATE_HEALTH = 2
    ACTION_UPDATE_TITLE = 3
    ACTION_UPDATE_STYLE = 4
    ACTION_UPDATE_PROPERTIES = 5

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.boss_bars: dict[uuid_lib.UUID, BossBar] = {}

        # Register for boss bar packet
        protocol.on("boss", self._on_boss_packet)

    def get_boss_bar(self, uuid: uuid_lib.UUID) -> Optional[BossBar]:
        """
        Get boss bar by UUID.

        Args:
            uuid: Boss bar UUID

        Returns:
            BossBar or None if not found
        """
        return self.boss_bars.get(uuid)

    def get_all_boss_bars(self) -> list[BossBar]:
        """
        Get all active boss bars.

        Returns:
            List of all BossBar objects
        """
        return list(self.boss_bars.values())

    def _on_boss_packet(self, packet_data: dict) -> None:
        """
        Handle boss bar packet from server.

        Args:
            packet_data: Decoded packet data
        """
        action = packet_data.get("action")
        uuid = packet_data.get("uuid")

        if uuid is None:
            return

        try:
            # Parse UUID from bytes/string
            if isinstance(uuid, str):
                uuid = uuid_lib.UUID(uuid)
            elif isinstance(uuid, bytes):
                uuid = uuid_lib.UUID(bytes=uuid)
        except (ValueError, TypeError):
            print(f"[BOSS_BAR] Invalid UUID: {uuid}")
            return

        if action == self.ACTION_ADD:
            self._add_boss_bar(uuid, packet_data)
        elif action == self.ACTION_REMOVE:
            self._remove_boss_bar(uuid)
        elif action == self.ACTION_UPDATE_HEALTH:
            self._update_health(uuid, packet_data)
        elif action == self.ACTION_UPDATE_TITLE:
            self._update_title(uuid, packet_data)
        elif action == self.ACTION_UPDATE_STYLE:
            self._update_style(uuid, packet_data)
        elif action == self.ACTION_UPDATE_PROPERTIES:
            self._update_properties(uuid, packet_data)
        else:
            print(f"[BOSS_BAR] Unknown action: {action}")

    def _add_boss_bar(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Add new boss bar"""
        if uuid in self.boss_bars:
            # Update existing
            self._update_boss_bar(uuid, data)
            return

        boss_bar = BossBar(
            uuid=uuid,
            title=data.get("title", ""),
            health=data.get("health", 1.0),
            color=data.get("color", BossBarColor.PINK),
            style=data.get("style", BossBarStyle.PROGRESS),
            flags=data.get("flags", 0),
            entity_uuid=data.get("entity_uuid"),
        )

        self.boss_bars[uuid] = boss_bar
        print(f"[BOSS_BAR] Created boss bar: {boss_bar.title}")
        self.protocol.emit("boss_bar_created", boss_bar)

    def _remove_boss_bar(self, uuid: uuid_lib.UUID) -> None:
        """Remove boss bar"""
        if uuid in self.boss_bars:
            boss_bar = self.boss_bars.pop(uuid)
            print(f"[BOSS_BAR] Removed boss bar: {boss_bar.title}")
            self.protocol.emit("boss_bar_deleted", boss_bar)

    def _update_health(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Update boss bar health"""
        if uuid in self.boss_bars:
            boss_bar = self.boss_bars[uuid]
            boss_bar.health = data.get("health", boss_bar.health)
            self.protocol.emit("boss_bar_updated", boss_bar)

    def _update_title(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Update boss bar title"""
        if uuid in self.boss_bars:
            boss_bar = self.boss_bars[uuid]
            boss_bar.title = data.get("title", boss_bar.title)
            self.protocol.emit("boss_bar_updated", boss_bar)

    def _update_style(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Update boss bar style"""
        if uuid in self.boss_bars:
            boss_bar = self.boss_bars[uuid]
            boss_bar.color = data.get("color", boss_bar.color)
            boss_bar.style = data.get("style", boss_bar.style)
            self.protocol.emit("boss_bar_updated", boss_bar)

    def _update_properties(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Update boss bar properties (health, color, style, flags)"""
        if uuid in self.boss_bars:
            self._update_boss_bar(uuid, data)
            self.protocol.emit("boss_bar_updated", self.boss_bars[uuid])

    def _update_boss_bar(self, uuid: uuid_lib.UUID, data: dict) -> None:
        """Update boss bar with all properties"""
        boss_bar = self.boss_bars[uuid]

        if "health" in data:
            boss_bar.health = data["health"]
        if "title" in data:
            boss_bar.title = data["title"]
        if "color" in data:
            boss_bar.color = data["color"]
        if "style" in data:
            boss_bar.style = data["style"]
        if "flags" in data:
            boss_bar.flags = data["flags"]
        if "entity_uuid" in data:
            boss_bar.entity_uuid = data["entity_uuid"]


__all__ = [
    "BossBarManager",
    "BossBar",
    "BossBarColor",
    "BossBarStyle",
    "BossBarFlag",
]
