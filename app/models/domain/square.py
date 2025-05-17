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
    """
    Representa una casilla en el tablero de Parqués.

    Atributos:
        id: Identificador único de la casilla.
        type: Tipo de la casilla (NORMAL, SEGURO, SALIDA, etc).
        occupants: Lista de fichas actualmente en esta casilla.
        color_association: Color asociado a la casilla, si aplica.
    """
    id: SquareId
    type: SquareType
    occupants: List['Piece']
    color_association: Optional[Color]

    def __init__(self, square_id: SquareId, square_type: SquareType, color_association: Optional[Color] = None) -> None:
        """
        Inicializa una nueva casilla.

        Args:
            square_id: Identificador único de la casilla.
            square_type: Tipo de la casilla.
            color_association: Color asociado a la casilla, si aplica.
        """
        self.id = square_id
        self.type = square_type
        self.occupants = []
        self.color_association = color_association

    def __repr__(self) -> str:
        """
        Retorna una representación en cadena de la casilla.
        """
        occupant_details = []
        for occ in self.occupants:
            detail = f"{occ.color.name}{occ.piece_player_id + 1}"
            occupant_details.append(detail)
        return (f"Square(ID: {self.id}, Type: {self.type.name}, "
                f"ColorAssoc: {self.color_association.name if self.color_association else 'N/A'}, "
                f"Occupants: [{', '.join(occupant_details)}])")

    def add_piece(self, piece: 'Piece') -> None:
        """
        Agrega una ficha a la casilla y actualiza su posición.

        Args:
            piece: La ficha a agregar.
        """
        if piece not in self.occupants:
            self.occupants.append(piece)
            piece.position = self.id

    def remove_piece(self, piece: 'Piece') -> None:
        """
        Remueve una ficha de la casilla.

        Args:
            piece: La ficha a remover.
        """
        if piece in self.occupants:
            self.occupants.remove(piece)
            # La posición de la ficha puede limpiarse si es enviada a la cárcel en otro lugar.

    def is_occupied(self) -> bool:
        """
        Verifica si la casilla está ocupada por alguna ficha.

        Returns:
            True si hay al menos una ficha, False en caso contrario.
        """
        return len(self.occupants) > 0

    def is_occupied_by_color(self, color: Color) -> bool:
        """
        Verifica si la casilla está ocupada por alguna ficha de un color específico.

        Args:
            color: Color a verificar.

        Returns:
            True si alguna ficha coincide con el color, False en caso contrario.
        """
        return any(occupant.color == color for occupant in self.occupants)

    def get_occupying_pieces_by_color(self, color: Color) -> List['Piece']:
        """
        Obtiene todas las fichas de un color específico que ocupan la casilla.

        Args:
            color: Color por el cual filtrar.

        Returns:
            Lista de fichas que coinciden con el color.
        """
        return [occupant for occupant in self.occupants if occupant.color == color]

    def get_other_color_pieces(self, color: Color) -> List['Piece']:
        """
        Obtiene todas las fichas de colores diferentes al especificado.

        Args:
            color: Color a excluir.

        Returns:
            Lista de fichas que no coinciden con el color.
        """
        return [occupant for occupant in self.occupants if occupant.color != color]

    def is_forming_wall(self) -> Optional[Color]:
        """
        Verifica si la casilla forma una barrera (dos o más fichas del mismo color).

        Returns:
            El color que forma la barrera si existe, si no None.
        """
        if len(self.occupants) >= 2:
            first_piece_color = self.occupants[0].color
            if all(p.color == first_piece_color for p in self.occupants):
                return first_piece_color
        return None

    def is_safe_square_for_piece(self, piece_color: Color) -> bool:
        """
        Determina si esta casilla es intrínsecamente segura para una ficha de un color dado.

        No considera la presencia de otras fichas.

        Args:
            piece_color: Color de la ficha a verificar.

        Returns:
            True si la casilla es segura para la ficha, False en caso contrario.
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