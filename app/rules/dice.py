"""Utilidades para lanzar dados en Parqués.

Este módulo proporciona la clase Dice para simular el lanzamiento de dos dados de seis caras,
incluyendo métodos útiles para verificar pares.
"""
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
            Tupla con los resultados de los dos dados.
        """
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        return d1, d2

    @staticmethod
    def are_pairs(d1: int, d2: int) -> bool:
        """
        Verifica si los resultados de los dados son un par.

        Args:
            d1: Resultado del primer dado.
            d2: Resultado del segundo dado.

        Returns:
            True si ambos dados muestran el mismo valor, False en caso contrario.
        """
        return d1 == d2