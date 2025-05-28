# ws/actions/gameActions/start_game.py
import httpx
import json
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager
from fastapi import WebSocket


async def handle_start_game(manager: ConnectionManager, room_id: str, caller_socket: WebSocket):
    try:
        if not manager.is_creator(room_id, caller_socket):
            return {
                "event": "error",
                "data": {
                    "message": "Solo el creador de la partida puede iniciarla."
                }
            }

        game_id = manager.get_game_id(room_id)
        creator_user_id = manager.get_user_id(caller_socket)

        if not game_id or not creator_user_id:
            return {
                "event": "error",
                "data": {
                    "message": "No se encontró game_id o user_id en el contexto de esta sala."
                }
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/games/{game_id}/start",
                headers={
                    "accept": "application/json",
                    "x-user-id": creator_user_id
                },
                data=""
            )

        if response.status_code == 200:
            game_data = response.json()

            await manager.broadcast(json.dumps({
                "action": "game_started",
                "payload": game_data,
                "room_id": room_id
            }), room_id)
        else:
            return {
                "event": "error",
                "data": {
                    "message": f"Error al iniciar el juego: {response.status_code} - {response.text}"
                }
            }

    except Exception as e:
        return {
            "event": "error",
            "data": {
                "message": f"Excepción en game_start: {str(e)}"
            }
        }

    return None