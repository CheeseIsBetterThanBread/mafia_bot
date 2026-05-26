import pytest

from utils.validate import validate_adapter


class A: ...


class B: ...


class C: ...


class SimpleBus:
    def __init__(self):
        self.subscribers = {}


class SimpleAdapter:
    REQUIRED_EVENTS = [A, B, C]

    def handle(self):
        return 42


def test_valid():
    bus = SimpleBus()
    adapter = SimpleAdapter()

    bus.subscribers[A] = adapter.handle()
    bus.subscribers[B] = adapter.handle()
    bus.subscribers[C] = adapter.handle()

    validate_adapter(bus, adapter)


def test_invalid():
    bus = SimpleBus()
    adapter = SimpleAdapter()

    bus.subscribers[A] = adapter.handle()
    bus.subscribers[B] = adapter.handle()

    with pytest.raises(RuntimeError):
        validate_adapter(bus, adapter)
