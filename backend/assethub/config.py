from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "db"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


@dataclass(frozen=True)
class Settings:
    database_url: str
    max_upload_bytes: int = 20 * 1024 * 1024


def load_settings() -> Settings:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 환경변수가 필요합니다. 예: postgresql://localhost/assethub")
    return Settings(database_url=url)
