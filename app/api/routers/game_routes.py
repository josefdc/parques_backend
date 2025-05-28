"""Endpoints de la API para operaciones del juego de Parqués.

Este módulo define las rutas de FastAPI para crear, unirse, iniciar
y gestionar el estado de las partidas de Parqués.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status, Header
from typing import Annotated, Optional
import uuid

from app.models import schemas
from app.core.enums import Color, GameState
from app.core.dependencies import GameServiceDep
from app.services.game_service import GameServiceError


router = APIRouter()

async def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> Optional[str]:
    """
    Extrae el ID de usuario del encabezado X-User-ID.

    Args:
        x_user_id: Valor del encabezado X-User-ID, si está presente.

    Returns:
        El ID de usuario como cadena si el encabezado está presente, de lo contrario None.
    """
    if not x_user_id:
        return None
    return x_user_id

UserIdDep = Annotated[Optional[str], Depends(get_current_user_id)]

@router.post(
    "/games",
    response_model=schemas.GameInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva partida de Parqués"
)
async def create_game_endpoint(
    create_request: schemas.CreateGameRequest,
    service: GameServiceDep,
) -> schemas.GameInfo:
    """
    Crea una nueva partida de Parqués.

    El ID del creador se toma del cuerpo de la solicitud.

    Args:
        create_request: Contiene creator_user_id, creator_color y max_players.
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 422 si creator_color es inválido.

    Returns:
        Información sobre la partida creada.
    """
    final_creator_color: Color
    if isinstance(create_request.creator_color, Color):
        final_creator_color = create_request.creator_color
    else:
        try:
            final_creator_color = Color(create_request.creator_color)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Valor inválido para creator_color: '{create_request.creator_color}'. Valores permitidos son {[(m.name, m.value) for m in Color]}"
            )

    try:
        game = await service.create_new_game(
            creator_user_id=create_request.creator_user_id,
            creator_color=final_creator_color,
            max_players=create_request.max_players
        )
        player_infos = [
            schemas.PlayerInfo.model_validate(p) for p in game.players.values()
        ]
        for p_info in player_infos:
            p_info.is_current_turn = (game.current_turn_color == p_info.color and game.state == GameState.IN_PROGRESS)

        return schemas.GameInfo(
            id=game.id,
            state=game.state,
            max_players=game.max_players,
            current_player_count=len(game.players),
            players=player_infos,
            created_at=game.created_at
        )
    except GameServiceError as e:
        raise

@router.post(
    "/games/{game_id}/join",
    response_model=schemas.GameInfo,
    summary="Unirse a una partida existente"
)
async def join_game_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="El ID de la partida a la que unirse")],
    join_request: schemas.JoinGameRequest,
    service: GameServiceDep
) -> schemas.GameInfo:
    """
    Permite a un usuario unirse a una partida existente.

    Args:
        game_id: UUID de la partida.
        join_request: Contiene user_id y color solicitado.
        service: Inyección de dependencia para GameService.

    Returns:
        Información actualizada de la partida.
    """
    game = await service.join_game(
        game_id=game_id,
        user_id=join_request.user_id,
        requested_color=join_request.color
    )
    player_infos = [
        schemas.PlayerInfo.model_validate(p) for p in game.players.values()
    ]
    for p_info in player_infos:
        p_info.is_current_turn = (game.current_turn_color == p_info.color and game.state == GameState.IN_PROGRESS)

    return schemas.GameInfo(
        id=game.id,
        state=game.state,
        max_players=game.max_players,
        current_player_count=len(game.players),
        players=player_infos,
        created_at=game.created_at
    )

@router.post(
    "/games/{game_id}/start",
    response_model=schemas.GameInfo,
    summary="Iniciar una partida que está lista"
)
async def start_game_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida a iniciar")],
    user_id: UserIdDep,
    service: GameServiceDep
) -> schemas.GameInfo:
    """
    Inicia una partida en estado 'READY_TO_START'.

    El usuario debe ser el creador.

    Args:
        game_id: UUID de la partida.
        user_id: ID del usuario (de X-User-ID).
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 400 si falta el encabezado X-User-ID.

    Returns:
        Información de la partida tras iniciar.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido para iniciar la partida.")

    game = await service.start_game(game_id, user_id)

    player_infos = [
        schemas.PlayerInfo.model_validate(p) for p in game.players.values()
    ]
    for p_info in player_infos:
        p_info.is_current_turn = (game.current_turn_color == p_info.color and game.state == GameState.IN_PROGRESS)

    return schemas.GameInfo(
        id=game.id,
        state=game.state,
        max_players=game.max_players,
        current_player_count=len(game.players),
        players=player_infos,
        created_at=game.created_at
    )

@router.get(
    "/games/{game_id}/state",
    response_model=schemas.GameSnapshot,
    summary="Obtener el estado completo de una partida"
)
async def get_game_state_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="El ID de la partida")],
    service: GameServiceDep
) -> schemas.GameSnapshot:
    """
    Obtiene el estado completo actual de una partida.

    Args:
        game_id: UUID de la partida.
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 404 si la partida no existe.

    Returns:
        Snapshot del estado actual del juego.
    """
    game = await service._repository.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partida no encontrada")

    board_info = [schemas.SquareInfo.model_validate(sq) for sq_id, sq in game.board.squares.items()]
    player_infos = []
    for p_color, p_obj in game.players.items():
        p_info = schemas.PlayerInfo.model_validate(p_obj)
        p_info.is_current_turn = (game.current_turn_color == p_color and game.state == GameState.IN_PROGRESS)
        player_infos.append(p_info)

    return schemas.GameSnapshot(
        game_id=game.id,
        state=game.state,
        board=board_info,
        players=player_infos,
        turn_order=list(game.turn_order),
        current_turn_color=game.current_turn_color,
        current_player_doubles_count=game.current_player_doubles_count,
        last_dice_roll=game.last_dice_roll,
        winner=game.winner
    )

@router.post(
    "/games/{game_id}/roll",
    response_model=schemas.DiceRollResponse,
    summary="Lanzar los dados para el jugador actual"
)
async def roll_dice_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida")],
    user_id: UserIdDep,
    service: GameServiceDep
) -> schemas.DiceRollResponse:
    """
    Permite al jugador actual lanzar los dados.

    Args:
        game_id: UUID de la partida.
        user_id: ID del usuario (de X-User-ID).
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 400 si falta el encabezado X-User-ID.

    Returns:
        Resultado del lanzamiento de dados incluyendo el color del turno actual.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    updated_game, dice_rolled, roll_val_result, possible_mvs = await service.roll_dice(game_id, user_id)

    return schemas.DiceRollResponse(
        dice1=dice_rolled[0],
        dice2=dice_rolled[1],
        is_pairs=(dice_rolled[0] == dice_rolled[1]),
        roll_validation_result=roll_val_result,
        possible_moves=possible_mvs,
        current_turn_color=updated_game.current_turn_color
    )

@router.post(
    "/games/{game_id}/move",
    response_model=schemas.GameSnapshot,
    summary="Mover una ficha"
)
async def move_piece_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida")],
    move_request: schemas.MovePieceRequest,
    user_id: UserIdDep,
    service: GameServiceDep
) -> schemas.GameSnapshot:
    """
    Permite al jugador actual mover una ficha.

    Args:
        game_id: UUID de la partida.
        move_request: Contiene piece_uuid, target_square_id y steps_used.
        user_id: ID del usuario (de X-User-ID).
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 400 si falta el encabezado X-User-ID.

    Returns:
        Estado completo del juego tras el movimiento.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.move_piece(
        game_id=game_id,
        user_id=user_id,
        piece_uuid_str=str(move_request.piece_uuid),
        target_square_id_from_player=move_request.target_square_id,
        steps_taken_for_move=move_request.steps_used
    )

    board_info = [schemas.SquareInfo.model_validate(sq) for sq_id, sq in game.board.squares.items()]
    player_infos = []
    for p_color, p_obj in game.players.items():
        p_info = schemas.PlayerInfo.model_validate(p_obj)
        p_info.is_current_turn = (game.current_turn_color == p_color and game.state == GameState.IN_PROGRESS)
        player_infos.append(p_info)

    return schemas.GameSnapshot(
        game_id=game.id,
        state=game.state,
        board=board_info,
        players=player_infos,
        turn_order=list(game.turn_order),
        current_turn_color=game.current_turn_color,
        current_player_doubles_count=game.current_player_doubles_count,
        last_dice_roll=game.last_dice_roll,
        winner=game.winner
    )

@router.post(
    "/games/{game_id}/burn-piece",
    response_model=schemas.GameSnapshot,
    summary="Manejar la penalización por tres pares (quemar ficha)"
)
async def burn_piece_three_pairs_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida")],
    burn_request: schemas.BurnPieceRequest,
    user_id: UserIdDep,
    service: GameServiceDep
) -> schemas.GameSnapshot:
    """
    Maneja la penalización por sacar tres pares consecutivos.

    Args:
        game_id: UUID de la partida.
        burn_request: Puede contener piece_uuid a quemar.
        user_id: ID del usuario (de X-User-ID).
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 400 si falta el encabezado X-User-ID.

    Returns:
        Estado completo del juego tras la penalización.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.handle_three_pairs_penalty(
        game_id=game_id,
        user_id=user_id,
        piece_to_burn_uuid_str=str(burn_request.piece_uuid) if burn_request.piece_uuid else None
    )
    board_info = [schemas.SquareInfo.model_validate(sq) for sq_id, sq in game.board.squares.items()]
    player_infos = []
    for p_color, p_obj in game.players.items():
        p_info = schemas.PlayerInfo.model_validate(p_obj)
        p_info.is_current_turn = (game.current_turn_color == p_color and game.state == GameState.IN_PROGRESS)
        player_infos.append(p_info)

    return schemas.GameSnapshot(
        game_id=game.id,
        state=game.state,
        board=board_info,
        players=player_infos,
        turn_order=list(game.turn_order),
        current_turn_color=game.current_turn_color,
        current_player_doubles_count=game.current_player_doubles_count,
        last_dice_roll=game.last_dice_roll,
        winner=game.winner
    )

@router.post(
    "/games/{game_id}/pass-turn",
    response_model=schemas.GameSnapshot,
    summary="Pasar el turno (generalmente cuando no hay movimientos válidos)"
)
async def pass_turn_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida")],
    user_id: UserIdDep,
    service: GameServiceDep
) -> schemas.GameSnapshot:
    """
    Permite al jugador actual pasar su turno.

    Args:
        game_id: UUID de la partida.
        user_id: ID del usuario (de X-User-ID).
        service: Inyección de dependencia para GameService.

    Raises:
        HTTPException: 400 si falta el encabezado X-User-ID.

    Returns:
        Estado completo del juego tras pasar el turno.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.pass_player_turn(game_id, user_id)

    board_info = [schemas.SquareInfo.model_validate(sq) for sq_id, sq in game.board.squares.items()]
    player_infos = []
    for p_color, p_obj in game.players.items():
        p_info = schemas.PlayerInfo.model_validate(p_obj)
        p_info.is_current_turn = (game.current_turn_color == p_color and game.state == GameState.IN_PROGRESS)
        player_infos.append(p_info)

    return schemas.GameSnapshot(
        game_id=game.id,
        state=game.state,
        board=board_info,
        players=player_infos,
        turn_order=list(game.turn_order),
        current_turn_color=game.current_turn_color,
        current_player_doubles_count=game.current_player_doubles_count,
        last_dice_roll=game.last_dice_roll, # Should be None after passing turn
        winner=game.winner
    )