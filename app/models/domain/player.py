#app/models/domain/piece.py
"""Modelo de dominio para un jugador de Parqués.

Define la clase Player, que representa a un jugador y sus fichas,
incluyendo métodos para la gestión de fichas y verificación de condiciones de victoria.
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Union

from app.core.enums import Color

if TYPE_CHECKING:
    from app.models.domain.piece import Piece

# Número estándar de fichas por jugador en Parqués
PIECES_PER_PLAYER = 4

class Player:
    """
    Representa un jugador en una partida de Parqués.

    Atributos:
        user_id: Identificador único del usuario.
        color: Color asignado al jugador.
        pieces: Lista de fichas del jugador.
        has_won: Indica si el jugador ha ganado la partida.
        consecutive_pairs_count: Contador de pares consecutivos lanzados por el jugador.
    """
    user_id: str
    color: Color
    pieces: List['Piece']
    has_won: bool
    consecutive_pairs_count: int

    def __init__(self, user_id: str, color_input: Union[Color, str]) -> None:
        """
        Inicializa un nuevo jugador.

        Args:
            user_id: Identificador único del usuario.
            color_input: Color asignado al jugador (Color o str).

        Raises:
            ValueError: Si el color es inválido.
            TypeError: Si color_input no es Color ni str.
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
        """
        Retorna una representación en cadena del jugador.
        """
        return f"Player(UserID: {self.user_id}, Color: {self.color.name}, Pieces in Jail: {self.get_jailed_pieces_count()})"

    def get_jailed_pieces(self) -> List['Piece']:
        """
        Retorna una lista de las fichas del jugador que están en la cárcel.
        """
        return [piece for piece in self.pieces if piece.is_in_jail]

    def get_jailed_pieces_count(self) -> int:
        """
        Retorna el número de fichas del jugador que están en la cárcel.
        """
        return len(self.get_jailed_pieces())

    def get_pieces_in_play(self) -> List['Piece']:
        """
        Retorna una lista de las fichas del jugador que están en juego (no en la cárcel ni en cielo).
        """
        return [
            piece for piece in self.pieces if not piece.is_in_jail and not piece.has_reached_cielo
        ]

    def get_pieces_in_cielo_count(self) -> int:
        """
        Retorna el número de fichas del jugador que han llegado al cielo.
        """
        return sum(1 for piece in self.pieces if piece.has_reached_cielo)

    def check_win_condition(self) -> bool:
        """
        Verifica si el jugador ha ganado (todas las fichas en cielo).

        Returns:
            True si el jugador ha ganado, False en caso contrario.
        """
        if self.get_pieces_in_cielo_count() == PIECES_PER_PLAYER:
            self.has_won = True
            return True
        return False

    def get_piece_by_id(self, piece_internal_id: int) -> Optional['Piece']:
        """
        Obtiene una ficha específica por su ID interno relativo al jugador (0 a PIECES_PER_PLAYER - 1).

        Args:
            piece_internal_id: ID interno de la ficha.

        Returns:
            La instancia de Piece si se encuentra, si no None.
        """
        if 0 <= piece_internal_id < len(self.pieces):
            for piece in self.pieces:
                if piece.piece_player_id == piece_internal_id:
                    return piece
        return None

    def get_piece_by_uuid(self, piece_uuid_str: str) -> Optional['Piece']:
        """
        Obtiene una ficha específica por su UUID global.

        Args:
            piece_uuid_str: UUID de la ficha.

        Returns:
            La instancia de Piece si se encuentra, si no None.
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
        """
        Reinicia el contador de pares consecutivos.
        """
        self.consecutive_pairs_count = 0

    def increment_consecutive_pairs(self) -> None:
        """
        Incrementa el contador de pares consecutivos.
        """
        self.consecutive_pairs_count += 1