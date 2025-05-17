import random
from typing import Tuple

class Dice:
    """
    Clase para simular el lanzamiento de dos dados de Parqués.
    """

    @staticmethod
    def roll() -> Tuple[int, int]:
        """
        Lanza dos dados de seis caras.
        Returns:
            Tuple[int, int]: Una tupla con los resultados de los dos dados.
        """
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        return d1, d2

    @staticmethod
    def are_pairs(d1: int, d2: int) -> bool:
        """
        Verifica si los resultados de los dados son pares.
        """
        return d1 == d2