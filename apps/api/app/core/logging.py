"""Structured JSON logging — file + console, UTC, secret-redacted, context-rich.

Follows the MMQRDepositBot logging method (common/cloudwatch_logger.py + common/log.py):
a daily-rotating file handler kept on disk for after-the-fact debugging
(``mac_logs/`` on macOS dev, ``logs/`` in Docker/Linux), a console handler captured
by ``docker-compose logs`` / journald, UTC timestamps, secret redaction on every
record, and a ``log_with_context()`` helper that tags the caller + key=value context.

Deliberate deviation from MMQR: FB Group keeps JSON output instead of MMQR's plain
``[caller] msg | k=v`` line, because the existing call-sites already log via
``extra={"extra": {...}}`` and JSON is the CloudWatch/OTel-friendly format the docs
promise. The *behaviours* (rotating file + console + UTC + redaction + context) match.
The AWS/watchtower handler is omitted — in prod a CloudWatch agent tails the log file
(MMQR's own UAT/PROD mode), so no in-process AWS dependency is needed.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import platform
import re
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler

# ── Secret redaction (ported from MMQRDepositBot common/log.py) ──────────────
# Scrubs sensitive values from every emitted record so JWTs / passwords / API keys
# never land in a log file or console line.
_SECRET_PATTERNS = [
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),         # JWTs
    re.compile(r"(?i)(authorization)\b[\"']?\s*[:=]\s*[\"']?(bearer\s+)?\S+"),    # auth headers
    re.compile(r"(?i)(pwd|password)\b[\"']?\s*[:=]\s*[\"']?[^\"'\s;,}]+"),        # passwords
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),                                  # long secrets/keys
]


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class JsonFormatter(logging.Formatter):
    """UTC, JSON, secret-redacted. Renders structured extras passed as
    ``logger.info(msg, extra={"extra": {...}})``."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return _redact(json.dumps(payload, default=str))


def _log_dir() -> str:
    """``mac_logs/`` on macOS dev, ``logs/`` on Linux/Docker (mirrors MMQRDepositBot)."""
    api_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # apps/api
    sub = "mac_logs" if platform.system() == "Darwin" else "logs"
    path = os.path.join(api_root, sub)
    os.makedirs(path, exist_ok=True)
    return path


def configure_logging(level: str = "INFO", service_name: str = "api") -> None:
    """Console + daily-rotating file (7-day retention), UTC, secret-redacted.

    The file handler is the MMQR-style persisted log (survives across runs, rotated
    at midnight UTC). If the log directory is unwritable (e.g. a read-only mount) we
    fall back to console-only rather than crashing the boot.
    """
    fmt = JsonFormatter()
    handlers: list[logging.Handler] = []

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    handlers.append(console)

    log_path = None
    try:
        log_path = os.path.join(_log_dir(), f"{service_name}.log")
        file_handler = TimedRotatingFileHandler(
            log_path, when="midnight", interval=1, backupCount=7,
            encoding="utf-8", utc=True,
        )
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    except OSError as exc:  # unwritable mount → console-only, don't take the API down
        print(f"[logging] file handler disabled ({exc})", file=sys.stderr)

    root = logging.getLogger()
    root.handlers = handlers
    root.setLevel(level)

    get_logger("app.startup").info("logging_configured", extra={"extra": {
        "service": service_name, "level": level,
        "file": log_path, "platform": platform.system()}})


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context: object) -> None:
    """MMQRDepositBot-style contextual log: tags the calling function + key=value
    context. Emitted into the JSON ``extra`` so it stays machine-parseable.

        log_with_context(logger, logging.INFO, "Order paid", order_id="T1", amount=9.9)
    """
    caller = inspect.stack()[1].function
    logger.log(level, message, extra={"extra": {"caller": caller, **context}})
