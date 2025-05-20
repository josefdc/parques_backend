from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.domain.game import MAX_PLAYERS
from .manager import ConnectionManager
from app.services.game_service import GameService
from app.core.enums import Color
from app.services.game_service import MoveValidator
from app.services.game_service import Dice
import json
from app.repositories.base_repository import GameRepository
from app.repositories.game_repositoryimpl import GameRepositoryImpl

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):

    # Instancias singleton de dependencias para el GameService
    repository: GameRepository = GameRepositoryImpl()
    validator = MoveValidator()
    dice_roller = Dice()
    game_service = GameService(repository, validator, dice_roller)



    await manager.connect(websocket)
    try:
        await manager.send_personal_message(f"Bienvenido a la sala {room_id}", websocket)

        await manager.broadcast(f"Un nuevo jugador se unió a la sala {room_id}")
        
        while True:
            data_text = await websocket.receive_text()
            await manager.broadcast(f"[{room_id}] x {data}")

            
            try:
                data = json.loads(data_text)
                action = data.get("action")
                payload = data.get("payload", {})

                if action == "create_new_game":
                    creator_user_id = payload.get("creator_user_id")
                    color_str = payload.get("creator_color")
                    max_players = payload.get("max_players", MAX_PLAYERS)

                    # Convertir string a Enum
                    creator_color = Color[color_str.upper()]

                    # Llamar función
                    game = await game_service.create_new_game(
                        creator_user_id=creator_user_id,
                        creator_color=creator_color,
                        max_players=max_players
                    )

                    # Usar retorno en broadcast
                    await manager.broadcast(f"Juego creado: {game}")

                else:
                    await manager.send_personal_message("Acción no reconocida", websocket)

            except Exception as e:
                await manager.send_personal_message(f"Error: {str(e)}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Un jugador salió de la sala {room_id}")