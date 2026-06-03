import json

import pytest
from unittest.mock import AsyncMock, Mock

from vkbottle import Bot, Keyboard

from adapters.vk.adapter import (
    create_inline_keyboard,
    format_text,
    EventBus,
    ResponseBase,
    ResponseWithAlert,
    ResponseWithOptions,
    VkAdapter,
    QueryType,
)


class TestFormatText:
    def test_no_parse_mode(self):
        text = "Simple text without formatting"
        result = format_text(text, None)
        assert result == text

    def test_markdown_bold(self):
        text = "This is **bold** text"
        result = format_text(text, "MarkdownV2")
        assert result == "This is <b>bold</b> text"

    def test_markdown_italic(self):
        text = "This is *italic* text"
        result = format_text(text, "MarkdownV2")
        assert result == "This is <i>italic</i> text"

    def test_markdown_underline(self):
        text = "This is __underlined__ text"
        result = format_text(text, "MarkdownV2")
        assert result == "This is <u>underlined</u> text"

    def test_markdown_strikethrough(self):
        text = "This is ~~strikethrough~~ text"
        result = format_text(text, "MarkdownV2")
        assert result == "This is <s>strikethrough</s> text"

    def test_markdown_code(self):
        text = "This is `code` text"
        result = format_text(text, "MarkdownV2")
        assert result == "This is <code>code</code> text"

    def test_markdown_link(self):
        text = "Click [here](https://example.com)"
        result = format_text(text, "MarkdownV2")
        assert result == 'Click <a href="https://example.com">here</a>'

    def test_markdown_combined(self):
        text = "**Bold** and *italic* and `code`"
        result = format_text(text, "MarkdownV2")
        assert result == "<b>Bold</b> and <i>italic</i> and <code>code</code>"

    def test_other_parse_mode(self):
        text = "Some **text**"
        result = format_text(text, "HTML")
        assert result == text


class TestCreateInlineKeyboard:
    @pytest.mark.parametrize(
        "cmd, expected_type",
        [
            (QueryType.START_GAME, "join_game"),
            (QueryType.PRE_NOMINATE, "nominate"),
            (QueryType.PRE_VOTE, "vote"),
            (QueryType.PRE_BALANCE, "balance"),
            (QueryType.NIGHT_ACTION, "night_action"),
        ],
    )
    def test_vk_valid_commands(self, cmd, expected_type):
        candidates = [("Button 1", "data1"), ("Button 2", "data2")]
        keyboard = create_inline_keyboard(candidates, cmd)

        assert keyboard is not None
        assert isinstance(keyboard, Keyboard)

        assert keyboard.inline is True

        keyboard_json = keyboard.get_json()
        keyboard_dict = json.loads(keyboard_json)
        assert "buttons" in keyboard_dict
        assert len(keyboard_dict["buttons"]) == 2

        for i, (text, callback_data) in enumerate(candidates):
            button = keyboard_dict["buttons"][i][0]
            assert button["action"]["type"] == "callback"
            assert button["action"]["label"] == text
            assert button["action"]["payload"]["type"] == expected_type
            assert button["action"]["payload"]["data"] == callback_data

    def test_vk_empty_candidates(self):
        result = create_inline_keyboard([], QueryType.START_GAME)
        assert result is None

    def test_vk_unknown_command(self):
        candidates = [("Button", "data")]
        result = create_inline_keyboard(candidates, "UNKNOWN")
        assert result is None


class TestVkAdapter:
    @pytest.fixture
    def mock_bot(self):
        bot = Mock(spec=Bot)
        bot.api = Mock()
        bot.api.messages = AsyncMock()
        bot.api.messages.send = AsyncMock()
        bot.api.messages.edit = AsyncMock()
        return bot

    @pytest.fixture
    def mock_bus(self):
        bus = Mock(spec=EventBus)
        bus.on = Mock(return_value=lambda func: func)
        return bus

    @pytest.fixture
    def adapter(self, mock_bot, mock_bus):
        return VkAdapter(mock_bot, mock_bus)

    def test_init(self, mock_bot, mock_bus):
        adapter = VkAdapter(mock_bot, mock_bus)
        assert adapter.bot == mock_bot
        assert adapter.bus == mock_bus
        assert mock_bus.on.call_count == 3

    def test_vk_register_sets_handlers(self, mock_bot, mock_bus):
        VkAdapter(mock_bot, mock_bus)

        assert mock_bus.on.call_count == 3

        called_types = []
        for args, kwargs in mock_bus.on.call_args_list:
            called_types.append(args[0])

        assert ResponseBase in called_types
        assert ResponseWithAlert in called_types
        assert ResponseWithOptions in called_types

    @pytest.mark.asyncio
    async def test_vk_base_handler_sends_message(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        VkAdapter(mock_bot, mock_bus)

        response = ResponseBase(
            chat_id=123456789, text="Test message", parse_mode="HTML"
        )
        await handlers[ResponseBase](response)

        mock_bot.api.messages.send.assert_called_once_with(
            peer_id=123456789, message="Test message", random_id=0
        )

    @pytest.mark.asyncio
    async def test_vk_alert_handler_valid_response_edits_message(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        VkAdapter(mock_bot, mock_bus)

        mock_callback = Mock()
        mock_callback.peer_id = 123
        mock_callback.conversation_message_id = 456

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=True,
            text="Updated message",
            callback=mock_callback,
            parse_mode="HTML",
        )
        await handlers[ResponseWithAlert](response)

        mock_bot.api.messages.edit.assert_called_once_with(
            peer_id=123,
            message_id=456,
            message="Updated message",
            random_id=0,
        )
        mock_callback.show_snackbar.assert_not_called()

    @pytest.mark.asyncio
    async def test_vk_alert_handler_invalid_response_shows_alert(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        VkAdapter(mock_bot, mock_bus)

        mock_callback = Mock()
        mock_callback.peer_id = 123
        mock_callback.conversation_message_id = 456
        mock_callback.show_snackbar = AsyncMock()

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=False,
            text="Updated message",
            callback=mock_callback,
            parse_mode="HTML",
        )
        await handlers[ResponseWithAlert](response)

        mock_bot.api.messages.edit.assert_not_called()
        mock_callback.show_snackbar.assert_called_once_with("Updated message")

    @pytest.mark.asyncio
    async def test_vk_options_handler_creates_keyboard(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        VkAdapter(mock_bot, mock_bus)

        candidates = [
            ("Option 1", "callback_1"),
            ("Option 2", "callback_2"),
            ("Option 3", "callback_3"),
        ]

        response = ResponseWithOptions(
            chat_id=123456789,
            text="Choose option:",
            candidates=candidates,
            parse_mode="HTML",
            cmd=QueryType.NIGHT_ACTION,
        )
        await handlers[ResponseWithOptions](response)

        mock_bot.api.messages.send.assert_called_once()
        call_args = mock_bot.api.messages.send.call_args

        kwargs = call_args[1]
        assert kwargs["peer_id"] == 123456789
        assert kwargs["message"] == "Choose option:"
        assert kwargs["random_id"] == 0

        keyboard_json = kwargs["keyboard"]
        keyboard_dict = json.loads(keyboard_json)
        assert "buttons" in keyboard_dict
        assert len(keyboard_dict["buttons"]) == len(candidates)

        for i, (text, callback_data) in enumerate(candidates):
            button = keyboard_dict["buttons"][i][0]
            assert button["action"]["type"] == "callback"
            assert button["action"]["label"] == text
            assert button["action"]["payload"]["type"] == "night_action"
            assert button["action"]["payload"]["data"] == callback_data

    @pytest.mark.asyncio
    async def test_vk_options_handler_empty_candidates(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        VkAdapter(mock_bot, mock_bus)

        response = ResponseWithOptions(
            chat_id=123456789,
            text="Choose option:",
            candidates=[],
            parse_mode="HTML",
            cmd=QueryType.NIGHT_ACTION,
        )
        await handlers[ResponseWithOptions](response)

        mock_bot.api.messages.send.assert_called_once()
        call_args = mock_bot.api.messages.send.call_args

        kwargs = call_args[1]
        assert kwargs["peer_id"] == 123456789
        assert kwargs["message"] == "Choose option:"
        assert kwargs["random_id"] == 0
        assert kwargs["keyboard"] is None
