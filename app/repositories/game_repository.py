from __future__ import annotations
import uuid
from typing import Dict, Optional, List, TYPE_CHECKING

from app.repositories.base_repository import GameRepository
# No necesitamos importar GameAggregate aquí para las anotaciones si usamos string
# o si base_repository ya lo hace con TYPE_CHECKING.
# Pero si necesitamos el tipo para `isinstance` o creación, sí.

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate


class InMemoryGameRepository(GameRepository):
    """
    Implementación en memoria del repositorio de partidas.
    Utiliza un diccionario para almacenar las partidas.
    """
    _games: Dict[uuid.UUID, GameAggregate] # El tipo real de GameAggregate

    def __init__(self):
        self._games: Dict[uuid.UUID, GameAggregate] = {}
        print("InMemoryGameRepository initialized.") # Para debug

    async def get_by_id(self, game_id: uuid.UUID) -> Optional[GameAggregate]:
        print(f"InMemoryGameRepository: Attempting to get game by ID: {game_id}") # Para debug
        return self._games.get(game_id)

    async def save(self, game: GameAggregate) -> None:
        # Aquí 'game' es del tipo app.models.domain.game.GameAggregate
        print(f"InMemoryGameRepository: Saving game ID: {game.id}, State: {game.state}") # Para debug
        self._games[game.id] = game

    async def delete(self, game_id: uuid.UUID) -> bool:
        print(f"InMemoryGameRepository: Attempting to delete game ID: {game_id}") # Para debug
        if game_id in self._games:
            del self._games[game_id]
            return True
        return False

    async def get_all_active(self) -> List[GameAggregate]:
        """
        Devuelve una lista de todas las partidas que no están en estado FINISHED o ABORTED.
        (La definición de "activa" puede variar según tus necesidades).
        """
        # Necesitaremos importar GameState para esto
        from app.core.enums import GameState
        print("InMemoryGameRepository: Getting all active games.") # Para debug
        
        active_games = [
            game for game in self._games.values() 
            if game.state not in [GameState.FINISHED, GameState.ABORTED]
        ]
        return active_games

    async def get_all(self) -> List[GameAggregate]:
        """Devuelve todas las partidas, sin importar su estado."""
        print("InMemoryGameRepository: Getting all games.") # Para debug
        return list(self._games.values())