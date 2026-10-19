"""연결된 모든 증권사 계좌를 동기화한다 (collect.cmd 가 시세 수집 뒤에 부른다).

    DATABASE_URL=postgresql:///assethub uv run python -m assethub.sync_brokers
"""
from __future__ import annotations

import json
import sys

import psycopg
from psycopg.rows import dict_row

from .brokers.sync import PROVIDERS, sync_source
from .config import load_settings
from .db import utf8


def main() -> int:
    url = load_settings().database_url
    failed = 0
    with psycopg.connect(utf8(url), row_factory=dict_row, autocommit=True) as conn:
        sources = conn.execute(
            """SELECT id, label FROM data_source WHERE provider = ANY(%s) AND credential_enc IS NOT NULL
                AND status <> 'paused' ORDER BY id""", (list(PROVIDERS),)).fetchall()
        if not sources:
            print("연결된 증권사가 없습니다.")
        for s in sources:
            print(f"== {s['label']}")
            result = sync_source(conn, s["id"], log=lambda m: print("  " + m))
            if result["status"] == "failed":
                failed += 1
                print(f"  실패: {result['error']}")
    print(json.dumps({"connections": len(sources), "failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
