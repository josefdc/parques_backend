# ws/actions/gameActions/create_game.py
import httpx
import json
from ws.config import API_BASE_URL
from ws.manager import ConnectionManager
from fastapi import WebSocket


async def handle_create_new_game(payload: dict, manager: ConnectionManager, room_id: str, creator_socket: WebSocket):
    try:
        creator_user_id = manager.get_user_id(creator_socket)
        creator_color = manager.assign_color(creator_user_id, room_id)

        async with httpx.AsyncClient() as client:
            # Crear juego
            response = await client.post(
                f"{API_BASE_URL}/games",
                json={
                    "max_players": payload.get("max_players"),
                    "creator_user_id": creator_user_id,
                    "creator_color": creator_color
                },
                headers={"accept": "application/json"}
            )

            if response.status_code == 201:
                game_data = response.json()
                game_id = game_data["id"]

                # Guardar game_id para la sala
                manager.set_game_for_room(room_id, game_id)
                manager.set_room_creator(room_id, creator_socket)

                # Notificar a todos que se creó el juego
                await manager.broadcast(json.dumps({
                    "event": "game_created",
                    "data": game_data,
                    "room_id": room_id
                }), room_id)

                # Confirmar al creador
                await manager.send_personal_message(
                    json.dumps({
                        "event": "you_joined",
                        "data": {
                            "message": f"Te uniste exitosamente como {creator_color}",
                            "color": creator_color,
                            "user_id": creator_user_id
                        },
                        "room_id": room_id
                    }),
                    creator_socket
                )

                await manager.broadcast(json.dumps({
                    "event": "player_joined",
                    "data": {
                        "user_id": creator_user_id,
                        "color": creator_color
                    },
                    "room_id": room_id
                }), room_id)

                # Unir automáticamente al resto de conexiones en la sala
                connections = manager.get_room_connections(room_id)

                for ws in connections:
                    if ws == creator_socket:
                        continue

                    try:
                        user_id = manager.get_user_id(ws)
                        color = manager.assign_color(user_id, room_id)

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
                            # Confirmación privada al jugador que se unió
                            await manager.send_personal_message(
                                json.dumps({
                                    "event": "you_joined",
                                    "data": {
                                        "message": f"Te uniste exitosamente como {color}",
                                        "color": color,
                                        "user_id": user_id
                                    },
                                    "room_id": room_id
                                }),
                                ws
                            )

                            # Notificación global de nuevo jugador
                            await manager.broadcast(json.dumps({
                                "event": "player_joined",
                                "data": {
                                    "user_id": user_id,
                                    "color": color
                                },
                                "room_id": room_id
                            }), room_id)
                    except Exception as e:
                        await manager.send_personal_message(
                            f"Error inesperado al unir al juego: {str(e)}",
                            ws
                        )
            else:
                return f"Error creando juego: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Excepción en create_new_game: {str(e)}"

    return None