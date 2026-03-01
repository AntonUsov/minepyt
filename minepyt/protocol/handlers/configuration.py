"""
Configuration state packet handlers for Minecraft 1.21.4
"""

from typing import TYPE_CHECKING

from mcproto.buffer import Buffer
from mcproto.protocol.base_io import StructFormat

if TYPE_CHECKING:
    from ..connection import MinecraftProtocol


class ConfigurationHandler:
    """Handler for configuration state packets (clientbound)"""

    async def handle_configuration_packet(
        self: "MinecraftProtocol", packet_id: int, buf: Buffer
    ) -> None:
        """Handle configuration state packets"""
        if packet_id == 0x00:  # Cookie Request
            await self._handle_cookie_request(buf)

        elif packet_id == 0x02:  # Disconnect
            reason = buf.read_utf()
            print(f"Disconnected during configuration: {reason}")
            self.emit("kicked", reason)
            self._running = False

        elif packet_id == 0x03:  # Finish Configuration
            print("Configuration: Finish Configuration received!")
            await self.send_acknowledge_finish_configuration()

        elif packet_id == 0x04:  # Keep Alive (config)
            await self._handle_config_keep_alive(buf)

        elif packet_id == 0x05:  # Ping
            await self._handle_config_ping(buf)

        elif packet_id == 0x07:  # Registry Data
            print("Configuration: Registry Data received")

        elif packet_id == 0x0C:  # Feature Flags
            print("Configuration: Feature Flags received")

        elif packet_id == 0x0D:  # Update Tags
            print("Configuration: Update Tags received")

        elif packet_id == 0x0E:  # Clientbound Known Packs
            print("Configuration: Known Packs received")
            await self.send_known_packs()

        else:
            print(f"Configuration packet: ID=0x{packet_id:02X}, remaining={buf.remaining} bytes")

    async def _handle_cookie_request(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Cookie Request packet (0x00)"""
        print("Configuration: Cookie Request")
        key = buf.read_utf()
        # Send Cookie Response (0x01) - has_cookie = False, no data
        resp_buf = Buffer()
        resp_buf.write_utf(key)
        resp_buf.write_value(StructFormat.BOOL, False)
        await self._write_packet(0x01, bytes(resp_buf))
        print(f"Configuration: Cookie Response sent for {key}")

    async def _handle_config_keep_alive(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Keep Alive packet in configuration state (0x04)"""
        keep_alive_id = buf.read_value(StructFormat.LONGLONG)
        # Respond with serverbound keep alive (0x04 in config)
        resp_buf = Buffer()
        resp_buf.write_value(StructFormat.LONGLONG, keep_alive_id)
        await self._write_packet(0x04, bytes(resp_buf))
        print("Configuration: Keep Alive responded")

    async def _handle_config_ping(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Ping packet in configuration state (0x05)"""
        ping_id = buf.read_value(StructFormat.INT)
        # Respond with pong (0x05 in config)
        resp_buf = Buffer()
        resp_buf.write_value(StructFormat.INT, ping_id)
        await self._write_packet(0x05, bytes(resp_buf))
        print("Configuration: Pong sent")


__all__ = ["ConfigurationHandler"]
