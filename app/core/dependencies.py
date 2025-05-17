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
    return GameService(
        repository=game_repository_instance,
        validator=move_validator_instance,
        dice_roller=dice_roller_instance
    )

async def get_game_service_dependency() -> GameService:
    # In a real application, this could involve more complex setup,
    # like getting a DB session, etc. For now, it's simple.
    return create_game_service()

# La dependencia anotada que se usará en los endpoints
GameServiceDep = Annotated[GameService, Depends(get_game_service_dependency)]

# UserIdDep could also be moved here if it's used across multiple routers,
# but for now, as per your example, it can stay in game_routes.py if only used there.
