"""
Plugin loader - handles loading and injecting plugins into the bot
Port of mineflayer/lib/plugin_loader.js
"""

from typing import Callable, Dict, Any, List, Optional


class PluginLoader:
    """
    Manages plugin loading and injection for the bot
    """

    def __init__(self, bot, options: Dict[str, Any] = None):
        self.bot = bot
        self.options = options or {}
        self._loaded = False
        self._plugin_list: List[Callable] = []

        # Register for inject_allowed event
        self.bot.once("inject_allowed", self._on_inject_allowed)

    def _on_inject_allowed(self) -> None:
        """Called when bot is ready for plugin injection"""
        self._loaded = True
        self._inject_plugins()

    def load_plugin(self, plugin: Callable) -> None:
        """
        Load a single plugin

        Args:
            plugin: A function that takes (bot, options) as arguments
        """
        if not callable(plugin):
            raise ValueError("Plugin needs to be callable (function)")

        if self.has_plugin(plugin):
            return

        self._plugin_list.append(plugin)

        if self._loaded:
            plugin(self.bot, self.options)

    def load_plugins(self, plugins: List[Callable]) -> None:
        """
        Load multiple plugins

        Args:
            plugins: List of plugin functions
        """
        # Validate all plugins are callable
        for plugin in plugins:
            if not callable(plugin):
                raise ValueError("All plugins need to be callable (functions)")

        for plugin in plugins:
            self.load_plugin(plugin)

    def _inject_plugins(self) -> None:
        """Inject all loaded plugins into the bot"""
        for plugin in self._plugin_list:
            try:
                plugin(self.bot, self.options)
            except Exception as e:
                if not self.options.get("hideErrors", False):
                    print(f"[minepyt] Error loading plugin {plugin.__name__}: {e}")

    def has_plugin(self, plugin: Callable) -> bool:
        """Check if a plugin is already loaded"""
        return plugin in self._plugin_list
