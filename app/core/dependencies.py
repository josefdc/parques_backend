"""Dependency injection setup for the application.

This module configures and provides dependencies, such as services and repositories,
to be injected into FastAPI path operations. It utilizes a simple singleton pattern
for instantiating shared resources like the game repository, dice roller, and
move validator.
"""

from typing import Annotated
from fastapi import Depends

from app.services.game_service import GameService
from app.repositories.base_repository import GameRepository
from app.repositories.game_repository import InMemoryGameRepository
from app.rules.dice import Dice
from app.rules.move_validator import MoveValidator

# --- Instancias de Dependencias (Singleton pattern simple) ---
game_repository_instance: GameRepository = InMemoryGameRepository()
dice_roller_instance: Dice = Dice()
move_validator_instance: MoveValidator = MoveValidator()

def create_game_service() -> GameService:
    """Creates and returns an instance of GameService.

    This factory function initializes the GameService with its required
    dependencies (repository, validator, dice_roller).

    Returns:
        An instance of GameService.
    """
    return GameService(
        repository=game_repository_instance,
        validator=move_validator_instance,
        dice_roller=dice_roller_instance
    )

async def get_game_service_dependency() -> GameService:
    """FastAPI dependency to get a GameService instance.

    In a more complex application, this function might handle tasks like
    obtaining a database session. For this application, it simply returns
    an instance created by `create_game_service`.

    Returns:
        An instance of GameService.
    """
    return create_game_service()

# Annotated dependency to be used in FastAPI path operations
GameServiceDep = Annotated[GameService, Depends(get_game_service_dependency)]

# Note: UserIdDep could be moved here if used across multiple routers.
# Currently, it remains in game_routes.py as it's only used there.
