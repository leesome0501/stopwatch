from decimal import Decimal

import pytest

from assethub.importer.standard import COLUMNS

from .files import html_xls_bytes, xlsx_bytes

D = Decimal

HEADER = ["No.", "거래일시", "적요", "기재내용", "찾으신금액", "맡기신금액", "거래후 잔액", "취급점"]


def woori(rows, account_no="1002-123-456789"):
    return html_xls_bytes([["계좌번호", account_no], [], HEADER] + rows)


# 은행 화면 그대로: 최신이 위
OCT_1_TO_3 = [
    ["3", "2026.10.03 18:00:00", "체크카드", "스타벅스", "5,000", "0", "1,145,000", ""],
    ["2", "2026.10.02 09:00:00", "타행이체", "(주)회사", "0", "150,000", "1,150,000", ""],
    ["1", "2026.10.01 12:00:00", "자동이체", "자동이체", "100,000", "0", "1,000,000", ""],
]


@pytest.fixture
def family(client):
    hid = client.post("/api/households", json={"name": "우리집"}).json()["id"]
    me = client.post(f"/api/households/{hid}/members", json={"name": "홍길동", "relation": "self"}).json()["id"]
    sp = client.post(f"/api/households/{hid}/members", json={"name": "김영희", "relation": "spouse"}).json()["id"]
    bank = client.post(f"/api/households/{hid}/accounts", json={
        "name": "우리 월급통장", "account_type": "checking", "institution_code": "WOORI",
        "account_number_masked": "1002-***-**6789", "owners": [{"member_id": me}]}).json()
    return {"hid": hid, "me": me, "spouse": sp, "bank": bank["id"]}


def upload(client, account_id, data, preview=False, name="statement.xls"):
    url = f"/api/accounts/{account_id}/imports" + ("/preview" if preview else "")
    return client.post(url, files={"file": (name, data, "application/vnd.ms-excel")})


def summary_value(client, hid, account_id):
    s = client.get(f"/api/households/{hid}/summary").json()
    return D(next(a for a in s["accounts"] if a["account_id"] == account_id)["value_krw"])


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/accounts/{account_id}/imports/preview" in paths


def test_account_owner_validation(client, family):
    hid = family["hid"]
    r = client.post(f"/api/households/{hid}/accounts", json={
        "name": "공동명의 아파트", "account_type": "real_asset",
        "owners": [{"member_id": family["me"], "share": "0.5"}, {"member_id": family["spouse"], "share": "0.4"}]})
    assert r.status_code == 422 and "지분 합계" in r.json()["detail"]
    r = client.post(f"/api/households/{hid}/accounts", json={
        "name": "공동명의 아파트", "account_type": "real_asset",
        "owners": [{"member_id": family["me"], "share": "0.5"}, {"member_id": family["spouse"], "share": "0.5"}]})
    assert r.status_code == 201 and len(r.json()["owners"]) == 2


def test_preview_does_not_save(client, family):
    r = upload(client, family["bank"], woori(OCT_1_TO_3), preview=True)
    body = r.json()
    assert r.status_code == 200 and body["committed"] is False
    assert body["format"] == "Woori" and body["file_direction"] == "newest-first"
    assert body["counts"] == {"total": 3, "new": 3, "duplicate": 0, "error": 0}
    # 저장 순서와 같은 과거→최신
    assert [row["amount"] for row in body["rows"]] == ["-100000", "150000", "-5000"]
    assert client.get(f"/api/accounts/{family['bank']}/transactions").json() == []


def test_first_import_sets_opening_balance_and_matches_bank(client, family):
    r = upload(client, family["bank"], woori(OCT_1_TO_3))
    body = r.json()
    assert r.status_code == 201 and body["committed"]
    assert D(body["opening_balance"]) == D(1100000)   # 1,000,000 + 100,000
    assert body["warnings"] == []
    txns = client.get(f"/api/accounts/{family['bank']}/transactions").json()
    assert len(txns) == 4 and txns[-1]["kind"] == "adjustment"
    assert summary_value(client, family["hid"], family["bank"]) == D(1145000)
    batches = client.get(f"/api/accounts/{family['bank']}/imports").json()
    assert batches[0]["records_new"] == 3 and batches[0]["status"] == "succeeded"


def test_reupload_is_idempotent(client, family):
    upload(client, family["bank"], woori(OCT_1_TO_3))
    body = upload(client, family["bank"], woori(OCT_1_TO_3)).json()
    assert body["counts"]["new"] == 0 and body["counts"]["duplicate"] == 3
    assert any("같은 파일" in w for w in body["warnings"])
    assert summary_value(client, family["hid"], family["bank"]) == D(1145000)


def test_overlapping_file_without_times_only_adds_new_rows(client, family):
    """두 번째 파일은 날짜만 있고 기간이 겹친다. 잔액 기반 키라서 겹친 거래는 중복으로 걸러진다."""
    upload(client, family["bank"], woori(OCT_1_TO_3))
    second = woori([
        ["2", "2026.10.04", "체크카드", "마트", "45,000", "0", "1,100,000", ""],
        ["1", "2026.10.03", "체크카드", "스타벅스", "5,000", "0", "1,145,000", ""],
    ])
    body = upload(client, family["bank"], second).json()
    assert body["counts"] == {"total": 2, "new": 1, "duplicate": 1, "error": 0}
    assert body["warnings"] == []
    assert summary_value(client, family["hid"], family["bank"]) == D(1100000)


def test_missing_transaction_is_flagged(client, family):
    upload(client, family["bank"], woori(OCT_1_TO_3))
    gap = woori([["1", "2026.10.06 10:00:00", "체크카드", "약국", "10,000", "0", "1,000,000", ""]])
    body = upload(client, family["bank"], gap).json()
    assert body["counts"]["new"] == 1
    assert any("빠진 거래" in w for w in body["warnings"])


def test_wrong_account_file_warns(client, family):
    body = upload(client, family["bank"], woori(OCT_1_TO_3, account_no="1002-999-000111"), preview=True).json()
    assert any("다른 계좌의 파일" in w for w in body["warnings"])


def test_category_learning_and_rules(client, family, conn):
    hid = family["hid"]
    upload(client, family["bank"], woori(OCT_1_TO_3))
    cafe = conn.execute("SELECT id FROM category WHERE name = '카페' AND household_id IS NULL").fetchone()["id"]
    salary = conn.execute("SELECT id FROM category WHERE name = '급여' AND household_id IS NULL").fetchone()["id"]
    starbucks = next(t for t in client.get(f"/api/accounts/{family['bank']}/transactions").json()
                     if t["counterparty"] == "스타벅스")
    assert client.patch(f"/api/transactions/{starbucks['id']}", json={"category_id": cafe}).status_code == 200
    conn.execute("""INSERT INTO category_rule (household_id, match_field, match_type, pattern, category_id)
                    VALUES (%s, 'description', 'contains', '(주)회사', %s)""", (hid, salary))

    nov = woori([
        ["2", "2026.11.02 09:00:00", "타행이체", "(주)회사", "0", "3,000,000", "4,140,000", ""],
        ["1", "2026.11.01 08:00:00", "체크카드", "스타벅스", "5,000", "0", "1,140,000", ""],
    ])
    rows = upload(client, family["bank"], nov, preview=True).json()["rows"]
    by_desc = {r["description"]: r for r in rows}
    assert by_desc["스타벅스"]["category_name"] == "카페" and by_desc["스타벅스"]["category_source"] == "history"
    assert by_desc["(주)회사"]["category_name"] == "급여" and by_desc["(주)회사"]["category_source"] == "rule"


def test_brokerage_standard_template(client, family):
    hid = family["hid"]
    acc = client.post(f"/api/households/{hid}/accounts", json={
        "name": "한투 위탁", "account_type": "brokerage", "institution_code": "KIS",
        "owners": [{"member_id": family["me"]}]}).json()["id"]
    sam = client.post("/api/instruments", json={"kind": "stock", "asset_class": "equity", "name": "삼성전자",
                                               "currency": "KRW", "symbol": "005930", "market": "KRX"}).json()["id"]
    aapl = client.post("/api/instruments", json={"kind": "stock", "asset_class": "equity", "name": "Apple",
                                                "currency": "USD", "symbol": "AAPL", "market": "NASDAQ"}).json()["id"]
    assert client.post("/api/instruments", json={"kind": "stock", "asset_class": "equity", "name": "중복",
                                                 "currency": "KRW", "symbol": "005930", "market": "KRX"}).status_code == 409

    def line(*cells):
        return list(cells) + [""] * (len(COLUMNS) - len(cells))

    data = xlsx_bytes([COLUMNS,
                       line("2026-10-12", "08:00", "입금", "3000000", "", "", "", "", "", "", "", "투자이체"),
                       line("2026-10-12", "09:05", "매수", "", "", "005930", "KRX", 20, 60000, 150),
                       line("2026-10-13", "10:00", "환전", "-1390000", "KRW", "", "", "", "", "", "", "", "", "", "", "fx1"),
                       line("2026-10-13", "10:00", "환전", "1000", "USD", "", "", "", "", "", "", "", "", "", "", "fx1"),
                       line("2026-10-13", "23:40", "매수", "", "", "AAPL", "", 4, 200, 1),
                       line("2026-10-15", "", "배당", "3.40", "", "AAPL", "", "", "", "", "0.60", "배당금"),
                       line("2026-10-16", "", "매수", "", "", "TSLA", "", 1, 300)])
    body = upload(client, acc, data, name="trades.xlsx").json()
    assert body["format"] == "AssetHub"
    assert body["counts"] == {"total": 7, "new": 6, "duplicate": 0, "error": 1}
    err = next(r for r in body["rows"] if r["status"] == "error")
    assert "TSLA" in err["message"]
    usd_rows = [r for r in body["rows"] if r["currency"] == "USD"]
    assert len(usd_rows) == 3   # 환전 USD 다리, AAPL 매수, 배당 (통화 비우면 종목 통화)

    txns = client.get(f"/api/accounts/{acc}/transactions").json()
    fx = [t for t in txns if t["kind"] == "fx"]
    assert len(fx) == 2 and fx[0]["group_id"] == fx[1]["group_id"] is not None

    assert client.put(f"/api/instruments/{sam}/prices", json=[{"price_date": "2026-10-15", "close": "70000"}]).status_code == 204
    client.put(f"/api/instruments/{aapl}/prices", json=[{"price_date": "2026-10-15", "close": "220"}])
    client.put("/api/fx-rates", json=[{"currency": "USD", "rate_date": "2026-10-15", "krw_rate": "1400"}])
    # db/tests.sql 과 같은 계산: 409,850 + 20*70,000 + (202.40 + 4*220)*1,400
    assert summary_value(client, hid, acc) == D(3325210)

    flow = client.get(f"/api/households/{hid}/cashflow", params={"month": "2026-10"}).json()
    assert D(flow["income_krw"]) == D(4760)   # 배당 3.40 USD (투자이체는 내부이체라 제외)


def test_manual_transaction_void_and_validation(client, family):
    acc, hid = family["bank"], family["hid"]
    r = client.post(f"/api/accounts/{acc}/transactions", json={
        "occurred_at": "2026-10-01T09:00:00", "kind": "cash_in", "amount": "50000", "description": "용돈"})
    assert r.status_code == 201 and r.json()["trade_date"] == "2026-10-01" and r.json()["currency"] == "KRW"
    assert summary_value(client, hid, acc) == D(50000)
    bad = client.post(f"/api/accounts/{acc}/transactions", json={
        "occurred_at": "2026-10-01T09:00:00", "kind": "cash_in", "amount": "-1"})
    assert bad.status_code == 422
    assert client.delete(f"/api/transactions/{r.json()['id']}").status_code == 204
    assert summary_value(client, hid, acc) == D(0)
    assert client.get(f"/api/accounts/{acc}/transactions").json() == []


def test_template_download_and_bad_files(client, family):
    t = client.get("/api/import-template")
    assert t.status_code == 200 and t.content[:4] == b"PK\x03\x04"
    assert upload(client, family["bank"], b"PK\x03\x04garbage").status_code == 422
    r = upload(client, family["bank"], xlsx_bytes([["이름"], ["홍길동"]]))
    assert r.status_code == 422 and "표준 양식" in r.json()["detail"]
    assert client.get(f"/api/accounts/{family['bank']}/imports").json() == []
    assert client.get("/api/accounts/9999").status_code == 404
