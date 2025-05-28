import httpx
import json
from fastapi import WebSocket
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager

async def handle_move_piece(manager: ConnectionManager, payload: dict, room_id: str, socket: WebSocket):
    try:
        game_id = manager.get_game_id(room_id)
        user_id = manager.get_user_id(socket)

        # Extraer datos del payload
        piece_uuid = payload.get("piece_uuid")
        target_square_id = payload.get("target_square_id")
        steps_used = payload.get("steps_used")

        if not all([piece_uuid, target_square_id is not None, steps_used is not None]):
            await manager.send_personal_message(
                json.dumps({
                    "event": "error",
                    "data": {
                        "message": "Faltan datos en el movimiento."
                    }
                }),
                socket
            )
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/games/{game_id}/move",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "x-user-id": user_id
                },
                json={
                    "piece_uuid": piece_uuid,
                    "target_square_id": target_square_id,
                    "steps_used": steps_used
                }
            )

        if response.status_code == 200:
            move_data = response.json()
            color = manager.get_user_color(user_id)

            # Se elimina "board" si está presente
            move_data.pop("board", None)

            await manager.broadcast(
                json.dumps({
                    "event": "piece_move_result",  # permitido en respuesta
                    "data": move_data,
                    "room_id": room_id
                }),
                room_id
            )

        else:
            await manager.send_personal_message(
                json.dumps({
                    "event": "error",
                    "data": {
                        "message": f"Error al mover la pieza: {response.status_code} - {response.text}"
                    }
                }),
                socket
            )

    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "event": "error",
                "data": {
                    "message": f"Excepción en move_piece: {str(e)}"
                }
            }),
            socket
        )