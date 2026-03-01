"""
Title tracking for Minecraft 1.21.4

This module provides:
- Track title and subtitle on screen
- Title times (fade in, stay, fade out)
- Title clear events

Titles are sent via SetTitleText packet (0x66) and Title packet (0x63).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class TitleAction(IntEnum):
    """Title action types"""

    SET_TITLE = 0
    SET_SUBTITLE = 1
    SET_ACTION_BAR = 2
    SET_TIMES_AND_DISPLAY = 3
    HIDE = 4
    RESET = 5


@dataclass
class TitleTimes:
    """
    Title fade times.

    Attributes:
        fade_in: Fade in duration (ticks, 20 ticks = 1 second)
        stay: Stay duration (ticks)
        fade_out: Fade out duration (ticks)
    """

    fade_in: int = 10  # 0.5 seconds
    stay: int = 70  # 3.5 seconds
    fade_out: int = 20  # 1 second


class TitleManager:
    """
    Manages title tracking.

    This class handles:
    - Title and subtitle updates
    - Title times (fade in/stay/out)
    - Action bar text
    - Title clear events

    Title packets:
    - SetTitleText (0x66): Title and subtitle text
    - SetTitleTime (0x68): Fade times
    - ClearTitles (0x69): Clear all titles
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.title: str = ""
        self.subtitle: str = ""
        self.action_bar: str = ""
        self.times: Optional[TitleTimes] = None

        # Register for title packets
        protocol.on("set_title_text", self._on_set_title_text)
        protocol.on("set_title_time", self._on_set_title_time)
        protocol.on("clear_titles", self._on_clear_titles)

    @property
    def current_title(self) -> str:
        """Get current title"""
        return self.title

    @property
    def current_subtitle(self) -> str:
        """Get current subtitle"""
        return self.subtitle

    @property
    def current_action_bar(self) -> str:
        """Get current action bar text"""
        return self.action_bar

    def _on_set_title_text(self, packet_data: dict) -> None:
        """
        Handle set title text packet (0x66).

        Args:
            packet_data: Decoded packet data
        """
        action = packet_data.get("action")

        if action == TitleAction.SET_TITLE:
            self.title = self._parse_text(packet_data.get("title", ""))
            self._display()
            self.protocol.emit("title", self.title, "title")

        elif action == TitleAction.SET_SUBTITLE:
            self.subtitle = self._parse_text(packet_data.get("title", ""))
            self._display()
            self.protocol.emit("title", self.subtitle, "subtitle")

        elif action == TitleAction.SET_ACTION_BAR:
            self.action_bar = self._parse_text(packet_data.get("text", ""))
            self._display()
            self.protocol.emit("title", self.action_bar, "action_bar")

        elif action == TitleAction.SET_TIMES_AND_DISPLAY:
            # Set times if provided
            if "fade_in" in packet_data or "stay" in packet_data or "fade_out" in packet_data:
                self.times = TitleTimes(
                    fade_in=packet_data.get("fade_in", 10),
                    stay=packet_data.get("stay", 70),
                    fade_out=packet_data.get("fade_out", 20),
                )

            # Set title if provided
            if "title" in packet_data:
                self.title = self._parse_text(packet_data["title"])
            if "subtitle" in packet_data:
                self.subtitle = self._parse_text(packet_data["subtitle"])

            self._display()

            # Emit events
            if "title" in packet_data:
                self.protocol.emit("title", self.title, "title")
            if "subtitle" in packet_data:
                self.protocol.emit("title", self.subtitle, "subtitle")
            if "times" in packet_data:
                self.protocol.emit(
                    "title_times", self.times.fade_in, self.times.stay, self.times.fade_out
                )

    def _on_set_title_time(self, packet_data: dict) -> None:
        """
        Handle set title time packet (0x68).

        Args:
            packet_data: Decoded packet data
        """
        self.times = TitleTimes(
            fade_in=packet_data.get("fade_in", 10),
            stay=packet_data.get("stay", 70),
            fade_out=packet_data.get("fade_out", 20),
        )

        # Update display
        self._display()

        self.protocol.emit("title_times", self.times.fade_in, self.times.stay, self.times.fade_out)

    def _on_clear_titles(self, packet_data: dict) -> None:
        """
        Handle clear titles packet (0x69).

        Args:
            packet_data: Decoded packet data
        """
        reset_titles = packet_data.get("reset", False)

        if reset_titles:
            # Reset to default values
            self.title = ""
            self.subtitle = ""
            self.action_bar = ""
            self.times = None
        else:
            # Clear without resetting
            self.title = ""
            self.subtitle = ""
            self.action_bar = ""

        self.protocol.emit("title_clear")

    def _display(self) -> None:
        """Display current title configuration"""
        if self.title or self.subtitle:
            print(f"[TITLE] Title: '{self.title}', Subtitle: '{self.subtitle}'")
        if self.action_bar:
            print(f"[TITLE] Action Bar: '{self.action_bar}'")

    def _parse_text(self, text: str) -> str:
        """
        Parse text component to string.

        Args:
            text: JSON component or plain text

        Returns:
            Parsed string
        """
        if not text:
            return ""

        try:
            # Try parsing as JSON
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                # Extract text from JSON component
                if "text" in parsed:
                    return parsed["text"]
                # Handle translations
                elif "translate" in parsed:
                    return parsed["translate"]
            return str(parsed)
        except (json.JSONDecodeError, TypeError):
            # Use plain text
            return text

    def set_title(self, title: str) -> None:
        """
        Set title (client-side).

        This is a convenience method, usually handled by server.

        Args:
            title: Title text
        """
        self.title = self._parse_text(title)
        self._display()

    def set_subtitle(self, subtitle: str) -> None:
        """
        Set subtitle (client-side).

        This is a convenience method, usually handled by server.

        Args:
            subtitle: Subtitle text
        """
        self.subtitle = self._parse_text(subtitle)
        self._display()

    def clear(self) -> None:
        """Clear all titles"""
        self.title = ""
        self.subtitle = ""
        self.action_bar = ""
        self.times = None


__all__ = [
    "TitleManager",
    "TitleAction",
    "TitleTimes",
]
