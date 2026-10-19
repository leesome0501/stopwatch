"""파일 행을 실제 발생 순서(과거→최신)로 세우고, 거래 후 잔액이 이어지는지 검증한다.

사업자관리(ADMIN) transactionSequence.ts 에서 확인된 규칙:
  1. 파일에 날짜가 둘 이상이면 날짜로 방향을 정한다.
  2. 전부 같은 시각이면, 시각이 있는 은행 파일은 최신→과거, 날짜만 있는 파일은 과거→최신이 기본.
     단 기본 방향으로 잔액이 안 이어지고 반대로는 이어지면 잔액을 근거로 뒤집는다.
잔액 불일치는 저장을 막지 않고 경고로 보여준다.
"""
from __future__ import annotations

from decimal import Decimal

from .rows import ImportRow

BALANCE_EPS = Decimal(1)
MAX_ISSUES = 5


def chain_issues(rows: list[ImportRow], limit: int = MAX_ISSUES) -> list[str]:
    """과거→최신 순서의 행에서 '직전 잔액 + 금액 = 잔액' 이 깨지는 곳."""
    issues: list[str] = []
    prev: dict[str | None, Decimal] = {}
    for r in rows:
        if r.balance_after is None:
            continue
        cur = r.currency
        if cur in prev:
            expected = prev[cur] + r.amount
            if abs(expected - r.balance_after) > BALANCE_EPS and len(issues) < limit:
                when = r.moment.at.strftime("%Y-%m-%d %H:%M") if r.moment.has_time else r.moment.day.isoformat()
                issues.append(f"{when} '{r.description}' 거래 후 잔액이 맞지 않습니다 "
                              f"(예상 {expected:,.0f}, 파일 {r.balance_after:,.0f})")
        prev[cur] = r.balance_after
    return issues


def _count_breaks(rows: list[ImportRow]) -> int:
    return len(chain_issues(rows, limit=10**9))


def order_rows(rows: list[ImportRow]) -> tuple[list[ImportRow], str]:
    """(과거→최신으로 정렬된 행, 파일 방향 'oldest-first' | 'newest-first')."""
    if len(rows) < 2:
        return list(rows), "oldest-first"
    first, last = rows[0].moment.at, rows[-1].moment.at
    if first < last:
        direction = "oldest-first"
    elif first > last:
        direction = "newest-first"
    else:
        has_time = any(r.moment.has_time for r in rows)
        default = "newest-first" if has_time else "oldest-first"
        other = "oldest-first" if default == "newest-first" else "newest-first"

        def orient(d: str) -> list[ImportRow]:
            return list(rows) if d == "oldest-first" else list(reversed(rows))

        direction = default
        if _count_breaks(orient(default)) > 0 and _count_breaks(orient(other)) == 0:
            direction = other
    oriented = list(rows) if direction == "oldest-first" else list(reversed(rows))
    # 정렬은 안정적이라 같은 시각끼리는 방향을 맞춘 파일 순서가 유지된다
    return sorted(oriented, key=lambda r: r.moment.at), direction
