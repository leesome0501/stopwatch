"""증권사 API 연결 (키움, 한국투자). 앱키는 암호화해 저장하고 응답에는 절대 내보내지 않는다."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from ..brokers.base import BrokerError, Credentials, make_client
from ..brokers.sync import DEFAULT_LOOKBACK, INSTITUTION, PROVIDERS, connector_for, load_source, sync_source
from ..db import Conn, get_conn
from ..importer.parsing import KST
from ..secrets import decrypt_json, encrypt_json
from .common import require

router = APIRouter(tags=["증권사 연결"])

Provider = Literal["kiwoom", "kis"]
PROVIDER_NAME = {"kiwoom": "키움증권", "kis": "한국투자증권"}


class ConnectionIn(BaseModel):
    provider: Provider
    member_id: int
    label: str | None = None
    environment: Literal["real", "mock"] = "real"
    app_key: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)
    accounts: list[str] = []      # 한국투자: '12345678-01'
    verify: bool = True


class ConnectionPatch(BaseModel):
    label: str | None = None
    app_key: str | None = Field(default=None, min_length=1)
    app_secret: str | None = Field(default=None, min_length=1)
    environment: Literal["real", "mock"] | None = None
    accounts: list[str] | None = None


class LinkIn(BaseModel):
    ref: str
    account_id: int | None = None          # 기존 계좌에 연결
    create_name: str | None = None         # 없으면 새 위탁 계좌를 만든다
    start_date: date | None = None         # 첫 동기화에서 거래를 받기 시작할 날


class UnlinkIn(BaseModel):
    ref: str


def _transport(request: Request):
    return getattr(request.app.state, "http_transport", None)


def _today():
    from datetime import datetime
    return datetime.now(KST).date()


def _source(conn: Conn, source_id: int) -> dict:
    try:
        ds = load_source(conn, source_id)
    except BrokerError:
        raise HTTPException(404, "증권사 연결을 찾을 수 없습니다.") from None
    if (ds["config"] or {}).get("deleted"):
        raise HTTPException(404, "해제된 연결입니다.")
    return ds


def _public(conn: Conn, ds: dict) -> dict:
    creds = Credentials.from_dict(decrypt_json(ds["credential_enc"])) if ds["credential_enc"] else None
    linked = conn.execute(
        """SELECT id AS account_id, name AS account_name, external_ref AS ref FROM account
            WHERE data_source_id = %s AND external_ref IS NOT NULL ORDER BY id""", (ds["id"],)).fetchall()
    member = conn.execute("SELECT name FROM member WHERE id = %s", (ds["member_id"],)).fetchone() if ds["member_id"] else None
    last_run = conn.execute(
        """SELECT id, started_at, finished_at, status, error FROM sync_run WHERE data_source_id = %s
            ORDER BY id DESC LIMIT 1""", (ds["id"],)).fetchone()
    config = ds["config"] or {}
    return {
        "id": ds["id"], "provider": ds["provider"], "provider_name": PROVIDER_NAME.get(ds["provider"], ds["provider"]),
        "label": ds["label"], "member_id": ds["member_id"], "member_name": member["name"] if member else None,
        "environment": creds.environment if creds else None,
        "key_hint": f"…{creds.app_key[-4:]}" if creds and creds.app_key else None,
        "kis_accounts": creds.accounts if creds and ds["provider"] == "kis" else [],
        "status": ds["status"], "last_synced_at": ds["last_synced_at"], "last_error": ds["last_error"],
        "linked": [{**l, "synced_until": (config.get("synced_until") or {}).get(l["ref"]),
                    "start_date": (config.get("start_dates") or {}).get(l["ref"])} for l in linked],
        "last_run": last_run,
    }


@router.get("/api/households/{household_id}/connections")
def list_connections(household_id: int, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    rows = conn.execute(
        """SELECT * FROM data_source WHERE household_id = %s AND provider = ANY(%s)
            AND NOT coalesce((config->>'deleted')::boolean, false) ORDER BY id""",
        (household_id, list(PROVIDERS))).fetchall()
    return [_public(conn, ds) for ds in rows]


@router.post("/api/households/{household_id}/connections", status_code=201)
def create_connection(household_id: int, body: ConnectionIn, request: Request, conn: Conn = Depends(get_conn)):
    """앱키를 받아 증권사에 실제로 확인한 뒤 저장한다. 확인에 실패하면 아무것도 저장하지 않는다."""
    require(conn, "household", household_id, "가구")
    if not conn.execute("SELECT 1 FROM member WHERE id = %s AND household_id = %s",
                        (body.member_id, household_id)).fetchone():
        raise HTTPException(422, "명의자는 이 가구의 구성원이어야 합니다.")
    creds = Credentials(app_key=body.app_key.strip(), app_secret=body.app_secret.strip(),
                        environment=body.environment, accounts=[a.strip() for a in body.accounts if a.strip()])
    if body.provider == "kis":
        from ..brokers.kis import split_account
        try:
            creds.accounts = [f"{c}-{p}" for c, p in (split_account(a) for a in creds.accounts)]
        except BrokerError as e:
            raise HTTPException(422, str(e)) from None
        if not creds.accounts:
            raise HTTPException(422, "한국투자는 계좌번호를 하나 이상 입력해야 합니다 (예: 12345678-01).")
    inst = conn.execute("SELECT id FROM institution WHERE code = %s", (INSTITUTION[body.provider],)).fetchone()
    member = conn.execute("SELECT name FROM member WHERE id = %s", (body.member_id,)).fetchone()
    label = body.label or f"{PROVIDER_NAME[body.provider]} · {member['name']}"
    ds = conn.execute(
        """INSERT INTO data_source (household_id, member_id, institution_id, provider, label, credential_enc, config)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
        (household_id, body.member_id, inst["id"] if inst else None, body.provider, label,
         encrypt_json(creds.to_dict()), Jsonb({"start_dates": {}, "synced_until": {}}))).fetchone()
    broker_accounts = []
    if body.verify:
        with make_client(_transport(request)) as client:
            try:
                broker_accounts = [a.__dict__ for a in connector_for(conn, ds, client).accounts()]
            except BrokerError as e:
                raise HTTPException(422, f"앱키를 확인하지 못했습니다: {e}") from None
    ds = load_source(conn, ds["id"])
    return {**_public(conn, ds), "broker_accounts": broker_accounts}


@router.patch("/api/connections/{source_id}")
def update_connection(source_id: int, body: ConnectionPatch, conn: Conn = Depends(get_conn)):
    ds = _source(conn, source_id)
    creds = Credentials.from_dict(decrypt_json(ds["credential_enc"]))
    changes = body.model_dump(exclude_unset=True)
    if "app_key" in changes or "app_secret" in changes or "environment" in changes:
        creds.token = creds.token_expires = None   # 키가 바뀌면 토큰도 새로
    for k in ("app_key", "app_secret", "environment"):
        if changes.get(k):
            setattr(creds, k, changes[k].strip() if isinstance(changes[k], str) else changes[k])
    if body.accounts is not None:
        from ..brokers.kis import split_account
        try:
            creds.accounts = [f"{c}-{p}" for c, p in (split_account(a) for a in body.accounts if a.strip())]
        except BrokerError as e:
            raise HTTPException(422, str(e)) from None
    conn.execute("UPDATE data_source SET credential_enc = %s, label = coalesce(%s, label), status = 'active', "
                 "last_error = NULL WHERE id = %s", (encrypt_json(creds.to_dict()), body.label, source_id))
    return _public(conn, load_source(conn, source_id))


@router.delete("/api/connections/{source_id}", status_code=204)
def delete_connection(source_id: int, conn: Conn = Depends(get_conn)):
    """연결을 해제한다. 앱키는 지우고, 이미 받은 거래와 계좌는 그대로 둔다."""
    ds = _source(conn, source_id)
    conn.execute("UPDATE account SET data_source_id = NULL, external_ref = NULL WHERE data_source_id = %s", (source_id,))
    config = {**(ds["config"] or {}), "deleted": True}
    conn.execute("UPDATE data_source SET credential_enc = NULL, status = 'paused', config = %s WHERE id = %s",
                 (Jsonb(config), source_id))
    return Response(status_code=204)


@router.get("/api/connections/{source_id}/broker-accounts")
def broker_accounts(source_id: int, request: Request, conn: Conn = Depends(get_conn)):
    """증권사가 알려준 계좌 목록과 AssetHub 계좌 연결 상태."""
    ds = _source(conn, source_id)
    with make_client(_transport(request)) as client:
        try:
            accounts = connector_for(conn, ds, client).accounts()
        except BrokerError as e:
            raise HTTPException(422, str(e)) from None
    linked = {r["external_ref"]: r for r in conn.execute(
        "SELECT id, name, external_ref FROM account WHERE data_source_id = %s", (source_id,)).fetchall()}
    return [{"ref": a.ref, "label": a.label, "account_id": linked.get(a.ref, {}).get("id"),
             "account_name": linked.get(a.ref, {}).get("name")} for a in accounts]


@router.post("/api/connections/{source_id}/link")
def link_account(source_id: int, body: LinkIn, conn: Conn = Depends(get_conn)):
    ds = _source(conn, source_id)
    ref = body.ref.strip()
    creds = Credentials.from_dict(decrypt_json(ds["credential_enc"]))
    if ds["provider"] == "kis" and ref not in creds.accounts:
        raise HTTPException(422, "이 연결에 등록된 계좌번호가 아닙니다.")
    if conn.execute("SELECT 1 FROM account WHERE data_source_id = %s AND external_ref = %s", (source_id, ref)).fetchone():
        raise HTTPException(409, "이미 연결된 계좌입니다.")
    if body.account_id is not None:
        acc = conn.execute("SELECT * FROM account WHERE id = %s AND household_id = %s",
                           (body.account_id, ds["household_id"])).fetchone()
        if acc is None:
            raise HTTPException(422, "이 가구의 계좌가 아닙니다.")
        if acc["valuation_method"] != "transactions":
            raise HTTPException(422, "평가액 직접 입력 계좌에는 연결할 수 없습니다.")
        if acc["data_source_id"] is not None and acc["external_ref"] is not None:
            raise HTTPException(409, "이미 다른 증권사 연결에 묶인 계좌입니다.")
        conn.execute("UPDATE account SET data_source_id = %s, external_ref = %s, updated_at = now() WHERE id = %s",
                     (source_id, ref, acc["id"]))
        account_id = acc["id"]
    else:
        name = (body.create_name or "").strip() or f"{PROVIDER_NAME[ds['provider']]} {ref}"
        masked = f"{ref[:4]}-***-{ref[-4:]}" if len(ref) >= 8 else ref
        account_id = conn.execute(
            """INSERT INTO account (household_id, institution_id, name, account_type, account_number_masked,
                                    data_source_id, external_ref)
               VALUES (%s, %s, %s, 'brokerage', %s, %s, %s) RETURNING id""",
            (ds["household_id"], ds["institution_id"], name, masked, source_id, ref)).fetchone()["id"]
        if ds["member_id"]:
            conn.execute("INSERT INTO account_owner (account_id, member_id, share) VALUES (%s, %s, 1)",
                         (account_id, ds["member_id"]))
    config = dict(ds["config"] or {})
    starts = dict(config.get("start_dates") or {})
    starts[ref] = (body.start_date or (_today() - DEFAULT_LOOKBACK)).isoformat()
    config["start_dates"] = starts
    conn.execute("UPDATE data_source SET config = %s WHERE id = %s", (Jsonb(config), source_id))
    return _public(conn, load_source(conn, source_id))


@router.post("/api/connections/{source_id}/unlink")
def unlink_account(source_id: int, body: UnlinkIn, conn: Conn = Depends(get_conn)):
    ds = _source(conn, source_id)
    conn.execute("UPDATE account SET data_source_id = NULL, external_ref = NULL WHERE data_source_id = %s AND external_ref = %s",
                 (source_id, body.ref))
    config = dict(ds["config"] or {})
    for key in ("synced_until", "start_dates"):
        config[key] = {k: v for k, v in (config.get(key) or {}).items() if k != body.ref}
    conn.execute("UPDATE data_source SET config = %s WHERE id = %s", (Jsonb(config), source_id))
    return _public(conn, load_source(conn, source_id))


@router.post("/api/connections/{source_id}/sync")
def sync_connection(source_id: int, request: Request, conn: Conn = Depends(get_conn)):
    """지금 동기화한다. 거래를 받고 증권사 잔고에 맞춘다."""
    _source(conn, source_id)
    with make_client(_transport(request)) as client:
        return sync_source(conn, source_id, client=client, min_interval=getattr(request.app.state, "broker_interval", 0.25))


@router.get("/api/connections/{source_id}/runs")
def sync_runs(source_id: int, limit: int = 10, conn: Conn = Depends(get_conn)):
    _source(conn, source_id)
    return conn.execute("""SELECT id, started_at, finished_at, status, summary, error FROM sync_run
                            WHERE data_source_id = %s ORDER BY id DESC LIMIT %s""", (source_id, min(limit, 100))).fetchall()
