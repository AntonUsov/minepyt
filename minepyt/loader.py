"""
Bot loader - creates and configures Minecraft bots
Port of mineflayer/lib/loader.js

This module provides the high-level Bot API that wraps
the low-level MinecraftProtocol implementation.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List

from .protocol import MinecraftProtocol, create_bot as protocol_create_bot
from .version import LATEST_SUPPORTED_VERSION, OLDEST_SUPPORTED_VERSION, __version__
from .plugin_loader import PluginLoader

logger = logging.getLogger("minepyt")


class Bot:
    """
    Main bot class - wraps Minecraft connection and provides high-level API

    This class provides a mineflayer-compatible API while using
    the modular MinecraftProtocol implementation internally.
    """

    def __init__(self, options: Dict[str, Any] = None):
        options = options or {}

        # Default options
        self.username = options.get("username", "Player")
        self.password = options.get("password")
        self.host = options.get("host", "localhost")
        self.port = options.get("port", 25565)
        self.version = options.get("version", False)  # False = auto-detect
        self.auth = options.get("auth", "offline")  # 'offline' or 'microsoft'
        self.hide_errors = options.get("hideErrors", False)
        self.log_errors = options.get("logErrors", True)
        self.brand = options.get("brand", "vanilla")
        self.respawn = options.get("respawn", True)

        # Internal state
        self._protocol: Optional[MinecraftProtocol] = None
        self._connected = False
        self._spawned = False
        self._plugins_loaded = False

        # Event handlers (simple dict-based event system)
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Bot state (proxied from protocol)
        self.game: Dict[str, Any] = {}
        self.health = 20
        self.food = 20
        self.food_saturation = 5.0
        self.is_alive = True
        self.position = None
        self.entity = None
        self.players: Dict[str, Any] = {}
        self.entities: Dict[int, Any] = {}
        self.uuid_to_username: Dict[str, str] = {}

        # Plugin system
        self._plugin_loader = PluginLoader(self, options)

        # Setup logging
        if not self.hide_errors:
            logging.basicConfig(level=logging.INFO)

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def once(self, event: str, handler: Callable) -> None:
        """Register a one-time event handler"""

        def wrapper(*args, **kwargs):
            self.remove_handler(event, wrapper)
            return handler(*args, **kwargs)

        self.on(event, wrapper)

    def remove_handler(self, event: str, handler: Callable) -> None:
        """Remove an event handler"""
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event][:]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    if self.log_errors and not self.hide_errors:
                        logger.error(f"Error in event handler for '{event}': {e}")

    def load_plugin(self, plugin: Callable) -> None:
        """Load a single plugin"""
        self._plugin_loader.load_plugin(plugin)

    def load_plugins(self, plugins: List[Callable]) -> None:
        """Load multiple plugins"""
        self._plugin_loader.load_plugins(plugins)

    def has_plugin(self, plugin: Callable) -> bool:
        """Check if a plugin is loaded"""
        return self._plugin_loader.has_plugin(plugin)

    def chat(self, message: str) -> None:
        """Send a chat message"""
        if self._protocol and self._connected:
            asyncio.create_task(self._protocol.chat(message))

    def end(self, reason: str = None) -> None:
        """Disconnect from the server"""
        if self._protocol:
            asyncio.create_task(self._protocol.disconnect())
            self._connected = False
            self.emit("end", reason)

    def quit(self, reason: str = "disconnect.quitting") -> None:
        """Gracefully quit the server"""
        self.end(reason)

    async def connect(self) -> None:
        """Connect to the Minecraft server"""
        # Create protocol instance
        self._protocol = MinecraftProtocol(host=self.host, port=self.port, username=self.username)

        # Set up event forwarding
        self._setup_event_forwarding()

        # Connect
        await self._protocol.connect()
        self._connected = True

    def _setup_event_forwarding(self) -> None:
        """Forward protocol events to Bot events"""
        if not self._protocol:
            return

        # Forward spawn event
        def on_spawn():
            self._spawned = True
            self.position = self._protocol.position
            self.entity = self._protocol.entity
            self.emit("spawn")

        self._protocol.on("spawn", on_spawn)

        # Forward health event
        def on_health():
            self.health = self._protocol.health
            self.food = self._protocol.food
            self.food_saturation = self._protocol.food_saturation
            self.is_alive = self._protocol.is_alive
            self.emit("health")

        self._protocol.on("health", on_health)

        # Forward chat event
        def on_chat(text, json_data, overlay):
            self.emit("chat", text)

        self._protocol.on("chat", on_chat)

        # Forward game event
        def on_game():
            self.game = {
                "game_mode": self._protocol.game.game_mode,
                "dimension": self._protocol.game.dimension,
                "difficulty": self._protocol.game.difficulty,
                "hardcore": self._protocol.game.hardcore,
            }
            self.emit("game")

        self._protocol.on("game", on_game)

        # Forward death event
        def on_death():
            self.is_alive = False
            self.emit("death")

        self._protocol.on("death", on_death)

        # Forward kicked event
        def on_kicked(reason):
            self._connected = False
            self.emit("kicked", reason)

        self._protocol.on("kicked", on_kicked)

        # Forward end event
        def on_end():
            self._connected = False
            self.emit("end")

        self._protocol.on("end", on_end)

        # Forward error event
        def on_error(error):
            self.emit("error", error)

        self._protocol.on("error", on_error)

        # Forward entity events
        def on_entity_spawn(entity):
            self.entities[entity.entity_id] = entity
            self.emit("entity_spawn", entity)

        self._protocol.on("entity_spawn", on_entity_spawn)

        def on_entity_gone(entity):
            if entity.entity_id in self.entities:
                del self.entities[entity.entity_id]
            self.emit("entity_gone", entity)

        self._protocol.on("entity_gone", on_entity_gone)

        # Forward block update event
        def on_block_update(block):
            self.emit("block_update", block)

        self._protocol.on("block_update", on_block_update)

        # Forward chunk loaded event
        def on_chunk_loaded(x, z):
            self.emit("chunk_loaded", x, z)

        self._protocol.on("chunk_loaded", on_chunk_loaded)

    async def wait_for_spawn(self, timeout: float = 30.0) -> bool:
        """Wait for the bot to spawn in the world"""
        future = asyncio.Future()

        def on_spawn():
            if not future.done():
                future.set_result(True)

        self.once("spawn", on_spawn)

        try:
            await asyncio.wait_for(future, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    # === Convenience methods that delegate to protocol ===

    async def dig(self, x: int, y: int, z: int, face: int = 1) -> bool:
        """Dig a block at the specified position"""
        if self._protocol:
            return await self._protocol.dig(x, y, z, face)
        return False

    async def attack(self, entity, swing_hand: bool = True) -> bool:
        """Attack an entity"""
        if self._protocol:
            return await self._protocol.attack(entity, swing_hand)
        return False

    async def interact(self, entity, hand: int = 0, swing_hand: bool = True) -> bool:
        """Interact with an entity"""
        if self._protocol:
            return await self._protocol.interact(entity, hand, swing_hand)
        return False

    def block_at(self, x: int, y: int, z: int):
        """Get block at position"""
        if self._protocol:
            return self._protocol.block_at(x, y, z)
        return None

    def find_block(self, block_type: str, max_distance: float = 16.0):
        """Find nearest block of type"""
        if self._protocol:
            return self._protocol.findBlock(block_type, {"max_distance": max_distance})
        return None

    def nearest_entity(self, entity_type: str = None, max_distance: float = 16.0):
        """Find nearest entity"""
        if self._protocol:
            return self._protocol.nearest_entity(entity_type, max_distance)
        return None

    def nearest_hostile(self, max_distance: float = 16.0):
        """Find nearest hostile mob"""
        if self._protocol:
            return self._protocol.nearest_hostile(max_distance)
        return None

    def nearest_player(self, max_distance: float = 16.0):
        """Find nearest player"""
        if self._protocol:
            return self._protocol.nearest_player(max_distance)
        return None

    async def look_at(self, x: float, y: float, z: float) -> None:
        """Look at a position"""
        if self._protocol:
            await self._protocol.look_at(x, y, z)

    async def stay_alive(self, duration: float = 120.0) -> float:
        """Stay connected for specified duration"""
        if self._protocol:
            return await self._protocol.stay_alive(duration)
        return 0.0


def create_bot(options: Dict[str, Any] = None) -> Bot:
    """
    Create a new Minecraft bot

    Args:
        options: Dictionary of bot options
            - username: Bot username (default: 'Player')
            - password: Password for online mode
            - host: Server host (default: 'localhost')
            - port: Server port (default: 25565)
            - version: Minecraft version (default: auto-detect)
            - auth: 'offline' or 'microsoft' (default: 'offline')
            - hideErrors: Hide error messages (default: False)
            - logErrors: Log errors (default: True)
            - brand: Client brand (default: 'vanilla')
            - respawn: Auto-respawn on death (default: True)

    Returns:
        Bot instance (not yet connected - call await bot.connect())
    """
    bot = Bot(options)
    return bot


async def create_and_connect(options: Dict[str, Any] = None) -> Bot:
    """
    Create and connect a bot in one step.

    This is the recommended way to create a bot for most use cases.

    Args:
        options: Same as create_bot

    Returns:
        Connected Bot instance
    """
    bot = Bot(options)
    await bot.connect()
    return bot
