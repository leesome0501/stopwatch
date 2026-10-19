from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from ..db import Conn, get_conn
from ..market.collector import collect, today_kst
from ..market.providers import provider_for
from ..valuation import ACCOUNT_TYPE_LABEL, RANGES, ZERO, Ledger, history_days, pct, won
from .common import require

router = APIRouter(tags=["대시보드·시세"])

STALE_AFTER = timedelta(days=5)


_r = won


@router.get("/api/households/{household_id}/dashboard")
def dashboard(household_id: int, range: str = "1y", conn: Conn = Depends(get_conn)):
    """대시보드 한 화면에 필요한 값을 한 번에 돌려준다 (오늘 기준, KRW)."""
    household = require(conn, "household", household_id, "가구")
    if range not in RANGES and range != "all":
        raise HTTPException(422, f"range 는 {', '.join([*RANGES, 'all'])} 중 하나여야 합니다.")
    today = today_kst()
    ledger = Ledger(conn, household_id)
    first = ledger.first_day() or today
    start = first if range == "all" else max(first, today - timedelta(days=RANGES[range]))
    days = history_days(start, today)
    month_ago = today - timedelta(days=30)
    walk_days = sorted(set(days) | ({month_ago} if month_ago >= first else set()))
    walked = ledger.walk(walk_days)
    by_day = {d: values for d, _, values in walked}
    _, state, now_values = walked[-1]

    def totals(values: dict[int, Decimal]) -> tuple[Decimal, Decimal]:
        return (sum((v for v in values.values() if v > 0), ZERO), sum((v for v in values.values() if v < 0), ZERO))

    assets, liabilities = totals(now_values)
    net = assets + liabilities
    change = None
    if month_ago in by_day:
        before = sum(by_day[month_ago].values(), ZERO)
        change = {"from_date": month_ago, "amount_krw": _r(net - before),
                  "pct": pct((net - before) / abs(before) * 100) if before else None}

    history = []
    for d in days:
        a, l = totals(by_day[d])
        history.append({"date": d, "net_worth_krw": _r(a + l), "assets_krw": _r(a), "liabilities_krw": _r(l)})

    accounts = []
    for aid, acc in ledger.accounts.items():
        if aid not in now_values:
            continue
        rep_days = [s.asof(today)[1] for s in ledger.reported.get(aid, {}).values() if s.asof(today)]
        accounts.append({
            "id": aid, "name": acc["name"], "account_type": acc["account_type"],
            "type_label": ACCOUNT_TYPE_LABEL.get(acc["account_type"], acc["account_type"]),
            "institution": acc["institution"], "valuation_method": acc["valuation_method"],
            "owners": [{"member_id": o["member_id"], "name": o["name"], "share": o["share"]} for o in ledger.owners[aid]],
            "value_krw": _r(now_values[aid]), "reported_as_of": max(rep_days) if rep_days else None,
        })
    accounts.sort(key=lambda a: -abs(a["value_krw"]))

    members: dict[int, dict] = {}
    for a in accounts:
        for o in a["owners"]:
            m = members.setdefault(o["member_id"], {"member_id": o["member_id"], "name": o["name"], "net_worth_krw": ZERO})
            m["net_worth_krw"] += a["value_krw"] * o["share"]
    for m in members.values():
        m["net_worth_krw"] = _r(m["net_worth_krw"])

    holdings = ledger.holdings(state, today)
    stale = []
    for h in holdings:
        inst = ledger.instruments[h.instrument_id]
        auto = provider_for(inst) is not None
        if h.price_basis != "market":
            stale.append({"name": h.name, "reason": "시세 없음 (거래 단가로 평가)" if h.price_basis == "trade" else "시세 없음",
                          "auto": auto})
        elif auto and h.price_date < today - STALE_AFTER:
            stale.append({"name": h.name, "reason": f"{h.price_date} 시세", "auto": auto})
    last_run = conn.execute(
        """SELECT id, started_at, finished_at, status, prices_upserted, fx_upserted, errors
             FROM market_sync_run ORDER BY id DESC LIMIT 1""").fetchone()

    this_month = today.replace(day=1)
    six_months_ago = (this_month - timedelta(days=150)).replace(day=1)
    monthly = conn.execute(
        """SELECT month, sum(amount_krw) FILTER (WHERE kind = 'income') AS income_krw,
                  -sum(amount_krw) FILTER (WHERE kind = 'expense') AS expense_krw
             FROM v_monthly_cashflow WHERE household_id = %s AND month >= %s
            GROUP BY month ORDER BY month""", (household_id, six_months_ago)).fetchall()
    month_map = {r["month"]: r for r in monthly}
    months, m = [], six_months_ago
    while m <= this_month:
        r = month_map.get(m, {})
        months.append({"month": m.strftime("%Y-%m"), "income_krw": r.get("income_krw") or ZERO,
                       "expense_krw": r.get("expense_krw") or ZERO})
        m = (m + timedelta(days=32)).replace(day=1)
    by_category = conn.execute(
        """SELECT top_category AS category, -sum(amount_krw) AS amount_krw FROM v_monthly_cashflow
            WHERE household_id = %s AND month = %s AND kind = 'expense'
            GROUP BY top_category HAVING sum(amount_krw) < 0 ORDER BY 2 DESC""",
        (household_id, this_month)).fetchall()

    return {
        "as_of": today,
        "household": {"id": household["id"], "name": household["name"]},
        "kpi": {"net_worth_krw": _r(net), "assets_krw": _r(assets), "liabilities_krw": _r(liabilities),
                "change_1m": change, "month": months[-1]["month"],
                "month_income_krw": months[-1]["income_krw"], "month_expense_krw": months[-1]["expense_krw"]},
        "history": {"range": range, "points": history},
        "allocation": ledger.allocation(state, today),
        "accounts": accounts,
        "members": sorted(members.values(), key=lambda m: m["member_id"]),
        "holdings": [h.__dict__ for h in holdings],
        "cashflow": {"months": months, "this_month_by_category": by_category},
        "market": {"last_run": last_run, "stale": stale},
    }


@router.post("/api/market/refresh")
def refresh_market(conn: Conn = Depends(get_conn)):
    """시세·환율을 지금 수집한다. 보통은 매일 python -m assethub.collect 로 돌린다."""
    return collect(conn)


@router.get("/api/market/runs")
def market_runs(limit: int = 10, conn: Conn = Depends(get_conn)):
    return conn.execute(
        """SELECT id, started_at, finished_at, status, prices_upserted, fx_upserted, errors
             FROM market_sync_run ORDER BY id DESC LIMIT %s""", (min(limit, 100),)).fetchall()
