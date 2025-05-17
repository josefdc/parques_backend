"""Configuración de inyección de dependencias para la aplicación.

Este módulo configura y proporciona dependencias, como servicios y repositorios,
que se inyectarán en las operaciones de ruta de FastAPI. Utiliza un patrón simple de
singleton para la instanciación de recursos compartidos como el repositorio de juegos,
el lanzador de dados y el validador de movimientos.
"""

from typing import Annotated
from fastapi import Depends

from app.services.game_service import GameService
from app.repositories.base_repository import GameRepository
from app.repositories.game_repository import InMemoryGameRepository
from app.rules.dice import Dice
from app.rules.move_validator import MoveValidator

# Instancias singleton de dependencias
game_repository_instance: GameRepository = InMemoryGameRepository()
dice_roller_instance: Dice = Dice()
move_validator_instance: MoveValidator = MoveValidator()

def create_game_service() -> GameService:
    """
    Crea y retorna una instancia de GameService.

    Returns:
        Instancia de GameService.
    """
    return GameService(
        repository=game_repository_instance,
        validator=move_validator_instance,
        dice_roller=dice_roller_instance
    )

async def get_game_service_dependency() -> GameService:
    """
    Dependencia de FastAPI para obtener una instancia de GameService.

    Returns:
        Instancia de GameService.
    """
    return create_game_service()

GameServiceDep = Annotated[GameService, Depends(get_game_service_dependency)]
