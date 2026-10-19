"""API 입출력 모델. 금액은 정밀도를 지키려고 JSON 에서 문자열로 주고받는다."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Relation = Literal["self", "spouse", "child", "parent", "sibling", "other"]
AccountType = Literal["checking", "savings", "time_deposit", "installment_savings", "cma", "brokerage",
                      "isa", "pension_savings", "irp", "dc_pension", "crypto", "credit_card", "loan",
                      "insurance", "real_asset", "cash", "other"]
TxnKind = Literal["cash_in", "cash_out", "buy", "sell", "dividend", "interest", "fee", "tax", "fx",
                  "instrument_in", "instrument_out", "split", "adjustment"]


class Row(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HouseholdIn(BaseModel):
    name: str = Field(min_length=1)


class Household(Row):
    id: int
    name: str
    created_at: datetime


class MemberIn(BaseModel):
    name: str = Field(min_length=1)
    relation: Relation
    birth_date: date | None = None
    is_dependent: bool = False


class MemberPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    relation: Relation | None = None
    birth_date: date | None = None
    is_dependent: bool | None = None


class HouseholdPatch(BaseModel):
    name: str = Field(min_length=1)


class HouseholdDelete(BaseModel):
    confirm_name: str   # 실수 방지: 가구 이름을 그대로 입력해야 지운다


class Institution(Row):
    id: int
    code: str
    name: str
    kind: str


class CategoryIn(BaseModel):
    name: str = Field(min_length=1)
    parent_id: int | None = None
    kind: Literal["income", "expense", "transfer"] | None = None   # 상위 카테고리를 새로 만들 때만


class CategoryRuleIn(BaseModel):
    match_field: Literal["description", "counterparty"] = "description"
    match_type: Literal["contains", "equals", "regex"] = "contains"
    pattern: str = Field(min_length=1)
    category_id: int
    account_id: int | None = None
    priority: int = 100


class CategoryRule(Row):
    id: int
    match_field: str
    match_type: str
    pattern: str
    category_id: int
    category_name: str
    account_id: int | None
    priority: int
    enabled: bool


class ReportedBalanceIn(BaseModel):
    as_of: date
    total_value: Decimal
    currency: str = Field(default="KRW", min_length=3, max_length=3)
    cash_amount: Decimal | None = None


class ReportedBalance(Row):
    as_of: date
    currency: str
    total_value: Decimal
    cash_amount: Decimal | None


class Member(Row):
    id: int
    household_id: int
    name: str
    relation: Relation
    birth_date: date | None
    is_dependent: bool


class OwnerShare(BaseModel):
    member_id: int
    share: Decimal = Field(default=Decimal(1), gt=0, le=1)


class AccountIn(BaseModel):
    name: str = Field(min_length=1)
    account_type: AccountType
    institution_code: str | None = None
    valuation_method: Literal["transactions", "reported"] = "transactions"
    base_currency: str = Field(default="KRW", min_length=3, max_length=3)
    account_number_masked: str | None = None
    visibility: Literal["household", "owners"] = "household"
    opened_on: date | None = None
    maturity_on: date | None = None
    interest_rate: Decimal | None = None
    memo: str | None = None
    owners: list[OwnerShare] = Field(min_length=1)


class AccountPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    institution_code: str | None = None
    opened_on: date | None = None
    account_number_masked: str | None = None
    visibility: Literal["household", "owners"] | None = None
    maturity_on: date | None = None
    closed_on: date | None = None
    interest_rate: Decimal | None = None
    memo: str | None = None


class Account(Row):
    id: int
    household_id: int
    name: str
    account_type: str
    institution_code: str | None
    institution_name: str | None
    valuation_method: str
    base_currency: str
    account_number_masked: str | None
    visibility: str
    opened_on: date | None
    maturity_on: date | None
    closed_on: date | None
    interest_rate: Decimal | None
    memo: str | None
    owners: list[OwnerShare]
    data_source_id: int | None = None     # 증권사 API 로 동기화되는 계좌면 연결 ID
    external_ref: str | None = None


class InstrumentIn(BaseModel):
    kind: Literal["stock", "etf", "etn", "fund", "bond", "reit", "crypto", "gold", "real_estate", "vehicle", "other"]
    asset_class: Literal["equity", "bond", "cash_equiv", "commodity", "crypto", "real_estate", "alternative", "mixed"]
    name: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    symbol: str | None = None
    market: str | None = None
    isin: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    household_id: int | None = None


class InstrumentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    asset_class: Literal["equity", "bond", "cash_equiv", "commodity", "crypto", "real_estate", "alternative", "mixed"] | None = None
    price_code: str | None = None


class PricePoint(Row):
    price_date: date
    close: Decimal
    source: str


class Instrument(Row):
    id: int
    kind: str
    asset_class: str
    name: str
    currency: str
    symbol: str | None
    market: str | None
    isin: str | None
    country: str | None
    household_id: int | None
    price_code: str | None = None


class PriceIn(BaseModel):
    price_date: date
    close: Decimal = Field(ge=0)
    source: str = "manual"


class FxRateIn(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    rate_date: date
    krw_rate: Decimal = Field(gt=0)
    source: str = "manual"


class Category(Row):
    id: int
    household_id: int | None
    parent_id: int | None
    name: str
    kind: str


class TxnIn(BaseModel):
    occurred_at: datetime
    kind: TxnKind
    amount: Decimal
    currency: str | None = None
    instrument_id: int | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal = Field(default=Decimal(0), ge=0)
    tax: Decimal = Field(default=Decimal(0), ge=0)
    category_id: int | None = None
    counterparty: str | None = None
    description: str | None = None
    memo: str | None = None
    group_id: UUID | None = None


class TxnPatch(BaseModel):
    category_id: int | None = None
    description: str | None = None
    counterparty: str | None = None
    memo: str | None = None
    group_id: UUID | None = None


class Txn(Row):
    id: int
    account_id: int
    occurred_at: datetime
    trade_date: date
    kind: str
    amount: Decimal
    currency: str
    instrument_id: int | None
    quantity: Decimal | None
    unit_price: Decimal | None
    balance_after: Decimal | None
    fee: Decimal
    tax: Decimal
    category_id: int | None
    counterparty: str | None
    description: str | None
    memo: str | None
    group_id: UUID | None
    status: str


class TxnListItem(Txn):
    account_name: str
    category_name: str | None
    category_parent: str | None
    category_kind: str | None
    instrument_name: str | None
    instrument_symbol: str | None
    amount_krw: Decimal


class TxnPage(BaseModel):
    total: int
    sum_in_krw: Decimal
    sum_out_krw: Decimal
    items: list[TxnListItem]


class ImportRowOut(BaseModel):
    file_index: int
    status: Literal["new", "duplicate", "error"]
    occurred_at: datetime | None
    trade_date: date | None
    kind: str | None
    amount: Decimal | None
    currency: str | None
    description: str | None
    counterparty: str | None
    balance_after: Decimal | None
    instrument_symbol: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    category_id: int | None
    category_name: str | None
    category_source: str | None   # file | rule | history | kind
    message: str | None


class ImportResult(BaseModel):
    committed: bool
    batch_id: int | None
    format: str | None
    file_direction: str | None
    account_number: str | None
    counts: dict[str, int]
    opening_balance: Decimal | None
    warnings: list[str]
    rows: list[ImportRowOut]


class ImportBatch(Row):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    file_name: str | None
    records_total: int
    records_new: int
    records_duplicate: int
    error: str | None
