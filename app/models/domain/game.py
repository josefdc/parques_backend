"""Domain model for the Parqués game aggregate.

Defines the GameAggregate class, which encapsulates the full state and logic
of a Parqués game, including player management, turn order, and event logging.
"""
from __future__ import annotations
import uuid
import asyncio
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Deque, TYPE_CHECKING, Tuple

from app.core.enums import GameState, Color
from app.models.domain.board import Board

if TYPE_CHECKING:
    from app.models.domain.player import Player
    from app.models.schemas import GameEventPydantic

MIN_PLAYERS = 2
MAX_PLAYERS = 4

class GameAggregate:
    """Represents the complete state of a Parqués game.

    This is the root aggregate in DDD terminology. It manages players, board,
    turn order, game state, and event logging.
    """
    id: uuid.UUID
    state: GameState
    board: Board
    players: Dict[Color, 'Player']
    turn_order: Deque[Color]
    current_turn_color: Optional[Color]
    dice_roll_count: int
    last_dice_roll: Optional[Tuple[int, int]]
    current_player_doubles_count: int
    max_players: int
    lock: asyncio.Lock
    log: List['GameEventPydantic']
    winner: Optional[Color]
    created_at: datetime
    last_activity_at: datetime

    def __init__(self, game_id: uuid.UUID, max_players_limit: int = MAX_PLAYERS) -> None:
        """Initializes a new game aggregate.

        Args:
            game_id: The unique identifier for the game.
            max_players_limit: The maximum number of players allowed.
        """
        from app.models.domain.player import Player

        self.id = game_id
        self.state = GameState.WAITING_PLAYERS
        self.board = Board()
        self.players = {}
        self.turn_order = deque()
        self.current_turn_color = None
        self.dice_roll_count = 0
        self.last_dice_roll = None
        self.current_player_doubles_count = 0
        self.max_players = max_players_limit
        self.lock = asyncio.Lock()
        self.log = []
        self.winner = None

        self.created_at = datetime.now()
        self.last_activity_at = self.created_at

        self._add_game_event("game_created", {"game_id": str(self.id), "max_players": self.max_players})

    def _add_game_event(self, event_type: str, payload: Dict) -> None:
        """Adds an event to the game log.

        Args:
            event_type: The type of event (e.g., "player_joined").
            payload: A dictionary with event-specific data.
        """
        from app.models.schemas import GameEventPydantic
        event = GameEventPydantic(type=event_type, payload=payload)
        self.log.append(event)
        # In a real system, this event could also be emitted via WebSocket.

    def add_player(self, player: 'Player') -> bool:
        """Adds a player to the game.

        Args:
            player: The Player instance to add.

        Returns:
            True if the player was added, False if the game is full, color is taken, or state is not waiting.
        """
        if len(self.players) >= self.max_players:
            return False
        if not isinstance(player.color, Color):
            pass
        if player.color in self.players:
            return False
        if self.state != GameState.WAITING_PLAYERS:
            return False

        self.players[player.color] = player
        self.turn_order.append(player.color)

        if len(self.players) >= MIN_PLAYERS:
            self.state = GameState.READY_TO_START

        # DEBUG lines (commented out by default)
        print(f"DEBUG en add_player: player.user_id='{player.user_id}'")
        print(f"DEBUG en add_player: player.color='{player.color}'")
        print(f"DEBUG en add_player: type(player.color) is {type(player.color)}")
        print(f"DEBUG en add_player: isinstance(player.color, Color) is {isinstance(player.color, Color)}")

        self._add_game_event("player_joined", {"user_id": player.user_id, "color": player.color.value})
        self.last_activity_at = datetime.now()
        return True

    def remove_player(self, color_to_remove: Color) -> bool:
        """Removes a player from the game (e.g., if they disconnect before starting).

        Args:
            color_to_remove: The color of the player to remove.

        Returns:
            True if the player was removed, False otherwise.
        """
        if color_to_remove in self.players:
            removed_player = self.players.pop(color_to_remove)
            if color_to_remove in self.turn_order:
                new_turn_order = deque([c for c in self.turn_order if c != color_to_remove])
                self.turn_order = new_turn_order

            if self.state == GameState.READY_TO_START and len(self.players) < MIN_PLAYERS:
                self.state = GameState.WAITING_PLAYERS

            if self.current_turn_color == color_to_remove and self.state == GameState.IN_PROGRESS:
                self.current_turn_color = None

            self._add_game_event("player_left", {"user_id": removed_player.user_id, "color": removed_player.color.name})
            self.last_activity_at = datetime.now()
            return True
        return False

    def start_game(self) -> bool:
        """Starts the game, determines turn order, and sets the first player.

        Returns:
            True if the game was started, False otherwise.
        """
        if self.state != GameState.READY_TO_START or len(self.players) < MIN_PLAYERS:
            return False
        if not self.turn_order:
            return False

        self.current_turn_color = self.turn_order[0]
        self.state = GameState.IN_PROGRESS
        self.current_player_doubles_count = 0
        if self.current_turn_color and self.players[self.current_turn_color]:
            self.players[self.current_turn_color].reset_consecutive_pairs()

        self._add_game_event("game_started", {"turn_order": [c.name for c in self.turn_order]})
        self.last_activity_at = datetime.now()
        return True

    def next_turn(self) -> None:
        """Advances to the next player in the turn order."""
        if not self.current_turn_color or not self.turn_order:
            return

        self.turn_order.rotate(-1)
        self.current_turn_color = self.turn_order[0]
        self.current_player_doubles_count = 0
        self.last_dice_roll = None
        self.dice_roll_count = 0

        if self.current_turn_color and self.players[self.current_turn_color]:
            self.players[self.current_turn_color].reset_consecutive_pairs()

        self._add_game_event("next_turn", {"player_color": self.current_turn_color.name})
        self.last_activity_at = datetime.now()

    def check_for_winner(self) -> Optional[Color]:
        """Checks if any player has won the game.

        If a winner is found, updates the game state and returns the winner's color.

        Returns:
            The Color of the winning player, or None if there is no winner.
        """
        for color, player in self.players.items():
            if player.check_win_condition():
                self.winner = color
                self.state = GameState.FINISHED
                self._add_game_event("game_finished", {"winner": color.name})
                self.last_activity_at = datetime.now()
                return color
        return None

    def get_player(self, color: Color) -> Optional['Player']:
        """Gets a player by their color.

        Args:
            color: The color of the player.

        Returns:
            The Player instance if found, else None.
        """
        return self.players.get(color)

    def get_current_player(self) -> Optional['Player']:
        """Gets the current player whose turn it is.

        Returns:
            The Player instance if there is a current turn, else None.
        """
        if self.current_turn_color:
            return self.players.get(self.current_turn_color)
        return None