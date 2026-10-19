"""시세·환율을 한 번 수집한다. 매일 장 마감 후 cron 이나 systemd timer 로 돌린다.

    DATABASE_URL=postgresql:///assethub uv run python -m assethub.collect
"""
from __future__ import annotations

import json
import sys

import psycopg
from psycopg.rows import dict_row

from .config import load_settings
from .db import utf8
from .market.collector import collect


def main() -> int:
    settings = load_settings()
    with psycopg.connect(utf8(settings.database_url), row_factory=dict_row, autocommit=True) as conn:
        result = collect(conn)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
