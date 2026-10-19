from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile

from ..db import Conn, get_conn
from ..importer import service
from ..importer.reader import UnreadableFile
from ..importer.standard import build_template
from ..schemas import ImportBatch, ImportResult, ImportRowOut
from .accounts import fetch_account

router = APIRouter(tags=["엑셀 가져오기"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/api/import-template")
def download_template():
    return Response(build_template(), media_type=XLSX,
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''AssetHub_import_template.xlsx"})


async def _read(request: Request, file: UploadFile) -> bytes:
    limit = request.app.state.settings.max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"파일이 너무 큽니다 (최대 {limit // 1024 // 1024}MB).")
    return data


def _result(report: service.ImportReport, committed: bool) -> ImportResult:
    rows: list[ImportRowOut] = []
    for a in report.rows:
        r = a.row
        rows.append(ImportRowOut(
            file_index=r.file_index, status=a.status, occurred_at=r.moment.at, trade_date=r.moment.day,
            kind=r.kind, amount=r.amount, currency=a.currency, description=r.description,
            counterparty=r.counterparty, balance_after=r.balance_after, instrument_symbol=r.instrument_symbol,
            quantity=r.quantity, unit_price=r.unit_price, category_id=a.category_id,
            category_name=a.category_name, category_source=a.category_source, message=a.message))
    for e in report.errors:
        rows.append(ImportRowOut(
            file_index=e.file_index, status="error", occurred_at=None, trade_date=None, kind=None,
            amount=None, currency=None, description=" ".join(e.raw.values())[:200] or None,
            counterparty=None, balance_after=None, instrument_symbol=None, quantity=None,
            unit_price=None, category_id=None, category_name=None, category_source=None, message=e.message))
    return ImportResult(
        committed=committed, batch_id=report.batch_id, format=report.format, file_direction=report.direction,
        account_number=report.account_number, counts=report.counts(), opening_balance=report.opening_balance,
        warnings=report.warnings, rows=rows)


@router.post("/api/accounts/{account_id}/imports/preview", response_model=ImportResult)
async def preview_import(account_id: int, file: UploadFile, request: Request, conn: Conn = Depends(get_conn)):
    """파일을 분석만 하고 저장하지 않는다. 행마다 새 거래/중복/오류와 자동 분류 결과를 보여준다."""
    fetch_account(conn, account_id)
    data = await _read(request, file)
    try:
        return _result(service.analyze(conn, account_id, data), committed=False)
    except UnreadableFile as e:
        raise HTTPException(422, str(e)) from None


@router.post("/api/accounts/{account_id}/imports", response_model=ImportResult, status_code=201)
async def commit_import(account_id: int, file: UploadFile, request: Request, conn: Conn = Depends(get_conn)):
    """파일을 분석해 새 거래만 저장한다. 같은 파일을 다시 올려도 중복으로 들어가지 않는다."""
    fetch_account(conn, account_id)
    data = await _read(request, file)
    try:
        report = service.commit(conn, account_id, data, file.filename)
    except UnreadableFile as e:
        raise HTTPException(422, str(e)) from None
    if report.format is None:
        raise HTTPException(422, report.warnings[0] if report.warnings else "읽을 수 있는 표가 없습니다.")
    return _result(report, committed=True)


@router.get("/api/accounts/{account_id}/imports", response_model=list[ImportBatch])
def list_imports(account_id: int, conn: Conn = Depends(get_conn)):
    fetch_account(conn, account_id)
    return conn.execute(
        """SELECT id, started_at, finished_at, status, file_name, records_total, records_new,
                  records_duplicate, error
             FROM import_batch WHERE account_id = %s ORDER BY id DESC""",
        (account_id,)).fetchall()
