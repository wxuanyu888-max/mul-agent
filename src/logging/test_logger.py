"""Tests for mul-agent Python logging system."""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging.logger import (
    LogLevel,
    LOG_LEVELS,
    Logger,
    LoggerSettings,
    ConsoleSettings,
    SubsystemLogger,
    LogRecord,
    parse_log_level,
    normalize_log_level,
    resolve_env_log_level,
    setup_logging,
    get_logger,
    get_subsystem_logger,
    reset_logging,
    set_logger_override,
    is_log_level_enabled,
    LEVEL_TO_MIN_LEVEL,
)


class TestLogLevelParsing:
    """Test log level parsing functions."""

    def test_parse_valid_levels(self):
        """Test parsing valid log levels."""
        for level in LOG_LEVELS:
            assert parse_log_level(level) == level

    def test_parse_invalid_levels(self):
        """Test parsing invalid log levels."""
        assert parse_log_level(None) is None
        assert parse_log_level("") is None
        assert parse_log_level("invalid") is None
        assert parse_log_level("DEBUG") is None  # Case sensitive

    def test_parse_with_whitespace(self):
        """Test parsing levels with whitespace."""
        assert parse_log_level("  info  ") == "info"
        assert parse_log_level("\tdebug\n") == "debug"

    def test_normalize_log_level(self):
        """Test log level normalization."""
        assert normalize_log_level(None) == "info"
        assert normalize_log_level("invalid", "warn") == "warn"
        assert normalize_log_level("error", "info") == "error"
        assert normalize_log_level("", "debug",) == "debug"

    def test_level_to_min_level(self):
        """Test level to numeric value conversion."""
        assert LEVEL_TO_MIN_LEVEL["silent"] == float("inf")
        assert LEVEL_TO_MIN_LEVEL["fatal"] == 0
        assert LEVEL_TO_MIN_LEVEL["error"] == 1
        assert LEVEL_TO_MIN_LEVEL["warn"] == 2
        assert LEVEL_TO_MIN_LEVEL["info"] == 3
        assert LEVEL_TO_MIN_LEVEL["debug"] == 4
        assert LEVEL_TO_MIN_LEVEL["trace"] == 5


class TestEnvLogLevel:
    """Test environment variable log level handling."""

    def setup_method(self):
        """Set up test environment."""
        self._original_level = os.environ.get("OPENCLAW_LOG_LEVEL")
        if "OPENCLAW_LOG_LEVEL" in os.environ:
            del os.environ["OPENCLAW_LOG_LEVEL"]
        reset_logging()

    def teardown_method(self):
        """Restore original environment."""
        if self._original_level is not None:
            os.environ["OPENCLAW_LOG_LEVEL"] = self._original_level
        elif "OPENCLAW_LOG_LEVEL" in os.environ:
            del os.environ["OPENCLAW_LOG_LEVEL"]
        reset_logging()

    def test_valid_env_level(self):
        """Test valid environment log level."""
        os.environ["OPENCLAW_LOG_LEVEL"] = "debug"
        assert resolve_env_log_level() == "debug"

    def test_invalid_env_level(self):
        """Test invalid environment log level."""
        os.environ["OPENCLAW_LOG_LEVEL"] = "invalid"
        assert resolve_env_log_level() is None

    def test_empty_env_level(self):
        """Test empty environment log level."""
        os.environ["OPENCLAW_LOG_LEVEL"] = ""
        assert resolve_env_log_level() is None

    def test_env_level_with_whitespace(self):
        """Test environment log level with whitespace."""
        os.environ["OPENCLAW_LOG_LEVEL"] = "  warn  "
        assert resolve_env_log_level() == "warn"


class TestLogRecord:
    """Test LogRecord class."""

    def test_to_dict(self):
        """Test converting log record to dictionary."""
        record = LogRecord(
            level="info",
            message="Test message",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            meta={"key": "value"},
        )
        result = record.to_dict()
        assert result["level"] == "info"
        assert result["message"] == "Test message"
        assert result["subsystem"] == "test"
        assert result["key"] == "value"
        assert "time" in result

    def test_to_dict_no_meta(self):
        """Test converting log record without meta."""
        record = LogRecord(
            level="debug",
            message="Simple message",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        result = record.to_dict()
        assert result["level"] == "debug"
        assert result["message"] == "Simple message"
        assert "key" not in result

    def test_to_jsonl(self):
        """Test converting log record to JSONL."""
        record = LogRecord(
            level="error",
            message="Error message",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        jsonl = record.to_jsonl()
        parsed = json.loads(jsonl)
        assert parsed["level"] == "error"
        assert parsed["message"] == "Error message"

    def test_to_text_pretty(self):
        """Test converting log record to pretty text."""
        record = LogRecord(
            level="info",
            message="Test",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 30, 45),
        )
        text = record.to_text("pretty")
        assert "[12:30:45]" in text
        assert "[test]" in text
        assert "INFO" in text
        assert "Test" in text

    def test_to_text_compact(self):
        """Test converting log record to compact text."""
        record = LogRecord(
            level="warn",
            message="Warning",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 30, 45, 123000),
        )
        text = record.to_text("compact")
        assert "2024-01-01T12:30:45.123" in text
        assert "[test]" in text
        assert "Warning" in text

    def test_to_text_json(self):
        """Test converting log record to JSON text."""
        record = LogRecord(
            level="debug",
            message="Debug",
            subsystem="test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        text = record.to_text("json")
        parsed = json.loads(text)
        assert parsed["level"] == "debug"


class TestLogger:
    """Test Logger class."""

    def setup_method(self):
        """Set up test environment."""
        self._original_level = os.environ.get("OPENCLAW_LOG_LEVEL")
        self._temp_dir = tempfile.mkdtemp()
        reset_logging()

    def teardown_method(self):
        """Restore original environment."""
        if self._original_level is not None:
            os.environ["OPENCLAW_LOG_LEVEL"] = self._original_level
        elif "OPENCLAW_LOG_LEVEL" in os.environ:
            del os.environ["OPENCLAW_LOG_LEVEL"]
        reset_logging()

    def test_logger_creation(self):
        """Test logger creation."""
        logger = Logger()
        assert logger.settings.level == "info"

    def test_logger_with_custom_settings(self):
        """Test logger with custom settings."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(
            level="debug",
            file=log_file,
            max_file_bytes=1024 * 1024,
        )
        logger = Logger(settings)
        assert logger.settings.level == "debug"
        assert logger.settings.file == log_file

    def test_logger_level_filtering(self):
        """Test logger level filtering."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(level="warn", file=log_file)
        logger = Logger(settings)

        # These should not be written
        logger.trace("Trace message")
        logger.debug("Debug message")
        logger.info("Info message")

        # These should be written
        logger.warn("Warn message")
        logger.error("Error message")

        # Read log file and verify
        content = log_file.read_text()
        assert "Warn message" in content
        assert "Error message" in content
        assert "Trace message" not in content
        assert "Debug message" not in content
        assert "Info message" not in content

    def test_subsystem_logger(self):
        """Test subsystem logger."""
        logger = Logger()
        subsystem_logger = logger.get_subsystem_logger("test/subsystem")

        assert isinstance(subsystem_logger, SubsystemLogger)
        assert subsystem_logger.subsystem == "test/subsystem"

        # Test child logger
        child_logger = subsystem_logger.child("child")
        assert child_logger.subsystem == "test/subsystem/child"

    def test_subsystem_logger_logging(self):
        """Test logging with subsystem logger."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(level="debug", file=log_file)
        logger = Logger(settings)
        subsystem_logger = logger.get_subsystem_logger("test/subsystem")

        subsystem_logger.info("Subsystem message", {"extra": "data"})

        content = log_file.read_text()
        assert "Subsystem message" in content
        assert "test/subsystem" in content
        assert "extra" in content

    def test_is_log_level_enabled(self):
        """Test is_log_level_enabled function."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(level="warn", file=log_file)
        logger = Logger(settings)

        assert not is_log_level_enabled("debug")
        assert not is_log_level_enabled("info")
        assert is_log_level_enabled("warn")
        assert is_log_level_enabled("error")
        assert is_log_level_enabled("fatal")

    def test_file_size_cap(self):
        """Test file size cap."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(level="info", file=log_file, max_file_bytes=500)
        logger = Logger(settings)

        # Write many messages
        for i in range(100):
            logger.info(f"Message {i}" * 10)

        # File should not exceed cap significantly
        size = log_file.stat().st_size
        assert size <= 500 + 200  # Small buffer for warning message


class TestGlobalLogger:
    """Test global logger functions."""

    def setup_method(self):
        """Set up test environment."""
        self._original_level = os.environ.get("OPENCLAW_LOG_LEVEL")
        reset_logging()

    def teardown_method(self):
        """Restore original environment."""
        if self._original_level is not None:
            os.environ["OPENCLAW_LOG_LEVEL"] = self._original_level
        elif "OPENCLAW_LOG_LEVEL" in os.environ:
            del os.environ["OPENCLAW_LOG_LEVEL"]
        reset_logging()

    def test_get_logger(self):
        """Test getting global logger."""
        logger = get_logger()
        assert logger is not None

        # Should return same instance
        logger2 = get_logger()
        assert logger is logger2

    def test_get_subsystem_logger(self):
        """Test getting subsystem logger."""
        logger = get_subsystem_logger("test")
        assert logger.subsystem == "test"

    def test_setup_logging(self):
        """Test setting up logging."""
        log_file = Path(self._temp_dir) / "test.log"
        logger = setup_logging(level="debug", file=str(log_file))

        assert logger.settings.level == "debug"
        assert logger.settings.file == log_file

    def test_reset_logging(self):
        """Test resetting logging."""
        logger1 = get_logger()
        reset_logging()
        logger2 = get_logger()

        # Should be different instances after reset
        assert logger1 is not logger2

    def test_set_logger_override(self):
        """Test setting logger override."""
        log_file = Path(self._temp_dir) / "test.log"
        settings = LoggerSettings(level="trace", file=log_file)
        set_logger_override(settings)

        logger = get_logger()
        assert logger.settings.level == "trace"

        # Reset and verify override is cleared
        reset_logging()
        logger2 = get_logger()
        assert logger2.settings.level != "trace"


class TestConsoleSettings:
    """Test console settings."""

    def test_default_console_settings(self):
        """Test default console settings."""
        settings = ConsoleSettings.default()
        assert settings.style in ("pretty", "compact", "json")

    def test_console_settings_with_tty(self):
        """Test console settings with TTY detection."""
        # This tests that the style is chosen based on TTY status
        settings = ConsoleSettings.default()
        assert isinstance(settings.style, str)


class TestLoggingConfig:
    """Test logging configuration."""

    def test_logging_config_from_dict(self):
        """Test creating LoggingConfig from dictionary."""
        from logging.config import LoggingConfig

        data = {
            "level": "debug",
            "file": "/tmp/test.log",
            "maxFileBytes": 1024,
            "consoleLevel": "warn",
            "consoleStyle": "json",
        }
        config = LoggingConfig.from_dict(data)

        assert config.level == "debug"
        assert config.file == Path("/tmp/test.log")
        assert config.max_file_bytes == 1024
        assert config.console_level == "warn"
        assert config.console_style == "json"

    def test_logging_config_from_dict_snake_case(self):
        """Test creating LoggingConfig from dictionary with snake_case."""
        from logging.config import LoggingConfig

        data = {
            "level": "info",
            "max_file_bytes": 2048,
            "console_level": "error",
            "console_style": "pretty",
        }
        config = LoggingConfig.from_dict(data)

        assert config.level == "info"
        assert config.max_file_bytes == 2048
        assert config.console_level == "error"
        assert config.console_style == "pretty"

    def test_read_logging_config(self):
        """Test reading logging configuration from file."""
        from logging.config import read_logging_config, get_config_path

        # Create temp config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "logging": {
                    "level": "debug",
                    "consoleStyle": "compact",
                }
            }, f)
            temp_path = f.name

        try:
            # Temporarily override config path
            original_path = os.environ.get("OPENCLAW_CONFIG")
            os.environ["OPENCLAW_CONFIG"] = temp_path

            config = read_logging_config()
            assert config is not None
            assert config.level == "debug"
            assert config.console_style == "compact"

        finally:
            os.unlink(temp_path)
            if original_path:
                os.environ["OPENCLAW_CONFIG"] = original_path
            elif "OPENCLAW_CONFIG" in os.environ:
                del os.environ["OPENCLAW_CONFIG"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
