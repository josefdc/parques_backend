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
    """Abstract interface for a Parqués game repository.

    Any repository implementation (in-memory, database, etc.) must implement these methods.
    """

    @abstractmethod
    async def get_by_id(self, game_id: uuid.UUID) -> Optional['GameAggregate']:
        """Retrieve a game by its ID.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            The GameAggregate instance if found, else None.
        """
        pass

    @abstractmethod
    async def save(self, game: 'GameAggregate') -> None:
        """Save (create or update) a game in the repository.

        Args:
            game: The GameAggregate instance to save.
        """
        pass

    @abstractmethod
    async def delete(self, game_id: uuid.UUID) -> bool:
        """Delete a game from the repository.

        Args:
            game_id: The unique identifier of the game to delete.

        Returns:
            True if the game was deleted, False if not found.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List['GameAggregate']:
        """Retrieve all active or waiting games.

        Returns:
            A list of GameAggregate instances representing active or waiting games.
        """
        pass