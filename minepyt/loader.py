"""
Bot loader - creates and configures Minecraft bots
Port of mineflayer/lib/loader.js
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from enum import Enum

# We'll use pyCraft for the Minecraft protocol implementation
try:
    from minecraft import authentication
    from minecraft.connection import Connection
    from minecraft.networking.packets import clientbound, serverbound
except ImportError:
    # pyCraft not installed yet, we'll handle this
    Connection = None
    authentication = None

from .version import LATEST_SUPPORTED_VERSION, OLDEST_SUPPORTED_VERSION, __version__
from .plugin_loader import PluginLoader

logger = logging.getLogger("minepyt")


class Bot:
    """
    Main bot class - wraps Minecraft connection and provides high-level API
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
        self._client = None
        self._connected = False
        self._spawned = False
        self._plugins_loaded = False

        # Event handlers (simple dict-based event system)
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Bot state
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
            for handler in self._event_handlers[event][
                :
            ]:  # Copy to allow removal during iteration
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
        if self._client and self._connected:
            # Will be implemented with actual packet sending
            pass

    def end(self, reason: str = None) -> None:
        """Disconnect from the server"""
        if self._client:
            self._connected = False
            self.emit("end", reason)

    def quit(self, reason: str = "disconnect.quitting") -> None:
        """Gracefully quit the server"""
        self.end(reason)

    async def connect(self) -> None:
        """Connect to the Minecraft server"""
        # This will be implemented with pyCraft
        raise NotImplementedError("Connection requires pyCraft installation")

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
        Bot instance
    """
    bot = Bot(options)
    return bot
