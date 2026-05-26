class Adapter:
    from connection.events import ResponseBase, ResponseWithAlert, ResponseWithOptions

    REQUIRED_EVENTS = [ResponseBase, ResponseWithAlert, ResponseWithOptions]
