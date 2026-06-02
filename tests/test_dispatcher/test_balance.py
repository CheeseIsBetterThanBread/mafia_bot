from collections import deque

import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *


class TestBalanceHandlers:
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
        game.state = GameState.BALANCE
        game.balance_players = [2, 3, 4]
        game.current_votes = {"acquit": 0, "kill": 0, "revote": 0}
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
        return game

    @pytest.mark.asyncio
    async def test_pre_balance_success(self, dispatcher, mock_engine, game):
        query = PreBalanceQuery(QueryType.PRE_BALANCE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_balance(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithOptions)
        assert "Ваш выбор на балансе?" in response.text
        assert len(response.candidates) == 3

        options_text = [opt[0] for opt in response.candidates]
        assert "🕊 Оправдать" in options_text
        assert "💀 Убить всех" in options_text
        assert "🔄 Переголосовать" in options_text

    @pytest.mark.asyncio
    async def test_pre_balance_wrong_turn(self, dispatcher, mock_engine, game):
        game.voting_queue = deque([game.players[2]])

        query = PreBalanceQuery(QueryType.PRE_BALANCE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text

    @pytest.mark.asyncio
    async def test_pre_balance_no_game(self, dispatcher, mock_engine):
        query = PreBalanceQuery(QueryType.PRE_BALANCE, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_pre_balance(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.VOTING,
            GameState.REVOTE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_pre_balance_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = PreBalanceQuery(QueryType.PRE_BALANCE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_balance(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_balance_no_voting_queue(self, dispatcher, mock_engine, game):
        game.voting_queue = None

        query = PreBalanceQuery(QueryType.PRE_BALANCE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text

    @pytest.mark.asyncio
    async def test_balance_acquit_success(self, dispatcher, mock_engine, game):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.resolve_balance", new_callable=AsyncMock
        ) as mock_resolve:
            await dispatcher._handle_balance(query)

            assert game.current_votes["acquit"] == 1
            assert game.vote_history[1] == "Оправдать"
            assert len(game.voting_queue) == 4

            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert isinstance(response, ResponseWithAlert)
            assert response.is_valid is True
            assert "Игрок №1 выбрал: Оправдать" in response.text

            mock_resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_balance_kill_success(self, dispatcher, mock_engine, game):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 2)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        assert game.current_votes["kill"] == 1
        assert game.vote_history[1] == "Убить всех"

    @pytest.mark.asyncio
    async def test_balance_revote_success(self, dispatcher, mock_engine, game):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        assert game.current_votes["revote"] == 1
        assert game.vote_history[1] == "Переголосовать"

    @pytest.mark.asyncio
    async def test_balance_last_voter_calls_resolve(
        self, dispatcher, mock_engine, game
    ):
        game.voting_queue = deque([game.players[1]])

        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.resolve_balance", new_callable=AsyncMock
        ) as mock_resolve:
            await dispatcher._handle_balance(query)

            assert len(game.voting_queue) == 0

            mock_resolve.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_balance_sends_next_message(self, dispatcher, mock_engine, game):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        with patch("engine.dispatcher.resolve_balance", new_callable=AsyncMock):
            await dispatcher._handle_balance(query)

            assert dispatcher.bus.emit.call_count >= 2

            next_message = dispatcher.bus.emit.call_args_list[1][0][0]
            assert "Следующий голосует" in next_message.text
            assert f"№{game.voting_queue[0].number}" in next_message.text
            assert "/balance" in next_message.text

    @pytest.mark.asyncio
    async def test_balance_wrong_turn(self, dispatcher, mock_engine, game):
        game.voting_queue = deque([game.players[2]])

        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text
        assert game.current_votes["acquit"] == 0

    @pytest.mark.asyncio
    async def test_balance_no_game(self, dispatcher, mock_engine):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Баланс не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.VOTING,
            GameState.REVOTE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_balance_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Баланс не идет" in response.text

    @pytest.mark.asyncio
    async def test_balance_no_voting_queue(self, dispatcher, mock_engine, game):
        game.voting_queue = None

        query = BalanceQuery(QueryType.BALANCE, [1], -100, 1, Mock(), 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text

    @pytest.mark.asyncio
    async def test_balance_player_not_found(self, dispatcher, mock_engine, game):
        query = BalanceQuery(QueryType.BALANCE, [1], -100, 99, Mock(), 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_balance(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь" in response.text
