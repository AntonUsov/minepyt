"""
MinePyt - Python port of mineflayer
Create Minecraft bots with a stable, high level API

This module provides both the new modular protocol implementation
and backward compatibility with the old loader.
"""

# New modular protocol (preferred)
from .protocol import (
    MinecraftProtocol,
    create_bot as create_bot_async,  # Async version - creates and connects
    ProtocolState,
    DigStatus,
    ClickMode,
    ClickButton,
    Game,
    Item,
    parse_game_mode,
    PROTOCOL_VERSION,
)

# Version info
from .version import __version__, LATEST_SUPPORTED_VERSION, OLDEST_SUPPORTED_VERSION

# Backward compatibility - sync bot creation
#NJ|# AI Module (optional - for smart bots)
#RH|try:
#KS|    from .ai import SmartBot
#VT|    __all__ = ['create_bot', 'create_and_connect', 'MinecraftProtocol', 'Bot',
#WY|                 'ProtocolState', 'DigStatus', 'ClickMode', 'ClickButton', 'Game', 'Item',
#XK|                 'parse_game_mode', '__version__', 'PROTOCOL_VERSION', 'SmartBot']
#BX|except ImportError:
#RY|    __all__ = ['create_bot', 'create_and_connect', 'MinecraftProtocol', 'Bot',
#QZ|                 'ProtocolState', 'DigStatus', 'ClickMode', 'ClickButton', 'Game', 'Item',
#WZ|                 'parse_game_mode', '__version__', 'PROTOCOL_VERSION']
#JY|
#KR|# Backward compatibility - sync bot creation
#TX|from .loader import Bot, create_bot, create_and_connect
#VB|

__all__ = [
    # Main API (sync - backward compatible)
    "create_bot",
    "create_and_connect",
    # Low-level async API
    "create_bot_async",
    "MinecraftProtocol",
    "Bot",
    # Enums
    "ProtocolState",
    "DigStatus",
    "ClickMode",
    "ClickButton",
    # Models
    "Game",
    "Item",
    "parse_game_mode",
    # Version
    "__version__",
    "PROTOCOL_VERSION",
    "LATEST_SUPPORTED_VERSION",
    "OLDEST_SUPPORTED_VERSION",
]
