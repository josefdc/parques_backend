from __future__ import annotations
from typing import List, Dict, Union, Tuple, Optional, TYPE_CHECKING

from app.core.enums import Color, SquareType
from app.models.domain.square import Square, SquareId # Square ya está definido

if TYPE_CHECKING:
    from app.models.domain.piece import Piece # Para type hinting en métodos si es necesario

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
    """
    Representa el tablero de juego de Parqués.
    Contiene todas las casillas y define los caminos para cada color.
    """
    squares: Dict[SquareId, Square]
    paths: Dict[Color, List[SquareId]] # El camino completo para cada color, incluyendo pasillo y meta
    # Podríamos añadir también una referencia al cielo, aunque es una única casilla
    cielo_square_id: SquareId 

    def __init__(self):
        self.squares = {}
        self.paths = {}
        self.cielo_square_id = ('cielo', None, 0) # ID único para el cielo
        self._initialize_board()
        self._initialize_paths()

    def _initialize_board(self):
        """Crea todas las casillas del tablero."""
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


    def _initialize_paths(self):
        """Define el recorrido completo para cada color."""
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
        """Obtiene una casilla por su ID."""
        return self.squares.get(square_id)

    def get_salida_square_id_for_color(self, color: Color) -> int:
        """Devuelve el ID de la casilla de SALIDA para un color."""
        return SALIDA_SQUARES_INDICES[color]

    def get_entrada_pasillo_square_id_for_color(self, color: Color) -> int:
        """Devuelve el ID de la casilla de ENTRADA_PASILLO para un color."""
        return ENTRADA_PASILLO_INDICES[color]

    def get_player_path(self, color: Color) -> List[SquareId]:
        """Devuelve la lista de IDs de casillas que componen el camino de un jugador."""
        return self.paths.get(color, [])

    def get_next_square_id_in_path(self, current_pos_in_path: SquareId, color: Color, steps: int) -> Optional[SquareId]:
        """
        Devuelve el ID de la casilla destino dado una posición actual en el camino del jugador,
        el color del jugador y el número de pasos.
        Retorna None si el movimiento es inválido o se pasa del cielo.
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
        """Calcula la posición en la pista principal después de un número de pasos."""
        return (start_square_id + steps) % NUM_MAIN_TRACK_SQUARES

    def advance_piece_logic(self, current_square_id: SquareId, steps: int, piece_color: Color) -> Optional[SquareId]:
        """
        Lógica de avance mejorada basada en tu pseudocódigo 'advance'.
        Devuelve la casilla destino o None si el movimiento rebasa la meta final (cielo)
        o si se requiere un tiro exacto y no se cumple.

        Esta lógica es compleja y es el núcleo del movimiento.
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