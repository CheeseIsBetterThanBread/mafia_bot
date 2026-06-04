import pytest
from unittest.mock import AsyncMock, Mock, patch
from types import SimpleNamespace

from vkbottle import GroupEventType
from vkbottle.bot import Message, MessageEvent
from vkbottle.dispatch.rules.base import CommandRule, PayloadRule, FuncRule

from adapters.vk.handlers import (
    setup_labeler,
    user_name_cache,
    EventBus,
    QueryType,
    NightAction,
)


class MockMessage:
    def __init__(self, peer_id, from_id, text="", chat_id=None, ctx_api=None):
        self.peer_id = peer_id
        self.from_id = from_id
        self.text = text
        self.chat_id = chat_id
        self.ctx_api = ctx_api or AsyncMock()
        self.answer = AsyncMock()


class MockMessageEvent:
    def __init__(self, peer_id, user_id, payload, ctx_api=None):
        self.object = SimpleNamespace()
        self.object.peer_id = peer_id
        self.object.user_id = user_id
        self.object.payload = payload
        self.ctx_api = ctx_api or AsyncMock()
        self.show_snackbar = AsyncMock()


class MockBotLabeler:
    def __init__(self):
        self.bus = None
        self.message_handlers = []
        self.raw_event_handlers = []
        self.func_rules = []

    def message(self, *rules):
        def decorator(func):
            self.message_handlers.append((rules, func))
            return func

        return decorator

    def raw_event(self, event_type, event_class):
        def decorator(func):
            self.raw_event_handlers.append((event_type, event_class, func))
            return func

        return decorator


@pytest.fixture
def mock_bus():
    bus = Mock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_user_cache():
    with patch("adapters.vk.handlers.user_name_cache") as mock:
        mock.get_user_name = AsyncMock(return_value="Test User")
        yield mock


@pytest.fixture
def labeler_with_handlers(mock_bus):
    with patch("adapters.vk.handlers.BotLabeler", MockBotLabeler):
        labeler = setup_labeler(mock_bus)
        return labeler, mock_bus


class TestSetupLabelerStructure:
    def test_setup_labeler_returns_labeler(self, mock_bus):
        with patch("adapters.vk.handlers.BotLabeler") as MockLabeler:
            mock_labeler = Mock()
            MockLabeler.return_value = mock_labeler
            result = setup_labeler(mock_bus)
            assert result == mock_labeler

    def test_message_handlers_registered(self, mock_bus):
        with patch("adapters.vk.handlers.BotLabeler", MockBotLabeler):
            labeler = setup_labeler(mock_bus)

            expected_commands = [
                "start",
                "help",
                "start_game",
                "run",
                "terminate",
                "alive",
                "description",
                "roles",
                "nominated",
                "voted",
                "status",
                "speech",
                "end_speech",
                "nominate",
                "vote",
                "balance",
                "start_night",
                "skip_night",
            ]

            registered_commands = []
            for rules, _ in labeler.message_handlers:
                for rule in rules:
                    if isinstance(rule, CommandRule):
                        registered_commands.append(rule.command_text)

            for cmd in expected_commands:
                assert cmd in registered_commands, f"Command {cmd} not registered"

    def test_callback_handlers_registered(self, mock_bus):
        with patch("adapters.vk.handlers.BotLabeler", MockBotLabeler):
            labeler = setup_labeler(mock_bus)
            assert len(labeler.raw_event_handlers) == 1

    def test_mafia_chat_handler_registered(self, mock_bus):
        with patch("adapters.vk.handlers.BotLabeler", MockBotLabeler):
            labeler = setup_labeler(mock_bus)

            func_rules_found = False
            for rules, _ in labeler.message_handlers:
                for rule in rules:
                    if isinstance(rule, FuncRule):
                        func_rules_found = True
                        break

            assert func_rules_found, "FuncRule for mafia chat not registered"


class TestStartCommand:
    @pytest.mark.asyncio
    async def test_start_command_private_chat(
        self, labeler_with_handlers, mock_user_cache
    ):
        labeler, mock_bus = labeler_with_handlers

        start_handler = None
        for rules, handler in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and "start" == rule.command_text:
                    start_handler = handler
                    break

        assert start_handler is not None

        message = MockMessage(peer_id=123, from_id=123, ctx_api=AsyncMock())

        assert start_handler
        await start_handler(message)

        mock_user_cache.get_user_name.assert_called_once_with(message.ctx_api, 123)

        message.answer.assert_called_once()
        answer_text = message.answer.call_args[0][0]
        assert "Привет! Я бот для Мафии" in answer_text
        assert "Ваш ID: 123" in answer_text
        assert "Ваше имя: Test User" in answer_text

    @pytest.mark.asyncio
    async def test_start_command_group_chat(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        start_handler = None
        for rules, handler in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and "start" == rule.command_text:
                    start_handler = handler
                    break

        message = MockMessage(peer_id=456, from_id=123, chat_id=456)

        assert start_handler
        await start_handler(message)

        message.answer.assert_not_called()


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_help_command(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        help_handler = None
        for rules, handler in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and "help" == rule.command_text:
                    help_handler = handler
                    break

        assert help_handler is not None

        message = MockMessage(peer_id=123, from_id=123)
        await help_handler(message)

        message.answer.assert_called_once()
        assert message.answer.call_args[1]["parse_mode"] == "html"


class TestGameControlCommands:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command,expected_type,chat_type",
        [
            ("start_game", QueryType.START_GAME, "group_chat"),
            ("run", QueryType.RUN, None),
            ("terminate", QueryType.TERMINATE, None),
            ("start_night", QueryType.START_NIGHT, None),
            ("skip_night", QueryType.SKIP_NIGHT, None),
        ],
    )
    async def test_game_control_commands(
        self, labeler_with_handlers, command, expected_type, chat_type
    ):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and command == rule.command_text:
                    handler = h
                    break

        assert handler is not None, f"Handler for {command} not found"

        message = MockMessage(peer_id=456, from_id=123, chat_id=456)

        await handler(message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == expected_type
        assert query.chat_id == 456
        assert query.user_id == 123

        if chat_type:
            assert query.chat_type == chat_type


class TestInfoCommands:
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
    async def test_info_commands(self, labeler_with_handlers, command, expected_type):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and command == rule.command_text:
                    handler = h
                    break

        assert handler is not None, f"Handler for {command} not found"

        message = MockMessage(peer_id=456, from_id=123)
        await handler(message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == expected_type


class TestSpeechCommands:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command,expected_type",
        [
            ("speech", QueryType.SPEECH),
            ("end_speech", QueryType.END_SPEECH),
        ],
    )
    async def test_speech_commands(self, labeler_with_handlers, command, expected_type):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and command == rule.command_text:
                    handler = h
                    break

        assert handler is not None

        message = MockMessage(peer_id=456, from_id=123)
        await handler(message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == expected_type


class TestPreActionCommands:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command,expected_type",
        [
            ("nominate", QueryType.PRE_NOMINATE),
            ("vote", QueryType.PRE_VOTE),
            ("balance", QueryType.PRE_BALANCE),
        ],
    )
    async def test_pre_action_commands(
        self, labeler_with_handlers, command, expected_type
    ):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, CommandRule) and command == rule.command_text:
                    handler = h
                    break

        assert handler is not None

        message = MockMessage(peer_id=456, from_id=123)
        await handler(message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == expected_type


class TestCallbackHandlers:
    @pytest.mark.asyncio
    async def test_join_game_callback(self, labeler_with_handlers, mock_user_cache):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for event_type, event_class, h in labeler.raw_event_handlers:
            handler = h
            break

        assert handler is not None

        event = MockMessageEvent(
            peer_id=456, user_id=123, payload={"type": "join_game"}
        )
        await handler(event)

        mock_user_cache.get_user_name.assert_called_once_with(event.ctx_api, 123)
        mock_bus.emit.assert_called_once()

        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == QueryType.JOIN_GAME
        assert query.chat_id == 456
        assert query.user_id == 123
        assert query.callback == event
        assert query.username == "Test User"

    @pytest.mark.asyncio
    async def test_nominate_callback(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        with patch("adapters.vk.handlers.TemplateParser") as MockParser:
            mock_parser = Mock()
            mock_parser.parse.return_value = {"chat_id": 456, "player_number": 42}
            MockParser.return_value = mock_parser

            handler = None
            for event_type, event_class, h in labeler.raw_event_handlers:
                handler = h
                break

            assert handler is not None

            event = MockMessageEvent(
                peer_id=456,
                user_id=123,
                payload={"type": "nominate", "data": "nominate_data"},
            )
            await handler(event)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]
            assert query.cmd == QueryType.NOMINATE
            assert query.chat_id == 456
            assert query.user_id == 123
            assert query.target_id == 42

    @pytest.mark.asyncio
    async def test_vote_callback(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        with patch("adapters.vk.handlers.TemplateParser") as MockParser:
            mock_parser = Mock()
            mock_parser.parse.return_value = {"chat_id": 456, "player_number": 7}
            MockParser.return_value = mock_parser

            handler = None
            for event_type, event_class, h in labeler.raw_event_handlers:
                handler = h
                break

            assert handler is not None

            event = MockMessageEvent(
                peer_id=456, user_id=123, payload={"type": "vote", "data": "vote_data"}
            )
            await handler(event)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]
            assert query.cmd == QueryType.VOTE
            assert query.target_id == 7

    @pytest.mark.asyncio
    async def test_balance_callback(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        with patch("adapters.vk.handlers.TemplateParser") as MockParser:
            mock_parser = Mock()
            mock_parser.parse.return_value = {"chat_id": 456, "number": 3}
            MockParser.return_value = mock_parser

            handler = None
            for event_type, event_class, h in labeler.raw_event_handlers:
                handler = h
                break

            assert handler is not None

            event = MockMessageEvent(
                peer_id=456,
                user_id=123,
                payload={"type": "balance", "data": "balance_data"},
            )
            await handler(event)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]
            assert query.cmd == QueryType.BALANCE
            assert query.target_id == 3

    @pytest.mark.asyncio
    async def test_night_action_callback(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        with patch("adapters.vk.handlers.TemplateParser") as MockParser:
            mock_parser = Mock()
            mock_parser.parse.return_value = {
                "chat_id": 456,
                "action": "vote",
                "target": 42,
            }
            MockParser.return_value = mock_parser

            handler = None
            for event_type, event_class, h in labeler.raw_event_handlers:
                handler = h
                break

            assert handler is not None

            event = MockMessageEvent(
                peer_id=456,
                user_id=123,
                payload={"type": "night_action", "data": "night_data"},
            )
            await handler(event)

            mock_bus.emit.assert_called_once()
            query = mock_bus.emit.call_args[0][0]
            assert query.cmd == QueryType.NIGHT_ACTION
            assert query.action == NightAction.VOTE
            assert query.target == 42


class TestMafiaChat:
    @pytest.mark.asyncio
    async def test_mafia_chat_valid_message(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, FuncRule):
                    handler = h
                    break

        assert handler is not None

        message = MockMessage(peer_id=123, from_id=123, text="Hello from mafia")
        await handler(message)

        mock_bus.emit.assert_called_once()
        query = mock_bus.emit.call_args[0][0]
        assert query.cmd == QueryType.MAFIA_CHAT
        assert query.text == "Hello from mafia"

    @pytest.mark.asyncio
    async def test_mafia_chat_ignores_commands(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, FuncRule):
                    handler = h
                    break

        message = MockMessage(peer_id=123, from_id=123, text="/start")
        await handler(message)

        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_mafia_chat_ignores_empty(self, labeler_with_handlers):
        labeler, mock_bus = labeler_with_handlers

        handler = None
        for rules, h in labeler.message_handlers:
            for rule in rules:
                if isinstance(rule, FuncRule):
                    handler = h
                    break

        message = MockMessage(peer_id=123, from_id=123, text="")
        await handler(message)

        mock_bus.emit.assert_not_called()
