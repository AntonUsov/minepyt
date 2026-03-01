"""
Kick events for Minecraft 1.21.4

This module provides:
- Track kick disconnect events
- Disconnect events
- Quit handling

Kicks are sent via KickDisconnect (0x1B) and Disconnect (0x19) packets.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


@dataclass
class KickEvent:
    """
    Represents a kick event.

    Attributes:
        reason: Kick reason text
        is_kick: True (disconnect is a kick)
    """

    reason: str = ""
    is_kick: bool = True


@dataclass
class DisconnectEvent:
    """
    Represents a disconnect event.

    Attributes:
        reason: Disconnect reason text
        is_kick: False (disconnect is not a kick)
    """

    reason: str = ""
    is_kick: bool = False


class KickManager:
    """
    Manages kick and disconnect events.

    This class handles:
    - Kick disconnect tracking
    - Generic disconnect tracking
    - Quit handling

    Packets:
    - KickDisconnect (0x1B): Server kicks player
    - Disconnect (0x19): Generic disconnect
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Register for kick/disconnect events
        protocol.on("kicked", self._on_kicked)
        protocol.on("disconnect", self._on_disconnect)
        protocol.on("end", self._on_end)

    @property
    def is_connected(self) -> bool:
        """Check if bot is connected"""
        return self.protocol.connection is not None and not self.protocol.connection.is_closed()

    async def quit(self, reason: str = "") -> None:
        """
        Quit from server.

        Args:
            reason: Quit reason message
        """
        print(f"[KICK] Quitting: {reason}")

        # Send disconnect packet if still connected
        if self.is_connected:
            from mcproto.buffer import Buffer

            buf = Buffer()
            # Empty disconnect packet
            await self.protocol._write_packet(0x19, bytes(buf))
            await asyncio.sleep(0.5)

        # Close connection
        if self.protocol.connection:
            self.protocol.connection.close()
            print("[KICK] Connection closed")

    def _on_kicked(self, reason: str) -> None:
        """
        Handle kick disconnect event.

        Args:
            reason: Kick reason text
        """
        event = KickEvent(reason=reason, is_kick=True)
        print(f"[KICK] Kicked: {reason}")
        self.protocol.emit("kicked", event)

    def _on_disconnect(self, reason: str) -> None:
        """
        Handle generic disconnect event.

        Args:
            reason: Disconnect reason text
        """
        event = DisconnectEvent(reason=reason, is_kick=False)
        print(f"[KICK] Disconnected: {reason}")
        self.protocol.emit("disconnect", event)

    def _on_end(self) -> None:
        """
        Handle connection end (disconnect or network error).

        Args:
            None (no data)
        """
        print("[KICK] Connection ended")
        # Emit disconnect with generic reason
        self._on_disconnect("Connection ended")


__all__ = [
    "KickManager",
    "KickEvent",
    "DisconnectEvent",
]
