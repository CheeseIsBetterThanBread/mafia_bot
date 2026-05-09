from logging.handlers import RotatingFileHandler
import logging
import os
from pathlib import Path

import pytest

from utils.logger import setup_rotating_logger


class TestRotatingLogger:
    @pytest.fixture
    def temp_log_file(self, tmp_path):
        log_file = tmp_path / "test.log"
        return str(log_file)

    @pytest.fixture
    def logger(self, temp_log_file):
        return setup_rotating_logger(temp_log_file, max_bytes=10000, backup_count=3, logger_name='test_logger')

    def test_logger_creation(self, logger, temp_log_file):
        assert logger is not None
        assert logger.name == 'test_logger'
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], RotatingFileHandler)

    def test_logger_writes_to_file(self, logger, temp_log_file):
        test_message = "Test log message"
        logger.info(test_message)

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert test_message in content

    def test_logger_encoding(self, logger, temp_log_file):
        russian_message = "Тестовое сообщение на русском языке с символами: ёЁъЪэЭ"
        logger.info(russian_message)

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert russian_message in content

    def test_log_levels(self, logger, temp_log_file):
        messages = {
            'DEBUG': "Debug message",
            'INFO': "Info message",
            'WARNING': "Warning message",
            'ERROR': "Error message",
            'CRITICAL': "Critical message"
        }

        logger.debug(messages['DEBUG'])
        logger.info(messages['INFO'])
        logger.warning(messages['WARNING'])
        logger.error(messages['ERROR'])
        logger.critical(messages['CRITICAL'])

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for level, message in messages.items():
                assert message in content
                assert level in content

    def test_log_format(self, logger, temp_log_file):
        def test_func():
            logger.info("Test message")
        test_func()

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'test_func' in content
            assert 'INFO' in content
            assert 'Test message' in content
            assert '-' in content and ':' in content  # asctime

    def test_rotation_by_size(self, temp_log_file):
        max_bytes = 500
        backup_count = 2
        small_logger = setup_rotating_logger(temp_log_file, max_bytes, backup_count, logger_name='test_logger')

        message_size = 100
        messages_count = (max_bytes // message_size) * (backup_count + 2)

        for i in range(messages_count):
            small_logger.info(f"Message number {i} with some extra text to make it longer")

        for handler in small_logger.handlers:
            handler.flush()

        log_dir = Path(temp_log_file).parent
        base_name = Path(temp_log_file).name
        log_files = list(log_dir.glob(f"{base_name}*"))

        assert len(log_files) <= backup_count + 1

        current_size = os.path.getsize(temp_log_file)
        assert current_size <= max_bytes * 1.1

    def test_backup_count_limit(self, temp_log_file):
        max_bytes = 300
        backup_count = 2
        small_logger = setup_rotating_logger(temp_log_file, max_bytes, backup_count, logger_name='test_logger')

        for i in range(50):
            small_logger.info(f"X" * 100)

        for handler in small_logger.handlers:
            handler.flush()

        log_dir = Path(temp_log_file).parent
        base_name = Path(temp_log_file).name
        log_files = sorted(log_dir.glob(f"{base_name}*"))

        max_expected_files = backup_count + 1
        assert len(log_files) <= max_expected_files, \
            f"Expected max {max_expected_files} files, got {len(log_files)}"

    def test_logger_with_exception(self, logger, temp_log_file):
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.exception(f"An error occurred: {e}")

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "An error occurred" in content
            assert "ValueError" in content
            assert "Test exception" in content

    def test_multiple_log_messages(self, logger, temp_log_file):
        messages_count = 100
        for i in range(messages_count):
            logger.info(f"Message {i}")

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) >= messages_count

    def test_logger_configuration(self, temp_log_file):
        max_bytes = 2048
        backup_count = 5
        test_logger = setup_rotating_logger(temp_log_file, max_bytes, backup_count, logger_name='config_logger')

        handler = test_logger.handlers[0]
        assert handler.maxBytes == max_bytes
        assert handler.backupCount == backup_count
        assert handler.encoding == 'utf-8'

    def test_rotation_does_not_lose_messages(self, temp_log_file):
        max_bytes = 2500
        small_logger = setup_rotating_logger(temp_log_file, max_bytes, backup_count=2, logger_name='rotation_logger')

        total_messages = 50
        for i in range(total_messages):
            small_logger.info(f"Message {i} ")

        for handler in small_logger.handlers:
            handler.flush()

        log_dir = Path(temp_log_file).parent
        base_name = Path(temp_log_file).name
        all_content = ""

        log_files = sorted(log_dir.glob(f"{base_name}*"))
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_content += f.read()

        assert len(log_files) > 1
        for i in range(total_messages):
            assert f"Message {i}" in all_content


class TestLoggerPerformance:
    def test_write_performance(self, tmp_path):
        import time

        log_file = tmp_path / "perf_test.log"
        logger = setup_rotating_logger(str(log_file), max_bytes=1000000, backup_count=3, logger_name='test_logger')

        start_time = time.time()
        messages_count = 1000

        for i in range(messages_count):
            logger.info(f"Performance test message {i}")

        elapsed_time = time.time() - start_time
        messages_per_second = messages_count / elapsed_time

        print(f"\nЗаписано {messages_count} сообщений за {elapsed_time:.2f} сек")
        print(f"Скорость: {messages_per_second:.0f} сообщений/сек")

        assert messages_per_second > 100
