from contextlib import contextmanager
import io
import logging
import sys
from pathlib import Path


root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

@contextmanager
def capture_logger_output(log_level = logging.DEBUG):
    from config.settings import LOG_FORMAT
    from utils.logger import LOGGER

    original_handlers = LOGGER.handlers.copy()
    original_level = LOGGER.level

    log_stream = io.StringIO()
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    LOGGER.handlers.clear()
    LOGGER.addHandler(stream_handler)
    LOGGER.setLevel(log_level)

    try:
        yield log_stream
    finally:
        LOGGER.handlers.clear()
        for handler in original_handlers:
            LOGGER.addHandler(handler)
        LOGGER.setLevel(original_level)
        log_stream.close()
