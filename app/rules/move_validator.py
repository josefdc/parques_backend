#app/rules/move_validator.py
from __future__ import annotations
from typing import Tuple, Optional, TYPE_CHECKING, List, Dict # Añadir List y Dict

from app.core.enums import Color, SquareType, MoveResultType
from app.models.domain.board import SALIDA_SQUARES_INDICES, PASSAGEWAY_LENGTH # Necesitamos PASSAGEWAY_LENGTH

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate
    from app.models.domain.player import Player
    from app.models.domain.piece import Piece
    from app.models.domain.square import Square, SquareId


class MoveValidator:
    """
    Valida los lanzamientos de dados y los movimientos de las fichas
    según las reglas del Parqués (versión colombiana simplificada).
    """

    def validate_and_process_roll(
        self,
        game: GameAggregate,
        player_color: Color,
        d1: int,
        d2: int
    ) -> MoveResultType:
        """
        Valida el resultado de un lanzamiento de dados y actualiza el estado del juego/jugador
        relacionado con los pares (ej. contador de pares, quemar ficha por 3 pares).
        """
        player = game.get_player(player_color)
        if not player:
            # Este caso no debería ocurrir si el GameService funciona correctamente
            return MoveResultType.INVALID_PIECE 

        is_roll_pairs = (d1 == d2)

        if is_roll_pairs:
            player.increment_consecutive_pairs()
            game.current_player_doubles_count = player.consecutive_pairs_count

            if player.consecutive_pairs_count == 3:
                # REGLA: Tres pares seguidos queman ficha. El turno NO se repite.
                # GameService se encargará de la lógica de qué ficha se quema.
                # El contador del jugador (player.consecutive_pairs_count) se reseteará 
                # cuando GameService maneje la quema y pase el turno.
                return MoveResultType.THREE_PAIRS_BURN
            else:
                # REGLA: Sacó pares (1er o 2do par).
                # El jugador PUEDE repetir turno DESPUÉS de mover.
                # Si saca de cárcel, la regla especial de "volver a tirar" aplica (manejado por GameService).
                return MoveResultType.OK # Indica que el tiro es válido.
        else:
            # No sacó pares. Resetea el contador de pares del jugador.
            player.reset_consecutive_pairs()
            # game.current_player_doubles_count se resetea en game.next_turn()
            return MoveResultType.OK # Tiro válido

    def get_possible_moves(
        self,
        game: GameAggregate,
        player_color: Color,
        d1: int,
        d2: int
    ) -> Dict[str, List[Tuple[SquareId, MoveResultType, int]]]:
        player = game.get_player(player_color)
        if not player or game.current_turn_color != player_color:
            return {}

        possible_moves_for_player: Dict[str, List[Tuple[SquareId, MoveResultType, int]]] = {}
        is_pairs = (d1 == d2)

        for piece in player.pieces:
            if piece.has_reached_cielo:
                continue

            current_piece_options: List[Tuple[SquareId, MoveResultType, int]] = []

            # --- Opción 1: Salir de la Cárcel (si aplica) ---
            if piece.is_in_jail and is_pairs:
                print(f"DEBUG get_possible_moves: Evaluating jail exit for piece {piece.id} (PlayerColor: {player_color}) with pairs {d1},{d2}") # DESCOMENTAR
                validation_result, target_id = self._validate_single_move_attempt(
                    game=game,
                    piece_to_move=piece,
                    steps=0,  # Special value for jail exit attempt
                    is_roll_pairs=True
                )
                print(f"DEBUG get_possible_moves: Jail exit validation for {piece.id}: Result={validation_result}, Target={target_id}") # DESCOMENTAR
                if validation_result == MoveResultType.JAIL_EXIT_SUCCESS and target_id is not None:
                    current_piece_options.append((target_id, validation_result, 0))
                # Si falla la salida (ej. JAIL_EXIT_FAIL_OCCUPIED_START), no se añade como opción.

            # --- Opción 2: Mover Fichas en Juego ---
            elif not piece.is_in_jail: # Solo si la ficha no está en la cárcel
                # print(f"DEBUG: Evaluating board moves for piece {piece.id} (not in jail) with dice {d1},{d2}")
                dice_steps_to_evaluate: List[int] = []
                if is_pairs:
                    # Con pares, se mueve la suma. (Podrías añadir d1 y d2 si las reglas lo permiten para mover dos fichas)
                    dice_steps_to_evaluate.append(d1 + d2)
                else:
                    # Sin pares, se pueden usar d1, d2, o d1+d2
                    dice_steps_to_evaluate.append(d1)
                    dice_steps_to_evaluate.append(d2)
                    if d1 != d2 : # Evitar duplicar si d1+d2 es igual a d1 o d2 (no pasará con dados 1-6)
                        dice_steps_to_evaluate.append(d1 + d2)
                
                # Eliminar duplicados y el 0 si está presente
                unique_steps = sorted(list(set(s for s in dice_steps_to_evaluate if s > 0)), reverse=True)

                for steps in unique_steps:
                    # print(f"DEBUG: Validating move for piece {piece.id} with steps {steps}")
                    validation_result, target_id = self._validate_single_move_attempt(
                        game=game,
                        piece_to_move=piece,
                        steps=steps,
                        is_roll_pairs=is_pairs # Importante para reglas internas de _validate_single_move_attempt
                    )
                    # print(f"DEBUG: Move validation for {piece.id} with {steps} steps: Result={validation_result}, Target={target_id}")
                    if validation_result not in [MoveResultType.INVALID_PIECE, MoveResultType.INVALID_ROLL] and target_id is not None:
                        current_piece_options.append((target_id, validation_result, steps))
                    # Incluir EXACT_ROLL_NEEDED como una opción informativa si tiene un target_id
                    elif validation_result == MoveResultType.EXACT_ROLL_NEEDED and target_id is not None:
                         current_piece_options.append((target_id, validation_result, steps))


            if current_piece_options:
                possible_moves_for_player[str(piece.id)] = current_piece_options
                
        print(f"FINAL DEBUG get_possible_moves: RETURNING possible_moves_for_player: {possible_moves_for_player}")
        return possible_moves_for_player

    def _validate_single_move_attempt(
        self,
        game: GameAggregate,
        piece_to_move: Piece,
        steps: int,
        is_roll_pairs: bool
    ) -> Tuple[MoveResultType, Optional[SquareId]]:
        """
        Lógica interna para validar un único intento de movimiento.
        Esta función es llamada por get_possible_moves.
        """
        board = game.board

        # 1. Regla de Salida de Cárcel
        if piece_to_move.is_in_jail:
            print(f"DEBUG _validate_single_move_attempt: Validating jail exit for piece {piece_to_move.id}. is_roll_pairs: {is_roll_pairs}") # DESCOMENTAR
            if not is_roll_pairs:
                print("DEBUG _validate_single_move_attempt: Failing jail exit: not pairs.") # DESCOMENTAR
                return MoveResultType.JAIL_EXIT_FAIL_NO_PAIRS, None
            
            salida_square_id = board.get_salida_square_id_for_color(piece_to_move.color)
            salida_square = board.get_square(salida_square_id)
            print(f"DEBUG _validate_single_move_attempt: Salida square ID: {salida_square_id}, Square object: {salida_square}") # DESCOMENTAR

            if not salida_square: # Configuración de tablero incorrecta
                print("DEBUG _validate_single_move_attempt: Failing jail exit: salida_square not found.") # DESCOMENTAR
                return MoveResultType.INVALID_PIECE, None

            print(f"DEBUG _validate_single_move_attempt: Salida square occupants: {len(salida_square.occupants)}") # DESCOMENTAR
            if len(salida_square.occupants) == 2 and \
               all(occ.color == piece_to_move.color for occ in salida_square.occupants):
                print("DEBUG _validate_single_move_attempt: Failing jail exit: salida_square occupied by own barrier.") # DESCOMENTAR
                return MoveResultType.JAIL_EXIT_FAIL_OCCUPIED_START, None
            
            print(f"DEBUG _validate_single_move_attempt: Jail exit SUCCESS for piece {piece_to_move.id}.") # DESCOMENTAR
            return MoveResultType.JAIL_EXIT_SUCCESS, salida_square_id

        # 2. Mover ficha que ya está en juego
        current_pos = piece_to_move.position
        if current_pos is None: # No debería pasar si no está en cárcel
            return MoveResultType.INVALID_PIECE, None

        target_square_id = board.advance_piece_logic(current_pos, steps, piece_to_move.color)

        if target_square_id is None: # Se pasó del cielo o movimiento inválido desde pasillo
            # Verificar si estaba intentando llegar al cielo pero necesitaba tiro exacto
            # `advance_piece_logic` devuelve None si `k + steps > PASSAGEWAY_LENGTH`
            # Si `k + steps == PASSAGEWAY_LENGTH` (tiro exacto para cielo), devuelve cielo_square_id.
            current_square_obj = board.get_square(current_pos)
            if current_square_obj and current_square_obj.type == SquareType.META:
                 # Si estaba en META y el tiro no fue exacto para el cielo
                 if isinstance(current_pos, tuple) and current_pos[0] == 'pas':
                     k_actual = current_pos[2]
                     if k_actual == PASSAGEWAY_LENGTH - 1 and (k_actual + steps) > PASSAGEWAY_LENGTH:
                         return MoveResultType.EXACT_ROLL_NEEDED, board.cielo_square_id # Informar que se pasó
            return MoveResultType.OUT_OF_BOUNDS, None


        target_square = board.get_square(target_square_id)
        if not target_square:
            return MoveResultType.OUT_OF_BOUNDS, None # Destino no válido

        # 3. Reglas de la casilla destino

        # 3.1 ¿Intenta llegar al CIELO?
        if target_square.type == SquareType.CIELO:
            # `advance_piece_logic` ya gestionó si se podía llegar con los `steps` dados.
            # Si current_pos era META y steps = 1, target_square_id será el cielo.
            return MoveResultType.PIECE_WINS, target_square_id

        # 3.2 ¿Casilla destino es SEGURA para esta ficha? (Ignorando otras fichas)
        is_target_intrinsically_safe = target_square.is_safe_square_for_piece(piece_to_move.color)

        # 3.3 ¿Hay fichas de OTRO color en la casilla destino?
        other_color_pieces_at_target = target_square.get_other_color_pieces(piece_to_move.color)

        if other_color_pieces_at_target:
            if is_target_intrinsically_safe:
                # Casilla segura, no hay captura.
                # En Parqués colombiano, usualmente no puedes compartir casilla segura con otro,
                # a menos que sea una salida pública (que no es el caso aquí).
                # Si es un SEGURO normal y hay otra ficha, es un bloqueo.
                # Si la casilla segura solo puede tener una ficha (o es SALIDA de otro) -> BLOQUEADO.
                # Sin embargo, como no hay muros, si la casilla es segura y está ocupada por otro,
                # NO PUEDES CAER AHÍ.
                # Si la casilla de SALIDA (que es segura) está ocupada por una ficha de otro color,
                # no puedes caer ahí.
                if target_square.type == SquareType.SEGURO or \
                   (target_square.type == SquareType.SALIDA and target_square.color_association != piece_to_move.color):
                    return MoveResultType.BLOCKED_BY_WALL, target_square_id # "Bloqueado por ficha ajena en seguro/salida ajena"
                # Si es tu pasillo/meta/salida, es seguro y puedes añadir tu ficha (hasta 2)
            else:
                # Casilla no segura y ocupada por otros -> CAPTURA
                return MoveResultType.CAPTURE, target_square_id
        
        # 3.4 Casilla destino vacía o con fichas PROPIAS
        # Se puede mover si no se excede el límite de fichas por casilla (usualmente 2).
        if len(target_square.occupants) < 2:
            return MoveResultType.OK, target_square_id
        elif len(target_square.occupants) == 1 and target_square.occupants[0].color == piece_to_move.color:
            # Ya hay una ficha propia, se puede añadir la segunda para formar "barrera" (aunque no bloquea el paso a otros)
            return MoveResultType.OK, target_square_id
        elif len(target_square.occupants) >= 2 and all(occ.color == piece_to_move.color for occ in target_square.occupants):
            # Ya hay dos fichas propias, no se puede añadir una tercera.
            return MoveResultType.BLOCKED_BY_OWN, target_square_id
        
        # Si la casilla está ocupada por 2 fichas de otro color y no es segura (ya se manejó en captura),
        # no se puede mover ahí. Esta condición ya debería estar cubierta.

        return MoveResultType.INVALID_ROLL, None # Fallback para casos no cubiertos explícitamente