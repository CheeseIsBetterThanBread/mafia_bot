import logging
from logging.handlers import RotatingFileHandler

from config.settings import LOG_FILE, MAX_BYTES_PER_FILE, BACKUP_FILES


def setup_rotating_logger(log_file, max_bytes, backup_count, logger_name='App'):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


LOGGER = setup_rotating_logger(LOG_FILE, MAX_BYTES_PER_FILE, BACKUP_FILES)
