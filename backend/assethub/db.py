"""PostgreSQL 연결. 구조는 db/migrations 가 진실의 원천이고, 여기서는 psycopg 로 SQL 을 직접 쓴다."""
from __future__ import annotations

from collections.abc import Iterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


Conn = psycopg.Connection


def utf8(url: str) -> str:
    """한국어 Windows 의 PostgreSQL 은 기본 문자 인코딩이 CP949 일 수 있어 UTF-8 로 고정한다."""
    return psycopg.conninfo.make_conninfo(url, client_encoding="utf8")


def open_pool(url: str) -> ConnectionPool:
    pool = ConnectionPool(utf8(url), kwargs={"row_factory": dict_row}, min_size=1, max_size=10, open=False)
    pool.open(wait=True)
    return pool


def get_conn(request: Request) -> Iterator[Conn]:
    """요청 하나 = 트랜잭션 하나. 예외가 나면 전부 롤백된다."""
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn
