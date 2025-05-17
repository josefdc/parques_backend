"""Modelo de dominio para una ficha del juego Parqués.

Define la clase Piece, que representa una sola ficha del juego y su estado,
incluyendo movimiento, estado en la cárcel y verificaciones de seguridad.
"""

import uuid
from typing import Union, Tuple, Optional, Any, TYPE_CHECKING

from app.core.enums import Color, SquareType

if TYPE_CHECKING:
    from app.models.domain.board import Board

SquareId = Union[int, Tuple[str, Optional[Color], Optional[int]]]


class Piece:
    """
    Representa una sola ficha del juego de Parqués.

    Atributos:
        id: Identificador global único para la ficha.
        color: El color de la ficha.
        position: El ID de la casilla actual o None si está en la cárcel.
        is_in_jail: Indica si la ficha está en la cárcel.
        has_reached_cielo: Indica si la ficha ha llegado al cielo.
        squares_advanced_in_path: Número de casillas avanzadas en el pasillo final.
    """

    id: uuid.UUID
    color: Color
    position: Optional[SquareId]
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int

    def __init__(self, piece_id: int, color: Color) -> None:
        """
        Inicializa una nueva ficha.

        Args:
            piece_id: ID relativo al jugador de la ficha (0-3).
            color: Color asignado a la ficha.
        """
        self.id = uuid.uuid4()
        self.piece_player_id = piece_id
        self.color = color
        self.is_in_jail = True
        self.position = None
        self.has_reached_cielo = False
        self.squares_advanced_in_path = 0

    def __repr__(self) -> str:
        """
        Retorna una representación en cadena de la ficha.
        """
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
        """
        Actualiza la posición de la ficha.

        Args:
            new_position: Nueva casilla a la que se mueve la ficha.
            is_pasillo: Indica si el movimiento es hacia el pasillo final.
            is_meta: Indica si el movimiento es hacia la meta.
            is_cielo: Indica si el movimiento es hacia el cielo.
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
        """
        Envía la ficha a la cárcel y reinicia su estado.
        """
        self.is_in_jail = True
        self.position = None
        self.has_reached_cielo = False
        self.squares_advanced_in_path = 0

    def is_currently_safe(self, board: "Board") -> bool:
        """
        Determina si la ficha está actualmente en una casilla segura.

        Args:
            board: Instancia del tablero de juego.

        Returns:
            True si la ficha está en la cárcel, ha llegado al cielo o está en una casilla segura; False en caso contrario.
        """
        if self.is_in_jail or self.has_reached_cielo:
            return True
        if self.position is None:
            return False

        square = board.get_square(self.position)
        if not square:
            return False

        return square.is_safe_square_for_piece(self.color)