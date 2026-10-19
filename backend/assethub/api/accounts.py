from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from ..db import Conn, get_conn
from ..schemas import Account, AccountIn, AccountPatch
from .common import not_found, require

router = APIRouter(tags=["계좌"])

_SELECT = """
SELECT a.*, i.code AS institution_code, i.name AS institution_name,
       coalesce((SELECT json_agg(json_build_object('member_id', o.member_id, 'share', o.share)
                                 ORDER BY o.member_id)
                   FROM account_owner o WHERE o.account_id = a.id), '[]') AS owners
  FROM account a LEFT JOIN institution i ON i.id = a.institution_id
"""


def fetch_account(conn: Conn, account_id: int) -> dict:
    row = conn.execute(_SELECT + " WHERE a.id = %s", (account_id,)).fetchone()
    if row is None:
        raise not_found("계좌")
    return row


@router.get("/api/households/{household_id}/accounts", response_model=list[Account])
def list_accounts(household_id: int, include_closed: bool = False, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    where = "" if include_closed else " AND a.closed_on IS NULL"
    return conn.execute(_SELECT + f" WHERE a.household_id = %s{where} ORDER BY a.id", (household_id,)).fetchall()


@router.post("/api/households/{household_id}/accounts", response_model=Account, status_code=201)
def create_account(household_id: int, body: AccountIn, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    total = sum((o.share for o in body.owners), Decimal(0))
    if abs(total - 1) > Decimal("0.0001"):
        raise HTTPException(422, f"명의 지분 합계가 1이어야 합니다 (현재 {total}).")
    member_ids = [o.member_id for o in body.owners]
    found = conn.execute("SELECT count(*) AS n FROM member WHERE household_id = %s AND id = ANY(%s)",
                         (household_id, member_ids)).fetchone()["n"]
    if found != len(set(member_ids)) or len(set(member_ids)) != len(member_ids):
        raise HTTPException(422, "명의자는 이 가구의 구성원이어야 하고 중복되면 안 됩니다.")
    inst_id = None
    if body.institution_code:
        inst = conn.execute("SELECT id FROM institution WHERE code = %s", (body.institution_code,)).fetchone()
        if inst is None:
            raise HTTPException(422, f"모르는 기관 코드입니다: {body.institution_code}")
        inst_id = inst["id"]
    acc_id = conn.execute(
        """INSERT INTO account (household_id, institution_id, name, account_type, valuation_method,
                                base_currency, account_number_masked, visibility, opened_on,
                                maturity_on, interest_rate, memo)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (household_id, inst_id, body.name, body.account_type, body.valuation_method,
         body.base_currency.upper(), body.account_number_masked, body.visibility, body.opened_on,
         body.maturity_on, body.interest_rate, body.memo)).fetchone()["id"]
    for o in body.owners:
        conn.execute("INSERT INTO account_owner (account_id, member_id, share) VALUES (%s,%s,%s)",
                     (acc_id, o.member_id, o.share))
    return fetch_account(conn, acc_id)


@router.get("/api/accounts/{account_id}", response_model=Account)
def get_account(account_id: int, conn: Conn = Depends(get_conn)):
    return fetch_account(conn, account_id)


@router.patch("/api/accounts/{account_id}", response_model=Account)
def patch_account(account_id: int, body: AccountPatch, conn: Conn = Depends(get_conn)):
    fetch_account(conn, account_id)
    changes = body.model_dump(exclude_unset=True)
    if changes:
        sets = ", ".join(f"{k} = %s" for k in changes)
        conn.execute(f"UPDATE account SET {sets}, updated_at = now() WHERE id = %s",
                     (*changes.values(), account_id))
    return fetch_account(conn, account_id)
