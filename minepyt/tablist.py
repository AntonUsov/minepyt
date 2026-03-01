"""
Tablist (player list) tracking for Minecraft 1.21.4

This module provides:
- Track player list (TAB list)
- Header and footer text
- Player info updates

Tablist is sent via PlayerInfoUpdate packet (0x40).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


@dataclass
class TabList:
    """
    Represents a player list (TAB list).

    Attributes:
        header: Header text (JSON component)
        footer: Footer text (JSON component)
        players: Dict of player data
    """

    header: str = ""
    footer: str = ""
    players: dict[str, dict] = None

    def __post_init__(self):
        if self.players is None:
            self.players = {}


class TabListManager:
    """
    Manages tablist (player list) tracking.

    This class handles:
    - Tab list header/footer updates
    - Player info updates
    - Player removal from list

    Tablist packets:
    - PlayerInfoRemove (0x3F): Remove player
    - PlayerInfoUpdate (0x40): Update player info
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.tablist = TabList()

        # Register for player info packets
        protocol.on("player_info_remove", self._on_player_info_remove)
        protocol.on("player_info_update", self._on_player_info_update)

    @property
    def header(self) -> str:
        """Get tablist header"""
        return self.tablist.header

    @property
    def footer(self) -> str:
        """Get tablist footer"""
        return self.tablist.footer

    @property
    def players(self) -> dict:
        """Get all players"""
        return self.tablist.players

    def get_player(self, uuid: str) -> Optional[dict]:
        """
        Get player by UUID.

        Args:
            uuid: Player UUID

        Returns:
            Player data or None if not found
        """
        return self.players.get(uuid)

    def _on_player_info_remove(self, packet_data: dict) -> None:
        """
        Handle player info remove packet (0x3F).

        Args:
            packet_data: Decoded packet data with UUIDs list
        """
        uuids = packet_data.get("uuids", [])
        for uuid in uuids:
            if uuid in self.players:
                del self.players[uuid]
                print(f"[TABLIST] Removed player: {uuid}")

    def _on_player_info_update(self, packet_data: dict) -> None:
        """
        Handle player info update packet (0x40).

        Args:
            packet_data: Decoded packet data with action field
        """
        action = packet_data.get("action")

        # For 1.20.3+, use JSON components for header/footer
        if action == 3:  # Add player
            self._add_player(packet_data)
        elif action == 4:  # Update gamemode
            self._update_gamemode(packet_data)
        elif action == 5:  # Update latency
            self._update_latency(packet_data)
        elif action == 6:  # Update display name
            self._update_display_name(packet_data)

    def _add_player(self, data: dict) -> None:
        """Add or update player info"""
        uuid = data.get("uuid")
        if uuid is None:
            return

        player_info = self.players.get(uuid, {})

        # Update fields
        if "name" in data:
            player_info["name"] = data["name"]
        if "properties" in data:
            player_info["properties"] = data["properties"]
        if "gamemode" in data:
            player_info["gamemode"] = data["gamemode"]
        if "ping" in data:
            player_info["ping"] = data["ping"]
        if "displayName" in data:
            player_info["displayName"] = data["displayName"]

        self.players[uuid] = player_info

    def _update_gamemode(self, data: dict) -> None:
        """Update player gamemode"""
        uuid = data.get("uuid")
        if uuid and uuid in self.players:
            self.players[uuid]["gamemode"] = data.get("gamemode")

    def _update_latency(self, data: dict) -> None:
        """Update player latency (ping)"""
        uuid = data.get("uuid")
        if uuid and uuid in self.players:
            self.players[uuid]["ping"] = data.get("ping")

    def _update_display_name(self, data: dict) -> None:
        """Update player display name"""
        uuid = data.get("uuid")
        if uuid and uuid in self.players:
            self.players[uuid]["displayName"] = data.get("displayName")

    def _set_header(self, header: str) -> None:
        """
        Set tablist header.

        Args:
            header: Header text (JSON component or plain text)
        """
        self.tablist.header = self._parse_text(header)
        print(f"[TABLIST] Header updated")

    def _set_footer(self, footer: str) -> None:
        """
        Set tablist footer.

        Args:
            footer: Footer text (JSON component or plain text)
        """
        self.tablist.footer = self._parse_text(footer)
        print(f"[TABLIST] Footer updated")

    def _parse_text(self, text: str) -> str:
        """
        Parse text component to string.

        Args:
            text: JSON component or plain text

        Returns:
            Parsed string
        """
        if not text:
            return ""

        try:
            # Try parsing as JSON
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                # Extract text from JSON component
                if "text" in parsed:
                    return parsed["text"]
                # Handle translations
                elif "translate" in parsed:
                    return parsed["translate"]
            return str(parsed)
        except (json.JSONDecodeError, TypeError):
            # Use plain text
            return text


__all__ = [
    "TabListManager",
    "TabList",
]
