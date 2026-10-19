from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from ..db import Conn, get_conn
from ..schemas import FxRateIn, Instrument, InstrumentIn, InstrumentPatch, PriceIn, PricePoint
from .common import require

router = APIRouter(tags=["종목·시세"])


@router.get("/api/instruments", response_model=list[Instrument])
def search_instruments(q: str = "", household_id: int | None = None, limit: int = 50,
                       conn: Conn = Depends(get_conn)):
    like = f"%{q}%"
    return conn.execute(
        """SELECT * FROM instrument
            WHERE (household_id IS NULL OR household_id = %s)
              AND (%s = '' OR name ILIKE %s OR symbol ILIKE %s OR isin = %s)
            ORDER BY name LIMIT %s""",
        (household_id, q, like, like, q, min(limit, 200))).fetchall()


@router.post("/api/instruments", response_model=Instrument, status_code=201)
def create_instrument(body: InstrumentIn, conn: Conn = Depends(get_conn)):
    try:
        with conn.transaction():
            return conn.execute(
                """INSERT INTO instrument (kind, asset_class, symbol, market, isin, name, currency,
                                           country, household_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (body.kind, body.asset_class, body.symbol, body.market, body.isin, body.name,
                 body.currency.upper(), body.country, body.household_id)).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "같은 시장·종목코드 또는 ISIN 이 이미 있습니다.") from None


@router.put("/api/instruments/{instrument_id}/prices", status_code=204)
def upsert_prices(instrument_id: int, body: list[PriceIn], conn: Conn = Depends(get_conn)):
    require(conn, "instrument", instrument_id, "종목")
    for p in body:
        conn.execute(
            """INSERT INTO price (instrument_id, price_date, close, source) VALUES (%s,%s,%s,%s)
               ON CONFLICT (instrument_id, price_date)
               DO UPDATE SET close = EXCLUDED.close, source = EXCLUDED.source, fetched_at = now()""",
            (instrument_id, p.price_date, p.close, p.source))


@router.put("/api/fx-rates", status_code=204)
def upsert_fx_rates(body: list[FxRateIn], conn: Conn = Depends(get_conn)):
    for r in body:
        if r.currency.upper() == "KRW":
            raise HTTPException(422, "KRW 환율은 항상 1이라 넣을 필요가 없습니다.")
        conn.execute(
            """INSERT INTO fx_rate (currency, rate_date, krw_rate, source) VALUES (%s,%s,%s,%s)
               ON CONFLICT (currency, rate_date)
               DO UPDATE SET krw_rate = EXCLUDED.krw_rate, source = EXCLUDED.source""",
            (r.currency.upper(), r.rate_date, r.krw_rate, r.source))


@router.patch("/api/instruments/{instrument_id}", response_model=Instrument)
def patch_instrument(instrument_id: int, body: InstrumentPatch, conn: Conn = Depends(get_conn)):
    require(conn, "instrument", instrument_id, "종목")
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "price_code"}
    if changes:
        sets = ", ".join(f"{k} = %s" for k in changes)
        conn.execute(f"UPDATE instrument SET {sets} WHERE id = %s", (*changes.values(), instrument_id))
    return conn.execute("SELECT * FROM instrument WHERE id = %s", (instrument_id,)).fetchone()


@router.get("/api/instruments/{instrument_id}/prices", response_model=list[PricePoint])
def recent_prices(instrument_id: int, limit: int = 30, conn: Conn = Depends(get_conn)):
    require(conn, "instrument", instrument_id, "종목")
    return conn.execute("""SELECT price_date, close, source FROM price WHERE instrument_id = %s
                            ORDER BY price_date DESC LIMIT %s""", (instrument_id, min(limit, 1000))).fetchall()


@router.delete("/api/instruments/{instrument_id}/prices/{price_date}", status_code=204)
def delete_price(instrument_id: int, price_date: str, conn: Conn = Depends(get_conn)):
    require(conn, "instrument", instrument_id, "종목")
    conn.execute("DELETE FROM price WHERE instrument_id = %s AND price_date = %s::date", (instrument_id, price_date))
