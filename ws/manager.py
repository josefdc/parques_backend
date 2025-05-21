# manager.py
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Diccionario de room_id -> lista de conexiones
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket):
        for room_id, connections in self.rooms.items():
            if websocket in connections:
                connections.remove(websocket)
                break

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room_id: str):
        for connection in self.rooms.get(room_id, []):
            await connection.send_text(message)

    def get_room_connections(self, room_id: str) -> List[WebSocket]:
        return self.rooms.get(room_id, [])