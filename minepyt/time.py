"""
Game time tracking for Minecraft 1.21.4

This module provides:
- Track in-game time (ticks)
- Time of day (day/night)
- Age tracking

Game time is sent via SetTime (0x6F) packet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class TimeOfDay(IntEnum):
    """Time of day states"""

    DAY = 1000
    SUNSET = 13000
    NIGHT = 18000
    SUNRISE = 23000
    MIDNIGHT = 0


@dataclass
class GameTime:
    """
    Represents in-game time.

    Attributes:
        time: Current game time in ticks (0-23999)
        time_of_day: Time of day
        day: Current day (0-6)
        age: Player age in ticks
        is_daylight: Whether it's daylight
        sky_light: Sky brightness (0-15)
    """

    time: int = 0
    time_of_day: TimeOfDay = TimeOfDay.DAY
    day: int = 0
    age: int = 0
    is_daylight: bool = True
    sky_light: int = 15
    moon_phase: int = 0


class TimeManager:
    """
    Manages game time tracking.

    This class handles:
    - Time tracking (ticks, day, age)
    - Time of day calculation
    - Sky light calculation

    Time is sent via SetTime (0x6F) packet.
    """

    def __init__(self, protocol: " MinecraftProtocol"):
        self.protocol = protocol

        self.time = GameTime()

    @property
    def day_time(self) -> TimeOfDay:
        """Get time of day"""
        return self.time.time_of_day

    @property
    def current_day(self) -> int:
        """Get current day number (0-6)"""
        return self.time.day

    @property
    def current_time(self) -> int:
        """Get current game time in ticks"""
        return self.time.time

    def _update_time_properties(self) -> None:
        """Update derived time properties"""
        # Time of day (0-23999 ticks)
        tod = self.time.time % 24000

        if 0 <= tod < 12000:
            self.time.time_of_day = TimeOfDay.DAY
            self.time.is_daylight = True
        elif 12000 <= tod < 13000:
            self.time.time_of_day = TimeOfDay.SUNSET
            self.time.is_daylight = True
        elif 13000 <= tod < 18000:
            self.time.time_of_day = TimeOfDay.NIGHT
            self.time.is_daylight = False
        elif 18000 <= tod < 23000:
            self.time.time_of_day = TimeOfDay.NIGHT
            self.time.is_daylight = False
        else:
            self.time.time_of_day = TimeOfDay.SUNRISE
            self.time.is_daylight = True

        # Day (0-6, each is 4000 ticks)
        self.time.day = self.time.time // 24000

        # Sky light based on time of day
        if self.time.time_of_day in [TimeOfDay.NIGHT]:
            self.time.sky_light = 4  # Dark night
        elif self.time.time_of_day in [TimeOfDay.SUNRISE, TimeOfDay.SUNSET]:
            self.time.sky_light = 10  # Bright dawn/dusk
        else:
            self.time.sky_light = 15  # Bright day

        # Moon phase (0-7, based on day)
        self.time.moon_phase = (self.time.day + 1) % 8


class TimeUpdateHandler:
    """Helper class for time updates"""

    def __init__(self, manager: TimeManager):
        self.manager = manager

    def handle_time_update(self, time_data: dict) -> None:
        """
        Handle time update from server.

        Args:
            time_data: Time packet data
        """
        world_age = time_data.get("world_age", 0)
        day_time = time_data.get("day_time", 0)

        self.manager.time.time = day_time
        self.manager.time.age = world_age
        self.manager._update_time_properties()

        self.manager.protocol.emit("time", self.manager.time)


# TimeManager with event handler integration
class TimeManagerWithEvents(TimeManager):
    def __init__(self, protocol: "MinecraftProtocol"):
        super().__init__(protocol)

        self._handler = TimeUpdateHandler(self)

        # Register for time event
        # Note: In a real implementation, this would be handled in protocol handlers


__all__ = [
    "TimeManager",
    "TimeManagerWithEvents",
    "GameTime",
    "TimeOfDay",
]
