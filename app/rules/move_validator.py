"""Move validation logic for Parqués.

This module defines the MoveValidator class, which validates dice rolls and piece movements
according to the rules of Colombian Parqués.
"""
from __future__ import annotations
from typing import Tuple, Optional, TYPE_CHECKING, List, Dict

from app.core.enums import Color, SquareType, MoveResultType
from app.models.domain.board import SALIDA_SQUARES_INDICES, PASSAGEWAY_LENGTH

if TYPE_CHECKING:
    from app.models.domain.game import GameAggregate
    from app.models.domain.player import Player
    from app.models.domain.piece import Piece
    from app.models.domain.square import Square, SquareId


class MoveValidator:
    """Validates dice rolls and piece movements according to Parqués rules."""

    def validate_and_process_roll(
        self,
        game: 'GameAggregate',
        player_color: Color,
        d1: int,
        d2: int
    ) -> MoveResultType:
        """Validates a dice roll and updates the player's pairs state.

        Args:
            game: Current game instance.
            player_color: Color of the player rolling the dice.
            d1: Value of the first die.
            d2: Value of the second die.

        Returns:
            MoveResultType indicating the result of the roll.
        """
        player = game.get_player(player_color)
        if not player:
            return MoveResultType.INVALID_PIECE 

        is_roll_pairs = (d1 == d2)

        if is_roll_pairs:
            player.increment_consecutive_pairs()
            game.current_player_doubles_count = player.consecutive_pairs_count

            if player.consecutive_pairs_count == 3:
                return MoveResultType.THREE_PAIRS_BURN
            else:
                return MoveResultType.OK
        else:
            player.reset_consecutive_pairs()
            return MoveResultType.OK

    def get_possible_moves(
        self,
        game: 'GameAggregate',
        player_color: Color,
        d1: int,
        d2: int
    ) -> Dict[str, List[Tuple['SquareId', MoveResultType, int]]]:
        """Returns all possible moves for a player given a dice roll.
        
        Assumes jail exit has already been handled by GameService.

        Args:
            game: Current game instance.
            player_color: Player's color.
            d1: Value of the first die.
            d2: Value of the second die.

        Returns:
            Dictionary mapping piece UUID to list of possible moves.
            Each move is a tuple: (target_square_id, move_result_type, steps_used).
        """
        player = game.get_player(player_color)
        if not player or game.current_turn_color != player_color:
            return {}

        possible_moves_for_player: Dict[str, List[Tuple[SquareId, MoveResultType, int]]] = {}
        is_pairs = (d1 == d2)

        for piece in player.pieces:
            # Skip pieces in jail or cielo - jail exit is handled by GameService
            if piece.has_reached_cielo or piece.is_in_jail:
                continue

            current_piece_options: List[Tuple[SquareId, MoveResultType, int]] = []
            
            # Calculate movement options for pieces on the board
            dice_steps_to_evaluate: List[int] = []
            if is_pairs:
                dice_steps_to_evaluate.append(d1 + d2)
            else:
                dice_steps_to_evaluate.append(d1)
                dice_steps_to_evaluate.append(d2)
                if d1 != d2:
                    dice_steps_to_evaluate.append(d1 + d2)
            
            unique_steps = sorted(list(set(s for s in dice_steps_to_evaluate if s > 0)), reverse=True)

            for steps in unique_steps:
                validation_result, target_id = self._validate_single_move_attempt(
                    game=game,
                    piece_to_move=piece,
                    steps=steps,
                    is_roll_pairs=is_pairs
                )
                if validation_result not in [MoveResultType.INVALID_PIECE, MoveResultType.INVALID_ROLL] and target_id is not None:
                    current_piece_options.append((target_id, validation_result, steps))
                elif validation_result == MoveResultType.EXACT_ROLL_NEEDED and target_id is not None:
                     current_piece_options.append((target_id, validation_result, steps))

            if current_piece_options:
                possible_moves_for_player[str(piece.id)] = current_piece_options
                
        return possible_moves_for_player

    def _validate_single_move_attempt(
        self,
        game: 'GameAggregate',
        piece_to_move: 'Piece',
        steps: int,
        is_roll_pairs: bool
    ) -> Tuple[MoveResultType, Optional['SquareId']]:
        """Validates a single move attempt.
        
        Allows unlimited stacking of own pieces and coexistence in safe squares.
        Capture only occurs in non-safe squares.

        Args:
            game: Current game instance.
            piece_to_move: Piece attempting to move.
            steps: Number of steps to move.
            is_roll_pairs: Whether the dice roll was pairs.

        Returns:
            Tuple of (MoveResultType, target_square_id).
        """
        board = game.board

        if piece_to_move.is_in_jail:
            if not is_roll_pairs:
                return MoveResultType.JAIL_EXIT_FAIL_NO_PAIRS, None
            
            salida_square_id = board.get_salida_square_id_for_color(piece_to_move.color)
            return MoveResultType.JAIL_EXIT_SUCCESS, salida_square_id

        current_pos = piece_to_move.position
        if current_pos is None:
            return MoveResultType.INVALID_PIECE, None

        target_square_id = board.advance_piece_logic(current_pos, steps, piece_to_move.color)

        if target_square_id is None:
            current_square_obj = board.get_square(current_pos)
            if current_square_obj and current_square_obj.type == SquareType.META:
                 if isinstance(current_pos, tuple) and current_pos[0] == 'pas':
                     k_actual = current_pos[2]
                     if k_actual == PASSAGEWAY_LENGTH - 1 and (k_actual + steps) > PASSAGEWAY_LENGTH:
                         return MoveResultType.EXACT_ROLL_NEEDED, board.cielo_square_id
            return MoveResultType.OUT_OF_BOUNDS, None

        target_square = board.get_square(target_square_id)
        if not target_square:
            return MoveResultType.OUT_OF_BOUNDS, None 

        if target_square.type == SquareType.CIELO:
            return MoveResultType.PIECE_WINS, target_square_id

        other_color_pieces_at_target = target_square.get_other_color_pieces(piece_to_move.color)

        if other_color_pieces_at_target:
            is_target_safe_for_mover = target_square.is_safe_square_for_piece(piece_to_move.color)
            
            if not is_target_safe_for_mover:
                return MoveResultType.CAPTURE, target_square_id
            else:
                return MoveResultType.OK, target_square_id
        else:
            return MoveResultType.OK, target_square_id