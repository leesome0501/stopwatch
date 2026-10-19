from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response

from ..db import Conn, get_conn
from ..schemas import Account, AccountIn, AccountPatch, OwnerShare, ReportedBalance, ReportedBalanceIn
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


def _check_owners(conn: Conn, household_id: int, owners: list[OwnerShare]) -> None:
    if not owners:
        raise HTTPException(422, "명의자가 한 명 이상 있어야 합니다.")
    total = sum((o.share for o in owners), Decimal(0))
    if abs(total - 1) > Decimal("0.0001"):
        raise HTTPException(422, f"명의 지분 합계가 1이어야 합니다 (현재 {total}).")
    member_ids = [o.member_id for o in owners]
    found = conn.execute("SELECT count(*) AS n FROM member WHERE household_id = %s AND id = ANY(%s)",
                         (household_id, member_ids)).fetchone()["n"]
    if found != len(set(member_ids)) or len(set(member_ids)) != len(member_ids):
        raise HTTPException(422, "명의자는 이 가구의 구성원이어야 하고 중복되면 안 됩니다.")


def _institution_id(conn: Conn, code: str | None) -> int | None:
    if not code:
        return None
    inst = conn.execute("SELECT id FROM institution WHERE code = %s", (code,)).fetchone()
    if inst is None:
        raise HTTPException(422, f"모르는 기관 코드입니다: {code}")
    return inst["id"]


@router.get("/api/households/{household_id}/accounts", response_model=list[Account])
def list_accounts(household_id: int, include_closed: bool = False, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    where = "" if include_closed else " AND a.closed_on IS NULL"
    return conn.execute(_SELECT + f" WHERE a.household_id = %s{where} ORDER BY a.id", (household_id,)).fetchall()


@router.post("/api/households/{household_id}/accounts", response_model=Account, status_code=201)
def create_account(household_id: int, body: AccountIn, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    _check_owners(conn, household_id, body.owners)
    inst_id = _institution_id(conn, body.institution_code)
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
    if "name" in changes and changes["name"] is None:
        del changes["name"]
    if "institution_code" in changes:
        changes["institution_id"] = _institution_id(conn, changes.pop("institution_code"))
    if changes:
        sets = ", ".join(f"{k} = %s" for k in changes)
        conn.execute(f"UPDATE account SET {sets}, updated_at = now() WHERE id = %s",
                     (*changes.values(), account_id))
    return fetch_account(conn, account_id)


@router.put("/api/accounts/{account_id}/owners", response_model=Account)
def set_owners(account_id: int, body: list[OwnerShare], conn: Conn = Depends(get_conn)):
    acc = fetch_account(conn, account_id)
    _check_owners(conn, acc["household_id"], body)
    conn.execute("DELETE FROM account_owner WHERE account_id = %s", (account_id,))
    for o in body:
        conn.execute("INSERT INTO account_owner (account_id, member_id, share) VALUES (%s,%s,%s)",
                     (account_id, o.member_id, o.share))
    return fetch_account(conn, account_id)


@router.delete("/api/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, conn: Conn = Depends(get_conn)):
    """거래·평가액·업로드 기록이 하나도 없는 계좌만 지운다. 쓰던 계좌는 '마감'(closed_on)으로 처리한다."""
    fetch_account(conn, account_id)
    used = conn.execute(
        """SELECT EXISTS (SELECT 1 FROM txn WHERE account_id = %(a)s)
               OR EXISTS (SELECT 1 FROM reported_balance WHERE account_id = %(a)s)
               OR EXISTS (SELECT 1 FROM import_batch WHERE account_id = %(a)s) AS used""",
        {"a": account_id}).fetchone()["used"]
    if used:
        raise HTTPException(409, "거래나 평가 기록이 있는 계좌는 지울 수 없습니다. 대신 마감 처리하세요.")
    conn.execute("DELETE FROM account WHERE id = %s", (account_id,))
    return Response(status_code=204)


@router.get("/api/accounts/{account_id}/reported-balances", response_model=list[ReportedBalance])
def list_reported(account_id: int, conn: Conn = Depends(get_conn)):
    fetch_account(conn, account_id)
    return conn.execute("""SELECT as_of, currency, total_value, cash_amount FROM reported_balance
                            WHERE account_id = %s ORDER BY as_of DESC, currency""", (account_id,)).fetchall()


@router.put("/api/accounts/{account_id}/reported-balances", response_model=list[ReportedBalance])
def put_reported(account_id: int, body: list[ReportedBalanceIn], conn: Conn = Depends(get_conn)):
    """보험 해지환급금, 연금 평가액처럼 기관이 알려준 잔액. 같은 날짜·통화는 덮어쓴다."""
    fetch_account(conn, account_id)
    for b in body:
        conn.execute(
            """INSERT INTO reported_balance (account_id, as_of, currency, total_value, cash_amount)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (account_id, as_of, currency)
               DO UPDATE SET total_value = EXCLUDED.total_value, cash_amount = EXCLUDED.cash_amount""",
            (account_id, b.as_of, b.currency.upper(), b.total_value, b.cash_amount))
    return list_reported(account_id, conn)


@router.delete("/api/accounts/{account_id}/reported-balances/{as_of}", status_code=204)
def delete_reported(account_id: int, as_of: str, currency: str = "KRW", conn: Conn = Depends(get_conn)):
    fetch_account(conn, account_id)
    conn.execute("DELETE FROM reported_balance WHERE account_id = %s AND as_of = %s::date AND currency = %s",
                 (account_id, as_of, currency.upper()))
    return Response(status_code=204)
