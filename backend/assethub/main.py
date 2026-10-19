"""AssetHub API.

    DATABASE_URL=postgresql:///assethub uv run uvicorn assethub.main:app --reload

인증은 아직 없다. 집 안 네트워크나 VPN 뒤에서만 띄울 것.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import accounts, households, imports, market, reports, transactions
from .config import Settings, load_settings
from .db import open_pool


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = settings or load_settings()
        app.state.settings = s
        app.state.pool = open_pool(s.database_url)
        try:
            yield
        finally:
            app.state.pool.close()

    app = FastAPI(title="AssetHub", version="0.1.0", lifespan=lifespan)

    @app.get("/health", tags=["상태"])
    def health():
        with app.state.pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    for module in (households, accounts, market, transactions, reports, imports):
        app.include_router(module.router)
    return app


def __getattr__(name: str):
    # `uvicorn assethub.main:app` 에서만 앱을 만든다 (import 만으로 DATABASE_URL 을 요구하지 않게)
    if name == "app":
        return create_app()
    raise AttributeError(name)
