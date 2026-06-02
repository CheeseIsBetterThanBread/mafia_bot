import pytest
from unittest.mock import Mock, AsyncMock, patch

from tests.conftest import capture_logger_output

from adapters.telegram.handlers import *


@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def setup_router(mock_bus):
    mock_router = setup_bus(mock_bus)
    return mock_router, mock_bus


@pytest.fixture
def mock_message():
    message = Mock(spec=Message)
    message.chat = Mock()
    message.chat.id = -100123456789
    message.chat.type = "group"
    message.from_user = Mock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    callback = Mock(spec=CallbackQuery)
    callback.message = Mock()
    callback.message.chat = Mock()
    callback.message.chat.id = -100123456789
    callback.from_user = Mock()
    callback.from_user.id = 123456789
    callback.from_user.username = "test_user"
    callback.answer = AsyncMock()
    callback.data = "some_data"
    return callback


class MockText:
    def __init__(self, value, startswith=False):
        self.value = value
        self._startswith = startswith

    def startswith(self, _):
        return self._startswith

    def __str__(self):
        return self.value


class TestTelegramHandlers:
    def test_setup_bus(self, mock_bus):
        result = setup_bus(mock_bus)
        from adapters.telegram.handlers import router as actual_router

        assert hasattr(actual_router, "bus")
        assert actual_router.bus == mock_bus
        assert result == actual_router

    @pytest.mark.asyncio
    async def test_cmd_start_private_chat(self, mock_message):
        mock_message.chat.type = "private"

        with capture_logger_output() as log_output:
            await cmd_start(mock_message)
            assert (
                f" {mock_message.from_user.id} - {mock_message.from_user.username} "
                in log_output.getvalue()
            )

        mock_message.answer.assert_called()
        assert mock_message.answer.call_count == 2

    @pytest.mark.asyncio
    async def test_cmd_start_group_chat(self, mock_message):
        mock_message.chat.type = "group"

        with capture_logger_output() as log_output:
            await cmd_start(mock_message)
            assert log_output.getvalue() == ""

        assert mock_message.answer.call_count == 0

    @pytest.mark.asyncio
    async def test_cmd_help(self, mock_message):
        await cmd_help(mock_message)

        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0]
        assert "Список команд бота" in str(args)

    @pytest.mark.asyncio
    async def test_cmd_start_game(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_start_game(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, StartGameQuery)
        assert query.cmd == QueryType.START_GAME
        assert query.chat_id == mock_message.chat.id
        assert query.user_id == mock_message.from_user.id

    @pytest.mark.asyncio
    async def test_handle_join_game(self, mock_callback, setup_router):
        router, mock_bus = setup_router
        mock_callback.data = "join_game"

        await handle_join_game(mock_callback)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, JoinQuery)
        assert query.cmd == QueryType.JOIN_GAME
        assert query.chat_id == mock_callback.message.chat.id
        assert query.user_id == mock_callback.from_user.id
        assert query.callback == mock_callback

    @pytest.mark.asyncio
    async def test_cmd_run(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_run(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, RunQuery)
        assert query.cmd == QueryType.RUN

    @pytest.mark.asyncio
    async def test_cmd_terminate(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_terminate(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, TerminateQuery)
        assert query.cmd == QueryType.TERMINATE

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command,expected_type",
        [
            ("alive", QueryType.ALIVE),
            ("description", QueryType.DESCRIPTION),
            ("roles", QueryType.ROLES),
            ("nominated", QueryType.NOMINATED),
            ("voted", QueryType.VOTED),
            ("status", QueryType.STATUS),
        ],
    )
    async def test_info_commands(
        self, mock_message, setup_router, command, expected_type
    ):
        router, mock_bus = setup_router

        commands_map = {
            "alive": cmd_alive,
            "description": cmd_description,
            "roles": cmd_roles,
            "nominated": cmd_nominated,
            "voted": cmd_voted,
            "status": cmd_status,
        }

        await commands_map[command](mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, InfoQuery)
        assert query.cmd == expected_type

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command,expected_type",
        [
            ("speech", QueryType.SPEECH),
            ("end_speech", QueryType.END_SPEECH),
        ],
    )
    async def test_speech_commands(
        self, mock_message, setup_router, command, expected_type
    ):
        router, mock_bus = setup_router

        commands_map = {
            "speech": cmd_speech,
            "end_speech": cmd_end_speech,
        }

        await commands_map[command](mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, SpeechRelatedQuery)
        assert query.cmd == expected_type

    @pytest.mark.asyncio
    async def test_cmd_nominate(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_nominate(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, PreNominateQuery)
        assert query.cmd == QueryType.PRE_NOMINATE

    @pytest.mark.asyncio
    async def test_handle_nominate(self, mock_callback, setup_router):
        router, mock_bus = setup_router

        chat_id = -100123456789
        player_number = 5
        mock_callback.data = NOMINATE_CALLBACK_TEMPLATE.format(
            chat_id=chat_id, player_number=player_number
        )

        with patch("adapters.telegram.handlers.TemplateParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.return_value = {
                "chat_id": chat_id,
                "player_number": player_number,
            }

            await handle_nominate(mock_callback)

            MockParser.assert_called_once_with(
                NOMINATE_CALLBACK_TEMPLATE, NOMINATE_TYPES
            )

            mock_parser.parse.assert_called_once_with(mock_callback.data)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]

            assert isinstance(query, NominateQuery)
            assert query.cmd == QueryType.NOMINATE
            assert query.target_id == player_number

    @pytest.mark.asyncio
    async def test_cmd_vote(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_vote(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, PreVoteQuery)
        assert query.cmd == QueryType.PRE_VOTE

    @pytest.mark.asyncio
    async def test_handle_vote(self, mock_callback, setup_router):
        router, mock_bus = setup_router

        chat_id = -100123456789
        player_number = 3
        mock_callback.data = VOTE_CALLBACK_TEMPLATE.format(
            chat_id=chat_id, player_number=player_number
        )

        with patch("adapters.telegram.handlers.TemplateParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.return_value = {
                "chat_id": chat_id,
                "player_number": player_number,
            }

            await handle_vote(mock_callback)

            MockParser.assert_called_once_with(VOTE_CALLBACK_TEMPLATE, VOTE_TYPES)

            mock_parser.parse.assert_called_once_with(mock_callback.data)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]

            assert isinstance(query, VoteQuery)
            assert query.cmd == QueryType.VOTE
            assert query.target_id == player_number

    @pytest.mark.asyncio
    async def test_cmd_balance(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_balance(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, PreBalanceQuery)
        assert query.cmd == QueryType.PRE_BALANCE

    @pytest.mark.asyncio
    async def test_handle_balance(self, mock_callback, setup_router):
        router, mock_bus = setup_router

        chat_id = -100123456789
        number = 2
        mock_callback.data = BALANCE_CALLBACK_TEMPLATE.format(
            chat_id=chat_id, number=number
        )

        with patch("adapters.telegram.handlers.TemplateParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.return_value = {"chat_id": chat_id, "number": number}

            await handle_balance(mock_callback)

            MockParser.assert_called_once_with(BALANCE_CALLBACK_TEMPLATE, BALANCE_TYPES)

            mock_parser.parse.assert_called_once_with(mock_callback.data)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]

            assert isinstance(query, BalanceQuery)
            assert query.cmd == QueryType.BALANCE
            assert query.target_id == number

    @pytest.mark.asyncio
    async def test_cmd_start_night(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_start_night(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, StartNightQuery)
        assert query.cmd == QueryType.START_NIGHT

    @pytest.mark.asyncio
    async def test_cmd_skip_night(self, mock_message, setup_router):
        router, mock_bus = setup_router

        await cmd_skip_night(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, SkipNightQuery)
        assert query.cmd == QueryType.SKIP_NIGHT

    @pytest.mark.asyncio
    async def test_handle_night_action(self, mock_callback, setup_router):
        router, mock_bus = setup_router

        chat_id = -100123456789
        action = NightAction.ROB
        target = 5
        mock_callback.data = NIGHT_CALLBACK_TEMPLATE.format(
            chat_id=chat_id, action=action, target=target
        )

        with patch("adapters.telegram.handlers.TemplateParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.return_value = {
                "chat_id": chat_id,
                "action": action,
                "target": target,
            }

            await handle_night_action(mock_callback)

            MockParser.assert_called_once_with(NIGHT_CALLBACK_TEMPLATE, NIGHT_TYPES)

            mock_parser.parse.assert_called_once_with(mock_callback.data)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]

            assert isinstance(query, NightActionQuery)
            assert query.cmd == QueryType.NIGHT_ACTION
            assert query.action == action
            assert query.target == target

    @pytest.mark.asyncio
    async def test_mafia_chat_valid_message(self, mock_message, setup_router):
        router, mock_bus = setup_router
        mock_message.chat.type = "private"
        mock_message.text = MockText("Hello from mafia")

        await mafia_chat(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]

        assert isinstance(query, MafiaChatQuery)
        assert query.cmd == QueryType.MAFIA_CHAT
        assert query.text == "Hello from mafia"

    @pytest.mark.asyncio
    async def test_mafia_chat_empty_message(self, mock_message, setup_router):
        router, mock_bus = setup_router
        mock_message.chat.type = "private"
        mock_message.text = None

        await mafia_chat(mock_message)

        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_mafia_chat_command(self, mock_message, setup_router):
        router, mock_bus = setup_router
        mock_message.chat.type = "private"
        mock_message.text = MockText("/start", True)

        await mafia_chat(mock_message)

        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_emit_raises_error(self):
        with pytest.raises(ValueError, match="Failed to connect to EventBus"):
            await fallback_bus.emit(None)

    @pytest.mark.asyncio
    async def test_router_without_bus(self, mock_message):
        from adapters.telegram.handlers import router as clean_router

        if hasattr(clean_router, "bus"):
            delattr(clean_router, "bus")

        with pytest.raises(ValueError, match="Failed to connect to EventBus"):
            await cmd_start_game(mock_message)

    @pytest.mark.asyncio
    async def test_full_workflow_start_game_to_join(
        self, setup_router, mock_message, mock_callback
    ):
        router, mock_bus = setup_router

        await cmd_start_game(mock_message)
        assert mock_bus.emit.call_count == 1
        start_query = mock_bus.emit.call_args[0][0]
        assert isinstance(start_query, StartGameQuery)

        mock_bus.emit.reset_mock()
        mock_callback.data = "join_game"
        await handle_join_game(mock_callback)

        assert mock_bus.emit.call_count == 1
        join_query = mock_bus.emit.call_args[0][0]
        assert isinstance(join_query, JoinQuery)


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_callback_with_malformed_data(self, mock_callback):
        mock_callback.data = "invalid_format"

        with patch("utils.parser.TemplateParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.side_effect = ValueError("Invalid data")

            with pytest.raises(TypeError):
                await handle_nominate(mock_callback)

            with pytest.raises(TypeError):
                await handle_vote(mock_callback)

            with pytest.raises(TypeError):
                await handle_balance(mock_callback)

            with pytest.raises(TypeError):
                await handle_night_action(mock_callback)

    @pytest.mark.asyncio
    async def test_mafia_chat_with_unicode(self, mock_message, setup_router):
        router, mock_bus = setup_router
        mock_message.chat.type = "private"
        mock_message.text = MockText("Привет, мафия! 🎭")

        await mafia_chat(mock_message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.text == "Привет, мафия! 🎭"
