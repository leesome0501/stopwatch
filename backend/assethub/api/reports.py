from __future__ import annotations

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from ..db import Conn, get_conn
from .common import require

router = APIRouter(tags=["현황"])


@router.get("/api/households/{household_id}/summary")
def summary(household_id: int, conn: Conn = Depends(get_conn)):
    """순자산, 계좌별 평가액, 구성원별 순자산 (오늘 기준, KRW)."""
    require(conn, "household", household_id, "가구")
    nw = conn.execute("SELECT * FROM v_net_worth WHERE household_id = %s", (household_id,)).fetchone()
    accounts = conn.execute(
        """SELECT account_id, name, account_type, valuation_method, cash_krw, holdings_krw, value_krw,
                  reported_as_of
             FROM v_account_value WHERE household_id = %s ORDER BY value_krw DESC NULLS LAST""",
        (household_id,)).fetchall()
    members = conn.execute(
        "SELECT member_id, name, net_worth_krw FROM v_member_net_worth WHERE household_id = %s ORDER BY member_id",
        (household_id,)).fetchall()
    zero = Decimal(0)
    return {
        "assets_krw": (nw or {}).get("assets_krw") or zero,
        "liabilities_krw": (nw or {}).get("liabilities_krw") or zero,
        "net_worth_krw": (nw or {}).get("net_worth_krw") or zero,
        "accounts": accounts,
        "members": members,
    }


@router.get("/api/households/{household_id}/cashflow")
def cashflow(household_id: int, month: str, conn: Conn = Depends(get_conn)):
    """한 달 수입·지출 (상위 카테고리별, 내부이체 제외). month = 'YYYY-MM'."""
    require(conn, "household", household_id, "가구")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(422, "month 는 YYYY-MM 형식이어야 합니다.")
    rows = conn.execute(
        """SELECT kind, top_category, amount_krw FROM v_monthly_cashflow
            WHERE household_id = %s AND month = %s::date ORDER BY kind, amount_krw""",
        (household_id, f"{month}-01")).fetchall()
    income = sum((r["amount_krw"] for r in rows if r["kind"] == "income"), Decimal(0))
    expense = sum((r["amount_krw"] for r in rows if r["kind"] == "expense"), Decimal(0))
    return {"month": month, "income_krw": income, "expense_krw": expense,
            "net_krw": income + expense, "by_category": rows}


@router.get("/api/households/{household_id}/unmatched-transfers")
def unmatched_transfers(household_id: int, conn: Conn = Depends(get_conn)):
    """이체로 분류됐는데 짝이 없거나 금액이 안 맞는 거래 (점검 화면용)."""
    require(conn, "household", household_id, "가구")
    return conn.execute(
        """SELECT u.id, u.account_id, u.trade_date, u.amount, u.currency, u.description, u.group_id
             FROM v_unmatched_transfer u JOIN account a ON a.id = u.account_id
            WHERE a.household_id = %s ORDER BY u.trade_date DESC""",
        (household_id,)).fetchall()
