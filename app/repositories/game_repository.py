#app/repositories/game_repository.py
"""In-memory repository implementation for Parqués games.

Provides a simple dictionary-based storage for game aggregates,
suitable for development and testing.
"""
from __future__ import annotations
import uuid
from typing import Dict, Optional, List, TYPE_CHECKING

from app.repositories.base_repository import GameRepository

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate

class InMemoryGameRepository(GameRepository):
    """In-memory implementation of the Parqués game repository.

    Stores games in a dictionary keyed by UUID.
    """
    _games: Dict[uuid.UUID, 'GameAggregate']

    def __init__(self) -> None:
        """Initializes the in-memory game repository."""
        self._games: Dict[uuid.UUID, 'GameAggregate'] = {}
        print("InMemoryGameRepository initialized.")  # For debug

    async def get_by_id(self, game_id: uuid.UUID) -> Optional['GameAggregate']:
        """Retrieve a game by its ID.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            The GameAggregate instance if found, else None.
        """
        print(f"InMemoryGameRepository: Attempting to get game by ID: {game_id}")  # For debug
        return self._games.get(game_id)

    async def save(self, game: 'GameAggregate') -> None:
        """Save (create or update) a game in the repository.

        Args:
            game: The GameAggregate instance to save.
        """
        print(f"InMemoryGameRepository: Saving game ID: {game.id}, State: {game.state}")  # For debug
        self._games[game.id] = game

    async def delete(self, game_id: uuid.UUID) -> bool:
        """Delete a game from the repository.

        Args:
            game_id: The unique identifier of the game to delete.

        Returns:
            True if the game was deleted, False if not found.
        """
        print(f"InMemoryGameRepository: Attempting to delete game ID: {game_id}")  # For debug
        if game_id in self._games:
            del self._games[game_id]
            return True
        return False

    async def get_all_active(self) -> List['GameAggregate']:
        """Retrieve all active or waiting games.

        Returns:
            A list of GameAggregate instances representing active or waiting games.
        """
        from app.core.enums import GameState
        print("InMemoryGameRepository: Getting all active games.")  # For debug
        active_games = [
            game for game in self._games.values()
            if game.state not in [GameState.FINISHED, GameState.ABORTED]
        ]
        return active_games

    async def get_all(self) -> List['GameAggregate']:
        """Retrieve all games, regardless of state.

        Returns:
            A list of all GameAggregate instances.
        """
        print("InMemoryGameRepository: Getting all games.")  # For debug
        return list(self._games.values())