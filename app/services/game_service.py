"""Game service logic for Parqués.

This module defines the GameService class and related exceptions, which encapsulate
the main business logic for managing Parqués games, including player actions,
turn management, dice rolling, and move validation.
"""
from __future__ import annotations
import uuid
from typing import Optional, Tuple, List, Dict, TYPE_CHECKING

from app.core.enums import Color, GameState, MoveResultType, SquareType
from app.repositories.base_repository import GameRepository
from app.rules.move_validator import MoveValidator
from app.rules.dice import Dice
from app.models.domain.player import Player, PIECES_PER_PLAYER
from app.models.domain.game import GameAggregate, MIN_PLAYERS, MAX_PLAYERS

if TYPE_CHECKING:
    from app.models.domain.piece import Piece
    from app.models.domain.square import SquareId
    from app.models.schemas import GameEventPydantic


class GameServiceError(Exception):
    """Base exception for game service errors.

    Args:
        message: Error description.
        result_type: Optional MoveResultType for additional detail.
    """
    
    def __init__(self, message: str, result_type: Optional[MoveResultType] = None):
        super().__init__(message)
        self.result_type = result_type


class GameNotFoundError(GameServiceError):
    """Exception raised when a game is not found.
    
    Args:
        game_id: ID of the game that was not found.
    """
    
    def __init__(self, game_id: uuid.UUID):
        super().__init__(f"Game with ID {game_id} not found.")


class PlayerNotInGameError(GameServiceError):
    """Exception raised when a player is not in the game.
    
    Args:
        user_id: ID of the user.
        game_id: ID of the game.
    """
    
    def __init__(self, user_id: str, game_id: uuid.UUID):
        super().__init__(f"Player {user_id} not found in game {game_id}.")


class NotPlayerTurnError(GameServiceError):
    """Exception raised when a player attempts an action outside their turn.
    
    Args:
        user_id: ID of the user.
        game_id: ID of the game.
    """
    
    def __init__(self, user_id: str, game_id: uuid.UUID):
        super().__init__(f"It's not player {user_id}'s turn in game {game_id}.", MoveResultType.NOT_YOUR_TURN)


class GameService:
    """Service for managing Parqués game logic.

    Handles player actions, turns, dice rolling, move validation, and state transitions.
    
    Attributes:
        _repository: Game data repository.
        _validator: Move validation logic.
        _dice: Dice rolling functionality.
    """
    
    def __init__(self, repository: GameRepository, validator: MoveValidator, dice_roller: Dice):
        """Initialize the GameService.

        Args:
            repository: Game repository instance.
            validator: Move validator instance.
            dice_roller: Dice roller instance.
        """
        self._repository = repository
        self._validator = validator
        self._dice = dice_roller

    async def create_new_game(self, creator_user_id: str, creator_color: Color, max_players: int = MAX_PLAYERS) -> GameAggregate:
        """Create a new Parqués game and add the creator as the first player.

        Args:
            creator_user_id: Creator's user ID.
            creator_color: Color chosen by the creator.
            max_players: Maximum number of players allowed.

        Returns:
            Created GameAggregate instance.
            
        Raises:
            GameServiceError: If max_players is invalid or player cannot be added.
        """
        game_id = uuid.uuid4()
        
        if not (MIN_PLAYERS <= max_players <= MAX_PLAYERS):
            raise GameServiceError(f"Maximum players must be between {MIN_PLAYERS} and {MAX_PLAYERS}.")

        game = GameAggregate(game_id=game_id, max_players_limit=max_players)
        
        creator_player = Player(user_id=creator_user_id, color_input=creator_color)
        if not game.add_player(creator_player):
            raise GameServiceError("Could not add creator to the game.")

        await self._repository.save(game)
        return game

    async def join_game(self, game_id: uuid.UUID, user_id: str, requested_color: Color) -> GameAggregate:
        """Allow a user to join an existing game.

        Args:
            game_id: Game UUID.
            user_id: User ID.
            requested_color: Requested color.

        Returns:
            Updated GameAggregate instance.
            
        Raises:
            GameNotFoundError: If the game doesn't exist.
            GameServiceError: If join conditions are not met.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        actual_requested_color_enum = self._validate_and_convert_color(requested_color)

        async with game.lock:
            self._validate_join_conditions(game, user_id, actual_requested_color_enum)
            
            new_player = Player(user_id=user_id, color_input=actual_requested_color_enum)
            if not game.add_player(new_player):
                raise GameServiceError(f"Could not join player {user_id} with color {actual_requested_color_enum.name}.")

            await self._repository.save(game)
        return game

    async def start_game(self, game_id: uuid.UUID, starting_user_id: str) -> GameAggregate:
        """Start a game if it's ready.

        Args:
            game_id: Game UUID.
            starting_user_id: ID of the player starting the game.

        Returns:
            Updated GameAggregate instance.
            
        Raises:
            GameNotFoundError: If the game doesn't exist.
            GameServiceError: If the game cannot be started.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)
        
        if not self._player_can_start_game(game, starting_user_id):
            raise GameServiceError(f"User {starting_user_id} doesn't have permission to start game {game_id}.")

        async with game.lock:
            if game.state != GameState.READY_TO_START:
                raise GameServiceError("Game is not ready to start or has already begun.")
            if len(game.players) < MIN_PLAYERS:
                raise GameServiceError(f"At least {MIN_PLAYERS} players are needed to start.")
            if not game.start_game():
                raise GameServiceError("Failed to start game due to internal state transition error.")
                
            await self._repository.save(game)
        return game

    async def roll_dice(
        self,
        game_id: uuid.UUID,
        user_id: str
    ) -> Tuple[GameAggregate, Tuple[int, int], MoveResultType, Dict[str, List[Tuple['SquareId', MoveResultType, int]]]]:
        """Handle a player's dice roll with automatic actions and move calculation.

        Validates the roll, performs massive jail exit if applicable (all pieces with pairs),
        calculates possible moves, and includes the 3-attempt rule for players stuck in jail.

        Args:
            game_id: Game UUID.
            user_id: Player ID.

        Returns:
            Tuple containing:
                - Updated GameAggregate.
                - Dice roll (d1, d2).
                - Roll result type (e.g., OK, THREE_PAIRS_BURN).
                - Dictionary of possible moves after any automatic actions.
                
        Raises:
            GameNotFoundError: If the game doesn't exist.
            GameServiceError: If the roll is not allowed.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        player_color, player_object = self._get_player_from_user_id(game, user_id)

        async with game.lock:
            self._validate_dice_roll_conditions(game, player_color, player_object)
            
            if game.dice_roll_count == 0:
                game.moves_made_this_roll = 0

            d1, d2 = self._dice.roll()
            game.last_dice_roll = (d1, d2)
            game.dice_roll_count += 1

            game._add_game_event("dice_rolled", {"player_color": player_color.name, "dice": [d1, d2]})

            roll_validation_result = self._validator.validate_and_process_roll(game, player_color, d1, d2)

            if roll_validation_result == MoveResultType.THREE_PAIRS_BURN:
                await self._repository.save(game)
                return game, (d1, d2), roll_validation_result, {}

            pieces_exited_jail_automatically = self._handle_massive_jail_exit(game, player_color, player_object, d1, d2)
            
            if self._should_auto_pass_turn(game, player_object, d1, d2):
                return await self._handle_auto_turn_pass(game, player_color, d1, d2)

            possible_moves = self._validator.get_possible_moves(game, player_color, d1, d2)
            
            self._log_no_moves_if_applicable(game, player_color, player_object, possible_moves, pieces_exited_jail_automatically, d1, d2)

            await self._repository.save(game)
        
        return game, (d1, d2), roll_validation_result, possible_moves

    async def move_piece(
        self,
        game_id: uuid.UUID,
        user_id: str,
        piece_uuid_str: str,
        target_square_id_from_player: 'SquareId',
        steps_taken_for_move: int
    ) -> GameAggregate:
        """Move a selected piece to the chosen destination, applying game rules.

        Args:
            game_id: Game UUID.
            user_id: Player ID.
            piece_uuid_str: UUID of the piece to move.
            target_square_id_from_player: Target square ID.
            steps_taken_for_move: Number of steps used.

        Returns:
            Updated GameAggregate instance.
            
        Raises:
            GameNotFoundError: If the game doesn't exist.
            NotPlayerTurnError: If it's not the player's turn.
            GameServiceError: If the move is invalid.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        current_player = game.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise NotPlayerTurnError(user_id, game_id)
        
        self._validate_move_preconditions(game)
        
        piece_to_move = current_player.get_piece_by_uuid(piece_uuid_str)
        if not piece_to_move:
            raise GameServiceError(f"Piece {piece_uuid_str} not found for player {user_id}.")

        original_dice_roll = game.last_dice_roll
        is_roll_pairs = (original_dice_roll[0] == original_dice_roll[1])
        
        move_result_type, validated_target_id = self._validator._validate_single_move_attempt(
            game=game,
            piece_to_move=piece_to_move,
            steps=steps_taken_for_move,
            is_roll_pairs=is_roll_pairs
        )

        self._validate_move_result(move_result_type, validated_target_id, target_square_id_from_player, piece_to_move, game)

        async with game.lock:
            self._execute_piece_move(game, current_player, piece_to_move, target_square_id_from_player, move_result_type)
            self._handle_end_of_turn_logic(game, current_player, is_roll_pairs, steps_taken_for_move, move_result_type)
            await self._repository.save(game)
        return game

    async def handle_three_pairs_penalty(
        self,
        game_id: uuid.UUID,
        user_id: str,
        piece_to_burn_uuid_str: Optional[str] = None
    ) -> GameAggregate:
        """Handle the penalty for rolling three consecutive pairs.

        Args:
            game_id: Game UUID.
            user_id: Penalized player ID.
            piece_to_burn_uuid_str: Optional UUID of the piece to burn.

        Returns:
            Updated GameAggregate instance.
            
        Raises:
            GameNotFoundError: If the game doesn't exist.
            PlayerNotInGameError: If the player is not in the game.
            GameServiceError: If the penalty cannot be applied.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        player_penalized = self._find_player_by_user_id(game, user_id)
        if not player_penalized:
            raise PlayerNotInGameError(user_id, game_id)
        
        if player_penalized.color != game.current_turn_color or player_penalized.consecutive_pairs_count < 3:
            raise GameServiceError("Player is not in condition to be penalized for three pairs.")

        async with game.lock:
            piece_to_send_to_jail = self._select_piece_to_burn(player_penalized, piece_to_burn_uuid_str)
            self._execute_piece_burn(game, player_penalized, piece_to_send_to_jail)
            
            player_penalized.reset_consecutive_pairs()
            game.next_turn()

            await self._repository.save(game)
        return game

    async def pass_player_turn(self, game_id: uuid.UUID, user_id: str) -> GameAggregate:
        """Handle the scenario where a player passes their turn due to no valid moves.

        Args:
            game_id: Game UUID.
            user_id: Player ID.

        Returns:
            Updated GameAggregate instance.
            
        Raises:
            GameNotFoundError: If the game doesn't exist.
            NotPlayerTurnError: If it's not the player's turn.
            GameServiceError: If the game is not in progress.
        """
        game = await self._repository.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(game_id)

        current_player = game.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise NotPlayerTurnError(user_id, game_id)

        async with game.lock:
            if game.state != GameState.IN_PROGRESS:
                raise GameServiceError("Game is not in progress.")

            game._add_game_event("player_passed_turn", {
                "player_color": current_player.color.name,
                "reason": "no_valid_moves"
            })

            current_player.reset_consecutive_pairs()
            game.next_turn()
            game.last_dice_roll = None
            game.dice_roll_count = 0

            await self._repository.save(game)
        
        return game

    def _get_player_from_user_id(self, game: GameAggregate, user_id: str) -> Tuple[Color, Player]:
        """Get color and Player object from user_id.

        Args:
            game: GameAggregate instance.
            user_id: User ID.

        Returns:
            Tuple of (Color, Player).
            
        Raises:
            PlayerNotInGameError: If the user is not in the game.
        """
        for color_enum, p_obj in game.players.items():
            if p_obj.user_id == user_id:
                return color_enum, p_obj
        raise PlayerNotInGameError(user_id, game.id)

    def _validate_and_convert_color(self, requested_color: Color) -> Color:
        """Validate and convert color to enum instance."""
        if isinstance(requested_color, str):
            try:
                return Color(requested_color)
            except ValueError:
                raise GameServiceError(f"Color '{requested_color}' is not valid.")
        elif isinstance(requested_color, Color):
            return requested_color
        else:
            raise GameServiceError(f"Unexpected color type: {type(requested_color)}")

    def _validate_join_conditions(self, game: GameAggregate, user_id: str, color: Color) -> None:
        """Validate conditions for joining a game."""
        if game.state not in [GameState.WAITING_PLAYERS, GameState.READY_TO_START]:
            raise GameServiceError("Game is not waiting for players or has already started.")
        if len(game.players) >= game.max_players:
            raise GameServiceError("Game is already full.")
        if color in game.players:
            raise GameServiceError(f"Color {color.name} is already taken.")

        for existing_player in game.players.values():
            if existing_player.user_id == user_id:
                raise GameServiceError(f"User {user_id} is already in the game with color {existing_player.color.name}.", result_type=MoveResultType.ACTION_FAILED)

    def _player_can_start_game(self, game: GameAggregate, user_id: str) -> bool:
        """Check if user has permission to start the game."""
        return any(p_obj.user_id == user_id for p_obj in game.players.values())

    def _validate_dice_roll_conditions(self, game: GameAggregate, player_color: Color, player_object: Player) -> None:
        """Validate conditions for rolling dice."""
        if game.state != GameState.IN_PROGRESS:
            raise GameServiceError("Game is not in progress.")
        if game.current_turn_color != player_color:
            raise NotPlayerTurnError(player_object.user_id, game.id)

        is_stuck_in_jail = player_object.get_jailed_pieces_count() == PIECES_PER_PLAYER
        can_roll_again_on_pairs = player_object.consecutive_pairs_count > 0 and player_object.consecutive_pairs_count < 3
        
        if game.dice_roll_count > 0 and not can_roll_again_on_pairs:
            if not is_stuck_in_jail:
                raise GameServiceError("You have already rolled the dice this turn or must move first.")
            elif game.dice_roll_count >= 3:
                raise GameServiceError("You have used your 3 attempts to get out of jail. You must pass the turn.")

    def _handle_massive_jail_exit(self, game: GameAggregate, player_color: Color, player_object: Player, d1: int, d2: int) -> bool:
        """Handle massive jail exit logic for pairs."""
        is_pairs = (d1 == d2)
        pieces_exited_jail_automatically = False

        if is_pairs and player_object.get_jailed_pieces_count() > 0:
            jailed_pieces = player_object.get_jailed_pieces()
            salida_square_id = game.board.get_salida_square_id_for_color(player_color)
            salida_square = game.board.get_square(salida_square_id)
            
            if salida_square and jailed_pieces:
                exited_piece_ids = []
                for piece in list(jailed_pieces):
                    piece.is_in_jail = False
                    piece.move_to(salida_square_id)
                    salida_square.add_piece(piece)
                    exited_piece_ids.append(str(piece.id))
                
                if exited_piece_ids:
                    game._add_game_event("massive_jail_exit", {
                        "player": player_color.name, 
                        "exited_pieces": exited_piece_ids,
                        "target_square": salida_square_id
                    })
                    pieces_exited_jail_automatically = True
                    game.dice_roll_count = 0
                    game.moves_made_this_roll = 0
                    game._add_game_event("player_rolls_again_after_massive_jail_exit", {"player": player_color.name})

        return pieces_exited_jail_automatically

    def _should_auto_pass_turn(self, game: GameAggregate, player_object: Player, d1: int, d2: int) -> bool:
        """Check if turn should be automatically passed."""
        is_stuck_in_jail = player_object.get_jailed_pieces_count() == PIECES_PER_PLAYER
        is_pairs = (d1 == d2)
        return is_stuck_in_jail and not is_pairs and game.dice_roll_count >= 3

    async def _handle_auto_turn_pass(self, game: GameAggregate, player_color: Color, d1: int, d2: int) -> Tuple[GameAggregate, Tuple[int, int], MoveResultType, Dict]:
        """Handle automatic turn pass for failed jail attempts."""
        player_object = game.get_player(player_color)
        
        game._add_game_event("player_failed_three_jail_attempts", {
            "player_color": player_color.name,
            "attempts": game.dice_roll_count
        })
        
        player_object.reset_consecutive_pairs()
        game.next_turn()
        game.last_dice_roll = None
        game.dice_roll_count = 0
        
        await self._repository.save(game)
        return game, (d1, d2), MoveResultType.OK, {}

    def _log_no_moves_if_applicable(self, game: GameAggregate, player_color: Color, player_object: Player, 
                                   possible_moves: Dict, pieces_exited_jail_automatically: bool, d1: int, d2: int) -> None:
        """Log event if no valid moves are available."""
        if not possible_moves and not (pieces_exited_jail_automatically and game.dice_roll_count == 0):
            if player_object.get_jailed_pieces_count() < PIECES_PER_PLAYER:
                game._add_game_event("no_valid_moves", {"player_color": player_color.name, "dice": [d1, d2]})

    def _validate_move_preconditions(self, game: GameAggregate) -> None:
        """Validate preconditions for moving a piece."""
        if game.state != GameState.IN_PROGRESS:
            raise GameServiceError("Game is not in progress.")
        if not game.last_dice_roll:
            raise GameServiceError("You must roll the dice before moving.")

    def _validate_move_result(self, move_result_type: MoveResultType, validated_target_id: 'SquareId', 
                            target_square_id_from_player: 'SquareId', piece_to_move: 'Piece', game: GameAggregate) -> None:
        """Validate the result of move validation."""
        if validated_target_id != target_square_id_from_player or \
           move_result_type in [MoveResultType.INVALID_PIECE, MoveResultType.INVALID_ROLL, MoveResultType.OUT_OF_BOUNDS]:
            if move_result_type == MoveResultType.OUT_OF_BOUNDS and piece_to_move.position is not None:
                current_square_obj = game.board.get_square(piece_to_move.position)
                if current_square_obj and current_square_obj.type == SquareType.META:
                    raise GameServiceError("Exact roll required to reach heaven and this move overshoots.", MoveResultType.EXACT_ROLL_NEEDED)
            
            raise GameServiceError(f"Invalid or not allowed move: {move_result_type.name}", move_result_type)

    def _execute_piece_move(self, game: GameAggregate, current_player: Player, piece_to_move: 'Piece', 
                          target_square_id: 'SquareId', move_result_type: MoveResultType) -> None:
        """Execute the actual piece movement based on move result type."""
        current_board_position_id = piece_to_move.position

        if move_result_type == MoveResultType.JAIL_EXIT_SUCCESS:
            self._handle_jail_exit_move(game, current_player, piece_to_move, target_square_id, current_board_position_id)
        elif move_result_type == MoveResultType.CAPTURE:
            self._handle_capture_move(game, current_player, piece_to_move, target_square_id, current_board_position_id)
        elif move_result_type == MoveResultType.PIECE_WINS:
            self._handle_winning_move(game, current_player, piece_to_move, target_square_id, current_board_position_id)
        elif move_result_type == MoveResultType.OK:
            self._handle_normal_move(game, current_player, piece_to_move, target_square_id, current_board_position_id)
        else:
            raise GameServiceError(f"Unhandled move result after validation: {move_result_type.name}", move_result_type)

    def _handle_jail_exit_move(self, game: GameAggregate, player: Player, piece: 'Piece', target_id: 'SquareId', current_pos: Optional['SquareId']) -> None:
        """Handle jail exit move logic."""
        salida_square = game.board.get_square(target_id)
        if not salida_square:
            raise GameServiceError("Internal error: Exit square not found.")
            
        if current_pos:
            old_square = game.board.get_square(current_pos)
            if old_square:
                old_square.remove_piece(piece)
        
        piece.is_in_jail = False
        piece.move_to(target_id)
        salida_square.add_piece(piece)
        game._add_game_event("piece_left_jail", {
            "player": player.color.name, 
            "piece_id": str(piece.id), 
            "target_square": target_id
        })

    def _handle_capture_move(self, game: GameAggregate, player: Player, piece: 'Piece', target_id: 'SquareId', current_pos: Optional['SquareId']) -> None:
        """Handle capture move logic."""
        target_square = game.board.get_square(target_id)
        if not target_square:
            raise GameServiceError("Internal error: Target square not found for capture.")

        captured_piece_ids = []
        pieces_to_send_to_jail = list(target_square.occupants)
        for occ_piece in pieces_to_send_to_jail:
            if occ_piece.color != player.color:
                target_square.remove_piece(occ_piece)
                occ_piece.send_to_jail()
                captured_piece_ids.append(str(occ_piece.id))
        
        if current_pos:
            old_square = game.board.get_square(current_pos)
            if old_square:
                old_square.remove_piece(piece)
        
        piece.move_to(target_id)
        target_square.add_piece(piece)
        game._add_game_event("piece_captured", {
            "player": player.color.name, 
            "piece_id": str(piece.id), 
            "target_square": target_id, 
            "captured_ids": captured_piece_ids
        })

    def _handle_winning_move(self, game: GameAggregate, player: Player, piece: 'Piece', target_id: 'SquareId', current_pos: Optional['SquareId']) -> None:
        """Handle winning move logic."""
        if current_pos:
            old_square = game.board.get_square(current_pos)
            if old_square:
                old_square.remove_piece(piece)
        
        piece.move_to(target_id, is_cielo=True)
        game._add_game_event("piece_reached_cielo", {
            "player": player.color.name, 
            "piece_id": str(piece.id)
        })

        if player.check_win_condition():
            game.winner = player.color
            game.state = GameState.FINISHED
            game._add_game_event("game_won", {"player": player.color.name})

    def _handle_normal_move(self, game: GameAggregate, player: Player, piece: 'Piece', target_id: 'SquareId', current_pos: Optional['SquareId']) -> None:
        """Handle normal move logic."""
        target_square = game.board.get_square(target_id)
        if not target_square:
            raise GameServiceError("Internal error: Target square not found.")

        if current_pos:
            old_square = game.board.get_square(current_pos)
            if old_square:
                old_square.remove_piece(piece)
        
        piece.move_to(target_id)
        target_square.add_piece(piece)
        game._add_game_event("piece_moved", {
            "player": player.color.name, 
            "piece_id": str(piece.id), 
            "from": current_pos, 
            "to": target_id
        })

    def _handle_end_of_turn_logic(self, game: GameAggregate, current_player: Player, is_roll_pairs: bool, 
                                steps_taken: int, move_result_type: MoveResultType) -> None:
        """Handle end of turn logic after a move."""
        if not is_roll_pairs:
            game.moves_made_this_roll += 1

        game_ended_by_win = (game.state == GameState.FINISHED)
        player_continues_turn = False

        if not game_ended_by_win:
            if is_roll_pairs:
                player_continues_turn = self._handle_pairs_turn_logic(game, current_player, move_result_type)
            else:
                player_continues_turn = self._handle_non_pairs_turn_logic(game, steps_taken)

            if not player_continues_turn:
                current_player.reset_consecutive_pairs()
                game.next_turn()
                game.last_dice_roll = None
                game.dice_roll_count = 0

    def _handle_pairs_turn_logic(self, game: GameAggregate, player: Player, move_result_type: MoveResultType) -> bool:
        """Handle turn logic for pairs rolls."""
        if move_result_type == MoveResultType.JAIL_EXIT_SUCCESS:
            game.dice_roll_count = 0
            game.moves_made_this_roll = 0
            game._add_game_event("player_rolls_again_after_jail_exit", {"player": player.color.name})
            return True
        elif player.consecutive_pairs_count < 3 and move_result_type != MoveResultType.JAIL_EXIT_SUCCESS:
            game.dice_roll_count = 0
            game.moves_made_this_roll = 0
            game._add_game_event("player_repeats_turn_for_pairs", {"player": player.color.name})
            return True
        return False

    def _handle_non_pairs_turn_logic(self, game: GameAggregate, steps_taken: int) -> bool:
        """Handle turn logic for non-pairs rolls."""
        d1_orig, d2_orig = game.last_dice_roll
        
        if steps_taken == (d1_orig + d2_orig):
            game.moves_made_this_roll = 2
        
        if game.moves_made_this_roll < 2:
            game._add_game_event("player_may_use_second_die", {
                "player": game.get_current_player().color.name, 
                "roll": game.last_dice_roll, 
                "moves_made": game.moves_made_this_roll
            })
            return True
        return False

    def _find_player_by_user_id(self, game: GameAggregate, user_id: str) -> Optional[Player]:
        """Find player by user ID."""
        for p_obj in game.players.values():
            if p_obj.user_id == user_id:
                return p_obj
        return None

    def _select_piece_to_burn(self, player: Player, piece_uuid_str: Optional[str]) -> Optional['Piece']:
        """Select piece to burn for three pairs penalty."""
        piece_to_send_to_jail: Optional['Piece'] = None
        
        if piece_uuid_str:
            piece_to_send_to_jail = player.get_piece_by_uuid(piece_uuid_str)
            if not piece_to_send_to_jail or piece_to_send_to_jail.is_in_jail or piece_to_send_to_jail.has_reached_cielo:
                piece_to_send_to_jail = None 
        
        if not piece_to_send_to_jail:
            fichas_en_juego = player.get_pieces_in_play()
            if fichas_en_juego:
                piece_to_send_to_jail = fichas_en_juego[0]
        
        return piece_to_send_to_jail

    def _execute_piece_burn(self, game: GameAggregate, player: Player, piece_to_burn: Optional['Piece']) -> None:
        """Execute the burning of a piece."""
        if piece_to_burn:
            current_pos_of_burned_piece = piece_to_burn.position
            if current_pos_of_burned_piece:
                square_of_burned_piece = game.board.get_square(current_pos_of_burned_piece)
                if square_of_burned_piece:
                    square_of_burned_piece.remove_piece(piece_to_burn)
            
            piece_to_burn.send_to_jail()
            game._add_game_event("piece_burned_three_pairs", {
                "player": player.color.name, 
                "piece_id": str(piece_to_burn.id)
            })
        else:
            game._add_game_event("no_piece_to_burn_three_pairs", {"player": player.color.name})
