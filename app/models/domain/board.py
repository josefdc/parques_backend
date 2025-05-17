"""Domain model for the Parqués game board.

Defines the Board class, which represents the game board, its squares,
and the logic for player movement paths and square lookups.
"""
from __future__ import annotations
from typing import List, Dict, Union, Tuple, Optional, TYPE_CHECKING

from app.core.enums import Color, SquareType
from app.models.domain.square import Square, SquareId

if TYPE_CHECKING:
    from app.models.domain.piece import Piece

# Constantes del tablero para 4 jugadores según tu documento
NUM_MAIN_TRACK_SQUARES = 68
SQUARES_PER_SIDE = 17 # 68 / 4
PASSAGEWAY_LENGTH = 7 # 0 a 6
TOTAL_SQUARES_PER_PLAYER_PATH = NUM_MAIN_TRACK_SQUARES + PASSAGEWAY_LENGTH # Recorrido completo

# Definición de casillas especiales (índices en la pista principal)
# Los colores se asignan en orden: RED, GREEN, BLUE, YELLOW
SALIDA_SQUARES_INDICES = {
    Color.RED: 0,
    Color.GREEN: SQUARES_PER_SIDE,           # 17
    Color.BLUE: SQUARES_PER_SIDE * 2,        # 34
    Color.YELLOW: SQUARES_PER_SIDE * 3       # 51
}

SEGURO_SQUARES_INDICES = [
    0, 6, 12,                 # Lado Rojo
    17, 17 + 6, 17 + 12,      # Lado Verde (17, 23, 29)
    34, 34 + 6, 34 + 12,      # Lado Azul (34, 40, 46)
    51, 51 + 6, 51 + 12       # Lado Amarillo (51, 57, 63)
] # Total 12 seguros

# La entrada al pasillo es la casilla ANTERIOR a la casilla de SALIDA
ENTRADA_PASILLO_INDICES = {
    color: (SALIDA_SQUARES_INDICES[color] - 1 + NUM_MAIN_TRACK_SQUARES) % NUM_MAIN_TRACK_SQUARES
    for color in Color
}


class Board:
    """Represents the Parqués game board.

    Contains all squares and defines the movement paths for each player color.
    """
    squares: Dict[SquareId, Square]
    paths: Dict[Color, List[SquareId]]
    cielo_square_id: SquareId

    def __init__(self) -> None:
        """Initializes the board with all squares and player paths."""
        self.squares = {}
        self.paths = {}
        self.cielo_square_id = ('cielo', None, 0)
        self._initialize_board()
        self._initialize_paths()

    def _initialize_board(self) -> None:
        """Creates all squares on the board, including main track, passages, and cielo."""
        # 1. Casillas de la pista principal (normales, salidas, seguros, entradas a pasillo)
        for i in range(NUM_MAIN_TRACK_SQUARES):
            square_id: SquareId = i
            square_type = SquareType.NORMAL
            color_assoc: Optional[Color] = None

            # Determinar si es una casilla especial
            if i in SALIDA_SQUARES_INDICES.values():
                square_type = SquareType.SALIDA
                # Encontrar a qué color pertenece esta salida
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
                # Las casillas de SALIDA también son SEGURO, por eso SEGURO va después en la lógica.
                # Opcionalmente, una casilla de SALIDA podría no ser SEGURO si las reglas lo dictan.
                # Tu documento indica que SALIDA es un tipo de SEGURO, así que esta lógica es consistente.
                # Si una casilla de salida es también la de un jugador (ej. SALIDA_SQUARES_INDICES[Color.RED] == 0),
                # y 0 es un SEGURO, el tipo SALIDA toma precedencia.
                # Para seguros que no son salidas, el color_assoc puede ser None.
                # O, si un seguro es "propiedad" de un color cercano, se podría asociar.
                # Por simplicidad, los seguros que no son salidas no tienen color_assoc aquí.

            self.squares[square_id] = Square(square_id, square_type, color_assoc)

        # 2. Casillas de los pasillos y metas para cada color
        for color in Color:
            for k in range(PASSAGEWAY_LENGTH): # k de 0 a 6
                pasillo_id: SquareId = ('pas', color, k)
                # La última casilla del pasillo (k=6) es la META
                pasillo_type = SquareType.META if k == PASSAGEWAY_LENGTH - 1 else SquareType.PASILLO
                self.squares[pasillo_id] = Square(pasillo_id, pasillo_type, color)

        # 3. Casilla CIELO (común para todos)
        self.squares[self.cielo_square_id] = Square(self.cielo_square_id, SquareType.CIELO)
        
        # (Opcional) Casillas de CÁRCEL si decides modelarlas como Squares
        # for color in Color:
        #     carcel_id: SquareId = ('carcel', color, 0) # El índice 0 es solo un placeholder
        #     self.squares[carcel_id] = Square(carcel_id, SquareType.CARCEL, color)


    def _initialize_paths(self) -> None:
        """Defines the complete movement path for each player color."""
        for color in Color:
            path: List[SquareId] = []
            salida_idx = SALIDA_SQUARES_INDICES[color]
            entrada_pasillo_idx = ENTRADA_PASILLO_INDICES[color]

            # Recorrido en la pista principal hasta la entrada del pasillo
            current_idx = salida_idx
            # Añade todas las casillas desde la salida hasta una antes de la entrada al pasillo
            # El recorrido es antihorario.
            # Si la entrada está "antes" de la salida en el ciclo, damos toda la vuelta.
            
            # La pieza se mueve desde su SALIDA hasta la ENTRADA_PASILLO de su propio color.
            # Una vez en la ENTRADA_PASILLO, el siguiente paso la lleva a la primera casilla de su PASILLO.
            
            temp_idx = salida_idx
            while temp_idx != entrada_pasillo_idx:
                path.append(temp_idx)
                temp_idx = (temp_idx + 1) % NUM_MAIN_TRACK_SQUARES
            path.append(entrada_pasillo_idx) # Añadir la casilla de entrada al pasillo

            # Recorrido por el pasillo de color
            for k in range(PASSAGEWAY_LENGTH): # k de 0 a 6
                path.append(('pas', color, k)) # Esto incluye la META que es ('pas', color, 6)

            # Finalmente, el CIELO
            path.append(self.cielo_square_id)
            
            self.paths[color] = path

    def get_square(self, square_id: SquareId) -> Optional[Square]:
        """Get a square by its ID.

        Args:
            square_id: The ID of the square to retrieve.

        Returns:
            The Square object if found, else None.
        """
        return self.squares.get(square_id)

    def get_salida_square_id_for_color(self, color: Color) -> int:
        """Get the SALIDA square ID for a given color.

        Args:
            color: The player color.

        Returns:
            The integer ID of the salida square.
        """
        return SALIDA_SQUARES_INDICES[color]

    def get_entrada_pasillo_square_id_for_color(self, color: Color) -> int:
        """Get the ENTRADA_PASILLO square ID for a given color.

        Args:
            color: The player color.

        Returns:
            The integer ID of the entrada_pasillo square.
        """
        return ENTRADA_PASILLO_INDICES[color]

    def get_player_path(self, color: Color) -> List[SquareId]:
        """Get the list of square IDs that make up a player's path.

        Args:
            color: The player color.

        Returns:
            List of SquareId objects representing the player's movement path.
        """
        return self.paths.get(color, [])

    def get_next_square_id_in_path(
        self, current_pos_in_path: SquareId, color: Color, steps: int
    ) -> Optional[SquareId]:
        """Get the destination square ID given a player's current position, color, and steps.

        Args:
            current_pos_in_path: The current position in the player's path.
            color: The player color.
            steps: Number of steps to advance.

        Returns:
            The target SquareId, or None if the move is invalid or overshoots the goal.
        """
        player_path = self.get_player_path(color)
        if not player_path:
            return None

        try:
            current_path_index = player_path.index(current_pos_in_path)
        except ValueError:
            # La posición actual no está en el camino definido (esto no debería ocurrir para una ficha activa)
            return None

        target_path_index = current_path_index + steps

        if target_path_index < len(player_path):
            return player_path[target_path_index]
        else:
            # Se pasó del final del camino (que es el cielo)
            return None # O manejar como tiro inválido si no es exacto para cielo

    def _get_main_track_position_after_steps(self, start_square_id: int, steps: int) -> int:
        """Calculate the main track position after a number of steps.

        Args:
            start_square_id: The starting square ID (int).
            steps: Number of steps to advance.

        Returns:
            The resulting square ID after moving the given steps.
        """
        return (start_square_id + steps) % NUM_MAIN_TRACK_SQUARES

    def advance_piece_logic(
        self, current_square_id: SquareId, steps: int, piece_color: Color
    ) -> Optional[SquareId]:
        """Core logic for advancing a piece on the board.

        Determines the destination square given the current square, number of steps, and piece color.
        Returns None if the move overshoots the goal or is otherwise invalid.

        Args:
            current_square_id: The current square ID of the piece.
            steps: Number of steps to advance.
            piece_color: The color of the piece.

        Returns:
            The destination SquareId, or None if the move is invalid.
        """
        # Caso 0: Si está en la cárcel, no puede usar esta función. Salida de cárcel es un movimiento especial.
        if current_square_id is None: # Asumiendo que None significa cárcel para la posición de la ficha
            # Esta función es para mover fichas ya en el tablero.
            # La salida de cárcel se maneja por separado (mover a SALIDA_SQUARES_INDICES[piece_color])
            return None

        # Identificar si estamos en la pista principal, en un pasillo, o en la meta
        current_square_object = self.get_square(current_square_id)
        if not current_square_object:
            return None # Casilla actual inválida

        # 1. Si estamos en la pista principal
        if isinstance(current_square_id, int):
            entrada_pasillo_propia = ENTRADA_PASILLO_INDICES[piece_color]
            pos_actual_pista = current_square_id
            
            for i in range(1, steps + 1):
                next_pos_pista = (pos_actual_pista + 1) % NUM_MAIN_TRACK_SQUARES
                # ¿Llegamos a la entrada de nuestro pasillo?
                if next_pos_pista == entrada_pasillo_propia:
                    pasos_restantes = steps - i
                    if pasos_restantes >= 0: # Si caemos justo o nos sobran pasos
                        # Entramos al pasillo. El primer paso del pasillo es el índice 0.
                        if pasos_restantes == 0: # Caímos justo en la entrada
                            return ('pas', piece_color, 0)
                        else: # Nos sobran pasos, avanzamos dentro del pasillo
                             # El pasillo va de k=0 a k=6 (PASSAGEWAY_LENGTH-1)
                            if pasos_restantes <= PASSAGEWAY_LENGTH:
                                return ('pas', piece_color, pasos_restantes -1) # -1 porque pasillo es 0-indexed
                            else: # Demasiados pasos, se pasa del cielo
                                return None 
                    # else: # No debería ocurrir si i va de 1 a steps
                    #     return None 
                pos_actual_pista = next_pos_pista
            
            # Si terminamos el bucle sin entrar al pasillo, la posición final es pos_actual_pista
            return pos_actual_pista

        # 2. Si estamos en un pasillo ('pas', color, k) o meta ('pas', color, 6)
        elif isinstance(current_square_id, tuple) and current_square_id[0] == 'pas':
            _, pasillo_color, k = current_square_id
            
            if pasillo_color != piece_color:
                # Esto no debería pasar, una ficha no debería estar en el pasillo de otro color.
                return None 

            target_k = k + steps
            
            if target_k < PASSAGEWAY_LENGTH: # Sigue en el pasillo/meta
                return ('pas', piece_color, target_k)
            elif target_k == PASSAGEWAY_LENGTH: # Intenta llegar al CIELO
                # Tiro exacto para llegar al cielo desde la última casilla del pasillo (meta)
                # La casilla meta es k = PASSAGEWAY_LENGTH - 1
                # Si estoy en k=6 y saco 1 -> target_k = 7, que es PASSAGEWAY_LENGTH
                return self.cielo_square_id
            else: # Se pasó del cielo
                return None
        
        # 3. Si ya está en el CIELO, no se puede mover más.
        elif current_square_id == self.cielo_square_id:
            return None # No se puede mover desde el cielo

        return None # Por si alguna condición no se maneja