from collections import deque

import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *


class TestVoteHandlers:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
        return engine

    @pytest.fixture
    def dispatcher(self, mock_engine):
        return EventDispatcher(mock_engine)

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
        game.nominated = [2, 3, 4]
        game.current_votes = {2: 0, 3: 0, 4: 0}
        game.vote_history = {}
        game.voting_queue = deque(
            [
                game.players[1],
                game.players[2],
                game.players[3],
                game.players[4],
                game.players[5],
            ]
        )
        game.state = GameState.VOTING
        game.balance_players = []
        return game

    @pytest.mark.asyncio
    async def test_pre_vote_success(self, dispatcher, mock_engine, game):
        query = PreVoteQuery(QueryType.PRE_VOTE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_vote(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithOptions)
        assert "Против кого вы голосуете?" in response.text
        assert len(response.candidates) == len(game.nominated)

        options_text = [opt[0] for opt in response.candidates]
        assert "№2" in str(options_text)
        assert "№3" in str(options_text)
        assert "№4" in str(options_text)

    @pytest.mark.asyncio
    async def test_pre_vote_revote_state(self, dispatcher, mock_engine, game):
        game.state = GameState.REVOTE
        game.balance_players = [2, 3]

        query = PreVoteQuery(QueryType.PRE_VOTE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert len(response.candidates) == len(game.balance_players)
        assert "№2" in str(response.candidates)
        assert "№3" in str(response.candidates)
        assert "№4" not in str(response.candidates)

    @pytest.mark.asyncio
    async def test_pre_vote_wrong_turn(self, dispatcher, mock_engine, game):
        game.voting_queue = deque([game.players[2]])

        query = PreVoteQuery(QueryType.PRE_VOTE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь голосовать" in response.text

    @pytest.mark.asyncio
    async def test_pre_vote_no_game(self, dispatcher, mock_engine):
        query = PreVoteQuery(QueryType.PRE_VOTE, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_pre_vote(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.BALANCE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_pre_vote_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = PreVoteQuery(QueryType.PRE_VOTE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_vote(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_vote_success(self, dispatcher, mock_engine, game):
        target_number = 3

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), target_number)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.finish_voting", new_callable=AsyncMock
        ) as mock_finish:
            await dispatcher._handle_vote(query)

            assert game.current_votes[target_number] == 1
            assert game.vote_history[1] == target_number
            assert len(game.voting_queue) == 4

            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert isinstance(response, ResponseWithAlert)
            assert response.is_valid is True
            assert (
                f"Игрок №1 проголосовал против Игрока №{target_number}" in response.text
            )

            mock_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_vote_last_voter_calls_finish(self, dispatcher, mock_engine, game):
        game.voting_queue = deque([game.players[1]])

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.finish_voting", new_callable=AsyncMock
        ) as mock_finish:
            await dispatcher._handle_vote(query)

            assert len(game.voting_queue) == 0

            mock_finish.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_vote_sends_next_message(self, dispatcher, mock_engine, game):
        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        with patch("engine.dispatcher.finish_voting", new_callable=AsyncMock):
            await dispatcher._handle_vote(query)

            assert dispatcher.bus.emit.call_count >= 2

            next_message = dispatcher.bus.emit.call_args_list[1][0][0]
            assert "Следующий голосует" in next_message.text
            assert f"№{game.voting_queue[0].number}" in next_message.text

    @pytest.mark.asyncio
    async def test_vote_revote_state(self, dispatcher, mock_engine, game):
        game.state = GameState.REVOTE
        game.balance_players = [2, 3, 4]
        game.current_votes = {2: 0, 3: 0, 4: 0}

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        assert game.current_votes[3] == 1

    @pytest.mark.asyncio
    async def test_vote_wrong_turn(self, dispatcher, mock_engine, game):
        game.voting_queue = deque([game.players[2]])

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text
        assert game.current_votes[3] == 0

    @pytest.mark.asyncio
    async def test_vote_invalid_target(self, dispatcher, mock_engine, game):
        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 5)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "нельзя голосовать" in response.text
        assert game.current_votes.get(5, 0) == 0

    @pytest.mark.asyncio
    async def test_vote_no_game(self, dispatcher, mock_engine):
        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Голосование сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.BALANCE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_vote_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Голосование сейчас не идет" in response.text

    @pytest.mark.asyncio
    async def test_vote_no_voting_queue(self, dispatcher, mock_engine, game):
        game.voting_queue = None

        query = VoteQuery(QueryType.VOTE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text

    @pytest.mark.asyncio
    async def test_vote_player_not_found(self, dispatcher, mock_engine, game):
        query = VoteQuery(QueryType.VOTE, [1], -100, 99, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_vote(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text
