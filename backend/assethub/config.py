from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
DB_DIR = REPO_ROOT / "db"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
ENV_FILE = BACKEND_DIR / ".env"   # setup 이 만든다. git 에는 올라가지 않는다


@dataclass(frozen=True)
class Settings:
    database_url: str
    max_upload_bytes: int = 20 * 1024 * 1024


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """KEY=VALUE 줄만 읽는 간단한 .env 파서."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_settings() -> Settings:
    """환경변수 DATABASE_URL, 없으면 backend/.env 의 값을 쓴다."""
    url = os.environ.get("DATABASE_URL") or read_env_file().get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 이 없습니다. setup.cmd(Windows)를 먼저 실행하거나 "
                           "환경변수로 지정하세요. 예: postgresql://localhost/assethub")
    return Settings(database_url=url)
