"""
Packet handler mixins for Minecraft 1.21.4

This module provides modular packet handlers that can be mixed into
the main protocol class. Each handler handles packets for a specific
protocol state.
"""

from .login import LoginHandler
from .configuration import ConfigurationHandler
from .play import PlayHandler

__all__ = ["LoginHandler", "ConfigurationHandler", "PlayHandler"]
