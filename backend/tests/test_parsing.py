from datetime import datetime
from decimal import Decimal

import pytest

from assethub.importer.parsing import KST, parse_amount, parse_moment


@pytest.mark.parametrize("raw, expected", [
    ("1,234,000", "1234000"), ("1,234원", "1234"), ("(5,000)", "-5000"), ("-", "0"), ("", "0"),
    ("3.40", "3.40"), ("-50,000", "-50000"), ("58,046,690 _", "58046690"), (1500.0, "1500.0"), (7, "7"),
    ("₩ 12,000", "12000"),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


def test_parse_amount_rejects_text():
    with pytest.raises(ValueError):
        parse_amount("합계")


@pytest.mark.parametrize("date_s, time_s, expected, has_time", [
    ("2026.10.01 13:45:10", None, datetime(2026, 10, 1, 13, 45, 10, tzinfo=KST), True),
    ("2026-10-01", None, datetime(2026, 10, 1, tzinfo=KST), False),
    ("20261001", None, datetime(2026, 10, 1, tzinfo=KST), False),
    ("20261001134510", None, datetime(2026, 10, 1, 13, 45, 10, tzinfo=KST), True),
    ("2026/10/01", "09:05", datetime(2026, 10, 1, 9, 5, tzinfo=KST), True),
    ("2026년 10월 1일", None, datetime(2026, 10, 1, tzinfo=KST), False),
    ("2026.10.01", "093015", datetime(2026, 10, 1, 9, 30, 15, tzinfo=KST), True),
])
def test_parse_moment(date_s, time_s, expected, has_time):
    m = parse_moment(date_s, time_s)
    assert m.at == expected and m.has_time is has_time


def test_parse_moment_handles_excel_datetime_and_garbage():
    m = parse_moment(datetime(2026, 10, 1, 8, 0))
    assert m.at.tzinfo is not None and m.has_time
    assert parse_moment("2026-13-01") is None
    assert parse_moment("합계") is None
    assert parse_moment("") is None


def test_kst_day_does_not_shift():
    """자정 직후 거래가 UTC 로 잘려 전날이 되면 안 된다 (ADMIN 2026-10-12 점검 사례)."""
    m = parse_moment("2026-10-02 00:30")
    assert m.day.isoformat() == "2026-10-02"
