"""키움증권 REST API (https://openapi.kiwoom.com).

- 앱키는 계좌에 묶여 있다. 계좌번호는 ka00001 로 받고, 조회 요청에는 계좌번호를 넣지 않는다.
- 호출: POST {host}{path}, 헤더 api-id 에 TR 코드. 연속조회는 응답 헤더 cont-yn=Y 와 next-key.
- 한도: 국내 계좌 조회 초당 5회(공식). 기본 간격 0.25초.
- 거래내역 kt00015(위탁종합거래내역)가 입출금·배당·이자·세금·수수료·환전까지 준다.
- 키 발급 전에 접속 IP를 키움에 등록해야 하고, 3개월 미접속 시 자동 해지된다.
필드 이름은 키움 공식 포털 스펙(2026-06-18판 사본)에 따른다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ..importer.parsing import KST, ParsedMoment
from ..importer.rows import ImportRow
from .base import (BrokerAccount, BrokerError, Connector, SnapHolding, Snapshot, guess_kind, kr_symbol,
                   kst_moment, num)

HOSTS = {"real": "https://api.kiwoom.com", "mock": "https://mockapi.kiwoom.com"}
LEDGER_CHUNK_DAYS = 90
MAX_PAGES = 200


def classify(row: dict) -> str:
    """kt00015 한 행의 적요·입출구분으로 표준 유형을 정한다."""
    text = f"{row.get('rmrk_nm', '')} {row.get('io_tp_nm', '')} {row.get('trde_kind_nm', '')}"
    has_stock = bool(kr_symbol(row.get("stk_cd", "")))
    if "환전" in text:
        return "fx"
    if "배당" in text:
        return "dividend"
    if has_stock and "매수" in text:
        return "buy"
    if has_stock and "매도" in text:
        return "sell"
    if "입고" in text:
        return "instrument_in"
    if "출고" in text:
        return "instrument_out"
    if "이용료" in text or ("이자" in text and "신용" not in text and "대출" not in text):
        return "interest"
    if "수수료" in text or "이자" in text:
        return "fee"
    if "세금" in text or "원천" in text:
        return "tax"
    if "입금" in text:
        return "cash_in"
    if "출금" in text:
        return "cash_out"
    return "unknown"


NEGATIVE = {"buy", "fee", "tax", "cash_out"}
POSITIVE = {"sell", "dividend", "interest", "cash_in"}


class Kiwoom(Connector):
    provider = "kiwoom"
    name = "키움증권"
    ledger_has_cash = True
    skipped = 0

    @property
    def host(self) -> str:
        return HOSTS.get(self.creds.environment, HOSTS["real"])

    # ------------------------------------------------------------ 인증
    def token(self) -> str:
        if self._token_valid():
            return self.creds.token
        self.throttle.wait()
        try:
            r = self.client.post(f"{self.host}/oauth2/token", json={
                "grant_type": "client_credentials", "appkey": self.creds.app_key, "secretkey": self.creds.app_secret},
                headers={"api-id": "au10001", "Content-Type": "application/json;charset=UTF-8"})
        except Exception as e:  # 네트워크
            raise BrokerError(f"키움 서버에 연결하지 못했습니다: {e.__class__.__name__}") from e
        body = self._json(r)
        token = body.get("token")
        if not token:
            raise BrokerError(f"키움 토큰 발급 실패: {body.get('return_msg') or r.text[:200]}")
        exp = body.get("expires_dt") or ""
        try:
            expires = datetime.strptime(exp, "%Y%m%d%H%M%S").replace(tzinfo=KST)
        except ValueError:
            expires = datetime.now(KST) + timedelta(hours=12)
        self.creds.token, self.creds.token_expires = token, expires.isoformat()
        self.on_token(self.creds)
        return token

    def _json(self, r) -> dict:
        try:
            body = r.json()
        except ValueError as e:
            raise BrokerError(f"키움 응답을 읽을 수 없습니다 (HTTP {r.status_code})") from e
        if r.status_code >= 400 or str(body.get("return_code", "0")) not in ("0", ""):
            msg = body.get("return_msg") or body.get("error_description") or r.text[:200]
            raise BrokerError(f"키움 오류: {msg}")
        return body

    def call(self, api_id: str, body: dict, path: str = "/api/dostk/acnt") -> list[dict]:
        """연속조회를 끝까지 따라가 응답 본문 목록을 돌려준다."""
        pages, cont, next_key = [], "N", ""
        for _ in range(MAX_PAGES):
            self.throttle.wait()
            headers = {"api-id": api_id, "authorization": f"Bearer {self.token()}",
                       "Content-Type": "application/json;charset=UTF-8", "cont-yn": cont, "next-key": next_key}
            try:
                r = self.client.post(f"{self.host}{path}", json=body, headers=headers)
            except Exception as e:
                raise BrokerError(f"키움 서버에 연결하지 못했습니다: {e.__class__.__name__}") from e
            pages.append(self._json(r))
            if r.headers.get("cont-yn") == "Y" and r.headers.get("next-key"):
                cont, next_key = "Y", r.headers["next-key"]
            else:
                break
        return pages

    # ------------------------------------------------------------ 조회
    def accounts(self) -> list[BrokerAccount]:
        pages = self.call("ka00001", {})
        raw = pages[0].get("acctNo") if pages else None
        nums = raw if isinstance(raw, list) else [x for x in str(raw or "").replace(";", ",").split(",") if x.strip()]
        out = []
        for n in nums:
            n = str(n).strip()
            out.append(BrokerAccount(ref=n, label=f"{n[:4]}-{n[4:8]}-{n[8:]}" if len(n) == 10 else n))
        if not out:
            raise BrokerError("키움이 계좌번호를 돌려주지 않았습니다. 앱키에 계좌가 등록되어 있는지 확인하세요.")
        return out

    def ledger(self, ref: str, start: date, end: date) -> list[ImportRow]:
        """원화 거래만 돌려준다. 외화(해외주식) 행은 보유 잔고 조회 TR 이 확인되지 않아 건너뛰고 skipped 에 센다."""
        rows: list[ImportRow] = []
        self.skipped = 0
        cur = start
        while cur <= end:
            chunk_end = min(end, cur + timedelta(days=LEDGER_CHUNK_DAYS - 1))
            for page in self.call("kt00015", {
                    "strt_dt": f"{cur:%Y%m%d}", "end_dt": f"{chunk_end:%Y%m%d}", "tp": "0", "stk_cd": "",
                    "crnc_cd": "", "gds_tp": "0", "frgn_stex_code": "", "dmst_stex_tp": "%", "qry_sort_tp": "2"}):
                for item in page.get("trst_ovrl_trde_prps_array") or []:
                    row = self._ledger_row(len(rows), item)
                    if row is not None:
                        rows.append(row)
            cur = chunk_end + timedelta(days=1)
        return rows

    def _ledger_row(self, idx: int, it: dict) -> ImportRow | None:
        kind = classify(it)
        currency = (it.get("crnc_cd") or "KRW").strip() or "KRW"
        foreign = currency != "KRW"
        if foreign:
            self.skipped += 1
            return None
        magnitude = abs(num(it.get("fc_exct_amt") if foreign else it.get("exct_amt")))
        qty = abs(num(it.get("trde_qty_jwa_cnt")))
        io = f"{it.get('io_tp_nm', '')}{it.get('rmrk_nm', '')}"
        if kind in NEGATIVE:
            amount = -magnitude
        elif kind in POSITIVE:
            amount = magnitude
        else:
            # 환전·기타: 입출구분으로 방향을 정한다
            amount = -magnitude if any(w in io for w in ("출", "매수", "지급")) else magnitude
        if kind == "unknown":
            kind = "cash_in" if amount >= 0 else "cash_out"
        if kind in ("instrument_in", "instrument_out") and qty == 0:
            return None
        if amount == 0 and kind not in ("instrument_in", "instrument_out"):
            return None
        symbol = kr_symbol(it.get("stk_cd", "")) or None
        quantity = None
        if symbol and kind in ("buy", "instrument_in"):
            quantity = qty
        elif symbol and kind in ("sell", "instrument_out"):
            quantity = -qty
        if kind in ("buy", "sell", "instrument_in", "instrument_out") and (not symbol or not qty):
            kind = "cash_in" if amount >= 0 else "cash_out"
            quantity = None
        tax = abs(num(it.get("trde_agri_tax"))) + abs(num(it.get("incm_resi_tax")))
        balance = None if foreign else (num(it.get("entra_remn")) if it.get("entra_remn") not in (None, "") else None)
        unit = num(it.get("trde_unit")) if quantity else None
        trde_dt = it.get("trde_dt") or ""
        moment = kst_moment(trde_dt, it.get("proc_tm"))
        return ImportRow(
            file_index=idx, moment=ParsedMoment(moment, bool(it.get("proc_tm"))), kind=kind, amount=amount,
            description=(it.get("rmrk_nm") or "").strip(), counterparty=(it.get("rcpmnyer") or "").strip() or None,
            balance_after=balance, currency=currency,
            instrument_symbol=symbol if quantity is not None or kind == "dividend" else None,
            instrument_market="KRX" if symbol else None, instrument_name=(it.get("stk_nm") or "").strip() or None,
            quantity=quantity, unit_price=unit or None,
            fee=abs(num(it.get("fc_cmsn") if foreign else it.get("cmsn"))), tax=tax,
            group_label=f"kiwoom-fx-{trde_dt}-{(it.get('orig_deal_no') or '').strip() or it.get('trde_no')}" if kind == "fx" else None,
            raw={k: str(v) for k, v in it.items() if v not in (None, "")},
            external_id=f"kiwoom:{trde_dt}:{(it.get('trde_no') or '').strip()}:{kind}",
        )

    def snapshot(self, ref: str) -> Snapshot:
        dep = self.call("kt00001", {"qry_tp": "3"})[0]
        cash = {"KRW": num(dep.get("d2_entra") or dep.get("entr"))}
        for fx in dep.get("stk_entr_prst") or []:
            cur = (fx.get("crnc_cd") or "").strip()
            if cur and cur != "KRW" and num(fx.get("d2_fx_entr") or fx.get("fx_entr")):
                cash[cur] = num(fx.get("d2_fx_entr") or fx.get("fx_entr"))
        holdings: list[SnapHolding] = []
        total = None
        for page in self.call("kt00018", {"qry_tp": "1", "dmst_stex_tp": "KRX"}):
            total = num(page.get("prsm_dpst_aset_amt")) if page.get("prsm_dpst_aset_amt") else total
            for h in page.get("acnt_evlt_remn_indv_tot") or []:
                qty = num(h.get("rmnd_qty"))
                if qty == 0:
                    continue
                name = (h.get("stk_nm") or "").strip()
                holdings.append(SnapHolding(symbol=kr_symbol(h.get("stk_cd", "")), name=name, quantity=qty,
                                            avg_price=num(h.get("pur_pric")) or None, price=num(h.get("cur_prc")) or None))
        return Snapshot(cash=cash, total_value=total, holdings=holdings, raw={"kt00001": dep})


__all__ = ["Kiwoom", "classify", "guess_kind"]
