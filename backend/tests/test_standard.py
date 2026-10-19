from decimal import Decimal

from assethub.importer.detect import parse_file
from assethub.importer.standard import COLUMNS, build_template

from .files import xlsx_bytes

D = Decimal


def make(rows):
    return parse_file(xlsx_bytes([COLUMNS] + [r + [""] * (len(COLUMNS) - len(r)) for r in rows]))


def test_signs_and_computed_amounts():
    r = make([
        ["2026-10-01", "", "출금", "5,000"],
        ["2026-10-12", "09:05", "매수", "", "KRW", "005930", "KRX", 20, 60000, 150],
        ["2026-10-20", "", "매도", "", "KRW", "005930", "KRX", 5, 70000, 100, 1050],
        ["2026-10-15", "", "배당", "3.40", "USD", "AAPL", "", "", "", "", "0.60", "배당금"],
        ["2026-10-01", "", "입고", "", "", "APT1", "PRIVATE", 1, 800000000],
    ])
    assert r.format == "AssetHub" and not r.errors
    out, buy, sell, div, inst_in = r.rows
    assert out.amount == D(-5000) and out.kind == "cash_out"
    assert buy.amount == D(-1200150) and buy.quantity == D(20)
    assert sell.amount == D(350000 - 100 - 1050) and sell.quantity == D(-5)
    assert div.amount == D("3.40") and div.tax == D("0.60") and div.category_name == "배당금"
    assert inst_in.amount == 0 and inst_in.unit_price == D(800000000)


def test_row_errors_are_reported_not_fatal():
    r = make([
        ["2026-10-01", "", "환전", "-1000", "KRW"],
        ["2026-10-01", "", "선물", "1000"],
        ["어제", "", "입금", "1000"],
        ["2026-10-01", "", "매수", "", "", "", "", "", ""],
        ["2026-10-02", "", "입금", "1000"],
    ])
    assert len(r.rows) == 1
    messages = [e.message for e in r.errors]
    assert any("묶음" in m for m in messages)
    assert any("알 수 없는 유형" in m for m in messages)
    assert any("일자" in m for m in messages)
    assert any("종목코드와 수량" in m for m in messages)


def test_downloaded_template_parses_to_no_rows_and_ignores_example_sheet():
    r = parse_file(build_template())
    assert r.format == "AssetHub" and r.rows == []
    assert "거래 행이 없습니다" in r.warnings[0]
