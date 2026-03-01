"""
Login state packet handlers for Minecraft 1.21.4
"""

from typing import TYPE_CHECKING

from mcproto.buffer import Buffer
from mcproto.protocol.base_io import StructFormat

if TYPE_CHECKING:
    from ..connection import MinecraftProtocol


class LoginHandler:
    """Handler for login state packets (clientbound)"""

    async def handle_login_packet(self: "MinecraftProtocol", packet_id: int, buf: Buffer) -> None:
        """Handle login state packets"""
        if packet_id == 0x00:  # Disconnect
            reason = buf.read_utf()
            print(f"Disconnected during login: {reason}")
            self.emit("kicked", reason)
            self._running = False

        elif packet_id == 0x01:  # Encryption Request
            print("Server requested encryption (online mode)")
            self._running = False

        elif packet_id == 0x02:  # Login Success
            await self._handle_login_success(buf)

        elif packet_id == 0x03:  # Set Compression
            self.compression_threshold = buf.read_varint()
            print(f"Compression enabled, threshold: {self.compression_threshold}")

        else:
            print(f"Unknown login packet: ID=0x{packet_id:02X}")

    async def _handle_login_success(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Login Success packet (0x02)"""
        uuid_bytes = buf.read(16)
        uuid_int = int.from_bytes(uuid_bytes, "big")
        self.uuid = f"{uuid_int:032x}"
        self.uuid = f"{self.uuid[:8]}-{self.uuid[8:12]}-{self.uuid[12:16]}-{self.uuid[16:20]}-{self.uuid[20:]}"

        self.username = buf.read_utf()

        property_count = buf.read_varint()
        for _ in range(property_count):
            buf.read_utf()
            buf.read_utf()
            has_signature = buf.read_value(StructFormat.BOOL)
            if has_signature:
                buf.read_utf()

        print(f"Login successful! UUID: {self.uuid}, Username: {self.username}")
        self.emit("login")

        await self.send_login_acknowledged()
        # Send client information after transitioning to configuration state
        await self.send_client_information()


__all__ = ["LoginHandler"]
