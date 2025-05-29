# manager.py
import uuid
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}            # room_id -> websockets
        self.user_ids: Dict[WebSocket, str] = {}               # websocket -> user_id  
        self.user_colors: Dict[str, str] = {}                  # user_id -> color
        self.room_color_index: Dict[str, int] = {}             # room_id -> color index        
        self.room_game_map: Dict[str, str] = {}                # room_id -> game_id
        self.room_creators: Dict[str, WebSocket] = {}          # room_id -> host websocket

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(websocket)

        # Generar user_id único para este websocket
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        self.user_ids[websocket] = user_id

    def disconnect(self, websocket: WebSocket):
        for room_id, connections in self.rooms.items():
            if websocket in connections:
                connections.remove(websocket)
                
                # Eliminar user_id asociado
                self.user_ids.pop(websocket, None)

                # Verificar si la sala quedó vacía
                if not connections:
                    self.cleanup_room(room_id)
                break

    def cleanup_room(self, room_id: str):
        print(f"Cleaning up room: {room_id}")

        # Eliminar la sala y todos sus datos asociados
        self.rooms.pop(room_id, None)
        self.room_color_index.pop(room_id, None)
        self.room_game_map.pop(room_id, None)
        self.room_creators.pop(room_id, None)

        # También puedes eliminar colores de usuarios que estaban en esa sala (opcional)
        user_ids_to_remove = [
            user_id for ws, user_id in self.user_ids.items()
            if ws not in self.get_room_connections(room_id)
        ]
        for user_id in user_ids_to_remove:
            self.user_colors.pop(user_id, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room_id: str):
        for connection in self.rooms.get(room_id, []):
            await connection.send_text(message)

    def get_room_connections(self, room_id: str) -> List[WebSocket]:
        return self.rooms.get(room_id, [])

    def get_user_id(self, websocket: WebSocket) -> str:
        return self.user_ids.get(websocket)
    
    def set_user_color(self, user_id: str, color: str):
        self.user_colors[user_id] = color

    def get_user_color(self, user_id: str) -> str:
        return self.user_colors.get(user_id)
    
    def assign_color(self, user_id: str, room_id: str) -> str:
        color_order = ["RED", "YELLOW", "BLUE", "GREEN"]

        # Inicializar índice si no existe
        if room_id not in self.room_color_index:
            self.room_color_index[room_id] = 0

        index = self.room_color_index[room_id]
        color = color_order[index % len(color_order)]

        self.user_colors[user_id] = color
        self.room_color_index[room_id] += 1

        return color

    def set_game_for_room(self, room_id: str, game_id: str):
        self.room_game_map[room_id] = game_id

    def get_game_id(self, room_id: str) -> str:
        return self.room_game_map.get(room_id)
    
    def set_room_creator(self, room_id: str, websocket: WebSocket):
        self.room_creators[room_id] = websocket

    def is_creator(self, room_id: str, websocket: WebSocket) -> bool:
        return self.room_creators.get(room_id) == websocket