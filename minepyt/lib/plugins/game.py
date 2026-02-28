"""
Game plugin - handles game state, time, difficulty, game mode
Port of mineflayer/lib/plugins/game.js
"""

from typing import Dict, Any, Optional
from enum import IntEnum


class GameMode(IntEnum):
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    SPECTATOR = 3


class Difficulty(IntEnum):
    PEACEFUL = 0
    EASY = 1
    NORMAL = 2
    HARD = 3


DIFFICULTY_NAMES = {0: "peaceful", 1: "easy", 2: "normal", 3: "hard"}

GAME_MODE_NAMES = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}

DIMENSION_NAMES = {-1: "the_nether", 0: "overworld", 1: "the_end"}


class GameState:
    """Represents the current game state"""

    def __init__(self):
        self.level_type: str = "default"
        self.hardcore: bool = False
        self.game_mode: str = "survival"
        self.dimension: str = "overworld"
        self.difficulty: str = "normal"
        self.max_players: int = 20
        self.server_view_distance: int = 10
        self.enable_respawn_screen: bool = True
        self.server_brand: Optional[str] = None
        self.min_y: int = 0
        self.height: int = 256
        self.time: int = 0
        self.age: int = 0

    def __repr__(self):
        return (
            f"GameState(game_mode={self.game_mode}, dimension={self.dimension}, "
            f"difficulty={self.difficulty}, time={self.time})"
        )


def parse_game_mode(game_mode_bits: int) -> str:
    """Parse game mode from bits"""
    if game_mode_bits < 0 or game_mode_bits > 0b11:
        return "survival"
    return GAME_MODE_NAMES.get(game_mode_bits & 0b11, "survival")


def game_plugin(bot, options: Dict[str, Any] = None) -> None:
    """
    Game plugin - injects game state handling into bot

    Adds to bot:
        bot.game - GameState instance with current game info

    Events emitted:
        'game' - when game state changes
        'time' - when world time changes
        'login' - when bot logs in
        'respawn' - when bot respawns
    """
    options = options or {}

    # Initialize game state
    bot.game = GameState()

    # Store reference to protocol for packet handling
    protocol = bot._protocol if hasattr(bot, "_protocol") else bot

    def handle_join_game(packet_data: Dict[str, Any]) -> None:
        """Handle login/join game packet data"""
        # Game mode (lower 4 bits, bit 3 = hardcore)
        game_mode_raw = packet_data.get("game_mode", 0)
        bot.game.hardcore = bool(game_mode_raw & 0b1000)
        bot.game.game_mode = parse_game_mode(game_mode_raw & 0b111)

        # Dimension
        dimension = packet_data.get("dimension", 0)
        if isinstance(dimension, int):
            bot.game.dimension = DIMENSION_NAMES.get(dimension, f"unknown_{dimension}")
        elif isinstance(dimension, str):
            bot.game.dimension = dimension.replace("minecraft:", "")

        # Level type
        bot.game.level_type = packet_data.get("level_type", "default")
        if packet_data.get("is_flat", False):
            bot.game.level_type = "flat"

        # Other info
        bot.game.max_players = packet_data.get("max_players", 20)
        bot.game.server_view_distance = packet_data.get("view_distance", 10)

        # World height
        bot.game.min_y = packet_data.get("min_y", 0)
        bot.game.height = packet_data.get("height", 256)

        print(
            f"[GAME] Mode: {bot.game.game_mode}, Dimension: {bot.game.dimension}, "
            f"Hardcore: {bot.game.hardcore}"
        )

        bot.emit("login")
        bot.emit("game")

    def handle_respawn(packet_data: Dict[str, Any]) -> None:
        """Handle respawn packet"""
        handle_join_game(packet_data)
        bot.emit("respawn")
        print(f"[GAME] Respawned in {bot.game.dimension}")

    def handle_game_state_change(reason: int, game_mode: int) -> None:
        """Handle game state change packet"""
        # Reason 3 = change game mode
        # Reason 4 = win game (credits)
        if reason == 3:
            bot.game.game_mode = parse_game_mode(game_mode)
            bot.emit("game")
            print(f"[GAME] Game mode changed to: {bot.game.game_mode}")
        elif reason == 4 and game_mode == 1:
            # Send client command to close credits
            pass  # TODO: implement when we have packet sending

    def handle_time_update(world_age: int, time_of_day: int) -> None:
        """Handle time update packet"""
        bot.game.age = world_age
        bot.game.time = time_of_day
        bot.emit("time")

    def handle_difficulty(difficulty: int) -> None:
        """Handle difficulty change"""
        bot.game.difficulty = DIFFICULTY_NAMES.get(difficulty, "unknown")
        print(f"[GAME] Difficulty: {bot.game.difficulty}")

    # Register packet handlers
    # These will be called by the protocol handler
    bot._game_handlers = {
        "join_game": handle_join_game,
        "respawn": handle_respawn,
        "game_state_change": handle_game_state_change,
        "time_update": handle_time_update,
        "difficulty": handle_difficulty,
    }

    print("[PLUGIN] Game plugin loaded")
