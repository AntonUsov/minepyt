"""
Scoreboard tracking for Minecraft 1.21.4

This module provides:
- Track scoreboard objectives
- Track scoreboard scores
- Track scoreboard display positions
- Scoreboard events (created, deleted, updated)

Scoreboards use multiple packets:
- Set Scoreboard Objective (0x5A)
- Update Score (0x5B)
- Display Objective (0x5C)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class ScoreboardPosition(IntEnum):
    """Scoreboard display positions"""

    LIST = 0  # Tab list
    SIDEBAR = 1  # Right side of screen
    BELOW_NAME = 2  # Below player name


class ScoreboardAction(IntEnum):
    """Scoreboard objective actions"""

    CREATE = 0  # Create objective
    REMOVE = 1  # Remove objective
    UPDATE_TEXT = 2  # Update display text


class ScoreAction(IntEnum):
    """Score update actions"""

    CREATE_OR_UPDATE = 0  # Create or update score
    REMOVE = 1  # Remove score


@dataclass
class Score:
    """Represents a single score entry"""

    name: str
    value: int

    def __lt__(self, other: "Score") -> bool:
        """Sort by value descending (higher scores first)"""
        return self.value > other.value


@dataclass
class Scoreboard:
    """
    Represents a scoreboard objective.

    Attributes:
        name: Objective name (internal identifier)
        title: Display title (shown to players)
        items: List of scores in this objective
    """

    name: str
    title: str
    items: dict[str, Score] = field(default_factory=dict)

    def set_title(self, title: str) -> None:
        """
        Update scoreboard title.

        Args:
            title: New title (can be JSON text component or plain text)
        """
        try:
            # Try parsing as JSON (for 1.13+ text components)
            parsed = json.loads(title)
            if isinstance(parsed, dict) and "text" in parsed:
                self.title = parsed["text"]
            else:
                self.title = title
        except (json.JSONDecodeError, TypeError):
            # Use plain text if not valid JSON
            self.title = title

    def add_score(self, name: str, value: int) -> Score:
        """
        Add or update a score.

        Args:
            name: Score name (usually entity/player name)
            value: Score value

        Returns:
            The Score object
        """
        score = Score(name=name, value=value)
        self.items[name] = score
        return score

    def remove_score(self, name: str) -> Optional[Score]:
        """
        Remove a score.

        Args:
            name: Score name to remove

        Returns:
            The removed Score or None if not found
        """
        return self.items.pop(name, None)

    def get_score(self, name: str) -> Optional[Score]:
        """
        Get a score by name.

        Args:
            name: Score name

        Returns:
            Score or None if not found
        """
        return self.items.get(name)

    def get_scores(self) -> list[Score]:
        """
        Get all scores sorted by value (descending).

        Returns:
            List of Score objects sorted highest to lowest
        """
        return sorted(self.items.values(), key=lambda s: s.value, reverse=True)

    @property
    def score_count(self) -> int:
        """Get number of scores in this objective"""
        return len(self.items)


class ScoreboardManager:
    """
    Manages scoreboard tracking.

    This class handles:
    - Scoreboard objective creation/deletion/updates
    - Score creation/removal/updates
    - Display position tracking

    Scoreboard packets:
    - Set Objective (0x5A): actions CREATE (0), REMOVE (1), UPDATE_TEXT (2)
    - Update Score (0x5B): actions CREATE_OR_UPDATE (0), REMOVE (1)
    - Display Objective (0x5C): position, objective name
    """

    # Packet IDs (Minecraft 1.21.4)
    PACKET_SET_OBJECTIVE = 0x5A
    PACKET_UPDATE_SCORE = 0x5B
    PACKET_DISPLAY_OBJECTIVE = 0x5C

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

        # Scoreboards by objective name
        self.scoreboards: dict[str, Scoreboard] = {}

        # Display positions: position -> objective name
        self.positions: dict[ScoreboardPosition, Optional[str]] = {
            ScoreboardPosition.LIST: None,
            ScoreboardPosition.SIDEBAR: None,
            ScoreboardPosition.BELOW_NAME: None,
        }

        # Register for scoreboard packets
        protocol.on("scoreboard_objective", self._on_set_objective)
        protocol.on("scoreboard_score", self._on_update_score)
        protocol.on("scoreboard_display_objective", self._on_display_objective)

    def get_scoreboard(self, name: str) -> Optional[Scoreboard]:
        """
        Get scoreboard by objective name.

        Args:
            name: Objective name

        Returns:
            Scoreboard or None if not found
        """
        return self.scoreboards.get(name)

    def get_all_scoreboards(self) -> list[Scoreboard]:
        """
        Get all scoreboards.

        Returns:
            List of all Scoreboard objects
        """
        return list(self.scoreboards.values())

    def get_display_position(self, position: ScoreboardPosition) -> Optional[Scoreboard]:
        """
        Get scoreboard at a display position.

        Args:
            position: ScoreboardPosition (LIST, SIDEBAR, BELOW_NAME)

        Returns:
            Scoreboard at position or None
        """
        objective_name = self.positions.get(position)
        if objective_name:
            return self.scoreboards.get(objective_name)
        return None

    # Packet handlers

    def _on_set_objective(self, packet_data: dict) -> None:
        """
        Handle set objective packet (0x5A).

        Args:
            packet_data: Decoded packet data with 'action' field
        """
        action = packet_data.get("action")
        name = packet_data.get("name")

        if action == ScoreboardAction.CREATE:
            self._create_objective(packet_data)
        elif action == ScoreboardAction.REMOVE:
            self._remove_objective(name)
        elif action == ScoreboardAction.UPDATE_TEXT:
            self._update_objective_text(name, packet_data)
        else:
            print(f"[SCOREBOARD] Unknown objective action: {action}")

    def _create_objective(self, data: dict) -> None:
        """Create new scoreboard objective"""
        name = data.get("name")
        display_text = data.get("displayText", "")

        scoreboard = Scoreboard(name=name, title="")
        scoreboard.set_title(display_text)

        self.scoreboards[name] = scoreboard
        print(f"[SCOREBOARD] Created objective: {name}")
        self.protocol.emit("scoreboard_created", scoreboard)

    def _remove_objective(self, name: str) -> None:
        """Remove scoreboard objective"""
        if name in self.scoreboards:
            scoreboard = self.scoreboards.pop(name)
            print(f"[SCOREBOARD] Removed objective: {name}")
            self.protocol.emit("scoreboard_deleted", scoreboard)

            # Remove from display positions if present
            for pos, obj_name in self.positions.items():
                if obj_name == name:
                    self.positions[pos] = None

    def _update_objective_text(self, name: str, data: dict) -> None:
        """Update objective display text"""
        if name in self.scoreboards:
            scoreboard = self.scoreboards[name]
            display_text = data.get("displayText", "")
            scoreboard.set_title(display_text)
            print(f"[SCOREBOARD] Updated objective title: {name}")
            self.protocol.emit("scoreboard_title_changed", scoreboard)

    def _on_update_score(self, packet_data: dict) -> None:
        """
        Handle update score packet (0x5B).

        Args:
            packet_data: Decoded packet data with 'action' field
        """
        action = packet_data.get("action")
        item_name = packet_data.get("itemName", "")
        score_name = packet_data.get("scoreName", "")
        value = packet_data.get("value", 0)

        # Try to find scoreboard by item_name or score_name
        scoreboard = None
        if score_name and score_name in self.scoreboards:
            scoreboard = self.scoreboards[score_name]
        elif item_name and item_name in self.scoreboards:
            scoreboard = self.scoreboards[item_name]

        if action == ScoreAction.CREATE_OR_UPDATE:
            if scoreboard:
                score = scoreboard.add_score(item_name, value)
                print(f"[SCOREBOARD] Updated score: {item_name} = {value}")
                self.protocol.emit("score_updated", scoreboard, score)
            else:
                # Score might not be in a scoreboard yet
                print(f"[SCOREBOARD] Received score for unknown scoreboard: {item_name}")

        elif action == ScoreAction.REMOVE:
            if scoreboard:
                score = scoreboard.remove_score(item_name)
                if score:
                    print(f"[SCOREBOARD] Removed score: {item_name}")
                    self.protocol.emit("score_removed", scoreboard, score)
            else:
                # Try removing from all scoreboards
                for sb in self.scoreboards.values():
                    if item_name in sb.items:
                        score = sb.remove_score(item_name)
                        print(f"[SCOREBOARD] Removed score: {item_name}")
                        self.protocol.emit("score_removed", sb, score)
                        break
        else:
            print(f"[SCOREBOARD] Unknown score action: {action}")

    def _on_display_objective(self, packet_data: dict) -> None:
        """
        Handle display objective packet (0x5C).

        Args:
            packet_data: Decoded packet data
        """
        position = packet_data.get("position")
        objective_name = packet_data.get("scoreName")

        if position is None:
            return

        self.positions[position] = objective_name

        scoreboard = self.scoreboards.get(objective_name)
        old_scoreboard = self.get_display_position(position)

        print(f"[SCOREBOARD] Display position {position}: {objective_name}")
        self.protocol.emit("scoreboard_position_changed", position, scoreboard, old_scoreboard)


__all__ = [
    "ScoreboardManager",
    "Scoreboard",
    "Score",
    "ScoreboardPosition",
    "ScoreboardAction",
    "ScoreAction",
]
