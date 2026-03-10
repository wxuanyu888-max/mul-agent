"""Core logging implementation for mul-agent Python backend.

Provides subsystem-based logging with support for:
- Multiple log levels (silent, fatal, error, warn, info, debug, trace)
- File and console output
- JSONL and text formats
- Rolling log files
- Environment variable overrides
"""

import os
import sys
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union
from dataclasses import dataclass, field

# Log levels matching TypeScript implementation
LOG_LEVELS = ["silent", "fatal", "error", "warn", "info", "debug", "trace"]
LogLevel = str  # "silent" | "fatal" | "error" | "warn" | "info" | "debug" | "trace"

# Default configuration
DEFAULT_LOG_DIR = Path(os.environ.get("OPENCLAW_TMP_DIR", "/tmp/openclaw"))
DEFAULT_MAX_FILE_BYTES = 500 * 1024 * 1024  # 500 MB
DEFAULT_LOG_FILE_PATTERN = "openclaw-{date}.log"
MAX_LOG_AGE_DAYS = 1

# Level to numeric value for comparison
LEVEL_TO_MIN_LEVEL = {
    "silent": float("inf"),
    "fatal": 0,
    "error": 1,
    "warn": 2,
    "info": 3,
    "debug": 4,
    "trace": 5,
}


def parse_log_level(level: Optional[str]) -> Optional[LogLevel]:
    """Parse log level string, return None if invalid."""
    if not isinstance(level, str):
        return None
    candidate = level.strip()
    if candidate in LOG_LEVELS:
        return candidate  # type: ignore
    return None


def normalize_log_level(level: Optional[str], fallback: LogLevel = "info") -> LogLevel:
    """Normalize log level string, return fallback if invalid."""
    parsed = parse_log_level(level)
    return parsed if parsed else fallback


def resolve_env_log_level() -> Optional[LogLevel]:
    """Resolve log level from OPENCLAW_LOG_LEVEL environment variable."""
    raw = os.environ.get("OPENCLAW_LOG_LEVEL", "")
    trimmed = raw.strip()
    if not trimmed:
        return None

    parsed = parse_log_level(trimmed)
    if parsed:
        return parsed

    # Warn about invalid value (only once)
    if not hasattr(resolve_env_log_level, "_warned"):
        resolve_env_log_level._warned = True
        allowed = "|".join(LOG_LEVELS)
        sys.stderr.write(
            f"[mul-agent] Ignoring invalid OPENCLAW_LOG_LEVEL=\"{trimmed}\" "
            f"(allowed: {allowed}).\n"
        )

    return None


@dataclass
class LogRecord:
    """A single log record."""
    level: LogLevel
    message: str
    subsystem: str
    timestamp: datetime
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "time": self.timestamp.isoformat(),
            "level": self.level,
            "subsystem": self.subsystem,
            "message": self.message,
        }
        if self.meta:
            result.update(self.meta)
        return result

    def to_jsonl(self) -> str:
        """Convert to JSONL format."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_text(self, style: str = "compact") -> str:
        """Convert to text format."""
        if style == "pretty":
            time_str = self.timestamp.strftime("%H:%M:%S")
            return f"[{time_str}] [{self.subsystem}] {self.level.upper()}: {self.message}"
        elif style == "json":
            return self.to_jsonl()
        else:  # compact
            time_str = self.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            return f"{time_str} [{self.subsystem}] {self.message}"


@dataclass
class LoggingState:
    """Global logging state (singleton pattern)."""
    cached_logger: Optional["Logger"] = None
    cached_settings: Optional["LoggerSettings"] = None
    cached_console_settings: Optional["ConsoleSettings"] = None
    override_settings: Optional["LoggerSettings"] = None
    invalid_env_log_level_value: Optional[str] = None
    console_patched: bool = False
    force_console_to_stderr: bool = False
    console_timestamp_prefix: bool = False
    console_subsystem_filter: Optional[List[str]] = None
    raw_console: Optional[Dict[str, Any]] = None

    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LoggingState":
        """Get singleton instance."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


@dataclass
class LoggerSettings:
    """Logger configuration."""
    level: LogLevel = "info"
    file: Optional[Path] = None
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES

    @classmethod
    def default(cls) -> "LoggerSettings":
        """Create default settings."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = DEFAULT_LOG_DIR / DEFAULT_LOG_FILE_PATTERN.format(date=today)
        return cls(
            level=normalize_log_level(os.environ.get("OPENCLAW_LOG_LEVEL"), "info"),
            file=log_file,
            max_file_bytes=DEFAULT_MAX_FILE_BYTES,
        )


@dataclass
class ConsoleSettings:
    """Console output configuration."""
    level: LogLevel = "info"
    style: str = "compact"  # "pretty" | "compact" | "json"

    @classmethod
    def default(cls) -> "ConsoleSettings":
        """Create default console settings."""
        env_level = resolve_env_log_level()
        level = env_level if env_level else "info"

        # Default to silent in test environment
        if os.environ.get("VITEST") == "true" and os.environ.get("OPENCLAW_TEST_CONSOLE") != "1":
            level = "silent"

        # Determine style based on TTY
        style = "compact"
        if sys.stdout.isatty():
            style = "pretty"

        return cls(level=level, style=style)


class SubsystemLogger:
    """Logger for a specific subsystem."""

    def __init__(
        self,
        subsystem: str,
        parent: "Logger",
    ):
        self.subsystem = subsystem
        self._parent = parent

    def _log(self, level: LogLevel, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Internal log method."""
        self._parent._log(self.subsystem, level, message, meta)

    def trace(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log trace level message."""
        self._log("trace", message, meta)

    def debug(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log debug level message."""
        self._log("debug", message, meta)

    def info(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log info level message."""
        self._log("info", message, meta)

    def warn(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log warn level message."""
        self._log("warn", message, meta)

    def error(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log error level message."""
        self._log("error", message, meta)

    def fatal(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log fatal level message."""
        self._log("fatal", message, meta)

    def child(self, name: str) -> "SubsystemLogger":
        """Create child subsystem logger."""
        return SubsystemLogger(f"{self.subsystem}/{name}", self._parent)

    def is_enabled(self, level: LogLevel, target: str = "any") -> bool:
        """Check if logging is enabled for given level."""
        return self._parent._is_level_enabled(level)


class Logger:
    """Main logger class."""

    def __init__(self, settings: Optional[LoggerSettings] = None):
        self.settings = settings or LoggerSettings.default()
        self._console_settings = ConsoleSettings.default()
        self._current_file_bytes = 0
        self._file_handle: Optional[TextIO] = None
        self._lock = threading.Lock()
        self._warned_about_size_cap = False

        # Initialize log directory and clean up old logs
        self._init_log_file()

    def _init_log_file(self) -> None:
        """Initialize log file and clean up old logs."""
        if self.settings.file is None:
            return

        # Create log directory if needed
        self.settings.file.parent.mkdir(parents=True, exist_ok=True)

        # Clean up old rolling logs
        self._prune_old_logs()

        # Get current file size
        if self.settings.file.exists():
            self._current_file_bytes = self.settings.file.stat().st_size

    def _prune_old_logs(self) -> None:
        """Remove log files older than MAX_LOG_AGE_DAYS."""
        if self.settings.file is None:
            return

        log_dir = self.settings.file.parent
        cutoff = datetime.now().timestamp() - (MAX_LOG_AGE_DAYS * 24 * 60 * 60)

        try:
            for entry in log_dir.iterdir():
                if not entry.is_file():
                    continue
                if not entry.name.startswith("openclaw-") or not entry.name.endswith(".log"):
                    continue
                if entry.stat().st_mtime < cutoff:
                    entry.unlink()
        except Exception:
            pass  # Ignore errors during cleanup

    def _is_level_enabled(self, level: LogLevel) -> bool:
        """Check if a log level is enabled."""
        return LEVEL_TO_MIN_LEVEL[level] <= LEVEL_TO_MIN_LEVEL[self.settings.level]

    def _write_to_file(self, record: LogRecord) -> None:
        """Write log record to file."""
        if self.settings.file is None:
            return

        try:
            line = record.to_jsonl() + "\n"
            line_bytes = len(line.encode("utf-8"))

            # Check file size cap
            next_bytes = self._current_file_bytes + line_bytes
            if next_bytes > self.settings.max_file_bytes:
                if not self._warned_about_size_cap:
                    self._warned_about_size_cap = True
                    warning = json.dumps({
                        "time": datetime.now().isoformat(),
                        "level": "warn",
                        "subsystem": "logging",
                        "message": f"Log file size cap reached; suppressing writes "
                                  f"file={self.settings.file} maxFileBytes={self.settings.max_file_bytes}",
                    })
                    with open(self.settings.file, "a", encoding="utf-8") as f:
                        f.write(warning + "\n")
                    sys.stderr.write(
                        f"[mul-agent] Log file size cap reached; suppressing writes "
                        f"file={self.settings.file} maxFileBytes={self.settings.max_file_bytes}\n"
                    )
                return

            with open(self.settings.file, "a", encoding="utf-8") as f:
                f.write(line)
            self._current_file_bytes = next_bytes

        except Exception:
            pass  # Never block on logging failures

    def _write_to_console(self, record: LogRecord) -> None:
        """Write log record to console."""
        # Check console level
        if LEVEL_TO_MIN_LEVEL[record.level] > LEVEL_TO_MIN_LEVEL[self._console_settings.level]:
            return

        # Check subsystem filter
        state = LoggingState.get_instance()
        if state.console_subsystem_filter:
            if not any(
                record.subsystem == prefix or record.subsystem.startswith(f"{prefix}/")
                for prefix in state.console_subsystem_filter
            ):
                return

        # Format and write
        try:
            line = record.to_text(self._console_settings.style)

            # Add timestamp prefix if configured
            if state.console_timestamp_prefix and self._console_settings.style != "json":
                if not line.startswith(("0", "1", "2")):  # No timestamp already
                    time_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                    line = f"{time_str} {line}"

            # Determine output stream
            sink = sys.stderr if (
                state.force_console_to_stderr or
                record.level in ("error", "fatal")
            ) else sys.stdout

            sink.write(line + "\n")
            sink.flush()

        except Exception:
            pass  # Never block on logging failures

    def _log(
        self,
        subsystem: str,
        level: LogLevel,
        message: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal log method."""
        if not self._is_level_enabled(level):
            return

        record = LogRecord(
            level=level,
            message=message,
            subsystem=subsystem,
            timestamp=datetime.now(),
            meta=meta,
        )

        with self._lock:
            self._write_to_file(record)
            self._write_to_console(record)

    def get_subsystem_logger(self, subsystem: str) -> SubsystemLogger:
        """Get a logger for a specific subsystem."""
        return SubsystemLogger(subsystem, self)

    def trace(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log trace level message."""
        self._log("root", "trace", message, meta)

    def debug(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log debug level message."""
        self._log("root", "debug", message, meta)

    def info(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log info level message."""
        self._log("root", "info", message, meta)

    def warn(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log warn level message."""
        self._log("root", "warn", message, meta)

    def error(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log error level message."""
        self._log("root", "error", message, meta)

    def fatal(self, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Log fatal level message."""
        self._log("root", "fatal", message, meta)


# Global functions
_state = LoggingState.get_instance()


def setup_logging(
    level: Optional[LogLevel] = None,
    file: Optional[Union[str, Path]] = None,
    max_file_bytes: Optional[int] = None,
    console_level: Optional[LogLevel] = None,
    console_style: Optional[str] = None,
) -> Logger:
    """Set up logging with custom configuration."""
    settings = LoggerSettings.default()

    if level:
        settings.level = level
    if file:
        settings.file = Path(file)
    if max_file_bytes:
        settings.max_file_bytes = max_file_bytes

    # Override with environment
    env_level = resolve_env_log_level()
    if env_level:
        settings.level = env_level

    # Reset singleton
    _state.cached_logger = None
    _state.cached_settings = None

    logger = Logger(settings)
    _state.cached_logger = logger
    _state.cached_settings = settings

    if console_level or console_style:
        console_settings = ConsoleSettings.default()
        if console_level:
            console_settings.level = console_level
        if console_style:
            console_settings.style = console_style
        _state.cached_console_settings = console_settings

    return logger


def get_logger() -> Logger:
    """Get the global logger instance."""
    # Check for override settings
    if _state.override_settings:
        logger = Logger(_state.override_settings)
        _state.cached_logger = logger
        _state.cached_settings = _state.override_settings
        return logger

    if _state.cached_logger is None:
        settings = LoggerSettings.default()

        # Check environment variable
        env_level = resolve_env_log_level()
        if env_level:
            settings.level = env_level

        logger = Logger(settings)
        _state.cached_logger = logger
        _state.cached_settings = settings

    return _state.cached_logger  # type: ignore


def get_subsystem_logger(subsystem: str) -> SubsystemLogger:
    """Get a subsystem logger."""
    return get_logger().get_subsystem_logger(subsystem)


def reset_logging() -> None:
    """Reset logging state (useful for testing)."""
    _state.cached_logger = None
    _state.cached_settings = None
    _state.cached_console_settings = None
    _state.override_settings = None


def set_logger_override(settings: Optional[LoggerSettings] = None) -> None:
    """Override logger settings (useful for testing)."""
    _state.override_settings = settings
    _state.cached_logger = None
    _state.cached_settings = None


def set_console_subsystem_filter(filters: Optional[List[str]] = None) -> None:
    """Set console subsystem filter."""
    if not filters:
        _state.console_subsystem_filter = None
    else:
        normalized = [f.strip() for f in filters if f.strip()]
        _state.console_subsystem_filter = normalized if normalized else None


def set_console_timestamp_prefix(enabled: bool) -> None:
    """Enable/disable console timestamp prefix."""
    _state.console_timestamp_prefix = enabled


def route_logs_to_stderr() -> None:
    """Route all console logs to stderr."""
    _state.force_console_to_stderr = True


def is_log_level_enabled(level: LogLevel) -> bool:
    """Check if a log level is enabled for file logging."""
    return LEVEL_TO_MIN_LEVEL[level] <= LEVEL_TO_MIN_LEVEL[get_logger().settings.level]
