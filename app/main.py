#app/main.py
from fastapi import FastAPI, Depends, HTTPException, Header, status
from typing import Annotated, Optional # Mantener Optional y Annotated
from contextlib import asynccontextmanager

from app.core.config import settings
# from app.repositories.base_repository import GameRepository # No longer needed here
# from app.repositories.game_repository import InMemoryGameRepository # No longer needed here
# from app.rules.dice import Dice # No longer needed here
# from app.rules.move_validator import MoveValidator # No longer needed here
from app.services.game_service import GameServiceError # Keep for exception handler
from app.models import schemas # Keep for exception handler
from app.services.game_service import GameNotFoundError, NotPlayerTurnError, PlayerNotInGameError # Keep for exception handler
from app.core.enums import MoveResultType # Ensure MoveResultType is imported

# --- Dependency definitions are now in app.core.dependencies ---

from app.api.routers import game_routes # This import is now safe

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend para el juego de Parqués Distribuido",
)

# --- Manejador de Excepciones Global (Permanece igual) ---
from fastapi.responses import JSONResponse
from fastapi.requests import Request
# from app.core.enums import MoveResultType # Already imported via schemas or GameServiceError if needed by handler

@app.exception_handler(GameServiceError)
async def game_service_exception_handler(request: Request, exc: GameServiceError):
    status_code = 400 
    if isinstance(exc, GameNotFoundError):
        status_code = 404
    elif isinstance(exc, NotPlayerTurnError):
        status_code = 403 # Forbidden
    elif isinstance(exc, PlayerNotInGameError):
        status_code = 404 # Or 403 depending on context, 404 seems fine if player is "not found" in game context

    detail_message = str(exc)
    
    # Use the enum member directly. Pydantic will handle .value on serialization if use_enum_values=True.
    result_type_member: MoveResultType = exc.result_type if exc.result_type else MoveResultType.ACTION_FAILED

    return JSONResponse(
        status_code=status_code,
        content=schemas.MoveOutcome(
            success=False, 
            message=detail_message, 
            move_result_type=result_type_member # Pass the enum member
        ).model_dump(exclude_none=True),
    )

# --- Incluir Routers de la API ---
app.include_router(
    game_routes.router, 
    prefix="/api/v1", 
    tags=["Game Management"]
)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Bienvenido al {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}"}