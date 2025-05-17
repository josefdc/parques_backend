"""Core enumerations used throughout the Parqués game application.

This module defines enumerations for player colors, square types on the game board,
possible game states, and types of results from validating a move.
"""
from enum import Enum

class Color(str, Enum): # Inherit from str
    """Enumeration for player colors.

    Values are uppercase strings for explicit API request/response handling.
    """
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"
    YELLOW = "YELLOW"
    # Potential future extension for more players:
    # ORANGE = "ORANGE"
    # PURPLE = "PURPLE"

    def __str__(self) -> str:
        # Returns lowercase name (e.g., "red") if str() is called on enum member.
        # Pydantic with use_enum_values=True will use the value (e.g., "RED") for serialization.
        return self.name.lower()

class SquareType(Enum):
    """Enumeration for the types of squares on the game board."""
    NORMAL = "normal"
    SALIDA = "salida"  # Casilla de inicio para cada color después de la cárcel
    SEGURO = "seguro"  # Casilla segura donde no se puede capturar
    ENTRADA_PASILLO = "entrada_pasillo" # Casilla que da acceso al pasillo final
    PASILLO = "pasillo" # Casillas del pasillo final de cada color
    META = "meta"      # La última casilla del pasillo antes del cielo (a veces llamada cielo parcial)
    CIELO = "cielo"    # Destino final de las fichas
    CARCEL = "carcel"  # Represents the jail area where pieces start or return to.

    def __str__(self) -> str:
        return self.value

class GameState(Enum):
    """Enumeration for the possible states of a game."""
    WAITING_PLAYERS = "waiting_players"  # Esperando jugadores (< 2 conectados)
    READY_TO_START = "ready_to_start"    # 2-4 jugadores conectados, listos para iniciar
    IN_PROGRESS = "in_progress"          # Partida activa
    FINISHED = "finished"                # Partida terminada (alguien ha ganado)
    ABORTED = "aborted"                  # Partida abortada (opcional, for handling game interruption)

    def __str__(self) -> str:
        return self.value

class MoveResultType(Enum):
    """Enumeration for the possible outcomes of a validated piece move."""
    OK = "ok"                         # Movimiento válido
    BLOCKED_BY_OWN = "blocked_by_own" # Bloqueado por una barrera propia en la salida
    BLOCKED_BY_WALL = "blocked_by_wall" # Bloqueado por una barrera de otro jugador
    CAPTURE = "capture"               # Movimiento resulta en captura
    EXACT_ROLL_NEEDED = "exact_roll_needed" # Se necesita tiro exacto para entrar/ganar
    OUT_OF_BOUNDS = "out_of_bounds"   # Movimiento fuera de los límites (ej. se pasa de la meta)
    JAIL_EXIT_SUCCESS = "jail_exit_success" # Salió de la cárcel
    JAIL_EXIT_FAIL_NO_PAIRS = "jail_exit_fail_no_pairs" # No sacó pares para salir de cárcel
    JAIL_EXIT_FAIL_OCCUPIED_START = "jail_exit_fail_occupied_start" # Casilla de salida ocupada por barrera propia
    PIECE_WINS = "piece_wins"         # La ficha llega al cielo
    GAME_WINS = "game_wins"           # Todas las fichas del jugador llegan al cielo
    INVALID_PIECE = "invalid_piece"   # La ficha seleccionada no es válida para mover
    INVALID_ROLL = "invalid_roll"     # El tiro de dados no permite mover la ficha seleccionada
    NOT_YOUR_TURN = "not_your_turn"
    THREE_PAIRS_BURN = "three_pairs_burn" # Quemada por tres pares
    ACTION_FAILED = "action_failed"   # Default for unspecified errors

    def __str__(self) -> str:
        return self.value