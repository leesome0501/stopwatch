from decimal import Decimal

from assethub.importer.dedupe import dedupe_keys
from assethub.importer.parsing import parse_moment
from assethub.importer.rows import ImportRow
from assethub.importer.sequence import chain_issues, order_rows

D = Decimal


def row(i, when, amount, balance=None, desc=""):
    return ImportRow(file_index=i, moment=parse_moment(when), kind="cash_in" if amount > 0 else "cash_out",
                     amount=D(amount), balance_after=None if balance is None else D(balance), description=desc)


def test_newest_first_file_is_reversed():
    rows = [row(0, "2026-10-03 10:00", -10, 80), row(1, "2026-10-02 10:00", -10, 90), row(2, "2026-10-01 10:00", 100, 100)]
    ordered, direction = order_rows(rows)
    assert direction == "newest-first"
    assert [r.file_index for r in ordered] == [2, 1, 0]
    assert chain_issues(ordered) == []


def test_same_time_bank_rows_default_newest_first():
    rows = [row(0, "2026-10-01 10:00", -10, 80), row(1, "2026-10-01 10:00", -10, 90)]
    ordered, direction = order_rows(rows)
    assert direction == "newest-first" and [r.file_index for r in ordered] == [1, 0]


def test_same_time_rows_flipped_when_balance_says_so():
    # 시각이 같은데 실제로는 위가 먼저인 파일: 기본(최신→과거)으로는 잔액이 안 이어진다
    rows = [row(0, "2026-10-01 10:00", 100, 100), row(1, "2026-10-01 10:00", -10, 90), row(2, "2026-10-01 10:00", -10, 80)]
    ordered, direction = order_rows(rows)
    assert direction == "oldest-first" and [r.file_index for r in ordered] == [0, 1, 2]


def test_date_only_ledger_defaults_oldest_first():
    rows = [row(0, "2026-10-01", 100), row(1, "2026-10-01", -10)]
    _, direction = order_rows(rows)
    assert direction == "oldest-first"


def test_chain_issue_reported():
    rows = [row(0, "2026-10-01 10:00", 100, 100), row(1, "2026-10-01 11:00", -10, 80, desc="커피")]
    issues = chain_issues(rows)
    assert len(issues) == 1 and "커피" in issues[0] and "예상 90" in issues[0]


def test_balance_key_ignores_time_of_day():
    """같은 거래를 시각 있는 파일과 날짜만 있는 파일로 받아도 같은 키여야 한다."""
    a = dedupe_keys([row(0, "2026-10-01 13:05", -5000, 95000)], ["KRW"])
    b = dedupe_keys([row(0, "2026-10-01", -5000, 95000)], ["KRW"])
    assert a == b and a[0].startswith("bal:2026-10-01|KRW|-5000|95000")


def test_rows_without_balance_get_occurrence_number():
    keys = dedupe_keys([row(0, "2026-10-01 10:00", -4500, desc="커피"), row(1, "2026-10-01 10:00", -4500, desc="커피")],
                       ["KRW", "KRW"])
    assert keys[0] != keys[1] and keys[0].endswith("#1") and keys[1].endswith("#2")
