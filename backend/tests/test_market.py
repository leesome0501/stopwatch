"""시세·환율 소스 파서와 수집기. 네트워크 대신 실제 네이버 응답을 저장한 파일을 쓴다."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from assethub.market.collector import collect
from assethub.market.providers import NaverDomestic, NaverForeign, NaverFx, ProviderError, Upbit, make_client

FIX = Path(__file__).parent / "fixtures"
D = Decimal


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def client_for(routes: dict):
    """경로 → 응답(JSON 또는 (status, body)). 요청 기록은 client.calls."""
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        for prefix, resp in routes.items():
            if request.url.path.startswith(prefix):
                if callable(resp):
                    resp = resp(request)
                if isinstance(resp, tuple):
                    return httpx.Response(resp[0], text=resp[1])
                return httpx.Response(200, json=resp)
        return httpx.Response(404, text="not found")

    c = make_client(httpx.MockTransport(handler))
    c.calls = calls
    return c


def test_naver_domestic_parses_real_response():
    c = client_for({"/chart/domestic/item/005930/day": load("naver_domestic_005930.json")})
    quotes, code = NaverDomestic().fetch(c, {"symbol": "005930", "market": "KRX"}, date(2026, 10, 13), date(2026, 10, 17))
    assert code == "005930" and quotes and all(q.close > 0 for q in quotes)
    assert quotes == sorted(quotes, key=lambda q: q.day)
    assert parse_qs(c.calls[0].url.query.decode())["startDateTime"] == ["202610130000"]


def test_naver_domestic_wrong_code_over_long_range():
    c = client_for({"/chart/domestic/item/": []})
    with pytest.raises(ProviderError, match="종목코드"):
        NaverDomestic().fetch(c, {"symbol": "999999", "market": "KRX"}, date(2026, 9, 1), date(2026, 10, 17))
    # 짧은 구간(연휴)은 빈 결과가 정상
    assert NaverDomestic().fetch(c, {"symbol": "005930", "market": "KRX"}, date(2026, 10, 3), date(2026, 10, 5))[0] == []


def test_naver_foreign_resolves_suffix_and_caches_code():
    c = client_for({
        "/stock/AAPL.O/basic": load("naver_basic_AAPL.O.json"),
        "/chart/foreign/item/AAPL.O/day": load("naver_foreign_AAPL.O.json"),
    })
    quotes, code = NaverForeign().fetch(c, {"symbol": "AAPL", "market": "NASDAQ"}, date(2026, 10, 13), date(2026, 10, 17))
    assert code == "AAPL.O" and quotes[0].close > 100
    # 저장된 코드가 있으면 찾기 요청을 다시 하지 않는다
    c2 = client_for({"/chart/foreign/item/AAPL.O/day": load("naver_foreign_AAPL.O.json")})
    NaverForeign().fetch(c2, {"symbol": "AAPL", "market": "NASDAQ", "price_code": "AAPL.O"}, date(2026, 10, 13), date(2026, 10, 17))
    assert all("/basic" not in r.url.path for r in c2.calls)


def test_naver_foreign_candidates():
    assert NaverForeign.candidates("KO", "NYSE")[0] == "KO"
    assert NaverForeign.candidates("AAPL", "NASDAQ")[0] == "AAPL.O"
    assert NaverForeign.candidates("BRK.B", "NYSE")[0] == "BRKb"
    assert "SCHD.K" in NaverForeign.candidates("SCHD", "AMEX")


def test_naver_foreign_not_found():
    c = client_for({"/stock/": (409, "{}")})
    with pytest.raises(ProviderError, match="찾지 못했"):
        NaverForeign().fetch(c, {"symbol": "ZZZZ", "market": "NASDAQ"}, date(2026, 10, 1), date(2026, 10, 17))


def test_naver_fx_pages_and_units():
    p1, p2 = load("naver_fx_usd_p1.json"), load("naver_fx_usd_p2.json")
    fx = NaverFx()
    fx.PAGE = 3   # 저장한 응답이 3개씩이라 페이지 크기를 맞춘다

    def pages(request):
        page = int(request.url.params["page"])
        return {1: p1, 2: p2}.get(page, [])
    c = client_for({"/marketindex/exchange/FX_USDKRW/prices": pages})
    quotes = fx.fetch(c, "USD", date(2026, 10, 10), date(2026, 10, 19))
    assert len(quotes) == 6 and quotes[-1].day == date(2026, 10, 19)
    assert quotes[-1].close == D(p1[0]["closePrice"].replace(",", ""))

    jpy = load("naver_fx_jpy_p1.json")
    c = client_for({"/marketindex/exchange/FX_JPYKRW/prices": jpy})
    q = NaverFx().fetch(c, "JPY", date(2026, 10, 1), date(2026, 10, 19))
    assert q[-1].close == D(jpy[0]["closePrice"]) / 100   # 100엔 → 1엔


def test_upbit_pages_backwards():
    def candles(request):
        to = request.url.params["to"]
        if to.startswith("2026-10-18"):
            return [{"candle_date_time_kst": f"2026-10-{d:02d}T09:00:00",
                     "candle_date_time_utc": f"2026-10-{d:02d}T00:00:00", "trade_price": 100000000 + d}
                    for d in range(17, 15, -1)]
        return [{"candle_date_time_kst": "2026-10-15T09:00:00", "candle_date_time_utc": "2026-10-15T00:00:00",
                 "trade_price": 99000000.0}]
    up = Upbit()
    up.PAGE = 2
    c = client_for({"/v1/candles/days": candles})
    quotes, code = up.fetch(c, {"symbol": "KRW-BTC", "market": "UPBIT"}, date(2026, 10, 15), date(2026, 10, 17))
    assert code == "KRW-BTC"
    assert [q.day.day for q in quotes] == [15, 16, 17] and quotes[0].close == D("99000000.0")


# ------------------------------------------------------------------- 수집기 (DB)

def test_collect_fills_prices_and_fx(client, conn):
    hid = client.post("/api/households", json={"name": "우리집"}).json()["id"]
    me = client.post(f"/api/households/{hid}/members", json={"name": "나", "relation": "self"}).json()["id"]
    acc = client.post(f"/api/households/{hid}/accounts", json={
        "name": "위탁", "account_type": "brokerage", "owners": [{"member_id": me}]}).json()["id"]
    ids = {}
    for body in ({"kind": "stock", "asset_class": "equity", "name": "삼성전자", "currency": "KRW", "symbol": "005930", "market": "KRX"},
                 {"kind": "stock", "asset_class": "equity", "name": "Apple", "currency": "USD", "symbol": "AAPL", "market": "NASDAQ"},
                 {"kind": "real_estate", "asset_class": "real_estate", "name": "아파트", "currency": "KRW", "market": "PRIVATE"},
                 {"kind": "stock", "asset_class": "equity", "name": "없는종목", "currency": "KRW", "symbol": "999999", "market": "KRX"}):
        ids[body["name"]] = client.post("/api/instruments", json=body).json()["id"]
    for name, cur, price in (("삼성전자", "KRW", 60000), ("Apple", "USD", 200), ("아파트", "KRW", 800000000), ("없는종목", "KRW", 1)):
        r = client.post(f"/api/accounts/{acc}/transactions", json={
            "occurred_at": "2026-09-01T10:00:00", "kind": "instrument_in", "amount": "0", "currency": cur,
            "instrument_id": ids[name], "quantity": "1", "unit_price": str(price)})
        assert r.status_code == 201
    # 수동으로 넣은 시세는 수집기가 덮어쓰지 않는다
    client.put(f"/api/instruments/{ids['삼성전자']}/prices",
               json=[{"price_date": "2026-10-13", "close": "1", "source": "manual"}])

    fx_pages = {1: load("naver_fx_usd_p1.json"), 2: load("naver_fx_usd_p2.json")}
    http = client_for({
        "/chart/domestic/item/005930/day": load("naver_domestic_005930.json"),
        "/chart/domestic/item/999999/day": [],
        "/stock/AAPL.O/basic": load("naver_basic_AAPL.O.json"),
        "/chart/foreign/item/AAPL.O/day": load("naver_foreign_AAPL.O.json"),
        "/marketindex/exchange/FX_USDKRW/prices": lambda r: fx_pages.get(int(r.url.params["page"]), []),
    })
    result = collect(conn, http, today=date(2026, 10, 19), delay=0)
    assert result["status"] == "partial"
    assert [e["target"] for e in result["errors"]] == ["999999"]
    assert result["manual_only"] == ["아파트"]
    assert result["prices_upserted"] > 0 and result["fx_upserted"] > 0

    assert conn.execute("SELECT price_code FROM instrument WHERE id = %s", (ids["Apple"],)).fetchone()["price_code"] == "AAPL.O"
    manual = conn.execute("SELECT close, source FROM price WHERE instrument_id = %s AND price_date = '2026-10-13'",
                          (ids["삼성전자"],)).fetchone()
    assert manual == {"close": D("1.00000000"), "source": "manual"}
    run = client.get("/api/market/runs").json()[0]
    assert run["status"] == "partial" and run["errors"][0]["target"] == "999999"
    # 첫 수집은 첫 거래일 일주일 전부터 요청한다
    first_req = next(r for r in http.calls if "/chart/domestic/item/005930" in r.url.path)
    assert first_req.url.params["startDateTime"] == "202608250000"
