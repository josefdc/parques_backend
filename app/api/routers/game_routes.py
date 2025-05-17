"""API Endpoints for Parqués game operations.

This module defines FastAPI routes for creating, joining, starting,
and managing the state of Parqués games.
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
    """Extracts the user ID from the X-User-ID header.

    Args:
        x_user_id: The value of the X-User-ID header, if present.

    Returns:
        The user ID as a string if the header is present, otherwise None.
    """
    # For endpoints that require a user ID, validation is performed within the endpoint.
    # Returning None here allows flexibility for endpoints that might not strictly require it
    # or have alternative ways of identifying the user.
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
    """Creates a new Parqués game.

    The user ID of the creator is taken from the request body.

    Args:
        create_request: Request body containing creator_user_id, creator_color, and max_players.
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 422 if creator_color is invalid.

    Returns:
        Information about the newly created game.
    """
    final_creator_color: Color
    if isinstance(create_request.creator_color, Color):
        final_creator_color = create_request.creator_color
    else:
        # This path is a safeguard. Ideally, Pydantic's field_validator
        # in CreateGameRequest handles the conversion.
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
        # This specific catch can be useful for endpoint-specific logging
        # or error transformation, but the global handler will also catch it.
        raise # Re-raise for the global exception handler.

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
    """Allows a user to join an existing game.

    Args:
        game_id: The UUID of the game to join.
        join_request: Request body containing the user_id and requested_color.
        service: Dependency injection for GameService.

    Returns:
        Updated information about the game after the player has joined.
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
    """Starts a game that is in a 'READY_TO_START' state.

    The user attempting to start the game must be the creator.

    Args:
        game_id: The UUID of the game to start.
        user_id: The ID of the user attempting to start the game (from X-User-ID header).
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 400 if X-User-ID header is missing.

    Returns:
        Information about the game after it has started.
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
    """Retrieves the complete current state of a game.

    Args:
        game_id: The UUID of the game.
        service: Dependency injection for GameService (used to access repository).

    Raises:
        HTTPException: 404 if the game is not found.

    Returns:
        A snapshot of the game's current state.
    """
    # Direct repository access for reads can be an option,
    # or a dedicated get_game method in GameService.
    game = await service._repository.get_by_id(game_id)
    if not game:
        # GameNotFoundError from the service would be caught by the global handler.
        # If accessing repo directly, raise HTTPException.
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
    """Allows the current player to roll the dice.

    Args:
        game_id: The UUID of the game.
        user_id: The ID of the user rolling the dice (from X-User-ID header).
                 Must match the current player's turn.
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 400 if X-User-ID header is missing.

    Returns:
        The result of the dice roll, including validation and possible moves.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    _game, dice_rolled, roll_val_result, possible_mvs = await service.roll_dice(game_id, user_id)

    # The _game object returned by service.roll_dice is already updated and saved.
    # We only need to return the specific dice roll response.
    return schemas.DiceRollResponse(
        dice1=dice_rolled[0],
        dice2=dice_rolled[1],
        is_pairs=(dice_rolled[0] == dice_rolled[1]),
        roll_validation_result=roll_val_result,
        possible_moves=possible_mvs
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
    """Allows the current player to move a piece.

    Args:
        game_id: The UUID of the game.
        move_request: Request body containing piece_uuid, target_square_id, and steps_used.
        user_id: The ID of the user making the move (from X-User-ID header).
                 Must match the current player's turn.
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 400 if X-User-ID header is missing.

    Returns:
        The complete game state after the move.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.move_piece(
        game_id=game_id,
        user_id=user_id,
        piece_uuid_str=str(move_request.piece_uuid),
        target_square_id_from_player=move_request.target_square_id,
        steps_taken_for_move=move_request.steps_used
        # original_dice_roll is taken from game.last_dice_roll within the service
    )

    # Construct the GameSnapshot response
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
    """Handles the penalty for rolling three consecutive pairs.

    The current player may choose a piece to burn; otherwise, the service
    determines the piece to burn based on game rules.

    Args:
        game_id: The UUID of the game.
        burn_request: Request body optionally containing the piece_uuid to burn.
        user_id: The ID of the user who rolled three pairs (from X-User-ID header).
                 Must match the current player's turn.
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 400 if X-User-ID header is missing.

    Returns:
        The complete game state after the penalty is applied.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.handle_three_pairs_penalty(
        game_id=game_id,
        user_id=user_id,
        piece_to_burn_uuid_str=str(burn_request.piece_uuid) if burn_request.piece_uuid else None
    )
    # Construct and return GameSnapshot
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
    """Allows the current player to pass their turn.

    This is typically used when the player has no valid moves after rolling the dice.

    Args:
        game_id: The UUID of the game.
        user_id: The ID of the user passing the turn (from X-User-ID header).
                 Must match the current player's turn.
        service: Dependency injection for GameService.

    Raises:
        HTTPException: 400 if X-User-ID header is missing.

    Returns:
        The complete game state after the turn has been passed.
    """
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.pass_player_turn(game_id, user_id)

    # Construct and return GameSnapshot
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