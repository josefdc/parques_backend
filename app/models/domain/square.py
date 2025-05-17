"""Domain model for a Parqués game board.

Defines the Square class, representing a board square, its type, occupants,
and utility methods for game logic such as safety and wall detection.
"""
from __future__ import annotations
from typing import List, Union, Tuple, Optional, TYPE_CHECKING

from app.core.enums import SquareType, Color

if TYPE_CHECKING:
    from app.models.domain.piece import Piece

SquareId = Union[int, Tuple[str, Optional[Color], Optional[int]]]

class Square:
    """Represents a square on the Parqués game board.

    Attributes:
        id: The unique identifier of the square.
        type: The type of the square (e.g., NORMAL, SEGURO, SALIDA).
        occupants: List of pieces currently on this square.
        color_association: The color associated with this square, if any.
    """
    id: SquareId
    type: SquareType
    occupants: List['Piece']
    color_association: Optional[Color]

    def __init__(self, square_id: SquareId, square_type: SquareType, color_association: Optional[Color] = None) -> None:
        """Initializes a new Square.

        Args:
            square_id: The unique identifier for the square.
            square_type: The type of the square.
            color_association: The color associated with the square, if any.
        """
        self.id = square_id
        self.type = square_type
        self.occupants = []
        self.color_association = color_association

    def __repr__(self) -> str:
        """Returns a string representation of the square."""
        occupant_details = []
        for occ in self.occupants:
            detail = f"{occ.color.name}{occ.piece_player_id + 1}"
            occupant_details.append(detail)
        return (f"Square(ID: {self.id}, Type: {self.type.name}, "
                f"ColorAssoc: {self.color_association.name if self.color_association else 'N/A'}, "
                f"Occupants: [{', '.join(occupant_details)}])")

    def add_piece(self, piece: 'Piece') -> None:
        """Adds a piece to the square and updates its position.

        Args:
            piece: The Piece to add.
        """
        if piece not in self.occupants:
            self.occupants.append(piece)
            piece.position = self.id

    def remove_piece(self, piece: 'Piece') -> None:
        """Removes a piece from the square.

        Args:
            piece: The Piece to remove.
        """
        if piece in self.occupants:
            self.occupants.remove(piece)
            # Optionally, clear piece.position if sent to jail elsewhere.

    def is_occupied(self) -> bool:
        """Checks if the square is occupied by any piece.

        Returns:
            True if there is at least one occupant, False otherwise.
        """
        return len(self.occupants) > 0

    def is_occupied_by_color(self, color: Color) -> bool:
        """Checks if the square is occupied by any piece of a specific color.

        Args:
            color: The color to check.

        Returns:
            True if any occupant matches the color, False otherwise.
        """
        return any(occupant.color == color for occupant in self.occupants)

    def get_occupying_pieces_by_color(self, color: Color) -> List['Piece']:
        """Gets all pieces of a specific color occupying the square.

        Args:
            color: The color to filter by.

        Returns:
            List of Piece instances matching the color.
        """
        return [occupant for occupant in self.occupants if occupant.color == color]

    def get_other_color_pieces(self, color: Color) -> List['Piece']:
        """Gets all pieces of colors different from the specified one.

        Args:
            color: The color to exclude.

        Returns:
            List of Piece instances not matching the color.
        """
        return [occupant for occupant in self.occupants if occupant.color != color]

    def is_forming_wall(self) -> Optional[Color]:
        """Checks if the square forms a wall (barrier) of two or more pieces of the same color.

        Returns:
            The color forming the wall if present, else None.
        """
        if len(self.occupants) >= 2:
            first_piece_color = self.occupants[0].color
            if all(p.color == first_piece_color for p in self.occupants):
                return first_piece_color
        return None

    def is_safe_square_for_piece(self, piece_color: Color) -> bool:
        """Determines if this square is intrinsically safe for a piece of a given color.

        Does not consider the presence of other pieces.

        Args:
            piece_color: The color of the piece to check safety for.

        Returns:
            True if the square is safe for the piece, False otherwise.
        """
        if self.type == SquareType.SEGURO:
            return True
        if self.type == SquareType.SALIDA and self.color_association == piece_color:
            return True
        if self.type in [SquareType.PASILLO, SquareType.ENTRADA_PASILLO, SquareType.META] and \
           self.color_association == piece_color:
            return True
        if self.type == SquareType.CIELO:
            return True
        return False