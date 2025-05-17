#app/models/domain/piece.py
"""Domain model for a Parqués game player.

Defines the Player class, representing a player and their pieces,
including methods for piece management and win condition checks.
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Union

from app.core.enums import Color

if TYPE_CHECKING:
    from app.models.domain.piece import Piece

# Número estándar de fichas por jugador en Parqués
PIECES_PER_PLAYER = 4

class Player:
    """Represents a player in a Parqués game.

    Attributes:
        user_id: Unique identifier for the user (e.g., session ID, username).
        color: The color assigned to the player.
        pieces: List of the player's pieces.
        has_won: Whether the player has won the game.
        consecutive_pairs_count: Counter for consecutive pairs rolled by the player.
    """
    user_id: str # Identificador único del usuario (puede ser un ID de sesión, nombre, etc.)
    color: Color
    pieces: List['Piece']
    has_won: bool
    consecutive_pairs_count: int

    def __init__(self, user_id: str, color_input: Union[Color, str]) -> None:
        """Initializes a new Player.

        Args:
            user_id: The unique identifier for the user.
            color_input: The color assigned to the player (Color or str).

        Raises:
            ValueError: If the color string is invalid.
            TypeError: If color_input is not a Color or str.
        """
        from app.models.domain.piece import Piece # Importación local para evitar problemas de carga inicial

        self.user_id = user_id

        if isinstance(color_input, str):
            try:
                self.color = Color[color_input.upper()]
            except KeyError:
                raise ValueError(f"Color inválido '{color_input}' para el jugador '{user_id}'.")
        elif isinstance(color_input, Color):
            self.color = color_input
        else:
            raise TypeError(f"Tipo inválido para el color del jugador: se esperaba Color o str, se obtuvo {type(color_input)}")

        self.pieces = [Piece(piece_id=i, color=self.color) for i in range(PIECES_PER_PLAYER)]
        self.has_won = False
        self.consecutive_pairs_count = 0

    def __repr__(self) -> str:
        """Returns a string representation of the player."""
        return f"Player(UserID: {self.user_id}, Color: {self.color.name}, Pieces in Jail: {self.get_jailed_pieces_count()})"

    def get_jailed_pieces(self) -> List['Piece']:
        """Returns a list of the player's pieces that are currently in jail."""
        return [piece for piece in self.pieces if piece.is_in_jail]

    def get_jailed_pieces_count(self) -> int:
        """Returns the number of the player's pieces that are currently in jail."""
        return len(self.get_jailed_pieces())

    def get_pieces_in_play(self) -> List['Piece']:
        """Returns a list of the player's pieces that are on the board (not in jail or cielo)."""
        return [
            piece for piece in self.pieces if not piece.is_in_jail and not piece.has_reached_cielo
        ]

    def get_pieces_in_cielo_count(self) -> int:
        """Returns the number of the player's pieces that have reached cielo."""
        return sum(1 for piece in self.pieces if piece.has_reached_cielo)

    def check_win_condition(self) -> bool:
        """Checks if the player has won (all pieces in cielo).

        Returns:
            True if the player has won, False otherwise.
        """
        if self.get_pieces_in_cielo_count() == PIECES_PER_PLAYER:
            self.has_won = True
            return True
        return False

    def get_piece_by_id(self, piece_internal_id: int) -> Optional['Piece']:
        """Gets a specific piece by its internal player-relative ID (0 to PIECES_PER_PLAYER - 1).

        Args:
            piece_internal_id: The internal ID of the piece.

        Returns:
            The Piece instance if found, else None.
        """
        if 0 <= piece_internal_id < len(self.pieces):
            for piece in self.pieces:
                if piece.piece_player_id == piece_internal_id:
                    return piece
        return None

    def get_piece_by_uuid(self, piece_uuid_str: str) -> Optional['Piece']:
        """Gets a specific piece by its global UUID.

        Args:
            piece_uuid_str: The UUID string of the piece.

        Returns:
            The Piece instance if found, else None.
        """
        try:
            import uuid
            target_uuid = uuid.UUID(piece_uuid_str)
            for piece in self.pieces:
                if piece.id == target_uuid:
                    return piece
        except ValueError:
            return None
        return None

    def reset_consecutive_pairs(self) -> None:
        """Resets the consecutive pairs counter."""
        self.consecutive_pairs_count = 0

    def increment_consecutive_pairs(self) -> None:
        """Increments the consecutive pairs counter."""
        self.consecutive_pairs_count += 1