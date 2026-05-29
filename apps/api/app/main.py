"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

configure_logging("DEBUG" if settings.DEBUG else "INFO")


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
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SecureHeadersMiddleware)
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
