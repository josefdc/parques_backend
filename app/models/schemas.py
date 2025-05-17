"""Pydantic schemas for API request and response models, and internal data structures.

This module defines the data structures used for validating API inputs,
serializing API outputs, and representing game entities like players, pieces,
and the game board state.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Union, Tuple, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.enums import Color, GameState, SquareType, MoveResultType

# --- Modelos Base para la API ---

class TunedModel(BaseModel):
    """Base Pydantic model with common configuration.

    Enables ORM mode (from_attributes) and serializes enums to their values.
    """
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )

# --- Esquemas para Información de Jugadores y Fichas ---

class PieceInfo(TunedModel):
    """Public information about a game piece.

    Attributes:
        id: The global unique identifier of the piece.
        piece_player_id: The player-specific ID of the piece (e.g., 0-3).
        color: The color of the piece.
        position: The current square ID where the piece is located.
                  Can be an integer or a tuple for special squares.
        is_in_jail: Whether the piece is currently in jail.
        has_reached_cielo: Whether the piece has reached the final goal (cielo).
        squares_advanced_in_path: Number of squares the piece has advanced on its main path.
    """
    id: UUID
    piece_player_id: int
    color: Color
    position: Optional[Union[int, Tuple[str, Optional[Color], Optional[int]]]]
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int

class PlayerInfo(TunedModel):
    """Public information about a player in the game.

    Attributes:
        user_id: The unique identifier of the user.
        color: The color assigned to the player.
        pieces: A list of the player's pieces.
        is_current_turn: Flag indicating if it is currently this player's turn.
        consecutive_pairs_count: Count of consecutive pairs rolled by the player in their current turn.
    """
    user_id: str
    color: Color
    pieces: List[PieceInfo]
    is_current_turn: bool = False
    consecutive_pairs_count: int

# --- Esquemas para Información del Tablero ---

class SquareInfo(TunedModel):
    """Public information about a square on the game board.

    Attributes:
        id: The unique identifier of the square.
        type: The type of the square (e.g., NORMAL, SEGURO, SALIDA).
        occupants: A list of pieces currently occupying this square.
        color_association: The color associated with this square, if any (e.g., for home rows, salida).
    """
    id: Union[int, Tuple[str, Optional[Color], Optional[int]]]
    type: SquareType
    occupants: List[PieceInfo]
    color_association: Optional[Color]

# --- Esquemas para Solicitudes (Requests) de la API ---

class CreateGameRequest(TunedModel):
    """Schema for a request to create a new game."""
    max_players: int = Field(default=4, ge=2, le=8)
    creator_user_id: str = Field(..., min_length=1, description="ID of the user creating the game")
    creator_color: Color = Field(..., description="Color chosen by the creator (e.g., 'RED', 'GREEN', 0, 1)")

    @field_validator('creator_color', mode='before')
    @classmethod
    def validate_creator_color(cls, v: Any) -> Color:
        """Validates and converts the creator_color field.

        Accepts Color enum members, color name strings (case-insensitive),
        or integers (0: RED, 1: GREEN, 2: BLUE, 3: YELLOW).

        Args:
            v: The input value for creator_color.

        Returns:
            A valid Color enum member.

        Raises:
            ValueError: If the input color string or integer is invalid.
            TypeError: If the input type is not str, int, or Color.
        """
        if isinstance(v, Color):
            return v
        if isinstance(v, str):
            try:
                return Color(v.upper())
            except ValueError:
                valid_colors_str = [e.value for e in Color]
                raise ValueError(f"Invalid color string: '{v}'. Must be one of {valid_colors_str} or a valid integer (0-3).")
        if isinstance(v, int):
            try:
                if v == 0: return Color.RED
                if v == 1: return Color.GREEN
                if v == 2: return Color.BLUE
                if v == 3: return Color.YELLOW
                raise ValueError(f"Invalid integer for color: {v}. Must be 0-3.")
            except ValueError as e:
                 raise ValueError(str(e)) from e
        raise TypeError(f"Invalid type for Color: {type(v)}. Expected string, int, or Color enum member.")

class JoinGameRequest(TunedModel):
    """Schema for a request to join an existing game."""
    user_id: str = Field(..., min_length=1, description="ID of the user joining the game")
    color: Color = Field(..., description="Color requested by the user (e.g., 'RED', 'GREEN', 0, 1)")

    @field_validator('color', mode='before')
    @classmethod
    def validate_join_color(cls, v: Any) -> Color:
        """Validates and converts the color field for a join request.

        Accepts Color enum members, color name strings (case-insensitive),
        or integers (0: RED, 1: GREEN, 2: BLUE, 3: YELLOW).

        Args:
            v: The input value for the color.

        Returns:
            A valid Color enum member.

        Raises:
            ValueError: If the input color string or integer is invalid.
            TypeError: If the input type is not str, int, or Color.
        """
        if isinstance(v, Color):
            return v
        if isinstance(v, str):
            try:
                return Color(v.upper())
            except ValueError:
                valid_colors_str = [e.value for e in Color]
                raise ValueError(f"Invalid color string: '{v}'. Must be one of {valid_colors_str} or a valid integer (0-3).")
        if isinstance(v, int):
            try:
                if v == 0: return Color.RED
                if v == 1: return Color.GREEN
                if v == 2: return Color.BLUE
                if v == 3: return Color.YELLOW
                raise ValueError(f"Invalid integer for color: {v}. Must be 0-3.")
            except ValueError as e:
                raise ValueError(str(e)) from e
        raise TypeError(f"Invalid type for Color: {type(v)}. Expected string, int, or Color enum member.")

class MovePieceRequest(TunedModel):
    """Schema for a request to move a piece.

    The `user_id` is typically obtained from authentication (e.g., token/session).
    The `game_id` is part of the URL path.

    Attributes:
        piece_uuid: UUID of the piece to be moved.
        target_square_id: The destination square ID for the move.
        steps_used: The dice roll value (d1, d2, or d1+d2) used for this specific move.
    """
    piece_uuid: UUID
    target_square_id: Union[int, Tuple[str, Optional[Color], Optional[int]]]
    steps_used: int

class BurnPieceRequest(TunedModel):
    """Schema for a request to burn a piece after rolling three pairs.

    If `piece_uuid` is not provided, the server may automatically choose a piece
    to burn based on game rules.

    Attributes:
        piece_uuid: Optional UUID of the piece the player chooses to burn.
    """
    piece_uuid: Optional[UUID] = None

# --- Esquemas para Respuestas (Responses) de la API ---

class GameInfo(TunedModel):
    """Basic information about a game.

    Used for listings (e.g., in a lobby) or after creating/joining a game.

    Attributes:
        id: Unique identifier of the game.
        state: Current state of the game (e.g., WAITING_PLAYERS, IN_PROGRESS).
        max_players: Maximum number of players allowed in the game.
        current_player_count: Current number of players in the game.
        players: List of players in the game.
        created_at: Timestamp of when the game was created.
    """
    id: UUID
    state: GameState
    max_players: int
    current_player_count: int
    players: List[PlayerInfo]
    created_at: datetime

class DiceRollResponse(TunedModel):
    """Schema for the response after a dice roll.

    Attributes:
        dice1: Value of the first die.
        dice2: Value of the second die.
        is_pairs: Boolean indicating if the roll was a pair.
        roll_validation_result: Result of validating the roll (e.g., THREE_PAIRS_BURN, OK).
        possible_moves: A dictionary mapping piece UUIDs to a list of possible moves.
                        Each move is a tuple: (target_square_id, move_result_type, steps_used).
    """
    dice1: int
    dice2: int
    is_pairs: bool
    roll_validation_result: MoveResultType
    possible_moves: Dict[str, List[Tuple[Union[int, Tuple[str, Optional[Color], Optional[int]]], MoveResultType, int]]]

class MoveOutcome(TunedModel):
    """Schema for the outcome of a piece movement or burning action.

    Attributes:
        success: Boolean indicating if the action was successful.
        message: A descriptive message about the outcome.
        move_result_type: The specific result type of the move, if applicable.
    """
    success: bool
    message: str
    move_result_type: Optional[MoveResultType] = None

class GameSnapshot(TunedModel):
    """Comprehensive representation of the current game state.

    Intended for clients to render the game.

    Attributes:
        game_id: Unique identifier of the game.
        state: Current state of the game.
        board: List of all squares on the board with their occupants.
        players: Detailed information for all players in the game.
        turn_order: Current order of player turns by color.
        current_turn_color: Color of the player whose turn it currently is.
        current_player_doubles_count: Game's count of consecutive doubles for the current player's turn.
        last_dice_roll: The dice values from the last roll in the current turn, if any.
        winner: The color of the winning player, if the game has finished.
    """
    game_id: UUID
    state: GameState
    board: List[SquareInfo]
    players: List[PlayerInfo]
    turn_order: List[Color]
    current_turn_color: Optional[Color]
    current_player_doubles_count: int
    last_dice_roll: Optional[Tuple[int, int]] = None
    winner: Optional[Color] = None

# --- Esquema para Eventos del Juego (usado en GameAggregate y WebSockets) ---

class GameEventPydantic(TunedModel):
    """Pydantic model for game events.

    Used for logging within GameAggregate and for sending updates via WebSockets.

    Attributes:
        ts: Timestamp of when the event occurred.
        type: String identifying the type of event (e.g., "dice_rolled", "piece_moved").
        payload: Dictionary containing event-specific data.
    """
    ts: datetime = Field(default_factory=datetime.now)
    type: str
    payload: Dict[str, Any]