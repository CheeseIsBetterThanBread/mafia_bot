import inspect
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config.settings import (
    LOG_FILE,
    VERBOSE_LOG_FILE,
    MAX_BYTES_PER_FILE,
    BACKUP_FILES,
    LOG_FORMAT,
)


def add_custom_methods(logger):
    verbose_logs = []

    def get_caller_info():
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back.f_back
            filename = caller_frame.f_code.co_filename
            line_no = caller_frame.f_lineno
            func_name = caller_frame.f_code.co_name

            short_filename = Path(filename).name

            return f"{short_filename}:{line_no} in {func_name}()"
        finally:
            del frame

    def verbose_debug(msg, *args):
        if logger.isEnabledFor(logging.DEBUG):
            formatted_msg = msg % args if args else msg
            caller_info = get_caller_info()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            log_entry = f"[{timestamp}] [{caller_info}] {formatted_msg}"
            verbose_logs.append(log_entry)

    def save_verbose_log():
        if not verbose_logs:
            print("No verbose logs to save")
            return

        with open(VERBOSE_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"Verbose Debug Log\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Total entries: {len(verbose_logs)}\n")
            f.write("=" * 80 + "\n\n")
            f.write("\n".join(verbose_logs))

        print(f"Saved verbose logs to {VERBOSE_LOG_FILE}")

    def clear_verbose_log():
        verbose_logs.clear()

    def get_verbose_log_count():
        return len(verbose_logs)

    logger.verbose_debug = verbose_debug
    logger.save_verbose_log = save_verbose_log
    logger.clear_verbose_log = clear_verbose_log
    logger.get_verbose_log_count = get_verbose_log_count

    return logger


def setup_rotating_logger(log_file, max_bytes, backup_count, logger_name="App"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )

    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


LOGGER = add_custom_methods(
    setup_rotating_logger(LOG_FILE, MAX_BYTES_PER_FILE, BACKUP_FILES)
)
