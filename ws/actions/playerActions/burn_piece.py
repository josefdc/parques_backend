# ws/actions/gameActions/burn_piece.py
import httpx
import json
from fastapi import WebSocket
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager


async def handle_burn_piece(manager: ConnectionManager, payload: dict, room_id: str, socket: WebSocket):
    try:
        game_id = manager.get_game_id(room_id)
        user_id = manager.get_user_id(socket)

        # Extraer datos del payload
        piece_uuid = payload.get("piece_uuid")

        if not piece_uuid:
            await manager.send_personal_message(
                json.dumps({
                    "event": "error",
                    "data": {
                        "message": "Falta el piece_uuid"
                    }
                }),
                socket
            )
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/games/{game_id}/burn_piece",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "x-user-id": user_id
                },
                json={
                    "piece_uuid": piece_uuid
                }
            )

        if response.status_code == 200:
            move_data = response.json()
            color = manager.get_user_color(user_id)

            await manager.broadcast(
                json.dumps({
                    "event": "piece_burn_result",  # respuesta, así que está bien usar "event"
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
                        "message": f"Error al quemar la pieza: {response.status_code} - {response.text}"
                    }
                }),
                socket
            )

    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "event": "error",
                "data": {
                    "message": f"Excepción en burn_piece: {str(e)}"
                }
            }),
            socket
        )