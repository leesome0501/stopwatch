from datetime import datetime
from decimal import Decimal

from assethub.importer.detect import NOT_FOUND, parse_file
from assethub.importer.parsing import KST

from .files import csv_bytes, html_xls_bytes, xlsx_bytes

D = Decimal

WOORI = [
    ["거래내역조회"],
    ["계좌번호", "1002-123-456789"],
    [],
    ["No.", "거래일시", "적요", "기재내용", "찾으신금액", "맡기신금액", "거래후 잔액", "취급점"],
    ["3", "2026.10.03 18:00:00", "체크카드", "스타벅스", "5,000", "0", "1,145,000", "본점"],
    ["2", "2026.10.02 09:00:00", "타행이체", "홍길동", "0", "150,000", "1,150,000", ""],
    ["1", "2026.10.01 12:00:00", "자동이체", "자동이체", "100,000", "0", "1,000,000", ""],
    ["합계", "", "", "", "105,000", "150,000", "", ""],
]


def test_woori_html_xls_in_cp949():
    r = parse_file(html_xls_bytes(WOORI))
    assert r.format == "Woori"
    assert r.account_number == "1002-123-456789"
    assert [x.amount for x in r.rows] == [D(-5000), D(150000), D(-100000)]
    assert r.rows[0].counterparty == "스타벅스"
    assert r.rows[2].counterparty is None  # 기재내용 == 적요
    assert r.rows[0].balance_after == D(1145000)
    assert r.rows[1].kind == "cash_in" and r.rows[0].kind == "cash_out"


def test_shinhan_separate_time_column_xlsx():
    rows = [
        ["거래일자", "거래시간", "적요", "출금(원)", "입금(원)", "내용", "잔액(원)", "거래점"],
        ["2026-10-05", "13:20:01", "체크", 12000, 0, "GS25", 988000, "강남"],
        ["2026-10-04", "08:00:00", "급여", 0, 3000000, "", 1000000, ""],
    ]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "Shinhan"
    assert r.rows[0].moment.at == datetime(2026, 10, 5, 13, 20, 1, tzinfo=KST)
    assert r.rows[0].description == "GS25"
    assert r.rows[1].description == "급여"
    assert r.rows[1].amount == D(3000000)


def test_hana_corp():
    rows = [["거래일시", "적요", "의뢰인/수취인", "입금", "출금", "거래후잔액"],
            ["2026-10-01 10:00", "인터넷", "(주)거래처", "500,000", "", "2,500,000"]]
    r = parse_file(csv_bytes(rows))
    assert r.format == "HanaCorp"
    assert r.rows[0].counterparty == "(주)거래처" and r.rows[0].amount == D(500000)


def test_hana_personal_joins_type_and_memo():
    rows = [["거래일시", "구분", "적요", "출금액", "입금액", "잔액"],
            ["2026-10-01 10:00:00", "체크카드", "올리브영", "23,000", "0", "77,000"]]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "HanaPersonal"
    assert r.rows[0].description == "체크카드 올리브영"


def test_ibk():
    rows = [["거래일시", "출금", "입금", "거래후 잔액", "거래내용", "상대계좌번호", "상대은행", "상대계좌예금주명"],
            ["2026-10-01 10:00:00", "", "70,000", "170,000", "이체", "110-222-333", "신한", "김영희"]]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "IBK"
    assert r.rows[0].counterparty == "김영희" and r.rows[0].balance_after == D(170000)


def test_transfer_history_skips_failed():
    rows = [["이체일시", "출금계좌", "입금계좌", "받는분", "이체금액", "내 통장표시", "처리결과"],
            ["2026-10-01 10:00", "110-1", "신한 110-2", "김영희", "50,000", "생활비", "정상완료"],
            ["2026-10-01 11:00", "110-1", "신한 110-2", "김영희", "50,000", "생활비", "실패"]]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "TransferHistory"
    assert len(r.rows) == 1 and r.rows[0].amount == D(-50000)


def test_generic_kb_style():
    rows = [["거래일시", "적요", "보낸분/받는분", "송금메모", "출금액(원)", "입금액(원)", "잔액(원)", "처리점"],
            ["2026.10.01 09:00:00", "전자금융", "김영희", "용돈", "0", "200,000", "1,200,000", "인터넷"]]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "Generic"
    row = r.rows[0]
    assert row.amount == D(200000) and row.counterparty == "김영희"
    assert row.description == "전자금융 용돈" and row.balance_after == D(1200000)


def test_generic_single_amount_with_direction_column():
    rows = [["거래일시", "구분", "거래금액", "거래 후 잔액", "거래구분", "내용"],
            ["2026.10.01 09:00:00", "출금", "15,000", "985,000", "체크카드", "편의점"],
            ["2026.10.01 10:00:00", "입금", "5,000", "990,000", "이체", "환불"]]
    r = parse_file(xlsx_bytes(rows))
    assert r.format == "Generic"
    assert [x.amount for x in r.rows] == [D(-15000), D(5000)]


def test_first_sheet_without_table_is_skipped():
    data = xlsx_bytes([["안내문"]], sheet="표지",
                      extra_sheets={"내역": [["거래일시", "출금", "입금", "거래후잔액", "거래내용"],
                                           ["2026-10-01 10:00", "1,000", "", "9,000", "커피"]]})
    r = parse_file(data)
    assert r.format == "IBK" and len(r.rows) == 1


def test_unknown_table():
    r = parse_file(xlsx_bytes([["이름", "나이"], ["홍길동", 40]]))
    assert r.format is None and r.warnings == [NOT_FOUND]
