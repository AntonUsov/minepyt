"""
Chat system for Minecraft 1.21.4

This module provides:
- Send chat messages
- Chat message parsing
- Chat patterns for matching
- Whisper functionality

Port of mineflayer/lib/plugins/chat.js
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


# Chat length limits
CHAT_LENGTH_LIMIT = 256  # 1.21.4


@dataclass
class ChatPattern:
    """A chat pattern for matching messages"""

    name: str
    pattern: re.Pattern
    repeat: bool = True
    parse: bool = False
    deprecated: bool = False


@dataclass
class ChatMessage:
    """Represents a parsed chat message"""

    text: str
    json_data: Dict[str, Any]
    position: int = 0
    sender: Optional[str] = None
    message_type: Optional[str] = None


class ChatManager:
    """
    Manages chat functionality.

    This class handles:
    - Sending chat messages
    - Parsing chat messages
    - Chat pattern matching
    - Whisper functionality
    """

    # Username regex for chat patterns
    USERNAME_REGEX = r"(?:\(.{1,15}\)|\[.{1,15}\]|.){0,5}?(\w+)"
    CHAT_REGEX = re.compile(f"^{USERNAME_REGEX}\\s?[>:\\-»\\]\\)~]+\\s(.*)$")
    WHISPER_REGEX = re.compile(f"^{USERNAME_REGEX} whispers(?: to you)?:? (.*)$")

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.patterns: Dict[int, ChatPattern] = {}
        self._pattern_counter = 0

    def add_pattern(
        self, name: str, pattern: Union[str, re.Pattern], repeat: bool = True, parse: bool = False
    ) -> int:
        """
        Add a chat pattern to match.

        Args:
            name: Pattern name (emits 'chat:{name}' event)
            pattern: Regex pattern to match
            repeat: Whether to repeat matching
            parse: Whether to parse captures

        Returns:
            Pattern ID
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        pattern_id = self._pattern_counter
        self.patterns[pattern_id] = ChatPattern(
            name=name, pattern=pattern, repeat=repeat, parse=parse
        )
        self._pattern_counter += 1
        return pattern_id

    def remove_pattern(self, pattern_id: int) -> None:
        """Remove a chat pattern"""
        if pattern_id in self.patterns:
            del self.patterns[pattern_id]

    async def send(self, message: str) -> None:
        """
        Send a chat message.

        Args:
            message: Message to send (max 256 chars)
        """
        if not isinstance(message, str):
            message = str(message)

        # Split long messages
        if len(message) > CHAT_LENGTH_LIMIT:
            for i in range(0, len(message), CHAT_LENGTH_LIMIT):
                await self._send_single(message[i : i + CHAT_LENGTH_LIMIT])
                await asyncio.sleep(0.1)  # Small delay between messages
        else:
            await self._send_single(message)

    async def _send_single(self, message: str) -> None:
        """Send a single chat message packet"""
        from mcproto.buffer import Buffer
        from mcproto.protocol.base_io import StructFormat

        # Limit message length
        message = message[:CHAT_LENGTH_LIMIT]

        buf = Buffer()
        buf.write_utf(message)
        buf.write_value(StructFormat.LONGLONG, int(time.time() * 1000))  # timestamp
        buf.write_value(StructFormat.LONGLONG, 0)  # salt
        buf.write_value(StructFormat.BOOL, False)  # no signature
        buf.write_varint(0)  # message count
        # FixedBitset(20) = 20 bits = 3 bytes
        buf.write_value(StructFormat.BYTE, 0)
        buf.write_value(StructFormat.BYTE, 0)
        buf.write_value(StructFormat.BYTE, 0)

        await self.protocol._write_packet(0x07, bytes(buf))
        print(f"[CHAT] Sent: {message}")

    async def whisper(self, username: str, message: str) -> None:
        """
        Send a whisper (private message) to a player.

        Args:
            username: Target player username
            message: Message to send
        """
        await self.send(f"/tell {username} {message}")

    async def command(self, command: str) -> None:
        """
        Send a command.

        Args:
            command: Command to send (without /)
        """
        if not command.startswith("/"):
            command = "/" + command
        await self.send(command)

    def parse_message(self, json_data: Dict[str, Any]) -> ChatMessage:
        """
        Parse a chat message from JSON.

        Args:
            json_data: Raw JSON chat data

        Returns:
            Parsed ChatMessage
        """
        text = self._extract_text(json_data)

        message = ChatMessage(text=text, json_data=json_data)

        # Try to extract sender
        match = self.CHAT_REGEX.match(text)
        if match:
            message.sender = match.group(1)

        return message

    def _extract_text(self, data: Any) -> str:
        """Extract plain text from JSON text component"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            if "text" in data:
                text = data["text"]
            elif "translate" in data:
                text = data["translate"]
                if "with" in data:
                    args = [self._extract_text(arg) for arg in data["with"]]
                    try:
                        text = text % tuple(args)
                    except:
                        text = " ".join([text] + args)
            else:
                text = ""

            if "extra" in data:
                for extra in data["extra"]:
                    text += self._extract_text(extra)

            return text
        elif isinstance(data, list):
            return "".join(self._extract_text(item) for item in data)
        else:
            return str(data)

    def check_patterns(self, message: ChatMessage) -> List[Tuple[str, List[str]]]:
        """
        Check message against all patterns.

        Args:
            message: Chat message to check

        Returns:
            List of (pattern_name, matches) tuples
        """
        matches = []

        for pattern_id, pattern in self.patterns.items():
            match = pattern.pattern.search(message.text)
            if match:
                if pattern.parse:
                    captures = list(match.groups())
                    matches.append((pattern.name, captures))
                else:
                    matches.append((pattern.name, [match.group(0)]))

        return matches


__all__ = [
    "ChatManager",
    "ChatPattern",
    "ChatMessage",
    "CHAT_LENGTH_LIMIT",
]
