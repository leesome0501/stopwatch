"""은행 거래내역 엑셀 형식.

우리·신한·하나(법인/개인)·IBK·이체내역 형식은 사업자관리(ADMIN) 프로젝트의
transactionParse.ts 를 옮긴 것이다. 그 밖의 은행은 마지막의 Generic 형식이
헤더 이름으로 컬럼을 찾아 처리한다.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from .parsing import norm_header, parse_amount, parse_moment, parse_optional_amount
from .reader import Matrix
from .rows import ImportRow, ParseResult, RowError

HEADER_SCAN_ROWS = 15


def _col(header: list[str], keys: list[str]) -> int | None:
    """정확히 같은 헤더를 먼저, 없으면 포함하는 헤더를 찾는다."""
    for k in keys:
        if k in header:
            return header.index(k)
    for k in keys:
        for i, h in enumerate(header):
            if k in h:
                return i
    return None


def _has(header: list[str], key: str) -> bool:
    return any(key in h for h in header)


def _paired(header: list[str], wd_keys: list[str], dep_keys: list[str], withdrawal_first: bool):
    """입금/출금 중 하나만 찾았으면(병합 헤더) 옆 칸을 짝으로 본다."""
    wd, dep = _col(header, wd_keys), _col(header, dep_keys)
    if withdrawal_first:
        if wd is not None and dep is None:
            dep = wd + 1
        elif dep is not None and wd is None:
            wd = dep - 1
    else:
        if dep is not None and wd is None:
            wd = dep + 1
        elif wd is not None and dep is None:
            dep = wd - 1
    return wd, dep


def _cell(row: list[str], i: int | None) -> str:
    if i is None or i < 0 or i >= len(row):
        return ""
    return str(row[i] or "").strip()


@dataclass
class Columns:
    date: int | None
    time: int | None = None
    withdrawal: int | None = None
    deposit: int | None = None
    signed_amount: int | None = None   # 거래금액 한 칸 + 구분 칸
    direction: int | None = None
    balance: int | None = None
    memo: list[int | None] | None = None
    counterparty: int | None = None
    status: int | None = None


@dataclass
class BankFormat:
    name: str
    detect: Callable[[list[str]], bool]
    columns: Callable[[list[str]], Columns]
    # 적요 칸이 여럿일 때 합치는 방식
    memo_join: str = "first"   # "first": 처음 비지 않은 값, "join": 공백으로 이어붙임
    counterparty_from_memo: bool = False


def _woori(h):
    wd, dep = _paired(h, ["찾으신금액"], ["맡기신금액"], True)
    return Columns(date=_col(h, ["거래일시"]), withdrawal=wd, deposit=dep,
                   balance=_col(h, ["거래후"]),
                   memo=[_col(h, ["기재내용"]), _col(h, ["적요"])])


def _shinhan(h):
    wd, dep = _paired(h, ["출금"], ["입금"], True)
    return Columns(date=_col(h, ["거래일자"]), time=_col(h, ["거래시간"]), withdrawal=wd, deposit=dep,
                   balance=_col(h, ["잔액"]), memo=[_col(h, ["내용"]), _col(h, ["적요"])])


def _hana_corp(h):
    wd, dep = _paired(h, ["출금"], ["입금"], False)
    return Columns(date=_col(h, ["거래일시"]), withdrawal=wd, deposit=dep,
                   balance=_col(h, ["거래후", "잔액"]), memo=[_col(h, ["적요"])],
                   counterparty=_col(h, ["의뢰인/수취인"]))


def _hana_personal(h):
    wd, dep = _paired(h, ["출금액", "출금"], ["입금액", "입금"], True)
    return Columns(date=_col(h, ["거래일시"]), withdrawal=wd, deposit=dep,
                   balance=_col(h, ["잔액"]), memo=[_col(h, ["구분"]), _col(h, ["적요"])])


def _ibk(h):
    wd, dep = _paired(h, ["출금"], ["입금"], True)
    return Columns(date=_col(h, ["거래일시"]), withdrawal=wd, deposit=dep,
                   balance=_col(h, ["거래후", "잔액"]), memo=[_col(h, ["거래내용"])],
                   counterparty=_col(h, ["상대계좌예금주명"]))


def _transfer_history(h):
    return Columns(date=_col(h, ["이체일시"]), withdrawal=_col(h, ["이체금액"]),
                   memo=[_col(h, ["내통장표시"]), _col(h, ["메모"])],
                   counterparty=_col(h, ["받는분"]), status=_col(h, ["처리결과"]))


_GENERIC_DATE = ["거래일시", "거래일자", "거래일", "일시", "날짜", "일자"]


def _generic(h):
    wd = _col(h, ["출금액", "출금", "찾으신금액", "지급액", "지급"])
    dep = _col(h, ["입금액", "입금", "맡기신금액"])
    signed = direction = None
    if wd is None and dep is None:
        signed = _col(h, ["거래금액", "금액"])
        direction = _col(h, ["입출금구분", "구분", "거래구분"])
    return Columns(
        date=_col(h, _GENERIC_DATE), time=_col(h, ["거래시간", "시간", "시각"]),
        withdrawal=wd, deposit=dep, signed_amount=signed, direction=direction,
        balance=_col(h, ["거래후잔액", "잔액"]),
        memo=[_col(h, ["적요"]), _col(h, ["내용", "거래내용", "기재내용"]), _col(h, ["메모"])],
        counterparty=_col(h, ["보낸분/받는분", "받는분/보낸분", "의뢰인/수취인", "상대방", "거래처"]),
    )


def _generic_detect(h):
    c = _generic(h)
    return c.date is not None and (c.withdrawal is not None or c.deposit is not None or c.signed_amount is not None)


FORMATS: list[BankFormat] = [
    BankFormat("Woori", lambda h: _has(h, "찾으신금액") and _has(h, "맡기신금액"), _woori,
               counterparty_from_memo=True),
    BankFormat("Shinhan", lambda h: _has(h, "거래일자") and (_has(h, "출금") or _has(h, "입금"))
               and any(_has(h, k) for k in ("적요", "잔액", "거래시간", "거래점", "내용")), _shinhan),
    BankFormat("HanaCorp", lambda h: _has(h, "의뢰인/수취인") or (_has(h, "적요") and _has(h, "추가메모"))
               or (_has(h, "적요") and _has(h, "거래일시") and not _has(h, "거래내용")
                   and not _has(h, "출금액") and not _has(h, "입금액")
                   and (_has(h, "입금") or _has(h, "출금"))), _hana_corp),
    BankFormat("HanaPersonal", lambda h: _has(h, "거래일시") and _has(h, "구분") and _has(h, "적요")
               and (_has(h, "출금액") or _has(h, "입금액")), _hana_personal, memo_join="join"),
    BankFormat("IBK", lambda h: (_has(h, "거래일시") and _has(h, "출금") and _has(h, "입금") and _has(h, "거래후"))
               or (_has(h, "거래일시") and _has(h, "상대계좌번호") and _has(h, "상대은행"))
               or (_has(h, "거래일시") and _has(h, "입금") and _has(h, "거래내용")), _ibk),
    BankFormat("TransferHistory", lambda h: _has(h, "이체일시") and _has(h, "출금계좌")
               and _has(h, "입금계좌") and _has(h, "이체금액"), _transfer_history),
    BankFormat("Generic", _generic_detect, _generic, memo_join="join"),
]


_ACCOUNT_NO = re.compile(r"(\d[\d-]{4,20}\d)")


def _account_number(matrix: Matrix) -> str | None:
    for row in matrix[:10]:
        for i, c in enumerate(row):
            if "계좌번호" not in str(c):
                continue
            for text in (str(c), _cell(row, i + 1)):
                m = _ACCOUNT_NO.search(text)
                if m:
                    return m.group(1)
    return None


def _find_header(matrix: Matrix) -> int | None:
    for r, row in enumerate(matrix[:HEADER_SCAN_ROWS]):
        h = [norm_header(c) for c in row]
        has_date = any(("거래일" in c or "일시" in c or c in ("날짜", "일자")) for c in h)
        has_money = any(k in c for c in h for k in ("입금", "출금", "찾으신", "맡기신", "금액"))
        if has_date and has_money:
            return r
    return None


def _memo(row: list[str], cols: list[int | None] | None, how: str) -> str:
    values = [v for v in (_cell(row, i) for i in (cols or [])) if v]
    if not values:
        return ""
    if how == "join":
        seen: list[str] = []
        for v in values:
            if v not in seen:
                seen.append(v)
        return " ".join(seen)
    return values[0]


def parse_bank_matrix(matrix: Matrix) -> ParseResult | None:
    """은행 형식이 아니면 None."""
    hr = _find_header(matrix)
    if hr is None:
        return None
    header = [norm_header(c) for c in matrix[hr]]
    fmt = next((f for f in FORMATS if f.detect(header)), None)
    if fmt is None:
        return None
    cols = fmt.columns(header)
    result = ParseResult(format=fmt.name, rows=[], account_number=_account_number(matrix))
    raw_header = [str(c).strip() for c in matrix[hr]]

    for idx, row in enumerate(matrix[hr + 1:]):
        if not any(str(c).strip() for c in row):
            continue
        raw = {raw_header[i] or f"col{i}": str(v) for i, v in enumerate(row) if i < len(raw_header) and str(v).strip()}
        moment = parse_moment(_cell(row, cols.date), _cell(row, cols.time))
        if moment is None:
            continue  # 합계 행, 안내 문구 등
        status = _cell(row, cols.status)
        if status and "완료" not in status:
            continue  # 실패·취소된 이체
        try:
            if cols.signed_amount is not None:
                amount = parse_amount(_cell(row, cols.signed_amount))
                direction = _cell(row, cols.direction)
                if amount > 0 and ("출금" in direction or "지급" in direction):
                    amount = -amount
            else:
                amount = parse_amount(_cell(row, cols.deposit)) - parse_amount(_cell(row, cols.withdrawal))
            balance = parse_optional_amount(_cell(row, cols.balance)) if cols.balance is not None else None
        except ValueError as e:
            result.errors.append(RowError(idx, str(e), raw))
            continue
        if amount == 0:
            continue
        memo = _memo(row, cols.memo, fmt.memo_join)
        counterparty = _cell(row, cols.counterparty) or None
        if fmt.counterparty_from_memo and counterparty is None:
            detail, kind_text = _cell(row, cols.memo[0]), _cell(row, cols.memo[1])
            if detail and detail != kind_text:
                counterparty = detail
        result.rows.append(ImportRow(
            file_index=idx, moment=moment,
            kind="cash_in" if amount > 0 else "cash_out", amount=amount,
            description=memo, counterparty=counterparty, balance_after=balance, raw=raw,
        ))
    return result
