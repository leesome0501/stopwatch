"""평가 엔진: 거래·시세·환율로 임의의 날짜 기준 계좌 평가액, 보유 종목, 자산 구성을 계산한다.

SQL 뷰(v_account_value)는 '오늘' 한 시점만 계산한다. 순자산 추이처럼 여러 날짜가 필요하면
거래를 날짜순으로 한 번 훑으며 이 엔진이 계산한다. 두 계산은 테스트로 같은 값을 내는지 확인한다.

규칙
  * 그날 시세가 없으면 직전 시세, 직전 시세도 없으면 마지막 거래 단가로 평가한다.
  * 그날 환율이 없으면 직전 환율, 그것도 없으면 가장 이른 환율을 쓴다.
  * 매입 원가는 이동평균법. 매도·출고 시 수량 비율만큼 원가를 덜어낸다.
    원화 원가는 매수일 환율로 고정해, 해외주식 수익률에 환율 효과가 포함된다.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .db import Conn

ZERO = Decimal(0)


def won(v: Decimal) -> Decimal:
    """원 단위 반올림 (PostgreSQL round() 와 같은 사사오입)."""
    return v.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def pct(v: Decimal, places: str = "0.01") -> Decimal:
    return v.quantize(Decimal(places), rounding=ROUND_HALF_UP)

CLASS_ORDER = ["현금성", "주식", "채권", "부동산", "가상자산", "보험·연금", "원자재", "기타"]
ASSET_CLASS_LABEL = {"equity": "주식", "bond": "채권", "cash_equiv": "현금성", "commodity": "원자재",
                     "crypto": "가상자산", "real_estate": "부동산", "alternative": "기타", "mixed": "기타"}
REPORTED_CLASS = {"insurance": "보험·연금", "irp": "보험·연금", "dc_pension": "보험·연금",
                  "pension_savings": "보험·연금"}
ACCOUNT_TYPE_LABEL = {
    "checking": "입출금", "savings": "예금", "time_deposit": "정기예금", "installment_savings": "적금",
    "cma": "CMA", "brokerage": "위탁", "isa": "ISA", "pension_savings": "연금저축", "irp": "IRP",
    "dc_pension": "퇴직연금", "crypto": "가상자산", "credit_card": "신용카드", "loan": "대출",
    "insurance": "보험", "real_asset": "실물자산", "cash": "현금", "other": "기타",
}


class Series:
    """날짜순 값. asof(d) = d 이전 마지막 값."""

    def __init__(self, rows: list[tuple[date, Decimal]]):
        rows = sorted(rows)
        self.days = [d for d, _ in rows]
        self.values = [v for _, v in rows]

    def asof(self, d: date) -> tuple[Decimal, date] | None:
        i = bisect_right(self.days, d)
        return (self.values[i - 1], self.days[i - 1]) if i else None

    def first(self) -> Decimal | None:
        return self.values[0] if self.values else None


@dataclass
class Position:
    quantity: Decimal = ZERO
    cost: Decimal = ZERO        # 종목 통화
    cost_krw: Decimal = ZERO    # 매수일 환율 기준


@dataclass
class State:
    cash: dict[tuple[int, str], Decimal] = field(default_factory=lambda: defaultdict(lambda: ZERO))
    pos: dict[tuple[int, int], Position] = field(default_factory=lambda: defaultdict(Position))
    last_trade_price: dict[int, Decimal] = field(default_factory=dict)


@dataclass
class Holding:
    account_id: int
    account_name: str
    instrument_id: int
    name: str
    symbol: str | None
    market: str | None
    currency: str
    asset_class: str
    quantity: Decimal
    avg_cost: Decimal | None
    cost_krw: Decimal
    price: Decimal | None
    price_date: date | None
    price_basis: str            # market | trade | none
    value_krw: Decimal
    pnl_krw: Decimal | None
    pnl_pct: Decimal | None


class Ledger:
    def __init__(self, conn: Conn, household_id: int):
        self.household_id = household_id
        accts = conn.execute(
            """SELECT a.id, a.name, a.account_type, a.valuation_method, a.closed_on, a.base_currency,
                      i.name AS institution
                 FROM account a LEFT JOIN institution i ON i.id = a.institution_id
                WHERE a.household_id = %s ORDER BY a.id""", (household_id,)).fetchall()
        self.accounts = {a["id"]: a for a in accts}
        self.owners: dict[int, list[dict]] = defaultdict(list)
        for o in conn.execute(
                """SELECT o.account_id, o.member_id, o.share, m.name FROM account_owner o
                     JOIN member m ON m.id = o.member_id WHERE m.household_id = %s
                    ORDER BY o.account_id, o.member_id""", (household_id,)).fetchall():
            self.owners[o["account_id"]].append(o)
        self.txns = conn.execute(
            """SELECT t.id, t.account_id, t.trade_date, t.kind, t.amount, t.currency, t.instrument_id,
                      t.quantity, t.unit_price, t.fee, t.tax
                 FROM txn t JOIN account a ON a.id = t.account_id
                WHERE a.household_id = %s AND t.status = 'posted'
                ORDER BY t.trade_date, t.occurred_at, t.id""", (household_id,)).fetchall()
        inst_ids = sorted({t["instrument_id"] for t in self.txns if t["instrument_id"]})
        self.instruments = {i["id"]: i for i in conn.execute(
            "SELECT id, name, symbol, market, currency, asset_class, kind FROM instrument WHERE id = ANY(%s)",
            (inst_ids,)).fetchall()}
        prices: dict[int, list] = defaultdict(list)
        for p in conn.execute("SELECT instrument_id, price_date, close FROM price WHERE instrument_id = ANY(%s)",
                              (inst_ids,)).fetchall():
            prices[p["instrument_id"]].append((p["price_date"], p["close"]))
        self.prices = {k: Series(v) for k, v in prices.items()}
        fx: dict[str, list] = defaultdict(list)
        for r in conn.execute("SELECT currency, rate_date, krw_rate FROM fx_rate").fetchall():
            fx[r["currency"]].append((r["rate_date"], r["krw_rate"]))
        self.fx = {k: Series(v) for k, v in fx.items()}
        rep: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for r in conn.execute(
                """SELECT rb.account_id, rb.as_of, rb.currency, rb.total_value FROM reported_balance rb
                     JOIN account a ON a.id = rb.account_id WHERE a.household_id = %s""",
                (household_id,)).fetchall():
            rep[r["account_id"]][r["currency"]].append((r["as_of"], r["total_value"]))
        self.reported = {a: {c: Series(v) for c, v in cur.items()} for a, cur in rep.items()}

    # ------------------------------------------------------------ 환율·시세
    def fx_rate(self, currency: str, day: date) -> Decimal:
        if currency == "KRW":
            return Decimal(1)
        s = self.fx.get(currency)
        if s is None:
            return ZERO   # 환율을 모르면 평가하지 않는다 (수집 전)
        hit = s.asof(day)
        return hit[0] if hit else s.first()

    def price(self, state: State, instrument_id: int, day: date) -> tuple[Decimal | None, date | None, str]:
        s = self.prices.get(instrument_id)
        hit = s.asof(day) if s else None
        if hit:
            return hit[0], hit[1], "market"
        if instrument_id in state.last_trade_price:
            return state.last_trade_price[instrument_id], None, "trade"
        return None, None, "none"

    # ------------------------------------------------------------ 거래 반영
    def apply(self, state: State, t: dict) -> None:
        state.cash[(t["account_id"], t["currency"])] += t["amount"]
        inst_id, q = t["instrument_id"], t["quantity"]
        if not inst_id or q is None:
            return
        inst = self.instruments[inst_id]
        key = (t["account_id"], inst_id)
        p = state.pos[key]
        if t["unit_price"] is not None:
            state.last_trade_price[inst_id] = t["unit_price"]
        if t["kind"] == "split":
            p.quantity += q
            return
        if q > 0:
            same_ccy = t["currency"] == inst["currency"]
            if t["unit_price"] is not None:
                base = q * t["unit_price"] + ((t["fee"] + t["tax"]) if same_ccy else ZERO)
            else:
                base = -t["amount"] if same_ccy and t["amount"] < 0 else ZERO
            p.cost += base
            p.cost_krw += base * self.fx_rate(inst["currency"], t["trade_date"])
        elif q < 0 and p.quantity > 0:
            ratio = min(-q / p.quantity, Decimal(1))
            p.cost -= p.cost * ratio
            p.cost_krw -= p.cost_krw * ratio
        p.quantity += q
        if p.quantity == 0:
            p.cost = p.cost_krw = ZERO

    # ------------------------------------------------------------ 평가
    def account_value(self, state: State, account_id: int, day: date) -> Decimal:
        acc = self.accounts[account_id]
        if acc["valuation_method"] == "reported":
            total = ZERO
            for cur, s in self.reported.get(account_id, {}).items():
                hit = s.asof(day)
                if hit:
                    total += hit[0] * self.fx_rate(cur, day)
            return total
        total = ZERO
        for (aid, cur), bal in state.cash.items():
            if aid == account_id and bal:
                total += bal * self.fx_rate(cur, day)
        for (aid, iid), p in state.pos.items():
            if aid == account_id and p.quantity:
                price, _, _ = self.price(state, iid, day)
                if price is not None:
                    total += p.quantity * price * self.fx_rate(self.instruments[iid]["currency"], day)
        return total

    def _open_on(self, account_id: int, day: date) -> bool:
        closed = self.accounts[account_id]["closed_on"]
        return closed is None or day < closed

    def walk(self, days: list[date]) -> list[tuple[date, State, dict[int, Decimal]]]:
        """날짜들(오름차순) 각각의 상태와 계좌별 평가액."""
        state, i, out = State(), 0, []
        for d in days:
            while i < len(self.txns) and self.txns[i]["trade_date"] <= d:
                self.apply(state, self.txns[i])
                i += 1
            values = {aid: self.account_value(state, aid, d) for aid in self.accounts if self._open_on(aid, d)}
            out.append((d, state, values))
        return out

    def first_day(self) -> date | None:
        days = [t["trade_date"] for t in self.txns[:1]]
        for cur in self.reported.values():
            days += [s.days[0] for s in cur.values() if s.days]
        return min(days) if days else None

    # ------------------------------------------------------------ 현재 시점 세부
    def holdings(self, state: State, day: date) -> list[Holding]:
        out = []
        for (aid, iid), p in state.pos.items():
            if not p.quantity or not self._open_on(aid, day):
                continue
            inst = self.instruments[iid]
            price, price_day, basis = self.price(state, iid, day)
            fx = self.fx_rate(inst["currency"], day)
            value = p.quantity * price * fx if price is not None else ZERO
            pnl = value - p.cost_krw if p.cost_krw and price is not None else None
            out.append(Holding(
                account_id=aid, account_name=self.accounts[aid]["name"], instrument_id=iid, name=inst["name"],
                symbol=inst["symbol"], market=inst["market"], currency=inst["currency"],
                asset_class=ASSET_CLASS_LABEL.get(inst["asset_class"], "기타"), quantity=p.quantity,
                avg_cost=(p.cost / p.quantity) if p.cost and p.quantity > 0 else None,
                cost_krw=won(p.cost_krw), price=price, price_date=price_day, price_basis=basis,
                value_krw=won(value),
                pnl_krw=won(pnl) if pnl is not None else None,
                pnl_pct=pct(pnl / p.cost_krw * 100) if pnl is not None else None))
        return sorted(out, key=lambda h: -h.value_krw)

    def allocation(self, state: State, day: date) -> list[dict]:
        buckets: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for aid, acc in self.accounts.items():
            if not self._open_on(aid, day):
                continue
            if acc["valuation_method"] == "reported":
                v = self.account_value(state, aid, day)
                if v > 0:
                    buckets[REPORTED_CLASS.get(acc["account_type"], "기타")] += v
                continue
            for (a, cur), bal in state.cash.items():
                if a == aid and bal > 0:
                    buckets["현금성"] += bal * self.fx_rate(cur, day)
        for h in self.holdings(state, day):
            if h.value_krw > 0:
                buckets[h.asset_class] += h.value_krw
        total = sum(buckets.values(), ZERO)
        return [{"asset_class": c, "value_krw": won(buckets[c]),
                 "share": pct(buckets[c] / total * 100) if total else ZERO}
                for c in CLASS_ORDER if buckets.get(c)]


RANGES = {"1m": 30, "3m": 91, "6m": 182, "1y": 365, "3y": 365 * 3}
MAX_POINTS = 400


def history_days(start: date, end: date) -> list[date]:
    n = (end - start).days
    if n < 0:
        return [end]
    step = max(1, -(-n // MAX_POINTS))
    days = [start + timedelta(days=i) for i in range(0, n + 1, step)]
    if days[-1] != end:
        days.append(end)
    return days
