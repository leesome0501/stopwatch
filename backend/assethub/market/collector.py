"""보유·거래 종목과 쓰이는 외화를 찾아, DB에 없는 기간의 시세·환율만 받아 저장한다.

이미 받은 날짜도 마지막 일주일은 다시 받는다 (장 마감 후 수정되는 종가 대비).
어디서부터 받을지는 자동 수집분만 보고 정한다 (수동 시세 하나가 앞 기간을 막지 않게).
수동 입력 시세(source='manual')는 덮어쓰지 않는다.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import httpx
from psycopg.types.json import Jsonb

from ..db import Conn
from ..importer.parsing import KST
from .providers import NaverFx, PriceProvider, ProviderError, Quote, make_client, provider_for

OVERLAP = timedelta(days=7)
DEFAULT_LOOKBACK = timedelta(days=30)
EARLIEST = date(2000, 1, 1)


def today_kst() -> date:
    from datetime import datetime
    return datetime.now(KST).date()


def price_targets(conn: Conn) -> list[dict]:
    """거래 내역이나 보고된 보유 내역에 나오는 종목."""
    return conn.execute(
        """SELECT i.id, i.name, i.symbol, i.market, i.currency, i.kind, i.price_code,
                  (SELECT max(price_date) FROM price p WHERE p.instrument_id = i.id AND p.source <> 'manual') AS last_price,
                  (SELECT min(trade_date) FROM txn t WHERE t.instrument_id = i.id AND t.status = 'posted') AS first_trade
             FROM instrument i
            WHERE EXISTS (SELECT 1 FROM txn t WHERE t.instrument_id = i.id AND t.status = 'posted')
               OR EXISTS (SELECT 1 FROM reported_holding h WHERE h.instrument_id = i.id)
            ORDER BY i.id""").fetchall()


def fx_targets(conn: Conn) -> list[dict]:
    return conn.execute(
        """WITH used AS (
               SELECT currency, min(trade_date) AS first_day FROM txn WHERE status = 'posted' GROUP BY currency
               UNION ALL
               SELECT i.currency, min(t.trade_date) FROM txn t JOIN instrument i ON i.id = t.instrument_id
                GROUP BY i.currency
               UNION ALL
               SELECT currency, min(as_of) FROM reported_balance GROUP BY currency)
           SELECT u.currency, min(u.first_day) AS first_day,
                  (SELECT max(rate_date) FROM fx_rate f WHERE f.currency = u.currency AND f.source <> 'manual') AS last_rate
             FROM used u WHERE u.currency <> 'KRW'
            GROUP BY u.currency ORDER BY u.currency""").fetchall()


def _start(last: date | None, first_use: date | None, today: date) -> date:
    if last:
        return max(last - OVERLAP, EARLIEST)
    if first_use:
        return max(first_use - OVERLAP, EARLIEST)
    return today - DEFAULT_LOOKBACK


def _upsert_prices(conn: Conn, instrument_id: int, quotes: list[Quote], source: str) -> int:
    n = 0
    for q in quotes:
        cur = conn.execute(
            """INSERT INTO price (instrument_id, price_date, close, source) VALUES (%s, %s, %s, %s)
               ON CONFLICT (instrument_id, price_date) DO UPDATE
                  SET close = EXCLUDED.close, source = EXCLUDED.source, fetched_at = now()
                WHERE price.source <> 'manual'""",
            (instrument_id, q.day, q.close, source))
        n += cur.rowcount
    return n


def _upsert_fx(conn: Conn, currency: str, quotes: list[Quote], source: str) -> int:
    n = 0
    for q in quotes:
        cur = conn.execute(
            """INSERT INTO fx_rate (currency, rate_date, krw_rate, source) VALUES (%s, %s, %s, %s)
               ON CONFLICT (currency, rate_date) DO UPDATE
                  SET krw_rate = EXCLUDED.krw_rate, source = EXCLUDED.source
                WHERE fx_rate.source <> 'manual'""",
            (currency, q.day, q.close, source))
        n += cur.rowcount
    return n


def collect(conn: Conn, client: httpx.Client | None = None, *, providers: list[PriceProvider] | None = None,
            fx_provider: NaverFx | None = None, today: date | None = None, delay: float = 0.2) -> dict:
    """한 번 수집하고 요약을 돌려준다. 종목 하나가 실패해도 나머지는 계속한다."""
    own_client = client is None
    client = client or make_client()
    today = today or today_kst()
    fx_provider = fx_provider or NaverFx()
    run_id = conn.execute("INSERT INTO market_sync_run DEFAULT VALUES RETURNING id").fetchone()["id"]
    errors: list[dict] = []
    skipped: list[str] = []
    prices = fx = 0
    try:
        for inst in price_targets(conn):
            label = inst["symbol"] or inst["name"]
            provider = provider_for(inst, providers)
            if provider is None:
                skipped.append(label)   # 부동산 등 수동 시세 대상
                continue
            start = _start(inst["last_price"], inst["first_trade"], today)
            try:
                quotes, code = provider.fetch(client, inst, start, today)
                with conn.transaction():
                    prices += _upsert_prices(conn, inst["id"], quotes, provider.name)
                    if code and code != inst["price_code"]:
                        conn.execute("UPDATE instrument SET price_code = %s WHERE id = %s", (code, inst["id"]))
            except ProviderError as e:
                errors.append({"target": label, "message": str(e)})
            if delay:
                time.sleep(delay)

        for row in fx_targets(conn):
            cur = row["currency"]
            start = _start(row["last_rate"], row["first_day"], today)
            try:
                quotes = fx_provider.fetch(client, cur, start, today, delay=delay)
                with conn.transaction():
                    fx += _upsert_fx(conn, cur, quotes, fx_provider.name)
            except ProviderError as e:
                errors.append({"target": cur, "message": str(e)})
    finally:
        if own_client:
            client.close()

    status = "succeeded" if not errors else ("partial" if prices or fx else "failed")
    conn.execute(
        """UPDATE market_sync_run SET finished_at = now(), status = %s, prices_upserted = %s,
                  fx_upserted = %s, errors = %s WHERE id = %s""",
        (status, prices, fx, Jsonb(errors), run_id))
    return {"run_id": run_id, "status": status, "prices_upserted": prices, "fx_upserted": fx,
            "errors": errors, "manual_only": skipped}
