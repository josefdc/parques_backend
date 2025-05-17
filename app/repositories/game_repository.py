#app/repositories/game_repository.py
"""Implementación en memoria del repositorio de partidas de Parqués.

Almacena las partidas en un diccionario con UUID como clave.
"""
from __future__ import annotations
import uuid
from typing import Dict, Optional, List, TYPE_CHECKING

from app.repositories.base_repository import GameRepository

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate

class InMemoryGameRepository(GameRepository):
    """Implementación en memoria del repositorio de partidas de Parqués.

    Almacena las partidas en un diccionario con UUID como clave.
    """
    _games: Dict[uuid.UUID, 'GameAggregate']

    def __init__(self) -> None:
        """Inicializa el repositorio en memoria."""
        self._games: Dict[uuid.UUID, 'GameAggregate'] = {}
        print("InMemoryGameRepository initialized.")  # Debug

    async def get_by_id(self, game_id: uuid.UUID) -> Optional['GameAggregate']:
        """Recupera una partida por su ID.

        Args:
            game_id: Identificador único de la partida.

        Returns:
            Instancia de GameAggregate si se encuentra, si no None.
        """
        print(f"InMemoryGameRepository: Attempting to get game by ID: {game_id}")  # Debug
        return self._games.get(game_id)

    async def save(self, game: 'GameAggregate') -> None:
        """Guarda (crea o actualiza) una partida en el repositorio.

        Args:
            game: Instancia de GameAggregate a guardar.
        """
        print(f"InMemoryGameRepository: Saving game ID: {game.id}, State: {game.state}")  # Debug
        self._games[game.id] = game

    async def delete(self, game_id: uuid.UUID) -> bool:
        """Elimina una partida del repositorio.

        Args:
            game_id: Identificador único de la partida a eliminar.

        Returns:
            True si la partida fue eliminada, False si no se encontró.
        """
        print(f"InMemoryGameRepository: Attempting to delete game ID: {game_id}")  # Debug
        if game_id in self._games:
            del self._games[game_id]
            return True
        return False

    async def get_all_active(self) -> List['GameAggregate']:
        """Recupera todas las partidas activas o en espera.

        Returns:
            Lista de instancias GameAggregate activas o en espera.
        """
        from app.core.enums import GameState
        print("InMemoryGameRepository: Getting all active games.")  # Debug
        active_games = [
            game for game in self._games.values()
            if game.state not in [GameState.FINISHED, GameState.ABORTED]
        ]
        return active_games

    async def get_all(self) -> List['GameAggregate']:
        """Recupera todas las partidas, sin importar el estado.

        Returns:
            Lista de todas las instancias GameAggregate.
        """
        print("InMemoryGameRepository: Getting all games.")  # Debug
        return list(self._games.values())