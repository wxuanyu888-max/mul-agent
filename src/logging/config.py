"""Logging configuration for mul-agent Python backend.

Handles reading logging configuration from config files.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .logger import LogLevel, LOG_LEVELS, normalize_log_level, DEFAULT_LOG_DIR, DEFAULT_MAX_FILE_BYTES


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: Optional[LogLevel] = None
    file: Optional[Path] = None
    max_file_bytes: Optional[int] = None
    console_level: Optional[LogLevel] = None
    console_style: Optional[str] = None  # "pretty" | "compact" | "json"
    redact_sensitive: Optional[str] = None  # "off" | "tools"
    redact_patterns: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingConfig":
        """Create LoggingConfig from dictionary."""
        if not isinstance(data, dict):
            return cls()

        config = cls()

        if "level" in data:
            config.level = normalize_log_level(data["level"], "info")

        if "file" in data:
            config.file = Path(data["file"])

        if "maxFileBytes" in data:
            config.max_file_bytes = int(data["maxFileBytes"])
        elif "max_file_bytes" in data:
            config.max_file_bytes = int(data["max_file_bytes"])

        if "consoleLevel" in data:
            config.console_level = normalize_log_level(data["consoleLevel"], "info")
        elif "console_level" in data:
            config.console_level = normalize_log_level(data["console_level"], "info")

        if "consoleStyle" in data:
            style = data["consoleStyle"]
            if style in ("pretty", "compact", "json"):
                config.console_style = style
        elif "console_style" in data:
            style = data["console_style"]
            if style in ("pretty", "compact", "json"):
                config.console_style = style

        if "redactSensitive" in data:
            config.redact_sensitive = data["redactSensitive"]
        elif "redact_sensitive" in data:
            config.redact_sensitive = data["redact_sensitive"]

        if "redactPatterns" in data:
            patterns = data["redactPatterns"]
            if isinstance(patterns, list):
                config.redact_patterns = [str(p) for p in patterns]
        elif "redact_patterns" in data:
            patterns = data["redact_patterns"]
            if isinstance(patterns, list):
                config.redact_patterns = [str(p) for p in patterns]

        return config


def get_config_path() -> Path:
    """Get path to configuration file."""
    # Check environment variable
    config_path = os.environ.get("OPENCLAW_CONFIG")
    if config_path:
        return Path(config_path)

    # Default config locations
    possible_paths = [
        Path.cwd() / "openclaw.config.json",
        Path.cwd() / "openclaw.config.jsonc",
        Path.home() / ".openclaw" / "config.json",
        Path.home() / ".openclaw" / "config.jsonc",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return Path.cwd() / "openclaw.config.json"


def read_jsonc(path: Path) -> Dict[str, Any]:
    """Read JSONC file (JSON with comments support)."""
    content = path.read_text(encoding="utf-8")

    # Simple comment removal (handles // and /* */ comments)
    lines = []
    in_block_comment = False
    for line in content.splitlines():
        if in_block_comment:
            end_idx = line.find("*/")
            if end_idx != -1:
                line = line[end_idx + 2:]
                in_block_comment = False
            else:
                continue

        # Remove single-line comments
        comment_idx = line.find("//")
        if comment_idx != -1:
            line = line[:comment_idx]

        # Check for block comment start
        while "/*" in line:
            start_idx = line.find("/*")
            end_idx = line.find("*/", start_idx + 2)
            if end_idx != -1:
                line = line[:start_idx] + line[end_idx + 2:]
            else:
                line = line[:start_idx]
                in_block_comment = True
                break

        lines.append(line)

    cleaned = "\n".join(lines)
    return json.loads(cleaned) if cleaned.strip() else {}


def read_logging_config() -> Optional[LoggingConfig]:
    """Read logging configuration from config file."""
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        if config_path.suffix == ".jsonc":
            parsed = read_jsonc(config_path)
        else:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))

        if not isinstance(parsed, dict):
            return None

        logging_data = parsed.get("logging")
        if not logging_data or not isinstance(logging_data, dict):
            return None

        return LoggingConfig.from_dict(logging_data)

    except Exception:
        return None
