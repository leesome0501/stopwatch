from __future__ import annotations

from fastapi import HTTPException

from ..db import Conn


def not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what}을(를) 찾을 수 없습니다.")


def require(conn: Conn, table: str, id_: int, what: str) -> dict:
    assert table in {"household", "member", "account", "instrument", "txn", "category"}
    row = conn.execute(f"SELECT * FROM {table} WHERE id = %s", (id_,)).fetchone()
    if row is None:
        raise not_found(what)
    return row
