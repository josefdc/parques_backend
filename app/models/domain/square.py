from __future__ import annotations # Necesario para usar 'Piece' sin comillas en Python < 3.9-3.10
                                 # En Python 3.10+ es el comportamiento por defecto.
                                 # Para versiones más antiguas, o si prefieres ser explícito,
                                 # puedes usar 'Piece' (como string) en las anotaciones.

from typing import List, Union, Tuple, Optional, TYPE_CHECKING

from app.core.enums import SquareType, Color

# Este bloque solo se ejecuta durante el chequeo de tipos (ej. con MyPy)
# Evita errores de importación circular en runtime.
if TYPE_CHECKING:
    from app.models.domain.piece import Piece # Importación para el chequeo de tipos


# Definimos SquareId de nuevo para claridad en este módulo, o puedes centralizarlo
# en un archivo de tipos comunes si se usa extensamente.
SquareId = Union[int, Tuple[str, Optional[Color], Optional[int]]]


class Square:
    """
    Representa una casilla en el tablero de Parqués.
    """
    id: SquareId
    type: SquareType
    occupants: List[Piece] # Ahora usa la forward reference 'Piece'
    # Atributo opcional para casillas de salida/entrada/pasillo/meta para saber a qué color pertenecen
    color_association: Optional[Color]

    def __init__(self, square_id: SquareId, square_type: SquareType, color_association: Optional[Color] = None):
        self.id = square_id
        self.type = square_type
        self.occupants = []
        self.color_association = color_association

    def __repr__(self) -> str:
        occupant_details = []
        for occ in self.occupants:
            # Accedemos a los atributos de Piece asumiendo que ya está definida
            detail = f"{occ.color.name}{occ.piece_player_id + 1}"
            occupant_details.append(detail)

        return (f"Square(ID: {self.id}, Type: {self.type.name}, "
                f"ColorAssoc: {self.color_association.name if self.color_association else 'N/A'}, "
                f"Occupants: [{', '.join(occupant_details)}])")

    def add_piece(self, piece: Piece):
        """Añade una ficha a la casilla."""
        if piece not in self.occupants:
            self.occupants.append(piece)
            piece.position = self.id # Actualiza la posición en la ficha

    def remove_piece(self, piece: Piece):
        """Remueve una ficha de la casilla."""
        if piece in self.occupants:
            self.occupants.remove(piece)
            # Opcionalmente, podrías querer limpiar la posición en la ficha si se va a la cárcel
            # if piece.is_in_jail:
            #     piece.position = None

    def is_occupied(self) -> bool:
        """Verifica si la casilla está ocupada."""
        return len(self.occupants) > 0

    def is_occupied_by_color(self, color: Color) -> bool:
        """Verifica si la casilla está ocupada por alguna ficha de un color específico."""
        return any(occupant.color == color for occupant in self.occupants)

    def get_occupying_pieces_by_color(self, color: Color) -> List[Piece]:
        """Obtiene todas las fichas de un color específico que ocupan la casilla."""
        return [occupant for occupant in self.occupants if occupant.color == color]

    def get_other_color_pieces(self, color: Color) -> List[Piece]:
        """Obtiene todas las fichas de colores DIFERENTES al especificado que ocupan la casilla."""
        return [occupant for occupant in self.occupants if occupant.color != color]

    def is_forming_wall(self) -> Optional[Color]:
        """
        Verifica si las fichas en esta casilla forman una barrera (muro).
        Una barrera se forma si hay dos fichas del mismo color en una casilla que no sea SALIDA ni SEGURO.
        (La regla de no formar barrera en SALIDA/SEGURO se aplicaría al *permitir* el movimiento a la casilla).
        Aquí solo detectamos si hay dos del mismo color.
        Devuelve el color de la barrera si existe, sino None.
        """
        if len(self.occupants) >= 2:
            # Se asume que todas las fichas en una casilla de barrera deben ser del mismo color.
            # Si una casilla puede tener múltiples fichas de diferentes colores y aún así una pareja
            # forma barrera, la lógica necesitaría ser más compleja.
            # Para Parqués, usualmente 2 fichas del mismo color en una casilla normal o de entrada es barrera.
            first_piece_color = self.occupants[0].color
            if all(p.color == first_piece_color for p in self.occupants):
                return first_piece_color
        return None

    def is_safe_square_for_piece(self, piece_color: Color) -> bool:
        """
        Determina si esta casilla es intrínsecamente segura para una ficha de un color dado.
        No considera si hay otras fichas.
        """
        if self.type == SquareType.SEGURO:
            return True
        if self.type == SquareType.SALIDA and self.color_association == piece_color:
            return True
        if self.type in [SquareType.PASILLO, SquareType.ENTRADA_PASILLO, SquareType.META] and \
           self.color_association == piece_color:
            return True
        if self.type == SquareType.CIELO: # El cielo es seguro
            return True
        return False