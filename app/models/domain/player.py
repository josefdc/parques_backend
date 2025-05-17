from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional

from app.core.enums import Color

if TYPE_CHECKING:
    from app.models.domain.piece import Piece # Forward reference para la clase Piece

# Número estándar de fichas por jugador en Parqués
PIECES_PER_PLAYER = 4

class Player:
    """
    Representa un jugador en la partida de Parqués.
    """
    user_id: str # Identificador único del usuario (puede ser un ID de sesión, nombre, etc.)
    color: Color
    pieces: List[Piece]
    has_won: bool
    # Atributo para manejar si el jugador ha lanzado tres pares seguidos.
    # Se resetea cuando el jugador pierde el turno o mueve una ficha quemada.
    consecutive_pairs_count: int

    def __init__(self, user_id: str, color: Color):
        from app.models.domain.piece import Piece # Importación local para evitar problemas de carga inicial

        self.user_id = user_id
        self.color = color
        self.pieces = [Piece(piece_id=i, color=self.color) for i in range(PIECES_PER_PLAYER)]
        self.has_won = False
        self.consecutive_pairs_count = 0

    def __repr__(self) -> str:
        return f"Player(UserID: {self.user_id}, Color: {self.color.name}, Pieces in Jail: {self.get_jailed_pieces_count()})"

    def get_jailed_pieces(self) -> List[Piece]:
        """Devuelve una lista de las fichas del jugador que están en la cárcel."""
        return [piece for piece in self.pieces if piece.is_in_jail]

    def get_jailed_pieces_count(self) -> int:
        """Devuelve el número de fichas del jugador que están en la cárcel."""
        return len(self.get_jailed_pieces())

    def get_pieces_in_play(self) -> List[Piece]:
        """Devuelve una lista de las fichas del jugador que están en el tablero (no en cárcel, no en cielo)."""
        return [
            piece for piece in self.pieces if not piece.is_in_jail and not piece.has_reached_cielo
        ]

    def get_pieces_in_cielo_count(self) -> int:
        """Devuelve el número de fichas del jugador que han llegado al cielo."""
        return sum(1 for piece in self.pieces if piece.has_reached_cielo)

    def check_win_condition(self) -> bool:
        """Verifica si el jugador ha ganado (todas sus fichas en el cielo)."""
        if self.get_pieces_in_cielo_count() == PIECES_PER_PLAYER:
            self.has_won = True
            return True
        return False

    def get_piece_by_id(self, piece_internal_id: int) -> Optional[Piece]:
        """
        Obtiene una ficha específica del jugador por su ID interno (0 a PIECES_PER_PLAYER - 1).
        """
        if 0 <= piece_internal_id < len(self.pieces):
            # Buscar la pieza que coincida con el piece_player_id
            for piece in self.pieces:
                if piece.piece_player_id == piece_internal_id:
                    return piece
        return None
        
    def get_piece_by_uuid(self, piece_uuid_str: str) -> Optional[Piece]:
        """
        Obtiene una ficha específica del jugador por su UUID global.
        """
        try:
            import uuid
            target_uuid = uuid.UUID(piece_uuid_str)
            for piece in self.pieces:
                if piece.id == target_uuid:
                    return piece
        except ValueError: # Si piece_uuid_str no es un UUID válido
            return None
        return None

    def reset_consecutive_pairs(self):
        """Resetea el contador de pares consecutivos."""
        self.consecutive_pairs_count = 0

    def increment_consecutive_pairs(self):
        """Incrementa el contador de pares consecutivos."""
        self.consecutive_pairs_count += 1