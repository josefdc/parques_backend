
# WebSocket API - Parqués

Este documento describe los eventos WebSocket disponibles para la integración cliente-servidor en el juego de Parqués.

## Conexión

- URL del WebSocket: `ws://<host>/ws/{game_id}/{user_id}`
- Reemplaza `<host>`, `game_id` y `user_id` con los valores correspondientes. ex (ws://127.0.0.1:8000/ws/game/pene-room)


## Eventos de Entrada (cliente → servidor)

### 1. `create_game`
Crea una nueva partida.

```json
{
  "action": "create_new_game",
  "payload": {
    "max_players": 4
  }
}
```

### 2. `start_game`
Inicia la partida cuando todos los jugadores estén listos.

```json
{
  "action": "game_start"
}
```

### 3. `roll_dice`
Lanza los dados.

```json
{
  "event": "roll_dice"
}
```

### 4. `move_piece`
Mueve una ficha luego de lanzar los dados.

```json
{
  "event": "move_piece",
  "data": {
    "piece_uuid": "<UUID_DE_LA_FICHA>",
    "target_square_id": "<ID_DE_LA_CASILLA_DESTINO>",
    "steps_used": "<NUMERO_DE_PASOS_UTILIZADOS>"
  }
}
```

## Notas

- Los websockets tienen la capacidad de controlar el user id y el session id
- Los mensajes deben estar codificados en JSON.
- El servidor puede emitir mensajes tipo `broadcast` para todos los jugadores.

