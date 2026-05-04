def validate_adapter(bus, adapter):
    missing = []

    for event_type in adapter.REQUIRED_EVENTS:
        has_handler = any(
            issubclass(event_type, subscribed)
            for subscribed in bus.subscribers
        )

        if not has_handler:
            missing.append(event_type.__name__)

    if missing:
        raise RuntimeError(
            f"{adapter.__class__.__name__} не обрабатывает: {missing}"
        )
