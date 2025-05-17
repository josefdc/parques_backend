"""Abstract base repository interface for Parqués games.

Defines the contract for repository implementations to manage game persistence.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate


class GameRepository(ABC):
    """
    Interfaz abstracta para un repositorio de partidas de Parqués.

    Cualquier implementación (memoria, base de datos, etc.) debe implementar estos métodos.
    """

    @abstractmethod
    async def get_by_id(self, game_id: uuid.UUID) -> Optional['GameAggregate']:
        """
        Recupera una partida por su ID.

        Args:
            game_id: Identificador único de la partida.

        Returns:
            Instancia de GameAggregate si se encuentra, si no None.
        """
        pass

    @abstractmethod
    async def save(self, game: 'GameAggregate') -> None:
        """
        Guarda (crea o actualiza) una partida en el repositorio.

        Args:
            game: Instancia de GameAggregate a guardar.
        """
        pass

    @abstractmethod
    async def delete(self, game_id: uuid.UUID) -> bool:
        """
        Elimina una partida del repositorio.

        Args:
            game_id: Identificador único de la partida a eliminar.

        Returns:
            True si la partida fue eliminada, False si no se encontró.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List['GameAggregate']:
        """
        Recupera todas las partidas activas o en espera.

        Returns:
            Lista de instancias GameAggregate representando partidas activas o en espera.
        """
        pass