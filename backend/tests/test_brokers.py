"""키움·한국투자 어댑터와 동기화. 실제 증권사 대신 가짜 서버(fake_brokers)를 쓴다."""
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from assethub.brokers.base import BrokerError, Credentials, num
from assethub.brokers.kis import Kis, split_account
from assethub.brokers.kiwoom import Kiwoom, classify
from assethub.secrets import SecretError, decrypt_json, encrypt_json

from .fake_brokers import FakeKis, FakeKiwoom, kst_today, pad

D = Decimal


def client(fake):
    return httpx.Client(transport=httpx.MockTransport(fake))


# ------------------------------------------------------------------ 단위

def test_number_and_symbol_helpers():
    assert num(pad(-1234)) == D(-1234) and num(pad(0)) == 0 and num("") == 0 and num("+12.50") == D("12.50")
    assert split_account("12345678-01") == ("12345678", "01") and split_account("1234567801") == ("12345678", "01")
    with pytest.raises(BrokerError):
        split_account("123-45")


@pytest.mark.parametrize("row, kind", [
    ({"rmrk_nm": "장내매수", "stk_cd": "A005930"}, "buy"),
    ({"rmrk_nm": "장내매도", "stk_cd": "A005930"}, "sell"),
    ({"rmrk_nm": "배당금입금", "stk_cd": "A005930"}, "dividend"),
    ({"rmrk_nm": "예탁금이용료"}, "interest"),
    ({"rmrk_nm": "신용이자", "io_tp_nm": "출금"}, "fee"),
    ({"rmrk_nm": "이체입금"}, "cash_in"),
    ({"rmrk_nm": "이체출금"}, "cash_out"),
    ({"rmrk_nm": "타사대체입고", "stk_cd": "A000660"}, "instrument_in"),
    ({"rmrk_nm": "환전매수"}, "fx"),
])
def test_kiwoom_classify(row, kind):
    assert classify(row) == kind


def test_secrets_roundtrip_and_wrong_key(monkeypatch):
    token = encrypt_json({"app_key": "k", "app_secret": "s"})
    assert b"app_secret" not in token and decrypt_json(token)["app_secret"] == "s"
    from cryptography.fernet import Fernet
    monkeypatch.setenv("ASSETHUB_SECRET_KEY", Fernet.generate_key().decode())
    with pytest.raises(SecretError):
        decrypt_json(token)


def test_kiwoom_ledger_mapping_and_paging():
    fake = FakeKiwoom()
    saved = []
    k = Kiwoom(Credentials(app_key="k", app_secret="s"), client(fake), on_token=saved.append, min_interval=0)
    assert [a.ref for a in k.accounts()] == ["5012345678"]
    rows = k.ledger("5012345678", date(2026, 9, 1), date(2026, 10, 19))
    assert k.skipped == 1                                     # 달러 행
    assert [r.kind for r in rows] == ["cash_in", "buy", "dividend", "sell", "cash_out", "interest"]
    buy, div, sell = rows[1], rows[2], rows[3]
    assert buy.amount == D(-600090) and buy.quantity == 10 and buy.instrument_symbol == "005930" and buy.fee == 90
    assert div.amount == D(3610) and div.tax == 556
    assert sell.amount == D(279250) and sell.quantity == -4 and sell.tax == 708
    assert rows[0].balance_after == D(1500000) and rows[0].counterparty == "홍길동"
    assert len({r.external_id for r in rows}) == 6
    assert fake.token_calls == 1 and len(saved) == 1          # 토큰은 한 번만, 저장 콜백 호출
    assert any(h == "kt00015" for h, _ in fake.calls)
    snap = k.snapshot("5012345678")
    assert snap.cash == {"KRW": D(982890)} and [h.symbol for h in snap.holdings] == ["005930", "000660"]


def test_kis_ledger_splits_three_month_boundary_and_pages():
    today = date(2026, 10, 19)
    fake = FakeKis(today)
    k = Kis(Credentials(app_key="k", app_secret="s", accounts=["12345678-01"]), client(fake), min_interval=0)
    k.today = today
    rows = k.ledger("12345678-01", date(2026, 6, 1), today)
    assert [(r.kind, r.quantity, r.amount) for r in rows] == [("buy", 10, D(-550000)), ("sell", -5, D(350000))]
    trs = {(tr, s, e) for tr, s, e in fake.ccld_calls}
    assert ("CTSC9215R", "20260601", "20260720") in trs        # 3개월 이전 TR
    assert all(tr == "TTTC0081R" for tr, s, e in trs if s >= "20260721")
    snap = k.snapshot("12345678-01")
    assert snap.cash == {"KRW": D(1234567)} and snap.holdings[1].avg_price == D(50000)


def test_kis_errors_are_readable():
    fake = FakeKis(date(2026, 10, 19))
    k = Kis(Credentials(app_key="BAD", app_secret="s", accounts=["12345678-01"]), client(fake), min_interval=0)
    with pytest.raises(BrokerError, match="유효하지 않은 AppKey"):
        k.accounts()


# ------------------------------------------------------------------ API + 동기화

@pytest.fixture
def home(client_with_fakes):
    c, fakes = client_with_fakes
    hid = c.post("/api/households", json={"name": "우리집"}).json()["id"]
    me = c.post(f"/api/households/{hid}/members", json={"name": "홍길동", "relation": "self"}).json()["id"]
    return c, fakes, hid, me


@pytest.fixture
def client_with_fakes(client):
    fakes = {"kiwoom": FakeKiwoom(), "kis": FakeKis(kst_today())}

    def route(request: httpx.Request):
        host = request.url.host
        return (fakes["kiwoom"] if "kiwoom" in host else fakes["kis"])(request)

    client.app.state.http_transport = httpx.MockTransport(route)
    client.app.state.broker_interval = 0
    return client, fakes


def cash_and_positions(conn, account_id):
    cash = conn.execute("SELECT coalesce(sum(amount),0) AS c FROM txn WHERE account_id = %s AND currency='KRW' AND status='posted'",
                        (account_id,)).fetchone()["c"]
    pos = {r["symbol"]: r["q"] for r in conn.execute(
        """SELECT i.symbol, sum(t.quantity) AS q FROM txn t JOIN instrument i ON i.id = t.instrument_id
            WHERE t.account_id = %s AND t.quantity IS NOT NULL GROUP BY i.symbol HAVING sum(t.quantity) <> 0""",
        (account_id,)).fetchall()}
    return cash, pos


def test_kiwoom_connect_link_sync(home, conn):
    c, fakes, hid, me = home
    r = c.post(f"/api/households/{hid}/connections", json={
        "provider": "kiwoom", "member_id": me, "app_key": "app-key-1234", "app_secret": "very-secret"})
    assert r.status_code == 201, r.text
    con = r.json()
    assert con["broker_accounts"] == [{"ref": "5012345678", "label": "5012-3456-78"}]
    assert con["key_hint"] == "…1234"
    assert "very-secret" not in r.text and "kw-token" not in r.text
    sid = con["id"]

    linked = c.post(f"/api/connections/{sid}/link", json={"ref": "5012345678", "start_date": "2026-09-01"}).json()
    acc = linked["linked"][0]["account_id"]
    a = c.get(f"/api/accounts/{acc}").json()
    assert a["account_type"] == "brokerage" and a["institution_code"] == "KIWOOM" and a["owners"][0]["member_id"] == me

    res = c.post(f"/api/connections/{sid}/sync").json()
    assert res["status"] == "succeeded", res
    s = res["accounts"][0]
    assert s["new"] == 6 and any("외화" in w for w in s["warnings"])
    # 시작일 이전부터 있던 SK하이닉스 3주는 기초 보유로, 현금은 첫 거래의 잔고로 맞는다
    assert [a for a in s["adjustments"] if a["type"] == "quantity"] == [
        {"type": "quantity", "symbol": "000660", "name": "SK하이닉스", "diff": "3"}]
    cash, pos = cash_and_positions(conn, acc)
    assert cash == D(982890) and pos == {"005930": D(6), "000660": D(3)}
    opening = conn.execute("SELECT trade_date FROM txn WHERE account_id = %s AND kind = 'instrument_in'", (acc,)).fetchone()
    assert opening["trade_date"] == date(2026, 8, 31)
    inst = conn.execute("SELECT kind, market, name FROM instrument WHERE symbol = '005930'").fetchone()
    assert inst == {"kind": "stock", "market": "KRX", "name": "삼성전자"}
    rep = conn.execute("SELECT count(*) AS n FROM reported_holding WHERE account_id = %s", (acc,)).fetchone()["n"]
    assert rep == 2
    cat = conn.execute("""SELECT c.name FROM txn t JOIN category c ON c.id = t.category_id
                           WHERE t.account_id = %s AND t.kind = 'dividend'""", (acc,)).fetchone()
    assert cat["name"] == "배당금"
    px = conn.execute("""SELECT p.close, p.source FROM price p JOIN instrument i ON i.id = p.instrument_id
                          WHERE i.symbol = '000660'""").fetchone()
    assert px == {"close": D("160000.00000000"), "source": "kiwoom"}   # 증권사 현재가를 그날 시세로

    # 두 번째 동기화: 오늘 매수 1건만 새로, 잔고 맞춤 없음, 토큰 재발급 없음
    today = kst_today()
    fakes["kiwoom"].ledger.append(dict(
        trde_dt=today.strftime("%Y%m%d"), trde_no="000000099", rmrk_nm="장내매수", io_tp_nm="매수", stk_cd="A000660",
        stk_nm="SK하이닉스", trde_qty_jwa_cnt=pad(1), trde_unit="160000", exct_amt=pad(160024), cmsn=pad(24),
        entra_remn=pad(822866), crnc_cd="KRW"))
    fakes["kiwoom"].cash = 822866
    fakes["kiwoom"].holdings[1]["rmnd_qty"] = pad(4)
    # 지난 동기화를 일주일 전으로 돌려 겹치는 구간이 오늘까지 오게 한다
    conn.execute("""UPDATE data_source SET config = jsonb_set(config, '{synced_until,5012345678}', to_jsonb(%s::text))
                    WHERE id = %s""", ((today - timedelta(days=3)).isoformat(), sid))
    res2 = c.post(f"/api/connections/{sid}/sync").json()["accounts"][0]
    assert res2["new"] == 1 and res2["adjustments"] == []
    assert fakes["kiwoom"].token_calls == 1
    cash, pos = cash_and_positions(conn, acc)
    assert cash == D(822866) and pos["000660"] == D(4)

    # 증권사만 아는 차액(예: 수수료)이 생기면 잔고 맞춤이 들어간다
    fakes["kiwoom"].cash = 821866
    res3 = c.post(f"/api/connections/{sid}/sync").json()["accounts"][0]
    assert res3["adjustments"] == [{"type": "cash", "currency": "KRW", "diff": "-1000"}]
    assert cash_and_positions(conn, acc)[0] == D(821866)


def test_kis_connect_sync_and_token_reuse(home, conn):
    c, fakes, hid, me = home
    bad = c.post(f"/api/households/{hid}/connections", json={
        "provider": "kis", "member_id": me, "app_key": "BAD", "app_secret": "x", "accounts": ["12345678-01"]})
    assert bad.status_code == 422 and "AppKey" in bad.json()["detail"]
    assert c.get(f"/api/households/{hid}/connections").json() == []   # 실패하면 저장하지 않는다
    assert c.post(f"/api/households/{hid}/connections", json={
        "provider": "kis", "member_id": me, "app_key": "k", "app_secret": "s"}).status_code == 422

    sid = c.post(f"/api/households/{hid}/connections", json={
        "provider": "kis", "member_id": me, "app_key": "key-9876", "app_secret": "s3cret",
        "accounts": ["1234567801"]}).json()["id"]
    assert c.post(f"/api/connections/{sid}/link", json={"ref": "99999999-01"}).status_code == 422
    acc_existing = c.post(f"/api/households/{hid}/accounts", json={
        "name": "한투 위탁", "account_type": "brokerage", "owners": [{"member_id": me}]}).json()["id"]
    c.post(f"/api/connections/{sid}/link", json={"ref": "12345678-01", "account_id": acc_existing,
                                                  "start_date": (kst_today() - timedelta(days=200)).isoformat()})
    fakes["kis"].fills[0]["ord_dt"] = (kst_today() - timedelta(days=150)).strftime("%Y%m%d")
    fakes["kis"].fills[1]["ord_dt"] = (kst_today() - timedelta(days=30)).strftime("%Y%m%d")
    res = c.post(f"/api/connections/{sid}/sync").json()
    assert res["status"] == "succeeded", res
    s = res["accounts"][0]
    assert s["new"] == 2
    kinds = {a["type"] for a in s["adjustments"]}
    assert kinds == {"quantity", "cash"}                    # 카카오 기초 보유 + 수수료·입출금 등 현금 차액
    cash, pos = cash_and_positions(conn, acc_existing)
    assert cash == D(1234567) and pos == {"005930": D(5), "035720": D(2)}
    assert {tr for tr, _, _ in fakes["kis"].ccld_calls} == {"CTSC9215R", "TTTC0081R"}

    c.post(f"/api/connections/{sid}/sync")
    assert fakes["kis"].token_calls == 2                    # 실패한 BAD 1번 + 정상 1번. 두 번째 동기화는 저장된 토큰 사용
    assert len(c.get(f"/api/connections/{sid}/runs").json()) == 2

    lst = c.get(f"/api/households/{hid}/connections").json()
    assert lst[0]["linked"][0]["account_id"] == acc_existing and lst[0]["kis_accounts"] == ["12345678-01"]
    assert "s3cret" not in str(lst) and "kis-token" not in str(lst)


def test_unlink_and_delete_connection(home, conn):
    c, fakes, hid, me = home
    sid = c.post(f"/api/households/{hid}/connections", json={
        "provider": "kiwoom", "member_id": me, "app_key": "k", "app_secret": "s"}).json()["id"]
    acc = c.post(f"/api/connections/{sid}/link", json={"ref": "5012345678", "create_name": "키움 위탁"}).json()["linked"][0]["account_id"]
    assert c.post(f"/api/connections/{sid}/link", json={"ref": "5012345678"}).status_code == 409
    accts = c.get(f"/api/connections/{sid}/broker-accounts").json()
    assert accts[0]["account_name"] == "키움 위탁"
    c.post(f"/api/connections/{sid}/sync")
    assert c.delete(f"/api/connections/{sid}").status_code == 204
    assert c.get(f"/api/households/{hid}/connections").json() == []
    row = conn.execute("SELECT credential_enc, status FROM data_source WHERE id = %s", (sid,)).fetchone()
    assert row["credential_enc"] is None and row["status"] == "paused"
    a = conn.execute("SELECT data_source_id, external_ref FROM account WHERE id = %s", (acc,)).fetchone()
    assert a == {"data_source_id": None, "external_ref": None}
    assert conn.execute("SELECT count(*) AS n FROM txn WHERE account_id = %s", (acc,)).fetchone()["n"] > 0   # 거래는 남는다
    assert c.post(f"/api/connections/{sid}/sync").status_code == 404


def test_sync_without_linked_accounts_reports_failure(home):
    c, fakes, hid, me = home
    sid = c.post(f"/api/households/{hid}/connections", json={
        "provider": "kiwoom", "member_id": me, "app_key": "k", "app_secret": "s"}).json()["id"]
    res = c.post(f"/api/connections/{sid}/sync").json()
    assert res["status"] == "failed" and "연결된 계좌가 없습니다" in res["error"]
