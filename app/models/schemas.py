from __future__ import annotations # Para usar tipos sin comillas si es necesario
from typing import List, Dict, Optional, Union, Tuple # Añadir Any si se usa como placeholder
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict # Import ConfigDict

from app.core.enums import Color, GameState, SquareType, MoveResultType # Importar nuestras enums

# --- Modelos Base para la API ---

class TunedModel(BaseModel):
    """Modelo Pydantic base con configuración común."""
    model_config = ConfigDict(
        from_attributes=True, # Permite crear modelos desde atributos de objetos (ORM mode)
        use_enum_values=True  # Serializa enums a sus valores (ej. "in_progress" en vez de GameState.IN_PROGRESS)
    )

# --- Esquemas para Información de Jugadores y Fichas ---

class PieceInfo(TunedModel):
    """Información pública de una ficha."""
    id: UUID # El UUID global de la ficha
    piece_player_id: int # El ID de la ficha para el jugador (0-3)
    color: Color # Color de la ficha
    position: Optional[Union[int, Tuple[str, Optional[Color], Optional[int]]]] # SquareId
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int

class PlayerInfo(TunedModel):
    """Información pública de un jugador."""
    user_id: str
    color: Color
    pieces: List[PieceInfo]
    is_current_turn: bool = False # Indica si es el turno de este jugador
    consecutive_pairs_count: int # Cuántos pares seguidos lleva (el personal del jugador)
    # Podríamos añadir más, como pieces_in_cielo_count si es útil para el frontend

# --- Esquemas para Información del Tablero ---

class SquareInfo(TunedModel):
    """Información pública de una casilla del tablero."""
    id: Union[int, Tuple[str, Optional[Color], Optional[int]]] # SquareId
    type: SquareType
    occupants: List[PieceInfo] # Lista de fichas que ocupan la casilla
    color_association: Optional[Color]

# --- Esquemas para Solicitudes (Requests) de la API ---

class CreateGameRequest(TunedModel):
    max_players: int = Field(default=4, ge=2, le=8) # Asumiendo que podrías extender a 6 u 8

class JoinGameRequest(TunedModel):
    user_id: str = Field(..., min_length=1)
    color: Color # El jugador elige un color (int o string según como lo manejes en el endpoint)

class MovePieceRequest(TunedModel):
    """
    El `user_id` se obtendrá del token/sesión.
    El `game_id` y `piece_id` (o `piece_uuid_str`) de la URL.
    """
    piece_uuid: UUID # UUID de la ficha a mover
    # El jugador indica el movimiento elegido basado en los `possible_moves`
    # que le dio el `roll_dice`. Esto incluye el destino y los pasos del dado usados.
    target_square_id: Union[int, Tuple[str, Optional[Color], Optional[int]]] # SquareId
    steps_used: int # d1, d2, o d1+d2 que se usaron para este movimiento específico

class BurnPieceRequest(TunedModel):
    """
    Solicitud para que un jugador elija qué ficha quemar después de 3 pares.
    Si no se proporciona piece_uuid, el servidor elige automáticamente.
    """
    piece_uuid: Optional[UUID] = None


# --- Esquemas para Respuestas (Responses) de la API ---

class GameInfo(TunedModel):
    """Información básica de una partida (ej. para listar en un lobby o después de crear/unirse)."""
    id: UUID
    state: GameState
    max_players: int
    current_player_count: int
    players: List[PlayerInfo] # Lista simplificada de jugadores, quizás solo user_id y color
    created_at: datetime

class DiceRollResponse(TunedModel):
    """Respuesta después de lanzar los dados."""
    dice1: int
    dice2: int
    is_pairs: bool
    roll_validation_result: MoveResultType # ej. THREE_PAIRS_BURN, OK
    # Los movimientos posibles se envían para que el cliente elija.
    # La estructura es: { "piece_uuid_str": [(target_square_id, move_result_type, steps_used), ...], ... }
    possible_moves: Dict[str, List[Tuple[Union[int, Tuple[str, Optional[Color], Optional[int]]], MoveResultType, int]]]

class MoveOutcome(TunedModel):
    """Resultado de una acción de movimiento o quema de ficha."""
    success: bool
    message: str
    move_result_type: MoveResultType
    # Opcionalmente, se podría devolver el GameSnapshot completo aquí
    # O solo los cambios relevantes.
    # game_state: Optional[GameSnapshot] # Decidir si se envía todo el snapshot o no

class GameSnapshot(TunedModel):
    """Representación completa del estado del juego para los clientes."""
    game_id: UUID
    state: GameState
    board: List[SquareInfo] # Lista de todas las casillas con sus ocupantes
    players: List[PlayerInfo] # Información completa de todos los jugadores
    turn_order: List[Color] # Orden de turno actual
    current_turn_color: Optional[Color]
    current_player_doubles_count: int # Contador de pares del juego para el turno actual
    last_dice_roll: Optional[Tuple[int, int]] = None # Último tiro de dados en el turno actual
    winner: Optional[Color] = None
    # Otros campos que puedan ser relevantes para el frontend para renderizar el juego

# --- Esquema para Eventos del Juego (usado en GameAggregate y WebSockets) ---

class GameEventPydantic(TunedModel):
    """
    Modelo Pydantic para los eventos del juego.
    Se usará en GameAggregate.log y para enviar por WebSockets.
    """
    ts: datetime = Field(default_factory=datetime.now)
    type: str  # "dice_rolled", "piece_moved", "player_joined", "game_started", etc.
    payload: Dict # Contenido específico del evento