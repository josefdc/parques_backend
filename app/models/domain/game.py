"""Modelo de dominio para el agregado de juego de Parqués.

Define la clase GameAggregate, que encapsula el estado y lógica completa
de una partida de Parqués, incluyendo gestión de jugadores, turnos y eventos.
"""
from __future__ import annotations
import uuid
import asyncio
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Deque, TYPE_CHECKING, Tuple

from app.core.enums import GameState, Color
from app.models.domain.board import Board

if TYPE_CHECKING:
    from app.models.domain.player import Player
    from app.models.schemas import GameEventPydantic

MIN_PLAYERS = 2
MAX_PLAYERS = 4

class GameAggregate:
    """Representa el estado completo de una partida de Parqués.

    Administra jugadores, tablero, turnos, estado del juego y eventos.
    """
    id: uuid.UUID
    state: GameState
    board: Board
    players: Dict[Color, 'Player']
    turn_order: Deque[Color]
    current_turn_color: Optional[Color]
    dice_roll_count: int
    last_dice_roll: Optional[Tuple[int, int]]
    current_player_doubles_count: int
    max_players: int
    lock: asyncio.Lock
    log: List['GameEventPydantic']
    winner: Optional[Color]
    created_at: datetime
    last_activity_at: datetime

    def __init__(self, game_id: uuid.UUID, max_players_limit: int = MAX_PLAYERS) -> None:
        """Inicializa un nuevo agregado de juego.

        Args:
            game_id: Identificador único del juego.
            max_players_limit: Máximo número de jugadores permitidos.
        """
        from app.models.domain.player import Player

        self.id = game_id
        self.state = GameState.WAITING_PLAYERS
        self.board = Board()
        self.players = {}
        self.turn_order = deque()
        self.current_turn_color = None
        self.dice_roll_count = 0
        self.last_dice_roll = None
        self.current_player_doubles_count = 0
        self.max_players = max_players_limit
        self.lock = asyncio.Lock()
        self.log = []
        self.winner = None

        self.created_at = datetime.now()
        self.last_activity_at = self.created_at

        self._add_game_event("game_created", {"game_id": str(self.id), "max_players": self.max_players})

    def _add_game_event(self, event_type: str, payload: Dict) -> None:
        """Agrega un evento al registro del juego.

        Args:
            event_type: Tipo de evento (ej: "player_joined").
            payload: Diccionario con datos específicos del evento.
        """
        from app.models.schemas import GameEventPydantic
        event = GameEventPydantic(type=event_type, payload=payload)
        self.log.append(event)

    def add_player(self, player: 'Player') -> bool:
        """Agrega un jugador a la partida.

        Args:
            player: Instancia de Player a agregar.

        Returns:
            True si se agregó, False si el juego está lleno, color ocupado o estado incorrecto.
        """
        if len(self.players) >= self.max_players:
            return False
        if not isinstance(player.color, Color):
            pass
        if player.color in self.players:
            return False
        if self.state != GameState.WAITING_PLAYERS:
            return False

        self.players[player.color] = player
        self.turn_order.append(player.color)

        if len(self.players) >= MIN_PLAYERS:
            self.state = GameState.READY_TO_START

        # DEBUG lines (comentadas por defecto)
        print(f"DEBUG en add_player: player.user_id='{player.user_id}'")
        print(f"DEBUG en add_player: player.color='{player.color}'")
        print(f"DEBUG en add_player: type(player.color) is {type(player.color)}")
        print(f"DEBUG en add_player: isinstance(player.color, Color) is {isinstance(player.color, Color)}")

        self._add_game_event("player_joined", {"user_id": player.user_id, "color": player.color.value})
        self.last_activity_at = datetime.now()
        return True

    def remove_player(self, color_to_remove: Color) -> bool:
        """Elimina un jugador de la partida (por ejemplo, si se desconecta antes de iniciar).

        Args:
            color_to_remove: Color del jugador a eliminar.

        Returns:
            True si se eliminó, False en caso contrario.
        """
        if color_to_remove in self.players:
            removed_player = self.players.pop(color_to_remove)
            if color_to_remove in self.turn_order:
                new_turn_order = deque([c for c in self.turn_order if c != color_to_remove])
                self.turn_order = new_turn_order

            if self.state == GameState.READY_TO_START and len(self.players) < MIN_PLAYERS:
                self.state = GameState.WAITING_PLAYERS

            if self.current_turn_color == color_to_remove and self.state == GameState.IN_PROGRESS:
                self.current_turn_color = None

            self._add_game_event("player_left", {"user_id": removed_player.user_id, "color": removed_player.color.name})
            self.last_activity_at = datetime.now()
            return True
        return False

    def start_game(self) -> bool:
        """Inicia la partida, determina el orden de turnos y asigna el primer jugador.

        Returns:
            True si el juego inició, False en caso contrario.
        """
        if self.state != GameState.READY_TO_START or len(self.players) < MIN_PLAYERS:
            return False
        if not self.turn_order:
            return False

        self.current_turn_color = self.turn_order[0]
        self.state = GameState.IN_PROGRESS
        self.current_player_doubles_count = 0
        if self.current_turn_color and self.players[self.current_turn_color]:
            self.players[self.current_turn_color].reset_consecutive_pairs()

        self._add_game_event("game_started", {"turn_order": [c.name for c in self.turn_order]})
        self.last_activity_at = datetime.now()
        return True

    def next_turn(self) -> None:
        """Avanza al siguiente jugador en el orden de turnos."""
        if not self.current_turn_color or not self.turn_order:
            return

        self.turn_order.rotate(-1)
        self.current_turn_color = self.turn_order[0]
        self.current_player_doubles_count = 0
        self.last_dice_roll = None
        self.dice_roll_count = 0

        if self.current_turn_color and self.players[self.current_turn_color]:
            self.players[self.current_turn_color].reset_consecutive_pairs()

        self._add_game_event("next_turn", {"player_color": self.current_turn_color.name})
        self.last_activity_at = datetime.now()

    def check_for_winner(self) -> Optional[Color]:
        """Verifica si algún jugador ha ganado la partida.

        Si hay ganador, actualiza el estado y retorna el color del ganador.

        Returns:
            Color del jugador ganador, o None si no hay ganador.
        """
        for color, player in self.players.items():
            if player.check_win_condition():
                self.winner = color
                self.state = GameState.FINISHED
                self._add_game_event("game_finished", {"winner": color.name})
                self.last_activity_at = datetime.now()
                return color
        return None

    def get_player(self, color: Color) -> Optional['Player']:
        """Obtiene un jugador por su color.

        Args:
            color: Color del jugador.

        Returns:
            Instancia Player si existe, si no None.
        """
        return self.players.get(color)

    def get_current_player(self) -> Optional['Player']:
        """Obtiene el jugador cuyo turno es actualmente.

        Returns:
            Instancia Player si hay turno actual, si no None.
        """
        if self.current_turn_color:
            return self.players.get(self.current_turn_color)
        return None