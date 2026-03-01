"""
Protocol states for Minecraft 1.21.4
"""

from enum import IntEnum


class ProtocolState(IntEnum):
    """Minecraft protocol states"""

    HANDSHAKING = 0
    STATUS = 1
    LOGIN = 2
    CONFIGURATION = 3  # Added in 1.20.2
    PLAY = 4


__all__ = ["ProtocolState"]
