import pytest
from unittest.mock import AsyncMock
from connection.middleware import logging_middleware, error_middleware


class MockEvent:
    def __init__(self, log_string="test_event"):
        self._log_string = log_string

    def get_log_string(self):
        return self._log_string


class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logging_middleware_logs_start_and_end(self, caplog):
        event = MockEvent("user_123_action")
        next_handler = AsyncMock()

        with caplog.at_level('DEBUG'):
            await logging_middleware(event, next_handler)

        next_handler.assert_awaited_once_with(event)

        assert len(caplog.records) == 2
        assert "[START] user_123_action" in caplog.text
        assert "[END] user_123_action" in caplog.text

    @pytest.mark.asyncio
    async def test_logging_middleware_calls_next_handler(self):
        event = MockEvent("test")
        next_handler = AsyncMock()

        await logging_middleware(event, next_handler)

        next_handler.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_logging_middleware_with_different_log_strings(self, caplog):
        test_cases = [
            "api_call",
            "database_query",
            "file_upload",
        ]

        for log_string in test_cases:
            event = MockEvent(log_string)
            next_handler = AsyncMock()

            with caplog.at_level('DEBUG'):
                await logging_middleware(event, next_handler)

            next_handler.assert_awaited_once_with(event)

            assert len(caplog.records) == 2
            assert f"[START] {log_string}" in caplog.text
            assert f"[END] {log_string}" in caplog.text

            caplog.clear()

    @pytest.mark.asyncio
    async def test_logging_middleware_preserves_exception(self):
        event = MockEvent("test")
        next_handler = AsyncMock(side_effect=ValueError("Test error"))

        with pytest.raises(ValueError, match="Test error"):
            await logging_middleware(event, next_handler)

    @pytest.mark.asyncio
    async def test_logging_middleware_called_without_await(self):
        event = MockEvent("test")
        next_handler = AsyncMock()

        result = logging_middleware(event, next_handler)
        assert hasattr(result, '__await__')


class TestErrorMiddleware:
    @pytest.mark.asyncio
    async def test_error_middleware_passes_successful_call(self, caplog):
        event = MockEvent("successful")
        next_handler = AsyncMock()


        with caplog.at_level('ERROR'):
            await error_middleware(event, next_handler)

        assert len(caplog.records) == 0

    @pytest.mark.asyncio
    async def test_error_middleware_catches_and_logs_exception(self, caplog):
        event = MockEvent("error_event")
        test_error = ValueError("Database connection failed")
        next_handler = AsyncMock(side_effect=test_error)

        with caplog.at_level('ERROR'):
            await error_middleware(event, next_handler)

        next_handler.assert_awaited_once_with(event)

        assert len(caplog.records) == 1
        assert f"{event.get_log_string()} | {test_error}" in caplog.text

    @pytest.mark.asyncio
    async def test_error_middleware_with_different_exceptions(self, caplog):
        exceptions = [
            (ValueError("Invalid input"), "Invalid input"),
            (TypeError("Wrong type"), "Wrong type"),
            (RuntimeError("Runtime error"), "Runtime error"),
            (KeyError("missing_key"), "'missing_key'"),
        ]

        for exception, _ in exceptions:
            event = MockEvent("test_event")
            next_handler = AsyncMock(side_effect=exception)

            with caplog.at_level('ERROR'):
                await error_middleware(event, next_handler)

            next_handler.assert_awaited_once_with(event)

            assert len(caplog.records) == 1
            assert f"{event.get_log_string()} | {exception}" in caplog.text

            caplog.clear()

    @pytest.mark.asyncio
    async def test_error_middleware_with_different_log_strings(self, caplog):
        test_cases = [
            (MockEvent("api_call"), Exception("Network error")),
            (MockEvent("db_query"), Exception("Connection timeout")),
            (MockEvent("file_operation"), Exception("Permission denied")),
        ]

        for event, exception in test_cases:
            next_handler = AsyncMock(side_effect=exception)

            with caplog.at_level('ERROR'):
                await error_middleware(event, next_handler)

            next_handler.assert_awaited_once_with(event)

            assert len(caplog.records) == 1
            assert f"{event.get_log_string()} | {exception}" in caplog.text

            caplog.clear()

    @pytest.mark.asyncio
    async def test_error_middleware_preserves_not_raise_after_catch(self):
        event = MockEvent("test")
        next_handler = AsyncMock(side_effect=RuntimeError("Test"))

        await error_middleware(event, next_handler)

    @pytest.mark.asyncio
    async def test_error_middleware_multiple_calls(self, caplog):
        event = MockEvent("test")

        with caplog.at_level('ERROR'):
            await error_middleware(event, AsyncMock())

        error_handler = AsyncMock(side_effect=ValueError("Error"))
        with caplog.at_level('ERROR'):
            await error_middleware(event, error_handler)

        assert len(caplog.records) == 1


class TestMiddlewareChain:
    @pytest.mark.asyncio
    async def test_both_middlewares_work_together(self, caplog):
        event = MockEvent("chain_test")
        handler = AsyncMock()

        async def chain(e, h):
            await logging_middleware(e, lambda e_: error_middleware(e_, h))

        with caplog.at_level('ERROR'):
            await chain(event, handler)
        assert len(caplog.records) == 0

        with caplog.at_level('DEBUG'):
            await chain(event, handler)
        assert len(caplog.records) == 2

    @pytest.mark.asyncio
    async def test_both_middlewares_with_error(self, caplog):
        event = MockEvent("error_chain")
        error = ValueError("Chain error")
        handler = AsyncMock(side_effect=error)

        async def chain(e, h):
            await logging_middleware(e, lambda e_: error_middleware(e_, h))

        with caplog.at_level('DEBUG'):
            await chain(event, handler)
        assert f"[START] {event.get_log_string()}" in caplog.text
        assert f"[END] {event.get_log_string()}" in caplog.text

        caplog.clear()

        with caplog.at_level('ERROR'):
            await chain(event, handler)
        assert f"{event.get_log_string()} | {error}" in caplog.text
