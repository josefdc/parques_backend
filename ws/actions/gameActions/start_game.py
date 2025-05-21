# ws/actions/gameActions/start_game.py
import httpx
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager
from fastapi import WebSocket

async def handle_start_game(manager, room_id: str, websocket: WebSocket):
    try:
        game_id = manager.get_game_id(room_id)
        creator_user_id = manager.get_user_id(websocket)


        if not game_id or not creator_user_id:
            return "Faltan campos obligatorios: 'game_id' y 'creator_user_id'."

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
            await manager.broadcast(f"La partida {game_id} ha comenzado.", room_id)
            await manager.broadcast(
                response.text,
                room_id
            )
        else:
            return f"Error al iniciar el juego: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Excepción en game_start: {str(e)}"

    return None