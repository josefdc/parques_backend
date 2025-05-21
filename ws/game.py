# websocket_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import ConnectionManager
from .actions.gameActions.create_game import handle_create_new_game
from .actions.gameActions.start_game import handle_start_game
import json


router = APIRouter()
manager = ConnectionManager()

# game.py
@router.websocket("/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        await manager.send_personal_message(f"Bienvenido a la sala {room_id}", websocket)
        await manager.broadcast(f"Un nuevo jugador se unió a la sala {room_id}", room_id)

        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                payload = data.get("payload", {})

                if action == "create_new_game":
                    error_msg = await handle_create_new_game(payload, manager, room_id, websocket)
                    if error_msg:
                        await manager.send_personal_message(error_msg, websocket)
                elif action == "game_start":
                    error_msg = await handle_start_game(payload, manager, room_id)
                    if error_msg:
                        await manager.send_personal_message(error_msg, websocket)
                else:
                    await manager.send_personal_message("Acción no reconocida", websocket)

            except Exception as e:
                await manager.send_personal_message(f"Error: {str(e)}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Un jugador salió de la sala {room_id}", room_id)