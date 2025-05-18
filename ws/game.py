from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket)
    try:
        await manager.send_personal_message(f"Bienvenido a la sala {room_id}", websocket)

        await manager.broadcast(f"📢 Un nuevo jugador se unió a la sala {room_id}")
        
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"[{room_id}] 🗨️ {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"❌ Un jugador salió de la sala {room_id}")