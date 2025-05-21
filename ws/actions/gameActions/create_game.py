import httpx
import json
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager
import uuid
from fastapi import WebSocket

async def handle_create_new_game(payload: dict, manager: ConnectionManager, room_id: str, creator_socket: WebSocket):
    try:
        async with httpx.AsyncClient() as client:
            # Crear juego
            response = await client.post(
                f"{API_BASE_URL}/games",
                json={
                    "max_players": payload.get("max_players"),
                    "creator_user_id": payload.get("creator_user_id"),
                    "creator_color": payload.get("creator_color")  # Ej: "RED"
                },
                headers={"accept": "application/json"}
            )

            if response.status_code == 201:
                game_data = response.json()
                game_id = game_data["id"]
                creator_user_id = payload.get("creator_user_id")
                creator_color = payload.get("creator_color")

                # Notificar creación del juego
                await manager.broadcast(json.dumps({
                    "event": "game_created",
                    "data": game_data,
                    "room_id": room_id
                }), room_id)

                # Confirmar al creador que fue unido como RED (u otro color)
                await manager.send_personal_message(
                    f"Te uniste exitosamente como {creator_color}",
                    creator_socket
                )

                # Hacer broadcast de la unión del creador
                await manager.broadcast(json.dumps({
                    "event": "player_joined",
                    "data": {
                        "user_id": creator_user_id,
                        "color": creator_color
                    },
                    "room_id": room_id
                }), room_id)

                # Unir al resto de jugadores conectados a la sala
                connections = manager.get_room_connections(room_id)
                color_list = ["BLUE", "GREEN", "YELLOW"]
                color_index = 0

                for ws in connections:
                    if ws == creator_socket:
                        continue  # Saltar al creador

                    user_id = f"user_{uuid.uuid4().hex[:6]}"
                    
                    # Saltar el color usado por el creador
                    while color_list[color_index % len(color_list)] == creator_color:
                        color_index += 1
                    
                    color = color_list[color_index % len(color_list)]
                    color_index += 1

                    join_response = await client.post(
                        f"{API_BASE_URL}/games/{game_id}/join",
                        json={
                            "user_id": user_id,
                            "color": color
                        },
                        headers={
                            "accept": "application/json",
                            "Content-Type": "application/json"
                        }
                    )

                    if join_response.status_code != 200:
                        await manager.send_personal_message(
                            f"Error al unir usuario {user_id}: {join_response.status_code} - {join_response.text}",
                            ws
                        )
                    else:
                        await manager.send_personal_message(
                            f"Te uniste exitosamente como {color}",
                            ws
                        )

                        # Hacer broadcast de la unión de este jugador
                        await manager.broadcast(json.dumps({
                            "event": "player_joined",
                            "data": {
                                "user_id": user_id,
                                "color": color
                            },
                            "room_id": room_id
                        }), room_id)

            else:
                return f"Error creando juego: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Excepción en create_new_game: {str(e)}"

    return None