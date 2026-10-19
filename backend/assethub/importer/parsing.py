"""셀 문자열을 금액·날짜로 바꾸는 함수들.

사업자관리(ADMIN) 프로젝트의 은행 거래내역 파서에서 실제로 겪은 사례를 반영했다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

_AMOUNT_JUNK = re.compile(r"[,\s원₩$]|KRW|USD", re.IGNORECASE)


def parse_amount(value: object) -> Decimal:
    """'1,234,000', '1,234원', '(5,000)', '-', '' 같은 셀을 Decimal로. 빈 값은 0."""
    if value is None:
        return Decimal(0)
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    s = str(value).strip()
    negative = s.startswith("(") and s.endswith(")")
    s = _AMOUNT_JUNK.sub("", s.strip("()"))
    if s in ("", "-", "+"):
        return Decimal(0)
    try:
        d = Decimal(s)
    except InvalidOperation:
        # 셀 끝에 엉뚱한 글자가 붙은 경우 앞쪽 숫자만이라도 건진다
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if not m:
            raise ValueError(f"금액으로 읽을 수 없습니다: {value!r}")
        d = Decimal(m.group(0))
    return -d if negative else d


def parse_optional_amount(value: object) -> Decimal | None:
    if value is None or str(value).strip() in ("", "-"):
        return None
    return parse_amount(value)


@dataclass(frozen=True)
class ParsedMoment:
    at: datetime   # KST aware
    has_time: bool

    @property
    def day(self) -> date:
        return self.at.astimezone(KST).date()


_DATE_TIME = re.compile(
    r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?"
    r"(?:[^\d]{0,3}(\d{1,2}):?(\d{2})(?::?(\d{2}))?)?"
)


def _build(y: int, mo: int, d: int, h: int | None, mi: int | None, s: int | None) -> ParsedMoment | None:
    try:
        if h is None:
            return ParsedMoment(datetime(y, mo, d, tzinfo=KST), False)
        return ParsedMoment(datetime(y, mo, d, h, mi or 0, s or 0, tzinfo=KST), True)
    except ValueError:
        return None


def parse_moment(date_value: object, time_value: object = None) -> ParsedMoment | None:
    """'2026.10.01 13:45:10', '2026-10-01', '20261001', '2026/10/01 13:45' + 별도 시간 칸.

    시각이 없는 파일과 있는 파일이 섞이므로 has_time 을 함께 돌려준다.
    시간대가 없는 값은 한국 시각으로 해석한다.
    """
    if isinstance(date_value, datetime):
        at = date_value if date_value.tzinfo else date_value.replace(tzinfo=KST)
        has_time = at.time() != time(0)
        return ParsedMoment(at.astimezone(KST), has_time)
    if isinstance(date_value, date):
        date_value = date_value.isoformat()

    ds = str(date_value or "").strip()
    ts = str(time_value or "").strip()
    if not ds:
        return None
    combined = f"{ds} {ts}".strip()

    m = _DATE_TIME.search(combined)
    if m:
        y, mo, d, h, mi, s = m.groups()
        return _build(int(y), int(mo), int(d),
                      int(h) if h else None, int(mi) if mi else None, int(s) if s else None)

    digits = re.sub(r"\D", "", combined)
    if len(digits) in (8, 12, 14):
        y, mo, d = int(digits[0:4]), int(digits[4:6]), int(digits[6:8])
        if len(digits) == 8:
            return _build(y, mo, d, None, None, None)
        return _build(y, mo, d, int(digits[8:10]), int(digits[10:12]),
                      int(digits[12:14]) if len(digits) == 14 else 0)
    return None


def norm_header(value: object) -> str:
    """헤더 비교용: 공백 제거."""
    return re.sub(r"\s+", "", str(value or ""))
