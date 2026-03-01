"""
Client settings for Minecraft 1.21.4

This module provides:
- Client settings tracking (chat, view distance, hand, etc.)
- Settings modification
- Client-side flags

Client settings are controlled via ClientSettings (0x07) packet.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class ChatSetting(IntEnum):
    """Chat settings"""

    ENABLED = 0
    COMMANDS_ONLY = 1
    HIDDEN = 2


class ViewDistance(IntEnum):
    """View distance settings (chunks)"""

    FAR = 12  # 32 chunks
    NORMAL = 10  # 16 chunks
    SHORT = 8   # 12 chunks
    TINY = 6     # 8 chunks


class MainHand(IntEnum):
    """Main hand preference"""

    LEFT = 0
    RIGHT = 1


@dataclass
class ClientSettings:
    """
    Represents client settings.

    Attributes:
        chat: Chat visibility setting
        view_distance: Render distance in chunks
        main_hand: Left or right hand
        skin_parts: Skin parts (cape, hat, jacket, etc.)
        difficulty: Game difficulty
        is_spectator: Whether in spectator mode
        enable_colors: Enable chat colors
    """

    chat: ChatSetting = ChatSetting.ENABLED
    view_distance: ViewDistance = ViewDistance.NORMAL
    main_hand: MainHand = MainHand.RIGHT
    skin_parts: int = 0x7F  # All parts enabled
    difficulty: int = 2  # Normal
    is_spectator: bool = False
    enable_colors: bool = True


class SettingsManager:
    """
    Manages client settings.

    This class handles:
    - Client settings tracking
    - Settings modification
    - ClientSettings packet sending

    Settings are sent via ClientSettings (0x07) packet.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.settings = ClientSettings()

    @property
    def chat(self) -> ChatSetting:
        """Get chat setting"""
        return self.settings.chat

    @property
    def view_distance(self) -> ViewDistance:
        """Get view distance"""
        return self.settings.view_distance

    async def set_chat(self, setting: ChatSetting) -> None:
        """
        Set chat visibility setting.

        Args:
            setting: Chat setting (enabled, commands_only, hidden)
        """
        self.settings.chat = setting
        await self._send_settings()
        print(f"[SETTINGS] Chat set to: {setting.name}")

    async def set_view_distance(self, distance: ViewDistance) -> None:
        """
        Set view distance.

        Args:
            distance: View distance (chunks to render)
        """
        self.settings.view_distance = distance
        await self._send_settings()
        print(f"[SETTINGS] View distance set to: {distance.name} ({distance.value} chunks)")

    async def set_main_hand(self, hand: MainHand) -> None:
        """
        Set main hand preference.

        Args:
            hand: Left or right hand
        """
        self.settings.main_hand = hand
        await self._send_settings()
        print(f"[SETTINGS] Main hand set to: {hand.name}")

    async def _send_settings(self) -> None:
        """Send ClientSettings packet to server"""
        from mcproto.buffer import Buffer

        buf = Buffer()
        # Language (varint)
        buf.write_varint("en_us")  # English US
        # View distance (byte)
        buf.write_byte(self.settings.view_distance.value)
        # Chat mode (varint)
        buf.write_varint(self.settings.chat.value)
        # Chat colors (bool)
        buf.write_boolean(self.settings.enable_colors)
        # Display skin parts (byte)
        buf.write_byte(self.settings.skin_parts)
        # Main hand (varint)
        buf.write_varint(self.settings.main_hand.value)
        # Enable/disable text filtering (bool)
        buf.write_boolean(False)  # Disable server-side text filtering

        await self.protocol._write_packet(0x07, bytes(buf))
        print("[SETTINGS] Sent client settings to server")


__all__ = [
    "SettingsManager",
    "ClientSettings",
    "ChatSetting",
    "ViewDistance",
    "MainHand",
]
