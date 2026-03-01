"""
Team tracking for Minecraft 1.21.4

This module provides:
- Track teams (create, remove, update, join, leave)
- Team members management
- Team properties (friendly fire, collision, formatting)

Teams are sent via Team packet (0x57).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol


class TeamMode(IntEnum):
    """Team update modes"""

    CREATE = 0
    REMOVE = 1
    UPDATE = 2
    JOIN = 3
    LEAVE = 4


class TeamVisibility(IntEnum):
    """Team name tag visibility"""

    ALWAYS = 0
    NEVER = 1
    HIDE_FOR_OTHER_TEAMS = 2
    HIDE_FOR_OWN_TEAM = 3


class TeamCollisionRule(IntEnum):
    """Team collision rules"""

    ALWAYS = 0
    NEVER = 1
    PUSH_OTHER_TEAMS = 2
    PUSH_OWN_TEAM = 3


@dataclass
class Team:
    """
    Represents a team.

    Attributes:
        name: Team name (internal identifier)
        display_name: Display name shown to players
        prefix: Text prefix before player names
        suffix: Text suffix after player names
        friendly_fire: Whether teammates can damage each other
        visibility: Name tag visibility
        collision: Collision rule with teammates
        color: Team color (0-15)
        members: List of player UUIDs in team
    """

    name: str
    display_name: Optional[str] = None
    prefix: str = ""
    suffix: str = ""
    friendly_fire: bool = False
    visibility: TeamVisibility = TeamVisibility.ALWAYS
    collision: TeamCollisionRule = TeamCollisionRule.ALWAYS
    color: int = 0
    members: list = None

    def __post_init__(self):
        if self.members is None:
            self.members = []

    def add_member(self, uuid: str) -> None:
        """
        Add player to team.

        Args:
            uuid: Player UUID
        """
        if uuid not in self.members:
            self.members.append(uuid)

    def remove_member(self, uuid: str) -> None:
        """
        Remove player from team.

        Args:
            uuid: Player UUID
        """
        if uuid in self.members:
            self.members.remove(uuid)

    @property
    def member_count(self) -> int:
        """Get number of team members"""
        return len(self.members)

    def update(
        self,
        display_name: Optional[str] = None,
        friendly_fire: Optional[bool] = None,
        visibility: Optional[TeamVisibility] = None,
        collision: Optional[TeamCollisionRule] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        color: Optional[int] = None,
    ) -> None:
        """
        Update team properties.

        Args:
            display_name: New display name
            friendly_fire: Friendly fire setting
            visibility: Name tag visibility
            collision: Collision rule
            prefix: Text prefix
            suffix: Text suffix
            color: Team color (0-15)
        """
        if display_name is not None:
            self.display_name = display_name
        if friendly_fire is not None:
            self.friendly_fire = friendly_fire
        if visibility is not None:
            self.visibility = visibility
        if collision is not None:
            self.collision = collision
        if prefix is not None:
            self.prefix = prefix
        if suffix is not None:
            self.suffix = suffix
        if color is not None:
            self.color = color


class TeamManager:
    """
    Manages team tracking.

    This class handles:
    - Team creation/deletion/updates
    - Team member management
    - Team property changes

    Team packets:
    - Team (0x57): Team updates with mode field
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol
        self.teams: dict[str, Team] = {}
        self.player_teams: dict[str, str] = {}  # UUID -> team name

        # Register for team packets
        protocol.on("team", self._on_team_packet)

    def get_team(self, name: str) -> Optional[Team]:
        """
        Get team by name.

        Args:
            name: Team name

        Returns:
            Team or None if not found
        """
        return self.teams.get(name)

    def get_all_teams(self) -> list[Team]:
        """
        Get all teams.

        Returns:
            List of all Team objects
        """
        return list(self.teams.values())

    def get_player_team(self, uuid: str) -> Optional[Team]:
        """
        Get team for a player.

        Args:
            uuid: Player UUID

        Returns:
            Team or None if player not in a team
        """
        team_name = self.player_teams.get(uuid)
        if team_name:
            return self.teams.get(team_name)
        return None

    def _on_team_packet(self, packet_data: dict) -> None:
        """
        Handle team packet (0x57).

        Args:
            packet_data: Decoded packet data with mode field
        """
        mode = packet_data.get("mode")
        team_name = packet_data.get("team_name", "")

        if mode == TeamMode.CREATE:
            self._create_team(team_name, packet_data)
        elif mode == TeamMode.REMOVE:
            self._remove_team(team_name)
        elif mode == TeamMode.UPDATE:
            self._update_team(team_name, packet_data)
        elif mode == TeamMode.JOIN:
            self._team_join(team_name, packet_data)
        elif mode == TeamMode.LEAVE:
            self._team_leave(team_name, packet_data)
        else:
            print(f"[TEAM] Unknown mode: {mode}")

    def _create_team(self, name: str, data: dict) -> None:
        """Create new team"""
        team = Team(
            name=name,
            display_name=self._parse_text(data.get("display_name")),
            prefix=self._parse_text(data.get("prefix", "")),
            suffix=self._parse_text(data.get("suffix", "")),
            friendly_fire=data.get("friendly_fire", False),
            visibility=TeamVisibility(data.get("visibility", 0)),
            collision=TeamCollisionRule(data.get("collision", 0)),
            color=data.get("color", 0),
        )

        self.teams[name] = team
        print(f"[TEAM] Created team: {name}")
        self.protocol.emit("team_created", team)

    def _remove_team(self, name: str) -> None:
        """Remove team"""
        if name in self.teams:
            team = self.teams.pop(name)

            # Remove all players from team
            for player_uuid in team.members:
                if self.player_teams.get(player_uuid) == name:
                    del self.player_teams[player_uuid]

            print(f"[TEAM] Removed team: {name}")
            self.protocol.emit("team_removed", team)

    def _update_team(self, name: str, data: dict) -> None:
        """Update team properties"""
        if name not in self.teams:
            # Team might not exist yet, try to create it
            print(f"[TEAM] Warning: Updating non-existent team {name}, creating...")
            self._create_team(name, data)
            return

        team = self.teams[name]
        team.update(
            display_name=self._parse_text(data.get("display_name")),
            friendly_fire=data.get("friendly_fire"),
            visibility=TeamVisibility(data.get("visibility")) if "visibility" in data else None,
            collision=TeamCollisionRule(data.get("collision")) if "collision" in data else None,
            prefix=self._parse_text(data.get("prefix")) if "prefix" in data else None,
            suffix=self._parse_text(data.get("suffix")) if "suffix" in data else None,
            color=data.get("color"),
        )

        print(f"[TEAM] Updated team: {name}")
        self.protocol.emit("team_updated", team)

    def _team_join(self, name: str, data: dict) -> None:
        """Add player(s) to team"""
        if name not in self.teams:
            print(f"[TEAM] Warning: Joining non-existent team {name}")
            return

        team = self.teams[name]
        players = data.get("players", [])

        for player_uuid in players:
            # Remove player from old team if any
            if player_uuid in self.player_teams:
                old_team_name = self.player_teams[player_uuid]
                if old_team_name in self.teams:
                    self.teams[old_team_name].remove_member(player_uuid)

            # Add to new team
            team.add_member(player_uuid)
            self.player_teams[player_uuid] = name

        print(f"[TEAM] {len(players)} player(s) joined team {name}")
        self.protocol.emit("team_member_added", team, players)

    def _team_leave(self, name: str, data: dict) -> None:
        """Remove player(s) from team"""
        if name not in self.teams:
            print(f"[TEAM] Warning: Leaving non-existent team {name}")
            return

        team = self.teams[name]
        players = data.get("players", [])

        for player_uuid in players:
            team.remove_member(player_uuid)
            if self.player_teams.get(player_uuid) == name:
                del self.player_teams[player_uuid]

        print(f"[TEAM] {len(players)} player(s) left team {name}")
        self.protocol.emit("team_member_removed", team, players)

    def _parse_text(self, text: Optional[str]) -> Optional[str]:
        """
        Parse text component to string.

        Args:
            text: JSON component or plain text

        Returns:
            Parsed string or None
        """
        if text is None:
            return None

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


__all__ = [
    "TeamManager",
    "Team",
    "TeamMode",
    "TeamVisibility",
    "TeamCollisionRule",
]
