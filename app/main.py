"""Main entry point for the Parqués backend application.

Initializes the FastAPI app, sets up global exception handling, and includes API routers.
"""
from fastapi import FastAPI, Depends, HTTPException, Header, status
from typing import Annotated, Optional
from contextlib import asynccontextmanager

from app.core.config import settings
from app.services.game_service import GameServiceError
from app.models import schemas
from app.services.game_service import GameNotFoundError, NotPlayerTurnError, PlayerNotInGameError
from app.core.enums import MoveResultType

from app.api.routers import game_routes

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend para el juego de Parqués Distribuido",
)

from fastapi.responses import JSONResponse
from fastapi.requests import Request

@app.exception_handler(GameServiceError)
async def game_service_exception_handler(request: Request, exc: GameServiceError):
    """
    Maneja excepciones GameServiceError globalmente y retorna una respuesta estandarizada.
    """
    status_code = 400
    if isinstance(exc, GameNotFoundError):
        status_code = 404
    elif isinstance(exc, NotPlayerTurnError):
        status_code = 403
    elif isinstance(exc, PlayerNotInGameError):
        status_code = 404

    detail_message = str(exc)
    result_type_member: MoveResultType = exc.result_type if exc.result_type else MoveResultType.ACTION_FAILED

    return JSONResponse(
        status_code=status_code,
        content=schemas.MoveOutcome(
            success=False,
            message=detail_message,
            move_result_type=result_type_member
        ).model_dump(exclude_none=True),
    )

app.include_router(
    game_routes.router,
    prefix="/api/v1",
    tags=["Game Management"]
)

@app.get("/", tags=["Root"])
async def read_root():
    """
    Endpoint raíz para verificación y mensaje de bienvenida.
    """
    return {"message": f"Bienvenido al {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}"}