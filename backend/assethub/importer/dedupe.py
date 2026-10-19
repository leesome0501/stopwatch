"""중복 판정 키.

사업자관리(ADMIN) transactionDedupe.ts 의 결론을 따른다: 같은 실거래라도 어떤 파일은
시각을, 어떤 파일은 날짜만 준다. 그래서 거래 후 잔액이 있으면
'한국 날짜 + 금액 + 거래 후 잔액' 을 키로 쓴다. 잔액은 그 순간의 누적값이라
같은 날 같은 금액에 잔액까지 같은 다른 거래는 사실상 없다.
잔액이 없으면 일시·유형·금액·종목·적요에 같은 파일 안 순번을 붙여 해시한다.
증권사 API 처럼 소스가 고유 거래번호(external_id)를 주면 그것을 가장 먼저 쓴다.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from decimal import Decimal

from .rows import ImportRow


def _num(d: Decimal | None) -> str:
    if d is None:
        return ""
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def dedupe_keys(rows: list[ImportRow], currencies: list[str]) -> list[str]:
    """rows 와 같은 순서의 키 목록. currencies 는 각 행의 실제 통화."""
    seen: Counter[str] = Counter()
    keys: list[str] = []
    for r, cur in zip(rows, currencies, strict=True):
        if r.external_id:
            keys.append(f"ext:{r.external_id}")
            continue
        if r.balance_after is not None:
            keys.append(f"bal:{r.moment.day}|{cur}|{_num(r.amount)}|{_num(r.balance_after)}")
            continue
        when = r.moment.at.isoformat() if r.moment.has_time else r.moment.day.isoformat()
        base = "|".join([when, r.kind, cur, _num(r.amount), r.instrument_symbol or "",
                         _num(r.quantity), r.description or ""])
        seen[base] += 1
        digest = hashlib.sha1(base.encode()).hexdigest()[:24]
        keys.append(f"row:{digest}#{seen[base]}")
    return keys
