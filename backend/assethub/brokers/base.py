from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx

from ..importer.parsing import KST
from ..importer.rows import ImportRow

UA = "AssetHub/0.1 (family asset tracker; read-only)"
ETF_BRANDS = ("KODEX", "TIGER", "KBSTAR", "RISE", "ACE", "SOL", "HANARO", "ARIRANG", "KOSEF", "PLUS",
              "TIMEFOLIO", "KIWOOM", "BNK", "WON", "히어로즈", "마이티", "에셋플러스", "1Q", "TRUSTON", "UNICORN")


class BrokerError(RuntimeError):
    """증권사가 거절했거나 응답을 이해할 수 없을 때. 메시지는 사용자에게 그대로 보여 줘도 되는 문장."""


@dataclass
class BrokerAccount:
    ref: str            # AssetHub 가 계좌를 구분하는 값 (account.external_ref)
    label: str          # 화면 표시용


@dataclass
class SnapHolding:
    symbol: str
    name: str
    quantity: Decimal
    avg_price: Decimal | None
    price: Decimal | None
    currency: str = "KRW"
    market: str = "KRX"


@dataclass
class Snapshot:
    """증권사가 알려준 지금 이 순간의 계좌 상태. 결제 예정분까지 반영한 현금(D+2)을 쓴다."""
    cash: dict[str, Decimal]
    total_value: Decimal | None
    holdings: list[SnapHolding] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class Credentials:
    app_key: str
    app_secret: str
    environment: str = "real"           # real | mock
    accounts: list[str] = field(default_factory=list)   # KIS: '12345678-01' 목록
    token: str | None = None
    token_expires: str | None = None    # ISO 시각

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "Credentials":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


def num(v) -> Decimal:
    """'000000000012345', '-00000123', '+12.5', '' 같은 증권사 숫자 문자열."""
    if v is None:
        return Decimal(0)
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "+"):
        return Decimal(0)
    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise BrokerError(f"숫자로 읽을 수 없는 값: {v!r}") from e


def kr_symbol(code: str) -> str:
    """키움 'A005930' 같은 접두어를 뗀다."""
    code = (code or "").strip()
    return code[1:] if len(code) == 7 and code[0].isalpha() else code


def guess_kind(name: str) -> str:
    n = (name or "").upper()
    return "etf" if any(n.startswith(b.upper()) for b in ETF_BRANDS) else "stock"


def kst_moment(day: str, hms: str | None = None) -> datetime:
    """'20261015' + '093015' → KST datetime."""
    d = datetime.strptime(day[:8], "%Y%m%d")
    if hms:
        h = hms.replace(":", "").ljust(6, "0")[:6]
        d = d.replace(hour=int(h[0:2]), minute=int(h[2:4]), second=int(h[4:6]))
    return d.replace(tzinfo=KST)


class Throttle:
    """초당 호출 수 제한을 지키기 위한 최소 간격."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        gap = time.monotonic() - self._last
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
        self._last = time.monotonic()


class Connector:
    """증권사 어댑터의 공통 모양."""
    provider: str = ""
    name: str = ""
    ledger_has_cash: bool = False   # 입출금·배당·수수료까지 거래내역으로 주는가 (아니면 잔고 맞춤이 채운다)

    def __init__(self, creds: Credentials, client: httpx.Client,
                 on_token: Callable[[Credentials], None] | None = None, min_interval: float = 0.25):
        self.creds = creds
        self.client = client
        self.on_token = on_token or (lambda c: None)
        self.throttle = Throttle(min_interval)
        self.today = datetime.now(KST).date()   # 동기화 기준일 (테스트에서 바꿀 수 있게)

    def accounts(self) -> list[BrokerAccount]: raise NotImplementedError
    def ledger(self, ref: str, start: date, end: date) -> list[ImportRow]: raise NotImplementedError
    def snapshot(self, ref: str) -> Snapshot: raise NotImplementedError

    def _token_valid(self) -> bool:
        if not self.creds.token or not self.creds.token_expires:
            return False
        try:
            exp = datetime.fromisoformat(self.creds.token_expires)
        except ValueError:
            return False
        return (exp - datetime.now(KST)).total_seconds() > 300   # 5분 여유


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": UA}, timeout=20.0, transport=transport)
