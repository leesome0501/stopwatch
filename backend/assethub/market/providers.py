"""시세·환율 소스.

네이버 금융 API 는 공식 공개 API 가 아니라 화면이 쓰는 내부 API 다. 형식이 바뀌면
여기만 고치면 되도록 소스별로 분리했다. 2단계에서 한국투자증권 API 를 붙이면
같은 인터페이스로 추가한다.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol

import httpx

UA = "Mozilla/5.0 (AssetHub personal finance; +https://github.com/leesome0501)"
NAVER = "https://api.stock.naver.com"
UPBIT = "https://api.upbit.com"

KR_MARKETS = {"KRX", "KOSPI", "KOSDAQ", "KONEX"}
US_MARKETS = {"NASDAQ", "NYSE", "AMEX", "NYSEARCA", "ARCA", "BATS", "US"}


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Quote:
    day: date
    close: Decimal


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"},
                        timeout=15.0, transport=transport, follow_redirects=True)


def _num(v) -> Decimal:
    return Decimal(str(v).replace(",", ""))


def _get_json(client: httpx.Client, url: str, params: dict | None = None, *, allow_404: bool = False):
    try:
        r = client.get(url, params=params)
    except httpx.HTTPError as e:
        raise ProviderError(f"연결 실패: {e.__class__.__name__}") from e
    if allow_404 and r.status_code in (404, 409):
        return None
    if r.status_code >= 400:
        raise ProviderError(f"HTTP {r.status_code}: {r.text[:120]}")
    try:
        return r.json()
    except ValueError as e:
        raise ProviderError("응답이 JSON 이 아닙니다") from e


class PriceProvider(Protocol):
    name: str

    def supports(self, inst: dict) -> bool: ...

    def fetch(self, client: httpx.Client, inst: dict, start: date, end: date) -> tuple[list[Quote], str | None]:
        """(일별 종가, 찾아낸 price_code)."""
        ...


def _dt_range(start: date, end: date) -> dict:
    return {"startDateTime": f"{start:%Y%m%d}0000", "endDateTime": f"{end:%Y%m%d}2359"}


def _naver_chart(rows) -> list[Quote]:
    if not isinstance(rows, list):
        raise ProviderError("예상과 다른 응답 형식")
    return [Quote(datetime.strptime(r["localDate"], "%Y%m%d").date(), _num(r["closePrice"])) for r in rows]


def _require_some(quotes: list[Quote], start: date, end: date, code: str) -> list[Quote]:
    # 휴장일만 낀 짧은 구간은 빈 결과가 정상. 열흘 넘게 비면 코드가 틀린 것으로 본다
    if not quotes and (end - start).days > 10:
        raise ProviderError(f"{code}: 시세가 없습니다. 종목코드를 확인해 주세요.")
    return quotes


class NaverDomestic:
    name = "naver"

    def supports(self, inst: dict) -> bool:
        return (inst.get("market") or "").upper() in KR_MARKETS and bool(inst.get("symbol"))

    def fetch(self, client, inst, start, end):
        code = inst.get("price_code") or inst["symbol"]
        rows = _get_json(client, f"{NAVER}/chart/domestic/item/{code}/day", _dt_range(start, end))
        return _require_some(_naver_chart(rows), start, end, code), code


def _norm_symbol(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


class NaverForeign:
    """미국 주식·ETF. 네이버 코드는 거래소마다 접미사가 달라(나스닥 .O, NYSE 없음,
    아멕스 일부 .K, BRK.B → BRKb) 후보를 차례로 확인해 찾고 instrument.price_code 에 저장한다."""
    name = "naver"

    def supports(self, inst: dict) -> bool:
        return (inst.get("market") or "").upper() in US_MARKETS and bool(inst.get("symbol"))

    @staticmethod
    def candidates(symbol: str, market: str) -> list[str]:
        sym = symbol.upper()
        bases = [sym]
        if "." in sym or "/" in sym or " " in sym:
            base, cls = re.split(r"[./ ]", sym, maxsplit=1)
            bases = [base + cls.lower(), sym]
        order = {"NASDAQ": [".O", "", ".K"], "NYSE": ["", ".N", ".K"]}.get(market.upper(), ["", ".K", ".O"])
        out: list[str] = []
        for b in bases:
            for suffix in order:
                if b + suffix not in out:
                    out.append(b + suffix)
        return out

    def resolve(self, client, inst) -> str:
        if inst.get("price_code"):
            return inst["price_code"]
        want = _norm_symbol(inst["symbol"])
        for code in self.candidates(inst["symbol"], inst.get("market") or ""):
            info = _get_json(client, f"{NAVER}/stock/{code}/basic", allow_404=True)
            if info and _norm_symbol(str(info.get("symbolCode", ""))) == want:
                return code
        raise ProviderError(f"{inst['symbol']}: 네이버에서 종목을 찾지 못했습니다.")

    def fetch(self, client, inst, start, end):
        code = self.resolve(client, inst)
        rows = _get_json(client, f"{NAVER}/chart/foreign/item/{code}/day", _dt_range(start, end))
        return _require_some(_naver_chart(rows), start, end, code), code


class Upbit:
    """업비트 공식 API. 일봉은 한국시간 오전 9시에 시작한다. 한 번에 200개까지."""
    name = "upbit"
    PAGE = 200
    MAX_PAGES = 40

    def supports(self, inst: dict) -> bool:
        return (inst.get("market") or "").upper() == "UPBIT" and bool(inst.get("symbol"))

    def fetch(self, client, inst, start, end):
        code = inst.get("price_code") or inst["symbol"]
        to = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        quotes: dict[date, Quote] = {}
        for _ in range(self.MAX_PAGES):
            rows = _get_json(client, f"{UPBIT}/v1/candles/days",
                             {"market": code, "count": self.PAGE, "to": to.strftime("%Y-%m-%dT%H:%M:%SZ")})
            if not isinstance(rows, list):
                raise ProviderError("예상과 다른 응답 형식")
            for r in rows:
                d = date.fromisoformat(r["candle_date_time_kst"][:10])
                if start <= d <= end:
                    quotes[d] = Quote(d, _num(r["trade_price"]))
            if len(rows) < self.PAGE:
                break
            oldest = min(rows, key=lambda r: r["candle_date_time_utc"])
            to = datetime.fromisoformat(oldest["candle_date_time_utc"]).replace(tzinfo=timezone.utc)
            if to.date() <= start:
                break
        return sorted(quotes.values(), key=lambda q: q.day), code


class NaverFx:
    """원화 환율. 엔·루피아·동은 100단위 시세라 1단위로 바꾼다. 페이지당 최대 60일."""
    name = "naver"
    PAGE = 60
    MAX_PAGES = 200
    PER_100 = {"JPY", "IDR", "VND"}

    def fetch(self, client: httpx.Client, currency: str, start: date, end: date, delay: float = 0.0) -> list[Quote]:
        cur = currency.upper()
        unit = Decimal(100) if cur in self.PER_100 else Decimal(1)
        out: list[Quote] = []
        for page in range(1, self.MAX_PAGES + 1):
            rows = _get_json(client, f"{NAVER}/marketindex/exchange/FX_{cur}KRW/prices",
                             {"page": page, "pageSize": self.PAGE})
            if not isinstance(rows, list):
                raise ProviderError("예상과 다른 응답 형식")
            if not rows:
                if page == 1:
                    raise ProviderError(f"{cur}: 환율을 찾지 못했습니다.")
                break
            for r in rows:
                d = date.fromisoformat(r["localTradedAt"][:10])
                if start <= d <= end:
                    out.append(Quote(d, _num(r["closePrice"]) / unit))
            if date.fromisoformat(rows[-1]["localTradedAt"][:10]) < start or len(rows) < self.PAGE:
                break
            if delay:
                time.sleep(delay)
        return sorted(out, key=lambda q: q.day)


PRICE_PROVIDERS: list[PriceProvider] = [NaverDomestic(), NaverForeign(), Upbit()]


def provider_for(inst: dict, providers: list[PriceProvider] | None = None) -> PriceProvider | None:
    return next((p for p in (providers or PRICE_PROVIDERS) if p.supports(inst)), None)
