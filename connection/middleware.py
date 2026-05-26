from utils.logger import LOGGER


async def logging_middleware(event, next_handler):
    LOGGER.debug(f"[START] {event.get_log_string()}")
    await next_handler(event)
    LOGGER.debug(f"[END] {event.get_log_string()}")


async def error_middleware(event, next_handler):
    try:
        await next_handler(event)
    except Exception as e:
        LOGGER.error(f"{event.get_log_string()} | {e}")
