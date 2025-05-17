#tests/unit/test_services.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.core.enums import Color, GameState, MoveResultType, SquareType
from app.services.game_service import GameService, GameServiceError, NotPlayerTurnError, PlayerNotInGameError, GameNotFoundError
from app.models.domain.game import GameAggregate, MIN_PLAYERS, MAX_PLAYERS
from app.models.domain.player import Player
from app.rules.dice import Dice
from app.rules.move_validator import MoveValidator

@pytest.fixture
def mock_game_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    return repo

@pytest.fixture
def move_validator_instance() -> MoveValidator:
    return MoveValidator()

@pytest.fixture
def dice_roller_instance() -> Dice:
    return Dice()

@pytest.fixture
def game_service(
    mock_game_repo: AsyncMock,
    move_validator_instance: MoveValidator,
    dice_roller_instance: Dice
) -> GameService:
    return GameService(
        repository=mock_game_repo,
        validator=move_validator_instance,
        dice_roller=dice_roller_instance
    )

@pytest.fixture
def started_game_with_two_players() -> GameAggregate:
    game = GameAggregate(game_id=uuid.uuid4(), max_players_limit=2)
    player_red = Player(user_id="user_red", color_input=Color.RED)
    player_green = Player(user_id="user_green", color_input=Color.GREEN)
    game.add_player(player_red)
    game.add_player(player_green)
    game.start_game() # RED starts
    return game

@pytest.mark.asyncio
class TestGameServiceCreateAndJoin:
    async def test_create_new_game(self, game_service: GameService, mock_game_repo: AsyncMock):
        creator_id = "user1"
        creator_color = Color.RED
        max_p = 4

        created_game = await game_service.create_new_game(creator_id, creator_color, max_p)

        assert created_game is not None
        assert created_game.max_players == max_p
        assert creator_color in created_game.players
        assert created_game.players[creator_color].user_id == creator_id
        # Puede ser READY_TO_START si MIN_PLAYERS==1, o WAITING_PLAYERS si MIN_PLAYERS>1
        assert created_game.state in (GameState.READY_TO_START, GameState.WAITING_PLAYERS)
        mock_game_repo.save.assert_called_once_with(created_game)

    async def test_create_new_game_fail_invalid_max_players_too_low(self, game_service: GameService):
        creator_id = "user_test"
        creator_color = Color.BLUE
        invalid_max_players = MIN_PLAYERS - 1 # Menor que MIN_PLAYERS

        expected_message = f"El número máximo de jugadores debe estar entre {MIN_PLAYERS} y {MAX_PLAYERS}."

        with pytest.raises(GameServiceError, match=expected_message):
            await game_service.create_new_game(creator_id, creator_color, invalid_max_players)

    async def test_create_new_game_fail_invalid_max_players_too_high(self, game_service: GameService):
        creator_id = "user_test"
        creator_color = Color.GREEN
        invalid_max_players = MAX_PLAYERS + 1 # Mayor que MAX_PLAYERS

        expected_message = f"El número máximo de jugadores debe estar entre {MIN_PLAYERS} y {MAX_PLAYERS}."
        
        with pytest.raises(GameServiceError, match=expected_message):
            await game_service.create_new_game(creator_id, creator_color, invalid_max_players)

    async def test_join_game_fail_game_not_found(self, game_service: GameService, mock_game_repo: AsyncMock):
        non_existent_game_id = uuid.uuid4()
        
        # Configurar el mock para que devuelva None cuando se busque este ID
        mock_game_repo.get_by_id.return_value = None

        user_trying_to_join = "user_ghost"
        color_for_ghost_user = Color.GREEN

        # Verificar que se lanza GameNotFoundError
        expected_message = f"Partida con ID {non_existent_game_id} no encontrada."
        with pytest.raises(GameNotFoundError, match=expected_message):
            await game_service.join_game(non_existent_game_id, user_trying_to_join, color_for_ghost_user)
        
        # Verificar que get_by_id fue llamado con el ID correcto
        mock_game_repo.get_by_id.assert_called_once_with(non_existent_game_id)
        # Asegurarse de que save no fue llamado
        mock_game_repo.save.assert_not_called()

    async def test_join_game_success(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        existing_game = GameAggregate(game_id=game_id, max_players_limit=4)
        initial_player = Player(user_id="user_creator", color_input=Color.RED)
        existing_game.add_player(initial_player)
        existing_game.state = GameState.WAITING_PLAYERS
        mock_game_repo.get_by_id.return_value = existing_game

        user_id_join = "user_joiner"
        requested_color = Color.GREEN

        joined_game_state = await game_service.join_game(game_id, user_id_join, requested_color)

        assert requested_color in joined_game_state.players
        assert joined_game_state.players[requested_color].user_id == user_id_join
        assert joined_game_state.state == GameState.READY_TO_START
        mock_game_repo.save.assert_called_once_with(joined_game_state)

    async def test_join_game_fail_if_not_waiting_players(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        # Crear un juego que NO está en estado WAITING_PLAYERS
        game_not_waiting = GameAggregate(game_id=game_id, max_players_limit=2)
        
        # Añadir un jugador inicial para que no esté vacío (opcional, pero realista)
        player1 = Player(user_id="user1", color_input=Color.RED)
        game_not_waiting.add_player(player1)
        
        # Establecer el estado a IN_PROGRESS (o cualquier estado que no sea WAITING_PLAYERS)
        game_not_waiting.state = GameState.IN_PROGRESS 
        
        mock_game_repo.get_by_id.return_value = game_not_waiting

        user_trying_to_join = "user_late"
        color_for_late_user = Color.BLUE

        with pytest.raises(GameServiceError, match="La partida no está esperando jugadores."):
            await game_service.join_game(game_id, user_trying_to_join, color_for_late_user)
        
        # Asegurarse de que save no fue llamado porque la operación debería haber fallado antes
        mock_game_repo.save.assert_not_called()

    async def test_join_game_fail_if_full(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        full_game = GameAggregate(game_id=game_id, max_players_limit=2)
        player1_added = full_game.add_player(Player(user_id="user1", color_input=Color.RED))
        assert player1_added is True
        player2_added = full_game.add_player(Player(user_id="user2", color_input=Color.GREEN))
        assert player2_added is True
        assert len(full_game.players) == full_game.max_players
        # Forzar el estado para que la comprobación de "lleno" sea la que falle,
        # después de que la comprobación de game.state != GameState.WAITING_PLAYERS pase.
        full_game.state = GameState.WAITING_PLAYERS # Sobrescribir el estado para el test
        mock_game_repo.get_by_id.return_value = full_game

        with pytest.raises(GameServiceError, match="La partida ya está llena."):
            await game_service.join_game(game_id, "user_new", Color.BLUE)

    async def test_join_game_fail_if_color_taken(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        existing_game = GameAggregate(game_id=game_id, max_players_limit=4)
        # Jugador 1 ya tomó el color ROJO
        player1 = Player(user_id="user1", color_input=Color.RED)
        existing_game.add_player(player1)
        existing_game.state = GameState.WAITING_PLAYERS
        mock_game_repo.get_by_id.return_value = existing_game

        user_id_joiner = "user_joiner"
        requested_color = Color.RED
        with pytest.raises(GameServiceError, match=f"El color {requested_color.name} ya está tomado."):
            await game_service.join_game(game_id, user_id_joiner, requested_color)

    async def test_start_game_success(self, game_service: GameService, mock_game_repo: AsyncMock):
        from app.models.domain.game import MIN_PLAYERS

        game_id = uuid.uuid4()
        game_to_start = GameAggregate(game_id=game_id, max_players_limit=4)
        players_to_add = [
            Player(user_id="user1", color_input=Color.RED),
            Player(user_id="user2", color_input=Color.GREEN)
        ]
        assert len(players_to_add) >= MIN_PLAYERS

        for p in players_to_add:
            game_to_start.add_player(p)
        assert game_to_start.state == GameState.READY_TO_START

        mock_game_repo.get_by_id.return_value = game_to_start

        starting_user = players_to_add[0].user_id
        started_game = await game_service.start_game(game_id, starting_user)

        assert started_game.state == GameState.IN_PROGRESS
        assert started_game.current_turn_color is not None
        assert started_game.current_turn_color in [p.color for p in players_to_add]
        mock_game_repo.save.assert_called_with(started_game)

@pytest.mark.asyncio
class TestGameServiceRollAndMove:
    async def test_roll_dice_success(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        monkeypatch: pytest.MonkeyPatch  # Use monkeypatch instead of mocker
    ):
        game = started_game_with_two_players
        mock_game_repo.get_by_id.return_value = game
        
        # Use monkeypatch instead of mocker.patch.object
        dice_mock = MagicMock(return_value=(1, 2))
        monkeypatch.setattr(game_service._dice, 'roll', dice_mock)
        
        validator_mock = MagicMock(return_value={"some_piece_id": [(1, MoveResultType.OK, 1)]})
        monkeypatch.setattr(game_service._validator, 'get_possible_moves', validator_mock)

        updated_game, dice_roll, roll_result, possible_moves = await game_service.roll_dice(game.id, "user_red")

        assert dice_roll == (1, 2)
        assert roll_result == MoveResultType.OK
        assert "some_piece_id" in possible_moves
        mock_game_repo.save.assert_called_with(game)

    async def test_roll_dice_not_player_turn(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate
    ):
        game = started_game_with_two_players
        mock_game_repo.get_by_id.return_value = game
        
        with pytest.raises(NotPlayerTurnError):
            await game_service.roll_dice(game.id, "user_green") # RED's turn

    async def test_roll_dice_game_not_in_progress(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock
    ):
        game = GameAggregate(game_id=uuid.uuid4())
        game.state = GameState.WAITING_PLAYERS
        player_red = Player(user_id="user_red", color_input=Color.RED)
        game.add_player(player_red) # Add player to avoid PlayerNotInGameError
        mock_game_repo.get_by_id.return_value = game

        with pytest.raises(GameServiceError, match="La partida no está en curso."):
            await game_service.roll_dice(game.id, "user_red")

    async def test_roll_dice_three_pairs_result(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        monkeypatch: pytest.MonkeyPatch  # Use monkeypatch instead of mocker
    ):
        game = started_game_with_two_players
        player_red = game.players[Color.RED]
        player_red.consecutive_pairs_count = 2
        game.current_player_doubles_count = 2
        mock_game_repo.get_by_id.return_value = game
        
        # Use monkeypatch instead of mocker.patch.object
        dice_mock = MagicMock(return_value=(3, 3))
        monkeypatch.setattr(game_service._dice, 'roll', dice_mock)

        _, _, roll_result, possible_moves = await game_service.roll_dice(game.id, "user_red")

        assert roll_result == MoveResultType.THREE_PAIRS_BURN
        assert not possible_moves # No moves calculated on three pairs burn

    async def test_roll_dice_no_moves_available(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        mocker: pytest.MonkeyPatch
    ):
        game = started_game_with_two_players
        player_red_object = game.players[Color.RED] # Get the Player object

        # Ensure player_red has one piece out of jail for the "no_valid_moves" event condition
        if player_red_object.pieces:
            piece_to_free = player_red_object.pieces[0]
            piece_to_free.is_in_jail = False

        mock_game_repo.get_by_id.return_value = game
        mocker.patch.object(game_service._dice, 'roll', return_value=(1, 2))
        mocker.patch.object(game_service._validator, 'get_possible_moves', return_value={}) # No moves
        mock_add_event = mocker.patch.object(game, '_add_game_event')

        _, _, _, possible_moves = await game_service.roll_dice(game.id, "user_red")

        assert not possible_moves
        mock_add_event.assert_any_call("no_valid_moves", {"player_color": Color.RED.name, "dice": [1, 2]})

    async def test_move_piece_simple_ok_and_pass_turn(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        mocker: pytest.MonkeyPatch
    ):
        game = started_game_with_two_players # RED's turn
        player_red = game.players[Color.RED]
        piece_to_move = player_red.pieces[0]
        piece_to_move.is_in_jail = False
        initial_pos_id = game.board.get_salida_square_id_for_color(Color.RED)
        # Ensure the salida square exists before adding a piece.
        salida_square = game.board.get_square(initial_pos_id)
        assert salida_square is not None
        salida_square.add_piece(piece_to_move)
        
        target_pos_id = game.board.advance_piece_logic(initial_pos_id, 3, Color.RED)
        steps_for_move = 3

        # Simulate that dice have been rolled for this turn
        game.last_dice_roll = (1, 2) # Or any roll that justifies the move
        game.dice_roll_count = 1 # Simulate one roll has occurred

        mock_game_repo.get_by_id.return_value = game
        mocker.patch.object(
            game_service._validator, 
            '_validate_single_move_attempt', 
            return_value=(MoveResultType.OK, target_pos_id)
        )
        mock_add_event = mocker.patch.object(game, '_add_game_event')

        updated_game = await game_service.move_piece(
            game.id, "user_red", str(piece_to_move.id), target_pos_id, steps_for_move
        )

        assert piece_to_move.position == target_pos_id
        assert updated_game.current_turn_color == Color.GREEN # Turn passed
        assert player_red.consecutive_pairs_count == 0
        mock_add_event.assert_any_call("piece_moved", {"player": Color.RED.name, "piece_id": str(piece_to_move.id), "from": initial_pos_id, "to": target_pos_id})
        mock_game_repo.save.assert_called_with(game)

    async def test_handle_three_pairs_penalty_auto_chooses_piece(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        mocker: pytest.MonkeyPatch
    ):
        game = started_game_with_two_players # RED's turn
        player_red = game.players[Color.RED]
        player_red.consecutive_pairs_count = 3 # Condition for penalty
        
        piece_in_play = player_red.pieces[0]
        piece_in_play.is_in_jail = False
        initial_pos_id = game.board.get_salida_square_id_for_color(Color.RED)
        game.board.get_square(initial_pos_id).add_piece(piece_in_play)
        
        # Mock get_pieces_in_play to control which piece is chosen
        mocker.patch.object(player_red, 'get_pieces_in_play', return_value=[piece_in_play])
        mock_game_repo.get_by_id.return_value = game
        mock_add_event = mocker.patch.object(game, '_add_game_event')

        updated_game = await game_service.handle_three_pairs_penalty(game.id, "user_red", None)

        assert piece_in_play.is_in_jail
        assert player_red.consecutive_pairs_count == 0
        assert updated_game.current_turn_color == Color.GREEN # Turn passed
        mock_add_event.assert_any_call("piece_burned_three_pairs", {"player": Color.RED.name, "piece_id": str(piece_in_play.id)})
        mock_game_repo.save.assert_called_with(game)

    async def test_pass_player_turn_no_moves(
        self,
        game_service: GameService,
        mock_game_repo: AsyncMock,
        started_game_with_two_players: GameAggregate,
        mocker: pytest.MonkeyPatch
    ):
        game = started_game_with_two_players # RED's turn
        player_red = game.players[Color.RED]
        player_red.consecutive_pairs_count = 1 # Simulate they had a pair but no moves
        game.current_player_doubles_count = 1

        mock_game_repo.get_by_id.return_value = game
        mock_add_event = mocker.patch.object(game, '_add_game_event')

        updated_game = await game_service.pass_player_turn(game.id, "user_red")

        assert updated_game.current_turn_color == Color.GREEN
        assert player_red.consecutive_pairs_count == 0
        assert updated_game.current_player_doubles_count == 0 # Reset by next_turn
        mock_add_event.assert_any_call("player_passed_turn", {"player_color": Color.RED.name, "reason": "no_valid_moves"})
        mock_game_repo.save.assert_called_with(game)
