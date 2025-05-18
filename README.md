# Backend API del Juego de Parqués Distribuido

Esta API ha sido desarrollada con FastAPI y está diseñada para ser consumida por clientes (como una aplicación web o móvil) para permitir a los usuarios jugar partidas de Parqués en red.

## 1. Visión General del Proyecto

El objetivo de este proyecto es implementar un juego de Parqués multijugador (2 a 4 jugadores) donde toda la lógica del juego reside en el servidor, y los clientes interactúan a través de esta API RESTful. Los clientes se encargarán de la representación gráfica y de enviar las acciones del usuario al servidor.

**Tecnologías Clave:**
* **Backend:** Python, FastAPI
* **Gestor de Paquetes y Entorno Virtual:** UV (ver `uv.lock` y `pyproject.toml`)
* **Testing:** Pytest, `httpx.AsyncClient` para tests de API.

## 2. Configuración del Entorno

Si necesitas correr el backend localmente para desarrollo o pruebas:

1.  **Clona el Repositorio:**
    ```bash
    git clone https://github.com/josefdc/parques_backend/
    cd parques_backend
    ```

2.  **Crea y Activa un Entorno Virtual con UV:**
    * Asegúrate de tener [UV instalado](https://github.com/astral-sh/uv).
    * Desde la raíz del proyecto (`parques_backend`):
        ```bash
        uv venv  # Crea un entorno virtual llamado .venv
        source .venv/bin/activate  # En Linux/macOS
        # .venv\Scripts\activate   # En Windows
        ```

3.  **Instala las Dependencias:**
    ```bash
    # o, si las dependencias bien definidas en pyproject.toml:
    uv sync
    ```

4.  **Ejecuta el Servidor de Desarrollo (FastAPI con Uvicorn):**
    El punto de entrada principal de la aplicación es `app/main.py`.
    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    * `--reload`: El servidor se reiniciará automáticamente con los cambios en el código.
    * `--host 0.0.0.0`: Permite el acceso desde otras máquinas en tu red local 
    * `--port 8000`: Puerto estándar, ajústalo si es necesario.

5.  **Accede a la Documentación Interactiva de la API (Swagger UI):**
    Una vez que el servidor esté corriendo, abre tu navegador y ve a:
    `http://127.0.0.1:8000/docs`

    Allí encontrarás una lista de todos los endpoints, sus parámetros, esquemas de solicitud/respuesta y podrás probarlos directamente.

## 3. Arquitectura de la API

La API sigue un diseño RESTful y se organiza alrededor del recurso principal: `Game` (Partida).

* **Prefijo Base:** `/api/v1`
* **Autenticación/Identificación de Usuario:** Para los endpoints que requieren identificar al jugador que realiza la acción (ej. iniciar partida, lanzar dados, mover ficha), se espera un encabezado HTTP:
    * `X-User-ID: <id_del_usuario_que_realiza_la_accion>`

## 4. Endpoints Principales de la API

A continuación, se describen los endpoints más importantes que el frontend necesitará para interactuar con el juego. **Por favor, consulta siempre `http://127.0.0.1:8000/docs` para la información más actualizada y detallada sobre los esquemas de solicitud y respuesta.**

---

### 4.1. Gestión de Partidas

#### **POST** `/api/v1/games`
* **Descripción:** Crea una nueva partida de Parqués.
* **Cuerpo de la Solicitud (`CreateGameRequest`):**
    ```json
    {
      "max_players": 2, // (int) Mínimo 2, Máximo 4 (según config actual)
      "creator_user_id": "nombre_usuario_creador", // (str)
      "creator_color": "RED" // (str) Colores válidos: "RED", "GREEN", "BLUE", "YELLOW"
    }
    ```
* **Respuesta Exitosa (`201 Created` - `GameInfo`):**
    ```json
    {
      "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef", // UUID de la partida
      "state": "waiting_players", // Estado inicial
      "max_players": 2,
      "current_player_count": 1,
      "players": [
        {
          "user_id": "nombre_usuario_creador",
          "color": "RED",
          "pieces": [ /* Array de PieceInfo, todas en cárcel inicialmente */ ],
          "is_current_turn": false,
          "consecutive_pairs_count": 0
        }
      ],
      "created_at": "2025-05-17T15:30:00.123Z"
    }
    ```
* **Posibles Errores:**
    * `422 Unprocessable Entity`: Si los datos de la solicitud son inválidos (ej. color inválido, `max_players` fuera de rango).
    * `400 Bad Request`: Si el `GameService` detecta un error lógico al crear (ej. no se pudo añadir el creador).

---

#### **POST** `/api/v1/games/{game_id}/join`
* **Descripción:** Permite a un usuario unirse a una partida existente que esté en estado `waiting_players`.
* **Parámetros de Ruta:**
    * `game_id` (UUID): ID de la partida.
* **Cuerpo de la Solicitud (`JoinGameRequest`):**
    ```json
    {
      "user_id": "nombre_usuario_que_se_une", // (str)
      "color": "BLUE" // (str) Color solicitado
    }
    ```
* **Respuesta Exitosa (`200 OK` - `GameInfo`):** Similar a `create_game`, pero con el nuevo jugador añadido y el estado posiblemente actualizado a `ready_to_start`.
* **Posibles Errores:**
    * `404 Not Found`: Si `game_id` no existe.
    * `400 Bad Request` (o similar, ver manejador de `GameServiceError`):
        * "La partida no está esperando jugadores."
        * "La partida ya está llena."
        * "El color [COLOR] ya está tomado."
        * "El usuario [USER_ID] ya está en la partida con el color [COLOR_EXISTENTE]."

---

#### **POST** `/api/v1/games/{game_id}/start`
* **Descripción:** Inicia una partida que está en estado `ready_to_start`.
* **Parámetros de Ruta:**
    * `game_id` (UUID): ID de la partida.
* **Encabezados Requeridos:**
    * `X-User-ID`: ID del usuario que intenta iniciar la partida (debe ser un jugador de la partida, típicamente el creador).
* **Respuesta Exitosa (`200 OK` - `GameInfo`):** Información de la partida con estado `in_progress` y el turno asignado.
* **Posibles Errores:**
    * `400 Bad Request`: Si falta el header `X-User-ID`.
    * `404 Not Found`: Si `game_id` no existe.
    * `400 Bad Request` (o similar):
        * "Usuario [USER_ID] no tiene permiso para iniciar la partida [GAME_ID]."
        * "La partida no está lista para iniciar o ya ha comenzado."
        * "Se necesitan al menos [MIN_PLAYERS] jugadores para iniciar."

---

#### **GET** `/api/v1/games/{game_id}/state`
* **Descripción:** Obtiene el estado completo y actual de una partida. Este es el endpoint principal que el frontend usará para renderizar el tablero y el estado del juego.
* **Parámetros de Ruta:**
    * `game_id` (UUID): ID de la partida.
* **Respuesta Exitosa (`200 OK` - `GameSnapshot`):**
    ```json
    {
      "game_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "state": "in_progress", // o "waiting_players", "ready_to_start", "finished"
      "board": [ /* Array de SquareInfo detallando cada casilla y sus ocupantes */ ],
      "players": [ /* Array de PlayerInfo con el estado de cada jugador y sus fichas */ ],
      "turn_order": ["RED", "BLUE"], // Array de colores indicando el orden de turnos
      "current_turn_color": "RED", // Color del jugador en turno (null si no ha empezado o terminó)
      "current_player_doubles_count": 0, // Pares consecutivos del jugador actual en este turno del juego
      "last_dice_roll": null, // o [dado1, dado2] si se lanzaron dados y se debe mover
      "winner": null // o el color del ganador si "state" es "finished"
    }
    ```
* **Posibles Errores:**
    * `404 Not Found`: Si `game_id` no existe.

---

### 4.2. Acciones del Jugador

Estos endpoints requieren el header `X-User-ID`.

#### **POST** `/api/v1/games/{game_id}/roll`
* **Descripción:** El jugador actual (identificado por `X-User-ID`) lanza los dados.
* **Parámetros de Ruta:** `game_id` (UUID).
* **Encabezados Requeridos:** `X-User-ID`.
* **Respuesta Exitosa (`200 OK` - `DiceRollResponse`):**
    ```json
    {
      "dice1": 3,
      "dice2": 3,
      "is_pairs": true,
      "roll_validation_result": "ok", // o "three_pairs_burn"
      "possible_moves": { // Diccionario: piece_uuid -> lista de movimientos [(target_id, result_type, steps_used), ...]
        "uuid_ficha_1": [
          [0, "jail_exit_success", 0] // Ejemplo salida de cárcel
        ],
        "uuid_ficha_2": [] // Quizás no tiene movimientos con este tiro
      }
    }
    ```
* **Posibles Errores:**
    * `400 Bad Request`: Si falta `X-User-ID`.
    * `404 Not Found`: Si `game_id` no existe o `user_id` no está en la partida.
    * `403 Forbidden`: Si no es el turno del jugador.
    * `400 Bad Request`: "La partida no está en curso.", "Ya has lanzado los dados..."

---

#### **POST** `/api/v1/games/{game_id}/move`
* **Descripción:** El jugador actual mueve una ficha elegida.
* **Parámetros de Ruta:** `game_id` (UUID).
* **Encabezados Requeridos:** `X-User-ID`.
* **Cuerpo de la Solicitud (`MovePieceRequest`):**
    ```json
    {
      "piece_uuid": "uuid_de_la_ficha_a_mover",
      "target_square_id": 5, // o una tupla como ["pas", "RED", 0]
      "steps_used": 3 // El valor del dado (d1, d2, o d1+d2) usado para este movimiento
    }
    ```
* **Respuesta Exitosa (`200 OK` - `GameSnapshot`):** El estado completo del juego actualizado.
* **Posibles Errores:**
    * `400 Bad Request`: Falta `X-User-ID`, datos de solicitud inválidos.
    * `404 Not Found`: Partida o ficha no encontrada.
    * `403 Forbidden`: No es el turno del jugador.
    * `400 Bad Request`: "Debes lanzar los dados antes de mover.", "Movimiento inválido..." (con detalles).

---

#### **POST** `/api/v1/games/{game_id}/burn-piece`
* **Descripción:** Maneja la penalización por tres pares. El jugador (identificado por `X-User-ID`) puede opcionalmente elegir qué ficha quemar. Si no se especifica, el servidor elige.
* **Parámetros de Ruta:** `game_id` (UUID).
* **Encabezados Requeridos:** `X-User-ID`.
* **Cuerpo de la Solicitud (`BurnPieceRequest`):**
    ```json
    {
      "piece_uuid": "uuid_de_la_ficha_a_quemar" // Opcional
    }
    ```
* **Respuesta Exitosa (`200 OK` - `GameSnapshot`):** El estado completo del juego actualizado (ficha quemada, turno pasado).
* **Posibles Errores:**
    * `400 Bad Request`: Falta `X-User-ID`.
    * `404 Not Found`: Partida no encontrada.
    * `400 Bad Request`: "El jugador no está en condición de ser penalizado..."

---

#### **POST** `/api/v1/games/{game_id}/pass-turn`
* **Descripción:** El jugador actual pasa su turno. Esto usualmente ocurre si, después de lanzar los dados, no tiene movimientos válidos.
* **Parámetros de Ruta:** `game_id` (UUID).
* **Encabezados Requeridos:** `X-User-ID`.
* **Respuesta Exitosa (`200 OK` - `GameSnapshot`):** El estado completo del juego actualizado con el turno pasado al siguiente jugador.
* **Posibles Errores:**
    * `400 Bad Request`: Falta `X-User-ID`.
    * `404 Not Found`: Partida no encontrada.
    * `403 Forbidden`: No es el turno del jugador.
    * `400 Bad Request`: "La partida no está en curso."

---

## 5. Esquemas de Datos Principales (Pydantic)

Todos los esquemas de solicitud y respuesta están definidos en `app/models/schemas.py`. Los más relevantes para el frontend son:

* `GameInfo`: Información resumida de la partida.
* `GameSnapshot`: Estado completo de la partida para renderizar.
* `PlayerInfo`: Detalles de un jugador y sus fichas.
* `PieceInfo`: Detalles de una ficha.
* `SquareInfo`: Detalles de una casilla del tablero, incluyendo sus ocupantes.
* `DiceRollResponse`: Respuesta al lanzar los dados, incluyendo movimientos posibles.
* `CreateGameRequest`, `JoinGameRequest`, `MovePieceRequest`, `BurnPieceRequest`: Cuerpos de solicitud.

**Nota sobre `SquareId`:** El ID de una casilla (`SquareId`) puede ser:
* Un `integer` para casillas en la pista principal (0-67).
* Una `tupla` para casillas especiales:
    * Pasillos: `("pas", "COLOR_DEL_PASILLO", indice_en_pasillo_0_a_6)`
    * Cielo: `("cielo", null, 0)` (o similar, consultar la estructura exacta devuelta por la API).

**Nota sobre `possible_moves` en `DiceRollResponse`:**
Este es un diccionario donde la clave es el UUID (string) de una ficha del jugador actual. El valor es una lista de movimientos posibles para esa ficha. Cada movimiento es una tupla:
`[target_square_id, move_result_type_str, steps_used_int]`
* `target_square_id`: El `SquareId` destino.
* `move_result_type_str`: String del `MoveResultType` (ej. "ok", "capture", "jail_exit_success").
* `steps_used_int`: Cuántos pasos del dado (d1, d2 o d1+d2) se consumirían con este movimiento.

El frontend debe presentar estas opciones al usuario para que elija una, y luego enviar la acción a `/move` con el `piece_uuid`, el `target_square_id` y los `steps_used` correspondientes.

## 6. Flujo de Juego Típico (Vista del Frontend)

1.  Un usuario crea una partida (`POST /games`).
2.  Otros usuarios se unen a la partida usando el `game_id` (`POST /games/{game_id}/join`).
3.  El creador (u otro jugador autorizado) inicia la partida (`POST /games/{game_id}/start` con su `X-User-ID`).
4.  **Bucle de Turno:**
    * El frontend obtiene el estado del juego (`GET /games/{game_id}/state`) para saber de quién es el turno y renderizar el tablero.
    * El jugador en turno lanza los dados (`POST /games/{game_id}/roll` con su `X-User-ID`).
        * La respuesta incluye los dados y `possible_moves`.
    * Si `roll_validation_result` es `THREE_PAIRS_BURN`:
        * El frontend podría permitir al usuario elegir una ficha para quemar (si hay opciones) o simplemente informar.
        * Llamar a `POST /games/{game_id}/burn-piece` (con `X-User-ID`). El turno pasará automáticamente.
    * Si hay `possible_moves`:
        * El frontend presenta las opciones al usuario.
        * El usuario selecciona un movimiento.
        * El frontend envía la acción a `POST /games/{game_id}/move` con los detalles del movimiento y `X-User-ID`.
        * La respuesta es el nuevo `GameSnapshot`. Si el jugador repite turno (por pares o salida de cárcel), el `current_turn_color` será el mismo.
    * Si no hay `possible_moves` (y no fue `THREE_PAIRS_BURN`):
        * El frontend informa al usuario.
        * El frontend (o el usuario) llama a `POST /games/{game_id}/pass-turn` con `X-User-ID`.
    * Se repite el bucle de turno hasta que `state` sea `FINISHED`.

## 7. Próximos Pasos (Desde la Perspectiva del Backend)

* Incrementar cobertura de tests unitarios para lógica de juego compleja.
* Implementar tests de API más exhaustivos para todos los endpoints y casos de error.
* Integración de WebSockets para actualizaciones en tiempo real (futuro).
* Persistencia de datos (futuro).

## 8. Consideraciones para el Frontend

* **Manejo de Errores:** La API utiliza códigos de estado HTTP estándar y devuelve mensajes de error en el cuerpo JSON (usualmente con el esquema `MoveOutcome` o el detalle de `HTTPException` de FastAPI).
* **Identificador de Usuario (`X-User-ID`):** Es core para las acciones de juego. Asegúrate de que el frontend lo envíe correctamente.
* **Validación de Entradas:** Aunque la API realiza validaciones, es buena práctica que el frontend también valide las entradas del usuario antes de enviarlas.
* **Actualización del Estado:** Después de cada acción que modifica el juego (`/roll`, `/move`, `/pass-turn`, `/burn-piece`), la API devuelve el snapshot completo del juego (`GameSnapshot`) para que el frontend pueda actualizar su vista.
* **Consistencia de IDs:** Los UUIDs de las fichas y los `SquareId` son la forma de referenciar elementos del juego.

## 9. Websockets

Este backend incluye soporte para comunicación en tiempo real mediante WebSockets. Esto permite reducir la latencia entre jugadores y facilitar una experiencia fluida durante la partida de Parqués.

### Endpoint WebSocket

```
ws://127.0.0.1:8000/ws/game/{room_id}
```

- `{room_id}`: Identificador único de la sala de juego (ej. `sala1`, `test-room`, etc.).
- Cada sala es independiente: solo los clientes conectados a la misma sala reciben los mensajes entre ellos.

### ¿Cómo probarlo?

#### 1. Ejecuta el servidor

En la raíz del proyecto, corre:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Esto levanta el backend en `http://127.0.0.1:8000`.

#### 2. Abre una herramienta de pruebas WebSocket

Puedes usar cualquiera de estas herramientas:

- [WebSocket King](https://websocketking.com/)
- Postman (opción “New > WebSocket Request”)
- Extensión de navegador: **Simple WebSocket Client**
- Cliente HTML personalizado (opcional)

#### 3. Conéctate al WebSocket

Utiliza una URL como la siguiente:

```
ws://127.0.0.1:8000/ws/game/test-room
```

Puedes abrir varias conexiones (pestañas o clientes) con el mismo `room_id` para simular varios jugadores.

#### 4. Envía mensajes

Envía un texto desde el cliente WebSocket:

```
Hola desde el cliente A
```

Todos los clientes conectados a la misma sala recibirán un mensaje tipo:

```
Mensaje en sala test-room: Hola desde el cliente A
```

### Comportamiento del servidor

- Cada mensaje es **broadcast** a todos los clientes de la sala.
- Cuando un cliente se **desconecta**, los demás reciben una notificación.
- Se puede usar `send_personal_message` si deseas enviar mensajes individuales (por ejemplo, mensajes privados o turnos).

