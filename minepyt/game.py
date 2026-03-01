"""
Game state tracking for Minecraft 1.21.4

This module provides:
- Track game difficulty
- Track game mode
- Track dimension
- Spectator mode

Game state is sent via GameStateChange (0x4A) packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class Difficulty(IntEnum):
    """Game difficulty levels"""

    PEACEFUL = 0
    EASY = 1
    NORMAL = 2
    HARD = 3
    HARDCORE = 4


class GameMode(IntEnum):
    """Game modes"""

    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    SPECTATOR = 3


class Dimension(IntEnum):
    """World dimensions"""

    OVERWORLD = 0
    THE_NETHER = 1
    THE_END = 2
    THE_END_MIDLANDS = None  # Added in 1.21


@dataclass
class GameState:
    """
    Represents current game state.

    Attributes:
        difficulty: Game difficulty
        game_mode: Game mode
        dimension: Current dimension
        is_spectator: Whether in spectator mode
        is_hardcore: Whether hardcore mode
        is_flat: Whether flat world
    """

    difficulty: Difficulty = Difficulty.NORMAL
    game_mode: GameMode = GameMode.SURVIVAL
    dimension: Dimension = Dimension.OVERWORLD
    is_spectator: bool = False
    is_hardcore: bool = False
    is_flat: bool = False


class GameStateManager:
    """
    Manages game state tracking.

    This class handles:
    - Difficulty tracking
    - Game mode tracking
    - Dimension tracking
    - Spectator mode tracking

    Game state is sent via GameStateChange (0x4A) packet.
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        self.state = GameState()

        # Register for game state events (handled in protocol)
        protocol.on("game_mode", self._on_game_mode)
        protocol.on("difficulty", self._on_difficulty)
        protocol.on("dimension", self._on_dimension)
        protocol.on("spectator", self._on_spectator)

    @property
    def current_difficulty(self) -> Difficulty:
        """Get current difficulty"""
        return self.state.difficulty

    @property
    def current_game_mode(self) -> GameMode:
        """Get current game mode"""
        return self.state.game_mode

    @property
    def current_dimension(self) -> Dimension:
        """Get current dimension"""
        return self.state.dimension

    @property
    def is_spectator_mode(self) -> bool:
        """Check if in spectator mode"""
        return self.state.is_spectator

    def _on_game_mode(self, game_mode: GameMode) -> None:
        """
        Handle game mode change.

        Args:
            game_mode: New game mode
        """
        old_mode = self.state.game_mode
        self.state.game_mode = game_mode

        print(f"[GAME] Game mode: {old_mode.name} -> {game_mode.name}")
        self.protocol.emit("game_mode", game_mode, old_mode)

    def _on_difficulty(self, difficulty: Difficulty) -> None:
        """
        Handle difficulty change.

        Args:
            difficulty: New difficulty
        """
        old_difficulty = self.state.difficulty
        self.state.difficulty = difficulty

        print(f"[GAME] Difficulty: {old_difficulty.name} -> {difficulty.name}")
        self.protocol.emit("difficulty", difficulty, old_difficulty)

    def _on_dimension(self, dimension: Dimension) -> None:
        """
        Handle dimension change.

        Args:
            dimension: New dimension
        """
        old_dimension = self.state.dimension
        self.state.dimension = dimension

        print(f"[GAME] Dimension: {old_dimension.name if old_dimension else 'unknown'} -> {dimension.name if dimension else 'unknown'}")
        self.protocol.emit("dimension", dimension, old_dimension)

    def _on_spectator(self, is_spectator: bool) -> None:
        """
        Handle spectator mode change.

        Args:
            is_spectator: Whether in spectator mode
        """
        old_spectator = self.state.is_spectator
        self.state.is_spectator = is_spectator

        if old_spectator != is_spectator:
            print(f"[GAME] Spectator mode: {is_spectator}")
            self.protocol.emit("spectator", is_spectator)
        elif old_spectator:
            print("[GAME] Exited spectator mode")
            self.protocol.emit("spectator", is_spectator)


__all__ = [
    "GameStateManager",
    "GameState",
    "Difficulty",
    "GameMode",
    "Dimension",
]
