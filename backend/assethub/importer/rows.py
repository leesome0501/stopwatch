"""모든 파일 형식이 공통으로 내놓는 행."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .parsing import ParsedMoment


@dataclass
class ImportRow:
    file_index: int                  # 파일 안 원래 위치 (0 = 맨 위 데이터 행)
    moment: ParsedMoment
    kind: str                        # txn.kind
    amount: Decimal                  # 계좌 입장 현금 변화 (부호 포함)
    description: str = ""            # 소스 원문 적요
    counterparty: str | None = None
    balance_after: Decimal | None = None
    currency: str | None = None      # None 이면 계좌 기본 통화
    instrument_symbol: str | None = None
    instrument_market: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal = Decimal(0)
    tax: Decimal = Decimal(0)
    category_name: str | None = None
    memo: str | None = None
    group_label: str | None = None
    raw: dict[str, str] = field(default_factory=dict)
    external_id: str | None = None       # 증권사 API 의 거래번호처럼 소스가 주는 고유 ID (중복 판정에 우선 사용)
    instrument_name: str | None = None   # API 로 받은 종목명 (종목 자동 등록용)


@dataclass
class RowError:
    file_index: int
    message: str
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class ParseResult:
    format: str | None
    rows: list[ImportRow]
    errors: list[RowError] = field(default_factory=list)
    account_number: str | None = None
    warnings: list[str] = field(default_factory=list)
