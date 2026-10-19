"""PostgreSQL 연결. SQL 은 db/schema.sql 이 진실의 원천이고, 여기서는 psycopg 로 직접 쓴다."""
from __future__ import annotations

from collections.abc import Iterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DB_DIR

Conn = psycopg.Connection


def open_pool(url: str) -> ConnectionPool:
    pool = ConnectionPool(url, kwargs={"row_factory": dict_row}, min_size=1, max_size=10, open=False)
    pool.open(wait=True)
    return pool


def get_conn(request: Request) -> Iterator[Conn]:
    """요청 하나 = 트랜잭션 하나. 예외가 나면 전부 롤백된다."""
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn


def apply_schema(conn: Conn, *, with_seed: bool = True) -> None:
    """빈 DB에 스키마(와 기본 데이터)를 올린다. 개발·테스트용."""
    for name in ("schema.sql", "seed.sql") if with_seed else ("schema.sql",):
        sql = (DB_DIR / name).read_text(encoding="utf-8")
        # 파일 안의 BEGIN/COMMIT 은 바깥 트랜잭션과 충돌하므로 autocommit 으로 실행
        conn.execute(sql)
