"""Domain model for a Parqués game piece.

Defines the Piece class, representing a single game piece and its state,
including movement, jail status, and safety checks.
"""

import uuid
from typing import Union, Tuple, Optional, Any, TYPE_CHECKING

from app.core.enums import Color, SquareType

if TYPE_CHECKING:
    from app.models.domain.board import Board

SquareId = Union[int, Tuple[str, Optional[Color], Optional[int]]]


class Piece:
    """Represents a single Parqués game piece.

    Attributes:
        id: Unique global identifier for the piece.
        color: The color of the piece.
        position: The current square ID or None if in jail.
        is_in_jail: Whether the piece is currently in jail.
        has_reached_cielo: Whether the piece has reached the final goal.
        squares_advanced_in_path: Number of squares advanced in the final path.
    """

    id: uuid.UUID
    color: Color
    position: Optional[SquareId]
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int

    def __init__(self, piece_id: int, color: Color) -> None:
        """Initializes a new Piece.

        Args:
            piece_id: The player-relative ID of the piece (0-3).
            color: The color assigned to the piece.
        """
        self.id = uuid.uuid4()
        self.piece_player_id = piece_id
        self.color = color
        self.is_in_jail = True
        self.position = None
        self.has_reached_cielo = False
        self.squares_advanced_in_path = 0

    def __repr__(self) -> str:
        """Returns a string representation of the piece."""
        status = "Jail"
        if self.has_reached_cielo:
            status = "Cielo"
        elif self.position is not None:
            status = f"Pos: {self.position}"
        return f"Piece({self.color.name} {self.piece_player_id + 1}, ID: {str(self.id)[:8]}, Status: {status})"

    def move_to(
        self,
        new_position: SquareId,
        is_pasillo: bool = False,
        is_meta: bool = False,
        is_cielo: bool = False,
    ) -> None:
        """Updates the position of the piece.

        Args:
            new_position: The new square ID to move to.
            is_pasillo: Whether the move is into the final passageway.
            is_meta: Whether the move is into the meta square.
            is_cielo: Whether the move is into the final goal (cielo).
        """
        self.position = new_position
        self.is_in_jail = False
        if is_cielo:
            self.has_reached_cielo = True
            self.position = None
            self.squares_advanced_in_path = 7
        elif is_pasillo or is_meta:
            if isinstance(new_position, tuple) and len(new_position) == 3:
                self.squares_advanced_in_path = new_position[2] + 1
        else:
            self.squares_advanced_in_path = 0

    def send_to_jail(self) -> None:
        """Sends the piece to jail, resetting its state."""
        self.is_in_jail = True
        self.position = None
        self.has_reached_cielo = False
        self.squares_advanced_in_path = 0

    def is_currently_safe(self, board: "Board") -> bool:
        """Determines if the piece is currently on a safe square.

        Args:
            board: The game board instance.

        Returns:
            True if the piece is in jail, has reached cielo, or is on a safe square; False otherwise.
        """
        if self.is_in_jail or self.has_reached_cielo:
            return True
        if self.position is None:
            return False

        square = board.get_square(self.position)
        if not square:
            return False

        return square.is_safe_square_for_piece(self.color)