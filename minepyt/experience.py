"""
Experience tracking for Minecraft 1.21.4

This module provides:
- Track experience level and points
- Level progress tracking
- Level-up events

Experience is tracked via SetExperience (0x62) packet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


@dataclass
class Experience:
    """
    Represents experience tracking.

    Attributes:
        level: Current experience level
        progress: Progress to next level (0.0 to 1.0)
        total_experience: Total XP points
        level_start_xp: XP needed for current level
        score: Score display score
    """

    level: int = 0
    progress: float = 0.0
    total_experience: int = 0
    level_start_xp: int = 0
    score: int = 0


class ExperienceManager:
    """
    Manages experience tracking.

    This class handles:
    - Experience level tracking
    - Progress to next level
    - Level-up events
    - Score display tracking

    Experience is sent via SetExperience (0x) packet.
    """

    # XP required for each level
    LEVEL_XP = [
        0,    # Level 0
        7,     # Level 1
        20,    # Level 2
        37,    # Level 3
        62,    # Level 4
        101,   # Level 5
        149,   # Level 6
        208,   # Level 7
        307,   # Level 8
        444,   # Level 9
        635,   # Level 10
        801,   # Level 11
        982,   # Level 12
        1154,  # Level 13
        1358,  # Level 14
        1628,  # Level 15
        1924,  # Level 16
        2222,  # Level 17
        2567,  # Level 18
        2952,  # Level 19
        3341,  # Level 20
        3577,  # Level 21
        3833,  # 22
        4112,  # Level 23
        4415,  # Level 24
        4743,  # Level 25
        5094,  # Level 26
        5466,  # Level 27
        5865,  # Level 28
        6298,  # Level 29
        6755,  # Level 30
        7233,  # Level 31
        7732,  # Level 32
        8256,  # Level 33
        8812,  # Level 34
        9398,  # Level 35
        10005, # Level 36
        10627, # Level 37
        11271, # Level 38
        11941, # Level 39
        12634, # Level 40
        13348, # Level 41
        14083, # Level 42
        14833, # Level 43
        15617, # Level 44
        16432, #  level 45
        17268, # Level 46
        18129, # Level 47
        19039, # Level 48
        19972, # Level 49
        20936, # Level 50
        21926, # Level 51
        22946, # Level 52
        23973, # Level 53
        25039, # Level 54
        26111, # Level 55
        27227, # Level 56
        28353, # Level 57
        29501, # Level 58
        30673, # Level 59
        31881, # Level 60
        33112, # Level 61
        34368, # Level 62
    ]

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.xp = Experience()

    @property
    def level(self) -> int:
        """Get current level"""
        return self.xp.level

    @property
    def level_progress(self) -> float:
        """Get progress to next level (0.0-1.0)"""
        return self.xp.progress

    @property
    def total_experience(self) -> int:
        """Get total XP"""
        return self.xp.total_experience

    @property
    def points_until_next_level(self) -> int:
        """Get XP needed for next level"""
        if self.xp.level < len(self.LEVEL_XP) - 1:
            return self.LEVEL_XP[self.xp.level + 1] - self.xp.total_experience
        return 0

    def _add_xp(self, amount: int) -> None:
        """
        Add experience points.

        Args:
            amount: XP amount to add
        """
        old_level = self.xp.level
        self.xp.total_experience += amount

        # Check for level up
        for level, level_xp in enumerate(self.LEVEL_XP):
            if self.xp.total_experience >= level_xp and old_level < level:
                # Level up!
                self.xp.level = level
                self.xp.level_start_xp = self.LEVEL_XP[level - 1]
                print(f"[EXP] Level up! New level: {level}")
                self.protocol.emit("level_up", level)
                break

        # Update progress
        if self.xp.level < len(self.LEVEL_XP) - 1:
            next_xp = self.LEVEL_XP[self.xp.level + 1]
            current_xp = self.xp.total_experience - self.LEVEL_XP[self.xp.level]
            self.xp.progress = (current_xp / (next_xp - self.LEVEL_XP[self.xp.level]))

        # Update score display
        self.xp.score = self.xp.level

    def _set_xp(self, total_experience: int, level: int, progress: float) -> None:
        """
        Set experience from server data.

        Args:
            total_experience: Total XP points
            level: Current level
            progress: Progress to next level
        """
        self.xp.total_experience = total_experience
        self.xp.level = level
        self.xp.progress = progress

        if self.xp.level < len(self.LEVEL_XP):
            self.xp.level_start_xp = self.LEVEL_XP[self.xp.level]
            self.xp.score = level

        print(f"[EXP] Experience: Level {level}, Progress: {progress:.2%}, Total XP: {total_experience}")

    def add_experience(self, amount: int) -> None:
        """
        Add experience points (for custom XP gain).

        Args:
            amount: XP amount to add
        """
        self._add_xp(amount)
        self.protocol.emit("experience_gained", self.xp)


__all__ = [
    "ExperienceManager",
    "Experience",
]
