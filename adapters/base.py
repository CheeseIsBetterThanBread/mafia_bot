class Adapter:
    from connection.events import ResponseBase, ResponseWithAlert, ResponseWithOptions

    REQUIRED_EVENTS = [ResponseBase, ResponseWithAlert, ResponseWithOptions]


class FallBack:
    @staticmethod
    async def emit(_):
        raise ValueError("Failed to connect to EventBus")


fallback_bus = FallBack()
