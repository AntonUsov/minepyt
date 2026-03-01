"""
Resource pack tracking for Minecraft 1.21.4

This module provides:
- Track resource pack status
- Resource pack download progress
- Resource pack events

Resource packs are sent via ResourcePack (0x66) packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class ResourcePackStatus(IntEnum):
    """Resource pack status"""

    SUCCESSFULLY_LOADED = 0
    DECLINED = 1
    FAILED_DOWNLOAD = 2
    ACCEPTED = 3


class TexturePackResult(IntEnum):
    """Texture pack handling result"""

    SUCCESSFULLY_LOADED = 3
    DECLINED = 4
    FAILED_DOWNLOAD = 5
    ACCEPTED = 6


@dataclass
class ResourcePack:
    """
    Represents a resource pack.

    Attributes:
        id: Resource pack ID (UUID)
        url: Download URL
        hash: Resource pack hash
        status: Current download/apply status
    """

    id: str = ""
    url: str = ""
    hash: str = ""
    status: ResourcePackStatus = ResourcePackStatus.SUCCESSFULLY_LOADED


class ResourcePackManager:
    """
    Manages resource pack tracking.

    This class handles:
    - Resource pack status tracking
    - Download progress
    - Accept/decline resource packs

    Resource packs are tracked via:
    - ResourcePackSend (0x66): Server sends resource pack
    - ResourcePack (0x67): Client accepts/declines
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.current_pack: Optional[ResourcePack] = None

        # Register for resource pack events
        protocol.on("resource_pack_send", self._on_resource_pack_send)
        protocol.on("resource_pack", self._on_resource_pack)

    @property
    def resource_pack(self) -> Optional[ResourcePack]:
        """Get current resource pack"""
        return self.current_pack

    def _on_resource_pack_send(self, pack_data: dict) -> None:
        """
        Handle resource pack send from server.

        Args:
            pack_data: Resource pack data with id, url, hash
        """
        pack = ResourcePack(
            id=pack_data.get("id", ""),
            url=pack_data.get("url", ""),
            hash=pack_data.get("hash", ""),
            status=ResourcePackStatus.FAILED_DOWNLOAD,
        )

        print(f"[RESOURCE_PACK] Server sent resource pack: {pack.id}")
        print(f"[RESOURCE_PACK] URL: {pack.url}")
        self.current_pack = pack

        self.protocol.emit("resource_pack_send", pack)

    async def accept_resource_pack(self) -> None:
        """
        Accept the resource pack.

        This sends a resource pack packet with success status.
        """
        if not self.current_pack:
            print("[RESOURCE_PACK] No resource pack to accept")
            return

        # Send acceptance packet
        from mcproto.buffer import Buffer

        buf = Buffer()
        # Write resource pack ID
        buf.write_varint(int.from_bytes(self.current_pack.id.replace("-", ""), 16))

        await self.protocol._write_packet(0x67, bytes(buf))

        self.current_pack.status = ResourcePackStatus.ACCEPTED
        print(f"[RESOURCE_PACK] Accepted resource pack: {self.current_pack.id}")
        self.protocol.emit("resource_pack", self.current_pack)

    async def decline_resource_pack(self) -> None:
        """
        Decline the resource pack.

        This sends a resource pack packet with declined status.
        """
        if not self.current_pack:
            print("[RESOURCE_PACK] No resource pack to decline")
            return

        # Send decline packet
        from mcproto.buffer import Buffer

        buf = Buffer()
        # Write resource pack ID
        buf.write_varint(int.from_bytes(self.current_pack.id.replace("-", ""), 16))

        await self.protocol._write_packet(0x67, bytes(buf))

        self.current_pack.status = ResourcePackStatus.DECLINED
        print(f"[RESOURCE_PACK] Declined resource pack: {self.current_pack.id}")
        self.protocol.emit("resource_pack", self.current_pack)

    def _on_resource_pack(self, result: TexturePackResult) -> None:
        """
        Handle resource pack response from server.

        Args:
            result: Server response (accepted, declined, etc.)
        """
        if result == TexturePackResult.SUCCESSFULLY_LOADED:
            self.current_pack.status = ResourcePackStatus.SUCCESSFULLY_LOADED
            print(f"[RESOURCE_PACK] Successfully loaded: {self.current_pack.id}")
        elif result == TexturePackResult.DECLINED:
            self.current_pack.status = ResourcePackStatus.DECLINED
            print(f"[RESOURCE_PACK] Server declined: {self.current_pack.id}")
        elif result == TexturePackResult.FAILED_DOWNLOAD:
            self.current_pack.status = ResourcePackStatus.FAILED_DOWNLOAD
            print(f"[RESOURCE_PACK] Failed to download: {self.current_pack.id}")

        self.protocol.emit("resource_pack_status", result)


__all__ = [
    "ResourcePackManager",
    "ResourcePack",
    "ResourcePackStatus",
    "TexturePackResult",
]
