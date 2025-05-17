"""Enumeraciones principales usadas en la aplicación de Parqués.

Define los colores de los jugadores, tipos de casillas, estados de la partida y resultados de movimientos.
"""
from enum import Enum

class Color(str, Enum):
    """Colores de los jugadores."""
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"
    YELLOW = "YELLOW"

    def __str__(self) -> str:
        return self.name.lower()

class SquareType(Enum):
    """Tipos de casillas en el tablero."""
    NORMAL = "normal"
    SALIDA = "salida"
    SEGURO = "seguro"
    ENTRADA_PASILLO = "entrada_pasillo"
    PASILLO = "pasillo"
    META = "meta"
    CIELO = "cielo"
    CARCEL = "carcel"

    def __str__(self) -> str:
        return self.value

class GameState(Enum):
    """Estados posibles de una partida."""
    WAITING_PLAYERS = "waiting_players"
    READY_TO_START = "ready_to_start"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ABORTED = "aborted"

    def __str__(self) -> str:
        return self.value

class MoveResultType(Enum):
    """Resultados posibles al validar un movimiento de ficha."""
    OK = "ok"
    BLOCKED_BY_OWN = "blocked_by_own"
    BLOCKED_BY_WALL = "blocked_by_wall"
    CAPTURE = "capture"
    EXACT_ROLL_NEEDED = "exact_roll_needed"
    OUT_OF_BOUNDS = "out_of_bounds"
    JAIL_EXIT_SUCCESS = "jail_exit_success"
    JAIL_EXIT_FAIL_NO_PAIRS = "jail_exit_fail_no_pairs"
    JAIL_EXIT_FAIL_OCCUPIED_START = "jail_exit_fail_occupied_start"
    PIECE_WINS = "piece_wins"
    GAME_WINS = "game_wins"
    INVALID_PIECE = "invalid_piece"
    INVALID_ROLL = "invalid_roll"
    NOT_YOUR_TURN = "not_your_turn"
    THREE_PAIRS_BURN = "three_pairs_burn"
    ACTION_FAILED = "action_failed"

    def __str__(self) -> str:
        return self.value