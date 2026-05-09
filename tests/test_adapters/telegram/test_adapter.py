import pytest
from unittest.mock import AsyncMock, Mock

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, CallbackQuery
from aiogram.client.default import Default

from adapters.telegram.adapter import TelegramAdapter, get_parse_mode
from connection.events import (
    ResponseBase,
    ResponseWithAlert,
    ResponseWithOptions
)
from connection.event_bus import EventBus


class TestGetParseMode:
    def test_get_parse_mode_with_mode(self):
        result = get_parse_mode("HTML")
        assert result == "HTML"

    def test_get_parse_mode_with_none(self):
        from aiogram.client.default import Default
        result = get_parse_mode(None)
        assert isinstance(result, Default)

    def test_get_parse_mode_with_empty_string(self):
        result = get_parse_mode("")
        assert result == ""


@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def mock_bus():
    bus = Mock(spec=EventBus)
    bus.on = Mock(return_value=lambda x: x)
    return bus

@pytest.fixture
def mock_callback():
    callback = AsyncMock(spec=CallbackQuery)
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.reply_markup = None
    callback.answer = AsyncMock()
    return callback

@pytest.fixture
def adapter(mock_bot, mock_bus):
    return TelegramAdapter(mock_bot, mock_bus)


class TestTelegramAdapter:
    def test_adapter_initialization(self, mock_bot, mock_bus):
        adapter = TelegramAdapter(mock_bot, mock_bus)

        assert adapter.bot == mock_bot
        assert adapter.bus == mock_bus

    def test_register_sets_handlers(self, mock_bot, mock_bus):
        TelegramAdapter(mock_bot, mock_bus)

        assert mock_bus.on.call_count == 3

        called_types = []
        for args, kwargs in mock_bus.on.call_args_list:
            called_types.append(args[0])

        assert ResponseBase in called_types
        assert ResponseWithAlert in called_types
        assert ResponseWithOptions in called_types

    @pytest.mark.asyncio
    async def test_base_handler_sends_message(self, adapter, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseBase(
            chat_id=123456789,
            text="Test message",
            parse_mode="HTML"
        )
        await handlers[ResponseBase](response)

        mock_bot.send_message.assert_called_once_with(
            123456789,
            "Test message",
            parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_base_handler_without_parse_mode(self, adapter, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseBase(
            chat_id=123456789,
            text="Test message",
            parse_mode=None
        )
        await handlers[ResponseBase](response)

        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args[1]
        assert isinstance(call_args['parse_mode'], Default)

    @pytest.mark.asyncio
    async def test_alert_handler_valid_response_edits_message(self, mock_bot, mock_callback):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=True,
            text="Updated message",
            callback=mock_callback,
            parse_mode="HTML"
        )
        response.is_valid = Mock(return_value=True)
        await handlers[ResponseWithAlert](response)

        mock_callback.message.edit_text.assert_called_once_with(
            "Updated message",
            reply_markup=mock_callback.message.reply_markup,
            parse_mode="HTML"
        )
        mock_callback.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_alert_handler_invalid_response_shows_alert(self, mock_bot, mock_callback):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=False,
            text="Error message",
            callback=mock_callback,
            parse_mode="HTML"
        )
        await handlers[ResponseWithAlert](response)

        mock_callback.answer.assert_called_once_with(
            "Error message",
            show_alert=True,
            parse_mode="HTML"
        )
        mock_callback.message.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_alert_handler_without_parse_mode(self, mock_bot, mock_callback):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=True,
            text="Message",
            callback=mock_callback,
            parse_mode=None
        )
        await handlers[ResponseWithAlert](response)

        call_args = mock_callback.message.edit_text.call_args
        assert isinstance(call_args[1]['parse_mode'], Default)

    @pytest.mark.asyncio
    async def test_options_handler_creates_keyboard(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        candidates = [
            ("Option 1", "callback_1"),
            ("Option 2", "callback_2"),
            ("Option 3", "callback_3"),
        ]

        response = ResponseWithOptions(
            chat_id=123456789,
            text="Choose option:",
            candidates=candidates,
            parse_mode="HTML"
        )
        await handlers[ResponseWithOptions](response)

        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args

        args = call_args[0]
        assert args[0] == 123456789  # chat_id
        assert args[1] == "Choose option:"  # text

        kwargs = call_args[1]
        reply_markup = kwargs['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)

        keyboard_buttons = reply_markup.inline_keyboard
        assert len(keyboard_buttons) == 3
        assert keyboard_buttons[0][0].text == "Option 1"
        assert keyboard_buttons[0][0].callback_data == "callback_1"
        assert keyboard_buttons[1][0].text == "Option 2"
        assert keyboard_buttons[1][0].callback_data == "callback_2"
        assert keyboard_buttons[2][0].text == "Option 3"
        assert keyboard_buttons[2][0].callback_data == "callback_3"

        assert kwargs['parse_mode'] == "HTML"

    @pytest.mark.asyncio
    async def test_options_handler_empty_candidates(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        response = ResponseWithOptions(
            chat_id=123456789,
            text="No options",
            candidates=[],
            parse_mode=None
        )
        await handlers[ResponseWithOptions](response)

        call_args = mock_bot.send_message.call_args
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert len(reply_markup.inline_keyboard) == 0

    @pytest.mark.asyncio
    async def test_options_handler_single_candidate(self, mock_bot):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        candidates = [("Only Option", "callback_only")]

        response = ResponseWithOptions(
            chat_id=123456789,
            text="Single option",
            candidates=candidates,
            parse_mode="Markdown"
        )
        await handlers[ResponseWithOptions](response)

        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        reply_markup = call_args[1]['reply_markup']

        assert len(reply_markup.inline_keyboard) == 1
        assert reply_markup.inline_keyboard[0][0].text == "Only Option"
        assert reply_markup.inline_keyboard[0][0].callback_data == "callback_only"
        assert call_args[1]['parse_mode'] == "Markdown"

    @pytest.mark.asyncio
    async def test_adapter_handles_all_event_types(self, mock_bot, mock_callback):
        mock_bus = Mock(spec=EventBus)
        handlers = {}

        def on_side_effect(event_type):
            def decorator(handler):
                handlers[event_type] = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect
        TelegramAdapter(mock_bot, mock_bus)

        assert len(handlers) == 3
        assert ResponseBase in handlers
        assert ResponseWithAlert in handlers
        assert ResponseWithOptions in handlers


class TestIntegrationWithEventBus:
    @pytest.fixture
    def real_bus(self):
        from connection.event_bus import EventBus
        return EventBus()

    @pytest.fixture
    def mock_bot(self):
        return AsyncMock(spec=Bot)

    @pytest.mark.asyncio
    async def test_adapter_registers_with_real_bus(self, mock_bot, real_bus):
        TelegramAdapter(mock_bot, real_bus)

        assert ResponseBase in real_bus.subscribers
        assert ResponseWithAlert in real_bus.subscribers
        assert ResponseWithOptions in real_bus.subscribers

        assert len(real_bus.subscribers[ResponseBase]) == 1
        assert len(real_bus.subscribers[ResponseWithAlert]) == 1
        assert len(real_bus.subscribers[ResponseWithOptions]) == 1

    @pytest.mark.asyncio
    async def test_end_to_end_response_flow(self, mock_bot, real_bus):
        adapter = TelegramAdapter(mock_bot, real_bus)

        response = ResponseBase(
            chat_id=123456789,
            text="End-to-end test",
            parse_mode="Markdown"
        )
        await adapter.bus.emit(response)

        mock_bot.send_message.assert_called_once_with(
            123456789,
            "End-to-end test",
            parse_mode="Markdown"
        )

    @pytest.mark.asyncio
    async def test_end_to_end_with_alert_response(self, mock_bot, real_bus, mock_callback):
        adapter = TelegramAdapter(mock_bot, real_bus)

        response = ResponseWithAlert(
            chat_id=123456789,
            valid=True,
            text="Alert message",
            callback=mock_callback,
            parse_mode="HTML"
        )
        await adapter.bus.emit(response)

        mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_adapters_on_same_bus(self, mock_bot, real_bus):
        mock_bot2 = AsyncMock(spec=Bot)

        TelegramAdapter(mock_bot, real_bus)
        TelegramAdapter(mock_bot2, real_bus)

        response = ResponseBase(chat_id=1, text="Test", parse_mode=None)
        await real_bus.emit(response)

        assert mock_bot.send_message.call_count == 1
        assert mock_bot2.send_message.call_count == 1
