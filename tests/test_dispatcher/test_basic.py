import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *

class TestEventDispatcher:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
        return engine

    @pytest.fixture
    def dispatcher(self, mock_engine):
        return EventDispatcher(mock_engine)

    @pytest.mark.asyncio
    async def test_handle_invalid_query_type(self, dispatcher):
        class InvalidQuery:
            pass

        query = InvalidQuery()

        with pytest.raises(ValueError, match="has to be a subclass of QueryBase"):
            await dispatcher.handle(query)

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, dispatcher):
        query = QueryBase("UNKNOWN", [], 0, 0)

        with pytest.raises(ValueError, match="Unknown query type: UNKNOWN"):
            await dispatcher.handle(query)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cmd_value,handler_name", [
        (QueryType.START_GAME, "_handle_start_game"),
        (QueryType.JOIN_GAME, "_handle_join_game"),
        (QueryType.RUN, "_handle_run"),
        (QueryType.ALIVE, "_handle_alive"),
        (QueryType.DESCRIPTION, "_handle_description"),
        (QueryType.ROLES, "_handle_roles"),
        (QueryType.NOMINATED, "_handle_nominated"),
        (QueryType.VOTED, "_handle_voted"),
        (QueryType.STATUS, "_handle_status"),
        (QueryType.SPEECH, "_handle_speech"),
        (QueryType.END_SPEECH, "_handle_end_speech"),
        (QueryType.PRE_NOMINATE, "_handle_pre_nominate"),
        (QueryType.NOMINATE, "_handle_nominate"),
        (QueryType.PRE_VOTE, "_handle_pre_vote"),
        (QueryType.VOTE, "_handle_vote"),
        (QueryType.PRE_BALANCE, "_handle_pre_balance"),
        (QueryType.BALANCE, "_handle_balance"),
        (QueryType.START_NIGHT, "_handle_start_night"),
        (QueryType.SKIP_NIGHT, "_handle_skip_night"),
        (QueryType.MAFIA_CHAT, "_handle_mafia_chat"),
        (QueryType.NIGHT_ACTION, "_handle_night_action"),
    ])
    async def test_route_to_correct_handler(self, dispatcher, cmd_value, handler_name):
        query = QueryBase(cmd_value, [], 0, 0)

        with patch.object(dispatcher, handler_name, new_callable=AsyncMock) as mock_handler:
            await dispatcher.handle(query)
            mock_handler.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_block_non_admin(self, dispatcher):
        query = QueryBase("", [1, 2, 3], -100, 10)

        result = await dispatcher._EventDispatcher__not_admin(query)

        assert result is True
        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "только создателю игры" in response.text

    @pytest.mark.asyncio
    async def test_allow_admin(self, dispatcher):
        query = QueryBase("", [1, 2, 3], -100, 1)
        query.user_id = 1
        query.admin_ids = [1, 2, 3]

        result = await dispatcher._EventDispatcher__not_admin(query)

        assert result is False
        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_game_no_game(self, dispatcher):
        query = QueryBase("", [], -100, 0)
        dispatcher.engine.get_game.return_value = None

        result = await dispatcher._EventDispatcher__validate_game(query)

        assert result is None
        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_validate_game_wrong_state(self, dispatcher, state):
        query = QueryBase("", [], -100, 0)

        game = Mock(spec=Game)
        game.state = state
        dispatcher.engine.get_game.return_value = game

        result = await dispatcher._EventDispatcher__validate_game(query)

        assert result is None
        dispatcher.bus.emit.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [
        GameState.DAY,
        GameState.DEFENSE,
        GameState.VOTING,
        GameState.BALANCE,
        GameState.REVOTE,
        GameState.NIGHT_THIEF,
        GameState.NIGHT,
    ])
    async def test_validate_game_success(self, dispatcher, state):
        query = QueryBase("", [], -100, 0)

        game = Mock(spec=Game)
        game.state = state
        dispatcher.engine.get_game.return_value = game

        result = await dispatcher._EventDispatcher__validate_game(query)

        assert result == game
        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_response(self, dispatcher):
        response = Mock(spec=ResponseBase)

        await dispatcher._EventDispatcher__send_response(response)

        dispatcher.bus.emit.assert_called_once_with(response)

    @pytest.mark.asyncio
    async def test_send_response_base(self, dispatcher):
        with patch.object(dispatcher, '_EventDispatcher__send_response', new_callable=AsyncMock) as mock_send:
            await dispatcher._EventDispatcher__send_response_base(123, "Test", "HTML", True)

            mock_send.assert_called_once()
            response = mock_send.call_args[0][0]
            assert isinstance(response, ResponseBase)
            assert response.chat_id == 123
            assert response.text == "Test"
            assert response.parse_mode == "HTML"
            assert response.is_valid is True

    @pytest.mark.asyncio
    async def test_send_response_with_options(self, dispatcher):
        candidates = [("Option 1", "cb1"), ("Option 2", "cb2")]

        with patch.object(dispatcher, '_EventDispatcher__send_response', new_callable=AsyncMock) as mock_send:
            await dispatcher._EventDispatcher__send_response_with_options(candidates, 123, "Test", "HTML", True)

            mock_send.assert_called_once()
            response = mock_send.call_args[0][0]
            assert isinstance(response, ResponseWithOptions)
            assert response.candidates == candidates
            assert response.chat_id == 123
            assert response.text == "Test"
            assert response.parse_mode == "HTML"
            assert response.is_valid is True
