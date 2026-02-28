"""
Blocks plugin - handles chunk loading and block access
Port of mineflayer/lib/plugins/blocks.js

This plugin provides a mineflayer-compatible interface for block access.
The actual chunk/world implementation is in chunk_utils.py and protocol.py.
"""

from __future__ import annotations

from typing import Dict, Any

# Import from core implementations
from ...chunk_utils import World
# Note: Block and get_block_name are used in protocol.py


def blocks_plugin(bot, options: Dict[str, Any] = None) -> None:
    """
    Blocks plugin - injects block/chunk handling into bot

    Adds to bot:
        bot.world - World instance with all loaded chunks
        bot.blockAt(pos) - Get block at position

    Events emitted:
        'chunk_loaded' - when a chunk is loaded
        'chunk_unloaded' - when a chunk is unloaded
        'block_update' - when a block changes

    Note: The actual chunk parsing and world management is handled by
    protocol.py. This plugin provides the mineflayer-compatible interface.
    """
    options = options or {}

    # The world is already initialized in protocol.py
    # This plugin just provides the blockAt alias if needed

    if not hasattr(bot, "world"):
        # Initialize world if not already done
        min_y = bot.game.min_y if hasattr(bot, "game") else -64
        height = bot.game.height if hasattr(bot, "game") else 384
        bot.world = World(min_y=min_y, height=height)

    # Provide blockAt as alias for block_at if not present
    if not hasattr(bot, "blockAt"):
        bot.blockAt = bot.block_at

    print("[PLUGIN] Blocks plugin loaded")
