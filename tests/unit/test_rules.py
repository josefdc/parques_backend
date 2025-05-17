"""Unit tests for Parqués game rules and validators.

This module contains unit tests for dice rolling, move validation,
and board logic in the Parqués backend.
"""
import pytest  # type: ignore
import uuid
from typing import List, Tuple, Optional

# Importaciones de tu aplicación
from app.core.enums import Color, GameState, MoveResultType, SquareType
from app.models.domain.game import GameAggregate, MIN_PLAYERS, MAX_PLAYERS
from app.models.domain.player import Player
from app.models.domain.piece import Piece
from app.models.domain.board import Board, SALIDA_SQUARES_INDICES, PASSAGEWAY_LENGTH, NUM_MAIN_TRACK_SQUARES
from app.rules.dice import Dice
from app.rules.move_validator import MoveValidator

# --- Fixtures de Pytest (Podrías moverlos a tests/conftest.py si se usan en múltiples archivos) ---

@pytest.fixture
def move_validator() -> MoveValidator:
    """
    Provee una instancia de MoveValidator para pruebas.
    """
    return MoveValidator()

@pytest.fixture
def game_4_players() -> GameAggregate:
    """
    Crea un juego básico con 4 jugadores, listo para iniciar.
    """
    game = GameAggregate(game_id=uuid.uuid4(), max_players_limit=4)
    player_red = Player(user_id="user_red", color_input=Color.RED)
    player_green = Player(user_id="user_green", color_input=Color.GREEN)
    player_blue = Player(user_id="user_blue", color_input=Color.BLUE)
    player_yellow = Player(user_id="user_yellow", color_input=Color.YELLOW)
    
    game.add_player(player_red)
    game.add_player(player_green)
    game.add_player(player_blue)
    game.add_player(player_yellow)
    
    # game.start_game() # No la iniciamos aquí para poder controlar el estado
    return game

@pytest.fixture
def started_game_4_players(game_4_players: GameAggregate) -> GameAggregate:
    """
    Retorna un juego iniciado con 4 jugadores.
    """
    game_4_players.start_game() # Asume que el orden de turn_order es el de adición
    return game_4_players

# --- Pruebas para Dice ---

class TestDice:
    """
    Pruebas unitarias para métodos utilitarios de Dice.
    """

    def test_roll_dice(self):
        """
        Verifica que los valores de los dados estén en el rango válido.
        """
        d1, d2 = Dice.roll()
        assert 1 <= d1 <= 6
        assert 1 <= d2 <= 6

    def test_are_pairs(self):
        """
        Verifica que are_pairs identifica correctamente los pares.
        """
        assert Dice.are_pairs(3, 3) is True
        assert Dice.are_pairs(1, 6) is False

# --- Pruebas para MoveValidator ---

class TestMoveValidatorValidateAndProcessRoll:
    """
    Pruebas unitarias para MoveValidator.validate_and_process_roll.
    """

    def test_roll_no_pairs(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que al no sacar pares se resetea el contador de pares consecutivos.
        """
        game = game_4_players
        player = game.players[Color.RED]
        player.consecutive_pairs_count = 1 # Simula que venía de un par
        
        result = move_validator.validate_and_process_roll(game, Color.RED, 3, 4)
        
        assert result == MoveResultType.OK
        assert player.consecutive_pairs_count == 0 # Se resetea
        assert game.current_player_doubles_count == 0 # Se actualiza o se resetea en next_turn

    def test_roll_first_pair(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que al sacar el primer par se incrementa el contador.
        """
        game = game_4_players
        player = game.players[Color.RED]
        
        result = move_validator.validate_and_process_roll(game, Color.RED, 3, 3)
        
        assert result == MoveResultType.OK
        assert player.consecutive_pairs_count == 1
        assert game.current_player_doubles_count == 1

    def test_roll_second_pair(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que al sacar el segundo par se incrementa el contador.
        """
        game = game_4_players
        player = game.players[Color.RED]
        player.consecutive_pairs_count = 1 # Venía del primer par
        game.current_player_doubles_count = 1

        result = move_validator.validate_and_process_roll(game, Color.RED, 5, 5)
        
        assert result == MoveResultType.OK
        assert player.consecutive_pairs_count == 2
        assert game.current_player_doubles_count == 2
        
    def test_roll_third_pair_burns(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que al sacar el tercer par se activa la penalización de quemar ficha.
        """
        game = game_4_players
        player = game.players[Color.RED]
        player.consecutive_pairs_count = 2 # Venía del segundo par
        game.current_player_doubles_count = 2

        result = move_validator.validate_and_process_roll(game, Color.RED, 1, 1)
        
        assert result == MoveResultType.THREE_PAIRS_BURN
        assert player.consecutive_pairs_count == 3 # Se mantiene en 3 hasta que GameService lo maneje
        assert game.current_player_doubles_count == 3


class TestMoveValidatorGetPossibleMovesAndValidate:
    """
    Pruebas unitarias para MoveValidator.get_possible_moves y lógica relacionada.
    """

    def test_exit_jail_with_pairs(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que una ficha puede salir de la cárcel con pares.
        """
        game = game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        
        jailed_piece_to_check = None
        for p in player.pieces:
            if p.is_in_jail:
                jailed_piece_to_check = p # Tomamos una ficha de referencia
                break
        assert jailed_piece_to_check is not None, "No se encontró ninguna ficha en la cárcel para la prueba"
        print(f"TEST_DEBUG: Ficha en cárcel seleccionada para chequeo: {jailed_piece_to_check.id}")

        d1, d2 = 3, 3 # Pares
        
        # Asegurar que el turno sea del jugador correcto
        game.current_turn_color = player_color 
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        # --- NUEVO PRINT CRUCIAL ---
        print(f"TEST_DEBUG: Contenido de possible_moves_dict recibido por la prueba: {possible_moves_dict}")
        # --------------------------

        found_jail_exit_move = False
        if not possible_moves_dict:
            print("TEST_DEBUG: possible_moves_dict está VACÍO.")
        
        for piece_uuid_str, moves in possible_moves_dict.items():
            # print(f"TEST_DEBUG: Iterando pieza del dict: {piece_uuid_str}, con movimientos: {moves}") # Opcional
            piece_from_player_list = player.get_piece_by_uuid(piece_uuid_str) # Verificar que la pieza exista en el jugador

            if piece_from_player_list and piece_from_player_list.is_in_jail:
                # print(f"TEST_DEBUG:   Pieza {piece_from_player_list.id} está en cárcel. Chequeando sus movimientos.") # Opcional
                for target_id, result_type, steps_used in moves:
                    # print(f"TEST_DEBUG:     Movimiento: target={target_id}, result={result_type}, steps={steps_used}") # Opcional
                    if result_type == MoveResultType.JAIL_EXIT_SUCCESS:
                        print(f"TEST_DEBUG:       ¡JAIL_EXIT_SUCCESS encontrado para pieza {piece_uuid_str}!")
                        assert target_id == game.board.get_salida_square_id_for_color(player_color)
                        assert steps_used == 0
                        found_jail_exit_move = True
                        break 
                if found_jail_exit_move:
                    break 
        
        print(f"TEST_DEBUG: Valor final de found_jail_exit_move: {found_jail_exit_move}")
        assert found_jail_exit_move is True, f"No se encontró JAIL_EXIT_SUCCESS. possible_moves_dict fue: {possible_moves_dict}"

    def test_exit_jail_no_pairs_fail(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que una ficha no puede salir de la cárcel sin pares.
        """
        game = game_4_players
        player_color = Color.RED
        # Ficha en cárcel
        assert game.players[player_color].pieces[0].is_in_jail is True

        d1, d2 = 3, 4 # No son pares
        possible_moves = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        # No debería haber movimientos JAIL_EXIT_SUCCESS
        for piece_uuid_str, moves in possible_moves.items():
            for _, result_type, _ in moves:
                assert result_type != MoveResultType.JAIL_EXIT_SUCCESS
    
    def test_move_piece_on_board_simple(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica un movimiento simple en el tablero con pasos válidos.
        """
        game = started_game_4_players # Juego iniciado, turno de ROJO
        player_color = Color.RED
        player = game.players[player_color]
        
        # Poner una ficha en juego manualmente para la prueba
        piece_to_test = player.pieces[0]
        piece_to_test.is_in_jail = False
        start_pos_id = game.board.get_salida_square_id_for_color(player_color) + 1 # Casilla después de salida
        game.board.get_square(start_pos_id).add_piece(piece_to_test)
        
        d1, d2 = 2, 3 # Total 5
        possible_moves = move_validator.get_possible_moves(game, player_color, d1, d2)

        expected_target_with_5_steps = game.board.advance_piece_logic(start_pos_id, 5, player_color)
        
        found_move = False
        if str(piece_to_test.id) in possible_moves:
            for target_id, result_type, steps_used in possible_moves[str(piece_to_test.id)]:
                if steps_used == 5 and target_id == expected_target_with_5_steps:
                    assert result_type == MoveResultType.OK
                    found_move = True
                    break
        assert found_move, f"No se encontró movimiento OK de 5 pasos para la ficha desde {start_pos_id}"

    def test_move_to_capture(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede capturar a otra.
        """
        game = started_game_4_players
        attacker_color = Color.RED
        defender_color = Color.GREEN
        
        attacker_player = game.players[attacker_color]
        defender_player = game.players[defender_color]

        # Poner ficha atacante
        attacker_piece = attacker_player.pieces[0]
        attacker_piece.is_in_jail = False
        attacker_start_pos = 1 # Casilla 1
        game.board.get_square(attacker_start_pos).add_piece(attacker_piece)

        # Poner ficha defensora
        defender_piece = defender_player.pieces[0]
        defender_piece.is_in_jail = False
        defender_target_pos = 4 # Casilla 4
        game.board.get_square(defender_target_pos).add_piece(defender_piece)
        
        # Atacante necesita moverse 3 pasos para capturar (1 -> 4)
        d1, d2 = 1, 2 
        possible_moves = move_validator.get_possible_moves(game, attacker_color, d1, d2)

        found_capture_move = False
        if str(attacker_piece.id) in possible_moves:
            for target_id, result_type, steps_used in possible_moves[str(attacker_piece.id)]:
                if target_id == defender_target_pos and steps_used == (d1+d2) : # Mover con la suma
                    assert result_type == MoveResultType.CAPTURE
                    found_capture_move = True
                    break
        assert found_capture_move, "No se encontró movimiento de captura esperado."

    def test_move_to_safe_square_occupied_by_other_is_blocked(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que mover a un seguro ocupado por otro color está bloqueado.
        """
        game = started_game_4_players
        attacker_color = Color.RED
        defender_color = Color.GREEN
        
        attacker_player = game.players[attacker_color]
        defender_player = game.players[defender_color]

        # Poner ficha atacante
        attacker_piece = attacker_player.pieces[0]
        attacker_piece.is_in_jail = False
        attacker_start_pos = 5 # Va a intentar caer en el seguro 6
        game.board.get_square(attacker_start_pos).add_piece(attacker_piece)

        # Poner ficha defensora en una casilla SEGURO
        defender_piece = defender_player.pieces[0]
        defender_piece.is_in_jail = False
        safe_pos_idx = 6 # Esta es una casilla SEGURO
        assert game.board.get_square(safe_pos_idx).type == SquareType.SEGURO
        game.board.get_square(safe_pos_idx).add_piece(defender_piece)
        
        d1, d2 = 1, 0 # Mover 1 paso
        possible_moves = move_validator.get_possible_moves(game, attacker_color, d1, d2) # d2 es 0 para forzar uso de d1

        found_blocked_move = False
        if str(attacker_piece.id) in possible_moves:
            for target_id, result_type, steps_used in possible_moves[str(attacker_piece.id)]:
                if target_id == safe_pos_idx and steps_used == d1:
                    # Según la lógica actual, si la casilla es segura para el defensor,
                    # y el atacante no puede capturar, debería ser BLOCKED_BY_WALL
                    # porque no puedes ocupar un seguro ya ocupado.
                    assert result_type == MoveResultType.BLOCKED_BY_WALL
                    found_blocked_move = True
                    break
        assert found_blocked_move, "Esperaba BLOCKED_BY_WALL al intentar mover a seguro ocupado por otro."

    def test_exit_jail_fail_if_occupied_by_own_barrier(self, move_validator: MoveValidator, game_4_players: GameAggregate):
        """
        Verifica que una ficha no puede salir de la cárcel si la salida está bloqueada por barrera propia.
        """
        game = game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        
        salida_square_id = game.board.get_salida_square_id_for_color(player_color)
        salida_square = game.board.get_square(salida_square_id)
        assert salida_square is not None, "La casilla de salida no debería ser None"

        # Colocar dos fichas del jugador ROJO en su propia casilla de salida
        piece1_on_salida = player.pieces[1] # Usamos fichas diferentes a la que intentará salir
        piece1_on_salida.is_in_jail = False
        salida_square.add_piece(piece1_on_salida) # pieza1_on_salida.position se actualiza a salida_square_id

        piece2_on_salida = player.pieces[2]
        piece2_on_salida.is_in_jail = False
        salida_square.add_piece(piece2_on_salida) # pieza2_on_salida.position se actualiza a salida_square_id
        
        assert len(salida_square.occupants) == 2
        assert all(p.color == player_color for p in salida_square.occupants)

        # La ficha 0 del jugador ROJO sigue en la cárcel e intentará salir
        jailed_piece_to_try_exit = player.pieces[0]
        assert jailed_piece_to_try_exit.is_in_jail is True

        d1, d2 = 6, 6 # Pares para intentar salir
        game.current_turn_color = player_color # Es el turno del jugador
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        print(f"TEST_DEBUG (barrier): possible_moves_dict = {possible_moves_dict}")

        # Verificar que para la jailed_piece_to_try_exit, no haya un JAIL_EXIT_SUCCESS.
        # Y opcionalmente, verificar si se ofrece JAIL_EXIT_FAIL_OCCUPIED_START.
        jailed_piece_uuid_str = str(jailed_piece_to_try_exit.id)
        
        if jailed_piece_uuid_str in possible_moves_dict:
            moves_for_jailed_piece = possible_moves_dict[jailed_piece_uuid_str]
            # print(f"TEST_DEBUG (barrier): Moves for jailed piece {jailed_piece_uuid_str}: {moves_for_jailed_piece}")
            
            has_jail_exit_success_option = False
            has_jail_exit_fail_occupied_option = False
            
            for _target_id, result_type, _steps_used in moves_for_jailed_piece:
                if result_type == MoveResultType.JAIL_EXIT_SUCCESS:
                    has_jail_exit_success_option = True
                if result_type == MoveResultType.JAIL_EXIT_FAIL_OCCUPIED_START:
                    has_jail_exit_fail_occupied_option = True
            
            assert not has_jail_exit_success_option, "No debería poder salir de cárcel si la salida está bloqueada por barrera propia."
            # Si tu get_possible_moves está configurado para devolver fallos informativos:
            # assert has_jail_exit_fail_occupied_option, "Debería indicar que la salida está ocupada."
        else:
            # Si no hay entrada para la ficha en el diccionario, también es un pase (no hay movimientos válidos para ella)
            print(f"TEST_DEBUG (barrier): No se generaron movimientos para la ficha en cárcel {jailed_piece_uuid_str} con salida bloqueada.")
            pass # Esto es aceptable si los movimientos fallidos no se añaden.

    def test_move_normal_to_empty_square(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que mover a una casilla vacía está permitido.
        """
        game = started_game_4_players # Juego ya iniciado, turno de ROJO
        player_color = Color.RED
        player = game.players[player_color]

        # Poner una ficha en juego para la prueba
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False
        start_pos_id = game.board.get_salida_square_id_for_color(player_color) # Empezar en la salida
        game.board.get_square(start_pos_id).add_piece(piece_to_move)
        
        d1, d2 = 2, 3 # Mover 2, 3, o 5 pasos
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles"
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        
        # Verificar que se ofrece movimiento con 5 pasos
        expected_target_5 = game.board.advance_piece_logic(start_pos_id, 5, player_color)
        found_move_5_steps = any(
            target_id == expected_target_5 and result_type == MoveResultType.OK and steps_used == 5
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_move_5_steps, f"No se encontró movimiento OK de 5 pasos a casilla vacía {expected_target_5}"

        # Verificar que se ofrece movimiento con 2 pasos
        expected_target_2 = game.board.advance_piece_logic(start_pos_id, 2, player_color)
        found_move_2_steps = any(
            target_id == expected_target_2 and result_type == MoveResultType.OK and steps_used == 2
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_move_2_steps, f"No se encontró movimiento OK de 2 pasos a casilla vacía {expected_target_2}"

    def test_move_to_form_own_pair_on_square(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede formar par con otra del mismo color.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]

        # Ficha 1 ya en una casilla
        piece1 = player.pieces[0]
        piece1.is_in_jail = False
        pos_piece1 = game.board.get_salida_square_id_for_color(player_color) + 5 # Casilla 5
        game.board.get_square(pos_piece1).add_piece(piece1)

        # Ficha 2 intentará moverse a la misma casilla
        piece2 = player.pieces[1]
        piece2.is_in_jail = False
        pos_piece2_start = game.board.get_salida_square_id_for_color(player_color) + 2 # Casilla 2
        game.board.get_square(pos_piece2_start).add_piece(piece2)

        steps_to_target = pos_piece1 - pos_piece2_start # 3 pasos
        d1, d2 = 1, 2 # Total 3
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece2_uuid_str = str(piece2.id)
        assert piece2_uuid_str in possible_moves_dict, "Ficha 2 debería tener movimientos posibles"
        
        moves_for_piece2 = possible_moves_dict[piece2_uuid_str]
        found_move_to_pair = any(
            target_id == pos_piece1 and result_type == MoveResultType.OK and steps_used == steps_to_target
            for target_id, result_type, steps_used in moves_for_piece2
        )
        assert found_move_to_pair, f"No se encontró movimiento OK para formar par en casilla {pos_piece1}"

    def test_move_fail_if_target_has_own_two_pieces(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que mover a una casilla con dos fichas propias está bloqueado.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]

        target_pos_id = game.board.get_salida_square_id_for_color(player_color) + 7 # Casilla 7
        target_square = game.board.get_square(target_pos_id)
        assert target_square is not None

        # Poner dos fichas propias en la casilla objetivo
        piece1_on_target = player.pieces[0]
        piece1_on_target.is_in_jail = False
        target_square.add_piece(piece1_on_target)

        piece2_on_target = player.pieces[1]
        piece2_on_target.is_in_jail = False
        target_square.add_piece(piece2_on_target)
        assert len(target_square.occupants) == 2

        # Ficha 3 intentará moverse a esa misma casilla
        piece3_to_move = player.pieces[2]
        piece3_to_move.is_in_jail = False
        pos_piece3_start = game.board.get_salida_square_id_for_color(player_color) + 4 # Casilla 4
        game.board.get_square(pos_piece3_start).add_piece(piece3_to_move)

        steps_to_target = target_pos_id - pos_piece3_start # 3 pasos
        d1, d2 = 1, 2 # Total 3
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece3_uuid_str = str(piece3_to_move.id)
        assert piece3_uuid_str in possible_moves_dict, "Ficha 3 debería tener opciones evaluadas"

        moves_for_piece3 = possible_moves_dict[piece3_uuid_str]
        found_blocked_by_own = any(
            target_id == target_pos_id and result_type == MoveResultType.BLOCKED_BY_OWN and steps_used == steps_to_target
            for target_id, result_type, steps_used in moves_for_piece3
        )
        # Si BLOCKED_BY_OWN no se añade a possible_moves, entonces no debería haber un OK para ese target y steps.
        found_ok_move_to_full_square = any(
             target_id == target_pos_id and result_type == MoveResultType.OK and steps_used == steps_to_target
            for target_id, result_type, steps_used in moves_for_piece3
        )

        if found_blocked_by_own:
            assert True # El validador informó correctamente del bloqueo
        else:
            assert not found_ok_move_to_full_square, "No debería haber un movimiento OK a una casilla ya llena con fichas propias."

    def test_move_into_passageway(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede entrar al pasillo.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False

        # Entrada para ROJO es la casilla ANTES de su primer pasillo.
        # El ID de la casilla de tipo ENTRADA_PASILLO para ROJO.
        # Si SALIDA_SQUARES_INDICES[Color.RED] es 0, ENTRADA_PASILLO es 67 (0 - 1 + 68) % 68.
        entrada_pasillo_square_main_track_id = game.board.get_entrada_pasillo_square_id_for_color(player_color)
        # Colocamos la ficha a 2 pasos ANTES de la casilla de ENTRADA_PASILLO en el carril principal
        start_pos_id = (entrada_pasillo_square_main_track_id - 2 + NUM_MAIN_TRACK_SQUARES) % NUM_MAIN_TRACK_SQUARES
        game.board.get_square(start_pos_id).add_piece(piece_to_move)
        
        d1, d2 = 1, 2 # Total 3 pasos. 2 para llegar a la casilla ENTRADA_PASILLO, 1 para entrar al pasillo[0]
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles."
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        
        expected_passageway_entry_id = ('pas', player_color, 0) # Primera casilla del pasillo
        
        found_move_into_passageway = any(
            target_id == expected_passageway_entry_id and \
            result_type == MoveResultType.OK and \
            steps_used == (d1 + d2)
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_move_into_passageway, \
            f"No se encontró movimiento OK a la primera casilla del pasillo {expected_passageway_entry_id}. Movimientos: {moves_for_piece}"

    def test_move_within_passageway(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede moverse dentro del pasillo.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False

        start_passageway_pos_id = ('pas', player_color, 2) # Casilla 3 del pasillo (índice 2)
        game.board.get_square(start_passageway_pos_id).add_piece(piece_to_move)
        piece_to_move.squares_advanced_in_path = 2 + 1 # k es 0-indexed

        d1, d2 = 1, 1 # Total 2 pasos
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles."
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        expected_passageway_target_id = ('pas', player_color, 4) # Mover 2 pasos desde índice 2 a índice 4
        
        found_move_within_passageway = any(
            target_id == expected_passageway_target_id and \
            result_type == MoveResultType.OK and \
            steps_used == (d1 + d2)
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_move_within_passageway, \
            f"No se encontró movimiento OK dentro del pasillo a {expected_passageway_target_id}. Movimientos: {moves_for_piece}"

    def test_reach_meta_square(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede llegar a la casilla meta.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False

        # PASSAGEWAY_LENGTH es 7, así que los índices son 0-6. Meta es el índice 6.
        # Colocar la ficha en la penúltima casilla del pasillo (índice 5)
        start_passageway_pos_id = ('pas', player_color, 5)
        game.board.get_square(start_passageway_pos_id).add_piece(piece_to_move)
        piece_to_move.squares_advanced_in_path = 5 + 1

        d1, d2 = 1, 0 # Total 1 paso (d2=0 para forzar uso de d1)
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles."
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        expected_meta_id = ('pas', player_color, 6) # Última casilla del pasillo (META)
        
        found_reach_meta = any(
            target_id == expected_meta_id and \
            result_type == MoveResultType.OK and \
            steps_used == d1
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_reach_meta, \
            f"No se encontró movimiento OK a la casilla META {expected_meta_id}. Movimientos: {moves_for_piece}"
        assert game.board.get_square(expected_meta_id).type == SquareType.META

    def test_reach_cielo_exact_roll(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha puede llegar al cielo con tiro exacto.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False

        # Colocar la ficha en la casilla META
        meta_pos_id = ('pas', player_color, PASSAGEWAY_LENGTH - 1) # Índice 6
        game.board.get_square(meta_pos_id).add_piece(piece_to_move)
        piece_to_move.squares_advanced_in_path = PASSAGEWAY_LENGTH

        d1, d2 = 1, 0 # Total 1 paso, exacto para llegar al cielo
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles."
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        
        found_reach_cielo = any(
            target_id == game.board.cielo_square_id and \
            result_type == MoveResultType.PIECE_WINS and \
            steps_used == d1
            for target_id, result_type, steps_used in moves_for_piece
        )
        assert found_reach_cielo, \
            f"No se encontró movimiento PIECE_WINS al CIELO. Movimientos: {moves_for_piece}"

    def test_reach_cielo_fail_if_roll_too_high_from_meta(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha no puede llegar al cielo si el tiro es demasiado alto desde meta.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_to_move = player.pieces[0]
        piece_to_move.is_in_jail = False

        meta_pos_id = ('pas', player_color, PASSAGEWAY_LENGTH - 1)
        game.board.get_square(meta_pos_id).add_piece(piece_to_move)
        piece_to_move.squares_advanced_in_path = PASSAGEWAY_LENGTH

        d1, d2 = 1, 1 # Total 2 pasos (demasiado alto)
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_to_move.id)
        assert piece_uuid_str in possible_moves_dict, "La ficha debería tener movimientos posibles."
        
        moves_for_piece = possible_moves_dict[piece_uuid_str]
        
        found_exact_roll_needed = any(
            target_id == game.board.cielo_square_id and \
            result_type == MoveResultType.EXACT_ROLL_NEEDED and \
            steps_used == (d1 + d2)
            for target_id, result_type, steps_used in moves_for_piece
        )
        # También verificar que no haya un PIECE_WINS
        found_piece_wins = any(
            result_type == MoveResultType.PIECE_WINS for _, result_type, _ in moves_for_piece
        )
        assert found_exact_roll_needed, \
            f"No se encontró movimiento EXACT_ROLL_NEEDED al intentar llegar al CIELO con tiro alto. Movimientos: {moves_for_piece}"
        assert not found_piece_wins, "No debería haber PIECE_WINS si el tiro es muy alto desde META."

    def test_move_from_cielo_is_not_possible(self, move_validator: MoveValidator, started_game_4_players: GameAggregate):
        """
        Verifica que una ficha en el cielo no puede moverse.
        """
        game = started_game_4_players
        player_color = Color.RED
        player = game.players[player_color]
        piece_in_cielo = player.pieces[0]
        
        # Simular que la ficha ya llegó al cielo
        piece_in_cielo.is_in_jail = False
        piece_in_cielo.has_reached_cielo = True
        piece_in_cielo.position = game.board.cielo_square_id # O None, dependiendo de la implementación
        
        d1, d2 = 3, 3
        game.current_turn_color = player_color
        
        possible_moves_dict = move_validator.get_possible_moves(game, player_color, d1, d2)
        
        piece_uuid_str = str(piece_in_cielo.id)
        assert piece_uuid_str not in possible_moves_dict, \
            f"No deberían ofrecerse movimientos para una ficha que ya está en el CIELO. Movimientos: {possible_moves_dict}"

    # TODO: Más pruebas para:
    # - Salida de cárcel bloqueada por fichas propias. (Ya implementada como test_exit_jail_fail_if_occupied_by_own_barrier)
    # - Mover a casilla con 2 fichas propias (debería ser BLOCKED_BY_OWN). (Ya implementada como test_move_fail_if_target_has_own_two_pieces)
    # - Validar que solo se puedan usar d1, d2, d1+d2 cuando no son pares.
    # - Validar que con pares, se pueda usar la suma para mover fichas en juego.