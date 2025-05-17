import pytest
import uuid
from unittest.mock import AsyncMock

from app.core.enums import Color, GameState
from app.services.game_service import GameService, GameServiceError
from app.models.domain.game import GameAggregate
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

    async def test_join_game_success(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        existing_game = GameAggregate(game_id=game_id, max_players_limit=4)
        initial_player = Player(user_id="user_creator", color=Color.RED)
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

    async def test_join_game_fail_if_full(self, game_service: GameService, mock_game_repo: AsyncMock):
        game_id = uuid.uuid4()
        full_game = GameAggregate(game_id=game_id, max_players_limit=2)
        full_game.add_player(Player(user_id="user1", color=Color.RED))
        full_game.add_player(Player(user_id="user2", color=Color.GREEN))
        assert len(full_game.players) == full_game.max_players
        full_game.state = GameState.READY_TO_START
        mock_game_repo.get_by_id.return_value = full_game

        with pytest.raises(GameServiceError, match="La partida ya está llena."):
            await game_service.join_game(game_id, "user_new", Color.BLUE)

    # TODO: test_join_game_fail_if_color_taken
    # TODO: test_join_game_fail_if_user_already_in_game
    # TODO: test_join_game_fail_if_not_waiting_for_players

@pytest.mark.asyncio
class TestGameServiceRollAndMove:
    # Aquí irían las pruebas para roll_dice, move_piece, handle_three_pairs, pass_turn
    pass
