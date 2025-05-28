import httpx
import json
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager
from fastapi import WebSocket

async def handle_roll_dice(manager: ConnectionManager, room_id: str, socket: WebSocket):
    try:
        game_id = manager.get_game_id(room_id)
        user_id = manager.get_user_id(socket)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/games/{game_id}/roll",
                headers={
                    "accept": "application/json",
                    "x-user-id": user_id
                }
            )

        if response.status_code == 200:
            roll_data = response.json()
            dice1 = roll_data.get("dice1")
            dice2 = roll_data.get("dice2")
            color = manager.get_user_color(user_id)

            # Enviar resultado privado al usuario (respuesta directa)
            await manager.send_personal_message(
                json.dumps({
                    "event": "dice_roll_result",
                    "data": roll_data
                }),
                socket
            )

            # Broadcast del evento a la sala (respuesta directa)
            await manager.broadcast(
                json.dumps({
                    "event": "dice_rolled",
                    "data": {
                        "user_id": user_id,
                        "color": color,
                        "dice1": dice1,
                        "dice2": dice2
                    },
                    "room_id": room_id
                }),
                room_id
            )

        else:
            await manager.send_personal_message(
                json.dumps({
                    "action": "error",
                    "payload": {
                        "message": f"Error al lanzar los dados: {response.status_code} - {response.text}"
                    }
                }),
                socket
            )

    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "action": "error",
                "payload": {
                    "message": f"Excepción en roll_dice: {str(e)}"
                }
            }),
            socket
        )