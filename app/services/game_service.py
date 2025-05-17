from __future__ import annotations
import uuid
from typing import Optional, Tuple, List, Dict, TYPE_CHECKING

from app.core.enums import Color, GameState, MoveResultType, SquareType
from app.repositories.base_repository import GameRepository
from app.rules.move_validator import MoveValidator
from app.rules.dice import Dice
from app.models.domain.player import Player, PIECES_PER_PLAYER

# --- Importa las constantes y GameAggregate a nivel de módulo ---
from app.models.domain.game import GameAggregate, MIN_PLAYERS, MAX_PLAYERS

if TYPE_CHECKING:
    from app.models.domain.piece import Piece
    from app.models.domain.square import SquareId
    from app.models.schemas import GameEventPydantic
    # Ensure GameAggregate is imported for type hinting if not already
    # from app.models.domain.game import GameAggregate

class GameServiceError(Exception):
    """Excepción base para errores del servicio de juego."""
    def __init__(self, message: str, result_type: Optional[MoveResultType] = None):
        super().__init__(message)
        self.result_type = result_type

class GameNotFoundError(GameServiceError):
    def __init__(self, game_id: uuid.UUID):
        super().__init__(f"Partida con ID {game_id} no encontrada.")

class PlayerNotInGameError(GameServiceError):
    def __init__(self, user_id: str, game_id: uuid.UUID):
        super().__init__(f"Jugador {user_id} no encontrado en la partida {game_id}.")

class NotPlayerTurnError(GameServiceError):
    def __init__(self, user_id: str, game_id: uuid.UUID):
        super().__init__(f"No es el turno del jugador {user_id} en la partida {game_id}.", MoveResultType.NOT_YOUR_TURN)


class GameService:
    """
    Servicio para gestionar la lógica de las partidas de Parqués.
    """
    _repository: GameRepository
    _validator: MoveValidator
    _dice: Dice

    def __init__(self, repository: GameRepository, validator: MoveValidator, dice_roller: Dice):
        self._repository = repository
        self._validator = validator
        self._dice = dice_roller
        print("GameService initialized.")

    async def create_new_game(self, creator_user_id: str, creator_color: Color, max_players: int = MAX_PLAYERS) -> GameAggregate:
        """
        Crea una nueva partida de Parqués.
        El creador se añade automáticamente como el primer jugador.
        """
        game_id = uuid.uuid4()
        game = GameAggregate(game_id=game_id, max_players_limit=max_players) 
        
        creator_player = Player(user_id=creator_user_id, color=creator_color)
        if not game.add_player(creator_player):
            raise GameServiceError("No se pudo añadir al jugador creador a la nueva partida.")

        await self._repository.save(game)
        print(f"GameService: Nueva partida creada con ID: {game.id} por {creator_user_id} ({creator_color.name})")
        return game

    async def join_game(self, game_id: uuid.UUID, user_id: str, requested_color: Color) -> GameAggregate:
        """
        Permite a un usuario unirse a una partida existente.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        async with game.lock: # Asegurar atomicidad al modificar la partida
            if game.state != GameState.WAITING_PLAYERS:
                raise GameServiceError("La partida no está esperando jugadores.")
            if len(game.players) >= game.max_players:
                raise GameServiceError("La partida ya está llena.")
            if requested_color in game.players:
                raise GameServiceError(f"El color {requested_color.name} ya está tomado.")
            
            for existing_player in game.players.values():
                if existing_player.user_id == user_id:
                    raise GameServiceError(f"El usuario {user_id} ya está en la partida.")


            new_player = Player(user_id=user_id, color=requested_color)
            if not game.add_player(new_player): # add_player actualiza el estado si es necesario
                 # Esta condición de fallo ya está cubierta por las validaciones anteriores
                raise GameServiceError(f"No se pudo unir al jugador {user_id} con color {requested_color.name}.")

            await self._repository.save(game)
            print(f"GameService: Jugador {user_id} ({requested_color.name}) se unió a la partida {game_id}")
        return game

    async def start_game(self, game_id: uuid.UUID, starting_user_id: str) -> GameAggregate:
        """
        Inicia una partida si está lista.
        El `starting_user_id` debe ser uno de los jugadores en la partida, usualmente el creador o
        alguien con permiso para iniciarla.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)
        
        # Verificar que el usuario que intenta iniciar está en el juego
        player_can_start = False
        for p_color, p_obj in game.players.items():
            if p_obj.user_id == starting_user_id:
                player_can_start = True
                break
        if not player_can_start:
            raise GameServiceError(f"Usuario {starting_user_id} no tiene permiso para iniciar la partida {game_id}.")


        async with game.lock:
            if game.state != GameState.READY_TO_START:
                raise GameServiceError("La partida no está lista para iniciar o ya ha comenzado.")
            if len(game.players) < MIN_PLAYERS: 
                raise GameServiceError(f"Se necesitan al menos {MIN_PLAYERS} jugadores para iniciar.")
            if not game.start_game():
                raise GameServiceError("Falló la transición de estado al iniciar la partida internamente.")
            print(f"GameService: Partida {game_id} iniciada. Primer turno: {game.current_turn_color.name if game.current_turn_color else 'N/A'}")
            await self._repository.save(game)
        return game

    async def roll_dice(self, game_id: uuid.UUID, user_id: str) -> Tuple[GameAggregate, Tuple[int, int], MoveResultType, Dict[str, List[Tuple[SquareId, MoveResultType, int]]]]:
        """
        Un jugador lanza los dados.
        1. Valida que sea el turno del jugador.
        2. Lanza los dados.
        3. Valida el resultado del tiro (ej. 3 pares).
        4. Si el tiro es válido, calcula los movimientos posibles.
        Devuelve:
            - El estado actualizado del juego.
            - La tirada de dados (d1, d2).
            - El resultado de la validación del tiro (ej. THREE_PAIRS_BURN).
            - Los movimientos posibles.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        player_color, player_object = self._get_player_from_user_id(game, user_id)

        async with game.lock:
            if game.state != GameState.IN_PROGRESS:
                raise GameServiceError("La partida no está en curso.")
            if game.current_turn_color != player_color:
                raise NotPlayerTurnError(user_id, game_id)
            # Check if player can roll:
            # Player can roll if dice_roll_count is 0 (first roll of their turn part)
            # OR if they got pairs and are eligible for another roll (consecutive_pairs_count is 1 or 2)
            if game.dice_roll_count > 0 and not (player_object.consecutive_pairs_count > 0 and player_object.consecutive_pairs_count < 3):
                raise GameServiceError("Ya has lanzado los dados en este turno o debes mover primero.")

            d1, d2 = self._dice.roll()
            game.last_dice_roll = (d1, d2) # GUARDAR EL TIRO
            game.dice_roll_count += 1 # Incrementar contador de tiros en el turno

            game._add_game_event("dice_rolled", {"player_color": player_color.name, "dice": [d1, d2]})

            roll_validation_result = self._validator.validate_and_process_roll(game, player_color, d1, d2)

            possible_moves = {}
            if roll_validation_result != MoveResultType.THREE_PAIRS_BURN:
                possible_moves = self._validator.get_possible_moves(game, player_color, d1, d2)
                # Log if no moves are possible and it's not a three-pairs burn scenario
                # and player has pieces not in jail (meaning they are not forced to pass due to all pieces jailed)
                if not possible_moves and player_object.get_jailed_pieces_count() < PIECES_PER_PLAYER:
                    game._add_game_event("no_valid_moves", {"player_color": player_color.name, "dice": [d1, d2]})
                    # El jugador deberá pasar el turno. La API llamará a pass_player_turn.

            await self._repository.save(game)
        
        return game, (d1, d2), roll_validation_result, possible_moves

    async def move_piece(
        self,
        game_id: uuid.UUID,
        user_id: str,
        piece_uuid_str: str, # UUID de la ficha a mover
        target_square_id_from_player: SquareId, # El destino que el jugador eligió de los `possible_moves`
        steps_taken_for_move: int # Cuántos pasos del dado se usaron (d1, d2, o d1+d2)
        # original_dice_roll ya no se pasa como parámetro
    ) -> GameAggregate:
        """
        Mueve una ficha seleccionada por el jugador a un destino elegido.
        Valida que el movimiento sea uno de los presentados como posibles.
        Aplica las consecuencias del movimiento (captura, salida de cárcel, etc.).
        Maneja el final del turno o la repetición del mismo.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        current_player = game.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise NotPlayerTurnError(user_id, game_id)
        
        if game.state != GameState.IN_PROGRESS:
            raise GameServiceError("La partida no está en curso.")
        
        if not game.last_dice_roll: # No se ha tirado en este turno (o el estado es inválido)
             raise GameServiceError("Debes lanzar los dados antes de mover.")

        piece_to_move = current_player.get_piece_by_uuid(piece_uuid_str)
        if not piece_to_move:
            raise GameServiceError(f"Ficha {piece_uuid_str} no encontrada para el jugador {user_id}.")

        original_dice_roll = game.last_dice_roll # USAR EL TIRO GUARDADO
        is_roll_pairs = (original_dice_roll[0] == original_dice_roll[1])
        
        move_result_type, validated_target_id = self._validator._validate_single_move_attempt(
            game=game,
            piece_to_move=piece_to_move,
            steps=steps_taken_for_move,
            is_roll_pairs=is_roll_pairs
        )

        if validated_target_id != target_square_id_from_player or \
           move_result_type in [MoveResultType.INVALID_PIECE, MoveResultType.INVALID_ROLL, MoveResultType.OUT_OF_BOUNDS]:
            if move_result_type == MoveResultType.OUT_OF_BOUNDS and piece_to_move.position is not None:
                 current_square_obj = game.board.get_square(piece_to_move.position)
                 if current_square_obj and current_square_obj.type == SquareType.META:
                     raise GameServiceError("Se requiere un tiro exacto para llegar al cielo y este movimiento se pasa.", MoveResultType.EXACT_ROLL_NEEDED)
            
            raise GameServiceError(f"Movimiento inválido o no permitido: {move_result_type.name}", move_result_type)

        async with game.lock:
            current_board_position_id = piece_to_move.position

            if move_result_type == MoveResultType.JAIL_EXIT_SUCCESS:
                salida_square = game.board.get_square(target_square_id_from_player)
                if salida_square:
                    if current_board_position_id:
                        old_square = game.board.get_square(current_board_position_id)
                        if old_square: old_square.remove_piece(piece_to_move)
                    
                    piece_to_move.is_in_jail = False # Actualizar estado de la ficha
                    piece_to_move.move_to(target_square_id_from_player) # Actualizar posición de la ficha
                    salida_square.add_piece(piece_to_move) # Añadir al nuevo square
                    game._add_game_event("piece_left_jail", {"player": current_player.color.name, "piece_id": str(piece_to_move.id), "target_square": target_square_id_from_player})
                    
                    # game.dice_roll_count = 0 # This will be handled by end-of-turn logic
                else:
                    raise GameServiceError("Error interno: Casilla de salida no encontrada.")

            elif move_result_type == MoveResultType.CAPTURE:
                target_square = game.board.get_square(target_square_id_from_player)
                if not target_square: raise GameServiceError("Error interno: Casilla destino no encontrada para captura.")

                captured_piece_ids = []
                pieces_to_send_to_jail = list(target_square.occupants)
                for occ_piece in pieces_to_send_to_jail:
                    if occ_piece.color != current_player.color: # Cannot capture own pieces
                        target_square.remove_piece(occ_piece)
                        occ_piece.send_to_jail()
                        # Need to get the player of the captured piece to update their pieces_in_jail count if tracked
                        captured_player = game.get_player(occ_piece.color)
                        if captured_player:
                            # Assuming Player object has a way to notify it or its pieces are jailed
                            pass # Logic for updating captured_player if needed
                        captured_piece_ids.append(str(occ_piece.id))
                
                if current_board_position_id:
                    old_square = game.board.get_square(current_board_position_id)
                    if old_square: old_square.remove_piece(piece_to_move)
                
                piece_to_move.move_to(target_square_id_from_player) # Actualizar posición de la ficha
                target_square.add_piece(piece_to_move) # Añadir al nuevo square
                game._add_game_event("piece_captured", {
                    "player": current_player.color.name, "piece_id": str(piece_to_move.id), 
                    "target_square": target_square_id_from_player, "captured_ids": captured_piece_ids
                })

            elif move_result_type == MoveResultType.PIECE_WINS:
                if current_board_position_id:
                    old_square = game.board.get_square(current_board_position_id)
                    if old_square: old_square.remove_piece(piece_to_move)
                
                piece_to_move.move_to(target_square_id_from_player, is_cielo=True)
                game._add_game_event("piece_reached_cielo", {"player": current_player.color.name, "piece_id": str(piece_to_move.id)})

                if current_player.check_win_condition(): # This should update player.has_won
                    game.winner = current_player.color
                    game.state = GameState.FINISHED
                    game._add_game_event("game_won", {"player": current_player.color.name})
                    # No further turn logic if game is won
            
            elif move_result_type == MoveResultType.OK:
                target_square = game.board.get_square(target_square_id_from_player)
                if not target_square: raise GameServiceError("Error interno: Casilla destino no encontrada.")

                if current_board_position_id:
                    old_square = game.board.get_square(current_board_position_id)
                    if old_square: old_square.remove_piece(piece_to_move)
                
                piece_to_move.move_to(target_square_id_from_player) # Actualizar posición de la ficha
                target_square.add_piece(piece_to_move) # Añadir al nuevo square
                game._add_game_event("piece_moved", {"player": current_player.color.name, "piece_id": str(piece_to_move.id), "from": current_board_position_id, "to": target_square_id_from_player})

            else: # Should not happen if validation is correct
                raise GameServiceError(f"Resultado de movimiento no manejado después de la validación: {move_result_type.name}", move_result_type)

            # --- Refined end-of-turn logic ---
            game_ended_by_win = (game.state == GameState.FINISHED)

            if not game_ended_by_win:
                player_continues_turn = False

                if move_result_type == MoveResultType.JAIL_EXIT_SUCCESS and is_roll_pairs:
                    # Salió de cárcel con pares -> Vuelve a tirar.
                    # player.consecutive_pairs_count NO se resetea (handled by validate_and_process_roll).
                    # game.current_player_doubles_count NO se resetea (handled by validate_and_process_roll).
                    game.dice_roll_count = 0 # Permite nuevo tiro
                    player_continues_turn = True
                    game._add_game_event("player_rolls_again_after_jail_exit", {"player": current_player.color.name})
                
                elif is_roll_pairs and current_player.consecutive_pairs_count < 3 and move_result_type != MoveResultType.JAIL_EXIT_SUCCESS:
                    # Sacó pares (1ro o 2do) y no fue salida de cárcel (ya manejado arriba) -> Repite turno.
                    # player.consecutive_pairs_count NO se resetea.
                    # game.current_player_doubles_count NO se resetea.
                    game.dice_roll_count = 0 # Permite nuevo tiro
                    player_continues_turn = True
                    game._add_game_event("player_repeats_turn_for_pairs", {"player": current_player.color.name})

                if not player_continues_turn:
                    # El turno pasa al siguiente jugador.
                    current_player.reset_consecutive_pairs() # Jugador actual pierde racha de pares.
                    game.next_turn() # Esto resetea game.current_player_doubles_count
                                     # y actualiza current_turn_color.
                    game.last_dice_roll = None # Limpiar el tiro usado para el turno que termina.
                    game.dice_roll_count = 0 # Reset para el próximo jugador.
            
            await self._repository.save(game)
        return game

    async def handle_three_pairs_penalty(self, game_id: uuid.UUID, user_id: str, piece_to_burn_uuid_str: Optional[str] = None) -> GameAggregate:
        """
        Maneja la penalización por tres pares seguidos.
        Una ficha del jugador se envía a la cárcel.
        El turno pasa al siguiente jugador.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        player_penalized = None
        # Ensure we are getting the player object from game.players
        for color, p_obj in game.players.items():
            if p_obj.user_id == user_id:
                player_penalized = p_obj
                break
        
        if not player_penalized:
            raise PlayerNotInGameError(user_id, game_id)
        
        if player_penalized.color != game.current_turn_color or player_penalized.consecutive_pairs_count < 3:
            raise GameServiceError("El jugador no está en condición de ser penalizado por tres pares.")

        async with game.lock:
            piece_to_send_to_jail: Optional[Piece] = None
            if piece_to_burn_uuid_str:
                piece_to_send_to_jail = player_penalized.get_piece_by_uuid(piece_to_burn_uuid_str)
                if not piece_to_send_to_jail or piece_to_send_to_jail.is_in_jail or piece_to_send_to_jail.has_reached_cielo:
                    piece_to_send_to_jail = None 
            
            if not piece_to_send_to_jail:
                fichas_en_juego = player_penalized.get_pieces_in_play() # This method needs to be in Player
                if fichas_en_juego:
                    # TODO: Implementar lógica para "más adelantada" si es necesario.
                    piece_to_send_to_jail = fichas_en_juego[0] 

            if piece_to_send_to_jail:
                current_pos_of_burned_piece = piece_to_send_to_jail.position
                if current_pos_of_burned_piece:
                    square_of_burned_piece = game.board.get_square(current_pos_of_burned_piece)
                    if square_of_burned_piece:
                        square_of_burned_piece.remove_piece(piece_to_send_to_jail)
                
                piece_to_send_to_jail.send_to_jail()
                game._add_game_event("piece_burned_three_pairs", {
                    "player": player_penalized.color.name, 
                    "piece_id": str(piece_to_send_to_jail.id)
                })
            else:
                 game._add_game_event("no_piece_to_burn_three_pairs", {"player": player_penalized.color.name})

            player_penalized.reset_consecutive_pairs()
            game.next_turn()

            await self._repository.save(game)
        return game

    async def pass_player_turn(self, game_id: uuid.UUID, user_id: str) -> GameAggregate:
        """
        Handles the scenario where a player has no valid moves and must pass their turn.
        This method should be called by the API/controller if roll_dice returns
        an empty possible_moves list and the roll_validation_result is not THREE_PAIRS_BURN.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        current_player = game.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise NotPlayerTurnError(user_id, game_id)
        
        # Additional check: ensure there were indeed no moves or specific condition met.
        # For now, we trust the caller (API layer) makes this call appropriately.
        # For example, after roll_dice returned empty possible_moves.

        async with game.lock:
            if game.state != GameState.IN_PROGRESS:
                raise GameServiceError("La partida no está en curso.")

            game._add_game_event("player_passed_turn", {
                "player_color": current_player.color.name,
                "reason": "no_valid_moves"
            })

            # Reset player's consecutive pairs count as they are losing the turn.
            current_player.reset_consecutive_pairs()
            
            # Advance to the next player.
            game.next_turn() # game.next_turn() also resets game.current_player_doubles_count.
            game.last_dice_roll = None # Clear the roll as the turn is passed.
            game.dice_roll_count = 0 # Reset for the next player.

            await self._repository.save(game)
        
        return game

    def _get_player_from_user_id(self, game: GameAggregate, user_id: str) -> Tuple[Color, Player]:
        """Helper para obtener el color y objeto del jugador a partir de su user_id."""
        for color_enum, p_obj in game.players.items():
            if p_obj.user_id == user_id:
                return color_enum, p_obj
        raise PlayerNotInGameError(user_id, game.id)

    # --- Otros métodos podrían ser necesarios (ej. get_game_state, etc.) ---
