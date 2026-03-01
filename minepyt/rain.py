"""
Weather (rain) tracking for Minecraft 1.21.4

This module provides:
- Track rain state
- Thunder state
- Weather changes

Weather is sent via GameStateChange packet (0x4A) with reason 3.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class WeatherState(IntEnum):
    """Weather states"""

    CLEAR = 0
    RAINING = 1
    RAINING_THUNDERING = 2


class ThunderState(IntEnum):
    """Thunder states"""

    OFF = 0
    STARTING = 1
    STOPPING = 2


@dataclass
class Weather:
    """
    Represents current weather.

    Attributes:
        is_raining: Whether it's raining
        is_thundering: Whether it's thundering
        rain_state: Rain intensity
        thunder_state: Thunder state
    """

    is_raining: bool = False
    is_thundering: bool = False
    rain_state: WeatherState = WeatherState.CLEAR
    thunder_state: ThunderState = ThunderState.OFF


class WeatherManager:
    """
    Manages weather tracking.

    This class handles:
    - Rain/thunder state tracking
    - Weather change events

    Weather is tracked via GameStateChange packet (0x4A) with reason 3.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.weather = Weather()

        # Register for weather events (handled in protocol/game state changes)
        protocol.on("weather_update", self._on_weather_update)

    @property
    def current_weather(self) -> Weather:
        """Get current weather"""
        return self.weather

    def _on_weather_update(self, rain_state: WeatherState, thunder_state: ThunderState) -> None:
        """
        Handle weather update event.

        Args:
            rain_state: Rain state (clear, raining, thundering)
            thunder_state: Thunder state (off, starting, stopping)
        """
        old_raining = self.weather.is_raining
        old_thundering = self.weather.is_thundering

        self.weather.rain_state = rain_state
        self.weather.thunder_state = thunder_state

        self.weather.is_raining = rain_state != WeatherState.CLEAR
        self.weather.is_thundering = thunder_state != ThunderState.OFF

        if old_raining != self.weather.is_raining:
            print(f"[WEATHER] Rain: {'Started' if self.weather.is_raining else 'Stopped'}")
            self.protocol.emit("rain", self.weather.is_raining)

        if old_thundering != self.weather.is_thundering:
            print(f"[WEATHER] Thunder: {'Started' if self.weather.is_thundering else 'Stopped'}")
            self.protocol.emit("thunder", self.weather.is_thundering)


__all__ = [
    "WeatherManager",
    "Weather",
    "WeatherState",
    "ThunderState",
]
