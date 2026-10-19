"""관리 화면이 쓰는 API: 구성원·계좌·명의·평가액·카테고리·규칙·거래 검색·가구 삭제."""
from decimal import Decimal

import pytest

from assethub.config import DB_DIR

from .files import html_xls_bytes

D = Decimal


@pytest.fixture
def home(client):
    hid = client.post("/api/households", json={"name": "우리집"}).json()["id"]
    me = client.post(f"/api/households/{hid}/members", json={"name": "홍길동", "relation": "self"}).json()["id"]
    sp = client.post(f"/api/households/{hid}/members", json={"name": "김영희", "relation": "spouse"}).json()["id"]
    return {"hid": hid, "me": me, "sp": sp}


def test_household_and_member_edit(client, home):
    assert client.patch(f"/api/households/{home['hid']}", json={"name": "홍씨네"}).json()["name"] == "홍씨네"
    m = client.patch(f"/api/members/{home['sp']}", json={"birth_date": "1987-07-15", "is_dependent": True}).json()
    assert m["birth_date"] == "1987-07-15" and m["is_dependent"] is True and m["name"] == "김영희"
    assert client.patch(f"/api/members/{home['sp']}", json={"birth_date": None}).json()["birth_date"] is None
    assert client.patch(f"/api/members/{home['sp']}", json={"name": ""}).status_code == 422


def test_member_delete_blocked_by_ownership(client, home):
    acc = client.post(f"/api/households/{home['hid']}/accounts", json={
        "name": "영희 통장", "account_type": "checking", "owners": [{"member_id": home["sp"]}]}).json()["id"]
    r = client.delete(f"/api/members/{home['sp']}")
    assert r.status_code == 409 and "영희 통장" in r.json()["detail"]
    client.put(f"/api/accounts/{acc}/owners", json=[{"member_id": home["me"]}])
    assert client.delete(f"/api/members/{home['sp']}").status_code == 204


def test_account_owners_institution_close_delete(client, home):
    hid = home["hid"]
    inst = client.get("/api/institutions").json()
    assert any(i["code"] == "KB" for i in inst)
    acc = client.post(f"/api/households/{hid}/accounts", json={
        "name": "아파트", "account_type": "real_asset", "owners": [{"member_id": home["me"]}]}).json()["id"]
    r = client.put(f"/api/accounts/{acc}/owners", json=[{"member_id": home["me"], "share": "0.5"},
                                                         {"member_id": home["sp"], "share": "0.4"}])
    assert r.status_code == 422
    r = client.put(f"/api/accounts/{acc}/owners", json=[{"member_id": home["me"], "share": "0.5"},
                                                         {"member_id": home["sp"], "share": "0.5"}])
    assert len(r.json()["owners"]) == 2
    a = client.patch(f"/api/accounts/{acc}", json={"institution_code": "KB", "name": "우리 아파트"}).json()
    assert a["institution_code"] == "KB" and a["name"] == "우리 아파트"
    assert client.patch(f"/api/accounts/{acc}", json={"institution_code": "NOPE"}).status_code == 422
    assert client.patch(f"/api/accounts/{acc}", json={"institution_code": None}).json()["institution_code"] is None

    # 거래가 생기면 지울 수 없고, 마감은 된다
    client.post(f"/api/accounts/{acc}/transactions", json={
        "occurred_at": "2026-10-01T09:00:00", "kind": "cash_in", "amount": "1"})
    assert client.delete(f"/api/accounts/{acc}").status_code == 409
    client.patch(f"/api/accounts/{acc}", json={"closed_on": "2026-10-20"})
    assert all(x["id"] != acc for x in client.get(f"/api/households/{hid}/accounts").json())
    assert any(x["id"] == acc for x in client.get(f"/api/households/{hid}/accounts?include_closed=true").json())

    empty = client.post(f"/api/households/{hid}/accounts", json={
        "name": "잘못 만든 계좌", "account_type": "cash", "owners": [{"member_id": home["me"]}]}).json()["id"]
    assert client.delete(f"/api/accounts/{empty}").status_code == 204


def test_reported_balances_drive_value(client, home):
    hid = home["hid"]
    acc = client.post(f"/api/households/{hid}/accounts", json={
        "name": "종신보험", "account_type": "insurance", "valuation_method": "reported",
        "owners": [{"member_id": home["sp"]}]}).json()["id"]
    client.put(f"/api/accounts/{acc}/reported-balances", json=[{"as_of": "2026-09-30", "total_value": "14000000"}])
    rows = client.put(f"/api/accounts/{acc}/reported-balances",
                      json=[{"as_of": "2026-10-10", "total_value": "15000000"}]).json()
    assert [r["as_of"] for r in rows] == ["2026-10-10", "2026-09-30"]
    summary = client.get(f"/api/households/{hid}/summary").json()
    assert D(next(a for a in summary["accounts"] if a["account_id"] == acc)["value_krw"]) == D(15000000)
    client.delete(f"/api/accounts/{acc}/reported-balances/2026-10-10")
    assert len(client.get(f"/api/accounts/{acc}/reported-balances").json()) == 1


def test_categories_and_rules(client, home, conn):
    hid = home["hid"]
    food = conn.execute("SELECT id FROM category WHERE name = '식비' AND household_id IS NULL").fetchone()["id"]
    cafe = conn.execute("SELECT id FROM category WHERE name = '카페' AND household_id IS NULL").fetchone()["id"]
    c = client.post(f"/api/households/{hid}/categories", json={"name": "아이 간식", "parent_id": food}).json()
    assert c["kind"] == "expense" and c["household_id"] == hid
    assert client.post(f"/api/households/{hid}/categories", json={"name": "아이 간식", "parent_id": food}).status_code == 409
    assert client.post(f"/api/households/{hid}/categories", json={"name": "손자", "parent_id": c["id"]}).status_code == 422
    assert client.post(f"/api/households/{hid}/categories", json={"name": "부업"}).status_code == 422
    top = client.post(f"/api/households/{hid}/categories", json={"name": "부업", "kind": "income"}).json()
    assert top["parent_id"] is None
    names = [x["name"] for x in client.get(f"/api/households/{hid}/categories").json()]
    assert "아이 간식" in names and "부업" in names

    assert client.post(f"/api/households/{hid}/category-rules", json={
        "pattern": "[", "match_type": "regex", "category_id": cafe}).status_code == 422
    rule = client.post(f"/api/households/{hid}/category-rules", json={"pattern": "스타벅스", "category_id": cafe}).json()
    assert rule["category_name"] == "카페"
    assert len(client.get(f"/api/households/{hid}/category-rules").json()) == 1
    assert client.delete(f"/api/households/{hid}/category-rules/{rule['id']}").status_code == 204
    assert client.delete(f"/api/households/{hid}/category-rules/{rule['id']}").status_code == 404


def test_transaction_search(client, home, conn):
    hid = home["hid"]
    acc = client.post(f"/api/households/{hid}/accounts", json={
        "name": "월급통장", "account_type": "checking", "owners": [{"member_id": home["me"]}]}).json()["id"]
    data = html_xls_bytes([
        ["거래일시", "적요", "기재내용", "찾으신금액", "맡기신금액", "거래후 잔액"],
        ["2026.10.03 18:00:00", "체크카드", "스타벅스", "5,000", "0", "1,145,000"],
        ["2026.10.02 09:00:00", "타행이체", "(주)회사", "0", "150,000", "1,150,000"],
        ["2026.09.20 12:00:00", "체크카드", "마트", "100,000", "0", "1,000,000"],
    ])
    client.post(f"/api/accounts/{acc}/imports", files={"file": ("a.xls", data)})
    url = f"/api/households/{hid}/transactions"
    page = client.get(url).json()
    assert page["total"] == 4   # 3건 + 기초잔액
    assert D(page["sum_out_krw"]) == D(105000)
    assert page["items"][0]["counterparty"] == "스타벅스" and page["items"][0]["account_name"] == "월급통장"

    oct_ = client.get(url, params={"date_from": "2026-10-01", "date_to": "2026-10-31"}).json()
    assert oct_["total"] == 2
    assert client.get(url, params={"q": "스타"}).json()["total"] == 1
    assert client.get(url, params={"direction": "in"}).json()["total"] == 2
    unc = client.get(url, params={"uncategorized": True}).json()
    assert unc["total"] == 3   # 기초잔액(adjustment)은 분류 대상이 아님

    cafe = conn.execute("SELECT id FROM category WHERE name = '카페' AND household_id IS NULL").fetchone()["id"]
    food = conn.execute("SELECT id FROM category WHERE name = '식비' AND household_id IS NULL").fetchone()["id"]
    tid = page["items"][0]["id"]
    client.patch(f"/api/transactions/{tid}", json={"category_id": cafe, "memo": "아침 커피"})
    by_parent = client.get(url, params={"category_id": food}).json()   # 상위로 골라도 하위가 나온다
    assert by_parent["total"] == 1 and by_parent["items"][0]["category_parent"] == "식비"
    assert by_parent["items"][0]["memo"] == "아침 커피"
    client.delete(f"/api/transactions/{tid}")
    assert client.get(url).json()["total"] == 3
    paged = client.get(url, params={"limit": 2, "offset": 2}).json()
    assert paged["total"] == 3 and len(paged["items"]) == 1


def test_instrument_patch_and_prices(client):
    iid = client.post("/api/instruments", json={"kind": "real_estate", "asset_class": "real_estate",
                                               "name": "아파트", "currency": "KRW", "market": "PRIVATE"}).json()["id"]
    client.put(f"/api/instruments/{iid}/prices", json=[{"price_date": "2026-09-01", "close": "900000000"},
                                                      {"price_date": "2026-10-01", "close": "1000000000"}])
    prices = client.get(f"/api/instruments/{iid}/prices").json()
    assert [p["price_date"] for p in prices] == ["2026-10-01", "2026-09-01"] and prices[0]["source"] == "manual"
    client.delete(f"/api/instruments/{iid}/prices/2026-10-01")
    assert len(client.get(f"/api/instruments/{iid}/prices").json()) == 1
    i = client.patch(f"/api/instruments/{iid}", json={"name": "우리 아파트", "price_code": "X"}).json()
    assert i["name"] == "우리 아파트" and i["price_code"] == "X"
    assert client.patch(f"/api/instruments/{iid}", json={"price_code": None}).json()["price_code"] is None


def test_delete_household_removes_everything(client, conn):
    conn.execute((DB_DIR / "sample.sql").read_text(encoding="utf-8"))
    hid = conn.execute("SELECT id FROM household WHERE name = '우리집'").fetchone()["id"]
    other = client.post("/api/households", json={"name": "다른 집"}).json()["id"]
    r = client.request("DELETE", f"/api/households/{hid}", json={"confirm_name": "우리"})
    assert r.status_code == 422
    assert client.request("DELETE", f"/api/households/{hid}", json={"confirm_name": "우리집"}).status_code == 204
    counts = conn.execute("""SELECT (SELECT count(*) FROM txn) AS txn, (SELECT count(*) FROM account) AS account,
                                    (SELECT count(*) FROM member) AS member,
                                    (SELECT count(*) FROM instrument WHERE household_id IS NOT NULL) AS private_inst,
                                    (SELECT count(*) FROM household) AS households""").fetchone()
    assert counts == {"txn": 0, "account": 0, "member": 0, "private_inst": 0, "households": 1}
    assert client.get(f"/api/households/{other}").status_code == 200
    # 공용 종목(삼성전자 등)과 시세는 남는다
    assert conn.execute("SELECT count(*) AS n FROM instrument WHERE household_id IS NULL").fetchone()["n"] == 3
