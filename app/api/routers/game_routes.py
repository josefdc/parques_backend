#app/api/routers/game_routes.py
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status, Header
from typing import Annotated, Optional
import uuid

# from app.services.game_service import GameService, GameServiceError # GameServiceError might still be needed if specific errors are caught here
from app.models import schemas
from app.core.enums import Color, GameState # Importar GameState si se usa en PlayerInfo
# --- IMPORTACIÓN CAMBIADA ---
from app.core.dependencies import GameServiceDep 
# ---------------------------
# GameServiceError can be imported from app.services.game_service if needed for specific handling
from app.services.game_service import GameServiceError


router = APIRouter()

# Simulación de obtención de user_id (puede quedarse aquí o moverse a dependencies.py)
async def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> Optional[str]:
    if not x_user_id:
        # Para endpoints que lo necesitan, se valida dentro del endpoint.
        # Consider raising HTTPException(status_code=400, detail="X-User-ID header missing")
        # if a user ID is strictly required for all routes using this dependency.
        # For now, returning None and letting endpoints handle it is fine.
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
    service: GameServiceDep, # <- Usa la dependencia importada
    # user_id: UserIdDep # El creator_user_id viene en el body
):
    # El user_id del creador ya está en create_request.creator_user_id
    # No necesitamos UserIdDep aquí a menos que queramos validar que
    # el x_user_id del header coincide con el creator_user_id del body.
    # Por ahora, asumimos que el creator_user_id del body es la fuente de verdad.
    
    final_creator_color: Color
    if isinstance(create_request.creator_color, Color):
        final_creator_color = create_request.creator_color
    else:
        try:
            # This path should ideally not be hit if the field_validator in CreateGameRequest
            # successfully converts the input to a Color enum instance.
            # However, as a safeguard, or if the validator isn't 'before' or Pydantic's behavior changes.
            final_creator_color = Color(create_request.creator_color) 
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Valor inválido para creator_color: '{create_request.creator_color}'. Valores permitidos son {[(m.name, m.value) for m in Color]}"
            )

    try:
        game = await service.create_new_game(
            creator_user_id=create_request.creator_user_id, 
            creator_color=final_creator_color, # <--- Usar la instancia del enum convertida/validada
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
            players=player_infos, # Asegúrate que PlayerInfo no cause problemas de serialización con Enums
            created_at=game.created_at # Asumiendo que GameAggregate tiene created_at
        )
    except GameServiceError as e:
        # Este catch es opcional si el manejador global es suficiente.
        # Podría ser útil para logging específico del endpoint o transformar el error.
        # Por ahora, el manejador global se encargará.
        raise # Re-lanza para que el manejador global lo capture.

@router.post(
    "/games/{game_id}/join",
    response_model=schemas.GameInfo,
    summary="Unirse a una partida existente"
)
async def join_game_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="El ID de la partida a la que unirse")],
    join_request: schemas.JoinGameRequest, # user_id y color están aquí
    service: GameServiceDep
):
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
    response_model=schemas.GameInfo, # O GameSnapshot si prefieres devolver el estado completo
    summary="Iniciar una partida que está lista"
)
async def start_game_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida a iniciar")],
    user_id: UserIdDep, # Obtener user_id (del header X-User-ID para este ejemplo)
    service: GameServiceDep
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido para iniciar la partida.")
    
    game = await service.start_game(game_id, user_id)
    
    player_infos = [
        schemas.PlayerInfo.model_validate(p) for p in game.players.values()
    ]
    for p_info in player_infos:
        p_info.is_current_turn = (game.current_turn_color == p_info.color and game.state == GameState.IN_PROGRESS)
        
    return schemas.GameInfo( # Devolvemos GameInfo por consistencia con create/join
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
    service: GameServiceDep # Aunque no usemos service, es bueno tenerlo por si evoluciona
):
    # Acceso directo al repo para leer es una opción, o añadir un método get_game a GameService
    game = await service._repository.get_by_id(game_id) 
    if not game:
        # La excepción GameNotFoundError será capturada por el manejador global si se lanza desde el servicio
        # Si accedemos directo al repo, lanzamos HTTPException directamente
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
    user_id: UserIdDep, # Obtener user_id del header
    service: GameServiceDep
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    _game, dice_rolled, roll_val_result, possible_mvs = await service.roll_dice(game_id, user_id)
    
    # El _game devuelto por roll_dice ya está actualizado y guardado.
    # No necesitamos construir GameSnapshot aquí, solo la respuesta específica del roll.
    return schemas.DiceRollResponse(
        dice1=dice_rolled[0],
        dice2=dice_rolled[1],
        is_pairs=(dice_rolled[0] == dice_rolled[1]),
        roll_validation_result=roll_val_result,
        possible_moves=possible_mvs
    )

@router.post(
    "/games/{game_id}/move",
    response_model=schemas.GameSnapshot, # Devolver el estado completo del juego después del movimiento
    summary="Mover una ficha"
)
async def move_piece_endpoint(
    game_id: Annotated[uuid.UUID, Path(description="ID de la partida")],
    move_request: schemas.MovePieceRequest, # Contiene piece_uuid, target_square_id, steps_used
    user_id: UserIdDep, # Obtener user_id del header
    service: GameServiceDep
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.move_piece(
        game_id=game_id,
        user_id=user_id,
        piece_uuid_str=str(move_request.piece_uuid), # Convertir UUID a string si GameService lo espera así
        target_square_id_from_player=move_request.target_square_id,
        steps_taken_for_move=move_request.steps_used
        # original_dice_roll se toma de game.last_dice_roll dentro del servicio
    )
    
    # Reutilizar la lógica de get_game_state_endpoint para construir el snapshot
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
    burn_request: schemas.BurnPieceRequest, # Contiene el piece_uuid opcional a quemar
    user_id: UserIdDep, # Jugador que cometió la falta (debe ser el current_player)
    service: GameServiceDep
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")

    game = await service.handle_three_pairs_penalty(
        game_id=game_id,
        user_id=user_id,
        piece_to_burn_uuid_str=str(burn_request.piece_uuid) if burn_request.piece_uuid else None
    )
    # Construir y devolver GameSnapshot similar a move_piece_endpoint
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
    user_id: UserIdDep, # Jugador que está pasando el turno
    service: GameServiceDep
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-ID header es requerido.")
    
    game = await service.pass_player_turn(game_id, user_id)
    
    # Construir y devolver GameSnapshot
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
        last_dice_roll=game.last_dice_roll, # Debería ser None después de pasar turno
        winner=game.winner
    )