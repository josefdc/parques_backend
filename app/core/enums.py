#app/core/enums.py
from enum import Enum

class Color(str, Enum): # Inherit from str
    """
    Enumeración para los colores de los jugadores.
    Los valores son strings para ser explícitos en API requests/responses.
    """
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"
    YELLOW = "YELLOW"
    # Podrías añadir más si decides extender a 6 u 8 jugadores en el futuro
    # ORANGE = "ORANGE"
    # PURPLE = "PURPLE"

    def __str__(self):
        # Returns lowercase name (e.g., "red") if str() is called on enum member.
        # Pydantic with use_enum_values=True will use the value (e.g., "RED") for serialization.
        return self.name.lower()

class SquareType(Enum):
    """
    Enumeración para los tipos de casilla en el tablero.
    """
    NORMAL = "normal"
    SALIDA = "salida"  # Casilla de inicio para cada color después de la cárcel
    SEGURO = "seguro"  # Casilla segura donde no se puede capturar
    ENTRADA_PASILLO = "entrada_pasillo" # Casilla que da acceso al pasillo final
    PASILLO = "pasillo" # Casillas del pasillo final de cada color
    META = "meta"      # La última casilla del pasillo antes del cielo (a veces llamada cielo parcial)
    CIELO = "cielo"    # Destino final de las fichas
    CARCEL = "carcel"  # Aunque no explícito en tu SquareType, es un lugar donde están las piezas

    def __str__(self):
        return self.value

class GameState(Enum):
    """
    Enumeración para los estados posibles de una partida.
    """
    WAITING_PLAYERS = "waiting_players"  # Esperando jugadores (< 2 conectados)
    READY_TO_START = "ready_to_start"    # 2-4 jugadores conectados, listos para iniciar
    IN_PROGRESS = "in_progress"          # Partida activa
    FINISHED = "finished"                # Partida terminada (alguien ha ganado)
    ABORTED = "aborted"                  # Partida abortada (opcional, por si quieres manejar esto)

    def __str__(self):
        return self.value

class MoveResultType(Enum):
    """
    Enumeración para los posibles resultados de un movimiento validado.
    (Adición sugerida basada en la sección 5 de tu documento)
    """
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

    def __str__(self):
        return self.value