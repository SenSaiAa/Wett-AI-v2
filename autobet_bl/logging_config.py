"""Logging configuration utilities for AutoBet BL."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from .config import AutoBetConfig


class JsonLinesHandler(logging.Handler):
    """Logging handler that writes structured records to JSONL files."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - logging path
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if isinstance(record.args, dict):
            log_entry.update(record.args)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def configure_logging(config: AutoBetConfig) -> None:
    """Configure standard and JSONL logging sinks."""

    config.logging.log_dir.mkdir(parents=True, exist_ok=True)
    config.logging.jsonl_dir.mkdir(parents=True, exist_ok=True)

    log_file = config.logging.log_dir / "autobet.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count,
        encoding="utf-8",
    )

    jsonl_handler = JsonLinesHandler(config.logging.jsonl_dir / "predictions.jsonl")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[handler, jsonl_handler, logging.StreamHandler()],
    )


__all__ = ["configure_logging", "JsonLinesHandler"]
