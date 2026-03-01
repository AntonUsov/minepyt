"""
Minecraft protocol implementation for minepyt
Supports protocol version 769 (1.21.4)

This package provides a modular implementation of the Minecraft protocol,
organized into logical components:
- connection: Connection management and packet I/O
- states: Protocol state enumeration
- models: Data models (Game, Item)
- enums: Protocol enums (DigStatus, ClickMode, etc.)
- handlers: Packet handlers for different states
- packets: Packet definitions (clientbound/serverbound)
"""

from .states import ProtocolState
from .enums import DigStatus, ClickMode, ClickButton
from .models import Game, Item, parse_game_mode
from .connection import MinecraftProtocol, create_bot

__all__ = [
    # Enums
    "ProtocolState",
    "DigStatus",
    "ClickMode",
    "ClickButton",
    # Models
    "Game",
    "Item",
    "parse_game_mode",
    # Connection
    "MinecraftProtocol",
    "create_bot",
]

# Protocol version
PROTOCOL_VERSION = 769  # Minecraft 1.21.4
