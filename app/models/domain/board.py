"""Modelo de dominio para el tablero de Parqués.

Define la clase Board, que representa el tablero, sus casillas,
y la lógica para los recorridos y búsquedas de casillas.
"""
from __future__ import annotations
from typing import List, Dict, Union, Tuple, Optional, TYPE_CHECKING

from app.core.enums import Color, SquareType
from app.models.domain.square import Square, SquareId

if TYPE_CHECKING:
    from app.models.domain.piece import Piece

NUM_MAIN_TRACK_SQUARES = 68
SQUARES_PER_SIDE = 17
PASSAGEWAY_LENGTH = 7
TOTAL_SQUARES_PER_PLAYER_PATH = NUM_MAIN_TRACK_SQUARES + PASSAGEWAY_LENGTH

SALIDA_SQUARES_INDICES = {
    Color.RED: 0,
    Color.GREEN: SQUARES_PER_SIDE,
    Color.BLUE: SQUARES_PER_SIDE * 2,
    Color.YELLOW: SQUARES_PER_SIDE * 3
}

SEGURO_SQUARES_INDICES = [
    0, 6, 12,
    17, 23, 29,
    34, 40, 46,
    51, 57, 63
]

ENTRADA_PASILLO_INDICES = {
    color: (SALIDA_SQUARES_INDICES[color] - 1 + NUM_MAIN_TRACK_SQUARES) % NUM_MAIN_TRACK_SQUARES
    for color in Color
}


class Board:
    """Representa el tablero de Parqués.

    Contiene todas las casillas y define los recorridos de movimiento para cada color.
    """
    squares: Dict[SquareId, Square]
    paths: Dict[Color, List[SquareId]]
    cielo_square_id: SquareId

    def __init__(self) -> None:
        """Inicializa el tablero con todas las casillas y recorridos de los jugadores."""
        self.squares = {}
        self.paths = {}
        self.cielo_square_id = ('cielo', None, 0)
        self._initialize_board()
        self._initialize_paths()

    def _initialize_board(self) -> None:
        """Crea todas las casillas del tablero, incluyendo pista principal, pasillos y cielo."""
        for i in range(NUM_MAIN_TRACK_SQUARES):
            square_id: SquareId = i
            square_type = SquareType.NORMAL
            color_assoc: Optional[Color] = None

            if i in SALIDA_SQUARES_INDICES.values():
                square_type = SquareType.SALIDA
                for color_val, idx in SALIDA_SQUARES_INDICES.items():
                    if idx == i:
                        color_assoc = color_val
                        break
            elif i in ENTRADA_PASILLO_INDICES.values():
                square_type = SquareType.ENTRADA_PASILLO
                for color_val, idx in ENTRADA_PASILLO_INDICES.items():
                    if idx == i:
                        color_assoc = color_val
                        break
            elif i in SEGURO_SQUARES_INDICES:
                square_type = SquareType.SEGURO

            self.squares[square_id] = Square(square_id, square_type, color_assoc)

        for color in Color:
            for k in range(PASSAGEWAY_LENGTH):
                pasillo_id: SquareId = ('pas', color, k)
                pasillo_type = SquareType.META if k == PASSAGEWAY_LENGTH - 1 else SquareType.PASILLO
                self.squares[pasillo_id] = Square(pasillo_id, pasillo_type, color)

        self.squares[self.cielo_square_id] = Square(self.cielo_square_id, SquareType.CIELO)

    def _initialize_paths(self) -> None:
        """Define el recorrido completo de movimiento para cada color."""
        for color in Color:
            path: List[SquareId] = []
            salida_idx = SALIDA_SQUARES_INDICES[color]
            entrada_pasillo_idx = ENTRADA_PASILLO_INDICES[color]

            temp_idx = salida_idx
            while temp_idx != entrada_pasillo_idx:
                path.append(temp_idx)
                temp_idx = (temp_idx + 1) % NUM_MAIN_TRACK_SQUARES
            path.append(entrada_pasillo_idx)

            for k in range(PASSAGEWAY_LENGTH):
                path.append(('pas', color, k))

            path.append(self.cielo_square_id)
            self.paths[color] = path

    def get_square(self, square_id: SquareId) -> Optional[Square]:
        """Obtiene una casilla por su ID.

        Args:
            square_id: ID de la casilla.

        Returns:
            Objeto Square si existe, si no None.
        """
        return self.squares.get(square_id)

    def get_salida_square_id_for_color(self, color: Color) -> int:
        """Obtiene el ID de la casilla de SALIDA para un color.

        Args:
            color: Color del jugador.

        Returns:
            ID entero de la casilla de salida.
        """
        return SALIDA_SQUARES_INDICES[color]

    def get_entrada_pasillo_square_id_for_color(self, color: Color) -> int:
        """Obtiene el ID de la casilla de ENTRADA_PASILLO para un color.

        Args:
            color: Color del jugador.

        Returns:
            ID entero de la casilla de entrada al pasillo.
        """
        return ENTRADA_PASILLO_INDICES[color]

    def get_player_path(self, color: Color) -> List[SquareId]:
        """Obtiene la lista de IDs de casillas que forman el recorrido de un jugador.

        Args:
            color: Color del jugador.

        Returns:
            Lista de SquareId representando el recorrido.
        """
        return self.paths.get(color, [])

    def get_next_square_id_in_path(
        self, current_pos_in_path: SquareId, color: Color, steps: int
    ) -> Optional[SquareId]:
        """Obtiene el ID de la casilla destino dado la posición actual, color y pasos.

        Args:
            current_pos_in_path: Posición actual en el recorrido.
            color: Color del jugador.
            steps: Número de pasos a avanzar.

        Returns:
            SquareId destino, o None si el movimiento es inválido o excede el recorrido.
        """
        player_path = self.get_player_path(color)
        if not player_path:
            return None

        try:
            current_path_index = player_path.index(current_pos_in_path)
        except ValueError:
            return None

        target_path_index = current_path_index + steps

        if target_path_index < len(player_path):
            return player_path[target_path_index]
        else:
            return None

    def _get_main_track_position_after_steps(self, start_square_id: int, steps: int) -> int:
        """Calcula la posición en la pista principal después de avanzar ciertos pasos.

        Args:
            start_square_id: ID de la casilla inicial (int).
            steps: Número de pasos a avanzar.

        Returns:
            ID de la casilla resultante.
        """
        return (start_square_id + steps) % NUM_MAIN_TRACK_SQUARES

    def advance_piece_logic(
        self, current_square_id: SquareId, steps: int, piece_color: Color
    ) -> Optional[SquareId]:
        """Lógica principal para avanzar una ficha en el tablero.

        Determina la casilla destino dada la casilla actual, pasos y color de la ficha.
        Retorna None si el movimiento excede la meta o es inválido.

        Args:
            current_square_id: Casilla actual de la ficha.
            steps: Pasos a avanzar.
            piece_color: Color de la ficha.

        Returns:
            SquareId destino, o None si el movimiento es inválido.
        """
        if current_square_id is None:
            return None

        current_square_object = self.get_square(current_square_id)
        if not current_square_object:
            return None

        if isinstance(current_square_id, int):
            entrada_pasillo_propia = ENTRADA_PASILLO_INDICES[piece_color]
            pos_actual_pista = current_square_id
            
            for i in range(1, steps + 1):
                next_pos_pista = (pos_actual_pista + 1) % NUM_MAIN_TRACK_SQUARES
                if next_pos_pista == entrada_pasillo_propia:
                    pasos_restantes = steps - i
                    if pasos_restantes >= 0:
                        if pasos_restantes == 0:
                            return ('pas', piece_color, 0)
                        else:
                            if pasos_restantes <= PASSAGEWAY_LENGTH:
                                return ('pas', piece_color, pasos_restantes - 1)
                            else:
                                return None 
                pos_actual_pista = next_pos_pista
            
            return pos_actual_pista

        elif isinstance(current_square_id, tuple) and current_square_id[0] == 'pas':
            _, pasillo_color, k = current_square_id
            
            if pasillo_color != piece_color:
                return None 

            target_k = k + steps
            
            if target_k < PASSAGEWAY_LENGTH:
                return ('pas', piece_color, target_k)
            elif target_k == PASSAGEWAY_LENGTH:
                return self.cielo_square_id
            else:
                return None
        
        elif current_square_id == self.cielo_square_id:
            return None

        return None