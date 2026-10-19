"""파일 가져오기: 미리보기와 반영. 둘 다 같은 분석 단계를 거친다."""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from psycopg.types.json import Jsonb

from ..db import Conn
from .dedupe import dedupe_keys
from .detect import parse_file
from .rows import ImportRow, RowError
from .sequence import BALANCE_EPS, chain_issues, order_rows

GROUP_NS = uuid.UUID("0b6f2f3e-5d4c-4b1a-9a57-1f4f8e0a6c11")


class AccountNotFound(LookupError):
    pass


@dataclass
class AnalyzedRow:
    row: ImportRow
    status: str                       # new | duplicate | error
    currency: str
    dedupe_key: str | None = None
    instrument_id: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    category_source: str | None = None  # file | rule | history
    message: str | None = None


@dataclass
class ImportReport:
    format: str | None
    direction: str | None
    account_number: str | None
    rows: list[AnalyzedRow]
    errors: list[RowError]
    warnings: list[str] = field(default_factory=list)
    batch_id: int | None = None
    opening_balance: Decimal | None = None

    def counts(self) -> dict[str, int]:
        c = {"total": len(self.rows) + len(self.errors), "new": 0, "duplicate": 0, "error": len(self.errors)}
        for r in self.rows:
            c[r.status] += 1
        return c


# ---------------------------------------------------------------- 조회 도우미

def _account(conn: Conn, account_id: int) -> dict:
    acc = conn.execute(
        "SELECT id, household_id, name, base_currency, account_number_masked FROM account WHERE id = %s",
        (account_id,)).fetchone()
    if acc is None:
        raise AccountNotFound(account_id)
    return acc


def _instruments(conn: Conn, household_id: int, symbols: set[str]) -> list[dict]:
    if not symbols:
        return []
    return conn.execute(
        """SELECT id, symbol, market, currency FROM instrument
            WHERE symbol = ANY(%s) AND (household_id IS NULL OR household_id = %s)""",
        (list(symbols), household_id)).fetchall()


def _categories(conn: Conn, household_id: int) -> list[dict]:
    return conn.execute(
        """SELECT id, name, kind, household_id, parent_id FROM category
            WHERE household_id IS NULL OR household_id = %s
            ORDER BY household_id NULLS LAST, parent_id NULLS FIRST, id""",
        (household_id,)).fetchall()


def _rules(conn: Conn, household_id: int, account_id: int) -> list[dict]:
    return conn.execute(
        """SELECT match_field, match_type, pattern, category_id FROM category_rule
            WHERE household_id = %s AND enabled AND (account_id IS NULL OR account_id = %s)
            ORDER BY priority, id""",
        (household_id, account_id)).fetchall()


def _history(conn: Conn, household_id: int, field_name: str) -> dict[str, dict]:
    col = {"description": "t.description", "counterparty": "t.counterparty"}[field_name]
    rows = conn.execute(
        f"""SELECT DISTINCT ON ({col}) {col} AS key, t.category_id, c.kind
              FROM txn t JOIN account a ON a.id = t.account_id
              JOIN category c ON c.id = t.category_id
             WHERE a.household_id = %s AND {col} IS NOT NULL AND {col} <> ''
               AND t.status = 'posted'
             ORDER BY {col}, t.occurred_at DESC, t.id DESC""",
        (household_id,)).fetchall()
    return {r["key"]: r for r in rows}


# ---------------------------------------------------------------- 분석

def _last_digits(s: str | None, n: int = 4) -> str:
    return re.sub(r"\D", "", s or "")[-n:]


def _rule_matches(rule: dict, row: ImportRow) -> bool:
    value = (row.description if rule["match_field"] == "description" else row.counterparty) or ""
    pattern = rule["pattern"]
    if rule["match_type"] == "equals":
        return value == pattern
    if rule["match_type"] == "contains":
        return pattern.lower() in value.lower()
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


def _direction_fits(kind: str, amount: Decimal) -> bool:
    return kind == "transfer" or (kind == "income" and amount > 0) or (kind == "expense" and amount < 0)


def analyze(conn: Conn, account_id: int, data: bytes) -> ImportReport:
    acc = _account(conn, account_id)
    hid = acc["household_id"]
    parsed = parse_file(data)
    report = ImportReport(format=parsed.format, direction=None, account_number=parsed.account_number,
                          rows=[], errors=list(parsed.errors), warnings=list(parsed.warnings))
    if not parsed.rows:
        return report

    # 다른 계좌의 파일을 올린 것 같으면 경고
    file_last, acc_last = _last_digits(parsed.account_number), _last_digits(acc["account_number_masked"])
    if file_last and acc_last and file_last != acc_last:
        report.warnings.append(
            f"파일의 계좌번호(…{file_last})가 이 계좌(…{acc_last})와 다릅니다. 다른 계좌의 파일인지 확인해 주세요.")

    ordered, report.direction = order_rows(parsed.rows)

    instruments = _instruments(conn, hid, {r.instrument_symbol for r in ordered if r.instrument_symbol})
    by_name: dict[str, dict] = {}
    for c in _categories(conn, hid):
        by_name.setdefault(c["name"], c)   # 가구 카테고리 > 시스템 상위 > 시스템 하위 순서로 먼저 온 것
    rules = _rules(conn, hid, account_id)
    hist_desc = _history(conn, hid, "description")
    hist_cp = _history(conn, hid, "counterparty")
    unknown_categories: set[str] = set()

    analyzed: list[AnalyzedRow] = []
    for r in ordered:
        a = AnalyzedRow(row=r, status="new", currency=r.currency or acc["base_currency"])
        if r.instrument_symbol:
            cands = [i for i in instruments if i["symbol"] == r.instrument_symbol
                     and (r.instrument_market is None or i["market"] == r.instrument_market)]
            if len(cands) != 1:
                a.status = "error"
                a.message = (f"종목 {r.instrument_symbol}이(가) 등록되어 있지 않습니다." if not cands
                             else f"종목 {r.instrument_symbol}이(가) 여러 시장에 있습니다. 시장을 적어 주세요.")
            else:
                a.instrument_id = cands[0]["id"]
                if r.currency is None:
                    a.currency = cands[0]["currency"]
        # 카테고리: 파일 > 규칙 > 같은 적요의 과거 거래 > 같은 거래처의 과거 거래
        if r.category_name:
            c = by_name.get(r.category_name)
            if c:
                a.category_id, a.category_name, a.category_source = c["id"], c["name"], "file"
            else:
                unknown_categories.add(r.category_name)
        if a.category_id is None and r.kind in ("cash_in", "cash_out", "dividend", "interest", "fee", "tax"):
            rule = next((x for x in rules if _rule_matches(x, r)), None)
            if rule:
                a.category_id, a.category_source = rule["category_id"], "rule"
            else:
                for hist, key in ((hist_desc, r.description), (hist_cp, r.counterparty)):
                    h = hist.get(key) if key else None
                    if h and _direction_fits(h["kind"], r.amount):
                        a.category_id, a.category_source = h["category_id"], "history"
                        break
            if a.category_id is not None and a.category_name is None:
                a.category_name = next((c["name"] for c in by_name.values() if c["id"] == a.category_id), None)
        analyzed.append(a)

    if unknown_categories:
        report.warnings.append("없는 카테고리라 비워 둔 값: " + ", ".join(sorted(unknown_categories)))

    for row, cur in zip(ordered, [a.currency for a in analyzed]):
        row.currency = row.currency or cur
    report.warnings.extend(chain_issues(ordered))

    keys = dedupe_keys(ordered, [a.currency for a in analyzed])
    existing = {r["dedupe_key"] for r in conn.execute(
        "SELECT dedupe_key FROM txn WHERE account_id = %s AND dedupe_key = ANY(%s)",
        (account_id, keys)).fetchall()}
    seen: set[str] = set()
    for a, k in zip(analyzed, keys):
        a.dedupe_key = k
        if a.status == "error":
            continue
        if k in existing or k in seen:
            a.status = "duplicate"
            a.message = "이미 있는 거래" if k in existing else "파일 안에서 중복"
        seen.add(k)

    report.rows = analyzed
    return report


# ---------------------------------------------------------------- 반영

def _file_source(conn: Conn, household_id: int) -> int:
    row = conn.execute(
        "SELECT id FROM data_source WHERE household_id = %s AND provider = 'file' ORDER BY id LIMIT 1",
        (household_id,)).fetchone()
    if row:
        return row["id"]
    return conn.execute(
        "INSERT INTO data_source (household_id, provider, label) VALUES (%s, 'file', '파일 업로드') RETURNING id",
        (household_id,)).fetchone()["id"]


def _raw_payload(r: ImportRow) -> dict:
    return {"file_index": r.file_index, "cells": r.raw}


def commit(conn: Conn, account_id: int, data: bytes, file_name: str | None) -> ImportReport:
    report = analyze(conn, account_id, data)
    if report.format is None:
        return report   # 읽을 표가 없으면 아무것도 기록하지 않는다
    acc = _account(conn, account_id)
    source_id = _file_source(conn, acc["household_id"])
    sha = hashlib.sha256(data).hexdigest()

    if conn.execute(
            """SELECT 1 FROM import_batch WHERE account_id = %s AND file_sha256 = %s
                AND status IN ('succeeded','partial') LIMIT 1""", (account_id, sha)).fetchone():
        report.warnings.append("같은 파일을 전에 올린 적이 있습니다. 이미 있는 거래는 건너뛰었습니다.")

    batch_id = conn.execute(
        """INSERT INTO import_batch (data_source_id, account_id, file_name, file_sha256)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (source_id, account_id, file_name, sha)).fetchone()["id"]
    report.batch_id = batch_id

    had_txns = conn.execute("SELECT 1 FROM txn WHERE account_id = %s LIMIT 1", (account_id,)).fetchone() is not None
    new_rows = [a for a in report.rows if a.status == "new"]

    # 첫 업로드면 첫 거래의 '거래 후 잔액 - 금액' 을 기초잔액으로 넣어 계산 잔액이 은행과 맞게 한다
    first = new_rows[0] if new_rows else None
    if (first and not had_txns and first.row.balance_after is not None
            and not any(a.row.kind == "adjustment" for a in new_rows)):
        opening = first.row.balance_after - first.row.amount
        if opening != 0:
            conn.execute(
                """INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency,
                                    description, data_source_id, dedupe_key)
                   VALUES (%s, %s, %s, 'adjustment', %s, %s, '기초잔액 (파일 첫 거래 기준)', %s, 'opening-balance')""",
                (account_id, first.row.moment.at - timedelta(microseconds=1), first.row.moment.day,
                 opening, first.currency, source_id))
            report.opening_balance = opening

    for e in report.errors:
        conn.execute(
            """INSERT INTO raw_record (import_batch_id, record_type, payload, parse_status, parse_error)
               VALUES (%s, 'transaction', %s, 'error', %s)""",
            (batch_id, Jsonb({"file_index": e.file_index, "cells": e.raw}), e.message))

    for a in report.rows:
        r = a.row
        status = {"new": "parsed", "duplicate": "skipped", "error": "error"}[a.status]
        raw_id = conn.execute(
            """INSERT INTO raw_record (import_batch_id, record_type, payload, parse_status, parse_error)
               VALUES (%s, 'transaction', %s, %s, %s) RETURNING id""",
            (batch_id, Jsonb(_raw_payload(r)), status, a.message)).fetchone()["id"]
        if a.status != "new":
            continue
        group_id = uuid.uuid5(GROUP_NS, f"{batch_id}:{r.group_label}") if r.group_label else None
        conn.execute(
            """INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency,
                                instrument_id, quantity, unit_price, balance_after, fee, tax,
                                category_id, counterparty, description, memo, group_id,
                                data_source_id, raw_record_id, dedupe_key)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (account_id, r.moment.at, r.moment.day, r.kind, r.amount, a.currency,
             a.instrument_id, r.quantity, r.unit_price, r.balance_after, r.fee, r.tax,
             a.category_id, r.counterparty, r.description or None, r.memo, group_id,
             source_id, raw_id, a.dedupe_key))

    _check_final_balance(conn, account_id, report)

    counts = report.counts()
    conn.execute(
        """UPDATE import_batch SET finished_at = now(), status = %s,
                  records_total = %s, records_new = %s, records_duplicate = %s
            WHERE id = %s""",
        ("partial" if counts["error"] else "succeeded", counts["total"], counts["new"],
         counts["duplicate"], batch_id))
    conn.execute("UPDATE data_source SET last_synced_at = now(), status = 'active' WHERE id = %s", (source_id,))
    return report


def _check_final_balance(conn: Conn, account_id: int, report: ImportReport) -> None:
    """파일의 마지막 '거래 후 잔액' 과 DB 계산 잔액을 비교한다 (빠진 거래, 다른 계좌 파일 감지)."""
    last = next((a for a in reversed(report.rows) if a.status != "error" and a.row.balance_after is not None), None)
    if last is None:
        return
    row = conn.execute(
        """SELECT coalesce(sum(amount), 0) AS bal FROM txn
            WHERE account_id = %s AND currency = %s AND status = 'posted' AND occurred_at <= %s""",
        (account_id, last.currency, last.row.moment.at)).fetchone()
    computed: Decimal = row["bal"]
    if abs(computed - last.row.balance_after) > BALANCE_EPS:
        report.warnings.append(
            f"계좌의 계산 잔액 {computed:,.0f}이(가) 파일의 마지막 잔액 {last.row.balance_after:,.0f}과(와) "
            f"다릅니다. 중간에 빠진 거래가 있거나 다른 계좌의 파일일 수 있습니다.")
