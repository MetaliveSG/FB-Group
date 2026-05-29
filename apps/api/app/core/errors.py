"""Domain exceptions + FastAPI handlers (structured, no internal leakage)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, log_with_context

logger = get_logger("app.errors")


class AppError(Exception):
    """Base domain error -> mapped to an HTTP response."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(req: Request, exc: AppError):
        # Client errors (4xx) log at WARNING; server errors (5xx) at ERROR. Either
        # way the business code + path is captured — the gap that made 4xx invisible.
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        log_with_context(logger, level, "app_error",
                         code=exc.code, status=exc.status_code,
                         method=req.method, path=req.url.path, detail=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def _unhandled(req: Request, exc: Exception):  # pragma: no cover - safety net
        log_with_context(logger, logging.ERROR, "unhandled_error",
                         method=req.method, path=req.url.path,
                         error=type(exc).__name__)
        logger.exception("unhandled_error_trace")  # full traceback into the log file
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error"}},
        )
