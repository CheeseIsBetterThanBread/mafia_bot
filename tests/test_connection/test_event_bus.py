import asyncio

import pytest
from unittest.mock import AsyncMock

from connection.event_bus import EventBus, prepare_bus

from tests.conftest import capture_logger_output


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def prepared_bus(self):
        return prepare_bus()

    class TestEvent:
        pass

    class AnotherEvent:
        pass

    class ChildEvent(TestEvent):
        pass

    def test_subscribe_method(self, bus):
        handler = AsyncMock()
        bus.subscribe(self.TestEvent, handler)

        assert handler in bus.subscribers[self.TestEvent]
        assert len(bus.subscribers[self.TestEvent]) == 1

    def test_on_decorator(self, bus):
        @bus.on(self.TestEvent)
        async def handler(_):
            pass

        assert handler in bus.subscribers[self.TestEvent]
        assert len(bus.subscribers[self.TestEvent]) == 1

    def test_multiple_subscribers(self, bus):
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(self.TestEvent, handler1)
        bus.subscribe(self.TestEvent, handler2)

        assert len(bus.subscribers[self.TestEvent]) == 2
        assert handler1 in bus.subscribers[self.TestEvent]
        assert handler2 in bus.subscribers[self.TestEvent]

    def test_different_event_types(self, bus):
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(self.TestEvent, handler1)
        bus.subscribe(self.AnotherEvent, handler2)

        assert handler1 in bus.subscribers[self.TestEvent]
        assert handler2 in bus.subscribers[self.AnotherEvent]
        assert len(bus.subscribers[self.TestEvent]) == 1
        assert len(bus.subscribers[self.AnotherEvent]) == 1

    @pytest.mark.asyncio
    async def test_emit_calls_handler(self, bus):
        handler = AsyncMock()
        bus.subscribe(self.TestEvent, handler)

        event = self.TestEvent()
        await bus.emit(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_emit_with_multiple_handlers(self, bus):
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        bus.subscribe(self.TestEvent, handler1)
        bus.subscribe(self.TestEvent, handler2)

        event = self.TestEvent()
        await bus.emit(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_emit_no_subscribers(self, bus):
        event = self.TestEvent()
        await bus.emit(event)

    @pytest.mark.asyncio
    async def test_emit_with_inheritance(self, bus):
        handler = AsyncMock()
        bus.subscribe(self.TestEvent, handler)

        event = self.ChildEvent()
        await bus.emit(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_emit_doesnt_call_unrelated_handlers(self, bus):
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(self.TestEvent, handler1)
        bus.subscribe(self.AnotherEvent, handler2)

        event = self.TestEvent()
        await bus.emit(event)

        handler1.assert_called_once()
        handler2.assert_not_called()

    @pytest.mark.asyncio
    async def test_emit_concurrent_execution(self, bus):
        event_handled = asyncio.Event()

        async def slow_handler(_):
            await asyncio.sleep(0.1)
            event_handled.set()

        async def fast_handler(_):
            pass

        bus.subscribe(self.TestEvent, slow_handler)
        bus.subscribe(self.TestEvent, fast_handler)

        event = self.TestEvent()
        await bus.emit(event)

        assert event_handled.is_set()

    @pytest.mark.asyncio
    async def test_emit_handles_exceptions(self, bus):
        called = asyncio.Event()

        async def failing_handler(_):
            raise ValueError("Test error")

        async def succeeding_handler(_):
            called.set()

        bus.subscribe(self.TestEvent, failing_handler)
        bus.subscribe(self.TestEvent, succeeding_handler)

        event = self.TestEvent()
        await bus.emit(event)

        assert called.is_set()

    @pytest.mark.asyncio
    async def test_emit_multiple_events(self, bus):
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(self.TestEvent, handler1)
        bus.subscribe(self.AnotherEvent, handler2)

        event1 = self.TestEvent()
        event2 = self.AnotherEvent()

        await bus.emit(event1)
        await bus.emit(event2)

        handler1.assert_called_once_with(event1)
        handler2.assert_called_once_with(event2)

    @pytest.mark.asyncio
    async def test_add_middleware(self, bus):
        middleware = AsyncMock()
        bus.add_middleware(middleware)

        assert len(bus.middlewares) == 1
        assert bus.middlewares[0] == middleware

    @pytest.mark.asyncio
    async def test_middleware_execution_order(self, bus):
        execution_order = []

        async def middleware1(event, next_middleware):
            execution_order.append(1)
            await next_middleware(event)
            execution_order.append(4)

        async def middleware2(event, next_middleware):
            execution_order.append(2)
            await next_middleware(event)
            execution_order.append(3)

        async def handler(_):
            execution_order.append('handler')

        bus.add_middleware(middleware1)
        bus.add_middleware(middleware2)
        bus.subscribe(self.TestEvent, handler)

        event = self.TestEvent()
        await bus.emit(event)

        assert execution_order == [1, 2, 'handler', 3, 4]

    @pytest.mark.asyncio
    async def test_middleware_can_modify_event(self, bus):
        class MutableEvent:
            def __init__(self, value):
                self.value = value

        async def modify_middleware(event, next_middleware):
            event.value += 1
            await next_middleware(event)

        async def handler(event):
            assert event.value == 2

        bus.add_middleware(modify_middleware)
        bus.subscribe(MutableEvent, handler)

        event = MutableEvent(1)
        await bus.emit(event)

    @pytest.mark.asyncio
    async def test_middleware_can_interrupt_chain(self, bus):
        handler_called = False

        async def stop_middleware(event, next_middleware):
            pass

        async def handler(_):
            nonlocal handler_called
            handler_called = True

        bus.add_middleware(stop_middleware)
        bus.subscribe(self.TestEvent, handler)

        event = self.TestEvent()
        await bus.emit(event)

        assert not handler_called

    def test_prepare_bus_creates_bus(self):
        ready_bus = prepare_bus()
        assert isinstance(ready_bus, EventBus)

    def test_prepare_bus_adds_middlewares(self):
        ready_bus = prepare_bus()
        assert len(ready_bus.middlewares) == 2

    @pytest.mark.asyncio
    async def test_emit_with_delayed_handlers(self, bus):
        results = []

        async def fast_handler(_):
            results.append('fast')

        async def slow_handler(_):
            await asyncio.sleep(0.2)
            results.append('slow')

        bus.subscribe(self.TestEvent, fast_handler)
        bus.subscribe(self.TestEvent, slow_handler)

        event = self.TestEvent()
        await bus.emit(event)

        assert set(results) == {'fast', 'slow'}

    @pytest.mark.asyncio
    async def test_concurrent_emits(self, bus):
        handler = AsyncMock()
        bus.subscribe(self.TestEvent, handler)

        event = self.TestEvent()

        await asyncio.gather(
            bus.emit(event),
            bus.emit(event),
            bus.emit(event)
        )

        assert handler.call_count == 3


class TestIntegration:
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        bus = prepare_bus()
        results = []

        class UserCreated:
            def __init__(self, user_id):
                self.user_id = user_id

            def get_log_string(self):
                return f"UserId: {self.user_id}"

        class UserDeleted:
            def __init__(self, user_id):
                self.user_id = user_id

            def get_log_string(self):
                return f"UserId: {self.user_id}"

        @bus.on(UserCreated)
        async def handle_user_created(event):
            results.append(f"User {event.user_id} created")
            return event

        @bus.on(UserDeleted)
        async def handle_user_deleted(event):
            results.append(f"User {event.user_id} deleted")

        with capture_logger_output():
            await bus.emit(UserCreated(1))
            await bus.emit(UserDeleted(1))

            assert len(results) == 2
            assert "User 1 created" in results
            assert "User 1 deleted" in results

    @pytest.mark.asyncio
    async def test_complex_event_hierarchy(self):
        bus = EventBus()
        results = []

        class BaseEvent:
            pass

        class SpecificEvent(BaseEvent):
            pass

        @bus.on(BaseEvent)
        async def base_handler(_):
            results.append("base_handler")

        @bus.on(SpecificEvent)
        async def specific_handler(_):
            results.append("specific_handler")

        await bus.emit(SpecificEvent())

        assert len(results) == 2
        assert "base_handler" in results
        assert "specific_handler" in results
