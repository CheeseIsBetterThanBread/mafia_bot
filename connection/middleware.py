from config.settings import MAIN_LOG, ERROR_LOG


async def logging_middleware(event, next_handler):
    with open(MAIN_LOG, 'a') as f:
        f.write(f"[START] {event.get_log_string()}")
        await next_handler(event)
        f.write(f"[END] {event.get_log_string()}")

async def error_middleware(event, next_handler):
    try:
        await next_handler(event)
    except Exception as e:
        with open(ERROR_LOG, 'a') as f:
            f.write(f"{event.get_log_string()} | {e}")
