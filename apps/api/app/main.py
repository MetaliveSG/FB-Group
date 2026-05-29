"""FastAPI application factory."""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger, log_with_context

configure_logging("DEBUG" if settings.DEBUG else "INFO")

_request_logger = get_logger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One structured access line per request — method, path, status, duration.
    INFO for 2xx/3xx, WARNING for 4xx, ERROR for 5xx, so every failed request is
    captured (not just unhandled 500s). Unhandled exceptions are logged then
    re-raised for the framework's 500 handler to form the response."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            dur_ms = round((time.perf_counter() - start) * 1000, 1)
            log_with_context(_request_logger, logging.ERROR, "request",
                             method=request.method, path=request.url.path,
                             status=500, duration_ms=dur_ms)
            raise
        dur_ms = round((time.perf_counter() - start) * 1000, 1)
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        log_with_context(_request_logger, level, "request",
                         method=request.method, path=request.url.path,
                         status=response.status_code, duration_ms=dur_ms)
        return response


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Singapore F&B CRM / QR ordering / loyalty platform (PoC).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        # Also accept any private-LAN origin (any port) so a phone on the same wifi
        # can reach the app via the host's LAN IP (e.g. http://192.168.1.5:3001) or
        # its Bonjour/mDNS name (e.g. http://samuels-macbook-air.local:3001).
        allow_origin_regex=(
            r"http://(localhost|127\.0\.0\.1|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
            r"[A-Za-z0-9-]+\.local)(:\d+)?"
        ),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SecureHeadersMiddleware)
    # Added last → outermost user middleware: wraps the others, sees the final
    # status of 4xx responses, and catches unhandled exceptions on the way out.
    app.add_middleware(RequestLoggingMiddleware)
    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "service": settings.APP_NAME, "env": settings.ENV}

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    from app.api.routes import (
        admin, auth, campaigns, catalog, crm, menu_admin, orders, org, platform, qr, reports, rewards,
    )

    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(qr.router, prefix=prefix)
    app.include_router(catalog.router, prefix=prefix)
    app.include_router(orders.router, prefix=prefix)
    app.include_router(crm.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    app.include_router(rewards.router, prefix=prefix)
    app.include_router(platform.router, prefix=prefix)
    app.include_router(campaigns.router, prefix=prefix)
    app.include_router(menu_admin.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(org.router, prefix=prefix)


app = create_app()
