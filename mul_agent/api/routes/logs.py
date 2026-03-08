"""Logs API routes"""

import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

# Log file paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
LOG_DIR = BASE_DIR / "storage" / "logs"


def _parse_log_line(line: str) -> dict:
    """Parse a single log line from JSONL format"""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def _load_all_logs(limit: int = 1000) -> list:
    """Load logs from all log files"""
    logs = []

    if not LOG_DIR.exists():
        return logs

    # Get all .jsonl and .log files, sorted by modification time (newest first)
    log_files = sorted(
        [f for f in LOG_DIR.glob("*.jsonl") if f.is_file()] +
        [f for f in LOG_DIR.glob("*.log") if f.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        log_entry = _parse_log_line(line)
                        if log_entry:
                            logs.append(log_entry)
                        if len(logs) >= limit:
                            return logs
        except Exception as e:
            logging.warning(f"Failed to read log file {log_file}: {e}")
            continue

    return logs


@router.get("/logs")
async def get_logs(limit: int = 100, level: str = None, keyword: str = None, source: str = None):
    """Get logs with optional filtering"""
    # Load logs
    all_logs = _load_all_logs(limit * 10)  # Load more to account for filtering

    # Apply filters
    filtered_logs = all_logs

    if level:
        filtered_logs = [log for log in filtered_logs if log.get("level", "").lower() == level.lower()]

    if keyword:
        keyword_lower = keyword.lower()
        filtered_logs = [
            log for log in filtered_logs
            if keyword_lower in log.get("message", "").lower() or
               keyword_lower in json.dumps(log.get("details", {})).lower()
        ]

    if source:
        filtered_logs = [log for log in filtered_logs if log.get("source", "").lower() == source.lower()]

    # Sort by timestamp (newest first)
    filtered_logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # Apply limit
    result_logs = filtered_logs[:limit]

    return {"logs": result_logs, "total": len(filtered_logs)}


@router.get("/logs/stats")
async def get_log_stats():
    """Get log statistics"""
    if not LOG_DIR.exists():
        return {"total_files": 0, "total_size": 0, "levels": {}, "sources": {}}

    log_files = list(LOG_DIR.glob("*.jsonl"))
    total_size = sum(f.stat().st_size for f in log_files)

    # Count by level and source
    levels = {}
    sources = {}

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        log_entry = _parse_log_line(line)
                        if log_entry:
                            level = log_entry.get("level", "unknown")
                            source = log_entry.get("source", "unknown")
                            levels[level] = levels.get(level, 0) + 1
                            sources[source] = sources.get(source, 0) + 1
        except Exception:
            continue

    return {
        "total_files": len(log_files),
        "total_size": total_size,
        "levels": levels,
        "sources": sources
    }


@router.get("/logs/files")
async def get_log_files():
    """Get list of log files"""
    if not LOG_DIR.exists():
        return {"files": []}

    files = []
    for log_file in LOG_DIR.glob("*.jsonl"):
        stat = log_file.stat()
        files.append({
            "filename": log_file.name,
            "path": str(log_file),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return {"files": sorted(files, key=lambda x: x["modified"], reverse=True)}
