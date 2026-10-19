"""증권사 연결 동기화.

계좌마다:
  1. 지난 동기화 이후(첫 동기화면 사용자가 고른 시작일부터) 거래를 받아 엑셀 가져오기와 같은 경로로 저장한다.
  2. 잔고 스냅샷을 받아 reported_balance / reported_holding 에 남긴다.
  3. 잔고 맞춤: 계산된 보유 수량·현금이 증권사 잔고와 다르면 차이만큼 조정 거래를 넣는다.
     - 첫 동기화: 시작일 이전부터 있던 보유분과 현금 → 시작일 전날 '기초 보유'로
     - 이후: API 가 주지 않는 수수료·세금·입출금·배당 등 → 그날 '잔고 맞춤'으로
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import httpx
from psycopg.types.json import Jsonb

from ..db import Conn
from ..importer import service
from ..importer.parsing import KST
from ..importer.rows import ParseResult
from ..secrets import decrypt_json, encrypt_json
from .base import BrokerError, Connector, Credentials, Snapshot, guess_kind, make_client
from .kis import Kis
from .kiwoom import Kiwoom

PROVIDERS: dict[str, type[Connector]] = {"kiwoom": Kiwoom, "kis": Kis}
INSTITUTION = {"kiwoom": "KIWOOM", "kis": "KIS"}
OVERLAP = timedelta(days=7)          # 지난 동기화와 겹쳐 받는 기간 (늦게 반영되는 거래 대비)
DEFAULT_LOOKBACK = timedelta(days=365)
KR_MARKETS = ("KRX", "KOSPI", "KOSDAQ", "KONEX")


def load_source(conn: Conn, source_id: int) -> dict:
    ds = conn.execute("SELECT * FROM data_source WHERE id = %s", (source_id,)).fetchone()
    if ds is None or ds["provider"] not in PROVIDERS:
        raise BrokerError("증권사 연결을 찾을 수 없습니다.")
    return ds


def connector_for(conn: Conn, ds: dict, client: httpx.Client, min_interval: float = 0.25) -> Connector:
    creds = Credentials.from_dict(decrypt_json(ds["credential_enc"]))
    if not creds.app_key:
        raise BrokerError("앱키가 없습니다. 연결을 다시 설정하세요.")

    def save_token(c: Credentials) -> None:
        # 토큰을 저장해 두어 다시 발급받지 않는다 (한국투자는 발급마다 알림톡이 간다)
        conn.execute("UPDATE data_source SET credential_enc = %s WHERE id = %s", (encrypt_json(c.to_dict()), ds["id"]))

    return PROVIDERS[ds["provider"]](creds, client, on_token=save_token, min_interval=min_interval)


def ensure_instruments(conn: Conn, rows, holdings) -> None:
    """API 로 받은 국내 종목이 종목 마스터에 없으면 등록한다."""
    wanted: dict[str, str] = {}
    for r in rows:
        if r.instrument_symbol:
            wanted.setdefault(r.instrument_symbol, r.instrument_name or r.instrument_symbol)
    for h in holdings:
        wanted.setdefault(h.symbol, h.name or h.symbol)
    for symbol, name in wanted.items():
        exists = conn.execute("SELECT 1 FROM instrument WHERE symbol = %s AND market = ANY(%s)",
                              (symbol, list(KR_MARKETS))).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO instrument (kind, asset_class, symbol, market, name, currency, country)
                   VALUES (%s, 'equity', %s, 'KRX', %s, 'KRW', 'KR')""",
                (guess_kind(name), symbol, name))


def _computed_positions(conn: Conn, account_id: int) -> dict[str, Decimal]:
    rows = conn.execute(
        """SELECT i.symbol, sum(t.quantity) AS qty FROM txn t JOIN instrument i ON i.id = t.instrument_id
            WHERE t.account_id = %s AND t.status = 'posted' AND t.quantity IS NOT NULL
              AND i.market = ANY(%s) GROUP BY i.symbol""", (account_id, list(KR_MARKETS))).fetchall()
    return {r["symbol"]: r["qty"] for r in rows}


def _computed_cash(conn: Conn, account_id: int) -> dict[str, Decimal]:
    rows = conn.execute("""SELECT currency, sum(amount) AS bal FROM txn WHERE account_id = %s AND status = 'posted'
                            GROUP BY currency""", (account_id,)).fetchall()
    return {r["currency"]: r["bal"] for r in rows}


def _n(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def reconcile(conn: Conn, account_id: int, snap: Snapshot, *, source_id: int, provider: str,
              when: datetime, opening: bool) -> list[dict]:
    """증권사 잔고와 계산 잔고의 차이를 조정 거래로 넣고, 넣은 내역을 돌려준다."""
    made: list[dict] = []
    label = "기초 보유 (증권사 잔고 기준)" if opening else "잔고 맞춤 (증권사 잔고 기준)"
    day = when.astimezone(KST).date()
    positions = _computed_positions(conn, account_id)
    snap_qty = {h.symbol: h for h in snap.holdings}
    for symbol in sorted(set(positions) | set(snap_qty)):
        have = positions.get(symbol, Decimal(0))
        h = snap_qty.get(symbol)
        want = h.quantity if h else Decimal(0)
        diff = want - have
        if diff == 0:
            continue
        inst = conn.execute("SELECT id, name FROM instrument WHERE symbol = %s AND market = ANY(%s) ORDER BY id LIMIT 1",
                            (symbol, list(KR_MARKETS))).fetchone()
        price = (h.avg_price if h and h.avg_price else None)
        kind = "instrument_in" if diff > 0 else "instrument_out"
        conn.execute(
            """INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency, instrument_id, quantity,
                                unit_price, description, data_source_id, dedupe_key)
               VALUES (%s, %s, %s, %s, 0, 'KRW', %s, %s, %s, %s, %s, %s)
               ON CONFLICT (account_id, dedupe_key) DO NOTHING""",
            (account_id, when, day, kind, inst["id"], diff, price, f"{label}: {inst['name']}", source_id,
             f"recon:{provider}:{day}:{symbol}:{_n(diff)}"))
        made.append({"type": "quantity", "symbol": symbol, "name": inst["name"], "diff": _n(diff)})
    cash = _computed_cash(conn, account_id)
    for currency, want in snap.cash.items():
        diff = want - cash.get(currency, Decimal(0))
        if abs(diff) < Decimal("0.01"):
            continue
        conn.execute(
            """INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency, description,
                                data_source_id, dedupe_key)
               VALUES (%s, %s, %s, 'adjustment', %s, %s, %s, %s, %s)
               ON CONFLICT (account_id, dedupe_key) DO NOTHING""",
            (account_id, when, day, diff, currency,
             label if opening else f"{label} · 수수료·세금·입출금·배당 등 API 에 없는 차액", source_id,
             f"recon:{provider}:{day}:cash:{currency}:{_n(diff)}"))
        made.append({"type": "cash", "currency": currency, "diff": _n(diff)})
    return made


def _store_snapshot(conn: Conn, account_id: int, snap: Snapshot, day: date) -> None:
    for currency, value in snap.cash.items():
        total = snap.total_value if currency == "KRW" and snap.total_value is not None else value
        conn.execute(
            """INSERT INTO reported_balance (account_id, as_of, currency, cash_amount, total_value)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (account_id, as_of, currency)
               DO UPDATE SET cash_amount = EXCLUDED.cash_amount, total_value = EXCLUDED.total_value""",
            (account_id, day, currency, value, total))
    for h in snap.holdings:
        inst = conn.execute("SELECT id FROM instrument WHERE symbol = %s AND market = ANY(%s) ORDER BY id LIMIT 1",
                            (h.symbol, list(KR_MARKETS))).fetchone()
        conn.execute(
            """INSERT INTO reported_holding (account_id, as_of, instrument_id, quantity, avg_cost, market_value)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (account_id, as_of, instrument_id)
               DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost,
                             market_value = EXCLUDED.market_value""",
            (account_id, day, inst["id"], h.quantity, h.avg_price, (h.price * h.quantity) if h.price else None))


def sync_account(conn: Conn, connector: Connector, ds: dict, account: dict, today: date) -> dict:
    ref = account["external_ref"]
    config = ds["config"] or {}
    last = (config.get("synced_until") or {}).get(ref)
    first = conn.execute("SELECT NOT EXISTS (SELECT 1 FROM txn WHERE account_id = %s) AS empty",
                         (account["id"],)).fetchone()["empty"]
    if last:
        start = date.fromisoformat(last) - OVERLAP
    else:
        start = date.fromisoformat((config.get("start_dates") or {}).get(ref) or (today - DEFAULT_LOOKBACK).isoformat())
    rows = connector.ledger(ref, start, today)
    snap = connector.snapshot(ref)
    ensure_instruments(conn, rows, snap.holdings)

    report = service.analyze_parsed(conn, account["id"], ParseResult(format=connector.name, rows=rows))
    report = service.commit_report(conn, account["id"], report, source_id=ds["id"],
                                   file_name=f"{connector.name} API {start:%Y-%m-%d}~{today:%Y-%m-%d}")
    # 첫 동기화의 기초 보유는 시작일 전날로, 이후 잔고 맞춤은 오늘로
    if first:
        when = datetime.combine(start - timedelta(days=1), time(23, 59), tzinfo=KST)
    else:
        when = datetime.now(KST) if today == datetime.now(KST).date() else datetime.combine(today, time(23, 59), tzinfo=KST)
    adjustments = reconcile(conn, account["id"], snap, source_id=ds["id"], provider=connector.provider,
                            when=when, opening=first)
    _store_snapshot(conn, account["id"], snap, today)
    counts = report.counts()
    warnings = [w for w in report.warnings if "계산 잔액" not in w]   # 잔고 맞춤이 처리하는 경고는 뺀다
    skipped = getattr(connector, "skipped", 0)
    if skipped:
        warnings.append(f"외화(해외주식) 거래 {skipped}건은 아직 지원하지 않아 건너뛰었습니다. 외화 예수금은 잔고 맞춤으로 반영됩니다.")
    errors = [r.message for r in report.rows if r.status == "error"]
    return {"account_id": account["id"], "account_name": account["name"], "ref": ref,
            "period": [start.isoformat(), today.isoformat()], "new": counts["new"], "duplicate": counts["duplicate"],
            "errors": errors, "adjustments": adjustments, "warnings": warnings,
            "broker_cash": {k: str(v) for k, v in snap.cash.items()},
            "broker_total": str(snap.total_value) if snap.total_value is not None else None}


def sync_source(conn: Conn, source_id: int, *, client: httpx.Client | None = None, today: date | None = None,
                min_interval: float = 0.25, log: Callable[[str], None] = lambda m: None) -> dict:
    """연결 하나를 동기화한다. 계좌 하나가 실패해도 나머지는 계속한다."""
    ds = load_source(conn, source_id)
    own = client is None
    client = client or make_client()
    run_id = conn.execute("INSERT INTO sync_run (data_source_id) VALUES (%s) RETURNING id", (source_id,)).fetchone()["id"]
    today = today or datetime.now(KST).date()
    results, failures = [], []
    try:
        connector = connector_for(conn, ds, client, min_interval)
        connector.today = today
        accounts = conn.execute(
            """SELECT id, name, external_ref FROM account WHERE data_source_id = %s AND external_ref IS NOT NULL
                AND closed_on IS NULL ORDER BY id""", (source_id,)).fetchall()
        config = dict(ds["config"] or {})
        synced = dict(config.get("synced_until") or {})
        for acc in accounts:
            try:
                with conn.transaction():
                    ds["config"] = {**config, "synced_until": synced}
                    res = sync_account(conn, connector, ds, acc, today)
                results.append(res)
                synced[acc["external_ref"]] = today.isoformat()
                log(f"{acc['name']}: 새 거래 {res['new']}건, 잔고 맞춤 {len(res['adjustments'])}건")
            except BrokerError as e:
                failures.append({"account_id": acc["id"], "account_name": acc["name"], "error": str(e)})
                log(f"{acc['name']}: 실패 - {e}")
        config["synced_until"] = synced
        status = "succeeded" if not failures else ("partial" if results else "failed")
        error = "; ".join(f"{f['account_name']}: {f['error']}" for f in failures) or None
        if not accounts:
            status, error = "failed", "연결된 계좌가 없습니다. 관리 화면에서 증권사 계좌를 AssetHub 계좌에 연결하세요."
        conn.execute("""UPDATE data_source SET config = %s, last_synced_at = now(), status = %s, last_error = %s
                         WHERE id = %s""",
                     (Jsonb(config), "active" if status != "failed" else "error", error, source_id))
    except BrokerError as e:
        status, error = "failed", str(e)
        conn.execute("UPDATE data_source SET status = 'error', last_error = %s WHERE id = %s", (error, source_id))
    finally:
        if own:
            client.close()
    summary = {"accounts": results, "failures": failures}
    conn.execute("UPDATE sync_run SET finished_at = now(), status = %s, summary = %s, error = %s WHERE id = %s",
                 (status, Jsonb(summary), error, run_id))
    return {"run_id": run_id, "status": status, "error": error, **summary}
