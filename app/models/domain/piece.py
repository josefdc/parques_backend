#app/models/domain/piece.py
import uuid
from typing import Union, Tuple, Optional, Any, TYPE_CHECKING

from app.core.enums import Color, SquareType # Asegúrate que la ruta de importación sea correcta

if TYPE_CHECKING:
    from app.models.domain.board import Board # Si is_safe necesita info del board y sus squares

# SquareId podría ser un alias más formal si lo usas en muchos lugares,
# pero por ahora una anotación de tipo directa está bien.
SquareId = Union[int, Tuple[str, Optional[Color], Optional[int]]]

class Piece:
    """
    Representa una ficha del juego.
    """
    id: uuid.UUID
    color: Color
    position: Optional[SquareId] # La casilla donde se encuentra, None si está en la cárcel inicialmente
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int # Para saber cuántas casillas ha avanzado en su pasillo final

    def __init__(self, piece_id: int, color: Color): # piece_id es un número (0-3) para ese jugador
        self.id = uuid.uuid4() # ID único global para la ficha
        self.piece_player_id = piece_id # ID de la ficha relativo al jugador (ej. ficha 0, 1, 2, 3 del jugador ROJO)
        self.color = color
        self.is_in_jail = True # Todas las fichas comienzan en la cárcel
        self.position = None # No tiene posición en el tablero cuando está en la cárcel
        self.has_reached_cielo = False
        self.squares_advanced_in_path = 0 # Útil para el avance en el pasillo final

    def __repr__(self) -> str:
        status = "Jail"
        if self.has_reached_cielo:
            status = "Cielo"
        elif self.position is not None:
            status = f"Pos: {self.position}"
        
        # Corrección aquí:
        # Simplemente mostraremos el color y el piece_player_id.
        # Si "Cuchara" era un placeholder para algo más, ajusta según sea necesario.
        return f"Piece({self.color.name} {self.piece_player_id + 1}, ID: {str(self.id)[:8]}, Status: {status})"

    def move_to(self, new_position: SquareId, is_pasillo: bool = False, is_meta: bool = False, is_cielo: bool = False):
        """Actualiza la posición de la ficha."""
        self.position = new_position
        self.is_in_jail = False # Si se mueve, ya no está en la cárcel
        if is_cielo:
            self.has_reached_cielo = True
            self.position = None # O una posición especial para 'cielo' si la defines como un Square
            self.squares_advanced_in_path = 7 # Máximo avance en pasillo
        elif is_pasillo or is_meta:
            # Si new_position es una tupla ('pas', color, k) o ('meta', color, k)
            # Necesitamos extraer k para actualizar squares_advanced_in_path
            if isinstance(new_position, tuple) and len(new_position) == 3:
                self.squares_advanced_in_path = new_position[2] + 1 # k es 0-indexed, avance es 1-indexed
            # Si es una meta que no es tupla, podrías tener otra lógica
        else:
            self.squares_advanced_in_path = 0 # Resetea si sale del pasillo

    def send_to_jail(self):
        """Envía la ficha a la cárcel."""
        self.is_in_jail = True
        self.position = None
        self.has_reached_cielo = False # No puede estar en cielo si está en cárcel
        self.squares_advanced_in_path = 0

    # Opción de refactorizar is_safe:
    def is_currently_safe(self, board: 'Board') -> bool:
        """
        Determina si la ficha está en una casilla segura.
        """
        if self.is_in_jail or self.has_reached_cielo:
            return True
        if self.position is None: # No debería pasar si no está en cárcel ni cielo
            return False # O True, dependiendo de la lógica (si no está en el tablero, no puede ser comida)

        square = board.get_square(self.position)
        if not square:
            return False # Posición inválida

        return square.is_safe_square_for_piece(self.color)