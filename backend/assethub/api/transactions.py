from __future__ import annotations

import uuid
from datetime import date

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from ..db import Conn, get_conn
from ..importer.parsing import KST
from ..schemas import Txn, TxnIn, TxnPatch
from .accounts import fetch_account
from .common import require

router = APIRouter(tags=["거래"])

_COLS = """id, account_id, occurred_at, trade_date, kind, amount, currency, instrument_id, quantity,
           unit_price, balance_after, fee, tax, category_id, counterparty, description, memo,
           group_id, status"""


def _check_category(conn: Conn, household_id: int, category_id: int | None) -> None:
    if category_id is None:
        return
    ok = conn.execute("SELECT 1 FROM category WHERE id = %s AND (household_id IS NULL OR household_id = %s)",
                      (category_id, household_id)).fetchone()
    if not ok:
        raise HTTPException(422, "이 가구에서 쓸 수 없는 카테고리입니다.")


@router.get("/api/accounts/{account_id}/transactions", response_model=list[Txn])
def list_transactions(account_id: int, date_from: date | None = None, date_to: date | None = None,
                      include_void: bool = False, limit: int = 200, offset: int = 0,
                      conn: Conn = Depends(get_conn)):
    fetch_account(conn, account_id)
    return conn.execute(
        f"""SELECT {_COLS} FROM txn
             WHERE account_id = %s
               AND (%s::date IS NULL OR trade_date >= %s)
               AND (%s::date IS NULL OR trade_date <= %s)
               AND (%s OR status <> 'void')
             ORDER BY occurred_at DESC, id DESC LIMIT %s OFFSET %s""",
        (account_id, date_from, date_from, date_to, date_to, include_void, min(limit, 1000), offset)).fetchall()


@router.post("/api/accounts/{account_id}/transactions", response_model=Txn, status_code=201)
def create_transaction(account_id: int, body: TxnIn, conn: Conn = Depends(get_conn)):
    acc = fetch_account(conn, account_id)
    _check_category(conn, acc["household_id"], body.category_id)
    at = body.occurred_at if body.occurred_at.tzinfo else body.occurred_at.replace(tzinfo=KST)
    try:
        with conn.transaction():
            return conn.execute(
                f"""INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency,
                                     instrument_id, quantity, unit_price, fee, tax, category_id,
                                     counterparty, description, memo, group_id, dedupe_key)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING {_COLS}""",
                (account_id, at, at.astimezone(KST).date(), body.kind, body.amount,
                 (body.currency or acc["base_currency"]).upper(), body.instrument_id, body.quantity,
                 body.unit_price, body.fee, body.tax, body.category_id, body.counterparty,
                 body.description, body.memo, body.group_id, f"manual:{uuid.uuid4()}")).fetchone()
    except psycopg.errors.CheckViolation as e:
        raise HTTPException(422, f"거래 규칙에 맞지 않습니다: {e.diag.constraint_name}") from None
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(422, "없는 종목입니다.") from None


@router.patch("/api/transactions/{txn_id}", response_model=Txn)
def patch_transaction(txn_id: int, body: TxnPatch, conn: Conn = Depends(get_conn)):
    txn = require(conn, "txn", txn_id, "거래")
    changes = body.model_dump(exclude_unset=True)
    if "category_id" in changes:
        hid = fetch_account(conn, txn["account_id"])["household_id"]
        _check_category(conn, hid, changes["category_id"])
    if changes:
        sets = ", ".join(f"{k} = %s" for k in changes)
        conn.execute(f"UPDATE txn SET {sets}, updated_at = now() WHERE id = %s", (*changes.values(), txn_id))
    return conn.execute(f"SELECT {_COLS} FROM txn WHERE id = %s", (txn_id,)).fetchone()


@router.delete("/api/transactions/{txn_id}", status_code=204)
def void_transaction(txn_id: int, conn: Conn = Depends(get_conn)):
    """삭제 대신 무효 처리한다. 원본과 중복 판정 키가 남아 같은 거래가 다시 들어오지 않는다."""
    require(conn, "txn", txn_id, "거래")
    conn.execute("UPDATE txn SET status = 'void', updated_at = now() WHERE id = %s", (txn_id,))
