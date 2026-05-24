import pytest
from unittest.mock import AsyncMock, Mock

from engine.dispatcher import *


class TestNominateHandlers:
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
        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
            game.players[i].has_nominated = False
        game.speech_queue = [game.players[1], game.players[2], game.players[3]]
        game.day_count = 2
        game.nominated = []
        return game

    @pytest.mark.asyncio
    async def test_pre_nominate_success(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [3], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithOptions)
        assert "Кого вы хотите выставить" in response.text
        assert len(response.candidates) == len(game.get_alive_players()) + 1

        cancel_option = response.candidates[-1]
        assert "Отмена" in cancel_option[0]
        assert str(NULL_OPTION) in cancel_option[1]

    @pytest.mark.asyncio
    async def test_pre_nominate_first_day(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.day_count = 1

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "первый день" in response.text.lower()
        assert "запрещено" in response.text

    @pytest.mark.asyncio
    async def test_pre_nominate_wrong_turn(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[2]]

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь говорить" in response.text

    @pytest.mark.asyncio
    async def test_pre_nominate_already_nominated(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.players[1].has_nominated = True

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Вы уже выставили одного кандидата" in response.text

    @pytest.mark.asyncio
    async def test_pre_nominate_no_game(self, dispatcher, mock_engine):
        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_pre_nominate(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [
        GameState.LOBBY,
        GameState.DEFENSE,
        GameState.VOTING,
        GameState.BALANCE,
        GameState.REVOTE,
        GameState.NIGHT_THIEF,
        GameState.NIGHT,
        GameState.FINISHED
    ])
    async def test_pre_nominate_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_nominate_no_speech_queue(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = None

        query = PreNominateQuery(QueryType.PRE_NOMINATE, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_pre_nominate(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_nominate_success(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        target_number = 3

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), target_number)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        assert target_number in game.nominated
        assert game.players[1].has_nominated is True

        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithAlert)
        assert response.is_valid is True
        assert f"Игрок №1 выставил Игрока №{target_number}" in response.text

    @pytest.mark.asyncio
    async def test_nominate_cancel(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), NULL_OPTION)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        assert game.nominated == []
        assert game.players[1].has_nominated is False

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Вы отменили выставление" in response.text

    @pytest.mark.asyncio
    async def test_nominate_wrong_turn(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[2]]

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Не лезь, сейчас не твоя очередь" in response.text
        assert 3 not in game.nominated

    @pytest.mark.asyncio
    async def test_nominate_already_nominated_player(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.nominated = [3]

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "уже выставлен на голосование" in response.text
        assert game.players[1].has_nominated is False

    @pytest.mark.asyncio
    async def test_nominate_dead_player(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.players[3].is_alive = False

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "уже покинул стол" in response.text

    @pytest.mark.asyncio
    async def test_nominate_speaker_already_nominated_this_round(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.players[1].has_nominated = True

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Вы уже выставили кандидата" in response.text

    @pytest.mark.asyncio
    async def test_nominate_no_game(self, dispatcher, mock_engine):
        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Действие недоступно" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [
        GameState.LOBBY,
        GameState.DEFENSE,
        GameState.VOTING,
        GameState.BALANCE,
        GameState.REVOTE,
        GameState.NIGHT_THIEF,
        GameState.NIGHT,
        GameState.FINISHED
    ])
    async def test_nominate_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Действие недоступно" in response.text

    @pytest.mark.asyncio
    async def test_nominate_no_speech_queue(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = None

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 3)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Действие недоступно" in response.text

    @pytest.mark.asyncio
    async def test_nominate_invalid_player(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY

        query = NominateQuery(QueryType.NOMINATE, [1], -100, 1, Mock(), 99)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominate(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "уже покинул стол" in response.text
