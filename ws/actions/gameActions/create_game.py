# game_actions.py
import httpx
import json
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager

async def handle_create_new_game(payload: dict, manager: ConnectionManager, room_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/games",
                json={
                    "max_players": payload.get("max_players"),
                    "creator_user_id": payload.get("creator_user_id"),
                    "creator_color": payload.get("creator_color")
                },
                headers={"accept": "application/json"}
            )

            if response.status_code == 201:
                game_data = response.json()
                await manager.broadcast(json.dumps({
                    "event": "game_created",
                    "data": game_data,
                    "room_id": room_id
                }))
            else:
                return f"Error creando juego: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Excepción en create_new_game: {str(e)}"

    return None 