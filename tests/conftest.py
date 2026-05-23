from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import io
import logging
import sys

from unittest.mock import patch


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


class MockOperations:
    def __init__(self, target, **mock_config):
        self.target = target
        self.mock_config = mock_config
        self.mocks = None

    def __enter__(self):
        kwargs = {name: mock_class() if callable(mock_class) else mock_class
                  for name, mock_class in self.mock_config.items()}
        self.patcher = patch.multiple(self.target, **kwargs)
        self.mocks = self.patcher.__enter__()
        return SimpleNamespace(**self.mocks)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.patcher.__exit__(exc_type, exc_val, exc_tb)
