"""평가 엔진이 SQL 뷰(db/tests.sql 로 손계산 검증됨)와 같은 값을 내는지, 그리고 대시보드 API."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from assethub.config import DB_DIR
from assethub.valuation import Ledger, history_days

D = Decimal


@pytest.fixture
def sample(conn):
    conn.execute((DB_DIR / "sample.sql").read_text(encoding="utf-8"))
    return conn.execute("SELECT id FROM household WHERE name = '우리집'").fetchone()["id"]


def test_engine_matches_sql_views(conn, sample):
    ledger = Ledger(conn, sample)
    today = date.today()
    _, state, values = ledger.walk([today])[0]
    sql = {r["account_id"]: r["value_krw"] for r in conn.execute(
        "SELECT account_id, value_krw FROM v_account_value WHERE household_id = %s", (sample,)).fetchall()}
    assert {k: v.quantize(D(1)) for k, v in values.items()} == sql
    assert sum(values.values()).quantize(D(1)) == D(729405010)


def test_holdings_cost_and_pnl(conn, sample):
    ledger = Ledger(conn, sample)
    _, state, _ = ledger.walk([date.today()])[0]
    h = {x.name: x for x in ledger.holdings(state, date.today())}
    sam = h["삼성전자"]
    assert sam.quantity == 20 and sam.avg_cost == D("60007.5")       # (1,200,000 + 수수료 150) / 20
    assert sam.value_krw == D(1400000) and sam.pnl_krw == D(1400000 - 1200150)
    aapl = h["Apple"]
    assert aapl.avg_cost == D("200.25")                                # (800 + 1) / 4
    assert aapl.cost_krw == D(round(801 * 1390))                       # 매수일 환율
    assert aapl.value_krw == D(4 * 220 * 1400)
    apt = h["우리집 아파트 84㎡"]
    assert apt.price_basis == "market" and apt.pnl_krw == D(200000000)


def test_moving_average_on_partial_sell(conn, sample):
    acc = conn.execute("SELECT id FROM account WHERE name = '한투 위탁'").fetchone()["id"]
    sam = conn.execute("SELECT id FROM instrument WHERE name = '삼성전자'").fetchone()["id"]
    conn.execute("""INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency, instrument_id,
                                     quantity, unit_price, fee, dedupe_key)
                    VALUES (%s, '2026-10-16 10:00+09', '2026-10-16', 'sell', 349900, 'KRW', %s, -5, 70000, 100, 't-sell')""",
                 (acc, sam))
    ledger = Ledger(conn, sample)
    _, state, _ = ledger.walk([date.today()])[0]
    h = next(x for x in ledger.holdings(state, date.today()) if x.name == "삼성전자")
    assert h.quantity == 15 and h.avg_cost == D("60007.5")   # 이동평균은 매도로 바뀌지 않는다
    assert h.cost_krw == D(900113)                            # 1,200,150 × 15/20 (반올림)


def test_history_and_closing(conn, sample):
    ledger = Ledger(conn, sample)
    walked = ledger.walk([date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 15)])
    sums = [sum(v.values()) for _, _, v in walked]
    assert sums[0] == 0                       # 첫 거래 전
    # 10/1: 통장 1천만 + 업비트 (현금 99,800 + BTC 0.004 × 1억) + 아파트 10억 - 대출 3억 (보험 보고는 10/10)
    assert sums[1] == D(10000000) + D(99800) + D(400000) + D(1000000000) - D(300000000)
    assert sums[2].quantize(D(1)) == D(729405010)


def test_history_days_downsamples():
    days = history_days(date(2020, 1, 1), date(2026, 10, 19))
    assert len(days) <= 401 and days[0] == date(2020, 1, 1) and days[-1] == date(2026, 10, 19)
    assert history_days(date(2026, 10, 1), date(2026, 10, 3)) == [date(2026, 10, d) for d in (1, 2, 3)]


def test_dashboard_api(client, conn, sample):
    r = client.get(f"/api/households/{sample}/dashboard", params={"range": "all"})
    assert r.status_code == 200
    d = r.json()
    assert D(d["kpi"]["net_worth_krw"]) == D(729405010)
    assert D(d["kpi"]["assets_krw"]) == D(1028705010) and D(d["kpi"]["liabilities_krw"]) == D(-299300000)
    assert d["history"]["points"][-1]["net_worth_krw"] == d["kpi"]["net_worth_krw"]
    assert d["history"]["points"][0]["date"] == "2026-10-01"
    alloc = {a["asset_class"]: D(a["value_krw"]) for a in d["allocation"]}
    assert list(alloc) == ["현금성", "주식", "부동산", "가상자산", "보험·연금"]   # 고정 순서
    assert alloc["부동산"] == D(1000000000) and alloc["보험·연금"] == D(15000000)
    assert sum(alloc.values()) == D(1028705010)
    members = {m["name"]: D(m["net_worth_krw"]) for m in d["members"]}
    assert members == {"홍길동": D(214705010), "김영희": D(514700000)}
    assert {h["name"] for h in d["holdings"]} == {"삼성전자", "Apple", "비트코인", "우리집 아파트 84㎡"}
    assert client.get(f"/api/households/{sample}/dashboard", params={"range": "5y"}).status_code == 422


def test_dashboard_empty_household(client):
    hid = client.post("/api/households", json={"name": "빈집"}).json()["id"]
    d = client.get(f"/api/households/{hid}/dashboard").json()
    assert D(d["kpi"]["net_worth_krw"]) == 0 and len(d["history"]["points"]) == 1
    assert d["allocation"] == [] and d["holdings"] == [] and len(d["cashflow"]["months"]) == 6
