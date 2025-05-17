"""Pydantic schemas for API request and response models, and internal data structures.

This module defines the data structures used for validating API inputs,
serializing API outputs, and representing game entities like players, pieces,
and the game board state.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Union, Tuple, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.enums import Color, GameState, SquareType, MoveResultType

class TunedModel(BaseModel):
    """
    Modelo base de Pydantic con configuración común.

    Habilita el modo ORM (from_attributes) y serializa enums por su valor.
    """
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )

class PieceInfo(TunedModel):
    """
    Información pública sobre una ficha del juego.

    Atributos:
        id: Identificador global único de la ficha.
        piece_player_id: ID relativo al jugador (ej: 0-3).
        color: Color de la ficha.
        position: ID de la casilla actual (entero o tupla para casillas especiales).
        is_in_jail: Indica si la ficha está en la cárcel.
        has_reached_cielo: Indica si la ficha ha llegado al cielo.
        squares_advanced_in_path: Número de casillas avanzadas en el pasillo final.
    """
    id: UUID
    piece_player_id: int
    color: Color
    position: Optional[Union[int, Tuple[str, Optional[Color], Optional[int]]]]
    is_in_jail: bool
    has_reached_cielo: bool
    squares_advanced_in_path: int

class PlayerInfo(TunedModel):
    """
    Información pública sobre un jugador en la partida.

    Atributos:
        user_id: Identificador único del usuario.
        color: Color asignado al jugador.
        pieces: Lista de fichas del jugador.
        is_current_turn: Indica si es el turno actual de este jugador.
        consecutive_pairs_count: Número de pares consecutivos lanzados por el jugador en su turno.
    """
    user_id: str
    color: Color
    pieces: List[PieceInfo]
    is_current_turn: bool = False
    consecutive_pairs_count: int

class SquareInfo(TunedModel):
    """
    Información pública sobre una casilla del tablero.

    Atributos:
        id: Identificador único de la casilla.
        type: Tipo de la casilla (NORMAL, SEGURO, SALIDA, etc).
        occupants: Lista de fichas que ocupan la casilla.
        color_association: Color asociado a la casilla, si aplica.
    """
    id: Union[int, Tuple[str, Optional[Color], Optional[int]]]
    type: SquareType
    occupants: List[PieceInfo]
    color_association: Optional[Color]

class CreateGameRequest(TunedModel):
    """
    Esquema para solicitud de creación de una nueva partida.
    """
    max_players: int = Field(default=4, ge=2, le=8)
    creator_user_id: str = Field(..., min_length=1, description="ID del usuario que crea la partida")
    creator_color: Color = Field(..., description="Color elegido por el creador (ej: 'RED', 'GREEN', 0, 1)")

    @field_validator('creator_color', mode='before')
    @classmethod
    def validate_creator_color(cls, v: Any) -> Color:
        """
        Valida y convierte el campo creator_color.

        Acepta miembros del enum Color, cadenas (case-insensitive) o enteros (0-3).

        Args:
            v: Valor de entrada para creator_color.

        Returns:
            Miembro válido de Color.

        Raises:
            ValueError: Si el color es inválido.
            TypeError: Si el tipo no es str, int o Color.
        """
        if isinstance(v, Color):
            return v
        if isinstance(v, str):
            try:
                return Color(v.upper())
            except ValueError:
                valid_colors_str = [e.value for e in Color]
                raise ValueError(f"Color inválido: '{v}'. Debe ser uno de {valid_colors_str} o un entero válido (0-3).")
        if isinstance(v, int):
            try:
                if v == 0: return Color.RED
                if v == 1: return Color.GREEN
                if v == 2: return Color.BLUE
                if v == 3: return Color.YELLOW
                raise ValueError(f"Entero inválido para color: {v}. Debe ser 0-3.")
            except ValueError as e:
                 raise ValueError(str(e)) from e
        raise TypeError(f"Tipo inválido para Color: {type(v)}. Se espera string, int o miembro del enum Color.")

class JoinGameRequest(TunedModel):
    """
    Esquema para solicitud de unión a una partida existente.
    """
    user_id: str = Field(..., min_length=1, description="ID del usuario que se une a la partida")
    color: Color = Field(..., description="Color solicitado por el usuario (ej: 'RED', 'GREEN', 0, 1)")

    @field_validator('color', mode='before')
    @classmethod
    def validate_join_color(cls, v: Any) -> Color:
        """
        Valida y convierte el campo color para la solicitud de unión.

        Acepta miembros del enum Color, cadenas (case-insensitive) o enteros (0-3).

        Args:
            v: Valor de entrada para color.

        Returns:
            Miembro válido de Color.

        Raises:
            ValueError: Si el color es inválido.
            TypeError: Si el tipo no es str, int o Color.
        """
        if isinstance(v, Color):
            return v
        if isinstance(v, str):
            try:
                return Color(v.upper())
            except ValueError:
                valid_colors_str = [e.value for e in Color]
                raise ValueError(f"Color inválido: '{v}'. Debe ser uno de {valid_colors_str} o un entero válido (0-3).")
        if isinstance(v, int):
            try:
                if v == 0: return Color.RED
                if v == 1: return Color.GREEN
                if v == 2: return Color.BLUE
                if v == 3: return Color.YELLOW
                raise ValueError(f"Entero inválido para color: {v}. Debe ser 0-3.")
            except ValueError as e:
                raise ValueError(str(e)) from e
        raise TypeError(f"Tipo inválido para Color: {type(v)}. Se espera string, int o miembro del enum Color.")

class MovePieceRequest(TunedModel):
    """
    Esquema para solicitud de movimiento de una ficha.

    Atributos:
        piece_uuid: UUID de la ficha a mover.
        target_square_id: ID de la casilla destino.
        steps_used: Valor del dado usado para este movimiento.
    """
    piece_uuid: UUID
    target_square_id: Union[int, Tuple[str, Optional[Color], Optional[int]]]
    steps_used: int

class BurnPieceRequest(TunedModel):
    """
    Esquema para solicitud de quemar una ficha tras sacar tres pares.

    Atributos:
        piece_uuid: UUID opcional de la ficha elegida para quemar.
    """
    piece_uuid: Optional[UUID] = None

class GameInfo(TunedModel):
    """
    Información básica sobre una partida.

    Atributos:
        id: Identificador único de la partida.
        state: Estado actual de la partida.
        max_players: Máximo de jugadores permitidos.
        current_player_count: Número actual de jugadores.
        players: Lista de jugadores en la partida.
        created_at: Fecha de creación.
    """
    id: UUID
    state: GameState
    max_players: int
    current_player_count: int
    players: List[PlayerInfo]
    created_at: datetime

class DiceRollResponse(TunedModel):
    """
    Esquema para la respuesta tras lanzar los dados.

    Atributos:
        dice1: Valor del primer dado.
        dice2: Valor del segundo dado.
        is_pairs: Indica si fue un par.
        roll_validation_result: Resultado de la validación del tiro.
        possible_moves: Diccionario de movimientos posibles por ficha.
    """
    dice1: int
    dice2: int
    is_pairs: bool
    roll_validation_result: MoveResultType
    possible_moves: Dict[str, List[Tuple[Union[int, Tuple[str, Optional[Color], Optional[int]]], MoveResultType, int]]]

class MoveOutcome(TunedModel):
    """
    Esquema para el resultado de un movimiento o quemada de ficha.

    Atributos:
        success: Indica si la acción fue exitosa.
        message: Mensaje descriptivo del resultado.
        move_result_type: Tipo específico de resultado, si aplica.
    """
    success: bool
    message: str
    move_result_type: Optional[MoveResultType] = None

class GameSnapshot(TunedModel):
    """
    Representación completa del estado actual de la partida.

    Atributos:
        game_id: Identificador único de la partida.
        state: Estado actual.
        board: Lista de casillas con sus ocupantes.
        players: Información detallada de los jugadores.
        turn_order: Orden actual de turnos por color.
        current_turn_color: Color del jugador en turno.
        current_player_doubles_count: Número de pares consecutivos del jugador actual.
        last_dice_roll: Último tiro de dados, si existe.
        winner: Color del jugador ganador, si la partida terminó.
    """
    game_id: UUID
    state: GameState
    board: List[SquareInfo]
    players: List[PlayerInfo]
    turn_order: List[Color]
    current_turn_color: Optional[Color]
    current_player_doubles_count: int
    last_dice_roll: Optional[Tuple[int, int]] = None
    winner: Optional[Color] = None

class GameEventPydantic(TunedModel):
    """
    Modelo Pydantic para eventos del juego.

    Usado para logs internos y para enviar actualizaciones por WebSockets.

    Atributos:
        ts: Marca de tiempo del evento.
        type: Tipo de evento (ej: "dice_rolled", "piece_moved").
        payload: Diccionario con datos específicos del evento.
    """
    ts: datetime = Field(default_factory=datetime.now)
    type: str
    payload: Dict[str, Any]