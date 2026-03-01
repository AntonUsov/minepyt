"""
Protocol enums for Minecraft 1.21.4
"""

from enum import IntEnum


class DigStatus(IntEnum):
    """Player digging action status"""

    START_DIGGING = 0
    CANCEL_DIGGING = 1
    FINISH_DIGGING = 2
    DROP_ITEM_STACK = 3
    DROP_ITEM = 4
    RELEASE_USE_ITEM = 5
    SWAP_ITEM_IN_HAND = 6


class ClickMode(IntEnum):
    """Container click modes for 1.21.4"""

    PICKUP = 0  # Click / Pickup (mouse button 0=left, 1=right)
    QUICK_MOVE = 1  # Shift+Click - move item to other inventory
    SWAP = 2  # Swap with hotbar slot (button = hotbar slot 0-8)
    CLONE = 3  # Clone item (middle click, creative only)
    THROW = 4  # Drop item (button 0=one, 1=stack)
    QUICK_CRAFT = 5  # Drag items (painting mode)
    PICKUP_ALL = 6  # Double-click to pickup all of same type


class ClickButton(IntEnum):
    """Mouse buttons for container clicks"""

    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


__all__ = ["DigStatus", "ClickMode", "ClickButton"]
